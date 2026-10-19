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


def make_track(duration, seed=0, path="music.wav"):
    rng = np.random.default_rng(seed)
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


if __name__ == "__main__":
    import sys
    make_track(float(sys.argv[1]) if len(sys.argv) > 1 else 30, int(sys.argv[2]) if len(sys.argv) > 2 else 0,
               sys.argv[3] if len(sys.argv) > 3 else "music.wav")
