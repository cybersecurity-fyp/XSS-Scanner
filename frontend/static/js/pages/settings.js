// XSSniper — Settings page logic

/* ── Server-side preferences injected via JSON script block ─────────────── */
let _serverPrefs = {};

function _initSettings() {
  if (!document.getElementById('save-settings-btn')) return;
  try {
    const raw = document.getElementById('settings-prefs-data');
    if (raw) _serverPrefs = JSON.parse(raw.textContent) || {};
  } catch (e) {}
  _loadSettings();
  _bindSettingsEvents();
}

document.addEventListener('DOMContentLoaded', _initSettings);
document.addEventListener('htmx:afterSettle', _initSettings);

/* ── Event wiring (replaces all inline onclick/oninput in template) ──────── */
function _bindSettingsEvents() {
  // Save preferences button
  document.getElementById('save-settings-btn')
    ?.addEventListener('click', saveSettings);

  // Clear history button
  document.getElementById('clear-history-btn')
    ?.addEventListener('click', _confirmClearHistory);

  // Delete account: open modal
  document.getElementById('open-delete-modal-btn')
    ?.addEventListener('click', () => openModal('delete-account-modal'));

  // Delete account modal: confirm/cancel
  document.getElementById('delete-account-modal')
    ?.querySelector('.modal-close')
    ?.addEventListener('click', () => closeModal('delete-account-modal'));
  document.getElementById('confirm-delete-btn')
    ?.addEventListener('click', confirmDeleteAccount);
  document.getElementById('cancel-delete-btn')
    ?.addEventListener('click', () => closeModal('delete-account-modal'));

  // Change password
  document.getElementById('cp-btn')
    ?.addEventListener('click', doChangePassword);
  document.getElementById('cp-new')
    ?.addEventListener('input', checkCpStrength);

  // Profile edit buttons
  document.getElementById('edit-username-btn')
    ?.addEventListener('click', () => toggleEditField('username'));
  document.getElementById('edit-email-btn')
    ?.addEventListener('click', () => toggleEditField('email'));
  document.getElementById('save-profile-btn')
    ?.addEventListener('click', saveProfile);
  document.getElementById('cancel-profile-btn')
    ?.addEventListener('click', cancelProfileEdit);

  // Password visibility toggles (settings page has several)
  document.querySelectorAll('[data-eye]').forEach(btn => {
    btn.addEventListener('click', () => togglePassword(btn.dataset.eye));
  });

  // ML confidence slider live label
  const confRange = document.getElementById('conf-range');
  const confVal   = document.getElementById('conf-val');
  if (confRange && confVal) {
    confRange.addEventListener('input', () => {
      confVal.textContent = parseFloat(confRange.value).toFixed(1);
    });
  }
}

/* ── Save / Load preferences ─────────────────────────────────────────────── */
async function saveSettings() {
  const btn   = document.getElementById('save-settings-btn');
  const prefs = {
    level:     document.getElementById('s-level').value,
    threads:   document.getElementById('s-threads').value,
    timeout:   document.getElementById('s-timeout').value,
    delay:     document.getElementById('s-delay').value,
    prefilter: document.getElementById('s-prefilter').value,
  };
  // Cache locally
  localStorage.setItem('xss-level',     prefs.level);
  localStorage.setItem('xss-threads',   prefs.threads);
  localStorage.setItem('xss-timeout',   prefs.timeout);
  localStorage.setItem('xss-delay',     prefs.delay);
  localStorage.setItem('xss-prefilter', prefs.prefilter);
  // Sync to server
  setButtonLoading(btn, true);
  try {
    await fetch('/api/v1/account/preferences', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(prefs),
    });
    toast('Settings saved to your account', 'success');
  } catch (e) {
    toast('Saved locally (server sync failed)', 'warning');
  }
  setButtonLoading(btn, false);
}

function _loadSettings() {
  const level   = _serverPrefs.level    || localStorage.getItem('xss-level');
  const threads = _serverPrefs.threads  || localStorage.getItem('xss-threads');
  const timeout = _serverPrefs.timeout  || localStorage.getItem('xss-timeout');
  const delay   = _serverPrefs.delay    || localStorage.getItem('xss-delay');
  const pre     = _serverPrefs.prefilter || localStorage.getItem('xss-prefilter');

  if (level)   document.getElementById('s-level').value   = level;
  if (threads) document.getElementById('s-threads').value = threads;
  if (timeout) document.getElementById('s-timeout').value = timeout;
  if (delay)   document.getElementById('s-delay').value   = delay;
  if (pre === 'true') {
    document.getElementById('t-prefilter')?.classList.add('on');
    const inp = document.getElementById('s-prefilter');
    if (inp) inp.value = 'true';
  }
}

/* ── Clear scan history ──────────────────────────────────────────────────── */
async function _confirmClearHistory() {
  const confirmed = await window.showConfirm(
    'Clear All Scan History',
    'Permanently delete every scan record, including logs and vulnerability findings. This cannot be undone.',
    'Clear All History'
  );
  if (!confirmed) return;
  await clearHistory();
}

async function clearHistory() {
  try {
    const history = await fetch('/api/v1/history').then(r => r.json());
    if (!history.length) { toast('No scan history to clear', 'info'); return; }
    let failed = 0;
    for (const scan of history) {
      const res = await fetch('/api/v1/history/' + scan.id, { method: 'DELETE' });
      if (!res.ok) failed++;
    }
    toast(
      failed === 0 ? 'All scan history cleared' : 'Cleared with ' + failed + ' error(s)',
      failed === 0 ? 'success' : 'warning'
    );
  } catch (err) {
    toast('Failed to clear history', 'error');
  }
}

