"""Generate an original, royalty-free lo-fi background bed with numpy.

Every track is synthesised from scratch (pads, bass, soft drums), so APG owns it outright.
A seed picks tempo, key and progression so each video gets a different track.
"""
import numpy as np
import wave

SR = 44100

PROGRESSIONS = [
    [(0, "m"), (8, "M"), (3, "M"), (10, "M")],   # i - VI - III - VII
    [(0, "m"), (5, "m"), (8, "M"), (7, "M")],    # i - iv - VI - V
    [(0, "M"), (9, "m"), (5, "M"), (7, "M")],    # I - vi - IV - V
    [(0, "m7"), (5, "m7"), (10, "M7"), (3, "M7")],
]
CHORD = {"m": [0, 3, 7], "M": [0, 4, 7], "m7": [0, 3, 7, 10], "M7": [0, 4, 7, 11]}


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):  # small arrays only (per-hit), fine
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def lowpass_fast(x, cutoff, passes=2):
    # cheap moving-average low-pass for long signals
    n = max(1, int(SR / cutoff / 2))
    k = np.ones(n) / n
    for _ in range(passes):
        x = np.convolve(x, k, mode="same")
    return x


def pad_note(f, dur, rng):
    t = np.arange(int(dur * SR)) / SR
    detune = [1.0, 1.003, 0.997]
    s = sum(np.sin(2 * np.pi * f * d * t + rng.uniform(0, 6.28)) for d in detune)
    s += 0.3 * sum(np.sin(2 * np.pi * 2 * f * d * t) for d in detune)
    att, rel = 0.6, 0.8
    env = np.minimum(1, t / att) * np.minimum(1, (dur - t) / rel).clip(0)
    return s * env


def kick(rng):
    d = 0.35
    t = np.arange(int(d * SR)) / SR
    f = 50 + 70 * np.exp(-t * 25)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 9)


def snare(rng):
    d = 0.22
    t = np.arange(int(d * SR)) / SR
    n = rng.standard_normal(len(t))
    n = n - lowpass(n, 1800)
    return (0.6 * n + 0.3 * np.sin(2 * np.pi * 190 * t)) * np.exp(-t * 18)


def hat(rng):
    d = 0.06
    t = np.arange(int(d * SR)) / SR
    n = rng.standard_normal(len(t))
    n = n - lowpass(n, 6000)
    return n * np.exp(-t * 60)


def add(buf, sig, start):
    s = int(start * SR)
    e = min(len(buf), s + len(sig))
    if s < len(buf):
        buf[s:e] += sig[: e - s]


def make_track(duration, seed=0, path="music.wav", style="lofi"):
    rng = np.random.default_rng(seed)
    if style != "lofi":
        mix = STYLES[style](duration, rng, seed)
        return _write(mix, duration, path, rng)
    bpm = rng.choice([78, 82, 86, 90])
    root = 57 + int(rng.choice([0, 2, 3, 5, -2]))  # around A3
    prog = PROGRESSIONS[seed % len(PROGRESSIONS)]
    beat = 60 / bpm
    bar = 4 * beat
    n = int((duration + 2) * SR)
    pads, bass, drums = np.zeros(n), np.zeros(n), np.zeros(n)

    k, sn, hh = kick(rng), snare(rng), hat(rng)
    t0, ci = 0.0, 0
    while t0 < duration + 2:
        off, q = prog[ci % len(prog)]
        chord_dur = 2 * bar
        for iv in CHORD[q]:
            add(pads, pad_note(hz(root + off + iv), chord_dur + 0.6, rng) * 0.12, t0)
        bn = hz(root + off - 12)
        for b in range(8):
            if b % 4 in (0, 2) or rng.random() < 0.25:
                bt = np.arange(int(beat * 0.9 * SR)) / SR
                add(bass, np.sin(2 * np.pi * bn * bt) * np.exp(-bt * 2.5) * 0.35, t0 + b * beat)
        for b in range(8):
            add(drums, k * 0.55, t0 + b * beat) if b % 2 == 0 else add(drums, sn * 0.22, t0 + b * beat)
            for h in range(2):
                add(drums, hh * (0.10 if h == 0 else 0.06), t0 + b * beat + h * beat / 2 + rng.uniform(0, 0.012))
        t0 += chord_dur
        ci += 1

    pads = lowpass_fast(pads, 2500)
    mix = pads + bass + drums
    # vinyl-ish noise bed for lo-fi texture
    mix += lowpass_fast(rng.standard_normal(n), 3000) * 0.004
    return _write(mix, duration, path, rng)


