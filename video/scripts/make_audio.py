"""Synthesize public/music.wav (upbeat loop) and public/pop.wav (ball pop). No external assets."""
import os, wave
import numpy as np

SR = 44100
here = os.path.dirname(os.path.abspath(__file__))
pub = os.path.join(here, "..", "public")


def save(name, x):
    x = np.clip(x / (np.max(np.abs(x)) + 1e-9) * 0.9, -1, 1)
    with wave.open(os.path.join(pub, name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def hz(midi):
    return 440 * 2 ** ((midi - 69) / 12)


def tone(f, dur, kind="tri", decay=6.0):
    t = np.arange(int(SR * dur)) / SR
    ph = (f * t) % 1
    w = {"tri": 4 * np.abs(ph - 0.5) - 1, "sq": np.sign(np.sin(2 * np.pi * f * t)) * 0.5,
         "sin": np.sin(2 * np.pi * f * t)}[kind]
    env = np.exp(-decay * t) * np.minimum(1, t * 200)
    return w * env


def add(buf, x, at):
    i = int(at * SR); buf[i:i + len(x)] += x[: max(0, len(buf) - i)]


BPM, BARS = 120, 16
beat = 60 / BPM
out = np.zeros(int(SR * beat * 4 * BARS) + SR)
# C - Am - F - G, as (root, chord tones)
prog = [(48, [60, 64, 67, 72]), (45, [57, 60, 64, 69]), (41, [53, 57, 60, 65]), (43, [55, 59, 62, 67])]
for bar in range(BARS):
    root, chord = prog[bar % 4]
    t0 = bar * 4 * beat
    for b in range(4):
        tb = t0 + b * beat
        # kick
        t = np.arange(int(SR * 0.25)) / SR
        add(out, np.sin(2 * np.pi * (50 + 120 * np.exp(-30 * t)) * t) * np.exp(-12 * t) * 1.2, tb)
        # hi-hat on off-beat
        add(out, np.random.randn(int(SR * 0.05)) * np.exp(-80 * np.arange(int(SR * 0.05)) / SR) * 0.15, tb + beat / 2)
        # bass
        add(out, tone(hz(root), beat * 0.9, "tri", 3) * 0.6, tb)
    # arpeggio, 8th notes
    for s in range(8):
        add(out, tone(hz(chord[[0, 1, 2, 3, 2, 1, 2, 3][s]]), beat * 0.45, "sq", 9) * 0.22, t0 + s * beat / 2)
    # pad
    for n in chord[:3]:
        add(out, tone(hz(n), beat * 4, "sin", 0.6) * 0.12, t0)
save("music.wav", out)

t = np.arange(int(SR * 0.18)) / SR
pop = np.sin(2 * np.pi * (300 + 900 * np.exp(-25 * t)) * t) * np.exp(-22 * t)
save("pop.wav", pop)
print("ok", len(out) / SR, "s")
