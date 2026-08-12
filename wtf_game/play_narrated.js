// Komodo's Workshop: Wrong Tool First — NARRATED real playthrough, v2.
// CDP-driven (proven full-speed): node polls the DOM, presses SPACE via
// Input.dispatchKeyEvent when the falling tool matches the job. Logs press
// times + win moment + per-frame wall times for exact SFX resynthesis.
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const FRAME_DIR = '/workspace/wtf_game/frames';
const URL = 'https://public.ilands.ai/agent-bundles/341986803529551872/43ba66a211ff4747d7e3f5f2da812d9cf1ad0f889f1d655e028b25ec2fc9cadb/index.html';
const PORT = 9233;

fs.mkdirSync(FRAME_DIR, { recursive: true });
for (const f of fs.readdirSync(FRAME_DIR)) fs.unlinkSync(path.join(FRAME_DIR, f));

const chrome = spawn('chromium', [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
  '--remote-debugging-port=' + PORT, '--window-size=480,920',
  '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
  '--disable-backgrounding-occluded-windows', '--disable-ipc-flooding-protection',
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

const audit = { presses: [], winAt: null, frameTimes: [], captureStart: null };

let frameCount = 0;
let capturing = true;

async function captureLoop() {
  while (capturing) {
    const t0 = Date.now();
    try {
      const r = await send('Page.captureScreenshot', { format: 'jpeg', quality: 85 });
      const file = path.join(FRAME_DIR, 'f_' + String(frameCount).padStart(5, '0') + '.jpg');
      fs.writeFileSync(file, Buffer.from(r.data, 'base64'));
      if (!audit.captureStart) audit.captureStart = t0;
      audit.frameTimes.push(t0);
      frameCount++;
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
    try { await send('Page.setWebLifecycleState', { state: 'active' }); } catch (e) {}

    // watch for the win overlay appearing (exact jingle timing)
    await js(`(() => {
      window.__winAt = null;
      const ov = document.getElementById('overlay');
      new MutationObserver(() => {
        if (!ov.className.includes('hidden') && ov.querySelector('h1').textContent.includes('WORKSHOP')) {
          window.__winAt = Date.now();
        }
      }).observe(ov, { attributes: true, subtree: true, childList: true });
      return true;
    })()`);

    captureLoop();

    // --- title screen breathes, then SPACE starts the run ---
    await sleep(1700);
    audit.presses.push({ t: Date.now(), kind: 'start' });
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
          overlayHidden: ov.className.includes('hidden')
        };
      })()`);
      if (!s) { await sleep(120); continue; }

      if (!s.overlayHidden && audit.presses.length > 1) {
        // game ended (win or gameover) -> overlay visible again
        finished = true;
        break;
      }

      const stateKey = s.toolVisible + '|' + s.toolEmoji + '|' + s.jobEmoji;
      if (s.toolVisible && stateKey !== lastToolState) {
        if (s.toolEmoji === s.jobEmoji) {
          await sleep(140 + Math.random() * 160); // human-ish reaction
          audit.presses.push({ t: Date.now(), kind: 'grab', tool: s.toolEmoji, job: s.jobEmoji });
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

    outcome = await js(`(() => ({
      h: document.getElementById('overlay').querySelector('h1').textContent.replace(/\\n/g,' '),
      sub: document.getElementById('overlay').querySelector('.sub').textContent,
      gag: document.getElementById('overlay').querySelector('.gag').textContent,
      score: document.getElementById('bigscore').textContent,
      strikes: document.getElementById('strikes').textContent
    }))()`);
    audit.winAt = await js('window.__winAt');
    await sleep(5200); // hold victory screen for the narration landing + jingle

    capturing = false;
    await sleep(300);
    const dur = (Date.now() - audit.captureStart) / 1000;
    const res = {
      frames: frameCount,
      seconds: dur.toFixed(1),
      fps: (frameCount / dur).toFixed(2),
      grabs,
      wrongLetFall,
      outcome,
      winAt: audit.winAt,
      captureStart: audit.captureStart,
      frameTimes: audit.frameTimes,
      pressTimes: audit.presses.map(p => ({ kind: p.kind, tool: p.tool || null, job: p.job || null, dt: p.t - audit.captureStart }))
    };
    fs.writeFileSync('/workspace/wtf_game/audit.json', JSON.stringify(res));
    console.log('DONE', JSON.stringify(res));
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
