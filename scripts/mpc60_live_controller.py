#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import os
import pty
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path


REPO = Path("/Users/izmar/git/codex-mame")
MAME_BIN = Path("/Users/izmar/git/mame/mame")
MAME_DIR = Path("/Users/izmar/git/mame")
LCD_READER = REPO / "scripts" / "mpc_lcd_reader.py"
HD61830_ROM = Path("/Users/izmar/git/mame/roms/hd61830.bin")
PLUGIN_PATHS = f"{REPO / 'plugins'};/Users/izmar/git/mame/plugins"
BRIDGE_SCRIPT = REPO / "scripts" / "mpc60_command_bridge.lua"


def load_lcd_reader_module():
    spec = importlib.util.spec_from_file_location("mpc_lcd_reader", LCD_READER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {LCD_READER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Mpc60LcdDecoder:
    def __init__(self, *, hd61830_rom: Path):
        self.reader = load_lcd_reader_module()
        self.templates = self.reader.build_hd61830_templates(hd61830_rom)
        self.cell_width = self.reader.CELL_WIDTH
        self.cell_height = self.reader.CELL_HEIGHT
        self.cell_bits = self.cell_width * self.cell_height
        self.full_cell_mask = (1 << self.cell_bits) - 1
        self.template_masks = {
            char: self.cell_to_mask(template)
            for char, template in self.templates.items()
        }

    def cell_to_mask(self, cell: list[list[bool]]) -> int:
        mask = 0
        bit = 0
        for y in range(self.cell_height):
            for x in range(self.cell_width):
                if cell[y][x]:
                    mask |= 1 << bit
                bit += 1
        return mask

    def crop_cell_mask(self, image_bits: list[list[bool]], x: int, y: int) -> int:
        mask = 0
        bit = 0
        for cy in range(self.cell_height):
            row = image_bits[y + cy]
            for cx in range(self.cell_width):
                if row[x + cx]:
                    mask |= 1 << bit
                bit += 1
        return mask

    def best_char_for_cell_mask(self, cell_mask: int) -> str:
        inverted_mask = cell_mask ^ self.full_cell_mask
        best_char = "?"
        best_score = self.cell_bits + 1
        for char, template_mask in self.template_masks.items():
            score = (cell_mask ^ template_mask).bit_count()
            if score < best_score:
                best_char = char
                best_score = score
            inverted_score = (inverted_mask ^ template_mask).bit_count()
            if inverted_score < best_score:
                best_char = char
                best_score = inverted_score
        return best_char

    def decode_fixed_row(self, image_bits: list[list[bool]], y: int) -> str:
        chars: list[str] = []
        for i in range(40):
            cell_mask = self.crop_cell_mask(image_bits, i * self.cell_width, y)
            chars.append(self.best_char_for_cell_mask(cell_mask))
        return "".join(chars).rstrip()

    def read_rows(self, image: Path) -> list[str]:
        image_bits = self.reader.load_bw_image(image)
        rows: list[str] = []
        for y in range(0, 64, 8):
            rows.append(self.decode_fixed_row(image_bits, y))
        return rows


class MameController:
    def __init__(self, *, hard_image: Path, visible: bool = True):
        self.hard_image = hard_image
        self.visible = visible
        self.proc: subprocess.Popen[str] | None = None
        self.master_fd: int | None = None
        self.lines: queue.Queue[str] = queue.Queue()
        self.history: list[str] = []
        self.reader_thread: threading.Thread | None = None

    def start(self) -> None:
        args = [
            str(MAME_BIN),
            "-console",
            "-snapview",
            "native",
            "-skip_gameinfo",
            "-plugin",
            "mpcprobe",
            "-pluginspath",
            PLUGIN_PATHS,
            "mpc60scsi",
            "-bios",
            "v214",
            "-hard",
            str(self.hard_image),
        ]
        if self.visible:
            args.insert(1, "-window")
        else:
            args.insert(1, "-nowindow")

        master_fd, slave_fd = pty.openpty()
        self.master_fd = master_fd
        self.proc = subprocess.Popen(
            args,
            cwd=MAME_DIR,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            text=False,
            close_fds=True,
        )
        os.close(slave_fd)
        self.reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self.reader_thread.start()
        self.wait_for("mpcprobe: ready", timeout=20)

    def _read_stdout(self) -> None:
        assert self.master_fd is not None
        pending = ""
        while True:
            try:
                data = os.read(self.master_fd, 4096)
            except OSError:
                break
            if not data:
                break
            decoded = data.decode("utf-8", errors="replace")
            if "\x1b[6n" in decoded and self.master_fd is not None:
                # MAME's linenoise console asks the terminal for cursor
                # position. If the pseudo-terminal controller does not answer,
                # the next command's first byte can be consumed as a broken
                # response. A fixed response is enough for non-interactive use.
                os.write(self.master_fd, b"\x1b[1;1R")
            pending += decoded
            while "\n" in pending:
                line, pending = pending.split("\n", 1)
                clean = line.rstrip("\r")
                self.history.append(clean)
                self.lines.put(clean)
        if pending:
            clean = pending.rstrip("\r")
            self.history.append(clean)
            self.lines.put(clean)

    def send(self, lua: str) -> None:
        assert self.master_fd is not None
        # Linenoise may have a pending cursor-position query at the prompt.
        # Answer before sending the command so the command's first byte is not
        # consumed as a malformed terminal response.
        os.write(self.master_fd, b"\x1b[1;80R")
        time.sleep(0.02)
        os.write(self.master_fd, (lua + "\n").encode("utf-8"))

    def wait_for(self, needle: str, *, timeout: float = 10) -> str:
        deadline = time.monotonic() + timeout
        recent: list[str] = []
        while time.monotonic() < deadline:
            try:
                line = self.lines.get(timeout=0.1)
            except queue.Empty:
                if self.proc and self.proc.poll() is not None:
                    tail = "\n".join((recent + self.history)[-40:])
                    raise RuntimeError(
                        f"MAME exited while waiting for {needle!r}; recent output:\n{tail}"
                    )
                continue
            recent.append(line)
            if needle in line:
                return line
        tail = "\n".join(recent[-20:])
        raise TimeoutError(f"timed out waiting for {needle!r}; recent output:\n{tail}")

    def snapshot_after(self, command: str | None, path: Path, *, timeout: float = 10) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        if command is not None:
            self.send(command)
        self.send(f'mpcprobe.snap("{path}")')
        self.wait_for(f"snapshot={path}", timeout=timeout)
        if not path.exists():
            raise RuntimeError(f"snapshot command completed but {path} does not exist")
        return path

    def clean_exit(self) -> None:
        if self.proc is None or self.proc.poll() is not None:
            return
        self.send("manager.machine:exit()")
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            raise RuntimeError("MAME did not exit cleanly within timeout")
        if self.master_fd is not None:
            os.close(self.master_fd)
            self.master_fd = None


class BridgeMameController:
    def __init__(self, *, hard_image: Path, bridge_dir: Path, visible: bool = True):
        self.hard_image = hard_image
        self.bridge_dir = bridge_dir
        self.visible = visible
        self.proc: subprocess.Popen[bytes] | None = None
        self.command_path = bridge_dir / "command.txt"
        self.response_path = bridge_dir / "response.txt"
        self.ready_path = bridge_dir / "ready.txt"
        self.command_id = 0

    def start(self) -> None:
        self.bridge_dir.mkdir(parents=True, exist_ok=True)
        for path in (self.command_path, self.response_path, self.ready_path):
            if path.exists():
                path.unlink()

        args = [
            str(MAME_BIN),
            "-snapview",
            "native",
            "-skip_gameinfo",
            "-plugin",
            "mpcprobe",
            "-pluginspath",
            PLUGIN_PATHS,
            "-autoboot_script",
            str(BRIDGE_SCRIPT),
            "mpc60scsi",
            "-bios",
            "v214",
            "-hard",
            str(self.hard_image),
        ]
        if self.visible:
            args.insert(1, "-window")
        else:
            args.insert(1, "-nowindow")

        env = os.environ.copy()
        env["MPC_BRIDGE_DIR"] = str(self.bridge_dir)
        self.proc = subprocess.Popen(
            args,
            cwd=MAME_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        self._wait_for_file(self.ready_path, timeout=20)

    def _wait_for_file(self, path: Path, *, timeout: float) -> str:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.proc and self.proc.poll() is not None:
                raise RuntimeError("MAME exited while waiting for bridge file")
            if path.exists():
                return path.read_text()
            time.sleep(0.05)
        raise TimeoutError(f"timed out waiting for {path}")

    def command(self, command: str, arg: str = "", *, timeout: float = 20) -> str:
        self.command_id += 1
        command_id = str(self.command_id)
        tmp = self.bridge_dir / "command.tmp"
        tmp.write_text(f"{command_id}|{command}|{arg}\n")
        tmp.replace(self.command_path)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.proc and self.proc.poll() is not None:
                raise RuntimeError("MAME exited while waiting for bridge response")
            if self.response_path.exists():
                response = self.response_path.read_text().strip()
                parts = response.split("|", 2)
                if parts and parts[0] == command_id:
                    if len(parts) >= 2 and parts[1] == "ok":
                        return response
                    raise RuntimeError(f"bridge command failed: {response}")
            time.sleep(0.05)
        raise TimeoutError(f"timed out waiting for bridge response to {command_id}|{command}")

    def snapshot_after(self, command: str | None, path: Path, *, timeout: float = 20) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        if command is not None:
            name, arg = command.split("|", 1)
            self.command(name, arg, timeout=timeout)
        self.command("snap", str(path), timeout=timeout)
        if not path.exists():
            raise RuntimeError(f"snapshot command completed but {path} does not exist")
        return path

    def clean_exit(self) -> None:
        if self.proc is None or self.proc.poll() is not None:
            return
        try:
            self.command("exit", "", timeout=5)
        except Exception:
            pass
        self.proc.wait(timeout=10)


def read_lcd(decoder: Mpc60LcdDecoder, image: Path) -> list[str]:
    return decoder.read_rows(image)


def selected_file(rows: list[str]) -> str:
    if len(rows) < 3:
        return ""
    line = rows[2]
    if "Size:" in line:
        line = line.split("Size:", 1)[0]
    return line.strip()


def comparable_file_name(name: str) -> str:
    return name.strip().upper()


def choose_visible_selected_file(variants: list[str]) -> str:
    cleaned = [variant.strip() for variant in variants if variant.strip()]
    if not cleaned:
        return ""
    # The cursor blink can temporarily hide one or more glyphs. Prefer the
    # frame that exposes the most text, then a deterministic lexical tie-break.
    return sorted(cleaned, key=lambda value: (len(value), value))[-1]


def print_rows(rows: list[str]) -> None:
    for row in rows:
        print(row)


def joined_rows(rows: list[str]) -> str:
    return "\n".join(rows)


def classify_screen(rows: list[str]) -> str:
    text = joined_rows(rows).upper()
    if "AKAI MPC60" in text or "VERSION 2.14" in text:
        return "splash"
    if "WAITING FOR" in text or "WAITING" in text:
        return "wait"
    if "LOAD/ERASE/RENAME FILES" in text or "SELECT FILE" in text:
        return "file_browser"
    if "SAVE A SEQUENCE" in text and "SELECT OPTION" in text:
        return "disk_menu"
    if "DISK" in text and "SELECT OPTION" in text:
        return "disk_menu"
    if "SQNC:" in text and "TMPO:" in text:
        return "main"
    return "unknown"


def observe(
    controller: BridgeMameController,
    decoder: Mpc60LcdDecoder,
    out_dir: Path,
    label: str,
    *,
    counter: list[int],
    verbose: bool = False,
) -> tuple[Path, list[str], str]:
    image = controller.snapshot_after(None, out_dir / f"{counter[0]:02d}-{label}.png")
    counter[0] += 1
    rows = read_lcd(decoder, image)
    screen = classify_screen(rows)
    if verbose:
        print(f"screen={screen} image={image}")
        print_rows(rows)
    return image, rows, screen


def wait_for_screen(
    controller: BridgeMameController,
    decoder: Mpc60LcdDecoder,
    out_dir: Path,
    wanted: set[str],
    *,
    counter: list[int],
    max_polls: int = 80,
    poll_seconds: float = 0.1,
    stable_polls: int = 1,
    verbose: bool = False,
) -> tuple[list[str], str]:
    last_rows: list[str] | None = None
    stable_count = 0
    for _ in range(max_polls):
        _, rows, screen = observe(
            controller,
            decoder,
            out_dir,
            "observe",
            counter=counter,
            verbose=verbose,
        )
        if rows == last_rows:
            stable_count += 1
        else:
            stable_count = 1
            last_rows = rows
        if screen in wanted and stable_count >= stable_polls:
            return rows, screen
        time.sleep(poll_seconds)
    raise TimeoutError(f"did not reach one of {sorted(wanted)}; last screen={screen}")


def wait_for_mpc60_boot_ready(
    controller: BridgeMameController,
    decoder: Mpc60LcdDecoder,
    out_dir: Path,
    *,
    counter: list[int],
    max_polls: int = 120,
    poll_seconds: float = 0.05,
    confirmation_samples: int = 2,
    verbose: bool = False,
) -> tuple[list[str], str]:
    first_seen_at: float | None = None
    for _ in range(max_polls):
        _, rows, screen = observe(
            controller,
            decoder,
            out_dir,
            "boot",
            counter=counter,
            verbose=verbose,
        )
        if first_seen_at is None and screen != "unknown":
            first_seen_at = time.perf_counter()
            print(f"boot_first_screen={screen}")
        if screen in {"disk_menu", "file_browser"}:
            return rows, screen
        if screen == "main":
            main_seen_at = time.perf_counter()
            confirmed_rows = rows
            confirmed = 0
            while confirmed < confirmation_samples:
                time.sleep(poll_seconds)
                _, candidate_rows, candidate_screen = observe(
                    controller,
                    decoder,
                    out_dir,
                    "boot-confirm",
                    counter=counter,
                    verbose=verbose,
                )
                if candidate_screen == "main":
                    confirmed_rows = candidate_rows
                    confirmed += 1
                    continue
                if candidate_screen != "unknown":
                    break
            if confirmed >= confirmation_samples:
                print(f"boot_ready_after_main_ms={(time.perf_counter() - main_seen_at) * 1000:.1f}")
                return confirmed_rows, "main"
        time.sleep(poll_seconds)
    raise TimeoutError("did not reach settled MPC60 main screen")


def observe_file_browser_blink_window(
    controller: BridgeMameController,
    decoder: Mpc60LcdDecoder,
    out_dir: Path,
    *,
    counter: list[int],
    samples: int = 8,
    poll_seconds: float = 0.08,
    verbose: bool = False,
) -> tuple[list[str], str, list[str]]:
    rows_variants: list[list[str]] = []
    selected_variants: list[str] = []
    for _ in range(samples):
        _, rows, screen = observe(
            controller,
            decoder,
            out_dir,
            "blink",
            counter=counter,
            verbose=verbose,
        )
        if screen != "file_browser":
            raise RuntimeError(f"expected file_browser while sampling blink window, got {screen}")
        rows_variants.append(rows)
        selected_variants.append(selected_file(rows))
        time.sleep(poll_seconds)
    visible = choose_visible_selected_file(selected_variants)
    best_rows = rows_variants[0]
    for rows in rows_variants:
        if selected_file(rows) == visible:
            best_rows = rows
            break
    print(f"selected_variants={selected_variants!r} visible={visible!r}")
    return best_rows, visible, selected_variants


def tap_and_wait(
    controller: BridgeMameController,
    decoder: Mpc60LcdDecoder,
    button: str,
    out_dir: Path,
    wanted: set[str],
    *,
    counter: list[int],
    max_polls: int = 80,
    verbose: bool = False,
) -> tuple[list[str], str]:
    print(f"tap={button}")
    controller.command("tap", button, timeout=10)
    return wait_for_screen(
        controller,
        decoder,
        out_dir,
        wanted,
        counter=counter,
        max_polls=max_polls,
        verbose=verbose,
    )


def find_file(args: argparse.Namespace) -> int:
    out_dir = Path(tempfile.mkdtemp(prefix="mpc60-find-file-"))
    bridge_dir = Path(tempfile.mkdtemp(prefix="mpc60-bridge-"))
    controller = BridgeMameController(
        hard_image=args.hard_image,
        bridge_dir=bridge_dir,
        visible=not args.headless,
    )
    print(f"snapshot_dir={out_dir}")
    print(f"bridge_dir={bridge_dir}")
    started_at = time.perf_counter()
    decoder = Mpc60LcdDecoder(hd61830_rom=HD61830_ROM)
    counter = [0]
    try:
        controller.start()
        print(f"bridge_ready_ms={(time.perf_counter() - started_at) * 1000:.1f}")
        rows, screen = wait_for_mpc60_boot_ready(
            controller,
            decoder,
            out_dir,
            counter=counter,
            max_polls=args.boot_polls,
            confirmation_samples=args.boot_confirmation_samples,
            verbose=args.verbose,
        )
        print(f"boot_ready_ms={(time.perf_counter() - started_at) * 1000:.1f}")

        if screen != "file_browser":
            if screen != "disk_menu":
                rows, screen = tap_and_wait(
                    controller,
                    decoder,
                    "Disk",
                    out_dir,
                    {"disk_menu", "file_browser"},
                    counter=counter,
                    max_polls=80,
                    verbose=args.verbose,
                )
            if screen != "file_browser":
                rows, screen = tap_and_wait(
                    controller,
                    decoder,
                    "6",
                    out_dir,
                    {"file_browser"},
                    counter=counter,
                    max_polls=80,
                    verbose=args.verbose,
                )

        previous = ""
        unchanged_count = 0
        for step in range(args.max_steps + 1):
            screen = classify_screen(rows)
            if screen != "file_browser":
                print(f"not in file browser at step {step}; screen={screen}")
                print_rows(rows)
                return 3
            rows, current, _ = observe_file_browser_blink_window(
                controller,
                decoder,
                out_dir,
                counter=counter,
                samples=args.blink_samples,
                poll_seconds=args.blink_poll_seconds,
                verbose=args.verbose,
            )
            comparable = comparable_file_name(current)
            print(f"step={step} selected={current!r}")
            if comparable == args.target.upper():
                print(f"found target {args.target} at step {step}")
                return 0
            if comparable == previous:
                unchanged_count += 1
            else:
                unchanged_count = 0
            if unchanged_count >= args.stall_limit:
                print(f"stalled on {current!r}")
                return 2
            previous = comparable
            if step == args.max_steps:
                break
            if args.advance_button:
                controller.command("tap", args.advance_button, timeout=10)
            else:
                controller.command("dial", str(args.direction), timeout=10)
            rows, screen = wait_for_screen(
                controller,
                decoder,
                out_dir,
                {"file_browser"},
                counter=counter,
                max_polls=20,
                verbose=args.verbose,
            )
        print(f"target {args.target} not found within {args.max_steps} steps")
        return 1
    finally:
        if args.exit:
            controller.clean_exit()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--hard-image", type=Path, default=Path("/tmp/mpc60scsi_10mb.img"))
    parser.add_argument("--headless", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    find_parser = subparsers.add_parser("find-file")
    find_parser.add_argument("target")
    find_parser.add_argument("--max-steps", type=int, default=40)
    find_parser.add_argument("--stall-limit", type=int, default=3)
    find_parser.add_argument("--direction", type=int, default=1)
    find_parser.add_argument("--advance-button", default="+")
    find_parser.add_argument("--boot-polls", type=int, default=120)
    find_parser.add_argument("--boot-confirmation-samples", type=int, default=2)
    find_parser.add_argument("--blink-samples", type=int, default=4)
    find_parser.add_argument("--blink-poll-seconds", type=float, default=0.08)
    find_parser.add_argument("--verbose", action="store_true")
    find_parser.add_argument("--exit", action="store_true")
    find_parser.set_defaults(func=find_file)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
