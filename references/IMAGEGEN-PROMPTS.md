# Feidudu image-generation prompt record

The artwork in this repository was created with the built-in image-generation mode. Nine internal character studies were organized into `source-images/reference-contact-sheet.jpg`, forming a single art-direction board for silhouette, proportions, materials, palette, and expression continuity.

## Shared character and output contract

The following constraints were carried through every accepted generation:

> Create Feidudu as a polished 3D soft-vinyl toy mascot using the repository's nine-image character design board: a golden-yellow pear-shaped chubby body, two long rounded ears, cream oval belly, oversized dark reddish-brown oval nose, round white eyes with dark-brown pupils, exactly two short arms, exactly two feet, and one thick curved tail. No clothing. Keep the same identity, proportions, materials, colors, face construction, and warm studio lighting across every frame. Render the complete character with no crop and no text, logo, watermark, border, scenery, floor, cast shadow, duplicate body, or extra limb. Use a perfectly uniform `#FF00FF` chroma background with hard panel separation and no magenta foreground object.

The orange laptop is a locked prop shared only by the working and review rows. Hearts are expression props, not part of the neutral character.

## Accepted generation set

1. **Canonical full-body base** — neutral front-facing stance, arms relaxed, feet visible, tail visible; single character on `#FF00FF`.
2. **Idle strip, six panels** — neutral breathing, lifted breath, closed-eye blink, happy open mouth, settling mouth, soft neutral return.
3. **Run-right strip, eight panels** — coherent right-facing gait with alternating contacts, passing poses, flight poses, stable scale, and complete limbs. The left-facing row was derived by framewise mirroring with order preserved.
4. **Greeting strip, four panels** — one-paw lift, open wave, happy apex, neutral return.
5. **Jump strip, five panels** — anticipation, takeoff, airborne apex, descent, landing; vertical arc retained during deterministic cell normalization.
6. **Blocked strip, eight panels** — recognition, concern, ear/body droop, lowest discouraged pose, recovery, neutral return.
7. **Needs-input strip, six panels** — attentive pause, hands near chest, questioning gesture, open-palmed request, soft hold, return.
8. **Working strip, six panels** — seated at a small orange laptop, alternating typing, blink, screen reading, resuming work.
9. **Review strip, six panels** — the exact same orange laptop, attentive reading, downward focus, blink, satisfied check, waiting pose.
10. **Cardinal gaze strip, four panels** — `000` up, `090` screen-right, `180` down, `270` screen-left.
11. **Gaze row 9, eight panels** — `000`, `022.5`, `045`, `067.5`, `090`, `112.5`, `135`, `157.5`, with one continuous 22.5-degree directional progression.
12. **Gaze row 10, eight panels** — `180`, `202.5`, `225`, `247.5`, `270`, `292.5`, `315`, `337.5`, continuing directly from row 9 and closing toward `000`.

For the two gaze rows, body height, head size, feet, belly, tail base, lighting, and lower-body registration were locked. Direction changes were expressed through coherent head turn, pupils, nose orientation, eyelids, ears, and tail perspective. Final placement into exact 192 × 208 cells was deterministic rather than delegated to the image model.

## Post-generation processing

- `#FF00FF` was removed with the repository chroma-key tooling.
- Standard state frames were extracted from separated pose groups.
- Jump frames were normalized while preserving their vertical trajectory.
- The approved run-right row was mirrored framewise to produce run-left.
- Gaze rows were independently segmented, normalized, and registered.
- One final atlas-wide edge decontamination removed magenta fringe.
- Static and animated Sprite V2 validators confirmed geometry, alpha, phase mapping, native state coverage, and unchanged look rows.