def _write(mix, duration, path, rng):
    mix = mix[: int(duration * SR)]
    fade = int(1.5 * SR)
    mix[:int(0.5 * SR)] *= np.linspace(0, 1, int(0.5 * SR))
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.8
    # gentle stereo width
    left = mix
    right = np.roll(mix, int(0.012 * SR))
    st = (np.stack([left, right], axis=1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(st.tobytes())
    return path


# ---------------- reggae / reggaeton ----------------

def skank(freqs, dur=0.14):
    """short choppy offbeat chord stab (guitar/organ 'skank')"""
    t = np.arange(int(dur * SR)) / SR
    s = np.zeros_like(t)
    for f in freqs:
        ph = 2 * np.pi * f * t
        s += np.sign(np.sin(ph)) * 0.25 + np.sin(2 * ph) * 0.35 + np.sin(ph) * 0.5  # bright square-ish
    s = s - lowpass_fast(s, 700, 1)  # thin out lows
    s = lowpass_fast(s, 3500, 1)
    return s * np.exp(-t * 28) * np.minimum(1, t / 0.004)


def organ_bubble(freqs, dur=0.09):
    t = np.arange(int(dur * SR)) / SR
    s = sum(np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t) for f in freqs)
    return s * np.exp(-t * 30) * np.minimum(1, t / 0.003)


def dub_bass(f, dur):
    t = np.arange(int(dur * SR)) / SR
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    s = np.tanh(1.6 * s)
    env = np.minimum(1, t / 0.01) * np.exp(-t * 1.6) * np.minimum(1, (dur - t) / 0.03).clip(0)
    return s * env


def rim(rng):
    t = np.arange(int(0.08 * SR)) / SR
    n = rng.standard_normal(len(t)); n = n - lowpass(n, 2500)
    return (0.5 * n + np.sin(2 * np.pi * 1700 * t)) * np.exp(-t * 55)


def clap(rng):
    t = np.arange(int(0.18 * SR)) / SR
    n = rng.standard_normal(len(t)); n = n - lowpass(n, 1200)
    env = np.exp(-t * 22) * (1 + 0.6 * ((t % 0.012) < 0.004) * (t < 0.03))
    return n * env


def sub_808(f, dur):
    t = np.arange(int(dur * SR)) / SR
    fr = f * (1 + 0.6 * np.exp(-t * 30))
    s = np.tanh(1.3 * np.sin(2 * np.pi * np.cumsum(fr) / SR))
    return s * np.exp(-t * 2.2) * np.minimum(1, (dur - t) / 0.03).clip(0)


REGGAE_PROGS = [[(0, "M"), (5, "M"), (7, "M"), (5, "M")],      # I IV V IV
                [(0, "m"), (5, "m"), (0, "m"), (7, "m")],      # i iv i v (roots)
                [(0, "M"), (9, "m"), (5, "M"), (7, "M")]]
TON_PROGS = [[(0, "m"), (8, "M"), (3, "M"), (10, "M")],        # i VI III VII (classic)
             [(0, "m7"), (5, "m7"), (8, "M7"), (7, "m")]]


def reggae(duration, rng, seed):
    bpm = float(rng.choice([70, 74, 78]))
    beat = 60 / bpm; bar = 4 * beat
    root = 52 + int(rng.choice([0, 2, 5, 7]))  # E3-ish
    prog = REGGAE_PROGS[seed % len(REGGAE_PROGS)]
    n = int((duration + 2) * SR)
    gtr, org, bass, drums, pads = (np.zeros(n) for _ in range(5))
    k, r, hh = kick(rng), rim(rng), hat(rng)
    swing = 0.06 * beat
    t0, ci = 0.0, 0
    # simple melodic bass figure (in scale degrees of chord) per bar: (beat pos, semis, len)
    figs = [[(0, 0, 0.9), (1.5, 7, 0.4), (2, 12, 0.5), (2.75, 10, 0.25), (3, 7, 0.8)],
            [(0, 0, 1.4), (1.75, 3, 0.25), (2, 5, 0.9), (3.5, 7, 0.4)]]
    while t0 < duration + 2:
        off, q = prog[ci % len(prog)]
        tones = [hz(root + 12 + off + iv) for iv in CHORD[q]]
        for i, iv in enumerate(CHORD[q]):
            add(pads, pad_note(hz(root + 12 + off + iv), bar + 0.4, rng) * 0.035, t0)
        for b in range(4):  # skank on the 'and' of every beat
            add(gtr, skank(tones) * 0.30, t0 + b * beat + beat / 2 + swing)
            for sub in (0.25, 0.75):  # organ bubble 16ths
                add(org, organ_bubble(tones) * 0.06, t0 + b * beat + sub * beat + (swing if sub == 0.75 else 0))
        fig = figs[(ci + seed) % len(figs)]
        for pos, semi, ln in fig:
            add(bass, dub_bass(hz(root - 12 + off + semi), ln * beat) * 0.42, t0 + pos * beat)
        add(drums, k * 0.6, t0 + 2 * beat)          # one drop: kick + rim on beat 3
        add(drums, r * 0.32, t0 + 2 * beat)
        for b in range(4):
            for sub in range(3):  # triplet hats
                add(drums, hh * (0.08 if sub == 0 else 0.045), t0 + b * beat + sub * beat / 3)
        if rng.random() < 0.3:
            add(drums, r * 0.15, t0 + 3.5 * beat + swing)
        t0 += bar; ci += 1
    mix = gtr + org + lowpass_fast(bass, 900) + drums + lowpass_fast(pads, 2000)
    # dub-style echo on the skank
    d = int(beat * 0.75 * SR)
    echo = np.zeros(n); echo[d:] = gtr[:-d] * 0.28; echo[2 * d:] += gtr[:-2 * d] * 0.12
    return mix + lowpass_fast(echo, 2500)


def reggaeton(duration, rng, seed):
    bpm = float(rng.choice([88, 92, 95]))
    beat = 60 / bpm; bar = 4 * beat; six = beat / 4
    root = 50 + int(rng.choice([0, 2, 3, 5]))
    prog = TON_PROGS[seed % len(TON_PROGS)]
    n = int((duration + 2) * SR)
    pads, pluck, bass, drums = (np.zeros(n) for _ in range(4))
    k, cl, hh = kick(rng), clap(rng), hat(rng)
    t0, ci = 0.0, 0
    while t0 < duration + 2:
        off, q = prog[ci % len(prog)]
        for iv in CHORD[q]:
            add(pads, pad_note(hz(root + 12 + off + iv), bar + 0.5, rng) * 0.09, t0)
        tones = [hz(root + 24 + off + iv) for iv in CHORD[q]]
        for i, pos in enumerate([0, 3, 6, 8, 11, 14]):  # soft plucked arpeggio on dembow grid
            t = np.arange(int(0.25 * SR)) / SR
            f = tones[i % len(tones)]
            add(pluck, (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 14) * 0.10, t0 + pos * six)
        for b in range(4):  # dembow: kick every beat, snare/clap on 4th & 7th 16th of each half-bar
            add(drums, k * 0.6, t0 + b * beat)
        for pos in (3, 6, 11, 14):
            add(drums, cl * 0.20, t0 + pos * six)
        for pos in range(0, 16, 2):
            add(drums, hh * (0.07 if pos % 4 == 2 else 0.04), t0 + pos * six)
        add(bass, sub_808(hz(root - 12 + off), 1.5 * beat) * 0.45, t0)
        add(bass, sub_808(hz(root - 12 + off), 1.5 * beat) * 0.38, t0 + 2 * beat)
        t0 += bar; ci += 1
    return lowpass_fast(pads, 2200) + pluck + bass + drums


STYLES = {"reggae": reggae, "reggaeton": reggaeton}


if __name__ == "__main__":
    import sys
    make_track(float(sys.argv[1]) if len(sys.argv) > 1 else 30, int(sys.argv[2]) if len(sys.argv) > 2 else 0,
               sys.argv[3] if len(sys.argv) > 3 else "music.wav")
