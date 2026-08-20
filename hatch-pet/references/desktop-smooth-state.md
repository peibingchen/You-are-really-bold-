# Smooth native-state image-time runtime

Use this opt-in path only after the complete static v2 atlas has passed normal structural, visual, semantic, and direction QA. It targets pets whose non-idle actions still look choppy at the desktop renderer's sprite-column cadence, or users who explicitly request roughly 20 phases and 12-15 named visual motions.

## Protocol boundary

Codex v2 has nine native trigger rows: `idle`, `running-right`, `running-left`, `waving`, `jumping`, `failed`, `waiting`, `running`, and `review`. Rows 9-10 are the 16 pointer-look directions. A pet atlas and the optional playback patch cannot create a tenth native event.

Treat 12-15 motions as named visual clips distributed across the nine native states. For example, idle may contain breathe, blink, mouth, and a small one-paw wave; working may contain alternating typing, a blink, and a read-screen bob. Document which native state owns every clip.

## How the runtime works

An animated WebP adds one global image-time axis around the approved static v2 atlas. At image-time phase `N`, each configured native row copies that state's approved phase-`N` cell into every column the renderer may select for that row. The desktop still chooses the real state row, while the WebP clock supplies the visual phase.

All native rows share the same WebP frame count and durations. State entry does not restart the image clock. Therefore:

- use one global duration timeline;
- make every state's phase list a valid periodic loop from any entry point;
- keep each clip's beginning and end compatible with neighboring clips;
- prefer 16-24 phases for an “about 20 frames” request;
- use 50-100 ms per phase for responsive desktop-pet motion, then judge the rendered loop rather than the number alone;
- do not count repeated atlas cells as new visual poses;
- do not use cross-fades, optical-flow interpolation, or code-drawn patches to satisfy missing visual frames;
- generate every distinct custom pose as a complete coherent `$imagegen` group, normalize it, and visually approve it before packaging.

Rows 9-10 always remain render-identical to the static QA master. Row 0 column 6 remains the neutral look cell and row 0 column 7 remains transparent.

## Motion manifest

The state-phase manifest uses schema version 1:

```json
{
  "schema_version": 1,
  "phases": [
    {"label": "t00", "duration_ms": 60},
    {"label": "t01", "duration_ms": 60}
  ],
  "motion_clips": [
    {"id": "work-type", "state": "running", "phase_range": [0, 1]}
  ],
  "states": {
    "idle": {
      "atlas_sequence": [0, 1]
    },
    "running": {
      "image_sequence": [
        "phases/running/00.png",
        "phases/running/01.png"
      ]
    }
  }
}
```

Every state declares exactly one of:

- `atlas_sequence`: static-atlas column numbers from that state's own native row;
- `image_sequence`: paths to approved static `192x208` RGBA cells, relative to the manifest;
- `phases`: explicit sources such as `{"atlas_column": 2}`, `{"atlas_row": 7, "atlas_column": 2}`, or `{"image": "..."}`.

Every sequence length must equal the global phase count. Production packaging should configure all nine states and pass `--require-all-states`.

## Complete-row generation and extraction

Generate connected motion in small coherent pose groups rather than one enormous twenty-pose sheet. Five-pose groups work well when each group starts and ends at the same neutral state pose. Reject the complete group if identity, scale, baseline, props, limb count, or limb connections drift.

For generated chroma-key groups, remove the key with the installed `$imagegen` helper, then extract and register them:

```bash
"$PYTHON" "$SKILL_DIR/scripts/extract_motion_phase_strips.py" \
  "$RUN_DIR/decoded/work-a-transparent.png" \
  "$RUN_DIR/decoded/work-b-transparent.png" \
  "$RUN_DIR/decoded/work-c-transparent.png" \
  "$RUN_DIR/decoded/work-d-transparent.png" \
  --frames-per-strip 5 \
  --reference-cell "$RUN_DIR/frames/running/00.png" \
  --output-dir "$RUN_DIR/phases/running" \
  --json-out "$RUN_DIR/qa/running-phase-extraction.json"
```

