#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import time
from pathlib import Path


REPO = Path("/Users/izmar/git/codex-mame")
CONTROLLER = REPO / "scripts" / "mpc3000_live_controller.py"


def load_controller_module():
    spec = importlib.util.spec_from_file_location("mpc3000_live_controller", CONTROLLER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {CONTROLLER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BridgeClient:
    def __init__(self, bridge_dir: Path):
        self.bridge_dir = bridge_dir
        self.command_path = bridge_dir / "command.txt"
        self.response_path = bridge_dir / "response.txt"
        self.command_id = int(time.time() * 1000) % 1000000

    def command(self, command: str, arg: str = "", *, timeout: float = 20) -> str:
        self.command_id += 1
        command_id = str(self.command_id)
        tmp = self.bridge_dir / "command.tmp"
        tmp.write_text(f"{command_id}|{command}|{arg}\n")
        tmp.replace(self.command_path)

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.response_path.exists():
                response = self.response_path.read_text().strip()
                parts = response.split("|", 2)
                if parts and parts[0] == command_id:
                    if len(parts) >= 2 and parts[1] == "ok":
                        return response
                    raise RuntimeError(f"bridge command failed: {response}")
            time.sleep(0.02)
        raise TimeoutError(f"timed out waiting for {command_id}|{command}")


def print_rows(rows: list[str]) -> None:
    for row in rows:
        print(row)


def merge_row_variants(rows_variants: list[list[str]]) -> list[str]:
    if not rows_variants:
        return []
    merged: list[str] = []
    row_count = max(len(rows) for rows in rows_variants)
    for row_idx in range(row_count):
        variants = [rows[row_idx] if row_idx < len(rows) else "" for rows in rows_variants]
        width = max(len(v) for v in variants)
        chars: list[str] = []
        for col in range(width):
            candidates = [v[col] if col < len(v) else " " for v in variants]
            non_blank = [c for c in candidates if c not in {" ", "_", "?"}]
            if non_blank:
                counts: dict[str, int] = {}
                for c in non_blank:
                    counts[c] = counts.get(c, 0) + 1
                chars.append(sorted(counts.items(), key=lambda kv: (kv[1], kv[0]))[-1][0])
                continue
            non_space = [c for c in candidates if c != " "]
            if non_space:
                counts = {}
                for c in non_space:
                    counts[c] = counts.get(c, 0) + 1
                chars.append(sorted(counts.items(), key=lambda kv: (kv[1], kv[0]))[-1][0])
            else:
                chars.append(" ")
        merged.append("".join(chars).rstrip())
    return merged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bridge_dir", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    tap_parser = subparsers.add_parser("tap")
    tap_parser.add_argument("button")

    dial_parser = subparsers.add_parser("dial")
    dial_parser.add_argument("delta", type=int)

    snap_parser = subparsers.add_parser("snap")
    snap_parser.add_argument("path", type=Path)

    observe_parser = subparsers.add_parser("observe")
    observe_parser.add_argument("path", type=Path)

    subparsers.add_parser("exit")

    args = parser.parse_args()
    client = BridgeClient(args.bridge_dir)

    if args.command == "tap":
        print(client.command("tap", args.button))
        return 0
    if args.command == "dial":
        print(client.command("dial", str(args.delta)))
        return 0
    if args.command == "snap":
        print(client.command("snap", str(args.path)))
        return 0
    if args.command == "observe":
        module = load_controller_module()
        decoder = module.Hd61830LcdDecoder(hd61830_rom=module.HD61830_ROM)
        rows_variants: list[list[str]] = []
        for idx in range(6):
            sample_path = args.path if idx == 0 else args.path.with_name(f"{args.path.stem}-{idx}{args.path.suffix}")
            print(client.command("snap", str(sample_path)))
            rows_variants.append(decoder.read_rows(sample_path))
            time.sleep(0.08)
        rows = merge_row_variants(rows_variants)
        print(f"screen={module.classify_screen(rows)}")
        print_rows(rows)
        return 0
    if args.command == "exit":
        print(client.command("exit", ""))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
