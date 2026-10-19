"""Render an APG short-form video from a script JSON.

usage: python render/render.py scripts/<name>.json videos/<name>.mp4 [--no-voice]

Each scene has a voiceover line ("vo"). With edge-tts available the line is spoken and the
scene lasts as long as the voice; otherwise (--no-voice) durations are estimated.
An original background track is generated per video (render/music.py) and ducked under the voice.
"""
import asyncio, json, os, re, subprocess, sys, tempfile, wave, math
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from music import make_track

W, H, FPS = 1080, 1920, 30
DARK, GREEN, LIME, GOLD, ORANGE, BROWN = "#14260F", "#2D6E2D", "#8DB84A", "#D4A055", "#C0622A", "#7B3F1A"
CREAM, MUTED = "#F6F1E7", "#D8E3CF"
FONT_DIR = os.environ.get("APG_FONTS", os.path.join(os.path.dirname(__file__), "fonts"))
FB = os.path.join(FONT_DIR, "Poppins-Bold.ttf")
FR = os.path.join(FONT_DIR, "Inter-Regular.otf")
FS = os.path.join(FONT_DIR, "Inter-SemiBold.otf")
_fc = {}


def font(p, s):
    if (p, s) not in _fc:
        _fc[(p, s)] = ImageFont.truetype(p, s)
    return _fc[(p, s)]


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines


def base(bg):
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    for i, c in enumerate([GREEN, LIME, GOLD, ORANGE, BROWN]):
        d.rectangle([i * W / 5, 0, (i + 1) * W / 5, 14], fill=c)
    d.text((80, 1790), "AVENUES PROPERTY GROUP", font=font(FS, 30), fill=LIME if bg != CREAM else GREEN)
    return im, d


def fade_text(im, xy, text, f, fill, a, dy=40):
    """draw text with opacity a (0..1) sliding up by dy*(1-a)"""
    if a <= 0:
        return
    x, y = int(xy[0]), int(xy[1] + dy * (1 - a))
    if a >= 1:
        ImageDraw.Draw(im).text((x, y), text, font=f, fill=fill)
        return
    l, t, r, b = f.getbbox(text)
    layer = Image.new("RGBA", (r + 4, b + 4), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((0, 0), text, font=f, fill=fill)
    alpha = layer.split()[3].point(lambda v: int(v * a))
    layer.putalpha(alpha)
    im.paste(layer, (x, y), layer)


def block(im, d, y, text, f, fill, t, start, gap=10, stagger=0.12, maxw=920):
    for i, ln in enumerate(wrap(d, text, f, maxw)):
        fade_text(im, (80, y), ln, f, fill, ease((t - start - i * stagger) / 0.45))
        y += f.size + gap
    return y


# ---------- scene painters: (scene, t_local, dur) -> Image ----------

def s_hook(sc, t, dur):
    im, d = base(DARK)
    y = 520
    fade_text(im, (80, y), sc["kicker"].upper(), font(FS, 38), GOLD, ease(t / 0.4)); y += 95
    y = block(im, d, y, sc["headline"], font(FB, 96), "white", t, 0.25) + 50
    block(im, d, y, sc.get("sub", ""), font(FR, 46), MUTED, t, 0.9)
    return im


def s_bars(sc, t, dur):
    im, d = base(CREAM)
    y = 150
    for ln in wrap(d, sc["title"], font(FB, 64), 920):
        d.text((80, y), ln, font=font(FB, 64), fill=DARK); y += 70
    y += 50
    rows = sc["rows"]
    rowh = min(120, (1580 - y) // len(rows))
    vmax = max(v for _, v in rows)
    hi = sc.get("highlight", 1)
    col = {"green": GREEN, "lime": LIME, "gold": GOLD}[sc.get("color", "green")]
    txtcol = {GREEN: GREEN, LIME: GREEN, GOLD: BROWN}[col]
    span = max(0.6, min(dur * 0.55, 0.28 * len(rows)))
    step = span / len(rows)
    for i, (lab, v) in enumerate(rows):
        yy = y + i * rowh
        p = ease((t - 0.2 - i * step) / 0.55)
        c = ORANGE if i < hi else col
        fade_text(im, (80, yy), lab, font(FS, 34), DARK, ease((t - 0.1 - i * step) / 0.3), dy=12)
        bw = int(620 * v / vmax * p)
        if p > 0:
            d.rounded_rectangle([80, yy + 44, 80 + max(bw, 8), yy + rowh - 22], 8, fill=c)
        if p > 0.6:
            d.text((80 + bw + 18, yy + 40), sc["fmt"].format(v * min(1, p / 0.95)) if p < 1 else sc["fmt"].format(v),
                   font=font(FB, 38), fill=ORANGE if i < hi else txtcol)
    if sc.get("note"):
        y2 = 1630
        for ln in wrap(d, sc["note"], font(FR, 26), 920):
            d.text((80, y2), ln, font=font(FR, 26), fill="#6B6B6B"); y2 += 32
    return im


def s_stat(sc, t, dur):
    im, d = base(DARK)
    y = 480
    fade_text(im, (80, y), sc["kicker"].upper(), font(FS, 38), GOLD, ease(t / 0.4)); y += 95
    big = sc["big"]
    if "count" in sc:  # animate the first number
        a, b, fmt = sc["count"]
        v = a + (b - a) * ease(t / 1.0)
        big = big.replace("{n}", fmt.format(v))
    f = font(FB, 92)
    for ln in wrap(d, big, f, 920):
        fade_text(im, (80, y), ln, f, "white", ease((t - 0.15) / 0.4)); y += f.size + 10
    y += 50
    for i, para in enumerate(sc.get("body", [])):
        y = block(im, d, y, para, font(FR, 44), MUTED, t, 0.8 + i * 0.9) + 30
    return im


def s_cta(sc, t, dur):
    im, d = base(GREEN)
    y = 600
    y = block(im, d, y, sc["headline"], font(FB, 84), "white", t, 0.0) + 60
    y = block(im, d, y, sc.get("sub", "Free APG Deal Analyser — in £, $ or J$."), font(FR, 46), "#EAF3DF", t, 0.5) + 70
    p = ease((t - 1.0) / 0.4)
    if p > 0:
        pulse = 1 + 0.03 * math.sin(max(0, t - 1.4) * 5)
        w2 = int(460 * pulse * p)
        cx = W // 2
        d.rounded_rectangle([cx - w2, y, cx + w2, y + 130], 65, fill=GOLD)
        f = font(FB, 50)
        tx = sc.get("button", "Link in bio")
        if p > 0.7:
            d.text((cx - d.textlength(tx, font=f) / 2, y + 30), tx, font=f, fill=DARK)
    return im


PAINT = {"hook": s_hook, "bars": s_bars, "stat": s_stat, "cta": s_cta}


# ---------- audio ----------

def wav_dur(p):
    with wave.open(p) as w:
        return w.getnframes() / w.getframerate()


LEXICON = json.load(open(os.path.join(os.path.dirname(__file__), "lexicon.json")))


def speakable(text):
    """apply pronunciation fixes (render/lexicon.json) before text-to-speech"""
    for k, v in LEXICON.items():
        text = re.sub(r"(?<![A-Za-z])" + re.escape(k), v, text)
    return text


async def tts_all(lines, voice, rate, outdir, voices=None):
    """voices: optional per-line voice overrides (used for voice sample reels)"""
    import edge_tts
    paths = []
    for i, ln in enumerate(lines):
        mp3 = os.path.join(outdir, f"vo{i}.mp3")
        v = (voices or [None] * len(lines))[i] or voice
        try:
            await edge_tts.Communicate(speakable(ln), v, rate=rate).save(mp3)
        except Exception as e:  # unknown voice etc. -> fall back so the reel still renders
            print(f"voice {v} failed ({e}); using {voice}", file=sys.stderr)
            await edge_tts.Communicate(speakable("This voice isn't available. " + ln), voice, rate=rate).save(mp3)
        wavp = mp3[:-4] + ".wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", "44100", "-ac", "1", wavp], check=True)
        paths.append(wavp)
    return paths


