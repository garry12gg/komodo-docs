"""Wrong Tool First — keytar take (the first listen).

112 bpm, 4/4. Two-octave board (C4..C6, midi 60..84). Plex's keytar.
Eighth = 60/112/2 = 0.267857s.

The gag, musically: ONE wrong note drops first (Db over C — the wrong
tool), and nobody grabs it. It falls. Then the work starts clean.

Timeline (audio t=0 = the wrong note):
  t=0.00   wrong note Db4 (61), square (the board's default voice)
  t=0.27   rest (it falls)
  t=0.55   saw click blip — the right tool seats into its slot
  t=0.80   drums + RIFF pass 1 (saw, REC'd live)
  t~9.98   LOOP takes over (square), LEAD played live over it
  t~19.0   final chord C4 + C5 held
  t~20.3   drums off, loop off, ring out

RIFF (4 bars, 32 eighths, saw, recorded + looped):
  C C G G | C C G G | C C G G | C C G G
  F F G G | F F G G | C C G G | C C C5 G   (C5 = 72 lifts into the loop)

LEAD (4 bars, 32 eighths, square, played live over the loop):
  E G A C5 | A G E C | F A C5 A | G A G E
  D C C(held) — then the chord
"""
EIGHTH = 60 / 112 / 2
NOTE_DUR = 0.20          # eighth with a small gap (staccato chiptune)
HOLD_DUR = 2 * EIGHTH - 0.05

WRONG = 61  # Db4 — the wrong tool that drops first

# 32 eighths, clean C-major, one lift at the end
RIFF = [
    60, 60, 67, 67, 60, 60, 67, 67,
    60, 60, 67, 67, 60, 60, 67, 67,
    65, 65, 67, 67, 65, 65, 67, 67,
    60, 60, 67, 67, 60, 60, 72, 67,
]

# 32 eighths, square, folk contour with a held-C cadence
LEAD = [
    64, 67, 69, 72, 69, 67, 64, 60,
    69, 71, 72, 71, 69, 67, 64, 67,
    65, 69, 72, 69, 67, 65, 64, 65,
    67, 69, 67, 64, 62, 60, 60, None,  # last 60 held, then rest
]

CHORD = (60, 72)  # C4 + C5, held


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
