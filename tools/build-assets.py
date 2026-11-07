#!/usr/bin/env python3
"""Build the palette cards and plugin icon in assets/.

    python tools/build-assets.py            # SVGs
    python tools/build-assets.py --png      # SVGs + icon.png (needs agent-browser)

Colors come from FLAVORS, the canonical Catppuccin palette. App previews,
the cover and the social card are rendered from themes/*.json by
tools/render-previews.py.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

UI = "'Inter','Segoe UI',system-ui,-apple-system,sans-serif"
MONO = "'JetBrains Mono','Cascadia Mono','SF Mono',Consolas,monospace"

# Catppuccin 26-color palette, in the canonical order.
FLAVORS = {
    "mocha": {
        "rosewater": "#f5e0dc", "flamingo": "#f2cdcd", "pink": "#f5c2e7",
        "mauve": "#cba6f7", "red": "#f38ba8", "maroon": "#eba0ac",
        "peach": "#fab387", "yellow": "#f9e2af", "green": "#a6e3a1",
        "teal": "#94e2d5", "sky": "#89dceb", "sapphire": "#74c7ec",
        "blue": "#89b4fa", "lavender": "#b4befe", "text": "#cdd6f4",
        "subtext1": "#bac2de", "subtext0": "#a6adc8", "overlay2": "#9399b2",
        "overlay1": "#7f849c", "overlay0": "#6c7086", "surface2": "#585b70",
        "surface1": "#45475a", "surface0": "#313244", "base": "#1e1e2e",
        "mantle": "#181825", "crust": "#11111b",
    },
    "latte": {
        "rosewater": "#dc8a78", "flamingo": "#dd7878", "pink": "#ea76cb",
        "mauve": "#8839ef", "red": "#d20f39", "maroon": "#e64553",
        "peach": "#fe640b", "yellow": "#df8e1d", "green": "#40a02b",
        "teal": "#179299", "sky": "#04a5e5", "sapphire": "#209fb5",
        "blue": "#1e66f5", "lavender": "#7287fd", "text": "#4c4f69",
        "subtext1": "#5c5f77", "subtext0": "#6c6f85", "overlay2": "#7c7f93",
        "overlay1": "#8c8fa1", "overlay0": "#9ca0b0", "surface2": "#acb0be",
        "surface1": "#bcc0cc", "surface0": "#ccd0da", "base": "#eff1f5",
        "mantle": "#e6e9ef", "crust": "#dce0e8",
    },
}

ORDER = [
    "rosewater", "flamingo", "pink", "mauve", "red", "maroon", "peach",
    "yellow", "green", "teal", "sky", "sapphire", "blue", "lavender",
    "text", "subtext1", "subtext0", "overlay2", "overlay1", "overlay0",
    "surface2", "surface1", "surface0", "base", "mantle", "crust",
]


def load_tokens(flavor: str) -> dict:
    name = "catppuccin-exact-dark.json" if flavor == "mocha" else "catppuccin-exact-light.json"
    return json.loads((ROOT / "themes" / name).read_text(encoding="utf-8"))["tokens"]


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


class Svg:
    def __init__(self, w: int, h: int, title: str):
        self.w, self.h, self.title = w, h, title
        self.parts: list[str] = []
        self.defs: list[str] = []

    def add(self, s: str) -> None:
        self.parts.append(s)

    def rect(self, x, y, w, h, fill, rx=0, stroke=None, sw=1, opacity=None, extra=""):
        a = f'<rect x="{x}" y="{y}" width="{w}" height="{h}"'
        if rx:
            a += f' rx="{rx}"'
        a += f' fill="{fill}"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}"'
        if opacity is not None:
            a += f' opacity="{opacity}"'
        self.add(a + (f" {extra}" if extra else "") + "/>")

    def circle(self, cx, cy, r, fill, stroke=None, sw=1, opacity=None):
        a = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}"'
        if opacity is not None:
            a += f' opacity="{opacity}"'
        self.add(a + "/>")

    def line(self, x1, y1, x2, y2, stroke, sw=1, opacity=None, dash=None):
        a = (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
             f'stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"')
        if opacity is not None:
            a += f' opacity="{opacity}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        self.add(a + "/>")

    def path(self, d, stroke=None, fill="none", sw=1.5, opacity=None,
             cap="round", join="round"):
        a = f'<path d="{d}" fill="{fill}"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}" stroke-linecap="{cap}" stroke-linejoin="{join}"'
        if opacity is not None:
            a += f' opacity="{opacity}"'
        self.add(a + "/>")

    def text(self, x, y, s, size=12, fill="#cdd6f4", weight=400, anchor="start",
             family=UI, opacity=None, ls=None, style=None):
        a = (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
             f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" xml:space="preserve"')
        if opacity is not None:
            a += f' opacity="{opacity}"'
        if ls is not None:
            a += f' letter-spacing="{ls}"'
        if style:
            a += f' style="{style}"'
        self.add(a + f">{esc(s)}</text>")

    def render(self) -> str:
        d = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{self.w}" '
            f'height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img">'
            f"<title>{esc(self.title)}</title>{d}{''.join(self.parts)}</svg>\n"
        )


# ---------------------------------------------------------------- palette

def draw_palette(flavor: str) -> str:
    p = FLAVORS[flavor]
    dark = flavor == "mocha"
    bg = p["base"]
    fg = p["text"]
    muted = p["subtext0"]
    border = p["surface0"] if dark else p["surface1"]
    w, h = 1000, 760
    s = Svg(w, h, f"Catppuccin {flavor.capitalize()} palette used by "
                  f"Catppuccin {'Exact' if dark else 'Latte Exact'}")
    s.defs.append(
        '<radialGradient id="pg" cx="50%" cy="50%" r="50%">'
        f'<stop offset="0" stop-color="{p["mauve"]}" stop-opacity="0.16"/>'
        '<stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>'
    )
    s.rect(0, 0, w, h, bg, rx=22)
    s.add(f'<ellipse cx="120" cy="0" rx="360" ry="240" fill="url(#pg)"/>')
    s.rect(0, 0, w, h, "none", rx=22, stroke=border, sw=1)

    s.text(40, 64, f"Catppuccin {flavor.capitalize()}", 28, fg, 700)
    s.text(40, 92, "26 colors  ·  " +
           ("dark theme `Catppuccin Exact`" if dark else "light theme `Catppuccin Latte Exact`"),
           12.5, muted)

    pad, gap = 40, 7
    cols = 7
    cw = (w - pad * 2 - gap * (cols - 1)) / cols
    ch = 86
    for i, name in enumerate(ORDER):
        row, col = divmod(i, cols)
        x = pad + col * (cw + gap)
        y = 120 + row * 150
        s.rect(x, y, cw, ch, p[name], rx=9)
        s.text(x, y + ch + 20, name, 12, fg, 500)
        s.text(x, y + ch + 36, p[name].upper(), 10.5, muted, 400, "start", MONO)

    s.text(40, h - 36, "base · mantle · crust build the canvas, panels and composer; "
                       "the accents drive code, charts and focus rings.",
           11.5, muted)
    return s.render()


# ---------------------------------------------------------------- icon

def draw_icon() -> str:
    p = FLAVORS["mocha"]
    w = h = 256
    s = Svg(w, h, "Catppuccin Exact for Orca")
    s.defs.append(
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{p["base"]}"/>'
        f'<stop offset="1" stop-color="{p["crust"]}"/></linearGradient>'
        '<linearGradient id="cat" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{p["mauve"]}"/>'
        f'<stop offset="1" stop-color="{p["pink"]}"/></linearGradient>'
    )
    s.rect(0, 0, w, h, p["crust"])
    s.rect(0, 0, w, h, "url(#bg)", rx=56)
    s.rect(0.75, 0.75, w - 1.5, h - 1.5, "none", rx=56, stroke=p["surface0"], sw=1.5)

    # cat head
    s.add(f'<path d="M 74 104 L 62 56 L 104 76 Q 128 66 152 76 L 194 56 L 182 104 '
          f'Q 190 132 178 158 Q 164 190 128 190 Q 92 190 78 158 Q 66 132 74 104 Z" '
          f'fill="url(#cat)"/>')
    # ears cut + eyes
    for ex in (105, 151):
        s.add(f'<ellipse cx="{ex}" cy="124" rx="6" ry="9" fill="{p["crust"]}"/>')
    # nose + mouth
    s.add(f'<path d="M 122 145 L 134 145 L 128 152 Z" fill="{p["crust"]}"/>')
    s.add(f'<path d="M 128 152 q -7 8 -14 2 M 128 152 q 7 8 14 2" fill="none" '
          f'stroke="{p["crust"]}" stroke-width="3" stroke-linecap="round"/>')
    # whiskers
    for dy in (-4, 4):
        s.line(96, 146 + dy, 70, 142 + dy, p["crust"], 3)
        s.line(160, 146 + dy, 186, 142 + dy, p["crust"], 3)

    # flavor dots
    dots = [p["green"], p["yellow"], p["peach"], p["blue"], p["lavender"]]
    for i, c in enumerate(dots):
        s.circle(78 + i * 25, 216, 7, c)
    return s.render()


# ---------------------------------------------------------------- build

def write(name: str, content: str) -> Path:
    path = ASSETS / name
    path.write_text(content, encoding="utf-8")
    print(f"  {path.relative_to(ROOT)}  {path.stat().st_size / 1024:.1f} KB")
    return path


def rasterize(svg: Path, png: Path, w: int, h: int) -> None:
    exe = Path.home() / "AppData/Local/Programs/orca/resources/agent-browser-win32-x64.exe"
    if not exe.exists():
        exe = shutil.which("agent-browser")
    if not exe:
        print("  ! agent-browser not found; skipping PNG")
        return
    cmd = [str(exe), "set", "viewport", str(w), str(h)]
    subprocess.run(cmd, capture_output=True)
    subprocess.run([str(exe), "open", svg.resolve().as_uri()], check=True, capture_output=True)
    subprocess.run([str(exe), "screenshot", str(png.resolve())], check=True, capture_output=True)
    print(f"  {png.relative_to(ROOT)}  {png.stat().st_size / 1024:.1f} KB")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", action="store_true", help="rasterize the icon PNG too")
    args = ap.parse_args()

    ASSETS.mkdir(exist_ok=True)
    print("SVG")
    write("palette-mocha.svg", draw_palette("mocha"))
    write("palette-latte.svg", draw_palette("latte"))
    write("icon.svg", draw_icon())

    if args.png:
        print("PNG")
        rasterize(ASSETS / "icon.svg", ASSETS / "icon.png", 256, 256)
    return 0


if __name__ == "__main__":
    sys.exit(main())
