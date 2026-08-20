# Feidudu contributor instructions

- Keep the public pet ID and install filenames stable: `feidudu`, `pet.json`, and `spritesheet.webp`.
- `spriteVersionNumber: 2` is the Codex sprite protocol; it is not a project release number.
- Preserve Feidudu's identity: golden-yellow pear-shaped body, two long ears, cream oval belly, oversized reddish-brown oval nose, round eyes, exactly two short arms, two feet, and one thick curved tail. The default character has no clothes.
- The orange laptop appears only in `running` and `review`; its shape, color, scale, and screen orientation must remain consistent between those rows.
- Hearts are optional expression props and must not become part of the neutral silhouette.
- Directional running uses two complete 0.80-second gait cycles inside the shared 1.60-second clock. Approve the rightward anatomy first, then derive the leftward loop by framewise mirroring with phase order preserved.
- Preserve the 20-phase synchronized runtime, 15 named visual clips, and 16 unchanged gaze cells. Codex still has exactly nine native triggers; never describe the visual clips as new event types.
- Keep every figure fully inside its 192 × 208 cell with clean transparency, stable scale, stable foot baseline where appropriate, and no duplicate or missing limbs.
- Rebuild galleries with `python scripts/build_gallery.py` and `python scripts/build_readme_assets.py`, then run the README validation commands and unit tests before proposing asset changes.
- Visual-development materials may carry separate rights. Confirm authorization before publishing the full art archive, and never recreate platform watermarks in generated output.
- Do not commit caches, temporary Codex-home test installs, rejected generations, or files containing machine-specific absolute paths.
