#!/usr/bin/env python3
"""Build Feidudu README artwork from the checked-in transparent pet frames."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FRAMES = ASSETS / "frames"

INK = "#4b2c12"
BROWN = "#6f3a13"
GOLD = "#ffb80e"
CREAM = "#fff8df"


def font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Helvetica.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    height = max(1, size[1] - 1)
    for y in range(size[1]):
        t = y / height
        color = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
        draw.line((0, y, size[0], y), fill=color)
    return image


def load_frame(relative: str) -> Image.Image:
    return Image.open(ASSETS / relative).convert("RGBA")


def trimmed(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    box = alpha.getbbox()
    return image.crop(box) if box else image


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    subject = trimmed(image)
    subject.thumbnail(size, Image.Resampling.LANCZOS)
    return subject


def paste_with_shadow(canvas: Image.Image, subject: Image.Image, xy: tuple[int, int], blur: int = 18) -> None:
    x, y = xy
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    mask = subject.getchannel("A")
    shadow_shape = Image.new("RGBA", subject.size, (96, 49, 11, 105))
    shadow_shape.putalpha(mask.point(lambda value: round(value * 0.36)))
    shadow.alpha_composite(shadow_shape, (x + 13, y + 17))
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(subject, (x, y))


def build_avatar() -> None:
    source = fit(load_frame("frames/idle/00.png"), (410, 430))
    avatar = gradient((512, 512), (255, 252, 225), (255, 207, 77)).convert("RGBA")
    draw = ImageDraw.Draw(avatar)
    draw.ellipse((28, 28, 484, 484), fill="#fff8d9", outline="#f7b411", width=10)
    paste_with_shadow(avatar, source, ((512 - source.width) // 2, 54), blur=11)
    avatar.save(ASSETS / "avatar.png", optimize=True)


def build_teaser() -> None:
    width, height = 1600, 760
    canvas = gradient((width, height), (255, 251, 222), (255, 205, 69)).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    for x, y, radius, alpha in [(1350, 100, 300, 55), (165, 650, 270, 42), (850, 760, 430, 30)]:
        glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(255, 255, 255, alpha))
        canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(55)))

    run = fit(load_frame("frames/running-left/04.png"), (320, 385))
    hero = fit(load_frame("frames/idle/00.png"), (525, 620))
    work = fit(load_frame("frames/running/03.png"), (350, 405))
    paste_with_shadow(canvas, run, (45, height - run.height - 48), blur=20)
    paste_with_shadow(canvas, hero, ((width - hero.width) // 2, height - hero.height - 35), blur=25)
    paste_with_shadow(canvas, work, (width - work.width - 35, height - work.height - 48), blur=20)

    draw.rounded_rectangle((74, 60, 625, 222), radius=28, fill=(255, 255, 255, 216), outline="#f3c45d", width=3)
    draw.text((108, 84), "HATCHPET", fill=BROWN, font=font(25, bold=True))
    draw.text((106, 116), "FEIDUDU", fill=INK, font=font(68, bold=True))
    draw.text((109, 190), "A bright companion for Codex", fill="#835527", font=font(20))
    canvas.convert("RGB").save(ASSETS / "teaser.png", quality=95, optimize=True)


def build_motion_board() -> None:
    width, height = 1920, 830
    canvas = gradient((width, height), (255, 253, 236), (255, 229, 153)).convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    draw.text((80, 55), "FEIDUDU IN MOTION", fill=INK, font=font(60, bold=True))
    draw.text((83, 127), "NINE NATIVE STATES  /  20 SYNCHRONIZED PHASES  /  16-DIRECTION GAZE", fill="#80531f", font=font(18, bold=True))
    draw.line((80, 170, width - 80, 170), fill=GOLD, width=6)

    entries = [
        ("RUN", "frames/running-right/04.png"),
        ("JUMP", "frames/jumping/02.png"),
        ("HELLO", "frames/waving/02.png"),
        ("WORK", "frames/running/03.png"),
        ("WAIT", "frames/waiting/04.png"),
        ("REVIEW", "frames/review/04.png"),
    ]
    card_width = 270
    gap = 28
    start_x = (width - (len(entries) * card_width + (len(entries) - 1) * gap)) // 2
    for index, (label, relative) in enumerate(entries):
        x = start_x + index * (card_width + gap)
        y = 215
        draw.rounded_rectangle((x, y, x + card_width, 720), radius=30, fill=(255, 255, 255, 229), outline="#f0cc7a", width=3)
        frame = fit(load_frame(relative), (235, 390))
        paste_with_shadow(canvas, frame, (x + (card_width - frame.width) // 2, y + 52), blur=12)
        draw.text((x + card_width // 2, 651), label, fill=INK, font=font(24, bold=True), anchor="mm")
        draw.text((x + card_width // 2, 688), f"STATE {index + 1:02d}", fill="#996923", font=font(13, bold=True), anchor="mm")

    draw.text((width - 80, 775), "192 × 208 CELLS  /  CODEX SPRITE V2", fill=BROWN, font=font(16, bold=True), anchor="ra")
    canvas.convert("RGB").save(ASSETS / "feidudu-in-motion.png", quality=95, optimize=True)


def main() -> None:
    build_avatar()
    build_teaser()
    build_motion_board()
    print("Built avatar.png, teaser.png, and feidudu-in-motion.png")


if __name__ == "__main__":
    main()
