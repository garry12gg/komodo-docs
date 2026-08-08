"""Plex's Pocket Keytar — the tune, as data.

112 bpm, 4/4. One octave C4..C5 (midi 60..72).
Eighth = 60/112/2 = 0.267857s.

Riff (SAW, recorded on the keytar's own REC, then LOOPed):
  4 bars: C C G G | C C G G | F F G G | C C G G  (32 eighths)

Lead (SQUARE, played live over the loop):
  8 bars, C-major folk contour with a cadence.
  None = rest (or joined with previous note => held).

Final chord: C4 + C5 held together.
"""
EIGHTH = 60 / 112 / 2
NOTE_DUR = 0.20          # eighth with a small gap (staccato chiptune)
HOLD_DUR = 2 * EIGHTH - 0.05

# 32 eighths
RIFF = [
    60, 60, 67, 67, 60, 60, 67, 67,
    60, 60, 67, 67, 60, 60, 67, 67,
    65, 65, 67, 67, 65, 65, 67, 67,
    60, 60, 67, 67, 60, 60, 67, 67,
]

# 64 eighths (8 bars x 8)
LEAD = [
    # bar 1
    64, 67, 69, 72, 69, 67, 64, 60,
    # bar 2
    69, 71, 72, 71, 69, 67, 64, 67,
    # bar 3
    65, 69, 72, 69, 67, 65, 64, 65,
    # bar 4
    67, 69, 67, 64, 62, 60, None, None,
    # bar 5
    60, 64, 67, 69, 67, 69, 72, 71,
    # bar 6  (last two joined -> held C)
    72, 71, 69, 67, 69, 71, 72, 72,
    # bar 7
    65, 69, 72, 69, 67, 65, 64, 65,
    # bar 8  (two 60s joined -> held C, then rests)
    67, 69, 64, 62, 60, 60, None, None,
]


def notes_with_durations(seq):
    """Yield (midi, dur) pairs; None joins into the previous note (held)."""
    out = []
    for midi in seq:
        if midi is None:
            if out:
                m, d = out[-1]
                out[-1] = (m, d + EIGHTH)
        else:
            out.append((midi, NOTE_DUR))
    return out


if __name__ == "__main__":
    riff = notes_with_durations(RIFF)
    lead = notes_with_durations(LEAD)
    print("riff notes:", len(riff), "dur: %.2fs" % (len(RIFF) * EIGHTH))
    print("lead notes:", len(lead), "dur: %.2fs" % (len(LEAD) * EIGHTH))
