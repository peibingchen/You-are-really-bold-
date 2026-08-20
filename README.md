<p align="center">
  <img src="assets/teaser.png" alt="HatchPet Feidudu, a bright golden desktop companion for Codex" width="100%">
</p>

<p align="center">
  <strong>A cheerful golden companion that reacts while Codex works.</strong><br>
  <a href="README.zh-CN.md">简体中文</a> · <a href="操作手册与说明.md">中文 operation manual</a>
</p>
# HatchPet: Feidudu

> Hint: For ideas and source code, please refer to the project https://github.com/srwang0506/HatchPet-CapybaraLulu.git

Feidudu (肥嘟嘟) is a custom desktop-pet pack built with the same Codex Sprite V2 workflow as the source HatchPet project. The character is derived from the nine supplied visual references: a golden-yellow, pear-shaped, long-eared creature with a cream belly, a large reddish-brown nose, round eyes, two short arms, two feet, and one curved tail.

The installable pack lives in [`pet/`](pet/). It contains a small manifest and one animated WebP atlas; no runtime service, network request, or third-party executable is required.

<p align="center">
  <img src="assets/feidudu-in-motion.png" alt="Feidudu running, jumping, greeting, working, waiting, and reviewing" width="100%">
</p>

## Highlights

- Nine native Codex states: idle, run right, run left, greeting, jump, blocked, needs input, working, and ready for review.
- Twenty synchronized image-time phases at 80 ms each, producing a seamless 1.60-second global loop.
- Fifteen authored visual clips distributed across the native states.
- Sixteen gaze directions arranged over the two Sprite V2 look rows.
- Transparent 192 × 208 cells in an 8 × 11, 1536 × 2288 atlas.
- A static RGBA fallback atlas for reduced-motion use and easy visual debugging.
- Complete source rows, extracted frames, previews, validation reports, and build scripts.

## Quick start

### Requirements

- Windows, macOS, or Linux
- Python 3.10 or newer
- A ChatGPT/Codex client that exposes custom desktop pets

Pillow is only needed for rebuilding or validating artwork:

```bash
python -m pip install -r requirements.txt
```

### Install

From the project root:

```bash
python scripts/install.py
```

On systems where Python 3 is named `python3`:

```bash
python3 scripts/install.py
```

The installer:

1. verifies the Feidudu Sprite V2 manifest;
2. backs up any existing `feidudu` installation under `~/.codex/backups/feidudu/`;
3. copies the pack to `~/.codex/pets/feidudu/`; and
4. sets `[desktop].selected-avatar-id` to `custom:feidudu` unless `--no-select` is supplied.

Fully quit and reopen the desktop app, then open **Settings → Pets** and select **肥嘟嘟** if it is not already active.

To install without changing the current selection:

```bash
python scripts/install.py --no-select
```

To test installation without touching the real Codex home:

```bash
python scripts/install.py --codex-home .tmp-codex
```

## State behavior

| Atlas row | Native state | Feidudu behavior |
|---:|---|---|
| 0 | `idle` | Breathes, blinks, changes mouth shape, and softly settles |
| 1 | `running-right` | Two complete rightward gait cycles |
| 2 | `running-left` | Framewise mirrored leftward gait with matching phase order |
| 3 | `waving` | Raises one paw and greets the user |
| 4 | `jumping` | Compresses, rises, reaches the apex, and lands |
| 5 | `failed` | Reacts to a blocked or failed task |
| 6 | `waiting` | Asks for attention while waiting for input |
| 7 | `running` | Works at a consistent orange laptop |
| 8 | `review` | Pauses at the same laptop for review |
| 9–10 | pointer gaze | Covers 000° through 337.5° in 22.5° steps |

All nine native state rows share one animated-WebP clock. Entering a state does not reset that clock, so every state sequence is authored as a valid periodic loop. The two look rows are identical in every image-time frame so pointer tracking remains stable.

## Motion archive

<p align="center">
  <img src="assets/all-frames.png" alt="Feidudu complete synchronized motion archive" width="100%">
</p>

Individual transparent frames are in [`assets/frames/`](assets/frames/), synchronized runtime phases in [`assets/state-phases/`](assets/state-phases/), and lightweight animation previews in [`assets/gifs/`](assets/gifs/).

