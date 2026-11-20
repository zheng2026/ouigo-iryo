"""Write docs/demo.svg: an animated terminal (typed commands, output appearing line by line),
looping. Pure SVG + CSS, so GitHub renders it in a README <img>; no recorder needed.
The outputs are real: captured from live runs on 2026-11-20 (Madrid -> Valencia, Dec 2026).
Run: python3 docs/make_demo.py   (reads nothing, writes docs/demo.svg)"""
from html import escape
from pathlib import Path

W, PAD, LH, FS, CW = 860, 22, 21, 13.5, 8.15   # width, padding, line height, font size, char width
TOP = 46                                       # below the title bar
TOTAL = 26.0                                   # seconds per loop
TYPE_CPS = 38                                  # typed characters per second

C = {"bg": "#0d1117", "bar": "#161b22", "fg": "#e6edf3", "dim": "#8b949e", "prompt": "#e5007e",
     "key": "#79c0ff", "str": "#a5d6ff", "num": "#ffa657", "ok": "#3fb950", "hl": "#f0d000"}

# Each scene: a command typed at the prompt, then output lines (list of [(text, colour)] runs).
S = lambda t, c="fg": (t, c)
SCENES = [
    ("ouigo calendar Madrid Valencia --from 2026-12-01 --to 2026-12-31 \\\n  | jq -c '.cheapest, [.days[] | .price]'",
     [[S('{', 'fg'), S('"date"', 'key'), S(':', 'fg'), S('"2026-12-01"', 'str'), S(',', 'fg'), S('"price"', 'key'), S(':', 'fg'), S('9', 'num'), S('}', 'fg')],
      [S('[9,9,15,17,19,17,19,19,13,13,15,19,13,13,9,9,13,17,19,15,15,15,19,25,17,19,19,19,15,22,15]', 'num')],
      [S('# cheapest Madrid -> Valencia day in December: 9 EUR', 'dim')]]),
    ("ouigo search Madrid Valencia -d 2026-12-15 --sort price --limit 3 \\\n  | jq -r '.trains[] | \"\\(.departure[11:16]) \\(.service) from \\(.fares[0].price) EUR\"'",
     [[S('07:15 06472 from 9 EUR', 'ok')],
      [S('12:15 06822 from 17 EUR', 'fg')],
      [S('17:45 06572 from 19 EUR', 'fg')]]),
    ("ouigo open Madrid Valencia -d 2026-12-15",
     [[S('{', 'fg'), S('"opened"', 'key'), S(': ', 'fg'), S('true', 'num'), S(', ', 'fg'), S('"shop"', 'key'), S(': {', 'fg'), S('"url"', 'key'), S(': ', 'fg'),
       S('"https://ventas.ouigo.com/es-ES/_deeplink/journey-search?…', 'str')],
      [S('  &outboundDate=2026-12-15…"', 'str'), S(', ', 'fg'), S('"next"', 'key'), S(': ', 'fg'), S('"Pick your train and fare on Ouigo\'s page, then pay there."', 'str'), S('}}', 'fg')],
      [S('# you choose and pay on Ouigo\'s own page; the tool never touches payment', 'dim')]]),
]

els, css, t, y = [], [], 0.6, TOP + 18
n = [0]


def show_at(start, kind="fade"):
    """CSS class: hidden until `start`, visible until the loop resets."""
    n[0] += 1
    name = f"a{n[0]}"
    a = start / TOTAL * 100
    css.append(f"@keyframes {name}{{0%,{a:.2f}%{{opacity:0}}{a + 0.4:.2f}%,96%{{opacity:1}}100%{{opacity:0}}}}"
               f".{name}{{opacity:0;animation:{name} {TOTAL}s linear infinite}}")
    return name


def type_clip(start, chars, x, y0, h):
    """A clip rect that widens like typing between start and start + chars/TYPE_CPS."""
    n[0] += 1
    name = f"t{n[0]}"
    dur = chars / TYPE_CPS
    a, b = start / TOTAL * 100, (start + dur) / TOTAL * 100
    full = chars * CW + 4
    css.append(f"@keyframes {name}{{0%,{a:.2f}%{{width:0}}{b:.2f}%,100%{{width:{full:.0f}px}}}}"
               f".{name}{{width:0;animation:{name} {TOTAL}s steps({max(chars, 1)},end) infinite}}")
    els.append(f'<clipPath id="c{name}"><rect class="{name}" x="{x}" y="{y0}" height="{h}"/></clipPath>')
    return f"c{name}", dur


def runs_to_tspans(runs):
    return "".join(f'<tspan fill="{C[c]}">{escape(txt)}</tspan>' for txt, c in runs)


for cmd, out in SCENES:
    lines = cmd.split("\n")
    for i, line in enumerate(lines):
        prompt = [("$ ", "prompt")] if i == 0 else [("", "fg")]
        cls = show_at(t)
        clip, dur = type_clip(t, len(line) + 2, PAD, y - FS, LH)
        els.append(f'<g class="{cls}"><text x="{PAD}" y="{y}" clip-path="url(#{clip})">'
                   f'{runs_to_tspans(prompt + [(line, "fg")])}</text></g>')
        t += dur + 0.15
        y += LH
    t += 0.7                                          # "running..." pause
    for runs in out:
        cls = show_at(t)
        els.append(f'<text class="{cls}" x="{PAD}" y="{y}">{runs_to_tspans(runs)}</text>')
        t += 0.25
        y += LH
    t += 1.6
    y += LH * 0.6

H = int(y + PAD)
cursor = show_at(t)
els.append(f'<text class="{cursor}" x="{PAD}" y="{y - LH * 0.6}"><tspan fill="{C["prompt"]}">$ </tspan>'
           f'<tspan class="blink" fill="{C["fg"]}">▋</tspan></text>')
assert t < TOTAL - 1.5, f"scenes take {t:.1f}s; raise TOTAL"

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="ouigo CLI demo: cheapest December day, three cheapest trains, open Ouigo's page">
<style>
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-size:{FS}px;white-space:pre}}
.blink{{animation:blink 1s steps(1) infinite}}@keyframes blink{{50%{{opacity:0}}}}
{"".join(css)}
@media (prefers-reduced-motion: reduce){{[class]{{animation:none!important;opacity:1!important}}rect[class]{{width:{W}px!important}}}}
</style>
<rect width="{W}" height="{H}" rx="10" fill="{C["bg"]}"/>
<rect width="{W}" height="32" rx="10" fill="{C["bar"]}"/><rect y="22" width="{W}" height="10" fill="{C["bar"]}"/>
<circle cx="20" cy="16" r="6" fill="#ff5f57"/><circle cx="40" cy="16" r="6" fill="#febc2e"/><circle cx="60" cy="16" r="6" fill="#28c840"/>
<text x="{W / 2}" y="20" text-anchor="middle" fill="{C["dim"]}" font-size="12">ouigo-es · Madrid → Valencia · real output (trimmed), Dec 2026</text>
<defs>{"".join(e for e in els if e.startswith("<clipPath"))}</defs>
{"".join(e for e in els if not e.startswith("<clipPath"))}
</svg>'''
out = Path(__file__).with_name("demo.svg")
out.write_text(svg, encoding="utf-8")
print(f"wrote {out} ({len(svg)} bytes, {W}x{H}, loop {TOTAL}s, scenes end at {t:.1f}s)")