Inspect a labeled contact sheet at normal pet size. For a prop interaction such as a laptop, require the shoulder, upper arm, forearm, paw, and prop contact to remain coherent in every phase. A detached limb is a complete-group hard failure even when generic component metrics pass.

Keep the native static row as a six- or eight-cell compatibility fallback. Select a coherent subset of the approved high-phase poses and replace only that native row with `replace_v2_atlas_row.py`; re-run all static-atlas validation afterward.

For a directional rightward loop that has already passed anatomy, direction, and continuity review, derive the leftward high-phase loop only when the pet's markings, lighting, and props are safe to mirror:

```bash
"$PYTHON" "$SKILL_DIR/scripts/mirror_motion_phase_directory.py" \
  --source-dir "$RUN_DIR/phases/running-right" \
  --output-dir "$RUN_DIR/phases/running-left" \
  --expected-count 20 \
  --confirm-appropriate-mirror \
  --decision-note "symmetric pet with no handed prop; framewise mirroring preserves identity" \
  --json-out "$RUN_DIR/qa/running-left-mirror.json"
```

This transformation mirrors every `192x208` phase independently and preserves phase order. Never mirror the complete strip as one image, because that reverses the animation timeline.

## Package and validate

```bash
"$PYTHON" "$SKILL_DIR/scripts/package_smooth_state_webp.py" \
  --source-atlas "$RUN_DIR/final/spritesheet-extended.webp" \
  --phase-manifest "$RUN_DIR/qa/state-phases.json" \
  --output "$RUN_DIR/final/spritesheet-runtime.webp" \
  --json-out "$RUN_DIR/qa/smooth-state-package.json" \
  --require-all-states \
  --min-motion-clips 12 \
  --max-motion-clips 15

"$PYTHON" "$SKILL_DIR/scripts/validate_atlas.py" \
  "$RUN_DIR/final/spritesheet-runtime.webp" \
  --require-v2 \
  --allow-animated \
  --allow-transparent-rgb-residue \
  --json-out "$RUN_DIR/qa/smooth-state-frame-0-validation.json"

"$PYTHON" "$SKILL_DIR/scripts/validate_smooth_state_webp.py" \
  "$RUN_DIR/final/spritesheet-runtime.webp" \
  --source-atlas "$RUN_DIR/final/spritesheet-extended.webp" \
  --phase-manifest "$RUN_DIR/qa/state-phases.json" \
  --json-out "$RUN_DIR/qa/smooth-state-validation.json" \
  --require-all-states \
  --min-motion-clips 12 \
  --max-motion-clips 15

"$PYTHON" "$SKILL_DIR/scripts/render_smooth_state_previews.py" \
  "$RUN_DIR/final/spritesheet-runtime.webp" \
  --output-dir "$RUN_DIR/qa/smooth-state-previews" \
  --states all \
  --json-out "$RUN_DIR/qa/smooth-state-previews.json"

"$PYTHON" "$SKILL_DIR/scripts/measure_motion_phase_continuity.py" \
  "$RUN_DIR/phases/running" \
  --expected-count 20 \
  --chroma-key "$CHROMA_KEY" \
  --json-out "$RUN_DIR/qa/running-phase-continuity.json"
```

The specialized validator must report the exact global phase count, durations, labels, synchronized columns for every configured native row, unchanged look rows, exact deterministic phase mapping, and the three runtime caveats: one shared clock, no clock reset on state entry, and no new native triggers.

## Visual acceptance

Render every configured state from column 0 across the complete WebP timeline. Review each state as both a loop and individual numbered frames. Pass only when:

- the requested unique pose count is honest and visually distinct;
- every declared motion clip is visible in its documented phase range;
- clip boundaries and the final-to-first loop do not snap;
- identity, scale, baseline, and props remain stable;
- arms and legs never detach, multiply, or switch sides;
- motion stays readable at `192x208` without effects clutter;
- the actual desktop state still changes immediately when its real trigger changes.

The optional desktop playback patch may keep the selected native row visible while the corresponding real state remains active. It cannot delay a real state transition or invent a new event.
