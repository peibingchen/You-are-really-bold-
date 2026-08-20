# Contributing to Feidudu

Thanks for helping Feidudu stay expressive, recognizable, and technically reliable. Keep changes focused, reviewable, and reproducible.

## Visual invariants

- Golden-yellow pear-shaped body, two long ears, cream oval belly, large reddish-brown nose, and round eyes.
- Exactly two arms, two feet, and one curved tail; no extra, fused, detached, or disappearing limbs.
- No clothing in the default design. Hearts are expression props only.
- The working and review rows use the same orange laptop with consistent scale and orientation.
- Directional motion remains mirrored without reversing phase order.
- Every gesture returns cleanly without an unexplained scale, baseline, lighting, or silhouette jump.
- Look rows preserve 16 coherent headings at 22.5-degree intervals.

## Before opening a pull request

1. Rebuild public assets with `python scripts/build_gallery.py` and `python scripts/build_readme_assets.py`.
2. Run every validation command and the unit tests documented in the README.
3. Inspect changed animations at normal pet size and inspect phase sheets for continuity.
4. Include before/after visuals for animation changes.
5. Keep rejected generations, caches, local test installs, and machine-specific files out of the repository.

Directional-running changes must regenerate `assets/directional-gait.png` and the framewise mirror report. Pull requests should explain the user-visible reason, affected rows or phases, character-contract impact, and validation performed.
