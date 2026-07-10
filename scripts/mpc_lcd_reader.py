#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import struct
import zlib
from pathlib import Path


CELL_WIDTH = 6
CELL_HEIGHT = 8


@dataclasses.dataclass(frozen=True)
class Glyph:
    codepoint: int
    atlas_x: int
    atlas_y: int
    width: int
    height: int
    xoffset: int
    yoffset: int
    xadvance: int


def paeth_predictor(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def unfilter_png_scanlines(raw: bytes, width: int, height: int, bpp: int) -> bytes:
    stride = width * bpp
    out = bytearray(height * stride)
    src = 0

    for row in range(height):
        filter_type = raw[src]
        src += 1
        row_start = row * stride
        prev_row_start = row_start - stride

        for col in range(stride):
            x = raw[src]
            src += 1
            left = out[row_start + col - bpp] if col >= bpp else 0
            up = out[prev_row_start + col] if row > 0 else 0
            up_left = out[prev_row_start + col - bpp] if row > 0 and col >= bpp else 0

            if filter_type == 0:
                value = x
            elif filter_type == 1:
                value = (x + left) & 0xFF
            elif filter_type == 2:
                value = (x + up) & 0xFF
            elif filter_type == 3:
                value = (x + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                value = (x + paeth_predictor(left, up, up_left)) & 0xFF
            else:
                raise ValueError(f"unsupported PNG filter type {filter_type}")

            out[row_start + col] = value

    return bytes(out)


def load_png_bw(path: Path) -> list[list[bool]]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG file")

    pos = 8
    width = 0
    height = 0
    bit_depth = 0
    color_type = 0
    palette: list[tuple[int, int, int, int]] | None = None
    idat = bytearray()

    while pos < len(data):
        length = struct.unpack_from(">I", data, pos)[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk_data = data[pos + 8 : pos + 8 + length]
        pos += 12 + length

        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, flt, interlace = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            if compression != 0 or flt != 0 or interlace != 0:
                raise ValueError("unsupported PNG compression/filter/interlace mode")
            if bit_depth != 8:
                raise ValueError(f"unsupported PNG bit depth {bit_depth}")
        elif chunk_type == b"PLTE":
            palette = []
            for i in range(0, len(chunk_data), 3):
                r, g, b = chunk_data[i : i + 3]
                palette.append((r, g, b, 255))
        elif chunk_type == b"tRNS":
            if palette is not None:
                updated = []
                for i, (r, g, b, _) in enumerate(palette):
                    alpha = chunk_data[i] if i < len(chunk_data) else 255
                    updated.append((r, g, b, alpha))
                palette = updated
        elif chunk_type == b"IDAT":
            idat.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    if channels is None:
        raise ValueError(f"unsupported PNG color type {color_type}")

    raw = zlib.decompress(bytes(idat))
    image = unfilter_png_scanlines(raw, width, height, channels)
    rows: list[list[bool]] = []

    for y in range(height):
        row: list[bool] = []
        offset = y * width * channels
        for x in range(width):
            base = offset + x * channels

            if color_type == 0:
                gray = image[base]
                alpha = 255
            elif color_type == 2:
                r, g, b = image[base : base + 3]
                gray = (299 * r + 587 * g + 114 * b) // 1000
                alpha = 255
            elif color_type == 3:
                if palette is None:
                    raise ValueError("indexed PNG without palette")
                index = image[base]
                r, g, b, alpha = palette[index]
                gray = (299 * r + 587 * g + 114 * b) // 1000
            elif color_type == 4:
                gray = image[base]
                alpha = image[base + 1]
            else:
                r, g, b, alpha = image[base : base + 4]
                gray = (299 * r + 587 * g + 114 * b) // 1000

            row.append(alpha >= 128 and gray < 200)
        rows.append(row)

    return rows


def load_bmp_bw(path: Path) -> list[list[bool]]:
    data = path.read_bytes()
    if data[:2] != b"BM":
        raise ValueError(f"{path} is not a BMP file")

    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    dib_size = struct.unpack_from("<I", data, 14)[0]
    if dib_size < 40:
        raise ValueError("unsupported BMP DIB header")

    width, height_signed, planes, bpp, compression = struct.unpack_from("<iiHHI", data, 18)
    if planes != 1 or compression != 0:
        raise ValueError("unsupported BMP planes/compression")
    if bpp not in (1, 4, 8, 24, 32):
        raise ValueError(f"unsupported BMP bit depth {bpp}")

    top_down = height_signed < 0
    height = abs(height_signed)

    palette: list[tuple[int, int, int]] = []
    if bpp <= 8:
        colors_used = struct.unpack_from("<I", data, 46)[0]
        palette_size = colors_used if colors_used else (1 << bpp)
        palette_offset = 14 + dib_size
        for i in range(palette_size):
            b, g, r, _ = struct.unpack_from("<BBBB", data, palette_offset + i * 4)
            palette.append((r, g, b))

    row_stride = ((width * bpp + 31) // 32) * 4
    rows: list[list[bool]] = []

    for logical_y in range(height):
        source_y = logical_y if top_down else (height - 1 - logical_y)
        row_data = data[pixel_offset + source_y * row_stride : pixel_offset + (source_y + 1) * row_stride]
        row: list[bool] = []

        if bpp == 1:
            for x in range(width):
                byte = row_data[x // 8]
                bit = 7 - (x % 8)
                index = (byte >> bit) & 1
                row.append(index == 0)
        elif bpp == 4:
            for x in range(width):
                byte = row_data[x // 2]
                index = (byte >> 4) & 0xF if x % 2 == 0 else byte & 0xF
                row.append(index == 0)
        elif bpp == 8:
            for x in range(width):
                index = row_data[x]
                row.append(index == 0)
        elif bpp == 24:
            for x in range(width):
                b, g, r = row_data[x * 3 : x * 3 + 3]
                gray = (299 * r + 587 * g + 114 * b) // 1000
                row.append(gray < 128)
        else:
            for x in range(width):
                b, g, r, a = row_data[x * 4 : x * 4 + 4]
                gray = (299 * r + 587 * g + 114 * b) // 1000
                row.append(a >= 128 and gray < 128)

        rows.append(row)

    return rows


def load_bw_image(path: Path) -> list[list[bool]]:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return load_png_bw(path)
    if suffix == ".bmp":
        return load_bmp_bw(path)
    raise ValueError(f"unsupported image type for {path}")


def parse_bmfont(path: Path) -> dict[int, Glyph]:
    data = path.read_bytes()
    if data[:4] != b"BMF\x03":
        raise ValueError(f"{path} is not a binary BMFont v3 file")

    pos = 4
    result: dict[int, Glyph] = {}
    while pos < len(data):
        block_id = data[pos]
        block_size = struct.unpack_from("<I", data, pos + 1)[0]
        body = data[pos + 5 : pos + 5 + block_size]

        if block_id == 4:
            for offset in range(0, block_size, 20):
                codepoint, x, y, width, height, xoffset, yoffset, xadvance, _, _ = (
                    struct.unpack_from("<IHHHHhhhBB", body, offset)
                )
                result[codepoint] = Glyph(
                    codepoint=codepoint,
                    atlas_x=x,
                    atlas_y=y,
                    width=width,
                    height=height,
                    xoffset=xoffset,
                    yoffset=yoffset,
                    xadvance=xadvance,
                )

        pos += 5 + block_size

    return result


def make_empty_matrix(height: int, width: int, value: bool = False) -> list[list[bool]]:
    return [[value for _ in range(width)] for _ in range(height)]


def build_templates(
    atlas_path: Path, glyphs: dict[int, Glyph], *, low: int = 32, high: int = 126
) -> dict[str, list[list[bool]]]:
    atlas = load_bw_image(atlas_path)
    templates: dict[str, list[list[bool]]] = {}

    for codepoint in range(low, high + 1):
        glyph = glyphs.get(codepoint)
        if glyph is None:
            continue

        cell = make_empty_matrix(CELL_HEIGHT, CELL_WIDTH)
        for y in range(glyph.height):
            for x in range(glyph.width):
                cx = glyph.xoffset + x
                cy = glyph.yoffset + y
                if 0 <= cx < CELL_WIDTH and 0 <= cy < CELL_HEIGHT:
                    cell[cy][cx] = atlas[glyph.atlas_y + y][glyph.atlas_x + x]

        templates[chr(codepoint)] = cell

    return templates


def render_ascii(bits: list[list[bool]]) -> str:
    return "\n".join("".join("#" if v else "." for v in row) for row in bits)


def invert_cell(cell: list[list[bool]]) -> list[list[bool]]:
    return [[not value for value in row] for row in cell]


def mismatch_count(a: list[list[bool]], b: list[list[bool]]) -> int:
    mismatches = 0
    for y in range(len(a)):
        for x in range(len(a[y])):
            if a[y][x] != b[y][x]:
                mismatches += 1
    return mismatches


def best_char_for_cell(
    cell: list[list[bool]], templates: dict[str, list[list[bool]]]
) -> tuple[str, int, bool]:
    best_char = "?"
    best_score = CELL_WIDTH * CELL_HEIGHT + 1
    best_inverted = False
    inverted = invert_cell(cell)

    for char, template in templates.items():
        score = mismatch_count(cell, template)
        if score < best_score:
            best_char = char
            best_score = score
            best_inverted = False

        inverted_score = mismatch_count(inverted, template)
        if inverted_score < best_score:
            best_char = char
            best_score = inverted_score
            best_inverted = True

    return best_char, best_score, best_inverted


def crop_cell(image_bits: list[list[bool]], x: int, y: int) -> list[list[bool]] | None:
    height = len(image_bits)
    width = len(image_bits[0]) if height else 0
    if y + CELL_HEIGHT > height or x + CELL_WIDTH > width:
        return None
    return [row[x : x + CELL_WIDTH] for row in image_bits[y : y + CELL_HEIGHT]]


def decode_line(
    image_bits: list[list[bool]],
    templates: dict[str, list[list[bool]]],
    *,
    x: int,
    y: int,
    cells: int,
) -> tuple[str, list[int], list[bool]]:
    chars: list[str] = []
    scores: list[int] = []
    inverted: list[bool] = []

    for i in range(cells):
        cell = crop_cell(image_bits, x + i * CELL_WIDTH, y)
        if cell is None:
            break
        char, score, is_inverted = best_char_for_cell(cell, templates)
        chars.append(char)
        scores.append(score)
        inverted.append(is_inverted)

    return "".join(chars), scores, inverted


def score_expected_text(
    image_bits: list[list[bool]],
    templates: dict[str, list[list[bool]]],
    *,
    x: int,
    y: int,
    text: str,
    invert: bool = False,
) -> int:
    total = 0
    for i, char in enumerate(text):
        cell = crop_cell(image_bits, x + i * CELL_WIDTH, y)
        if cell is None:
            return CELL_WIDTH * CELL_HEIGHT * len(text) + 1
        if invert:
            cell = invert_cell(cell)
        template = templates.get(char)
        if template is None:
            raise ValueError(f"missing template for character {char!r}")
        total += mismatch_count(cell, template)
    return total


def find_best_expected_text(
    image_bits: list[list[bool]],
    templates: dict[str, list[list[bool]]],
    *,
    text: str,
    x_from: int,
    x_to: int,
    y_from: int,
    y_to: int,
    invert: bool = False,
) -> tuple[int, int, int]:
    best: tuple[int, int, int] | None = None

    for y in range(y_from, y_to + 1):
        for x in range(x_from, x_to + 1):
            score = score_expected_text(
                image_bits, templates, x=x, y=y, text=text, invert=invert
            )
            item = (score, x, y)
            if best is None or item < best:
                best = item

    if best is None:
        raise ValueError("empty search range")
    return best


def auto_decode_screen(
    image_bits: list[list[bool]], templates: dict[str, list[list[bool]]], *, max_rows: int = 12
) -> list[tuple[float, int, int, int, str]]:
    height = len(image_bits)
    width = len(image_bits[0]) if height else 0
    results: list[tuple[float, int, int, int, str]] = []

    for row in range(0, height - CELL_HEIGHT + 1):
        for x_phase in range(CELL_WIDTH):
            cells = (width - x_phase) // CELL_WIDTH
            if cells <= 0:
                continue
            text, scores, _ = decode_line(
                image_bits, templates, x=x_phase, y=row, cells=cells
            )
            if not scores:
                continue
            trimmed = text.rstrip()
            if not trimmed:
                continue
            avg = float(sum(scores)) / (len(scores) * CELL_WIDTH * CELL_HEIGHT)
            results.append((avg, x_phase, row, cells, trimmed))

    results.sort(key=lambda item: item[0])
    return results[:max_rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--font-fnt", type=Path, required=True)
    parser.add_argument("--font-bmp", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--x", type=int)
    parser.add_argument("--y", type=int)
    parser.add_argument("--cells", type=int)
    parser.add_argument("--dump-cell", action="store_true")
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--expect")
    parser.add_argument("--invert", action="store_true")
    parser.add_argument("--search-x-from", type=int)
    parser.add_argument("--search-x-to", type=int)
    parser.add_argument("--search-y-from", type=int)
    parser.add_argument("--search-y-to", type=int)
    args = parser.parse_args()

    glyphs = parse_bmfont(args.font_fnt)
    templates = build_templates(args.font_bmp, glyphs)
    image_bits = load_bw_image(args.image)

    if args.auto:
        for avg, x_phase, row, cells, text in auto_decode_screen(image_bits, templates):
            print(f"score={avg:.4f} x={x_phase} y={row} cells={cells} text={text!r}")
        return

    if args.expect is not None:
        required = (
            args.search_x_from,
            args.search_x_to,
            args.search_y_from,
            args.search_y_to,
        )
        if any(value is None for value in required):
            parser.error(
                "--expect requires --search-x-from, --search-x-to, --search-y-from, and --search-y-to"
            )
        score, x, y = find_best_expected_text(
            image_bits,
            templates,
            text=args.expect,
            x_from=args.search_x_from,
            x_to=args.search_x_to,
            y_from=args.search_y_from,
            y_to=args.search_y_to,
            invert=args.invert,
        )
        print(f"score={score} x={x} y={y} text={args.expect!r} invert={args.invert}")
        return

    if args.x is None or args.y is None or args.cells is None:
        parser.error(
            "use --auto, or --expect with search ranges, or specify --x, --y, and --cells"
        )

    text, scores, inverted = decode_line(
        image_bits, templates, x=args.x, y=args.y, cells=args.cells
    )
    print(text)
    print("scores:", scores)
    print("inverted:", inverted)

    if args.dump_cell:
        for i in range(min(args.cells, 8)):
            cell = crop_cell(image_bits, args.x + i * CELL_WIDTH, args.y)
            if cell is None:
                break
            print(f"cell {i}")
            print(render_ascii(cell))


if __name__ == "__main__":
    main()
