// XSSniper — History page logic

/* ── Init: runs on both hard load and HTMX navigation ───────────────────── */
function _initHistory() {
  if (!document.getElementById('status-filter')) return;
  _formatIsoDates();

  // Filter controls
  document.getElementById('status-filter')
    ?.addEventListener('change', filterTable);
  document.getElementById('vuln-filter')
    ?.addEventListener('change', filterTable);
  document.getElementById('search-input')
    ?.addEventListener('input', filterTable);

  // Bulk action bar
  document.getElementById('bulk-delete-btn')
    ?.addEventListener('click', bulkDelete);
  document.getElementById('bulk-cancel-btn')
    ?.addEventListener('click', clearSelection);
  document.getElementById('check-all')
    ?.addEventListener('change', e => toggleAll(e.target));

  // Row-level actions — event delegation on table body
  const tbody = document.querySelector('#history-table tbody');
  if (tbody) {
    tbody.addEventListener('change', e => {
      if (e.target.classList.contains('scan-check')) updateBulkBar();
    });
    tbody.addEventListener('click', e => {
      const viewBtn   = e.target.closest('[data-action="view"]');
      const deleteBtn = e.target.closest('[data-action="delete"]');
      if (viewBtn)   viewReport(+viewBtn.dataset.id);
      if (deleteBtn) deleteHistoryScan(+deleteBtn.dataset.id, deleteBtn);
    });
  }

  // Report modal buttons
  document.querySelector('#report-modal .modal-close')
    ?.addEventListener('click', () => closeModal('report-modal'));
  document.querySelector('#report-modal [data-action="close-modal"]')
    ?.addEventListener('click', () => closeModal('report-modal'));
  document.getElementById('copy-log-btn')
    ?.addEventListener('click', copyModalLog);
}

document.addEventListener('DOMContentLoaded', _initHistory);
document.addEventListener('htmx:afterSettle', _initHistory);

/* ── Table filter ────────────────────────────────────────────────────────── */
function filterTable() {
  const q  = (document.getElementById('search-input')?.value || '').toLowerCase();
  const st = document.getElementById('status-filter')?.value  || '';
  const vf = document.getElementById('vuln-filter')?.value    || '';
  let visible = 0;
  document.querySelectorAll('#history-table tbody tr[data-id]').forEach(row => {
    const url = (row.dataset.url || '').toLowerCase();
    const ok  = url.includes(q)
             && (!st || row.dataset.status === st)
             && (!vf || (vf === 'vuln' ? +row.dataset.vulns > 0 : +row.dataset.vulns === 0));
    row.style.display = ok ? '' : 'none';
    if (ok) visible++;
  });
  const noResults = document.getElementById('no-results-row');
  if (noResults) noResults.style.display = visible === 0 ? '' : 'none';
}

/* ── Checkbox helpers ────────────────────────────────────────────────────── */
function toggleAll(cb) {
  document.querySelectorAll('.scan-check').forEach(c => { c.checked = cb.checked; });
  updateBulkBar();
}

function updateBulkBar() {
  const sel = document.querySelectorAll('.scan-check:checked');
  const bar = document.getElementById('bulk-bar');
  const cnt = document.getElementById('bulk-count');
  if (sel.length > 0) {
    bar?.classList.add('visible');
    if (cnt) cnt.textContent = sel.length + ' selected';
  } else {
    bar?.classList.remove('visible');
    const ca = document.getElementById('check-all');
    if (ca) ca.checked = false;
  }
}

function clearSelection() {
  document.querySelectorAll('.scan-check, #check-all').forEach(c => { c.checked = false; });
  document.getElementById('bulk-bar')?.classList.remove('visible');
}

/* ── Bulk delete ─────────────────────────────────────────────────────────── */
async function bulkDelete() {
  const checked = [...document.querySelectorAll('.scan-check:checked')];
  if (!checked.length) return;
  const confirmed = await window.showConfirm(
    'Delete ' + checked.length + ' Scan' + (checked.length !== 1 ? 's' : ''),
    'This will permanently remove ' + checked.length + ' scan record' + (checked.length !== 1 ? 's' : '') + ' including all logs and findings. This cannot be undone.',
    'Delete ' + checked.length + ' Scan' + (checked.length !== 1 ? 's' : '')
  );
  if (!confirmed) return;

  let deleted = 0;
  const removePromises = [];
  for (const cb of checked) {
    try {
      await api('DELETE', '/api/v1/history/' + cb.dataset.id);
      const row = cb.closest('tr');
      if (row) removePromises.push(_fadeOutRow(row));
      deleted++;
    } catch (e) {}
  }
  await Promise.all(removePromises);
  clearSelection();
  toast(deleted + ' scan' + (deleted !== 1 ? 's' : '') + ' deleted', 'success');
}

