#!/opt/homebrew/bin/python3
import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image

CELL_W = 6
CELL_H = 9
Cell = Tuple[Tuple[bool, ...], ...]
TemplateMap = Dict[str, Cell]


def load_bits(image_path: Path) -> List[List[bool]]:
    img = Image.open(image_path).convert('RGB')
    colors = img.getcolors(maxcolors=img.width * img.height)
    if not colors or len(colors) != 2:
        raise ValueError('expected exactly 2 colors in snapshot')
    fg = min((rgb for _count, rgb in colors), key=sum)
    px = img.load()
    return [[px[x, y] == fg for x in range(img.width)] for y in range(img.height)]


def crop_cell(bits: List[List[bool]], x: int, y: int) -> Cell:
    return tuple(
        tuple(bits[y + yy][x + xx] for xx in range(CELL_W))
        for yy in range(CELL_H)
    )


def invert_cell(cell: Cell) -> Cell:
    return tuple(tuple(not c for c in row) for row in cell)


def majority_template(cells: List[Cell]) -> Cell:
    rows = []
    for yy in range(CELL_H):
        row = []
        for xx in range(CELL_W):
            ones = sum(cell[yy][xx] for cell in cells)
            row.append(ones * 2 >= len(cells))
        rows.append(tuple(row))
    return tuple(rows)


def hamming(a: Cell, b: Cell) -> int:
    return sum(a[yy][xx] != b[yy][xx] for yy in range(CELL_H) for xx in range(CELL_W))


def learn_templates(bits: List[List[bool]], samples: List[dict]) -> TemplateMap:
    buckets: Dict[str, List[Cell]] = defaultdict(list)
    for sample in samples:
        x0 = sample['x']
        y0 = sample['y']
        inverted = sample.get('inverted', False)
        text = sample['text']
        for i, ch in enumerate(text):
            cell = crop_cell(bits, x0 + i * CELL_W, y0)
            if inverted:
                cell = invert_cell(cell)
            buckets[ch].append(cell)
    return {ch: majority_template(cells) for ch, cells in buckets.items()}


def render_text(text: str, inverted: bool, templates: TemplateMap) -> List[List[bool]]:
    rows: List[List[bool]] = []
    for yy in range(CELL_H):
        row: List[bool] = []
        for ch in text:
            template = templates[ch]
            row.extend((not value) if inverted else value for value in template[yy])
        rows.append(row)
    return rows


def crop_text(bits: List[List[bool]], x0: int, y0: int, length: int) -> List[List[bool]]:
    width = length * CELL_W
    return [[bits[y0 + yy][x0 + xx] for xx in range(width)] for yy in range(CELL_H)]


def hamming_matrix(a: List[List[bool]], b: List[List[bool]]) -> int:
    return sum(a[yy][xx] != b[yy][xx] for yy in range(len(a)) for xx in range(len(a[0])))


def coarse_decode(bits: List[List[bool]], x0: int, y0: int, length: int, inverted: bool, templates: TemplateMap) -> str:
    alphabet = sorted(templates)
    out = []
    for i in range(length):
        cell = crop_cell(bits, x0 + i * CELL_W, y0)
        if inverted:
            cell = invert_cell(cell)
        best = min(alphabet, key=lambda ch: hamming(cell, templates[ch]))
        out.append(best)
    return ''.join(out)


def decode_target(bits: List[List[bool]], target: dict, templates: TemplateMap) -> dict:
    x0 = target['x']
    y0 = target['y']
    inverted = target.get('inverted', False)
    length = target['length']
    actual = crop_text(bits, x0, y0, length)

    result = {
        'name': target['name'],
        'coarse': coarse_decode(bits, x0, y0, length, inverted, templates)
    }

    candidates = target.get('candidates')
    if candidates:
        scored = []
        for candidate in candidates:
            rendered = render_text(candidate, inverted, templates)
            scored.append({'candidate': candidate, 'score': hamming_matrix(actual, rendered)})
        scored.sort(key=lambda item: item['score'])
        result['best_candidate'] = scored[0]['candidate']
        result['candidate_scores'] = scored[: min(5, len(scored))]

    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('snapshot', type=Path)
    ap.add_argument('calibration', type=Path)
    args = ap.parse_args()

    bits = load_bits(args.snapshot)
    calibration = json.loads(args.calibration.read_text())
    templates = learn_templates(bits, calibration['samples'])

    result = {
        'snapshot': str(args.snapshot),
        'alphabet': ''.join(sorted(templates)),
        'decoded': [decode_target(bits, target, templates) for target in calibration['decode']]
    }
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
