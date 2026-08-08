import time
from playwright.sync_api import sync_playwright
URL = ("https://public.ilands.ai/agent-bundles/341632920605167616/"
       "b36b9527cbda65a5453e2863dad91e5329fba606c3c96f581d9f34c33b456922/index.html")
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True,
        args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
    ctx = b.new_context(viewport={"width": 520, "height": 800})
    page = ctx.new_page()
    page.goto(URL, wait_until="load", timeout=30000)
    page.wait_for_timeout(500)
    for kind in ("png", "jpeg"):
        t0 = time.time()
        for i in range(12):
            page.screenshot(path=f"/workspace/keytar/bench_{kind}_{i}.img", type=kind, quality=82) if kind=="jpeg" else page.screenshot(path=f"/workspace/keytar/bench_{kind}_{i}.png")
        dt = (time.time() - t0) / 12
        print(kind, f"{dt*1000:.0f}ms per shot")
    b.close()
