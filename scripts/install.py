#!/usr/bin/env python3
"""Install Feidudu as a local Codex custom pet."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "pet"
PET_ID = "feidudu"


def update_selected_pet(config_path: Path) -> None:
    key = "selected-avatar-id"
    value = f'"custom:{PET_ID}"'
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    lines = original.splitlines()
    desktop_start = next((i for i, line in enumerate(lines) if line.strip() == "[desktop]"), None)

    if desktop_start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["[desktop]", f"{key} = {value}"])
    else:
        desktop_end = next(
            (i for i in range(desktop_start + 1, len(lines)) if lines[i].strip().startswith("[")),
            len(lines),
        )
        existing = next(
            (i for i in range(desktop_start + 1, desktop_end) if lines[i].split("=", 1)[0].strip() == key),
            None,
        )
        if existing is None:
            lines.insert(desktop_end, f"{key} = {value}")
        else:
            lines[existing] = f"{key} = {value}"

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--no-select", action="store_true", help="install without changing the selected pet")
    args = parser.parse_args()

    codex_home = args.codex_home.expanduser().resolve()
    destination = codex_home / "pets" / PET_ID
    manifest = json.loads((SOURCE / "pet.json").read_text(encoding="utf-8"))
    if manifest.get("id") != PET_ID or manifest.get("spriteVersionNumber") != 2:
        raise SystemExit("pet/pet.json does not match the expected Feidudu v2 contract")
    if not (SOURCE / "spritesheet.webp").is_file():
        raise SystemExit("pet/spritesheet.webp is missing")

    if destination.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = codex_home / "backups" / PET_ID / stamp
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(destination, backup)
        print(f"Backed up the previous pet to {backup}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE / "pet.json", destination / "pet.json")
    shutil.copy2(SOURCE / "spritesheet.webp", destination / "spritesheet.webp")

    if not args.no_select:
        update_selected_pet(codex_home / "config.toml")

    print(f"Installed 肥嘟嘟 to {destination}")
    print("Fully quit and reopen the ChatGPT desktop app, then open Settings > Pets and select 肥嘟嘟 if needed.")


if __name__ == "__main__":
    main()
