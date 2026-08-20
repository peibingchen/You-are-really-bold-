# Desktop Smooth Idle Runtime

Use this opt-in path when a user explicitly reports slideshow-like desktop idle playback, long frozen holds, a choppy blink, or asks for higher-frequency idle motion without modifying the Codex application.

If the user also requests high-phase non-idle task motion or a 12-15 visual-motion library, use `desktop-smooth-state.md` instead of layering two animated wrappers. The smooth-state path includes idle and all eight non-idle native rows on one shared WebP clock.

## Runtime model

The desktop renderer selects the six idle atlas columns slowly. A smooth-idle runtime atlas moves approved idle phases into the animated WebP time axis. The default plan uses the existing six-pose idle loop:

- WebP animation frame 0 copies approved idle pose 0 into idle columns 0-5.
- WebP animation frame 1 copies approved idle pose 1 into idle columns 0-5.
- Continue through approved idle pose 5.
- Use durations `280,110,110,140,140,320` ms, totaling 1100 ms.
- Preserve the v2 neutral-look cell in row 0 column 6 unchanged.
- Keep row 0 column 7 transparent.
- Keep rows 1-10 render-identical to the approved static v2 source in every WebP frame: alpha and every visible RGB pixel must match exactly. Ignore codec-normalized hidden RGB only where alpha is zero.

Because all six renderer-selectable idle columns show the same phase at a given WebP time, the renderer's slow column changes do not cause a visible hold or phase jump. The image clock supplies the approved idle cadence. This is deterministic runtime packaging, not visual generation and not a substitute for any missing `$imagegen` row.

When the user explicitly requests an expressive idle, a phase manifest may replace the fixed six-pose timing with approved `192x208` pose images or populated static-atlas cells. Generate any new mouth-opening, tiny wave, ear twitch, or similar pose through `$imagegen`, normalize and visually approve it first, and include transition poses back to neutral. Keep the separate standard `waving` row intact because the desktop still owns its state semantics.

For a one-limb wave, define the moving limb in viewer coordinates before generation and keep the opposite limb in the same side-rest pose throughout the complete gesture. Inspect every source cell and reject limb switching, alternating hands, an opposite limb that rises or moves to the chest, or a moving limb that detaches or changes shoulders. Use at least one lift pose, three neighboring apex angles, one lower pose, and the neutral return. A two-position up/down toggle is not a wave and fails expressive-idle QA.

When an expressive eight-pose strip widens on only one side, do not center each silhouette independently; that makes the torso and fixed limb slide in the opposite direction. Register the row against the approved neutral cell with the lower-body anchor path in `assemble_extended_atlas.py`, then split `qa/expressive-idle-registered.png` with `extract_registered_row_frames.py`. The extractor performs exact `192x208` cell crops and never recenters them. Visually require the feet, torso, and declared fixed limb to stay anchored while the moving limb changes.

## Original-speed task-state repetition

The desktop renderer normally plays a non-idle row three times and then falls back to idle even when the underlying working, waiting, review, failure, hover, greeting, or drag state is still active. When the user explicitly asks for those actions to remain visible longer without slowing them down, use `scripts/patch_codex_pet_playback.mjs` as a separate opt-in renderer patch.

The patch changes playback semantics, not artwork or speed:

- each selected non-idle row keeps its original per-frame durations;
- the row loops from its first frame while the corresponding desktop state remains active;
- an actual state change still switches immediately to the new row;
- the idle JavaScript multiplier is restored to `1`, while animated-WebP idle phases continue on their own validated image clock;
- the patch verifies the renderer asset, ASAR block hashes, and Electron ASAR header hash before and after writing;
- the original `app.asar` and `Info.plist` are copied to a timestamped backup before mutation.

This patch is currently macOS-specific because it targets `/Applications/ChatGPT.app`. Fully quit and reopen ChatGPT after applying it. A ChatGPT application update may replace the patched renderer; rerun `--check` after every update and apply again only when integrity checks pass.

```bash
"$NODE" "$SKILL_DIR/scripts/patch_codex_pet_playback.mjs" \
  --check /Applications/ChatGPT.app

"$NODE" "$SKILL_DIR/scripts/patch_codex_pet_playback.mjs" \
  --apply /Applications/ChatGPT.app
```

The apply result includes `backupDir`. Restore that exact backup when needed:

```bash
"$NODE" "$SKILL_DIR/scripts/patch_codex_pet_playback.mjs" \
  --restore /Applications/ChatGPT.app \
  --backup /absolute/path/from/backupDir
```

Require `multiplier: 1`, `nonIdleStatesPersistent: true`, `assetHashMatches: true`, `blockHashesMatch: true`, and `headerHashMatches: true` in the post-apply report. Refuse the patch if the current application build no longer has the expected renderer structure or fails any preflight integrity check.

## Preconditions

- Complete all normal v2 generation and QA first.
- Keep the approved static v2 atlas as the visual and structural source of truth.
- Require its idle preview to pass at the original six durations.
- Use this path only for WebP output and only after explicit user demand for desktop smoothness.
- Use a custom phase manifest only after every external pose is visually approved at pet size, identity-stable, baseline-stable, and free of clipping or detached effects.
- Install under a new pet id or fully quit and reopen Codex; the desktop custom-pet list is process-cached.

