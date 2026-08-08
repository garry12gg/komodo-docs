"""Play a tune on Plex's Pocket Keytar (headless Chromium via playwright).

Captures:
  - video: playwright recordVideo (webm, 25fps)
  - audio: taps the page's master gain -> MediaStreamDestination -> MediaRecorder
           (patched in via add_init_script before the page's own JS runs)

The performance:
  1. DRUMS ON (112 bpm four-on-floor rolls in)
  2. switch to SAW, hit REC
  3. play a 4-bar bass riff  (recorded by the keytar's own REC)
  4. stop REC, hit LOOP -> the keytar loops the riff itself
  5. switch to SQUARE, play an 8-bar lead melody live over the loop
  6. final C4+C5 chord, LOOP off, DRUMS off, let it ring
"""
import base64
import json
import os
import sys
import time

sys.path.insert(0, "/workspace/keytar")
from compose import EIGHTH, RIFF, LEAD, notes_with_durations

URL = ("https://public.ilands.ai/agent-bundles/341632920605167616/"
       "b36b9527cbda65a5453e2863dad91e5329fba606c3c96f581d9f34c33b456922/index.html")

VIEW_W, VIEW_H = 520, 800
OUTDIR = "/workspace/keytar"
os.makedirs(OUTDIR, exist_ok=True)
STEPLOG = OUTDIR + "/steps.log"


def step(msg):
    with open(STEPLOG, "a") as f:
        f.write(f"{time.time():.1f} {msg}\n")


AUDIO_PATCH = r"""
(() => {
  if (window.__keytarPatched) return 'already';
  window.__keytarPatched = true;
  window.__cap = null;
  window.__capErr = null;
  window.__captureStart = null;

  const origConnect = GainNode.prototype.connect;
  GainNode.prototype.connect = function (...args) {
    const r = origConnect.apply(this, args);
    try {
      const target = args[0];
      // The page's audio core does master.connect(actx.destination) once.
      if (target && target.context && !window.__cap && !this.__tapped) {
        this.__tapped = true;
        const ctx = target.context;
        const streamDest = ctx.createMediaStreamDestination();
        this.connect(streamDest);
        const rec = new MediaRecorder(streamDest.stream);
        const chunks = [];
        rec.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
        rec.onstop = () => {
          const blob = new Blob(chunks, { type: rec.mimeType || 'audio/webm' });
          const fr = new FileReader();
          fr.onload = () => { window.__audioB64 = fr.result; };
          fr.readAsDataURL(blob);
        };
        window.__cap = { ctx, rec, streamDest };
        window.__captureStart = performance.now();
        if (ctx.state === 'suspended') ctx.resume();
        rec.start();
      }
    } catch (e) { window.__capErr = String(e); }
    return r;
  };
  return 'patched';
})();
"""

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
    """(midi, pressDurSeconds) — staccato eighths, full hold for held notes."""
    out = []
    for midi, dur in seq:
        press = dur - 0.04 if dur <= EIGHTH + 0.02 else dur - 0.03
        out.append([midi, round(press, 4)])
    return out


