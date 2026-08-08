"""Performance take 2: screenshot-based capture at a fixed 12fps.

No audio patch (synthesized separately). Screenshots are paced by wall clock
(deadline-based, so cumulative drift ~0), which makes the video timeline
uniform BY CONSTRUCTION. Audio events are anchored to the same wall clock.
"""
import json
import os
import sys
import time

sys.path.insert(0, "/workspace/keytar")
from compose import EIGHTH, RIFF, LEAD, notes_with_durations

URL = ("https://public.ilands.ai/agent-bundles/341632920605167616/"
       "b36b9527cbda65a5453e2863dad91e5329fba606c3c96f581d9f34c33b456922/index.html")

OUTDIR = "/workspace/keytar/take2"
SHOTS = OUTDIR + "/shots"
os.makedirs(SHOTS, exist_ok=True)

FPS = 12
DT = 1.0 / FPS

PLAY_JS = """
(arg) => {
  const seq = arg.seq, startMs = arg.startMs;
  const press = (midi, durMs, atMs) => {
    setTimeout(() => {
      const el = document.querySelector('[data-midi="' + midi + '"]');
      if (!el) return;
      el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerId: 7, isPrimary: true }));
      setTimeout(() => {
        el.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerId: 7, isPrimary: true }));
      }, durMs);
    }, atMs);
  };
  let t = 0;
  for (const [midi, dur] of seq) {
    press(midi, dur * 1000, startMs + t * 1000);
    t += dur;
  }
  return seq.length;
}
"""


def presses(seq):
    out = []
    for midi, dur in seq:
        p = dur - 0.04 if dur <= EIGHTH + 0.02 else dur - 0.03
        out.append([midi, round(p, 4)])
    return out


def main():
    from playwright.sync_api import sync_playwright

    log = {}
    riff = presses(notes_with_durations(RIFF))
    lead = presses(notes_with_durations(LEAD))

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/chromium", headless=True,
            args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required",
                  "--mute-audio=false", "--disable-gpu", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(viewport={"width": 520, "height": 800})
        page = ctx.new_page()
        t0 = time.time()
        page.goto(URL, wait_until="load", timeout=30000)
        page.wait_for_timeout(700)
        # wake audio (no sound) so the page is warm
        page.evaluate("document.body.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:1}))")
        page.wait_for_timeout(200)

        S0 = time.time()          # audio/video t=0 anchor
        log["S0_wall"] = S0
        log["page_loaded_wall"] = t0
        shot_n = 0

        def snap_until(abs_wall):
            """Screenshot every DT seconds until abs_wall, deadline-paced."""
            nonlocal shot_n
            while True:
                now = time.time()
                if now >= abs_wall:
                    return
                # slot for this shot
                k = shot_n
                slot = S0 + k * DT
                if now < slot - 0.005:
                    time.sleep(slot - now - 0.004)
                page.screenshot(path=f"{SHOTS}/{k:05d}.png")
                shot_n += 1

        def click(sel, label, wait=0.4):
            page.click(sel)
            page.wait_for_timeout(wait * 1000)
            log[f"clicked_{label}_wall"] = time.time()

        def play_seq(seq, start_delay, label):
            page.evaluate(PLAY_JS, {"seq": seq, "startMs": start_delay})
            log[f"{label}_scheduled_wall"] = time.time()

        # ---- performance (wall offsets relative to load, same as take 1) ----
        w = lambda d: S0 + d

        # drums click at ~S0+0.9 (matches take1: load+1.7 -> drums at +0.74... use +0.9 for comfort)
        snap_until(w(0.85))
        click("#drumBtn", "drums")
        snap_until(w(1.35))
        click(".wave[data-wave='sawtooth']", "saw", wait=0.1)
        snap_until(w(1.75))
        click("#recBtn", "rec_on", wait=0.05)
        play_seq(riff, 80, "riff")           # riff note 1 at ~S0+1.9
        log["riff_start_wall"] = time.time()
        # probes: is the page actually playing on schedule?
        for probe_t in (2.5, 4.5, 6.5, 8.5):
            snap_until(w(probe_t))
            log[f"status_probe_{probe_t}"] = page.evaluate(
                "document.getElementById('status').textContent")
        snap_until(w(1.9 + len(RIFF) * EIGHTH + 1.2))
        click("#recBtn", "rec_off")
        log["status_after_rec_off"] = page.evaluate(
            "document.getElementById('status').textContent")
        click("#loopBtn", "loop_on")
        loop_click_wall = time.time()
        log["loop_click_wall"] = loop_click_wall
        click(".wave[data-wave='square']", "square", wait=0.2)
        lead_start_wall = S0 + 21.1          # same as take 1
        snap_until(lead_start_wall - 0.55)
        play_seq(lead, 550, "lead")
        log["lead_start_wall"] = lead_start_wall
        snap_until(lead_start_wall + len(LEAD) * EIGHTH + 1.2)
        # final chord
        page.evaluate(
            "() => { const p=(m,d)=>{const el=document.querySelector('[data-midi=\"'+m+'\"]');"
            "el.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:8,isPrimary:true}));"
            "setTimeout(()=>el.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:8,isPrimary:true})),d);};"
            "p(60,1100);p(72,1100); }",
        )
        chord_wall = time.time()
        log["chord_wall"] = chord_wall
        snap_until(chord_wall + 2.2)
        click("#loopBtn", "loop_off", wait=0.25)
        click("#drumBtn", "drums_off", wait=0.25)
        snap_until(chord_wall + 3.6)
        end_wall = time.time()
        log["end_wall"] = end_wall
        log["shots"] = shot_n
        browser.close()

    with open(OUTDIR + "/log.json", "w") as f:
        json.dump(log, f, indent=2)
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
