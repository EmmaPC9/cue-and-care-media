"""Render Cue & Care v2 reels (1080x1920, 30 fps) from content.json.
Usage: python3 render.py OUTDIR [id ...]   (no ids = all)"""
import json, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = "/home/claude/fonts"
W, H = 1080, 1920
BG = (227, 241, 242); NAVY = (31, 42, 61); TEAL = (18, 120, 111); INK2 = (15, 90, 79)
PEACH = (245, 179, 160); WHITE = (255, 255, 255); MUTED = (150, 165, 175); CARD = (255, 255, 255)
X0, X1 = 80, 940            # keep clear of the right-side Reels buttons
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30"]

def serif(size, wght=800):
    f = ImageFont.truetype(f"{FONTS}/Fraunces.ttf", size)
    f.set_variation_by_axes([min(144, max(9, size)), wght, 0, 0]); return f
def script(size):
    f = ImageFont.truetype(f"{FONTS}/Caveat.ttf", size); f.set_variation_by_axes([600]); return f
def inter(size, w="SemiBold"):
    return ImageFont.truetype(f"/usr/share/fonts/opentype/inter/Inter-{w}.otf", size)

def wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = wd
    if cur: lines.append(cur)
    return lines

def text_block(d, xy, text, font, fill, maxw, lh):
    x, y = xy
    for ln in wrap(d, text, font, maxw):
        d.text((x, y), ln, font=font, fill=fill); y += lh
    return y

def base(kicker):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    d.rounded_rectangle((X0, 90, X0 + 62, 152), 14, fill=NAVY)
    f = serif(26, 900); cx = X0 + 31
    tw = d.textlength("c&c", font=f); x = cx - tw / 2
    for ch, col in (("c", WHITE), ("&", PEACH), ("c", WHITE)):
        d.text((x, 104), ch, font=f, fill=col); x += d.textlength(ch, font=f)
    d.text((X0 + 78, 98), "Cue & Care", font=serif(38, 700), fill=NAVY)
    d.text((X0, 250), kicker, font=inter(30, "Bold"), fill=TEAL)
    return im, d

def options(d, y, opts, ans=None):
    f = inter(42, "SemiBold"); maxw = X1 - X0 - 140
    for i, o in enumerate(opts):
        lines = wrap(d, o, f, maxw); h = 56 * len(lines) + 56
        state = None if ans is None else (i == ans)
        fill = CARD if state is None else (TEAL if state else (236, 243, 244))
        tcol = NAVY if state is None else (WHITE if state else MUTED)
        d.rounded_rectangle((X0, y, X1, y + h), 22, fill=fill)
        cfill = PEACH if (state is None or state) else (220, 228, 230)
        d.ellipse((X0 + 28, y + h / 2 - 32, X0 + 92, y + h / 2 + 32), fill=cfill)
        L = "ABCD"[i]; lf = inter(36, "Bold")
        d.text((X0 + 60 - d.textlength(L, font=lf) / 2, y + h / 2 - 24), L, font=lf, fill=NAVY)
        ty = y + 28
        for ln in lines: d.text((X0 + 120, ty), ln, font=f, fill=tcol); ty += 56
        y += h + 22
    return y

def why_box(d, y, label, text):
    f = inter(38, "Medium"); lines = wrap(d, text, f, X1 - X0 - 80)
    h = 100 + 52 * len(lines)
    d.rounded_rectangle((X0, y, X1, y + h), 26, fill=NAVY)
    d.text((X0 + 40, y + 32), label, font=inter(28, "Bold"), fill=PEACH)
    ty = y + 82
    for ln in lines: d.text((X0 + 40, ty), ln, font=f, fill=WHITE); ty += 52
    return y + h

def save_cta(d, y):
    d.text((X0, y), "save this for exam day", font=script(60), fill=INK2)

# ---------- scenes per format ----------
def scenes_first(it):
    a, d = base("NCLEX PRIORITIZATION")
    y = text_block(d, (X0, 310), "Who do you see FIRST?", serif(96), NAVY, X1 - X0, 108) + 30
    y = options(d, y, it["opts"])
    d.text((X0, min(y + 30, 1480)), "answer in 5 seconds", font=script(58), fill=INK2)
    b, d2 = base("NCLEX PRIORITIZATION")
    y = text_block(d2, (X0, 310), "Who do you see FIRST?", serif(96), NAVY, X1 - X0, 108) + 30
    y = options(d2, y, it["opts"], it["ans"])
    why_box(d2, y + 10, "WHY", it["why"])
    return [(a, 6.0, True), (b, 6.0, False)]

