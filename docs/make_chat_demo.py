"""Write docs/mcp-demo.svg: an animated chat where an AI assistant answers a trip question
through the ouigo MCP tools. Pure SVG + CSS (plays in a GitHub README <img>).
Content is from a REAL run on 2026-11-20 (Claude Sonnet via Claude Code + ouigo-mcp),
lightly shortened; the full transcript is docs/mcp_transcript.md.
Run: python3 docs/make_chat_demo.py   (reads nothing, writes docs/mcp-demo.svg)"""
from html import escape
from pathlib import Path

W, PAD, FS, LH = 860, 26, 14, 21
TOTAL = 24.0
C = {"bg": "#111418", "panel": "#1a1f26", "user": "#2b3340", "fg": "#e6edf3", "dim": "#8b949e",
     "chip": "#21262d", "chipb": "#30363d", "accent": "#e5007e", "ok": "#3fb950", "num": "#ffa657", "line": "#30363d"}

css, els = [], []
k = [0]


def show(start, slide=True):
    k[0] += 1
    n = f"s{k[0]}"
    a = start / TOTAL * 100
    move = "transform:translateY(6px);" if slide else ""
    css.append(f"@keyframes {n}{{0%,{a:.2f}%{{opacity:0;{move}}}{a + 1.2:.2f}%,96%{{opacity:1;transform:none}}100%{{opacity:0}}}}"
               f".{n}{{opacity:0;animation:{n} {TOTAL}s ease-out infinite}}")
    return n


def hide(start):
    """Visible from 0 of its parent's life, gone at `start` (for 'running…' spinners)."""
    k[0] += 1
    n = f"h{k[0]}"
    a = start / TOTAL * 100
    css.append(f"@keyframes {n}{{0%,{a:.2f}%{{opacity:1}}{a + 0.3:.2f}%,100%{{opacity:0}}}}"
               f".{n}{{animation:{n} {TOTAL}s linear infinite}}")
    return n


def typing(start, chars, x, y0, w, h, cps=45):
    k[0] += 1
    n = f"t{k[0]}"
    a, b = start / TOTAL * 100, (start + chars / cps) / TOTAL * 100
    css.append(f"@keyframes {n}{{0%,{a:.2f}%{{width:0}}{b:.2f}%,100%{{width:{w}px}}}}"
               f".{n}{{width:0;animation:{n} {TOTAL}s steps({chars},end) infinite}}")
    els.append(f'<clipPath id="c{n}"><rect class="{n}" x="{x}" y="{y0}" height="{h}"/></clipPath>')
    return f"c{n}", chars / cps


def text(x, y, s, fill="fg", weight=None, size=None, extra=""):
    w = f' font-weight="{weight}"' if weight else ""
    z = f' font-size="{size}"' if size else ""
    return f'<text x="{x}" y="{y}" fill="{C[fill]}"{w}{z}{extra}>{s}</text>'


body = []
y = 64
t = 0.5

# 1. user message, typed into a bubble
q1 = "I'm in Madrid and want to visit Valencia by Ouigo in December 2026."
q2 = "What's the cheapest day to go, and which trains run that day?"
bw = 560
bx = W - PAD - bw
g = show(t, slide=False)
clip1, d1 = typing(t, len(q1), bx + 16, y + 4, bw, 26)
clip2, d2 = typing(t + d1, len(q2), bx + 16, y + 26, bw, 26)
body.append(f'<g class="{g}"><rect x="{bx}" y="{y}" width="{bw}" height="58" rx="14" fill="{C["user"]}"/>'
            f'<text x="{bx + 16}" y="{y + 23}" fill="{C["fg"]}" clip-path="url(#{clip1})">{escape(q1)}</text>'
            f'<text x="{bx + 16}" y="{y + 45}" fill="{C["fg"]}" clip-path="url(#{clip2})">{escape(q2)}</text></g>')
t += d1 + d2 + 0.8
y += 84


def tool_chip(y, label, args, start, dur):
    g = show(start)
    spin = hide(start + dur)
    done = show(start + dur, slide=False)
    return (f'<g class="{g}"><rect x="{PAD}" y="{y}" width="{W - 2 * PAD}" height="34" rx="8" fill="{C["chip"]}" stroke="{C["chipb"]}"/>'
            f'<text x="{PAD + 14}" y="{y + 22}" fill="{C["dim"]}" font-size="12.5">ouigo</text>'
            f'<text x="{PAD + 62}" y="{y + 22}" fill="{C["fg"]}" font-size="12.5" font-family="ui-monospace,SFMono-Regular,Menlo,monospace">'
            f'{escape(label)}<tspan fill="{C["dim"]}">({escape(args)})</tspan></text>'
            f'<text class="{spin}" x="{W - PAD - 14}" y="{y + 22}" text-anchor="end" fill="{C["dim"]}" font-size="12.5">running…</text>'
            f'<text class="{done}" x="{W - PAD - 14}" y="{y + 22}" text-anchor="end" fill="{C["ok"]}" font-size="12.5">✓ 31 days</text></g>')


