"""Wrong Tool First — performance take.

Drives Plex's two-octave Pocket Keytar (dffe1b7f bundle) in headless
Chromium. All events scheduled INSIDE the page on setTimeout from t0, so
the page's own audio clock (ctx.currentTime) is the single source of
truth. Every event logs {wall, ctx} so the synth renders deterministically
from the same clock. Screenshots are deadline-paced at 12fps for visuals.
"""
import json
import os
import sys
import time

sys.path.insert(0, "/workspace/keytar")
from compose2 import EIGHTH, NOTE_DUR, WRONG, RIFF, LEAD, CHORD, notes_with_durations

URL = ("https://public.ilands.ai/agent-bundles/341632920605167616/"
       "dffe1b7f14a5d5ea92ea8cdc08a196ee45f9b680c451f6a193d0a9690354da25/index.html")

OUTDIR = "/workspace/keytar/take4"
SHOTS = OUTDIR + "/shots"
os.makedirs(SHOTS, exist_ok=True)

FPS = 12
DT = 1.0 / FPS

# wall offsets from t0, in ms
T_SAW = 550
T_DRUMS = 750          # grid starts +50ms -> 800
T_REC_ON = 780
T_REC_OFF = 9650
T_SQUARE = 9900
T_LOOP = 9920
T_CHORD = 19000
T_DRUMS_OFF = 20300
T_LOOP_OFF = 19200     # one full loop cycle (pass 2), then the chord owns the ending
T_END = 22600

PERF_JS = r"""
(arg) => {
  const t0 = arg.t0;                       // Date.now() at schedule time (ms)
  const STEP16 = 60 / 112 / 4;
  window.__evlog = [];
  const ev = (name, extra) => window.__evlog.push(
    Object.assign({ name, wall: Date.now(), ctx: window.__actxCtx ? window.__actxCtx.currentTime : -1 }, extra || {}));
  const off = (ms) => Math.max(0, ms - (Date.now() - t0));

  const press = (midi, durMs, atMs, tag) => setTimeout(() => {
    ev('press_' + tag, { midi });
    const el = document.querySelector('[data-midi="' + midi + '"]');
    if (!el) return;
    el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerId: 7, isPrimary: true }));
    setTimeout(() => {
      el.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerId: 7, isPrimary: true }));
    }, durMs);
  }, off(atMs));

  const click = (sel, tag, atMs) => setTimeout(() => {
    ev('click_' + tag, { sel });
    const el = document.querySelector(sel);
    if (el) el.click();
  }, off(atMs));

  const seqAt = (seq, tag, atMs) => {      // seq: [[midi, durMs], ...]
    seq.forEach((nd, k) => press(nd[0], nd[1], atMs + k * arg.EIGHTH_MS, tag));
  };

  // 1. the wrong note drops first, and falls (square = board default)
  press(arg.WRONG, 200, 0, 'wrong');

  // 2. the right tool seats into its slot (saw click blip)
  click('.wave[data-wave="sawtooth"]', 'saw', arg.T_SAW);

  // 3. drums + record + riff pass 1 (live, saw)
  click('#drumBtn', 'drums', arg.T_DRUMS);
  click('#recBtn', 'rec_on', arg.T_REC_ON);
  seqAt(arg.RIFF, 'riff', arg.T_REC_ON + 20);

  // 4. stop REC, switch to square, start LOOP; lead locked to the loop's
  //    own grid math (q16(ctx+0.06) + ev_t0), scheduled at loop time
  click('#recBtn', 'rec_off', arg.T_REC_OFF);
  click('.wave[data-wave="square"]', 'square', arg.T_SQUARE);
  setTimeout(() => {
    const ctx = window.__actxCtx;
    const startT = Math.ceil((ctx.currentTime + 0.06) / STEP16) * STEP16;
    const riff0 = window.__evlog.find(e => e.name === 'press_riff');
    const recOn = window.__evlog.find(e => e.name === 'click_rec_on');
    const ev_t0 = riff0 && recOn ? riff0.ctx - recOn.ctx : 0;
    ev('loop_click', { startT, ev_t0 });
    const loopBtn = document.getElementById('loopBtn');
    if (loopBtn) loopBtn.click();
    const lead0ctx = startT + ev_t0;
    arg.LEAD.forEach((nd, k) => {
      const delayMs = (lead0ctx + k * arg.EIGHTH - ctx.currentTime) * 1000;
      press(nd[0], nd[1], (Date.now() - t0) + delayMs, 'lead');
    });
  }, off(arg.T_LOOP));

  // 5. final chord C4 + C5, held
  setTimeout(() => {
    ev('chord');
    [60, 72].forEach((m, i) => {
      setTimeout(() => {
        const el = document.querySelector('[data-midi="' + m + '"]');
        if (el) el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerId: 8 + i, isPrimary: true }));
      }, i * 20);
    });
    setTimeout(() => {
      [60, 72].forEach((m, i) => {
        const el = document.querySelector('[data-midi="' + m + '"]');
        if (el) el.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerId: 8 + i, isPrimary: true }));
      });
    }, 1200);
  }, off(arg.T_CHORD));

  // 6. shut the machine down
  click('#drumBtn', 'drums_off', arg.T_DRUMS_OFF);
  click('#loopBtn', 'loop_off', arg.T_LOOP_OFF);
  return 'scheduled';
}
"""