def scenes_quiz(it):
    def draw(ans):
        im, d = base("NCLEX QUICK QUIZ")
        y = text_block(d, (X0, 310), it["q"], serif(78), NAVY, X1 - X0, 92) + 36
        y = options(d, y, it["opts"], ans)
        return im, d, y
    a, d, y = draw(None)
    d.text((X0, min(y + 30, 1480)), "answer in 5 seconds", font=script(58), fill=INK2)
    b, d2, y2 = draw(it["ans"]); why_box(d2, y2 + 10, "RATIONALE", it["why"])
    return [(a, 6.0, True), (b, 5.5, False)]

def scenes_myth(it):
    a, d = base("NCLEX MYTH OR FACT?")
    d.text((X0, 330), "MYTH", font=serif(150), fill=PEACH)
    text_block(d, (X0, 540), f"“{it['myth']}”", serif(80, 600), NAVY, X1 - X0, 96)
    yy = 540 + 96 * len(wrap(d, f"\u201c{it['myth']}\u201d", serif(80, 600), X1 - X0)) + 60
    d.text((X0, yy), "true or false?", font=script(62), fill=INK2)
    b, d2 = base("NCLEX MYTH OR FACT?")
    d2.text((X0, 330), "MYTH", font=serif(70), fill=MUTED)
    y = text_block(d2, (X0, 430), it["myth"], inter(38, "Medium"), MUTED, X1 - X0, 52) + 50
    d2.text((X0, y), "FACT", font=serif(150), fill=TEAL)
    y = text_block(d2, (X0, y + 200), it["fact"], serif(68, 600), NAVY, X1 - X0, 84)
    save_cta(d2, min(y + 50, 1480))
    return [(a, 4.5, False), (b, 6.5, False)]

def scenes_trick(it):
    out = []
    for k in range(len(it["lines"]) + 1):
        im, d = base("NCLEX MEMORY TRICK")
        y = text_block(d, (X0, 310), it["title"], serif(64, 700), NAVY, X1 - X0, 78) + 30
        y = text_block(d, (X0, y), it["mn"], serif(118 if len(it["mn"]) < 12 else 84), TEAL, X1 - X0, 130 if len(it["mn"]) < 12 else 96) + 50
        f = inter(44, "SemiBold")
        for ln in it["lines"][:k]:
            d.rounded_rectangle((X0, y, X0 + 12, y + 56), 6, fill=PEACH)
            y = text_block(d, (X0 + 40, y), ln, f, NAVY, X1 - X0 - 40, 58) + 26
        if k == len(it["lines"]): save_cta(d, min(y + 40, 1480))
        out.append((im, 1.4 if k == 0 else (4.0 if k == len(it["lines"]) else 1.3), False))
    return out

FMT = {"first": scenes_first, "quiz": scenes_quiz, "myth": scenes_myth, "trick": scenes_trick}

def encode(png, dur, timer, out):
    tmp = out + ".part.mp4"
    if timer:
        cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", png,
               "-f", "lavfi", "-i", f"color=c=0x1f2a3d:s=1080x10:r=30:d={dur}",
               "-filter_complex", f"[0:v]loop=-1:1,trim=duration={dur},setpts=PTS-STARTPTS[b];"
               f"[b][1:v]overlay=x='-W*t/{dur}':y=200:eval=frame,format=yuv420p", "-t", str(dur)] + ENC + [tmp]
    else:
        cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", png,
               "-vf", f"format=yuv420p,loop=-1:1,trim=duration={dur}", "-t", str(dur)] + ENC + [tmp]
    subprocess.run(cmd, check=True); os.replace(tmp, out)

def render(fmt, it, outdir):
    final = os.path.join(outdir, f"{it['id']}.mp4")
    with tempfile.TemporaryDirectory() as td:
        parts = []
        for n, (im, dur, timer) in enumerate(FMT[fmt](it)):
            png = f"{td}/s{n}.png"; im.save(png)
            mp = f"{td}/s{n}.mp4"; encode(png, dur, timer, mp); parts.append(mp)
        lst = f"{td}/l.txt"; open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
        tmp = final + ".part.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "64k", "-shortest", "-movflags", "+faststart", tmp], check=True)
        os.replace(tmp, final)
    return final

def frames(fmt, it, outdir):
    for n, (im, _, _) in enumerate(FMT[fmt](it)): im.save(os.path.join(outdir, f"{it['id']}-s{n}.jpg"), quality=88)

if __name__ == "__main__":
    data = json.load(open(os.path.join(HERE, "content.json")))
    outdir, ids = sys.argv[1], set(sys.argv[2:])
    mode = os.environ.get("MODE", "video")
    os.makedirs(outdir, exist_ok=True)
    jobs = [(f, it) for f, items in data.items() for it in items if not ids or it["id"] in ids]
    from concurrent.futures import ProcessPoolExecutor
    fn = frames if mode == "frames" else render
    with ProcessPoolExecutor(8) as ex:
        for r in ex.map(fn, [j[0] for j in jobs], [j[1] for j in jobs], [outdir] * len(jobs)): pass
    print("done", len(jobs))
