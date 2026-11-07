#!/usr/bin/env python3
"""Render the app previews, cover and social image from the theme JSON.

    python tools/render-previews.py

Builds HTML that uses the plugin's own tokens, then screenshots it with
agent-browser, so the artwork tracks themes/*.json. Pass --dark-capture
with a live Orca capture to use that as screenshot-dark.png instead.
"""

from __future__ import annotations

import base64
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

_spec = importlib.util.spec_from_file_location("build_assets", ROOT / "tools" / "build-assets.py")
_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_build)

FLAVORS = _build.FLAVORS
load_tokens = _build.load_tokens


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def syntax(flavor: str) -> dict:
    p = FLAVORS[flavor]
    dark = flavor == "mocha"
    return {
        "comment": p["overlay2"],
        "keyword": p["mauve"],
        "string": p["green"],
        "func": p["blue"],
        "type": p["yellow"],
        "number": p["peach"],
        "punct": p["overlay1"] if dark else p["overlay0"],
    }


def theme_vars(flavor: str) -> str:
    t = load_tokens(flavor)
    p = FLAVORS[flavor]
    dark = flavor == "mocha"
    extra = {
        "--hover": p["surface0"] if dark else p["surface0"],
        "--line": p["surface0"] if dark else p["surface1"],
        "--soft": p["surface1"] if dark else p["surface1"],
        "--green": p["green"],
        "--red": p["red"],
        "--yellow": p["yellow"],
        "--blue": p["blue"],
        "--mauve": p["mauve"],
        "--peach": p["peach"],
        "--teal": p["teal"],
        "--pink": p["pink"],
        "--comment": syntax(flavor)["comment"],
    }
    merged = {**t, **extra}
    return ";".join(f"{k}:{v}" for k, v in merged.items())


