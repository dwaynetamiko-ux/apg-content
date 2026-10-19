"""APG house-style video renderer (matches the Pictory-made posts on the TikTok page).

usage: python render/house.py scripts/<name>.json videos/<name>.mp4 [--no-voice]

Scene types (script["scenes"][i]["type"]):
  title  - stock clip on the top half, white panel with kicker + bold title
  stat   - full-bleed darkened stock clip, huge number (counts up) + one-line description
  broll  - full-bleed stock clip with word-by-word captions
  app    - Deal Analyser screen recording (clips/manifest.json) centred on black, with captions
  end    - white end card: APG logo, URL, "Link in bio"
Every scene has "vo" (voiceover). Stock footage comes from the Pixabay video API using the
scene's "q" search terms (env PIXABAY_API_KEY). Captions are timed to the voice word by word.
"""
import asyncio, json, os, random, re, subprocess, sys, tempfile, urllib.error, urllib.parse, urllib.request, wave, zlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from music import make_track

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(HERE)
FONT_DIR = os.path.join(HERE, "fonts")
FB = os.path.join(FONT_DIR, "Poppins-Bold.ttf")
FR = os.path.join(FONT_DIR, "Inter-Regular.otf")
FS = os.path.join(FONT_DIR, "Inter-SemiBold.otf")
LOGO = os.path.join(HERE, "assets", "apg-logo.png")
CLIPS = os.environ.get("APG_CLIPS_DIR", os.path.join(ROOT, "clips_dec"))
CACHE = os.environ.get("APG_MEDIA_CACHE", os.path.join(ROOT, ".media_cache"))
LEXICON = json.load(open(os.path.join(HERE, "lexicon.json")))
URL_TEXT = "avenues-deal-analyser.netlify.app"
_fc = {}


def font(p, s):
    if (p, s) not in _fc:
        _fc[(p, s)] = ImageFont.truetype(p, s)
    return _fc[(p, s)]


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def speakable(text):
    for k, v in LEXICON.items():
        text = re.sub(r"(?<![A-Za-z])" + re.escape(k), v, text)
    return text


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


# ---------------------------------------------------------------- stock footage (Pixabay)

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 apg-render"}


def _get(url, timeout=60):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)


