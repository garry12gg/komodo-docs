#!/usr/bin/env python3
"""Sim v3: deterministic Wrong Tool First run. Mirrors the page's EXACT rnd
draw order:
  startGame -> nextJob: 1 draw  (job = floor(r*4))
  spawnTool -> isC: 1 draw (r<0.72), wrongPick: 1 draw (floor(r*5)) if wrong,
               dur: 1 draw (2000+r*350) ALWAYS
  after each correct grab (+260ms) -> nextJob: 1 draw
Reaction timing is node-side (separate stream, does not touch page rng).
"""
import json

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

def mulberry32b(seed):
    return mulberry32(seed ^ 0x9E3779B9)

def simulate(seed):
    rnd = mulberry32(seed)
    react = mulberry32b(seed)
    spawns = []
    t_spawn = 600.0
    jobs_done = 0
    win_at = None
    job = int(rnd() * 4)              # first nextJob at startGame
    while jobs_done < 10:
        t = t_spawn
        is_correct = rnd() < 0.72
        if is_correct:
            dur = 2000.0 + rnd() * 350.0
            spawns.append({'t': round(t), 'correct': True, 'dur': round(dur)})
            press = t + 140.0 + react() * 160.0
            jobs_done += 1
            if jobs_done < 10:
                job = int(rnd() * 4)  # nextJob after the grab settles
                t_spawn = press + 260.0 + 700.0
            else:
                win_at = press + 260.0
        else:
            pick = int(rnd() * 5)
            dur = 2000.0 + rnd() * 350.0
            spawns.append({'t': round(t), 'correct': False, 'pick': pick, 'dur': round(dur)})
            t_spawn = t + dur + 350.0
    return {'win_at': round(win_at), 'spawns': spawns,
            'n_wrong': sum(1 for s in spawns if not s['correct'])}

def score(res):
    win = res['win_at']
    if not (35500 <= win <= 38500):
        return -1e9
    wrongs = [s['t'] for s in res['spawns'] if not s['correct']]
    n = len(wrongs)
    if n < 8 or n > 11:
        return -1e9
    s = 0.0
    s -= abs(win - 37000) / 1000
    if wrongs[0] < 8000: s += 2
    run = 0
    for sp in res['spawns']:
        run = run + 1 if not sp['correct'] else 0
        if run >= 4: s -= 5
    mid = win / 2
    if sum(1 for w in wrongs if w > mid) >= 2: s += 3
    else: s -= 3
    if win - wrongs[-1] > 4500: s += 2
    else: s -= 2
    if any(sp['correct'] is False and sp.get('pick') == 0 for sp in res['spawns']): s += 1
    return s

def main():
    best = []
    for seed in range(0, 30000):
        res = simulate(seed)
        sc = score(res)
        if sc > -1e8:
            best.append((sc, seed, res))
    best.sort(key=lambda x: -x[0])
    print(f"{len(best)} acceptable seeds")
    for sc, seed, res in best[:10]:
        wrongs = [(round(s['t']/1000, 1), s.get('pick')) for s in res['spawns'] if not s['correct']]
        print(f"seed {seed:6d}  score {sc:6.2f}  win {res['win_at']/1000:6.2f}s  wrongs@ {wrongs}")
    if best:
        sc, seed, res = best[0]
        sched = [{'t': s['t'], 'correct': s['correct'], 'pick': s.get('pick')} for s in res['spawns']]
        json.dump({'seed': seed, 'win_at': res['win_at'], 'schedule': sched},
                  open('/workspace/wtf_game/schedule.json', 'w'), indent=1)
        print('saved schedule.json seed', seed, 'win_at', res['win_at'])

if __name__ == '__main__':
    main()
