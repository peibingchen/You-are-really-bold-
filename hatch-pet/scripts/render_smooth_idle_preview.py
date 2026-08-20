#!/usr/bin/env python3
"""Render the visible idle cell from every smooth-idle WebP time frame."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

CELL_WIDTH = 192
CELL_HEIGHT = 208


def load_idle_frames(path: Path) -> tuple[list[Image.Image], list[int]]:
    frames: list[Image.Image] = []
    durations: list[int] = []
    with Image.open(path) as opened:
        if opened.format != "WEBP" or not getattr(opened, "is_animated", False):
            raise ValueError("input must be an animated WebP atlas")
        for index in range(opened.n_frames):
            opened.seek(index)
            opened.load()
            durations.append(int(opened.info.get("duration", 0)))
            frames.append(opened.convert("RGBA").crop((0, 0, CELL_WIDTH, CELL_HEIGHT)))
    if not frames or any(duration <= 0 for duration in durations):
        raise ValueError("animated WebP must contain positive-duration frames")
    return frames, durations


def save_preview(frames: list[Image.Image], durations: list[int], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".webp":
        frames[0].save(
            output,
            format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            lossless=True,
            quality=100,
            method=6,
            exact=True,
        )
    elif output.suffix.lower() == ".gif":
        frames[0].save(
            output,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            disposal=2,
            optimize=False,
        )
    else:
        raise ValueError("preview output must end in .gif or .webp")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime_atlas")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    runtime_path = Path(args.runtime_atlas).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    frames, durations = load_idle_frames(runtime_path)
    save_preview(frames, durations, output_path)
    print(
        json.dumps(
            {
                "ok": True,
                "runtime_atlas": str(runtime_path),
                "output": str(output_path),
                "frame_count": len(frames),
                "durations_ms": durations,
                "loop_duration_ms": sum(durations),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
