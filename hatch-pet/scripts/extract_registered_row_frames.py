#!/usr/bin/env python3
"""Split one already-registered 8-cell hatch-pet row without recentering it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

CELL_WIDTH = 192
CELL_HEIGHT = 208
FRAME_COUNT = 8
ROW_SIZE = (CELL_WIDTH * FRAME_COUNT, CELL_HEIGHT)


def extract_registered_frames(row_path: Path) -> list[Image.Image]:
    with Image.open(row_path) as opened:
        row = opened.convert("RGBA")
    if row.size != ROW_SIZE:
        raise ValueError(
            f"registered row must be {ROW_SIZE[0]}x{ROW_SIZE[1]}, got {row.width}x{row.height}"
        )
    frames = [
        row.crop(
            (
                index * CELL_WIDTH,
                0,
                (index + 1) * CELL_WIDTH,
                CELL_HEIGHT,
            )
        )
        for index in range(FRAME_COUNT)
    ]
    for index, frame in enumerate(frames):
        if frame.getchannel("A").getbbox() is None:
            raise ValueError(f"registered frame {index} is empty")
    return frames


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registered_row")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json-out")
    args = parser.parse_args()

    row_path = Path(args.registered_row).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    frames = extract_registered_frames(row_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    for index, frame in enumerate(frames):
        output = output_dir / f"{index:02d}.png"
        frame.save(output)
        outputs.append(str(output))

    result = {
        "ok": True,
        "registered_row": str(row_path),
        "output_dir": str(output_dir),
        "frame_count": len(outputs),
        "frames": outputs,
        "recentered": False,
    }
    if args.json_out:
        Path(args.json_out).expanduser().resolve().write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
