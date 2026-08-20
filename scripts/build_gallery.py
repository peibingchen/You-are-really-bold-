#!/usr/bin/env python3
"""Extract every shipped pet frame and rebuild the README galleries."""

from __future__ import annotations

import json
import shutil
from collections import OrderedDict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FRAMES_ROOT = ASSETS / "frames"
STATE_PHASES_ROOT = ASSETS / "state-phases"
GIF_ROOT = ASSETS / "gifs"
STATIC_ATLAS = ASSETS / "spritesheet-static.webp"
RUNTIME_ATLAS = ROOT / "pet" / "spritesheet.webp"

CELL_WIDTH = 192
CELL_HEIGHT = 208
ATLAS_SIZE = (1536, 2288)

WHITE = "#ffffff"
INK = "#432719"
ORANGE = "#f4a300"
GREEN = "#7d8b2f"
MUTED = "#8a6537"
RULE = "#f0dfad"

STATE_ROWS = OrderedDict(
    [
        ("running-right", (1, 8)),
        ("running-left", (2, 8)),
        ("waving", (3, 4)),
        ("jumping", (4, 5)),
        ("failed", (5, 8)),
        ("waiting", (6, 6)),
        ("running", (7, 6)),
        ("review", (8, 6)),
    ]
)

DURATIONS = {
    "running-right": [120, 120, 120, 120, 120, 120, 120, 220],
    "running-left": [120, 120, 120, 120, 120, 120, 120, 220],
    "waving": [140, 140, 140, 280],
    "jumping": [140, 140, 140, 140, 280],
    "failed": [140, 140, 140, 140, 140, 140, 140, 240],
    "waiting": [150, 150, 150, 150, 150, 260],
    "running": [120, 120, 120, 120, 120, 220],
    "review": [150, 150, 150, 150, 150, 280],
}

IDLE_LABELS = [
    "closed-mouth-rest",
    "breathing-lift",
    "blink",
    "mouth-open",
    "mouth-close",
    "wave-rest",
    "wave-quarter-lift",
    "wave-half-lift",
    "wave-apex-out",
    "wave-apex-center-1",
    "wave-apex-in",
    "wave-apex-center-2",
    "wave-apex-out-return",
    "wave-half-lower",
    "wave-rest-return",
    "neutral-return",
    "rest-loop",
    "breathing-loop",
    "rest-hold-1",
    "rest-hold-2",
]

LOOK_LABELS = [
    "000",
    "022.5",
    "045",
    "067.5",
    "090",
    "112.5",
    "135",
    "157.5",
    "180",
    "202.5",
    "225",
    "247.5",
    "270",
    "292.5",
    "315",
    "337.5",
]

DISPLAY_NAMES = OrderedDict(
    [
        ("idle", "Expressive idle"),
        ("running-right", "Run right"),
        ("running-left", "Run left"),
        ("waving", "Greeting"),
        ("jumping", "Jump"),
        ("failed", "Blocked"),
        ("waiting", "Needs input"),
        ("running", "Working"),
        ("review", "Ready / review"),
        ("look-directions", "16-direction gaze"),
    ]
)

ATLAS_ROW_LABELS = [
    "idle",
    "run right",
    "run left",
    "greeting",
    "jump",
    "blocked",
    "needs input",
    "working",
    "ready / review",
    "look 000–157.5",
    "look 180–337.5",
]

ATLAS_USED_COUNTS = [6, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8]


