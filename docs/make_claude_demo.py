"""Edit Jade's real Claude Desktop screen recording into docs/demo-claude.mp4 and docs/demo-claude.gif.

Honest edit: waiting parts are sped up and always carry a visible speed badge; the device name in
Claude's status line is blurred; nothing is drawn over the app or the websites.

Run:  uv run --with pillow python docs/make_claude_demo.py "<recording.mov>"
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SRC = sys.argv[1]
OUT = Path(__file__).parent
W, H = 1920, 1126  # source 3366x1974 scaled to 1920 wide (even height)
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
REG = "/System/Library/Fonts/Supplemental/Arial.ttf"

# (start, end, speed) on the source timeline, seconds
SEGMENTS = [(0, 28, 3), (28, 146, 10), (146, 193.5, 1.5)]
# Blur the device name in the status line: (x, y, w, h, t_from, t_to) in source pixels/seconds
BLURS = [(820, 440, 1080, 55, 27, 112), (820, 630, 880, 55, 95, 147)]
END_CARD_S = 5

tmp = Path(tempfile.mkdtemp())


def badge(text, path):
    f = ImageFont.truetype(BOLD, 44)
    pad = 18
    w = int(f.getlength(text)) + 2 * pad
    img = Image.new("RGBA", (w, 72), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, 71), radius=16, fill=(232, 59, 110, 235))
    d.text((pad, 12), text, font=f, fill="white")
    img.save(path)


def end_card(path):
    img = Image.new("RGB", (W, H), (18, 18, 24))
    d = ImageDraw.Draw(img)
    big, mid, small = (ImageFont.truetype(BOLD, s) for s in (84, 48, 36))
    reg = ImageFont.truetype(REG, 40)
    lines = [
        (big, "ouigo-iryo", (255, 255, 255), 250),
        (mid, "A mano en la web: 38 €  ·  Con el agente: 32 €", (255, 196, 64), 420),
        (reg, "By hand on the website: €38  ·  With the agent: €32", (220, 220, 230), 490),
        (mid, "Ouigo + Iryo, el mismo día, lado a lado", (120, 220, 255), 610),
        (reg, "Ouigo + Iryo, same day, side by side", (220, 220, 230), 680),
        (small, "CLI + MCP · open source · unofficial", (170, 170, 185), 840),
    ]
    for font, text, color, y in lines:
        d.text(((W - font.getlength(text)) / 2, y), text, font=font, fill=color)
    img.save(path)


def run(cmd):
    subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL)


parts = []
for i, (a, b, speed) in enumerate(SEGMENTS):
    label = f"×{speed:g}"
    bpath = tmp / f"badge{i}.png"
    badge(label, bpath)
    chain = f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v]"
    last = "v"
    for j, (x, y, w, h, t0, t1) in enumerate(BLURS):
        if t1 <= a or t0 >= b:
            continue
        s0, s1 = max(t0, a) - a, min(t1, b) - a
        chain += (f";[{last}]split[m{j}][c{j}];[c{j}]crop={w}:{h}:{x}:{y},boxblur=12:2[b{j}];"
                  f"[m{j}][b{j}]overlay={x}:{y}:enable='between(t,{s0},{s1})'[o{j}]")
        last = f"o{j}"
    chain += (f";[{last}]setpts=PTS/{speed},scale={W}:{H},fps=30[s];"
              f"[s][1:v]overlay=W-w-36:36[out]")
    p = tmp / f"part{i}.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", SRC, "-i", str(bpath), "-filter_complex", chain,
         "-map", "[out]", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(p)])
    parts.append(p)

card = tmp / "card.png"
end_card(card)
cp = tmp / "card.mp4"
run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", str(END_CARD_S), "-i", str(card),
     "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "20", str(cp)])
parts.append(cp)

lst = tmp / "list.txt"
lst.write_text("".join(f"file '{p}'\n" for p in parts))
mp4 = OUT / "demo-claude.mp4"
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
     "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "21", "-movflags", "+faststart", str(mp4)])

gif = OUT / "demo-claude.gif"
pal = tmp / "pal.png"
run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf", "fps=8,scale=960:-1:flags=lanczos,palettegen=max_colors=128", str(pal)])
run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-i", str(pal), "-lavfi",
     "fps=8,scale=960:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4", str(gif)])
print(mp4, gif)
