#!/usr/bin/env python3
"""Render animated previews and numbered phase sheets for native pet states."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from package_smooth_idle_webp import CELL_HEIGHT, CELL_WIDTH, decoded_frames
from package_smooth_state_webp import STATE_SPECS
from render_smooth_idle_preview import save_preview


def parse_states(raw: str) -> list[str]:
    if raw.strip().lower() == "all":
        return list(STATE_SPECS)
    states = [value.strip() for value in raw.split(",") if value.strip()]
    unknown = sorted(set(states) - set(STATE_SPECS))
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown native state(s): {', '.join(unknown)}")
    return states


def state_cells(frames: list[Image.Image], state: str) -> list[Image.Image]:
    row, _columns = STATE_SPECS[state]
    top = row * CELL_HEIGHT
    return [frame.crop((0, top, CELL_WIDTH, top + CELL_HEIGHT)) for frame in frames]


def save_phase_sheet(cells: list[Image.Image], output: Path, columns: int = 5) -> None:
    label_height = 22
    rows = math.ceil(len(cells) / columns)
    sheet = Image.new(
        "RGB",
        (columns * CELL_WIDTH, rows * (CELL_HEIGHT + label_height)),
        "#ffffff",
    )
    draw = ImageDraw.Draw(sheet)
    for index, cell in enumerate(cells):
        column = index % columns
        row = index // columns
        x = column * CELL_WIDTH
        y = row * (CELL_HEIGHT + label_height)
        draw.rectangle((x, y, x + CELL_WIDTH - 1, y + label_height - 1), fill="#4c2a16")
        draw.text((x + 6, y + 4), f"phase {index:02d}", fill="#ffffff")
        white = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), "#ffffff")
        white.alpha_composite(cell.convert("RGBA"))
        sheet.paste(white.convert("RGB"), (x, y + label_height))
        draw.rectangle(
            (x, y + label_height, x + CELL_WIDTH - 1, y + label_height + CELL_HEIGHT - 1),
            outline="#ead8c2",
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime_atlas")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--states", type=parse_states, default=list(STATE_SPECS))
    parser.add_argument("--json-out")
    args = parser.parse_args()

    runtime_path = Path(args.runtime_atlas).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    frames, durations, loop = decoded_frames(runtime_path)
    if not frames or any(duration <= 0 for duration in durations):
        parser.error("runtime atlas must be an animated WebP with positive durations")

    outputs: dict[str, dict[str, str]] = {}
    for state in args.states:
        cells = state_cells(frames, state)
        animation = output_dir / f"{state}.webp"
        sheet = output_dir / f"{state}-phases.png"
        save_preview(cells, durations, animation)
        save_phase_sheet(cells, sheet)
        outputs[state] = {"animation": str(animation), "phase_sheet": str(sheet)}

    result = {
        "ok": True,
        "runtime_atlas": str(runtime_path),
        "frame_count": len(frames),
        "durations_ms": durations,
        "loop_duration_ms": sum(durations),
        "loop": loop,
        "states": outputs,
    }
    if args.json_out:
        Path(args.json_out).expanduser().resolve().write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
