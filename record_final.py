#!/usr/bin/env python3
"""FINAL recorder: 'Whatever's Needed' playthrough.
Pumps CDP traffic to keep screencast frames flowing; saves ~15fps JPEGs.
"""
import sys, os, time, base64, re
sys.path.insert(0, "/opt/browser-use/lib/python3.11/site-packages")
from playwright.sync_api import sync_playwright

URL = "https://public.ilands.ai/agent-bundles/335620140622155776/524470a9cd343f27b036a4ae5eb34ac09874ddc5cddcac83120f7e47ceb40e66/index.html"
OUT = "/workspace/frames"
W, H = 1280, 720
FPS = 15

os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))

frame_count = 0
next_slot = 0.0

def answer_for(text):
    low = text.lower()
    if "stream" in low or "wings" in low or "carry across" in low: return "bridge"
    if "dark" in low or "can't see" in low or "find the door" in low: return "lantern"
    if "lock" in low or "lost the key" in low: return "key"
    if "wall" in low or "grip" in low or "climb" in low: return "ladder"
    if "went out" in low or "cold" in low or "forgot how to start" in low: return "flame"
    return None

def visible_buttons(page):
    return page.evaluate("""
        Array.from(document.querySelectorAll('button')).map((e,i)=>({i, txt:(e.innerText||'').trim(), vis:!!(e.offsetWidth||e.offsetHeight)})).filter(b=>b.vis)
    """)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": W, "height": H})
    cdp = page.context.new_cdp_session(page)

    def on_frame(params):
        global frame_count, next_slot
        now = time.time()
        if now >= next_slot:
            next_slot = now + 1.0 / FPS
            frame_count += 1
            with open(f"{OUT}/f{frame_count:05d}.jpg", "wb") as fh:
                fh.write(base64.b64decode(params["data"]))
        try:
            cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
        except Exception:
            pass

    cdp.on("Page.screencastFrame", on_frame)

    def pump(secs):
        """Keep CDP traffic flowing so the compositor emits frames."""
        t0 = time.time()
        while time.time() - t0 < secs:
            page.evaluate("void 0")
            time.sleep(0.066)

    def click_button(name):
        bs = [b for b in visible_buttons(page) if b["txt"].lower() != "light the lamp"]
        t = next((b for b in bs if b["txt"].lower() == name), None)
        if t is None:
            print(f"  !! {name} not among {[b['txt'] for b in bs]}")
            return False
        page.evaluate(f"document.querySelectorAll('button')[{t['i']}].click()")
        return True

    page.goto(URL, wait_until="load", timeout=60000)
    pump(0.6)                     # let first paint settle (avoid white pre-paint frame)
    cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 82, "maxWidth": W, "maxHeight": H})
    pump(4.5)                     # title hold
    page.click("button.btn", timeout=5000)
    pump(3.0)                     # lamp -> scene

    def wait_for_puzzle(prev_answer, timeout=14.0):
        """Pump until a NEW recognizable traveler puzzle is on screen (answer differs from prev)."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            btns = [b for b in visible_buttons(page) if b["txt"].lower() != "light the lamp"]
            if btns:
                txt = page.evaluate("document.body.innerText")
                correct = answer_for(txt)
                if correct is not None and correct != prev_answer:
                    return correct, btns
            pump(0.35)
        btns = [b for b in visible_buttons(page) if b["txt"].lower() != "light the lamp"]
        return (btns[0]["txt"] if btns else None), btns

    prev_answer = None
    for traveler in range(5):
        correct, btns = wait_for_puzzle(prev_answer)
        if correct is None:
            print(f"[t{traveler}] no puzzle found; ending loop", flush=True)
            break
        print(f"[t{traveler}] correct={correct} choices={[b['txt'] for b in btns]}", flush=True)
        pump(2.8)                 # let the traveler's line sit
        if traveler == 0:
            decoy = next((b["txt"] for b in btns if b["txt"].lower() != correct.lower()), None)
            if decoy:
                click_button(decoy)
                pump(2.6)         # "Not that one. The tail tries again."
        click_button(correct)
        pump(4.2)                 # resolve + transition
        prev_answer = correct

    pump(10.0)                    # ending hold
    cdp.send("Page.stopScreencast")
    time.sleep(0.3)
    browser.close()

print(f"TOTAL FRAMES: {frame_count}", flush=True)