def main():
    src, out = sys.argv[1], sys.argv[2]
    no_voice = "--no-voice" in sys.argv
    S = json.load(open(src))
    scenes = S["scenes"]
    tmp = tempfile.mkdtemp()
    lead, tail = 0.35, 0.55

    if no_voice:
        durs = [max(sc.get("min", 3.0), len(sc["vo"].split()) / 2.7 + lead + tail) for sc in scenes]
        vo_wavs = None
    else:
        vo_wavs = asyncio.run(tts_all([sc["vo"] for sc in scenes], S.get("voice", "en-GB-SoniaNeural"),
                                      S.get("rate", "+6%"), tmp, [sc.get("voice") for sc in scenes]))
        durs = [max(sc.get("min", 2.5), wav_dur(p) + lead + tail) for p, sc in zip(vo_wavs, scenes)]
    total = sum(durs)

    # voice track: each line placed at its scene start + lead
    voice = os.path.join(tmp, "voice.wav")
    if vo_wavs:
        inputs, filt, t0 = [], [], 0.0
        for i, (p, du) in enumerate(zip(vo_wavs, durs)):
            inputs += ["-i", p]
            filt.append(f"[{i}]adelay={int((t0 + lead) * 1000)}|{int((t0 + lead) * 1000)}[a{i}]")
            t0 += du
        filt.append("".join(f"[a{i}]" for i in range(len(vo_wavs))) + f"amix=inputs={len(vo_wavs)}:normalize=0,apad=whole_dur={total}[v]")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt),
                        "-map", "[v]", "-ar", "44100", "-ac", "1", voice], check=True)

    music = make_track(total, seed=S.get("music_seed", 0), path=os.path.join(tmp, "music.wav"),
                       style=S.get("music_style", "reggaeton"))

    # frames -> ffmpeg
    silent = os.path.join(tmp, "video.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                           "-crf", "20", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    XF = 0.25  # crossfade between scenes
    frames = int(total * FPS)
    starts = [sum(durs[:i]) for i in range(len(durs))]
    for fi in range(frames):
        t = fi / FPS
        k = max(i for i, s in enumerate(starts) if s <= t)
        img = PAINT[scenes[k]["type"]](scenes[k], t - starts[k], durs[k])
        if k + 1 < len(scenes) and starts[k + 1] - t < XF:
            nxt = PAINT[scenes[k + 1]["type"]](scenes[k + 1], 0, durs[k + 1])
            img = Image.blend(img, nxt, 1 - (starts[k + 1] - t) / XF)
        ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait()

    # mix: music ducked under voice
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    mvol = S.get("music_volume", 0.22)
    if vo_wavs:
        fc = (f"[1]volume={mvol}[m];[2]asplit=2[vs][vm];[m][vs]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[md];"
              f"[vm]loudnorm=I=-16:TP=-1.5[vn];[vn][md]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[a]")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", music, "-i", voice,
               "-filter_complex", fc, "-map", "0:v", "-map", "[a]"]
    else:
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", music,
               "-filter_complex", f"[1]volume={mvol * 2.2}[a]", "-map", "0:v", "-map", "[a]"]
    subprocess.run(cmd + ["-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
    print(f"{out}: {total:.1f}s, {len(scenes)} scenes")


if __name__ == "__main__":
    main()
