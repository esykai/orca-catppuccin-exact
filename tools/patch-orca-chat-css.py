#!/usr/bin/env python3
"""Apply or remove the exact-chat-surface CSS patch for Orca.

Orca's native chat derives a few internal surfaces with color-mix(). A plugin
theme cannot override those variables, so this optional local patch pins them
to the theme tokens. It performs equal-length byte replacements to keep the
asar metadata valid.

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

APP_TARGET = (
    b"--chat-composer-surface:color-mix(in srgb, var(--chat-source-foreground) "
    b"var(--chat-composer-mix), var(--chat-canvas))"
)
APP_REPLACEMENT = b"--chat-composer-surface:var(--card)"


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
    backup = path.with_suffix(path.suffix + ".catppuccin-exact.bak")
    if not backup.exists():
        shutil.copy2(path, backup)
        print(f"{label}: backup {backup.name}")
    path.write_bytes(data)
    print(f"{label}: patched ({original_size} bytes)")
    return True


def patch_app_css(path: Path) -> bool:
    data = path.read_bytes()
    if APP_TARGET not in data:
        print(f"{path.name}: composer target not found (Orca version changed?)")
        return False
    padded = APP_REPLACEMENT + b" " * (len(APP_TARGET) - len(APP_REPLACEMENT))
    data = data.replace(APP_TARGET, padded)
    original_size = path.stat().st_size
    if len(data) != original_size:
        raise SystemExit(f"{path.name}: size changed, refusing to write")
    backup = path.with_suffix(path.suffix + ".catppuccin-exact.bak")
    if not backup.exists():
        shutil.copy2(path, backup)
        print(f"{path.name}: backup {backup.name}")
    path.write_bytes(data)
    print(f"{path.name}: patched ({original_size} bytes)")
    return True


def restore(assets: Path) -> None:
    for name in ("App-DDdspUUq.css", "client-BjztnwFA.css"):
        path = assets / name
        backup = path.with_suffix(path.suffix + ".catppuccin-exact.bak")
        if backup.exists():
            shutil.copy2(backup, path)
            print(f"{name}: restored from {backup.name}")
        else:
            print(f"{name}: no backup found")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", help="Path to out/renderer/assets")
    parser.add_argument("--restore", action="store_true", help="Restore backups")
    args = parser.parse_args()

    assets = find_assets(args.assets)
    print(f"Orca assets: {assets}")
    if args.restore:
        restore(assets)
        print("Reload Orca to apply.")
        return 0

    client = assets / "client-BjztnwFA.css"
    app = assets / "App-DDdspUUq.css"
    if not client.is_file() or not app.is_file():
        raise SystemExit("Expected Orca CSS files are missing in that folder.")

    patch_bytes(client, CLIENT_REPLACEMENTS, client.name)
    patch_app_css(app)
    print("Done. Reload Orca (Ctrl+R / Cmd+R). Orca updates overwrite this patch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
