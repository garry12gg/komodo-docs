#!/usr/bin/env python3
"""Resynthesize the game's SFX from audit.json (grab beeps + win arpeggio)
with the same synthesis as the page (square/triangle oscillators, exp decay)."""
import json
import numpy as np
from scipy import signal

SR = 44100
audit = json.load(open('/workspace/wtf_game/audit.json'))
win_dt = audit['winAt'] - audit['captureStart']
presses = [p['dt'] for p in audit['pressTimes'] if p['kind'] == 'grab']

def osc(freq, dur, wave, vol, t0, total):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if wave == 'square':
        w = np.sign(np.sin(2 * np.pi * freq * t))
    else:  # triangle
        w = signal.sawtooth(2 * np.pi * freq * t, width=0.5)
    env = np.empty(n)
    na = int(0.004 * SR)
    env[:na] = np.linspace(0.0001, 1.0, na)
    env[na:] = np.exp(np.linspace(0, np.log(0.0001), n - na))
    start = int(t0 * SR)
    end = min(start + n, total)
    buf = np.zeros(total)
    if start < end:
        buf[start:end] = (w * env * vol)[:end - start]
    return buf

total = int((win_dt / 1000 + 5.5) * SR) + SR  # win + 5.5s hold + 1s pad
mix = np.zeros(total)

# grab: two square beeps (340 @ t, 520 @ t+70ms), vol 0.07 -> scale x4
for dt in presses:
    t0 = dt / 1000.0
    mix += osc(340, 0.07, 'square', 0.07 * 4, t0, total)
    mix += osc(520, 0.09, 'square', 0.07 * 4, t0 + 0.07, total)

# win: triangle arpeggio 392/523/659/784, 0.16s, 0.13 apart, vol 0.08 -> x4
wt = win_dt / 1000.0
for i, f in enumerate([392, 523, 659, 784]):
    mix += osc(f, 0.16, 'triangle', 0.08 * 4, wt + i * 0.13, total)

# normalize a bit, keep headroom
mix = np.clip(mix, -1, 1)
pcm = (mix * 32767).astype(np.int16)
import wave
with wave.open('/workspace/wtf_game/sfx.wav', 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print('sfx.wav written:', total / SR, 's; grabs:', len(presses), '; win at', wt)
