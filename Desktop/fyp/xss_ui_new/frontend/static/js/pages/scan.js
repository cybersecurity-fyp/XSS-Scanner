// XSSniper — Scan page logic

let currentScanId   = null;
let scanEventSource = null;

/* ── Init: runs on both hard load and HTMX navigation ────────────────────── */
function _initScan() {
  if (!document.getElementById('start-btn')) return;
  document.getElementById('start-btn')
    ?.addEventListener('click', startScan);
  document.getElementById('stop-btn')
    ?.addEventListener('click', stopScan);
  document.getElementById('copy-terminal-btn')
    ?.addEventListener('click', copyTerminal);
  document.getElementById('clear-terminal-btn')
    ?.addEventListener('click', clearTerminal);
  document.getElementById('adv-header')
    ?.addEventListener('click', toggleAdvanced);
  _bindRangeLabel('scan-level',   'level-val',   v => ['', 'Basic', 'Standard', 'Deep'][+v]);
  _bindRangeLabel('scan-threads', 'threads-val', v => v);
  _bindRangeLabel('scan-timeout', 'timeout-val', v => v);
}

document.addEventListener('DOMContentLoaded', _initScan);
document.addEventListener('htmx:afterSettle', _initScan);

/* Close any active EventSource when navigating away */
document.addEventListener('htmx:beforeSwap', () => {
  if (scanEventSource) { scanEventSource.close(); scanEventSource = null; }
});

function _bindRangeLabel(inputId, labelId, formatter) {
  const input = document.getElementById(inputId);
  const label = document.getElementById(labelId);
  if (input && label) {
    input.addEventListener('input', () => { label.textContent = formatter(input.value); });
  }
}

/* ── Terminal helpers ────────────────────────────────────────────────────── */
function copyTerminal() {
  const t   = document.getElementById('terminal-output');
  const btn = document.getElementById('copy-terminal-btn');
  navigator.clipboard.writeText(t ? (t.innerText || t.textContent) : '')
    .then(() => { toast('Log copied', 'success'); _flashCopied(btn); })
    .catch(() => toast('Copy failed', 'error'));
}

function _flashCopied(btn) {
  if (!btn) return;
  // Find and store only the text node so we never touch innerHTML
  let textNode = null;
  btn.childNodes.forEach(n => { if (n.nodeType === Node.TEXT_NODE && n.nodeValue.trim()) textNode = n; });
  const prevText = textNode ? textNode.nodeValue : '';
  btn.classList.add('btn--copied');
  if (textNode) textNode.nodeValue = ' ✓ Copied';
  setTimeout(() => {
    btn.classList.remove('btn--copied');
    if (textNode) textNode.nodeValue = prevText;
  }, 1500);
}

function clearTerminal() {
  const t = document.getElementById('terminal-output');
  if (t) {
    t.innerHTML = '<div class="line-dim">Terminal cleared — ready for next scan.</div>'
                + '<span class="cursor"></span>';
  }
}

/* ── Advanced panel toggle (CSS .collapsible class — no display hacks) ───── */
function toggleAdvanced() {
  const panel = document.getElementById('advanced-panel');
  const btn   = document.getElementById('adv-header');
  if (!panel) return;
  const open = panel.classList.toggle('open');
  if (btn) btn.setAttribute('aria-expanded', String(open));
}

