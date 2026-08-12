#!/usr/bin/env python3
"""Simulate a Wrong Tool First run driven by mulberry32(seed) as Math.random,
mirroring the game's rnd call order + the in-page driver's reaction draws.
Find seeds with good pacing: win ~33-38s, ducks sprinkled, clean ending."""
import random

def mulberry32(seed):
    a = seed & 0xFFFFFFFF
    def rnd():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = ((t << 15) | (t >> 17)) & 0xFFFFFFFF
        t = (t * (a ^ (t >> 11))) & 0xFFFFFFFF
        return ((t ^ (t >> 8)) & 0xFFFFFFFF) / 4294967296
    return rnd

TOTAL_JOBS = 10
WRONGS = 5  # wrong tool pool size

def simulate(seed):
    rnd = mulberry32(seed)
    # times in ms, anchored at the start press (t=0)
    events = []          # (t, kind) kind: correct|wrong
    wrong_tools = []     # (t, idx) for emoji mapping later
    t = 0.0
    rnd()  # nextJob #1
    t_spawn = 600.0
    jobs_done = 0
    grabs = []
    while jobs_done < TOTAL_JOBS:
        t = t_spawn
        is_correct = rnd() < 0.72
        if not is_correct:
            pick = int(rnd() * WRONGS)
            dur = 2000.0 + rnd() * 350.0
            wrong_tools.append((t, pick))
            events.append((t, 'wrong'))
            t_spawn = t + dur + 350.0
        else:
            dur = 2000.0 + rnd() * 350.0
            detect = t + 30.0                      # driver poll latency ~30ms
            react = 140.0 + rnd() * 160.0          # driver reaction draw
            press = detect + react
            grabs.append(press)
            events.append((t, 'correct'))
            jobs_done += 1
            if jobs_done < TOTAL_JOBS:
                rnd()  # nextJob
                t_spawn = press + 260.0 + 700.0
            else:
                win_at = press + 260.0
    return {
        'win_at': win_at, 'grabs': grabs, 'events': events,
        'wrongs': [w for w in wrong_tools], 'n_wrong': len(wrong_tools),
    }

def score(res):
    win = res['win_at']
    wrongs = [w[0] for w in res['wrongs']]
    if not (33000 <= win <= 38000):
        return -1e9
    # wrong tool spread: want 3-5, first within 12s, no gap > 12s between wrongs
    n = len(wrongs)
    if n < 3 or n > 6:
        return -1e9
    s = 0
    s -= abs(win - 35500) / 1000          # prefer win ~35.5s
    s += 2 if wrongs[0] < 12000 else 0    # early duck gag
    gaps = [wrongs[i+1] - wrongs[i] for i in range(len(wrongs)-1)]
    for g in gaps:
        if g > 12000: s -= 5
    # ending: last wrong should be > 8s before win (clean combo run to the end)
    last_wrong = wrongs[-1]
    if win - last_wrong > 8000: s += 3
    else: s -= 3
    return s

best = []
for seed in range(0, 4000):
    res = simulate(seed)
    sc = score(res)
    if sc > -1e8:
        best.append((sc, seed, res))

best.sort(key=lambda x: -x[0])
print(f"{len(best)} acceptable seeds")
for sc, seed, res in best[:8]:
    wrongs = [round(w[0]/1000, 1) for w in res['wrongs']]
    print(f"seed {seed:5d}  score {sc:6.2f}  win {res['win_at']/1000:6.2f}s  wrongs@ {wrongs}  n={res['n_wrong']}")