def pixabay_clip(query, used, seed):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key or not query:
        return None
    os.makedirs(CACHE, exist_ok=True)
    url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode(
        {"key": key, "q": query, "per_page": 20, "safesearch": "true", "order": "popular"})
    try:
        hits = json.load(_get(url, 30)).get("hits", [])
    except urllib.error.HTTPError as e:
        print(f"pixabay search failed for '{query}': {e} {e.read()[:200]!r}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"pixabay search failed for '{query}': {e}", file=sys.stderr)
        return None
    hits = [h for h in hits if h["id"] not in used and h.get("duration", 0) >= 4]
    if not hits:
        return None
    top = hits[:6]
    random.Random(seed).shuffle(top)
    h = top[0]
    used.add(h["id"])
    v = h["videos"].get("large") or h["videos"].get("medium")
    if not v or not v.get("url"):
        v = h["videos"].get("medium") or h["videos"].get("small")
    path = os.path.join(CACHE, f"pixabay-{h['id']}.mp4")
    if not os.path.exists(path):
        try:
            with _get(v["url"], 120) as r, open(path, "wb") as fh:
                fh.write(r.read())
        except Exception as e:
            print(f"download failed {h['id']}: {e}", file=sys.stderr)
            return None
    print(f"  '{query}' -> pixabay {h['id']} ({h.get('tags','')})", file=sys.stderr)
    return path


def clip_frames(path, dur, w, h, mode="cover", start=0.0, pan=True):
    """yield RGB numpy frames (h, w, 3) of the clip, covering/fitting the box, with slow Ken Burns pan."""
    n = int(round(dur * FPS))
    if path is None:
        # fallback: soft brand gradient
        g = np.linspace(0, 1, h)[:, None, None]
        base = (np.array([20, 38, 15]) * (1 - g) + np.array([45, 110, 45]) * g).astype(np.uint8)
        frame = np.broadcast_to(base, (h, w, 3)).copy()
        for _ in range(n):
            yield frame
        return
    if mode == "cover":
        sw, sh = int(w * 1.12), int(h * 1.12)
        vf = (f"scale={sw}:{sh}:force_original_aspect_ratio=increase,"
              f"crop={w}:{h}:x='(iw-{w})/2+((iw-{w})/2)*0.6*sin(t/{max(dur,1):.2f}*1.57-0.78)':y='(ih-{h})/2',fps={FPS}")
    else:  # fit (screen recordings): scale to width, centre on black, gentle zoom
        vf = (f"scale={w}:-2,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
              f"scale=w='{w}*(1+0.04*t/{max(dur,1):.2f})':h=-2:eval=frame,crop={w}:{h},fps={FPS}")
    cmd = ["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-ss", f"{start:.2f}", "-i", path,
           "-t", f"{dur + 0.5:.2f}", "-vf", vf, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    size = w * h * 3
    last = None
    for _ in range(n):
        buf = p.stdout.read(size)
        if len(buf) == size:
            last = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        if last is None:
            last = np.zeros((h, w, 3), np.uint8)
        yield last
    p.kill()


# ---------------------------------------------------------------- overlays

def captions(img, words, t, y_centre=1560):
    """Pictory-style captions: current phrase on a translucent dark box, spoken words bright."""
    if not words:
        return
    # group into phrases of up to ~2 lines
    d = ImageDraw.Draw(img)
    f = font(FR, 60)
    phrases, cur = [], []
    for w in words:
        cur.append(w)
        if len(" ".join(x[0] for x in cur)) > 30 or w[0].endswith((".", "?", "!", ",")) and len(cur) > 3:
            phrases.append(cur); cur = []
    if cur:
        phrases.append(cur)
    ph = None
    for p in phrases:
        if t >= p[0][1] - 0.05:
            ph = p
    if ph is None or t > ph[-1][2] + 0.6:
        return
    # lay out into lines
    lines, line = [], []
    for w in ph:
        test = " ".join(x[0] for x in line + [w])
        if line and d.textlength(test, font=f) > 900:
            lines.append(line); line = []
        line.append(w)
    lines.append(line)
    y = y_centre - len(lines) * 70 // 2
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(over)
    for ln in lines:
        text = " ".join(x[0] for x in ln)
        tw = d.textlength(text, font=f)
        x0 = (W - tw) / 2
        od.rectangle([x0 - 14, y - 6, x0 + tw + 14, y + 66], fill=(40, 40, 40, 190))
        x = x0
        for word, ws, we in ln:
            col = (255, 255, 255, 255) if t >= ws else (205, 205, 205, 235)
            od.text((x, y), word, font=f, fill=col)
            x += d.textlength(word + " ", font=f)
        y += 74
    img.paste(over, (0, 0), over)


def centre_text(d, y, text, f, fill, maxw=960, gap=8):
    for ln in wrap(d, text, f, maxw):
        tw = d.textlength(ln, font=f)
        d.text(((W - tw) / 2, y), ln, font=f, fill=fill)
        y += f.size + gap
    return y


def fmt_count(sc, t):
    if "count" not in sc:
        return sc["big"]
    a, b, f = sc["count"]
    return f.format(a + (b - a) * ease(t / 1.1))


# ---------------------------------------------------------------- audio

async def tts_words(text, voice, rate, mp3):
    import edge_tts
    com = edge_tts.Communicate(speakable(text), voice, rate=rate, boundary="WordBoundary")
    bounds = []
    with open(mp3, "wb") as fh:
        async for ch in com.stream():
            if ch["type"] == "audio":
                fh.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                bounds.append((ch["offset"] / 1e7, (ch["offset"] + ch["duration"]) / 1e7))
    return bounds


def align_words(text, bounds, speech_len):
    """map original (display) words to times. Uses boundary times when counts line up, else proportional."""
    orig = text.split()
    spoken = speakable(text).split()
    if bounds and len(bounds) == len(orig) == len(spoken):
        return [(w, s, e) for w, (s, e) in zip(orig, bounds)]
    t0 = bounds[0][0] if bounds else 0.05
    t1 = bounds[-1][1] if bounds else speech_len
    tot = sum(len(w) + 1 for w in orig)
    out, acc = [], 0
    for w in orig:
        s = t0 + (t1 - t0) * acc / tot
        acc += len(w) + 1
        out.append((w, s, t0 + (t1 - t0) * acc / tot))
    return out


def wav_dur(p):
    with wave.open(p) as w:
        return w.getnframes() / w.getframerate()


# ---------------------------------------------------------------- main

def main():
    src, out = sys.argv[1], sys.argv[2]
    no_voice = "--no-voice" in sys.argv
    S = json.load(open(src))
    scenes = S["scenes"]
    tmp = tempfile.mkdtemp()
    lead, tail = 0.3, 0.45
    voice = S.get("voice", "en-GB-SoniaNeural")
    rate = S.get("rate", "+6%")

    vo_wavs, words, durs = [], [], []
    for i, sc in enumerate(scenes):
        if no_voice:
            sl = len(sc["vo"].split()) / 2.7
            vo_wavs.append(None)
            words.append(align_words(sc["vo"], [], sl))
        else:
            mp3 = os.path.join(tmp, f"vo{i}.mp3")
            bounds = asyncio.run(tts_words(sc["vo"], voice, rate, mp3))
            wv = mp3[:-4] + ".wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", "44100", "-ac", "1", wv], check=True)
            sl = wav_dur(wv)
            vo_wavs.append(wv)
            words.append(align_words(sc["vo"], bounds, sl))
        durs.append(max(sc.get("min", 2.0), sl + lead + tail))
    total = sum(durs)
    starts = [sum(durs[:i]) for i in range(len(durs))]

    # ---- voice track
    voice_wav = os.path.join(tmp, "voice.wav")
    if not no_voice:
        inputs, filt = [], []
        for i, p in enumerate(vo_wavs):
            inputs += ["-i", p]
            ms = int((starts[i] + lead) * 1000)
            filt.append(f"[{i}]adelay={ms}|{ms}[a{i}]")
        filt.append("".join(f"[a{i}]" for i in range(len(vo_wavs))) +
                    f"amix=inputs={len(vo_wavs)}:normalize=0,apad=whole_dur={total}[v]")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt),
                        "-map", "[v]", "-ar", "44100", "-ac", "1", voice_wav], check=True)
        with wave.open(voice_wav) as w:
            sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32767
        act = x[np.abs(x) > 0.01]
        x = np.clip(x * (10 ** (-16 / 20) / max(np.sqrt((act ** 2).mean()) if len(act) else 0.1, 1e-4)), -0.97, 0.97)
        with wave.open(voice_wav, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((x * 32767).astype(np.int16).tobytes())

    # ---- music
    music = os.path.join(tmp, "music.wav")
    style = S.get("music_style", "reggaeton")
    if style.startswith("track:"):
        trk = os.path.join(os.environ.get("APG_MUSIC_DIR", os.path.join(ROOT, "music_dec")), style.split(":", 1)[1] + ".mp3")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-ss", str(S.get("music_start", 0)),
                        "-i", trk, "-t", f"{total:.2f}", "-af",
                        f"loudnorm=I=-17:TP=-2,afade=t=in:d=0.5,afade=t=out:st={max(0, total - 1.5):.2f}:d=1.5",
                        "-ar", "44100", "-ac", "2", music], check=True)
    else:
        make_track(total, seed=S.get("music_seed", 0), path=music, style=style)

    # ---- media per scene
    used, media = set(), []
    for i, sc in enumerate(scenes):
        if sc["type"] == "app":
            p = os.path.join(CLIPS, sc["clip"] + ".mp4")
            media.append(p if os.path.exists(p) else None)
        elif sc["type"] == "end":
            media.append(None)
        else:
            media.append(pixabay_clip(sc.get("q"), used, zlib.crc32(f"{S.get('id')}-{i}".encode())))

    logo = Image.open(LOGO).convert("RGB")
    lw = 640
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)

    # ---- frames
    silent = os.path.join(tmp, "video.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                           "-crf", "20", "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    prev_last = None
    XF = 6  # frames of crossfade from previous scene
    for i, sc in enumerate(scenes):
        typ, dur = sc["type"], durs[i]
        wl = [(w, s + lead, e + lead) for w, s, e in words[i]]
        if typ == "title":
            gen = clip_frames(media[i], dur, W, 960)
        elif typ == "app":
            gen = clip_frames(media[i], dur, W, H, mode="fit", start=sc.get("start", 0))
        elif typ == "end":
            gen = None
        else:
            gen = clip_frames(media[i], dur, W, H)
        n = int(round(dur * FPS))
        for fi in range(n):
            t = fi / FPS
            if typ == "title":
                top = next(gen)
                canvas = np.full((H, W, 3), 255, np.uint8)
                canvas[:960] = top
                img = Image.fromarray(canvas)
                d = ImageDraw.Draw(img)
                a = ease(t / 0.5)
                ky = 1150 + int(30 * (1 - a))
                centre_text(d, ky, sc.get("kicker", ""), font(FS, 40), (60, 60, 60))
                centre_text(d, ky + 80, sc["title"], font(FB, 86), (15, 15, 15), maxw=940, gap=10)
            elif typ == "stat":
                bg = next(gen).astype(np.float32) * 0.5
                img = Image.fromarray(bg.astype(np.uint8))
                d = ImageDraw.Draw(img)
                big = fmt_count(sc, t)
                a = ease(t / 0.4)
                fb = font(FB, 200)
                tw = d.textlength(big, font=fb)
                d.text(((W - tw) / 2, 600 + 40 * (1 - a)), big, font=fb, fill="white")
                if t > 0.35:
                    centre_text(d, 870, sc.get("desc", ""), font(FB, 62), "white", maxw=920, gap=10)
            elif typ == "end":
                img = Image.new("RGB", (W, H), "white")
                d = ImageDraw.Draw(img)
                a = ease(t / 0.6)
                s = 0.9 + 0.1 * a
                lg = logo.resize((int(logo.width * s), int(logo.height * s)), Image.LANCZOS)
                img.paste(lg, ((W - lg.width) // 2, 330 + (logo.height - lg.height) // 2))
                y = 330 + logo.height + 40
                if t > 0.4:
                    y = centre_text(d, y, "Or head to", font(FR, 46), (90, 90, 90))
                    y = centre_text(d, y, URL_TEXT, font(FS, 50), (30, 30, 30)) + 40
                if t > 0.8:
                    pill = "Link in bio"
                    f = font(FB, 56)
                    tw = d.textlength(pill, font=f)
                    d.rounded_rectangle([(W - tw) / 2 - 50, y, (W + tw) / 2 + 50, y + 110], 55, fill="#2D6E2D")
                    d.text(((W - tw) / 2, y + 22), pill, font=f, fill="white")
            else:  # broll / app
                img = Image.fromarray(next(gen))
            if typ in ("broll", "app") or (typ == "end" and sc.get("captions", False)):
                captions(img, wl, t)
            arr = np.asarray(img)
            if prev_last is not None and fi < XF:
                k = (fi + 1) / (XF + 1)
                arr = (prev_last.astype(np.float32) * (1 - k) + arr.astype(np.float32) * k).astype(np.uint8)
            ff.stdin.write(arr.tobytes())
            last = arr
        prev_last = last
    ff.stdin.close(); ff.wait()

    # ---- mux: music ducked under voice
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    mvol = S.get("music_volume", 0.22)
    if not no_voice:
        fc = (f"[1]volume={mvol}[m];[2]asplit=2[vs][vm];[m][vs]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[md];"
              f"[vm][md]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[a]")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", music, "-i", voice_wav,
               "-filter_complex", fc, "-map", "0:v", "-map", "[a]"]
    else:
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", music,
               "-filter_complex", f"[1]volume={mvol * 2.2}[a]", "-map", "0:v", "-map", "[a]"]
    subprocess.run(cmd + ["-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
    print(f"{out}: {total:.1f}s, {len(scenes)} scenes")


if __name__ == "__main__":
    main()