## Package and validate

```bash
"$PYTHON" "$SKILL_DIR/scripts/package_smooth_idle_webp.py" \
  --source-atlas "$RUN_DIR/final/spritesheet-extended.webp" \
  --output "$RUN_DIR/final/spritesheet-runtime.webp" \
  --json-out "$RUN_DIR/qa/smooth-idle-package.json"
```

Run ordinary structural validation on runtime frame 0, explicitly acknowledging animation:

```bash
"$PYTHON" "$SKILL_DIR/scripts/validate_atlas.py" \
  "$RUN_DIR/final/spritesheet-runtime.webp" \
  --json-out "$RUN_DIR/qa/smooth-idle-frame-0-validation.json" \
  --chroma-key "$CHROMA_KEY" \
  --require-v2 \
  --allow-animated \
  --allow-transparent-rgb-residue
```

Then validate the complete animated WebP against the approved static source:

```bash
"$PYTHON" "$SKILL_DIR/scripts/validate_smooth_idle_webp.py" \
  "$RUN_DIR/final/spritesheet-runtime.webp" \
  --source-atlas "$RUN_DIR/final/spritesheet-extended.webp" \
  --json-out "$RUN_DIR/qa/smooth-idle-validation.json"
```

Require all of these before installation:

- six WebP frames with exact durations and infinite looping;
- exact approved idle phase order;
- idle columns 0-5 synchronized inside every WebP frame, with neutral-look column 6 preserved;
- rows 1-10 have exact alpha and visible RGB in every WebP frame;
- runtime frame 0 passes the normal v2 structural validator;
- the approved static atlas, contact sheets, direction QA, previews, and semantics remain retained as QA artifacts.

Package `spritesheet-runtime.webp` as `spritesheet.webp`. Keep `spritesheet-extended.webp` in the run folder as the static QA master.

## Expressive idle phase manifest

Use `--phase-manifest` on both commands to declare any number of 2-60 approved phases. Each phase specifies a positive duration and exactly one source: either a populated static-atlas cell or a static `192x208` RGBA image. Relative image paths resolve from the manifest directory.

```json
{
  "phases": [
    {"label": "rest", "atlas_row": 0, "atlas_column": 0, "duration_ms": 260},
    {"label": "mouth-open", "image": "frames/mouth-open.png", "duration_ms": 150},
    {"label": "wave-out", "image": "frames/wave-out.png", "duration_ms": 170},
    {"label": "return", "atlas_row": 0, "atlas_column": 1, "duration_ms": 240}
  ]
}
```

```bash
"$PYTHON" "$SKILL_DIR/scripts/package_smooth_idle_webp.py" \
  --source-atlas "$RUN_DIR/final/spritesheet-extended.webp" \
  --phase-manifest "$RUN_DIR/qa/idle-phase-manifest.json" \
  --output "$RUN_DIR/final/spritesheet-runtime.webp" \
  --json-out "$RUN_DIR/qa/smooth-idle-package.json"

"$PYTHON" "$SKILL_DIR/scripts/validate_smooth_idle_webp.py" \
  "$RUN_DIR/final/spritesheet-runtime.webp" \
  --source-atlas "$RUN_DIR/final/spritesheet-extended.webp" \
  --phase-manifest "$RUN_DIR/qa/idle-phase-manifest.json" \
  --json-out "$RUN_DIR/qa/smooth-idle-validation.json"
```

The specialized validator must report the manifest's exact phase count, durations, labels, and source paths, synchronized idle columns, unchanged non-idle rows, and an exact deterministic phase map.

Render and inspect the exact packaged time-axis loop before installation:

```bash
"$PYTHON" "$SKILL_DIR/scripts/render_smooth_idle_preview.py" \
  "$RUN_DIR/final/spritesheet-runtime.webp" \
  --output "$RUN_DIR/qa/smooth-idle-preview.gif"
```

Reject visible identity drift, scale or baseline popping, an abrupt loop boundary, extra limbs, a gesture that does not read at pet size, chroma fringe, alternating hands, movement in a declared fixed limb, or a sparse two-position wave that visibly snaps.

## Limits

- The animated WebP wrapper fixes idle cadence and may add explicitly requested expressive gestures to the idle image clock. The optional playback patch can keep a non-idle row repeating only while its real desktop state remains active; it cannot invent a state, postpone a state transition, or keep “working” visible after Codex has actually moved to review, waiting, failure, or idle.
- Animated WebP continues on its image clock even when the desktop reduced-motion setting disables JavaScript sprite timers. Tell the user and do not enable this path unless they explicitly prioritize continuous idle motion.
- State entry does not reset the WebP clock. This is safe because the idle loop is periodic and every selectable idle column is phase-synchronized.
- Treat current desktop animated-WebP support as a runtime compatibility behavior, not a manifest guarantee. Retain the static source so the pet can be repackaged if a future desktop build changes image decoding.