The source references and generated working rows are retained under [`references/source-images/`](references/source-images/) and [`assets/source/`](assets/source/) so future changes can be reviewed against the same character contract. The accepted built-in image-generation prompt set is recorded in [`references/IMAGEGEN-PROMPTS.md`](references/IMAGEGEN-PROMPTS.md).

## Sprite V2 contract

| Property | Value |
|---|---:|
| Columns | 8 |
| Rows | 11 |
| Cell size | 192 × 208 px |
| Atlas size | 1536 × 2288 px |
| Runtime frames | 20 |
| Frame duration | 80 ms |
| Loop duration | 1600 ms |
| Sprite version | 2 |

The shipped runtime atlas is [`pet/spritesheet.webp`](pet/spritesheet.webp). The static fallback is [`assets/spritesheet-static.webp`](assets/spritesheet-static.webp). [`assets/state-phases.json`](assets/state-phases.json) is the exact phase-to-cell source map used to package the runtime file.

## Reduced-motion fallback

The static atlas has the same 8 × 11 geometry and can replace the animated atlas without changing `pet.json`:

```bash
cp assets/spritesheet-static.webp ~/.codex/pets/feidudu/spritesheet.webp
```

PowerShell:

```powershell
Copy-Item assets\spritesheet-static.webp "$HOME\.codex\pets\feidudu\spritesheet.webp" -Force
```

Restart the client after replacing the file. Run the installer again to restore the animated version.

## Rebuild and validation

The repository keeps the original generic `hatch-pet` tooling plus Feidudu-specific normalization helpers.

Rebuild documentation galleries from the checked-in static and runtime atlases:

```bash
python scripts/build_gallery.py
python scripts/build_readme_assets.py
```

Validate the static atlas:

```bash
python hatch-pet/scripts/validate_atlas.py assets/spritesheet-static.webp \
  --json-out assets/validation-static-feidudu.json --require-v2
```

Validate the animated runtime atlas and its exact phase map:

```bash
python hatch-pet/scripts/validate_atlas.py pet/spritesheet.webp \
  --json-out assets/validation-runtime-feidudu.json \
  --require-v2 --allow-animated --allow-transparent-rgb-residue

python hatch-pet/scripts/validate_smooth_state_webp.py pet/spritesheet.webp \
  --source-atlas assets/spritesheet-static.webp \
  --phase-manifest assets/state-phases.json \
  --json-out assets/validation-smooth-feidudu.json \
  --require-all-states --min-motion-clips 12 --max-motion-clips 15
```

Run the generic tooling tests:

```bash
python -m unittest discover -s hatch-pet/tests -v
```

## Project layout

```text
HatchPet-Feidudu-main/
├── pet/                         # ready-to-install Feidudu pack
│   ├── pet.json
│   └── spritesheet.webp
├── assets/
│   ├── source/                  # generated chroma-key rows and canonical art
│   ├── frames/                  # transparent static source frames
│   ├── state-phases/            # 20 extracted runtime phases per state
│   ├── gifs/                    # lightweight state previews
│   ├── runtime-previews/        # phase sheets and animated WebP previews
│   ├── spritesheet-static.webp  # reduced-motion/debug atlas
│   └── state-phases.json        # runtime phase mapping
├── references/source-images/    # nine supplied references + contact sheet
├── hatch-pet/                   # reusable Sprite V2 build and QA tools
├── scripts/                     # Feidudu build, gallery, and install helpers
├── README.md                    # English project README
├── README.zh-CN.md              # Chinese translation
└── 操作手册与说明.md              # detailed Chinese user manual
```

## Character and contribution rules

Keep Feidudu's defining silhouette and anatomy stable: golden pear-shaped body, two long ears, cream oval belly, oversized reddish-brown oval nose, round eyes, exactly two arms, two feet, and one curved tail. The default character has no clothing. The orange laptop belongs only to the working and review states; hearts are optional expression props, not part of the base identity.

See [`AGENTS.md`](AGENTS.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md) before changing motion or packaging.

## Reference and distribution note

The nine supplied images are retained as design references and may carry third-party platform marks or authorship information. The generated pet assets intentionally omit those marks. Confirm that you have the necessary rights before redistributing either the reference files or derivative artwork. See [`NOTICE`](NOTICE) for repository notices.

## License

Project code is provided under the license in [`LICENSE`](LICENSE). Artwork and supplied references may be subject to separate rights; review [`NOTICE`](NOTICE) before redistribution.