body.append(tool_chip(y, "cheapest_days", '"Madrid", "Valencia", "2026-12-01", "2026-12-31"', t, 2.2))
t += 2.6
y += 46
body.append(show_line := f'<g class="{show(t)}">' + text(PAD, y + 4, "Four days tie at €9: Dec 1, 2, 15 and 16. Pulling the trains for Dec 1.", "dim") + "</g>")
t += 1.0
y += 22
chip2 = tool_chip(y, "search_trains", '"Madrid", "Valencia", "2026-12-01"', t, 2.2).replace("✓ 31 days", "✓ 4 trains")
body.append(chip2)
t += 2.8
y += 58

# 3. the answer
ans = [
    [("Cheapest: ", "fg", "600"), ("€9", "num", "700"), (" (Esencial fare), on Tue 1, Wed 2, Tue 15 and Wed 16 Dec.", "fg", "600")],
    [("Trains on Tue 1 Dec, Madrid Chamartín → Valencia Joaquín Sorolla, direct:", "fg", None)],
]
for runs in ans:
    s = "".join(f'<tspan fill="{C[c]}"{f" font-weight={chr(34)}{w}{chr(34)}" if w else ""}>{escape(x)}</tspan>' for x, c, w in runs)
    body.append(f'<text class="{show(t)}" x="{PAD}" y="{y}">{s}</text>')
    t += 0.5
    y += LH + 4

rows = [("Depart", "Arrive", "Esencial"), ("07:15", "09:09", "€9"), ("12:15", "14:16", "€15"),
        ("18:15", "20:09", "€19"), ("21:15", "23:15", "€15")]
cols = [PAD + 10, PAD + 120, PAD + 230]
for i, r in enumerate(rows):
    g = show(t)
    head = i == 0
    cells = "".join(text(cols[j], y, escape(v), "dim" if head else ("num" if (j == 2 and v == "€9") else "fg"),
                         "700" if (j == 2 and v == "€9") else None, 12.5 if head else None) for j, v in enumerate(r))
    line = f'<line x1="{PAD}" y1="{y + 7}" x2="{PAD + 330}" y2="{y + 7}" stroke="{C["line"]}"/>' if head else ""
    body.append(f'<g class="{g}">{cells}{line}</g>')
    t += 0.3
    y += LH + 2
y += 6
tail = [("Only the 07:15 gets €9 that day. One-way fare; fares fetched 20 Nov and can change.", "dim"),
        ("Book on Ouigo's page: ventas.ouigo.com/…journey-search?…&outboundDate=2026-12-01", "accent")]
for s, c in tail:
    body.append(f'<text class="{show(t)}" x="{PAD}" y="{y}" fill="{C[c]}">{escape(s)}</text>')
    t += 0.5
    y += LH + 2
assert t < TOTAL - 2, f"{t:.1f}s"

H = int(y + 18)
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="An AI assistant answers a trip question by calling ouigo-mcp tools: cheapest December day 9 euros, four trains on 1 December">
<style>
text{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;font-size:{FS}px;white-space:pre}}
{"".join(css)}
@media (prefers-reduced-motion: reduce){{[class]{{animation:none!important;opacity:1!important;transform:none!important}}rect[class]{{width:{W}px!important}}[class^="h"]{{opacity:0!important}}}}
</style>
<rect width="{W}" height="{H}" rx="12" fill="{C["bg"]}"/>
<rect width="{W}" height="36" rx="12" fill="{C["panel"]}"/><rect y="24" width="{W}" height="12" fill="{C["panel"]}"/>
<text x="{PAD}" y="23" fill="{C["dim"]}" font-size="12.5">AI chat + <tspan fill="{C["fg"]}">ouigo-mcp</tspan></text>
<text x="{W - PAD}" y="23" text-anchor="end" fill="{C["dim"]}" font-size="12">real run · Claude Sonnet via Claude Code · 20 Nov 2026 (shortened)</text>
<defs>{"".join(els)}</defs>
{"".join(body)}
</svg>'''
out = Path(__file__).with_name("mcp-demo.svg")
out.write_text(svg, encoding="utf-8")
print(f"wrote {out} ({len(svg)} bytes, {W}x{H}, loop {TOTAL}s, content ends at {t:.1f}s)")