def main():
    from playwright.sync_api import sync_playwright

    riff = [[m, int(d * 1000)] for m, d in notes_with_durations(RIFF)]
    lead = [[m, int(d * 1000)] for m, d in notes_with_durations(LEAD)]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/chromium", headless=True,
            args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required",
                  "--disable-gpu", "--disable-dev-shm-usage",
                  "--disable-background-timer-throttling", "--disable-renderer-backgrounding"],
        )
        ctx = browser.new_context(viewport={"width": 520, "height": 800})
        page = ctx.new_page()
        t_load = time.time()
        page.goto(URL, wait_until="load", timeout=30000)
        page.wait_for_timeout(700)

        # capture the page's AudioContext before it is ever created
        page.evaluate("""
          () => {
            const Orig = window.AudioContext || window.webkitAudioContext;
            window.AudioContext = class extends Orig {
              constructor(...a) { super(...a); window.__actxCtx = this; }
            };
          }
        """)

        # wake the page (creates the ctx through our subclass)
        page.evaluate("() => { const el = document.querySelector('[data-midi=\"60\"]');"
                      "el.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:1,isPrimary:true}));"
                      "setTimeout(()=>el.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:1,isPrimary:true})),40); }")
        page.wait_for_timeout(400)
        assert page.evaluate("!!window.__actxCtx"), "AudioContext not captured"

        # run the performance
        page.evaluate(PERF_JS, {
            "t0": int(time.time() * 1000),
            "WRONG": WRONG, "RIFF": riff, "LEAD": lead,
            "EIGHTH": EIGHTH, "EIGHTH_MS": int(EIGHTH * 1000),
            "T_SAW": T_SAW, "T_DRUMS": T_DRUMS, "T_REC_ON": T_REC_ON,
            "T_REC_OFF": T_REC_OFF, "T_SQUARE": T_SQUARE, "T_LOOP": T_LOOP,
            "T_CHORD": T_CHORD, "T_DRUMS_OFF": T_DRUMS_OFF, "T_LOOP_OFF": T_LOOP_OFF,
        })

        # screenshot loop, deadline-paced from S0 (S0 == t0 approx)
        S0 = time.time()
        shot_n = 0
        start_abs = S0 - 0.25
        end_abs = S0 + T_END / 1000.0
        statuses = {}
        probe_at = [1500, 5000, 10500, 14500, 19500, 21000]
        while True:
            now = time.time()
            if now >= end_abs:
                break
            for probe_ms in list(probe_at):
                if now >= S0 + probe_ms / 1000.0:
                    statuses[probe_ms] = page.evaluate("document.getElementById('status').textContent")
                    probe_at.remove(probe_ms)
            slot = start_abs + shot_n * DT
            if now < slot - 0.005:
                time.sleep(slot - now - 0.004)
            page.screenshot(path=f"{SHOTS}/{shot_n:05d}.jpg", type="jpeg", quality=82)
            shot_n += 1

        evlog = page.evaluate("window.__evlog || []")
        browser.close()

    out = {
        "S0_wall": S0,
        "t_load_wall": t_load,
        "shots": shot_n,
        "statuses": statuses,
        "evlog": evlog,
    }
    with open(OUTDIR + "/log.json", "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "evlog"}, indent=1))
    print("evlog entries:", len(evlog))


if __name__ == "__main__":
    main()