def main():
    from playwright.sync_api import sync_playwright

    log = {}
    riff = presses(notes_with_durations(RIFF))
    lead = presses(notes_with_durations(LEAD))
    step("start")

    with sync_playwright() as p:
        step("launching chromium")
        browser = p.chromium.launch(
            executable_path="/usr/bin/chromium",
            headless=True,
            args=[
                "--no-sandbox",
                "--autoplay-policy=no-user-gesture-required",
                "--mute-audio=false",
                "--use-fake-device-for-media-stream",
                "--disable-gpu",
                "--disable-dev-shm-usage",
            ],
        )
        step("browser up")
        ctx = browser.new_context(
            viewport={"width": VIEW_W, "height": VIEW_H},
            record_video_dir=OUTDIR + "/video",
            record_video_size={"width": VIEW_W, "height": VIEW_H},
        )
        page = ctx.new_page()
        page.add_init_script(AUDIO_PATCH)
        step("context up")

        t0 = time.time()
        page.goto(URL, wait_until="load", timeout=30000)
        page.wait_for_timeout(1500)
        log["page_loaded_at"] = round(time.time() - t0, 2)
        log["title"] = page.title()
        log["patch"] = page.evaluate("window.__keytarPatched")
        page.screenshot(path=OUTDIR + "/01_loaded.png")
        step("loaded " + str(log["title"]))

        def click(sel, label, wait=0.4):
            page.click(sel)
            page.wait_for_timeout(wait * 1000)
            log[f"clicked_{label}_at"] = round(time.time() - t0, 2)
            step("clicked " + label)

        def play_seq(seq, start_delay, label):
            n = page.evaluate(PLAY_JS, {"seq": seq, "startMs": start_delay})
            log[f"{label}_scheduled"] = n
            step(f"scheduled {label} n={n}")

        # -------- the performance --------
        # timeline (seconds from page load)
        def wait_until(abs_t):
            now = time.time() - t0
            if abs_t > now:
                page.wait_for_timeout((abs_t - now) * 1000)
            return time.time() - t0

        # wake audio + start capture as early as possible so audio aligns with video
        page.evaluate("document.body.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:1}))")
        wait_until(0.8)
        click("#drumBtn", "drums")                       # ~1.2  drums roll in
        click(".wave[data-wave='sawtooth']", "saw")     # ~2.0  blip, set bass wave
        wait_until(2.2)
        click("#recBtn", "rec_on", wait=0.05)            # REC at ~2.2
        play_seq(riff, 80, "riff")                        # first note ~0.1s after REC -> loop has no long lead-in
        wait_until(2.3 + len(RIFF) * EIGHTH + 1.2)        # riff ends ~10.9, breath until ~12.1
        click("#recBtn", "rec_off")
        click("#loopBtn", "loop_on")
        # loop downbeat = loop_click + 0.06 + ~0.10 (first recorded ev.t) ; cycle = 8.57 + 1.0
        loop_click_t = time.time() - t0
        downbeat0 = loop_click_t + 0.16
        cycle = len(RIFF) * EIGHTH + 1.0
        click(".wave[data-wave='square']", "square")
        lead_start = downbeat0 + cycle                  # start lead on the 2nd loop cycle's downbeat
        wait_until(lead_start - 0.55)
        play_seq(lead, 550, "lead")
        lead_end = lead_start + len(LEAD) * EIGHTH
        wait_until(lead_end + 1.2)

        # final chord: C4 + C5 held together
        page.evaluate(
            "() => { const p=(m,d)=>{const el=document.querySelector('[data-midi=\"'+m+'\"]');"
            "el.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,pointerId:8,isPrimary:true}));"
            "setTimeout(()=>el.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,pointerId:8,isPrimary:true})),d);};"
            "p(60,1100);p(72,1100); }",
        )
        wait_until(lead_end + 2.9)
        click("#loopBtn", "loop_off", wait=0.3)
        click("#drumBtn", "drums_off", wait=0.3)
        wait_until(lead_end + 5.2)
        step("performance done")

        # ---- stop the recorder, then grab the audio ----
        page.evaluate("window.__cap && window.__cap.rec.stop()")
        page.wait_for_timeout(1200)
        step("recorder stopped")

        # ---- diagnostics ----
        diag = page.evaluate("""() => ({
          status: document.getElementById('status') ? document.getElementById('status').textContent : null,
          cap: window.__cap ? { recState: window.__cap.rec.state, ctxState: window.__cap.ctx.state, ct: window.__cap.ctx.currentTime } : null,
          capErr: window.__capErr,
          audioB64Len: window.__audioB64 ? window.__audioB64.length : 0,
          pressedKeys: document.querySelectorAll('.pressed').length,
        })""")
        log["diag"] = diag
        log["done_at"] = round(time.time() - t0, 2)
        page.screenshot(path=OUTDIR + "/02_end.png")
        step("diag captured")

        # ---- save audio ----
        b64 = page.evaluate("window.__audioB64 || null")
        if b64:
            raw = base64.b64decode(b64.split(",", 1)[1])
            with open(OUTDIR + "/keytar_audio.webm", "wb") as f:
                f.write(raw)
            log["audio_bytes"] = len(raw)
            step(f"audio saved {len(raw)} bytes")
        else:
            log["audio_bytes"] = 0
            step("WARN: no audio captured")

        video_path = page.video.path()
        log["video_path"] = video_path
        ctx.close()
        browser.close()
        step("closed browser")

    with open(OUTDIR + "/log.json", "w") as f:
        json.dump(log, f, indent=2)
    print(json.dumps(log, indent=2))
    step("log written")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        step("EXCEPTION: " + repr(e))
        raise
