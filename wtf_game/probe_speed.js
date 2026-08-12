// Probe: does the game run at full speed in this headless chromium?
// Measures setInterval(16) tick rate + a real tool fall duration.
const { spawn } = require('child_process');
const PORT = 9231;
const URL = 'https://public.ilands.ai/agent-bundles/341986803529551872/43ba66a211ff4747d7e3f5f2da812d9cf1ad0f889f1d655e028b25ec2fc9cadb/index.html';

const chrome = spawn('chromium', [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
  '--remote-debugging-port=' + PORT, '--window-size=480,920',
  '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
  '--disable-backgrounding-occluded-windows', '--disable-ipc-flooding-protection',
  '--disable-frame-rate-limit', '--disable-features=ThrottleDisplayNoneAndVisibilityHiddenCrossOriginIframes',
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
    } catch (e) {}
    await sleep(200);
  }
  throw new Error('no page');
}
let msgId = 0; const pending = new Map(); let ws;
function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++msgId; pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}
async function js(expr) {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error('JS: ' + JSON.stringify(r.exceptionDetails).slice(0, 200));
  return r.result && r.result.value;
}

(async () => {
  try {
    ws = new WebSocket(await getWsUrl());
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result); } };
    await send('Page.enable'); await send('Runtime.enable');
    await send('Page.navigate', { url: URL });
    await sleep(3000);

    // ticker probe: 16ms interval for 2s
    const tickRate = await js(`new Promise(res => {
      let n = 0;
      const t0 = performance.now();
      const iv = setInterval(() => { n++; if (performance.now() - t0 >= 2000) { clearInterval(iv); res({ ticks: n, ms: Math.round(2000 / n) }); } }, 16);
    })`);
    console.log('interval-16ms rate:', JSON.stringify(tickRate));

    // lifecycle active
    await send('Page.setWebLifecycleState', { state: 'active' });
    await sleep(300);
    const tickRate2 = await js(`new Promise(res => {
      let n = 0;
      const t0 = performance.now();
      const iv = setInterval(() => { n++; if (performance.now() - t0 >= 2000) { clearInterval(iv); res({ ticks: n, ms: Math.round(2000 / n) }); } }, 16);
    })`);
    console.log('after lifecycle-active rate:', JSON.stringify(tickRate2));

    // fall speed: start the game, measure one spawn -> gone (or grab) duration
    const fall = await js(`new Promise(res => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true, cancelable: true }));
      const tool = document.getElementById('tool');
      const seen = { spawn: null, gone: null, grabbed: null };
      const obs = new MutationObserver(() => {
        if (tool.style.display === 'flex' && !seen.spawn) {
          seen.spawn = performance.now();
          tool.dataset.probe = '1';
        }
        if (seen.spawn && tool.style.display === 'none' && !seen.gone) seen.gone = performance.now();
      });
      obs.observe(tool, { attributes: true, attributeFilter: ['style'] });
      setTimeout(() => { obs.disconnect(); res(seen); }, 15000);
    })`);
    console.log('fall probe:', JSON.stringify(fall));
  } catch (e) {
    console.error('FAIL:', e.message);
  } finally {
    chrome.kill();
    process.exit(0);
  }
})();