def app_html(flavor: str) -> str:
    v = theme_vars(flavor)
    dark = flavor == "mocha"
    p = FLAVORS[flavor]
    s = syntax(flavor)
    name = "Catppuccin Exact" if dark else "Catppuccin Latte Exact"
    slug = "catppuccin-exact-dark.json" if dark else "catppuccin-exact-light.json"
    json_name = slug
    # code sample
    code = [
        [("comment", "// Chat surfaces pinned to the palette, no color-mix().")],
        [],
        [("kw", "import"), ("punct", " { "), ("fn", "defineTheme"), ("punct", " } "),
         ("kw", "from"), ("punct", " "), ("str", "'@orca/themes'")],
        [],
        [("kw", "export const"), ("punct", " "), ("fn", "exact"), ("punct", " = "),
         ("fn", "defineTheme"), ("punct", "({")],
        [("punct", "  base: "), ("str", "'dark'"), ("punct", ",")],
        [("punct", "  canvas: "), ("str", "'#1e1e2e'"), ("punct", ",")],
        [("punct", "  panel: "), ("str", "'#181825'"), ("punct", ",")],
        [("punct", "  composer: "), ("str", "'#181825'"), ("punct", ",")],
        [("punct", "  sidebar: "), ("str", "'#181825'"), ("punct", ",")],
        [("punct", "  foreground: "), ("str", "'#cdd6f4'"), ("punct", ",")],
        [("punct", "  muted: "), ("str", "'#a6adc8'"), ("punct", ",")],
        [("punct", "  border: "), ("str", "'#7f849c19'"), ("punct", ",")],
        [("punct", "  accent: "), ("str", "'#cba6f7'"), ("punct", ",")],
        [("punct", "  tokens: "), ("num", "66"), ("punct", ", rules: "), ("num", "28"), ("punct", ",")],
        [("punct", "})")],
        [],
        [("comment", "// 4 flavors upstream, 2 surfaces here, zero tint.")],
    ]
    if not dark:
        code = [[(k, v.replace("'dark'", "'light'").replace("#1e1e2e", "#eff1f5")
                  .replace("#181825", "#e9ebef").replace("#cba6f7", "#7130c7")
                  .replace("#cdd6f4", "#4c4f69").replace("#a6adc8", "#616274")
                  .replace("#7f849c19", "#66677023"))
                 for k, v in line] for line in code]

    def span(kind: str, text: str) -> str:
        cls = {"comment": "c", "kw": "k", "str": "s", "fn": "f", "num": "n",
               "type": "t", "punct": "p", "plain": ""}[kind]
        return f'<span class="{cls}">{esc(text)}</span>' if cls else esc(text)

    lines = []
    for i, line in enumerate(code, 1):
        body = "".join(span(kind, text) for kind, text in line) if line else ""
        lines.append(f'<div class="line"><i>{i}</i><code>{body}</code></div>')

    tree = [
        (0, "folder", "assets", None, True),
        (1, "file", "screenshot-light.png", None, False),
        (1, "file", "screenshot-dark.png", None, False),
        (0, "folder", "themes", None, True),
        (1, "file", "catppuccin-exact-dark.json", "M", False),
        (1, "file", "catppuccin-exact-light.json", "M", False),
        (0, "folder", "tools", None, False),
        (0, "file", "orca-plugin.json", None, False),
        (0, "file", "README.md", None, False),
    ]
    tree_html = []
    for depth, kind, label, badge, open_ in tree:
        pad = 12 + depth * 16
        icon = "▾" if kind == "folder" and open_ else ("▸" if kind == "folder" else "∙")
        badge_html = f'<b class="mbadge">{badge}</b>' if badge else ""
        tree_html.append(
            f'<div class="row" style="padding-left:{pad}px">'
            f'<span class="ico {"folder" if kind == "folder" else ""}">{icon}</span>'
            f'<span class="name {"" if kind == "folder" else "mono"}">{esc(label)}</span>'
            f'{badge_html}</div>')

    sw = [p["mauve"], p["blue"], p["green"], p["peach"], p["pink"], p["teal"]]

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box}}
html,body{{margin:0;width:1600px;height:100vh;overflow:hidden}}
body{{{v};background:var(--background);color:var(--foreground);
 font-family:Inter,'Segoe UI',system-ui,-apple-system,sans-serif;font-size:13px;
 -webkit-font-smoothing:antialiased}}
.ico,.mono,code,pre,.num{{font-family:'Cascadia Mono','JetBrains Mono',Consolas,monospace}}
.app{{height:100vh;display:flex;flex-direction:column}}
.top{{height:46px;flex:none;display:flex;align-items:center;gap:16px;padding:0 16px;
 background:var(--card);border-bottom:1px solid var(--line)}}
.mark{{width:24px;height:24px;border-radius:7px;background:var(--primary);display:flex;
 align-items:center;justify-content:center;color:var(--primary-foreground);font-weight:800;font-size:13px}}
.brand{{font-weight:700;font-size:14px;letter-spacing:-.2px}}
.crumb{{color:var(--muted-foreground);display:flex;align-items:center;gap:7px;font-size:12px}}
.crumb b{{color:var(--foreground);font-weight:500}}
.crumb .sep{{opacity:.45}}
.branch{{display:inline-flex;align-items:center;gap:5px;padding:2px 7px;border-radius:5px;
 background:var(--hover);font-size:11px;color:var(--muted-foreground)}}
.search{{margin-left:auto;width:420px;height:30px;border-radius:8px;background:var(--muted);
 border:1px solid var(--line);display:flex;align-items:center;gap:9px;padding:0 11px;
 color:var(--muted-foreground);font-size:12px}}
.key{{margin-left:auto;font-size:10px;opacity:.8;font-family:'Cascadia Mono',Consolas,monospace}}
.pill{{font-size:11px;color:var(--muted-foreground);padding:3px 8px;border-radius:6px;background:var(--hover)}}
.avatar{{width:24px;height:24px;border-radius:50%;background:var(--primary);color:var(--primary-foreground);
 display:flex;align-items:center;justify-content:center;font-weight:700;font-size:11px}}