/* ── Password strength checker ───────────────────────────────────────────── */
function checkCpStrength() {
  const p = document.getElementById('cp-new').value;
  const checks = {
    'cp-ic-len': p.length >= 8,
    'cp-ic-up':  /[A-Z]/.test(p),
    'cp-ic-lo':  /[a-z]/.test(p),
    'cp-ic-nu':  /[0-9]/.test(p),
    'cp-ic-sy':  /[^A-Za-z0-9]/.test(p),
  };
  for (const id in checks) {
    const el = document.getElementById(id);
    if (!el) continue;
    el.textContent = checks[id] ? '✓' : '○';
    el.style.color = checks[id] ? 'var(--accent)' : 'var(--textDim)';
  }
}

/* ── Change password ─────────────────────────────────────────────────────── */
async function doChangePassword() {
  const current = document.getElementById('cp-current').value;
  const newPw   = document.getElementById('cp-new').value;
  const confirm = document.getElementById('cp-confirm').value;
  const btn     = document.getElementById('cp-btn');
  const errEl   = document.getElementById('cp-error');
  const sucEl   = document.getElementById('cp-success');

  _hide(errEl); _hide(sucEl);
  if (!current)  { _showEl(errEl, 'Enter your current password to continue.'); return; }
  if (!newPw)    { _showEl(errEl, 'Enter a new password.'); return; }
  if (!confirm)  { _showEl(errEl, 'Re-enter your new password to confirm.'); return; }
  setButtonLoading(btn, true);
  try {
    const res  = await fetch('/api/v1/account/change-password', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ current_password: current, new_password: newPw, confirm_password: confirm }),
    });
    const data = await res.json();
    if (!res.ok) {
      _showEl(errEl, data.detail || 'Password update failed.');
    } else {
      _showEl(sucEl, '✓ Password changed successfully!');
      document.getElementById('cp-current').value = '';
      document.getElementById('cp-new').value     = '';
      document.getElementById('cp-confirm').value = '';
      checkCpStrength();
    }
  } catch (err) {
    _showEl(errEl, 'Connection error — check your network and try again.');
  }
  setButtonLoading(btn, false);
}

/* ── Profile edit ────────────────────────────────────────────────────────── */
let _editingField = null;

function toggleEditField(field) {
  _editingField = field;
  _toggle('username-display', field !== 'username');
  _toggle('username-edit',    field === 'username');
  _toggle('email-display',    field !== 'email');
  _toggle('email-edit',       field === 'email');
  _toggle('profile-edit-panel', true);
  document.getElementById(field === 'username' ? 'new-username' : 'new-email')?.focus();
}

function cancelProfileEdit() {
  _editingField = null;
  _toggle('username-display', true);
  _toggle('username-edit',    false);
  _toggle('email-display',    true);
  _toggle('email-edit',       false);
  _toggle('profile-edit-panel', false);
  _hide(document.getElementById('profile-error'));
  _hide(document.getElementById('profile-success'));
}

async function saveProfile() {
  if (!_editingField) return;
  const value    = document.getElementById('new-' + _editingField)?.value.trim();
  const password = document.getElementById('profile-confirm-pass')?.value;
  const errEl    = document.getElementById('profile-error');
  const sucEl    = document.getElementById('profile-success');

  _hide(errEl); _hide(sucEl);
  if (!value)    { _showEl(errEl, 'New ' + _editingField + ' cannot be empty.'); return; }
  if (!password) { _showEl(errEl, 'Enter your current password to confirm the change.'); return; }
  try {
    const res  = await fetch('/api/v1/account/update-profile', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ field: _editingField, value, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      _showEl(errEl, data.detail || 'Update failed.');
    } else {
      _showEl(sucEl, '✓ ' + data.message);
      document.getElementById(_editingField + '-static').value = value;
      cancelProfileEdit();
      toast(data.message, 'success');
    }
  } catch (e) {
    _showEl(errEl, 'Connection error — check your network and try again.');
  }
}

/* ── Delete account ──────────────────────────────────────────────────────── */
async function confirmDeleteAccount() {
  const username = document.getElementById('delete-confirm-username')?.value.trim();
  const password = document.getElementById('delete-password')?.value;
  const errEl    = document.getElementById('delete-error');

  _hide(errEl);
  if (!username) { _showEl(errEl, 'Type your username to confirm deletion.'); return; }
  if (!password) { _showEl(errEl, 'Enter your password to authorise deletion.'); return; }
  try {
    const res  = await fetch('/api/v1/account/delete', {
      method:  'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ password, confirm_username: username }),
    });
    const data = await res.json();
    if (!res.ok) {
      _showEl(errEl, data.detail || 'Deletion failed.');
    } else {
      toast('Account deleted. Redirecting…', 'info');
      setTimeout(() => { window.location.href = '/login'; }, 1500);
    }
  } catch (e) {
    _showEl(errEl, 'Connection error — check your network and try again.');
  }
}

/* ── DOM helpers ─────────────────────────────────────────────────────────── */
function _hide(el) { if (el) el.classList.add('is-hidden'); }
function _showEl(el, msg) {
  if (!el) return;
  el.textContent = msg;
  el.classList.remove('is-hidden');
}
/** _toggle(id, visible) — show or hide an element by id */
function _toggle(id, visible) {
  const el = document.getElementById(id);
  if (!el) return;
  if (visible) el.classList.remove('is-hidden');
  else         el.classList.add('is-hidden');
}
