"""Deterministic render of 'Wrong Tool First' from the page's own clock.

Reads take4/log.json (evlog of ctx.currentTime at every event), places
notes/drums at exactly those audio-clock times, and renders with the
same synthesis as the page (dual detuned oscillators, lowpass 6500,
same envelopes, same drum grid). Audio t=0 == the wrong note.
"""
import json
import sys

import numpy as np
from scipy import signal

sys.path.insert(0, "/workspace/keytar")
from compose2 import EIGHTH, NOTE_DUR, RIFF, LEAD, notes_with_durations

SR = 48000
F16 = EIGHTH / 2       # 16th step for drums (60/112/4)
STEP16 = F16

rng = np.random.default_rng(7)


def freq(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def rbj_lowpass(fc, sr, q=1.0):
    w0 = 2 * np.pi * fc / sr
    alpha = np.sin(w0) / (2 * q)
    cw = np.cos(w0)
    b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
    a = [1 + alpha, -2 * cw, 1 - alpha]
    return b, a


def rbj_bandpass(fc, sr, q=1.0):
    w0 = 2 * np.pi * fc / sr
    alpha = np.sin(w0) / (2 * q)
    cw = np.cos(w0)
    b = [alpha, 0, -alpha]
    a = [1 + alpha, -2 * cw, 1 - alpha]
    return b, a


def rbj_highpass(fc, sr, q=1.0):
    w0 = 2 * np.pi * fc / sr
    alpha = np.sin(w0) / (2 * q)
    cw = np.cos(w0)
    b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
    a = [1 + alpha, -2 * cw, 1 - alpha]
    return b, a


LP = rbj_lowpass(6500, SR)
BP = rbj_bandpass(1900, SR)
HP = rbj_highpass(8000, SR)


def note_buffer(midi, wave, vel, n=SR):  # 1s max like the page (osc.stop(t+1))
    f = freq(midi)
    t = np.arange(n) / SR
    ph1 = 2 * np.pi * f * 2 ** (4 / 1200) * t
    ph2 = 2 * np.pi * f * 1.0035 * 2 ** (-4 / 1200) * t
    if wave == "square":
        o1 = np.sign(np.sin(ph1))
        o2 = np.sign(np.sin(ph2))
    else:  # sawtooth
        o1 = 2 * ((ph1 / (2 * np.pi)) - np.round(ph1 / (2 * np.pi)))
        o2 = 2 * ((ph2 / (2 * np.pi)) - np.round(ph2 / (2 * np.pi)))
    osc = 0.5 * (o1 + o2)
    env = np.empty(n)
    na = int(0.008 * SR)
    env[:na] = np.linspace(0.0001, vel, na)
    nd = int((0.9 - 0.008) * SR)
    if na + nd > n:
        nd = n - na
    env[na:na + nd] = vel * (0.0001 / vel) ** (np.arange(nd) / (nd - 1))
    if na + nd < n:
        env[na + nd:] = 0.0001
    return signal.lfilter(*LP, osc * env)


def kick_buffer():
    n = int(0.2 * SR)
    t = np.arange(n) / SR
    f = 48 + (150 - 48) * np.exp(-t / 0.04)
    phase = 2 * np.pi * np.cumsum(f) / SR
    osc = np.sin(phase)
    g = np.empty(n)
    nd = int(0.18 * SR)
    g[:nd] = 0.5 * (0.0001 / 0.5) ** (np.arange(nd) / (nd - 1))
    g[nd:] = 0.0001
    return signal.lfilter(*LP, osc * g)


def noise_buffer(dur, shape_pow, filt, vol):
    n = int(dur * SR)
    x = (rng.random(n) * 2 - 1) * (1 - np.arange(n) / n) ** shape_pow
    g = np.empty(n)
    g[:n] = vol * (0.0001 / vol) ** (np.arange(n) / (n - 1))
    return signal.lfilter(*filt, x * g)


def snare_buffer():
    return noise_buffer(0.15, 2, BP, 0.35)


def hat_buffer(vol):
    return noise_buffer(0.05, 3, HP, vol)


def add(buf, out, at):
    i = int(at * SR)
    if i >= len(out):
        return
    j = min(len(out), i + len(buf))
    out[i:j] += buf[:j - i]


def main():
    log = json.load(open("/workspace/keytar/take4/log.json"))
    ev = {e["name"]: e for e in log["evlog"]}
    evs = log["evlog"]

    def t_of(name, k=0):
        hits = [e for e in evs if e["name"] == name]
        return hits[k]["ctx"]

    t0 = ev["press_wrong"]["ctx"]  # audio t=0 == the wrong note
    A = lambda c: c - t0

    total = 24.0
    out = np.zeros(int(total * SR))

    # ---- drums: grid from drums click +0.05 to drums-off click ----
    kick = kick_buffer()
    snare = snare_buffer()
    hat06 = hat_buffer(0.06)
    hat13 = hat_buffer(0.13)
    t = A(ev["click_drums"]["ctx"]) + 0.05
    end = A(ev["click_drums_off"]["ctx"])
    step = 0
    while t < end:
        s = step % 16
        if s % 4 == 0:
            add(kick, out, t)
        if s % 2 == 0:
            add(hat13 if s % 8 == 4 else hat06, out, t)
        if s == 4 or s == 12:
            add(snare, out, t)
        step += 1
        t += F16

    # ---- wrong note (square, default voice) ----
    add(note_buffer(ev["press_wrong"]["midi"], "square", 0.3), out, 0.0)

    # ---- saw click blip: the tool seats into its slot ----
    add(note_buffer(60, "sawtooth", 0.18), out, A(ev["click_saw"]["ctx"]))

    # ---- riff pass 1 (live, saw, vel 0.3) ----
    riff_pairs = notes_with_durations(RIFF)
    riff_ctxs = [e["ctx"] for e in evs if e["name"] == "press_riff"]
    for (m, d), c in zip(riff_pairs, riff_ctxs):
        add(note_buffer(m, "sawtooth", 0.3), out, A(c))

    # ---- loop playback (square, vel 0.26), from the page's own math ----
    loop_ev = ev["loop_click"]
    startT = loop_ev["startT"]
    ev_t0 = loop_ev["ev_t0"]
    lastT = ev_t0 + (len(RIFF) - 1) * EIGHTH + NOTE_DUR
    cycle = np.ceil((lastT + 0.9) / STEP16) * STEP16
    loop_off_t = A(ev["click_loop_off"]["ctx"])
    p = 0
    while True:
        cstart = startT + p * cycle
        if cstart > loop_off_t:
            break
        for k, (m, d) in enumerate(riff_pairs):
            nt = cstart + ev_t0 + k * EIGHTH
            if nt > loop_off_t:
                break
            add(note_buffer(m, "square", 0.26), out, A(nt))
        p += 1

    # ---- square click blip ----
    add(note_buffer(60, "square", 0.18), out, A(ev["click_square"]["ctx"]))

    # ---- lead (live, square, vel 0.3) ----
    lead_pairs = notes_with_durations(LEAD)
    lead_ctxs = [e["ctx"] for e in evs if e["name"] == "press_lead"]
    for (m, d), c in zip(lead_pairs, lead_ctxs):
        add(note_buffer(m, "square", 0.3), out, A(c))

    # ---- final chord C4 + C5, held (square, vel 0.3) ----
    for m in (60, 72):
        add(note_buffer(m, "square", 0.3), out, A(ev["chord"]["ctx"]))

    # normalize to 0.95 peak
    peak = np.max(np.abs(out))
    out = out / peak * 0.95 if peak > 0 else out

    wav = (out * 32767).astype(np.int16)
    import wave
    with wave.open("/workspace/keytar/take4/riff.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(wav.tobytes())

    print(f"rendered {len(out)/SR:.2f}s  peak {peak:.3f}  loop cycle {cycle:.3f}s  pass2 start t={A(startT+ev_t0):.3f}s  chord t={A(ev['chord']['ctx']):.3f}s")


if __name__ == "__main__":
    main()