.body{{flex:1;display:flex;min-height:0}}
.sidebar{{width:272px;flex:none;background:var(--sidebar);border-right:1px solid var(--line);
 padding:12px 10px;display:flex;flex-direction:column;color:var(--sidebar-foreground)}}
.label{{font-size:9.5px;font-weight:700;letter-spacing:1.1px;color:var(--muted-foreground);
 opacity:.85;margin:4px 8px 8px}}
.wt{{height:44px;border-radius:8px;padding:7px 10px;margin-bottom:2px;position:relative}}
.wt.active{{background:var(--hover)}}
.wt.active:before{{content:'';position:absolute;left:0;top:9px;width:3px;height:26px;border-radius:2px;background:var(--primary)}}
.wt .t{{font-size:12px;font-weight:600}}
.wt .s{{font-size:10.5px;color:var(--muted-foreground);font-family:'Cascadia Mono',Consolas,monospace;margin-top:2px}}
.dot{{position:absolute;right:10px;top:18px;width:6px;height:6px;border-radius:50%}}
.g{{background:var(--green)}}.y{{background:var(--yellow)}}
.new{{font-size:11.5px;color:var(--muted-foreground);padding:6px 10px;opacity:.8}}
.tree{{margin-top:2px}}
.row{{height:26px;display:flex;align-items:center;gap:6px;border-radius:5px;font-size:11.5px;padding-right:8px}}
.row .ico{{width:12px;color:var(--muted-foreground);font-size:9px;text-align:center}}
.row .ico.folder{{color:var(--primary)}}
.row .name{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.row .name.mono{{font-size:11px;color:var(--muted-foreground)}}
.mbadge{{margin-left:auto;font:700 9.5px 'Cascadia Mono',Consolas,monospace;color:var(--yellow);
 background:color-mix(in srgb,var(--yellow) 14%,transparent);border-radius:5px;padding:1px 5px}}
.spacer{{flex:1}}
.themecard{{background:var(--hover);border:1px solid var(--line);border-radius:9px;padding:10px}}
.themecard .r1{{display:flex;align-items:center;gap:7px;font-size:11.5px;font-weight:600}}
.check{{color:var(--green);font-size:11px}}
.themecard .r2{{font-size:10px;color:var(--muted-foreground);margin:3px 0 0 18px}}
.sw{{display:flex;gap:5px;margin-top:9px}}
.sw i{{width:14px;height:14px;border-radius:50%;display:block}}
.editor{{flex:1;min-width:0;display:flex;flex-direction:column;background:var(--editor-surface)}}
.tabs{{height:40px;flex:none;display:flex;align-items:flex-end;background:var(--card);
 border-bottom:1px solid var(--line);padding-left:8px;gap:2px}}
.tab{{height:34px;display:flex;align-items:center;padding:0 15px;font-size:12px;color:var(--muted-foreground);
 border-radius:7px 7px 0 0}}
.tab.active{{background:var(--editor-surface);color:var(--foreground);border-top:2px solid var(--primary);
 padding-top:0;height:36px}}
.tab.mono{{font-family:'Cascadia Mono',Consolas,monospace;font-size:11.5px}}
.tabadd{{margin-left:4px;color:var(--muted-foreground);font-size:16px;align-self:center;opacity:.7}}
.code{{padding:16px 0;flex:1;min-height:0;overflow:hidden}}
.line{{display:flex;height:26px;line-height:26px;white-space:pre}}
.line i{{width:52px;flex:none;text-align:right;padding-right:18px;color:var(--muted-foreground);
 opacity:.7;font-style:normal;font-family:'Cascadia Mono',Consolas,monospace;font-size:12px}}
.line code{{font-size:13px}}
.c{{color:var(--comment);font-style:italic}}.k{{color:{s['keyword']}}}.s{{color:{s['string']}}}
.f{{color:{s['func']}}}.n{{color:{s['number']}}}.t{{color:{s['type']}}}.p{{color:{s['punct']}}}
.term{{height:186px;flex:none;border-top:1px solid var(--line);background:var(--card)}}
.termhead{{height:32px;display:flex;align-items:center;gap:18px;padding:0 16px;
 border-bottom:1px solid var(--line);font-size:10.5px;letter-spacing:.6px;color:var(--muted-foreground)}}
.termhead b{{font-weight:600;color:var(--foreground);letter-spacing:0}}
.termhead .tabon{{color:var(--primary)}}
.term pre{{margin:12px 16px;font-size:12px;line-height:21px;color:var(--muted-foreground);white-space:pre}}
.term .cmd{{color:var(--foreground)}}.term .ok{{color:var(--green)}}.term .dim{{opacity:.75}}
.term .path{{color:var(--blue)}}.term .br{{color:var(--green)}}
.chat{{width:520px;flex:none;background:var(--card);border-left:1px solid var(--line);
 display:flex;flex-direction:column}}
.chathead{{height:44px;flex:none;display:flex;align-items:center;gap:8px;padding:0 16px;
 border-bottom:1px solid var(--line);font-weight:650;font-size:12.5px}}
.chip{{font:500 9.5px 'Cascadia Mono',Consolas,monospace;color:var(--muted-foreground);
 background:var(--hover);border-radius:5px;padding:3px 6px}}
.live{{width:6px;height:6px;border-radius:50%;background:var(--green);margin-left:auto}}
.messages{{flex:1;min-height:0;overflow:hidden;padding:16px 16px 0;display:flex;flex-direction:column;gap:14px}}
.msg.user{{align-self:flex-end;max-width:420px;background:var(--hover);border:1px solid var(--line);
 border-radius:12px;padding:11px 13px;font-size:12.5px;line-height:1.45}}
.msg .meta{{font-size:9.5px;color:var(--muted-foreground);margin-top:6px;text-align:right;
 font-family:'Cascadia Mono',Consolas,monospace}}
.who{{display:flex;align-items:center;gap:7px;font-size:12px;font-weight:650;margin-bottom:6px}}
.paw{{width:22px;height:22px;border-radius:50%;background:color-mix(in srgb,var(--primary) 16%,transparent);
 color:var(--primary);display:flex;align-items:center;justify-content:center;font-size:11px}}
.who small{{font-weight:400;color:var(--muted-foreground);font:400 9.5px 'Cascadia Mono',Consolas,monospace}}
.msg.agent p{{margin:0 0 8px;font-size:12.5px;line-height:1.5}}
.edited{{border:1px solid var(--line);background:var(--card);border-radius:9px;padding:9px 11px;margin:2px 0 9px}}
.edited .h{{display:flex;align-items:center;gap:7px;font-size:11.5px;font-weight:600}}
.edited .h .ok{{color:var(--green)}}
.edited .f{{margin:3px 0 0 18px;font:10px 'Cascadia Mono',Consolas,monospace;color:var(--muted-foreground)}}
.plus{{margin-left:auto;font:600 10px 'Cascadia Mono',Consolas,monospace;color:var(--green)}}
.minus{{font:600 10px 'Cascadia Mono',Consolas,monospace;color:var(--red)}}
.diff{{border:1px solid var(--line);border-radius:9px;overflow:hidden;margin-bottom:9px}}
.diff .dh{{height:30px;display:flex;align-items:center;gap:7px;padding:0 10px;font:10.5px 'Cascadia Mono',Consolas,monospace;
 background:var(--card);border-bottom:1px solid var(--line);color:var(--muted-foreground)}}
.diff .dh b{{color:var(--foreground);font-weight:500}}
.diff .dl{{height:18px;line-height:18px;font:10.5px 'Cascadia Mono',Consolas,monospace;white-space:pre;padding:0 10px}}
.diff .add{{background:color-mix(in srgb,var(--green) 10%,transparent);color:var(--foreground)}}
.diff .del{{background:color-mix(in srgb,var(--red) 10%,transparent);color:var(--foreground)}}
.diff .g{{color:var(--green)}}.diff .r{{color:var(--red)}}
.after{{font-size:11px;color:var(--muted-foreground);display:flex;align-items:center;gap:6px;margin-top:2px}}
.composer{{height:120px;flex:none;padding:10px 14px 14px}}
.box{{height:96px;border:1px solid var(--line);background:var(--card);border-radius:12px;
 padding:12px 13px;display:flex;flex-direction:column}}
.ph{{font-size:12.5px;color:var(--foreground);opacity:.85}}
.hint{{font:10px 'Cascadia Mono',Consolas,monospace;color:var(--muted-foreground);margin-top:7px}}
.cbot{{margin-top:auto;display:flex;align-items:center;gap:8px}}
.model{{font:500 9.5px 'Cascadia Mono',Consolas,monospace;color:var(--muted-foreground);
 background:var(--hover);border-radius:6px;padding:4px 7px}}
.send{{margin-left:auto;width:30px;height:30px;border-radius:50%;background:var(--primary);
 color:var(--primary-foreground);display:flex;align-items:center;justify-content:center;font-size:14px}}
.status{{height:28px;flex:none;display:flex;align-items:center;gap:12px;padding:0 14px;
 background:var(--card);border-top:1px solid var(--line);color:var(--muted-foreground);
 font:10.5px 'Cascadia Mono',Consolas,monospace}}
.status .r{{margin-left:auto}}
.status b{{color:var(--foreground);font-weight:500}}
</style></head><body><div class="app">
<header class="top">
 <div class="mark">O</div><div class="brand">Orca</div>
 <div class="crumb">esykai <span class="sep">/</span> <b>orca-catppuccin-exact</b>
   <span class="branch">⑂ main</span></div>
 <div class="search">⌕&nbsp; Search files, commands, agents <span class="key">Ctrl K</span></div>
 <span class="pill">2 worktrees</span><div class="avatar">A</div>
</header>
<div class="body">
 <aside class="sidebar">
  <div class="label">WORKTREES</div>
  <div class="wt active"><div class="t">orca-catppuccin-exact</div><div class="s">⑂ main</div><i class="dot g"></i></div>
  <div class="wt"><div class="t" style="color:var(--muted-foreground)">exact-chat-surfaces</div><div class="s">⑂ feat/chat-surfaces</div><i class="dot y"></i></div>
  <div class="new">+ New worktree</div>
  <div class="label" style="margin-top:12px">EXPLORER</div>
  <div class="tree">{''.join(tree_html)}</div>
  <div class="spacer"></div>
  <div class="label">APPEARANCE</div>
  <div class="themecard"><div class="r1"><span class="check">✓</span> {esc(name)}</div>
   <div class="r2">Orca plugin · {flavor}</div>
   <div class="sw">{''.join(f'<i style="background:{c}"></i>' for c in sw)}</div></div>
 </aside>
 <main class="editor">
  <div class="tabs"><div class="tab active mono">{esc(json_name)}</div>
   <div class="tab mono">theme.ts</div><div class="tab">README.md</div><div class="tabadd">+</div></div>
  <div class="code">{''.join(lines)}</div>
  <div class="term"><div class="termhead"><span class="tabon">TERMINAL</span><b>orca</b><span>pwsh</span></div>
   <pre><span class="cmd">❯ orca plugin validate .</span>
<span class="ok">orca-plugin.json: ok</span>  <span class="dim">local.catppuccin-exact 1.0.0 (data)</span>
<span class="cmd">❯ orca plugin list</span>
<span class="path">local.catppuccin-exact</span>  1.0.0  idle  <span class="br">data</span></pre></div>
 </main>
 <section class="chat">
  <div class="chathead"><span class="paw">✾</span> Agent <span class="chip">DeepSeek V4.1 Flash</span><i class="live"></i></div>
  <div class="messages">
   <div class="msg user">Match the theme's surfaces exactly — drop Orca's extra tint on the chat canvas and the composer.<div class="meta">You · 14:02</div></div>
   <div class="msg agent"><div class="who"><span class="paw">✾</span> Orca <small>agent · 14:03</small></div>
    <p>Done. Chat canvas, composer and panels now use the palette tokens 1:1 — no mixes left in the chat view.</p>
    <div class="edited"><div class="h"><span class="ok">✓</span> Edited 2 files <span class="plus">+48</span> <span class="minus">−12</span></div>
     <div class="f">themes/{esc(slug)} · …light.json</div></div>
    <div class="diff"><div class="dh"><b>{esc(json_name)}</b><span class="plus">+18</span><span class="minus">−6</span></div>
     <div class="dl del"><span class="r">−</span>   "--chat-canvas": "#272738",</div>
     <div class="dl add"><span class="g">+</span>   "--chat-canvas": "#1e1e2e",</div>
     <div class="dl add"><span class="g">+</span>   "--chat-composer": "#181825",</div>
     <div class="dl"><span class="p"> </span>   "--background": "#1e1e2e"</div></div>
    <div class="after"><span class="ok">✓</span> 66 / 66 tokens · 0 unknown · no empty rules</div>
   </div>
   <div class="msg user">And the light pair?<div class="meta">You · 14:04</div></div>
   <div class="msg agent"><div class="who"><span class="paw">✾</span> Orca <small>agent · 14:04</small></div>
    <p>Latte Exact ships in the same plugin. Put it in the light slot — same tokens, warmer text.</p></div>
  </div>
  <div class="composer"><div class="box"><div class="ph">Ask Orca to change the palette…</div>
   <div class="hint">Shift+Enter for a new line  ·  @ to reference a file</div>
   <div class="cbot"><span class="model">Claude Sonnet 4.5</span><div class="send">↑</div></div></div></div>
 </section>
</div>
<footer class="status"><span>⑂ <b>main*</b></span><span>● 2 worktrees</span><span class="r">Ln 42, Col 18&nbsp;&nbsp; UTF-8&nbsp;&nbsp; {esc(name)}</span></footer>
</div></body></html>"""


def cover_html(width: int, height: int, social: bool) -> str:
    p = FLAVORS["mocha"]
    t = load_tokens("mocha")
    shot = base64.b64encode((ASSETS / "screenshot-dark.png").read_bytes()).decode()
    if social:
        pad, title, sub, shot_w = 64, 54, 15, 560
    else:
        pad, title, sub, shot_w = 92, 82, 17, 840
    shot_h = int(shot_w * 1000 / 1600)
    top = int(height * 0.09)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box}}
html,body{{margin:0;width:{width}px;height:{height}px;overflow:hidden}}
body{{background:{p['crust']};color:{t['--foreground']};
 font-family:Inter,'Segoe UI',system-ui,sans-serif;position:relative}}
body:before,body:after{{content:'';position:absolute;border-radius:50%;filter:blur(90px)}}
body:before{{width:900px;height:700px;left:-220px;top:-260px;background:{p['mauve']};opacity:.28}}
body:after{{width:1000px;height:800px;right:-260px;bottom:-380px;background:{p['blue']};opacity:.20}}
.left{{position:absolute;left:{pad}px;top:{top}px;width:{width - shot_w - pad * 2 - 40}px}}
.eyebrow{{display:inline-flex;align-items:center;gap:8px;font-size:{10 if social else 11}px;
 font-weight:700;letter-spacing:1.3px;color:{t['--primary']};
 background:color-mix(in srgb,{t['--primary']} 14%,transparent);padding:7px 13px;border-radius:20px}}
.eyebrow i{{width:6px;height:6px;border-radius:50%;background:{t['--primary']}}}
h1{{margin:{34 if social else 52}px 0 0;font-size:{title}px;line-height:.95;letter-spacing:-2.5px;font-weight:800}}
h1 span{{color:{t['--primary']}}}
.sub{{margin-top:{14 if social else 22}px;font-size:{sub + 9}px;color:{t['--muted-foreground']};font-weight:500}}
p{{margin:{20 if social else 34}px 0 0;font-size:{sub}px;line-height:1.55;color:{t['--muted-foreground']};max-width:{width - shot_w - pad * 2 - 40}px}}
.dots{{display:flex;gap:{14 if social else 16}px;margin-top:{30 if social else 48}px}}
.dots i{{width:{18 if social else 20}px;height:{18 if social else 20}px;border-radius:50%;display:block}}
.chips{{display:flex;gap:9px;margin-top:{24 if social else 34}px;flex-wrap:wrap}}
.chips span{{font:500 {9.5 if social else 10.5}px 'Cascadia Mono',Consolas,monospace;
 background:{p['surface0']};padding:7px 10px;border-radius:7px}}
.shot{{position:absolute;left:{width - shot_w - pad}px;top:{top + (0 if social else 40)}px;
 width:{shot_w}px;height:{shot_h}px;border-radius:16px;overflow:hidden;
 border:1px solid {p['surface0']};box-shadow:0 30px 80px #0008}}
.shot img{{width:100%;height:100%;object-fit:cover;display:block}}
</style></head><body>
<div class="left"><div class="eyebrow"><i></i>ORCA PLUGIN · THEMES</div>
<h1>Catppuccin<br><span>Exact</span></h1>
<div class="sub">for Orca</div>
<p>The Catppuccin palette, with Orca's extra surface tint removed. One canvas, one composer.</p>
<div class="dots">{''.join(f'<i style="background:{p[c]}"></i>' for c in ['rosewater','flamingo','pink','mauve','red','maroon','peach','yellow'])}</div>
<div class="chips"><span>Dark + Light</span><span>66 tokens</span><span>data · no code</span><span>MIT</span></div>
</div>
<div class="shot"><img src="data:image/png;base64,{shot}"></div>
</body></html>"""


def render(html: str, name: str, png: str, w: int, h: int) -> None:
    page = ASSETS / f".{name}.html"
    page.write_text(html, encoding="utf-8")
    exe = Path.home() / "AppData/Local/Programs/orca/resources/agent-browser-win32-x64.exe"
    brow = str(exe) if exe.exists() else "agent-browser"
    subprocess.run([brow, "set", "viewport", str(w), str(h)], capture_output=True)
    subprocess.run([brow, "open", page.resolve().as_uri()], check=True, capture_output=True)
    subprocess.run([brow, "screenshot", str((ASSETS / png).resolve())],
                   check=True, capture_output=True)
    page.unlink(missing_ok=True)
    print(f"  assets/{png}  {(ASSETS / png).stat().st_size / 1024:.0f} KB")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dark-capture", type=Path,
                    help="real Orca capture to use as screenshot-dark.png (1600x1000 window)")
    args = ap.parse_args()

    ASSETS.mkdir(exist_ok=True)
    print("Previews")
    if args.dark_capture:
        from PIL import Image
        im = Image.open(args.dark_capture).convert("RGB")
        im.resize((1600, 875), Image.LANCZOS).save(ASSETS / "screenshot-dark.png")
        print(f"  assets/screenshot-dark.png  {(ASSETS / 'screenshot-dark.png').stat().st_size / 1024:.0f} KB")
    else:
        render(app_html("mocha"), "screenshot-dark", "screenshot-dark.png", 1600, 875)
    render(app_html("latte"), "screenshot-light", "screenshot-light.png", 1600, 875)
    render(cover_html(1600, 1000, False), "cover", "cover.png", 1600, 1000)
    render(cover_html(1280, 640, True), "social", "social-preview.png", 1280, 640)
    return 0


if __name__ == "__main__":
    sys.exit(main())