/* ── Single row delete ───────────────────────────────────────────────────── */
async function deleteHistoryScan(id, btn) {
  const confirmed = await window.showConfirm(
    'Delete Scan Record',
    'Permanently remove this scan record, including all log output and findings? This cannot be undone.',
    'Delete Record'
  );
  if (!confirmed) return;
  try {
    await api('DELETE', '/api/v1/history/' + id);
    const row = btn.closest('tr');
    if (row) await _fadeOutRow(row);
    toast('Scan record deleted', 'success');
  } catch (err) {
    toast('Could not delete scan: ' + err.message, 'error');
  }
}

/** Animate a table row out, then remove it from the DOM */
function _fadeOutRow(row) {
  return new Promise(resolve => {
    row.classList.add('row-removing');
    row.addEventListener('animationend', () => { row.remove(); resolve(); }, { once: true });
  });
}

/* ── Copy modal log ──────────────────────────────────────────────────────── */
function copyModalLog() {
  const btn = document.getElementById('copy-log-btn');
  const el  = document.getElementById('modal-log');
  navigator.clipboard.writeText(el?.innerText || '')
    .then(() => { toast('Log copied', 'success'); _flashCopied(btn); })
    .catch(() => toast('Copy failed', 'error'));
}

/** Briefly add .btn--copied to a button, then remove it */
function _flashCopied(btn) {
  if (!btn) return;
  btn.classList.add('btn--copied');
  const prev = btn.textContent;
  btn.textContent = '✓ Copied';
  setTimeout(() => {
    btn.classList.remove('btn--copied');
    btn.textContent = prev;
  }, 1500);
}

/* ── View report ─────────────────────────────────────────────────────────── */
async function viewReport(scanId) {
  try {
    const d = await api('GET', '/api/v1/history/' + scanId);
    document.getElementById('modal-url').textContent      = d.url;
    document.getElementById('modal-date').textContent     = d.date;
    const _badge = document.createElement('span');
    _badge.className = 'badge badge-' + (d.status === 'Completed' ? 'green' : 'red');
    _badge.textContent = d.status;
    const _statusEl = document.getElementById('modal-status');
    _statusEl.textContent = '';
    _statusEl.appendChild(_badge);
    document.getElementById('modal-vulns').textContent    = d.vulnerabilities;
    document.getElementById('modal-duration').textContent = d.duration ? d.duration.toFixed(2) + 's' : 'N/A';

    const logEl = document.getElementById('modal-log');
    logEl.innerHTML = '';
    (d.log_output || 'No log available').split('\n').forEach(line => {
      if (!line.trim()) return;
      const el = document.createElement('div');
      if      (line.includes('[+]') || line.includes('VULNERABILITY') || line.includes('FOUND')) el.className = 'line-green';
      else if (line.includes('[ERROR]'))  el.className = 'line-red';
      else if (line.includes('[ML]'))     el.className = 'line-cyan';
      else if (line.includes('[WARN]'))   el.className = 'line-orange';
      else if (line.includes('[*]'))      el.className = 'line-dim';
      el.textContent = line;
      logEl.appendChild(el);
    });

    document.getElementById('export-csv-btn').onclick = () => exportCSV(scanId);
    const pdfBtn = document.getElementById('export-pdf-btn');
    if (pdfBtn) pdfBtn.onclick = () => exportPDF(scanId);
    openModal('report-modal');
  } catch (err) { toast('Failed to load report', 'error'); }
}

function exportCSV(scanId) { window.location.href = '/api/v1/csv/' + scanId;  toast('Downloading CSV…',    'success'); }
function exportPDF(scanId) { window.location.href = '/api/v1/pdf/' + scanId;  toast('Generating PDF…',    'info'); }

/* ── Format ISO dates to human-readable ─────────────────────────────────── */
function _formatIsoDates() {
  const isoRe = /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/g;
  document.querySelectorAll('td.cell-date, .history-date, [data-iso-date]').forEach(el => {
    el.textContent = el.textContent.replace(isoRe, iso => {
      try {
        return new Date(iso).toLocaleString('en-GB', {
          day: '2-digit', month: 'short', year: 'numeric',
          hour: '2-digit', minute: '2-digit', hour12: false,
        });
      } catch { return iso; }
    });
  });
  // Also catch any td that contains a raw ISO date
  document.querySelectorAll('#history-table tbody td:nth-child(2)').forEach(el => {
    el.textContent = el.textContent.replace(isoRe, iso => {
      try {
        return new Date(iso).toLocaleString('en-GB', {
          day: '2-digit', month: 'short', year: 'numeric',
          hour: '2-digit', minute: '2-digit', hour12: false,
        });
      } catch { return iso; }
    });
  });
}
