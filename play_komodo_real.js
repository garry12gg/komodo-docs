// Komodo's Workshop: Wrong Tool First — REAL playthrough.
// No demo mode. I read the job on screen (job icon emoji) and the tool that
// drops (tool emoji), and press SPACE only when they match. Wrong tool = let
// it fall. That's the whole game. Frames -> ffmpeg.
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const FRAME_DIR = '/workspace/kframes2';
const URL = 'https://public.ilands.ai/agent-bundles/341986803529551872/43ba66a211ff4747d7e3f5f2da812d9cf1ad0f889f1d655e028b25ec2fc9cadb/index.html';
const PORT = 9225;

fs.mkdirSync(FRAME_DIR, { recursive: true });
for (const f of fs.readdirSync(FRAME_DIR)) fs.unlinkSync(path.join(FRAME_DIR, f));

const chrome = spawn('chromium', [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
  '--remote-debugging-port=' + PORT, '--window-size=480,920',
  '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
  '--mute-audio', 'about:blank'
], { stdio: 'ignore' });

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function getWsUrl() {
  for (let i = 0; i < 50; i++) {
    try {
      const res = await fetch('http://127.0.0.1:' + PORT + '/json/list');
      const j = await res.json();
      const page = j.find(t => t.type === 'page');
      if (page && page.webSocketDebuggerUrl) return page.webSocketDebuggerUrl;
    } catch (e) { /* retry */ }
    await sleep(200);
  }
  throw new Error('no CDP page target');
}

let msgId = 0;
const pending = new Map();
let ws;

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++msgId;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function js(expr) {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
  if (r.exceptionDetails) throw new Error('JS error: ' + JSON.stringify(r.exceptionDetails).slice(0, 300));
  return r.result && r.result.value;
}

async function pressSpace() {
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: ' ', code: 'Space', windowsVirtualKeyCode: 32, nativeVirtualKeyCode: 32 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: ' ', code: 'Space', windowsVirtualKeyCode: 32, nativeVirtualKeyCode: 32 });
}

// ---------- frame capture ----------
let frameCount = 0;
let captureStart = null;
let capturing = true;

async function captureLoop() {
  while (capturing) {
    const t0 = Date.now();
    try {
      const r = await send('Page.captureScreenshot', { format: 'jpeg', quality: 85 });
      const file = path.join(FRAME_DIR, 'f_' + String(frameCount).padStart(5, '0') + '.jpg');
      fs.writeFileSync(file, Buffer.from(r.data, 'base64'));
      frameCount++;
      if (!captureStart) captureStart = t0;
    } catch (e) { /* keep going */ }
    const elapsed = Date.now() - t0;
    await sleep(Math.max(40, 100 - elapsed));
  }
}

(async () => {
  try {
    const wsUrl = await getWsUrl();
    ws = new WebSocket(wsUrl);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    ws.onmessage = ev => {
      const m = JSON.parse(ev.data);
      if (m.id && pending.has(m.id)) {
        const p = pending.get(m.id); pending.delete(m.id);
        if (m.error) p.reject(new Error(m.error.message)); else p.resolve(m.result);
      }
    };
    await send('Page.enable');
    await send('Runtime.enable');
    await send('Emulation.setDeviceMetricsOverride', { width: 480, height: 920, deviceScaleFactor: 1, mobile: false });

    await send('Page.navigate', { url: URL });
    await sleep(2500);
    captureLoop();

    // --- title screen: press SPACE to start (real input, no demo) ---
    await pressSpace();
    await sleep(400);

    // --- play loop ---
    let grabs = 0;
    let wrongLetFall = 0;
    let lastToolState = '';
    const t0 = Date.now();
    let finished = false;
    let outcome = null;

    while (Date.now() - t0 < 150000 && !finished) {
      const s = await js(`(() => {
        const tool = document.getElementById('tool');
        const ov = document.getElementById('overlay');
        return {
          toolVisible: tool.style.display === 'flex',
          toolEmoji: tool.dataset.emoji || '',
          jobEmoji: document.getElementById('jobicon').textContent,
          overlayHidden: ov.className.includes('hidden'),
          overlayH: ov.querySelector('h1') ? ov.querySelector('h1').textContent : '',
          score: document.getElementById('score').textContent
        };
      })()`);
      if (!s) { await sleep(120); continue; }

      if (!s.overlayHidden) {
        // game over or win screen reached
        finished = true;
        outcome = await js(`(() => ({
          h: document.getElementById('overlay').querySelector('h1').textContent.replace(/\\n/g,' '),
          sub: document.getElementById('overlay').querySelector('.sub').textContent,
          gag: document.getElementById('overlay').querySelector('.gag').textContent,
          score: document.getElementById('bigscore').textContent,
          strikes: document.getElementById('strikes').textContent
        }))()`);
        break;
      }

      const stateKey = s.toolVisible + '|' + s.toolEmoji + '|' + s.jobEmoji;
      if (s.toolVisible && stateKey !== lastToolState) {
        if (s.toolEmoji === s.jobEmoji) {
          // the right tool for the job on screen — grab it
          await sleep(140 + Math.random() * 160); // human-ish reaction
          await pressSpace();
          grabs++;
        } else {
          wrongLetFall++;
        }
        lastToolState = stateKey;
      }
      await sleep(90);
    }

    if (!finished) throw new Error('run did not finish in time');

    capturing = false;
    await sleep(1200); // hold end screen
    const dur = (Date.now() - captureStart) / 1000;
    console.log(JSON.stringify({
      frames: frameCount, seconds: dur.toFixed(1), fps: (frameCount / dur).toFixed(2),
      grabs, wrongLetFall, outcome
    }));
  } catch (e) {
    console.error('FAIL:', e.message);
    process.exitCode = 1;
  } finally {
    capturing = false;
    try { await send('Page.stopScreencast'); } catch (e) {}
    chrome.kill();
    process.exit(process.exitCode || 0);
  }
})();
