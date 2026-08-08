"""Deterministic render of the keytar performance.

Re-implements Plex's Pocket Keytar synthesis exactly as the page does
(playNote / kick / snare / hat, same envelopes, same biquad filters,
same master gain), driven by the event times recorded in log.json.

Audio time 0 == video time 0 (page load). Events below are wall-clock
seconds from the play.py run; audio_t = wall_t - 1.59.
"""
import json
import numpy as np
from scipy import signal

SR = 48000
WALL0 = 1.59          # wall time of video t=0 (context creation)
EIGHTH = 60 / 112 / 2  # 0.267857
F16 = EIGHTH / 2       # 16th step for drums


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


LP = rbj_lowpass(6500, SR)      # filterNode: lowpass 6500
BP = rbj_bandpass(1900, SR)     # snare bandpass 1900
HP = rbj_highpass(8000, SR)     # hat highpass 8000

rng = np.random.default_rng(7)


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
    # gain envelope: 0.0001 -> vel over 8ms, exp -> 0.0001 at 0.9s
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
    # page: freq exp ramp 150 -> 48 over 0.12s; gain 0.5 -> 0.0001 over 0.18s
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



def build():
    log = json.load(open("/workspace/keytar/take3/log.json"))
    S0 = log["S0_wall"]
    total = 43.8
    out = np.zeros(int(total * SR))

    def A(wall):
        return wall - S0

    def W(wall):
        return wall - S0

    # ---- drums: from drums click +0.05 to drums-off click ----
    kick = kick_buffer()
    snare = snare_buffer()
    hat06 = hat_buffer(0.06)
    hat13 = hat_buffer(0.13)
    t = A(log["clicked_drums_wall"]) + 0.05
    end = A(log["clicked_drums_off_wall"])
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

    # ---- saw blip (wave button) ----
    add(note_buffer(60, "sawtooth", 0.18), out, A(log["clicked_saw_wall"]))

    # ---- recorded riff: presses at rec_on + 0.05(click wait) + 0.08 + k*EIGHTH ----
    riff = [60, 60, 67, 67, 60, 60, 67, 67,
            60, 60, 67, 67, 60, 60, 67, 67,
            65, 65, 67, 67, 65, 65, 67, 67,
            60, 60, 67, 67, 60, 60, 67, 67]
    riff_start = A(log["clicked_rec_on_wall"]) + 0.05 + 0.08
    for k, m in enumerate(riff):
        add(note_buffer(m, "sawtooth", 0.3), out, riff_start + k * EIGHTH)

    # ---- loop playback ----
    # first ev.t: ctx created at wake (~page_loaded+0.2); recStart at rec click
    ctx0 = log["page_loaded_wall"] + 0.2
    rec_start_ctx = log["clicked_rec_on_wall"] - ctx0
    first_press_ctx = riff_start + S0 - ctx0
    ev_t0 = first_press_ctx - rec_start_ctx
    loop0 = A(log["loop_click_wall"]) + 0.06 + ev_t0
    lastT = ev_t0 + (len(riff) - 1) * EIGHTH + 0.16
    cycle = lastT + 0.9
    square_wall = log["clicked_square_wall"]
    loop_off = A(log["clicked_loop_off_wall"])
    for c in range(5):
        cstart = loop0 + c * cycle
        if cstart > loop_off:
            break
        for k, m in enumerate(riff):
            nt = cstart + k * EIGHTH
            if nt > loop_off:
                break
            w = "sawtooth" if (cstart + S0 + k * EIGHTH) < square_wall else "square"
            add(note_buffer(m, w, 0.26), out, nt)

    # ---- square blip ----
    add(note_buffer(60, "square", 0.18), out, A(square_wall))

    # ---- lead ----
    lead = [64, 67, 69, 72, 69, 67, 64, 60,
            69, 71, 72, 71, 69, 67, 64, 67,
            65, 69, 72, 69, 67, 65, 64, 65,
            67, 69, 67, 64, 62, 60, None, None,
            60, 64, 67, 69, 67, 69, 72, 71,
            72, 71, 69, 67, 69, 71, 72, 72,
            65, 69, 72, 69, 67, 65, 64, 65,
            67, 69, 64, 62, 60, 60, None, None]
    lead_start = A(log["lead_start_wall"])
    for k, m in enumerate(lead):
        if m is None:
            continue
        add(note_buffer(m, "square", 0.3), out, lead_start + k * EIGHTH)

    # ---- final chord ----
    chord_t = A(log["chord_wall"])
    add(note_buffer(60, "square", 0.3), out, chord_t)
    add(note_buffer(72, "square", 0.3), out, chord_t)

    out *= 0.5
    return out



def main():
    out = build()
    # stereo (same both channels, like a mono graph through a stereo out)
    stereo = np.repeat(out[:, None], 2, axis=1)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    import wave
    with wave.open("/workspace/keytar/keytar_synth.wav", "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("wrote", len(out) / SR, "s")


if __name__ == "__main__":
    main()