def font(size: int, *, bold: bool = False, style: str = "sans") -> ImageFont.ImageFont:
    if style == "display":
        candidates = [
            "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        ]
    elif style == "mono":
        candidates = [
            "/System/Library/Fonts/Menlo.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ]
    else:
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/HelveticaNeue.ttc",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def reset_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def clear_transparent_rgb(frame: Image.Image) -> Image.Image:
    """Zero hidden RGB so transparent source PNGs remain clean in every viewer."""
    rgba = frame.convert("RGBA")
    data = bytearray(rgba.tobytes())
    for index in range(0, len(data), 4):
        if data[index + 3] == 0:
            data[index : index + 3] = b"\x00\x00\x00"
    return Image.frombytes("RGBA", rgba.size, bytes(data))


def save_frames(
    name: str,
    frames: list[Image.Image],
    labels: list[str] | None = None,
    *,
    root: Path = FRAMES_ROOT,
) -> list[str]:
    output_dir = root / name
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    for index, frame in enumerate(frames):
        stem = labels[index] if labels else f"{index:02d}"
        output = output_dir / f"{stem}.png"
        clear_transparent_rgb(frame).save(output, optimize=True)
        outputs.append(output.relative_to(ROOT).as_posix())
    return outputs


def save_gif(name: str, frames: list[Image.Image], durations: list[int]) -> str:
    if len(frames) != len(durations):
        raise ValueError(f"{name}: {len(frames)} frames but {len(durations)} durations")
    output = GIF_ROOT / f"{name}.gif"
    preview_frames = [transparent_gif_frame(frame) for frame in frames]
    preview_frames[0].save(
        output,
        save_all=True,
        append_images=preview_frames[1:],
        duration=durations,
        loop=0,
        transparency=255,
        disposal=2,
        optimize=False,
    )
    return output.relative_to(ROOT).as_posix()


def transparent_gif_frame(frame: Image.Image, *, alpha_threshold: int = 64) -> Image.Image:
    """Quantize one RGBA frame while reserving palette index 255 for transparency."""
    rgba = frame.convert("RGBA")
    alpha = rgba.getchannel("A")
    paletted = rgba.convert("RGB").quantize(
        colors=255,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.FLOYDSTEINBERG,
    )
    transparent_mask = alpha.point(lambda value: 255 if value <= alpha_threshold else 0)
    paletted.paste(255, mask=transparent_mask)
    palette = paletted.getpalette() or []
    palette.extend([0] * (768 - len(palette)))
    palette[255 * 3 : 255 * 3 + 3] = [0, 0, 0]
    paletted.putpalette(palette[:768])
    paletted.info["transparency"] = 255
    return paletted


def extract_runtime_state_phases() -> tuple[OrderedDict[str, list[Image.Image]], list[int]]:
    phases: OrderedDict[str, list[Image.Image]] = OrderedDict(
        [("idle", [])] + [(name, []) for name in STATE_ROWS]
    )
    durations: list[int] = []
    with Image.open(RUNTIME_ATLAS) as runtime:
        if runtime.size != ATLAS_SIZE or not getattr(runtime, "is_animated", False):
            raise ValueError("runtime atlas must be an animated 1536x2288 WebP")
        for index in range(runtime.n_frames):
            runtime.seek(index)
            full = runtime.convert("RGBA")
            durations.append(int(runtime.info.get("duration", 100)))
            phases["idle"].append(full.crop((0, 0, CELL_WIDTH, CELL_HEIGHT)))
            for name, (row, _count) in STATE_ROWS.items():
                top = row * CELL_HEIGHT
                phases[name].append(full.crop((0, top, CELL_WIDTH, top + CELL_HEIGHT)))
    if len(durations) != len(IDLE_LABELS):
        raise ValueError(f"expected {len(IDLE_LABELS)} image-time phases, found {len(durations)}")
    return phases, durations


def extract_static_frames() -> tuple[dict[str, list[Image.Image]], list[Image.Image]]:
    with Image.open(STATIC_ATLAS) as opened:
        atlas = opened.convert("RGBA")
    if atlas.size != ATLAS_SIZE:
        raise ValueError(f"static atlas must be {ATLAS_SIZE[0]}x{ATLAS_SIZE[1]}")

    states: dict[str, list[Image.Image]] = {}
    for name, (row, count) in STATE_ROWS.items():
        states[name] = [
            atlas.crop(
                (
                    column * CELL_WIDTH,
                    row * CELL_HEIGHT,
                    (column + 1) * CELL_WIDTH,
                    (row + 1) * CELL_HEIGHT,
                )
            )
            for column in range(count)
        ]

    looks = []
    for row in (9, 10):
        for column in range(8):
            looks.append(
                atlas.crop(
                    (
                        column * CELL_WIDTH,
                        row * CELL_HEIGHT,
                        (column + 1) * CELL_WIDTH,
                        (row + 1) * CELL_HEIGHT,
                    )
                )
            )
    return states, looks


def flatten_on_white(frame: Image.Image) -> Image.Image:
    background = Image.new("RGBA", frame.size, "#ffffff")
    background.alpha_composite(frame.convert("RGBA"))
    return background.convert("RGB")


def frame_card(frame: Image.Image, size: tuple[int, int]) -> Image.Image:
    card = Image.new("RGBA", size, "#ffffff")
    thumb = frame.copy()
    thumb.thumbnail((size[0] - 8, size[1] - 8), Image.Resampling.LANCZOS)
    x = (size[0] - thumb.width) // 2
    y = size[1] - thumb.height - 4
    card.alpha_composite(thumb, (x, y))
    return card


def build_all_frames_gallery(groups: OrderedDict[str, list[Image.Image]]) -> None:
    width = 1920
    margin = 72
    header_height = 235
    row_height = 155
    frames_x = 370
    height = header_height + len(groups) * row_height + 55
    image = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(image)

    total_frames = sum(len(frames) for frames in groups.values())
    draw.rectangle((margin, 46, margin + 10, 137), fill=ORANGE)
    draw.rectangle((margin + 16, 46, margin + 26, 76), fill=GREEN)
    draw.text(
        (margin + 48, 45),
        "FEIDUDU / CHARACTER MOTION SYSTEM",
        fill=GREEN,
        font=font(16, bold=True, style="mono"),
    )
    draw.text(
        (margin + 44, 68),
        "MOTION ARCHIVE",
        fill=INK,
        font=font(72, style="display"),
    )

    count_text = f"{total_frames:02d}"
    count_font = font(76, style="display")
    count_box = draw.textbbox((0, 0), count_text, font=count_font)
    count_width = count_box[2] - count_box[0]
    count_x = width - margin - count_width
    draw.text((count_x, 46), count_text, fill=ORANGE, font=count_font)
    draw.text(
        (width - margin, 126),
        "RUNTIME POSES",
        fill=INK,
        font=font(14, bold=True, style="mono"),
        anchor="ra",
    )

    draw.line((margin, 164, width - margin, 164), fill=ORANGE, width=5)
    draw.text(
        (margin, 184),
        "VOL. 01   /   9 × 20 STATE PHASES   /   16 GAZE POSES",
        fill=MUTED,
        font=font(14, style="mono"),
    )
    draw.text(
        (width - margin, 184),
        "192 × 208 PX CELLS",
        fill=MUTED,
        font=font(14, style="mono"),
        anchor="ra",
    )

    for row_index, (name, frames) in enumerate(groups.items()):
        y = header_height + row_index * row_height
        draw.line((margin, y, width - margin, y), fill=RULE, width=2)
        draw.rectangle((margin, y + 31, margin + 4, y + 104), fill=ORANGE)
        draw.text(
            (margin + 18, y + 29),
            f"{row_index + 1:02d}",
            fill=ORANGE,
            font=font(29, style="display"),
        )
        draw.text(
            (margin + 78, y + 29),
            DISPLAY_NAMES[name],
            fill=INK,
            font=font(24, style="display"),
        )
        descriptor = "360° GAZE" if name == "look-directions" else "IMAGE-TIME LOOP"
        draw.text(
            (margin + 78, y + 68),
            f"{len(frames):02d} FRAMES  /  {descriptor}",
            fill=MUTED,
            font=font(12, style="mono"),
        )

        if len(frames) > 16:
            available = width - margin - frames_x
            slot_width = available / len(frames)
            frame_size = (66, 94)
            frame_y = y + 15
            index_y = y + 126
        elif len(frames) > 8:
            available = width - margin - frames_x
            slot_width = available / len(frames)
            frame_size = (84, 102)
            frame_y = y + 11
            index_y = y + 126
        else:
            slot_width = 151
            frame_size = (120, 130)
            frame_y = y + 1
            index_y = y + 132

        for index, frame in enumerate(frames):
            slot_x = frames_x + index * slot_width
            x = int(slot_x + (slot_width - frame_size[0]) / 2)
            card = frame_card(frame, frame_size).convert("RGB")
            image.paste(card, (x, frame_y))
            center_x = int(slot_x + slot_width / 2)
            draw.line((center_x, index_y - 9, center_x, index_y - 3), fill=GREEN, width=2)
            draw.text(
                (center_x, index_y),
                f"{index:02d}",
                fill=INK,
                font=font(11, style="mono"),
                anchor="ma",
            )

    footer_y = header_height + len(groups) * row_height
    draw.line((margin, footer_y, width - margin, footer_y), fill=ORANGE, width=3)
    draw.text(
        (margin, footer_y + 18),
        "FEIDUDU  /  SYNCHRONIZED IMAGE-TIME ARCHIVE",
        fill=GREEN,
        font=font(12, bold=True, style="mono"),
    )
    draw.text(
        (width - margin, footer_y + 18),
        "FRAME ORDER: LEFT → RIGHT",
        fill=MUTED,
        font=font(12, style="mono"),
        anchor="ra",
    )

    image.save(ASSETS / "all-frames.png", optimize=True)


def build_idle_timeline(frames: list[Image.Image], durations: list[int]) -> None:
    width = 1920
    height = 950
    margin = 72
    slot_width = (width - 2 * margin) / 10
    row_tops = [255, 585]
    image = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(image)

    total_duration = sum(durations)
    draw.rectangle((margin, 45, margin + 10, 137), fill=ORANGE)
    draw.rectangle((margin + 16, 45, margin + 26, 75), fill=GREEN)
    draw.text(
        (margin + 48, 44),
        "FEIDUDU / MOTION STUDY Nº 01",
        fill=GREEN,
        font=font(16, bold=True, style="mono"),
    )
    draw.text(
        (margin + 44, 70),
        "EXPRESSIVE IDLE",
        fill=INK,
        font=font(72, style="display"),
    )
    draw.text(
        (margin + 47, 151),
        "BREATH  /  BLINK  /  MOUTH  /  SOFT SETTLE  /  NEUTRAL RETURN",
        fill=MUTED,
        font=font(14, style="mono"),
    )

    duration_text = f"{total_duration / 1000:.2f} S"
    draw.text(
        (width - margin, 49),
        duration_text,
        fill=ORANGE,
        font=font(60, bold=True),
        anchor="ra",
    )
    draw.text(
        (width - margin, 125),
        "20 PHASES  /  SEAMLESS LOOP",
        fill=INK,
        font=font(14, bold=True, style="mono"),
        anchor="ra",
    )
    draw.line((margin, 195, width - margin, 195), fill=ORANGE, width=5)

    chapters = [
        (0, 4, "A / EXPRESSION"),
        (5, 9, "B / PAW LIFT"),
        (10, 14, "C / WAVE ARC"),
        (15, 19, "D / RETURN & REST"),
    ]
    for start, end, label in chapters:
        row = start // 10
        local_start = start % 10
        local_end = end % 10
        x1 = margin + local_start * slot_width
        x2 = margin + (local_end + 1) * slot_width - 18
        y = row_tops[row]
        draw.text((x1, y - 18), label, fill=GREEN, font=font(12, bold=True, style="mono"))
        draw.line((x1, y + 4, x2, y + 4), fill=GREEN, width=2)

    for index, frame in enumerate(frames):
        column = index % 10
        row = index // 10
        x_center = margin + column * slot_width + slot_width / 2
        y = row_tops[row]
        timeline_y = y + 36
        draw.line(
            (margin + column * slot_width, timeline_y, margin + (column + 1) * slot_width, timeline_y),
            fill=RULE,
            width=2,
        )
        draw.line((x_center, timeline_y - 7, x_center, timeline_y + 8), fill=ORANGE, width=3)
        draw.text(
            (x_center, timeline_y - 13),
            f"{index:02d}",
            fill=ORANGE,
            font=font(12, bold=True, style="mono"),
            anchor="ms",
        )

        frame_size = (138, 156)
        card = frame_card(frame, frame_size).convert("RGB")
        image.paste(card, (int(x_center - frame_size[0] / 2), timeline_y + 18))

        label = IDLE_LABELS[index].replace("-", " ").upper()
        draw.text(
            (x_center, y + 235),
            label,
            fill=INK,
            font=font(13, style="display"),
            anchor="ma",
        )
        draw.text(
            (x_center, y + 264),
            f"{durations[index]:03d} MS",
            fill=MUTED,
            font=font(11, style="mono"),
            anchor="ma",
        )

    draw.line((margin, 900, width - margin, 900), fill=ORANGE, width=3)
    draw.text(
        (margin, 919),
        "READ LEFT → RIGHT  /  ROW 01 CONTINUES INTO ROW 02",
        fill=GREEN,
        font=font(12, bold=True, style="mono"),
    )
    draw.text(
        (width - margin, 919),
        "TIMING SHOWN PER PHASE",
        fill=MUTED,
        font=font(12, style="mono"),
        anchor="ra",
    )
    image.save(ASSETS / "idle-frames.png", optimize=True)


def build_directional_gait_study(
    right_frames: list[Image.Image],
    left_frames: list[Image.Image],
    durations: list[int],
) -> None:
    if len(right_frames) != 20 or len(left_frames) != 20 or len(durations) != 20:
        raise ValueError("directional gait study requires two synchronized 20-phase loops")

    width = 1920
    height = 760
    margin = 72
    label_width = 260
    frames_x = margin + label_width
    frames_width = width - margin - frames_x
    slot_width = frames_width / 20
    row_tops = [265, 495]
    image = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(image)

    draw.rectangle((margin, 45, margin + 10, 137), fill=ORANGE)
    draw.rectangle((margin + 16, 45, margin + 26, 75), fill=GREEN)
    draw.text(
        (margin + 48, 44),
        "FEIDUDU / MOTION STUDY Nº 02",
        fill=GREEN,
        font=font(16, bold=True, style="mono"),
    )
    draw.text(
        (margin + 44, 70),
        "DIRECTIONAL GAIT",
        fill=INK,
        font=font(72, style="display"),
    )
    draw.text(
        (margin + 47, 151),
        "CONTACT  /  LOAD  /  PASS  /  FLIGHT  /  RETURN  /  TWO QUICK CADENCES",
        fill=MUTED,
        font=font(14, style="mono"),
    )
    draw.text(
        (width - margin, 49),
        "20 × 2",
        fill=ORANGE,
        font=font(60, bold=True),
        anchor="ra",
    )
    draw.text(
        (width - margin, 125),
        f"{durations[0]:03d} MS / PHASE  ·  2 × {sum(durations) / 2000:.2f} S GAITS",
        fill=INK,
        font=font(14, bold=True, style="mono"),
        anchor="ra",
    )
    draw.line((margin, 195, width - margin, 195), fill=ORANGE, width=5)

    chapters = (
        "GAIT A · OUT",
        "GAIT A · RETURN",
        "GAIT B · OUT",
        "GAIT B · RETURN",
    )
    for row_top in row_tops:
        for chapter_index, chapter in enumerate(chapters):
            start = frames_x + chapter_index * 5 * slot_width
            end = start + 5 * slot_width - 10
            draw.text(
                (start, row_top - 43),
                chapter,
                fill=GREEN,
                font=font(11, bold=True, style="mono"),
            )
            draw.line((start, row_top - 25, end, row_top - 25), fill=GREEN, width=2)

    rows = (
        ("RUN RIGHT", "SCREEN-RIGHT", right_frames, 1),
        ("RUN LEFT", "SCREEN-LEFT", left_frames, -1),
    )
    for row_index, (title, direction, frames, arrow_sign) in enumerate(rows):
        row_top = row_tops[row_index]
        draw.text(
            (margin, row_top + 17),
            title,
            fill=INK,
            font=font(34, style="display"),
        )
        draw.text(
            (margin, row_top + 58),
            direction,
            fill=MUTED,
            font=font(12, bold=True, style="mono"),
        )

        arrow_y = row_top + 104
        if arrow_sign > 0:
            draw.line((margin, arrow_y, margin + 160, arrow_y), fill=ORANGE, width=5)
            draw.polygon(
                [(margin + 160, arrow_y), (margin + 142, arrow_y - 11), (margin + 142, arrow_y + 11)],
                fill=ORANGE,
            )
        else:
            draw.line((margin, arrow_y, margin + 160, arrow_y), fill=ORANGE, width=5)
            draw.polygon(
                [(margin, arrow_y), (margin + 18, arrow_y - 11), (margin + 18, arrow_y + 11)],
                fill=ORANGE,
            )

        draw.line((frames_x, row_top + 140, width - margin, row_top + 140), fill=RULE, width=2)
        for index, frame in enumerate(frames):
            slot_left = frames_x + index * slot_width
            center_x = slot_left + slot_width / 2
            card = frame_card(frame, (70, 126)).convert("RGB")
            image.paste(card, (int(center_x - 35), row_top - 2))
            draw.line((center_x, row_top + 135, center_x, row_top + 147), fill=ORANGE, width=2)
            draw.text(
                (center_x, row_top + 155),
                f"{index:02d}",
                fill=INK,
                font=font(10, style="mono"),
                anchor="ma",
            )

    draw.line((margin, 704, width - margin, 704), fill=ORANGE, width=3)
    draw.text(
        (margin, 724),
        "20 PHASES  /  TWO 0.80 S GAITS  /  FRAMEWISE MIRROR",
        fill=GREEN,
        font=font(12, bold=True, style="mono"),
    )
    draw.text(
        (width - margin, 724),
        "EXACTLY TWO ARMS  ·  TWO LEGS  ·  ONE TAIL",
        fill=MUTED,
        font=font(12, style="mono"),
        anchor="ra",
    )
    image.save(ASSETS / "directional-gait.png", optimize=True)


def build_white_atlas_gallery() -> None:
    label_height = 22
    with Image.open(STATIC_ATLAS) as opened:
        atlas = opened.convert("RGBA")
    width = ATLAS_SIZE[0]
    height = len(ATLAS_ROW_LABELS) * (CELL_HEIGHT + label_height)
    sheet = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(sheet)
    label_font = font(12, bold=True)
    index_font = font(10)

    for row, label in enumerate(ATLAS_ROW_LABELS):
        y = row * (CELL_HEIGHT + label_height)
        draw.rectangle((0, y, width, y + label_height - 1), fill="#4c2a16")
        draw.text((7, y + 4), f"row {row} · {label}", fill="#ffffff", font=label_font)
        draw.text((width - 94, y + 4), f"{ATLAS_USED_COUNTS[row]} frames", fill="#ffffff", font=index_font)
        for column in range(8):
            cell = atlas.crop(
                (
                    column * CELL_WIDTH,
                    row * CELL_HEIGHT,
                    (column + 1) * CELL_WIDTH,
                    (row + 1) * CELL_HEIGHT,
                )
            )
            x = column * CELL_WIDTH
            white = flatten_on_white(cell)
            sheet.paste(white, (x, y + label_height))
            outline = "#e5c8a5" if column < ATLAS_USED_COUNTS[row] else "#eeeeee"
            draw.rectangle(
                (x, y + label_height, x + CELL_WIDTH - 1, y + label_height + CELL_HEIGHT - 1),
                outline=outline,
                width=1,
            )
            draw.text((x + 5, y + label_height + 4), f"{column:02d}", fill="#6a4a32", font=index_font)
    sheet.save(ASSETS / "sprite-atlas.png", optimize=True)


def build_white_look_gallery(look_frames: list[Image.Image]) -> None:
    label_height = 30
    width = 8 * CELL_WIDTH
    height = 3 * (CELL_HEIGHT + label_height)
    sheet = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(sheet)
    label_font = font(12, bold=True)

    with Image.open(STATIC_ATLAS) as opened:
        atlas = opened.convert("RGBA")
    neutral = atlas.crop((6 * CELL_WIDTH, 0, 7 * CELL_WIDTH, CELL_HEIGHT))
    sheet.paste(flatten_on_white(neutral), (0, label_height))
    draw.text((7, 7), "neutral", fill="#4c2a16", font=label_font)

    for index, frame in enumerate(look_frames):
        row = 1 + index // 8
        column = index % 8
        x = column * CELL_WIDTH
        y = row * (CELL_HEIGHT + label_height)
        draw.text((x + 7, y + 7), LOOK_LABELS[index], fill="#4c2a16", font=label_font)
        sheet.paste(flatten_on_white(frame), (x, y + label_height))
        draw.rectangle(
            (x, y + label_height, x + CELL_WIDTH - 1, y + label_height + CELL_HEIGHT - 1),
            outline="#ead8c2",
            width=1,
        )
    sheet.save(ASSETS / "look-directions.png", optimize=True)


def main() -> None:
    runtime_states, runtime_durations = extract_runtime_state_phases()
    states, look_frames = extract_static_frames()

    reset_directory(FRAMES_ROOT)
    reset_directory(STATE_PHASES_ROOT)
    reset_directory(GIF_ROOT)

    groups: OrderedDict[str, list[Image.Image]] = OrderedDict()
    groups.update(runtime_states)
    groups["look-directions"] = look_frames

    manifest: dict[str, object] = {
        "format": {
            "columns": 8,
            "rows": 11,
            "cell": [CELL_WIDTH, CELL_HEIGHT],
            "spriteVersionNumber": 2,
        },
        "animations": {},
    }

    idle_frames = runtime_states["idle"]
    idle_paths = save_frames("idle", idle_frames)
    idle_phase_paths = save_frames("idle", idle_frames, root=STATE_PHASES_ROOT)
    idle_gif = save_gif("idle", idle_frames, runtime_durations)
    phase_manifest = {
        "phases": [
            {
                "label": label,
                "image": f"frames/idle/{index:02d}.png",
                "duration_ms": runtime_durations[index],
            }
            for index, label in enumerate(IDLE_LABELS)
        ]
    }
    (ASSETS / "idle-phases.json").write_text(
        json.dumps(phase_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest["animations"]["idle"] = {
        "frames": idle_paths,
        "runtime_phases": idle_phase_paths,
        "gif": idle_gif,
        "durations_ms": runtime_durations,
        "labels": IDLE_LABELS,
    }

    for name, frames in states.items():
        frame_paths = save_frames(name, frames)
        runtime_frames = runtime_states[name]
        runtime_paths = save_frames(name, runtime_frames, root=STATE_PHASES_ROOT)
        gif_path = save_gif(name, runtime_frames, runtime_durations)
        manifest["animations"][name] = {
            "frames": frame_paths,
            "runtime_phases": runtime_paths,
            "gif": gif_path,
            "durations_ms": runtime_durations,
            "atlas_row": STATE_ROWS[name][0],
        }

    look_paths = save_frames("look-directions", look_frames, LOOK_LABELS)
    look_durations = [140] * 15 + [280]
    look_gif = save_gif("look-directions", look_frames, look_durations)
    manifest["animations"]["look-directions"] = {
        "frames": look_paths,
        "gif": look_gif,
        "durations_ms": look_durations,
        "directions": LOOK_LABELS,
        "atlas_rows": [9, 10],
    }

    (FRAMES_ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    build_all_frames_gallery(groups)
    build_idle_timeline(idle_frames, runtime_durations)
    build_directional_gait_study(
        runtime_states["running-right"],
        runtime_states["running-left"],
        runtime_durations,
    )
    build_white_atlas_gallery()
    build_white_look_gallery(look_frames)
    print(f"Wrote {sum(len(frames) for frames in groups.values())} frames and {len(groups)} GIFs under {ASSETS}")


if __name__ == "__main__":
    main()
