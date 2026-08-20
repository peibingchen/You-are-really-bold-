#!/usr/bin/env python3
"""Build a compact contact sheet from Feidudu's nine source references."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "references" / "source-images"
OUTPUT = SOURCE_DIR / "reference-contact-sheet.jpg"
CARD_SIZE = (360, 640)
GAP = 18
HEADER = 54


def main() -> None:
    sources = sorted(SOURCE_DIR.glob("reference-??.jpg"))
    if len(sources) != 9:
        raise SystemExit(f"expected 9 references, found {len(sources)}")

    width = CARD_SIZE[0] * 3 + GAP * 4
    height = (CARD_SIZE[1] + HEADER) * 3 + GAP * 4
    sheet = Image.new("RGB", (width, height), "#252017")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=22)

    for index, source in enumerate(sources):
        with Image.open(source) as opened:
            card = ImageOps.fit(opened.convert("RGB"), CARD_SIZE, method=Image.Resampling.LANCZOS)
        column = index % 3
        row = index // 3
        left = GAP + column * (CARD_SIZE[0] + GAP)
        top = GAP + row * (CARD_SIZE[1] + HEADER + GAP)
        sheet.paste(card, (left, top + HEADER))
        draw.text((left + 8, top + 14), f"REFERENCE {index + 1:02d}", fill="#fff4c7", font=font)

    sheet.save(OUTPUT, quality=94, subsampling=0)
    print(OUTPUT)


if __name__ == "__main__":
    main()
