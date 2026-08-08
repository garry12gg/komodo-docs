"""Minimal experiment: drums + loop behavior in headless chromium, with and without
anti-background-throttling flags. Measures whether the 1s-blip problem reproduces."""
import base64
import json
import os
import sys
import time

sys.path.insert(0, "/workspace/keytar")
from compose import EIGHTH, RIFF, notes_with_durations

URL = ("https://public.ilands.ai/agent-bundles/341632920605167616/"
       "b36b9527cbda65a5453e2863dad91e5329fba606c3c96f581d9f34c33b456922/index.html")

AUDIO_PATCH = open("/workspace/keytar/audio_patch.js").read()

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


def run(tag, extra_args):
    from playwright.sync_api import sync_playwright
    out = {}
    riff = presses(notes_with_durations(RIFF))
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/chromium", headless=True,
            args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required",
                  "--mute-audio=false", "--disable-gpu", "--disable-dev-shm-usage"] + extra_args,
        )
        ctx = browser.new_context(viewport={"width": 520, "height": 800})
        page = ctx.new_page()
        page.add_init_script(AUDIO_PATCH)
        page.goto(URL, wait_until="load", timeout=30000)
        page.wait_for_timeout(800)
        page.evaluate("document.body.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:1}))")
        page.wait_for_timeout(400)
        page.click("#drumBtn")                       # drums on
        page.wait_for_timeout(12000)                 # 12s of drums alone
        page.click("#recBtn")
        page.evaluate(PLAY_JS, {"seq": riff, "startMs": 80})
        page.wait_for_timeout(int(len(RIFF) * EIGHTH * 1000) + 800)
        page.click("#recBtn")
        page.click("#loopBtn")                       # loop on
        page.wait_for_timeout(11000)                 # ~1 loop cycle
        page.click("#loopBtn")                       # loop off
        page.wait_for_timeout(600)
        page.evaluate("window.__cap && window.__cap.rec.stop()")
        page.wait_for_timeout(1000)
        b64 = page.evaluate("window.__audioB64 || null")
        if b64:
            raw = base64.b64decode(b64.split(",", 1)[1])
            path = f"/workspace/keytar/exp_{tag}.webm"
            open(path, "wb").write(raw)
            out["audio"] = path
        out["diag"] = page.evaluate("""() => ({
            ctxState: window.__cap ? window.__cap.ctx.state : null,
            ct: window.__cap ? window.__cap.ctx.currentTime : null,
            capErr: window.__capErr,
        })""")
        browser.close()
    return out


if __name__ == "__main__":
    print(json.dumps(run("base", []), indent=2))
