#!/usr/bin/env python3
"""Apply or remove the exact-chat-surface CSS patch for Orca.

Orca's native chat derives a few internal surfaces with color-mix(). A plugin
theme cannot override those variables, so this optional local patch pins them
to the theme tokens. It performs equal-length byte replacements to keep the
asar metadata valid and finds Orca's hashed CSS filenames at runtime, so it
keeps working when an Orca update renames them.

Run with Orca closed if possible, then reload/restart Orca.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ASSETS = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/orca/resources/app.asar.unpacked/out/renderer/assets",
    Path("/Applications/Orca.app/Contents/Resources/app.asar.unpacked/out/renderer/assets"),
    Path.home() / "Applications/Orca.app/Contents/Resources/app.asar.unpacked/out/renderer/assets",
    Path("/opt/Orca/resources/app.asar.unpacked/out/renderer/assets"),
    Path("/usr/lib/orca/resources/app.asar.unpacked/out/renderer/assets"),
]

CLIENT_REPLACEMENTS = [
    (b"--chat-canvas-mix:5%", b"--chat-canvas-mix:0%"),
    (b"--chat-composer-mix:4%", b"--chat-composer-mix:0%"),
    (b"--chat-composer-base:transparent", b"--chat-composer-base:var(--card)"),
]

# Orca 1.4.268 moved the composer mix behind --chat-composer-base; older
# releases mixed directly into --chat-canvas. Support both shapes.
APP_TARGETS = [
    b"--chat-composer-surface:color-mix(in srgb, var(--chat-source-foreground) "
    b"var(--chat-composer-mix), var(--chat-canvas))",
    b"--chat-composer-surface:color-mix(in srgb, var(--chat-source-foreground) "
    b"var(--chat-composer-mix), var(--chat-composer-base))",
]
APP_REPLACEMENT = b"--chat-composer-surface:var(--card)"

BACKUP_SUFFIX = ".catppuccin-exact.bak"


def find_assets(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_dir():
            return path
        raise SystemExit(f"Not a directory: {path}")
    for path in ASSETS:
        if path.is_dir():
            return path
    raise SystemExit(
        "Could not find Orca's app.asar.unpacked assets. Pass --assets <dir>."
    )


def find_css(assets: Path, pattern: str, needles, label: str) -> Path:
    matches = [
        path
        for path in sorted(assets.glob(pattern))
        if any(needle in path.read_bytes() for needle in needles)
    ]
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches)
        raise SystemExit(f"{label}: ambiguous CSS files: {names}")
    if not matches:
        raise SystemExit(f"{label}: no {pattern} with the expected chat rules")
    return matches[0]


def backup(path: Path) -> None:
    target = path.with_suffix(path.suffix + BACKUP_SUFFIX)
    if not target.exists():
        shutil.copy2(path, target)
        print(f"{path.name}: backup {target.name}")


def patch_bytes(path: Path, replacements, label: str) -> bool:
    data = path.read_bytes()
    original_size = len(data)
    changed = False
    for target, replacement in replacements:
        if len(target) != len(replacement):
            raise SystemExit(f"{label}: replacement length mismatch")
        if target in data:
            data = data.replace(target, replacement)
            changed = True
    if not changed:
        print(f"{label}: already patched or target not found")
        return False
    if len(data) != original_size:
        raise SystemExit(f"{label}: size changed, refusing to write")
    backup(path)
    path.write_bytes(data)
    print(f"{label}: patched ({original_size} bytes)")
    return True


def patch_app_css(path: Path) -> bool:
    data = path.read_bytes()
    changed = False
    for target in APP_TARGETS:
        if target not in data:
            continue
        padded = APP_REPLACEMENT + b" " * (len(target) - len(APP_REPLACEMENT))
        data = data.replace(target, padded)
        changed = True
    if not changed:
        if APP_REPLACEMENT in data:
            print(f"{path.name}: already patched")
        else:
            print(f"{path.name}: composer target not found (Orca version changed?)")
        return False
    original_size = path.stat().st_size
    if len(data) != original_size:
        raise SystemExit(f"{path.name}: size changed, refusing to write")
    backup(path)
    path.write_bytes(data)
    print(f"{path.name}: patched ({original_size} bytes)")
    return True


def restore(assets: Path) -> None:
    backups = sorted(assets.glob(f"*{BACKUP_SUFFIX}"))
    if not backups:
        print(f"{assets}: no backups found")
        return
    for backup_path in backups:
        path = backup_path.with_name(backup_path.name[: -len(BACKUP_SUFFIX)])
        shutil.copy2(backup_path, path)
        print(f"{path.name}: restored from {backup_path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", help="Path to out/renderer/assets")
    parser.add_argument("--restore", action="store_true", help="Restore backups")
    args = parser.parse_args()

    assets = find_assets(args.assets)
    print(f"Orca assets: {assets}")
    if args.restore:
        restore(assets)
        print("Restart Orca to apply.")
        return 0

    client = find_css(
        assets,
        "client-*.css",
        (b"--chat-canvas-mix:5%", b"--chat-canvas-mix:0%"),
        "client CSS",
    )
    app = find_css(
        assets,
        "App-*.css",
        (b"--chat-composer-surface:color-mix", b"--chat-composer-surface:var(--card)"),
        "app CSS",
    )

    patch_bytes(client, CLIENT_REPLACEMENTS, client.name)
    patch_app_css(app)
    print("Done. Restart Orca (quit and reopen); a renderer reload may not reread it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