async function startScan() {
  const url = document.getElementById('scan-url').value.trim();
  if (!url || !/^https?:\/\//i.test(url)) {
    toast('Enter a valid URL starting with https:// or http://', 'error'); return;
  }
  try {
    const h = new URL(url).hostname;
    if (/^(localhost|127\.|192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.|0\.0\.0\.0|169\.254\.)/.test(h)) {
      toast('Private/internal addresses cannot be scanned', 'error'); return;
    }
  } catch (e) { toast('Could not parse URL — check the format and try again', 'error'); return; }

  const config = {
    url,
    data:         document.getElementById('scan-data')?.value.trim()    || '',
    json_mode:    document.getElementById('h-json')?.value    === 'true',
    crawl:        document.getElementById('h-crawl')?.value   === 'true',
    level:        parseInt(document.getElementById('scan-level')?.value   || 2),
    threads:      parseInt(document.getElementById('scan-threads')?.value || 2),
    timeout:      parseInt(document.getElementById('scan-timeout')?.value || 5),
    delay:        parseFloat(document.getElementById('scan-delay')?.value || 0),
    fuzzer:       document.getElementById('h-fuzzer')?.value  === 'true',
    encode:       document.getElementById('h-encode')?.value  === 'true',
    path:         document.getElementById('h-path')?.value    === 'true',
    file:         document.getElementById('scan-file')?.value.trim()      || '',
    skip_dom:     document.getElementById('h-skipdom')?.value === 'true',
    headers:      document.getElementById('scan-headers')?.value.trim()   || '',
    proxy:        document.getElementById('scan-proxy')?.value.trim()     || '',
    ml_prefilter: document.getElementById('h-ml')?.value      === 'true',
  };

  const terminal = document.getElementById('terminal-output');
  terminal.innerHTML = '';
  setButtonLoading(document.getElementById('start-btn'), true);
  document.getElementById('stop-btn').disabled  = false;
  document.getElementById('scan-url').disabled  = true;
  addLog('[*] XSSniper — ML-Enhanced XSS Vulnerability Scanner', 'dim');
  addLog('[*] Started: ' + new Date().toLocaleString(), 'dim');
  addLog('[*] Target:  ' + url, 'dim');
  addLog('[*] ' + '─'.repeat(58), 'dim');

  try {
    const { scan_id } = await api('POST', '/api/v1/scan/start', config);
    currentScanId   = scan_id;
    scanEventSource = new EventSource('/api/v1/scan/' + scan_id + '/stream');
    scanEventSource.onmessage = e => {
      if (e.data.startsWith('__DONE__')) {
        const result = JSON.parse(e.data.replace('__DONE__', ''));
        scanEventSource.close();
        onScanDone(result);
      } else { addLog(e.data); }
    };
    scanEventSource.onerror = () => {
      scanEventSource.close();
      addLog('[ERROR] Stream connection lost — the scan may have ended or the server restarted', 'red');
      resetScanUI();
    };
  } catch (err) {
    addLog('[ERROR] Could not start scan: ' + err.message, 'red');
    toast('Could not start scan: ' + err.message, 'error');
    resetScanUI();
  }
}

function addLog(msg, forceColor) {
  const terminal = document.getElementById('terminal-output');
  if (!terminal) return;
  const line = document.createElement('div');
  let cls = forceColor || 'default';
  if (!forceColor) {
    if      (msg.includes('[ERROR]') || msg.toLowerCase().includes('failed')) cls = 'red';
    else if (msg.includes('[+]') || msg.includes('VULNERABILITY') || msg.includes('FOUND')) cls = 'green';
    else if (msg.includes('[ML]'))   cls = 'cyan';
    else if (msg.includes('[WARN]')) cls = 'orange';
    else if (msg.includes('[*]'))    cls = 'dim';
  }
  const classMap = { green:'line-green', red:'line-red', cyan:'line-cyan', orange:'line-orange', dim:'line-dim', default:'' };
  if (classMap[cls]) line.className = classMap[cls];
  line.textContent = msg;
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}

function onScanDone(result) {
  addLog('', 'dim');
  addLog('─'.repeat(60), 'dim');
  if (result.status === 'success') {
    const v = result.vulnerabilities;
    addLog('[✓] Scan complete — ' + (v > 0 ? v + ' XSS finding' + (v !== 1 ? 's' : '') + ' detected' : 'No vulnerabilities found'), 'green');
    addLog('[✓] Duration: ' + (result.duration?.toFixed(2)) + 's', 'green');
    addLog('[✓] View full report in Scan History', 'dim');
    if (v > 0) {
      toast(v + ' XSS vulnerabilit' + (v !== 1 ? 'ies' : 'y') + ' found — review the report', 'warning');
    } else {
      toast('Scan complete — no XSS vulnerabilities detected', 'success');
    }
  } else {
    addLog('[ERROR] Scan failed — check your target URL and network connection', 'red');
    toast('Scan failed. Check the log for details.', 'error');
  }
  resetScanUI();
}

function resetScanUI() {
  setButtonLoading(document.getElementById('start-btn'), false);
  document.getElementById('stop-btn').disabled  = true;
  document.getElementById('scan-url').disabled  = false;
}

async function stopScan() {
  if (scanEventSource) scanEventSource.close();
  try {
    await api('POST', '/api/v1/scan/stop');
    addLog('[!] Scan stopped by user', 'orange');
    toast('Scan stopped', 'warning');
  } catch (e) {}
  resetScanUI();
}
