// XSSniper Frontend JS — shared utilities
// Page-specific logic: pages/auth.js, pages/scan.js, pages/history.js, pages/admin.js

/* ═══════════════════════════════════
   THEME  (delegates to core/theme.js)
═══════════════════════════════════ */
// core/theme.js runs in <head> and defines Theme, setTheme, toggleTheme.
// These stubs cover pages that don't extend base.html.
if (typeof setTheme    === 'undefined') { function setTheme(t)  { document.documentElement.setAttribute('data-theme',t); localStorage.setItem('xss-theme',t); } }
if (typeof toggleTheme === 'undefined') { function toggleTheme() { setTheme(document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark'); } }

/* ═══════════════════════════════════
   API Helper
═══════════════════════════════════ */
async function api(method, url, data = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (data) opts.body = JSON.stringify(data);
  const res = await fetch(url, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

/* ═══════════════════════════════════
   Toast Notifications
═══════════════════════════════════ */
function toast(msg, type) {
  type = type || 'info';
  const icons      = { success: '✓', error: '✗', info: 'ℹ', warning: '⚠' };
  const iconColors = { success: '#00e87a', error: '#ff4466', info: '#22d3ee', warning: '#ffb020' };

  const el = document.createElement('div');
  el.className = 'toast-item ' + type;

  const iconSpan = document.createElement('span');
  iconSpan.className   = 'toast-icon';
  iconSpan.style.color = iconColors[type] || iconColors.info;
  iconSpan.textContent = icons[type] || icons.info;

  const msgSpan = document.createElement('span');
  msgSpan.textContent = msg;  // textContent prevents XSS

  el.appendChild(iconSpan);
  el.appendChild(msgSpan);

  const wrap = document.getElementById('toast-wrap');
  if (wrap) {
    wrap.appendChild(el);
  } else {
    el.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;';
    document.body.appendChild(el);
  }

  setTimeout(() => {
    el.style.opacity    = '0';
    el.style.transform  = 'translateY(6px)';
    el.style.transition = 'opacity 0.25s, transform 0.25s';
    setTimeout(() => el.remove(), 260);
  }, 3500);
}

/* ═══════════════════════════════════
   Toggle Switches
═══════════════════════════════════ */
function initToggles() {
  document.querySelectorAll('.toggle').forEach(t => {
    // ARIA switch role + keyboard accessibility
    t.setAttribute('role', 'switch');
    t.setAttribute('tabindex', '0');
    t.setAttribute('aria-checked', t.classList.contains('on') ? 'true' : 'false');

    function _activate() {
      t.classList.toggle('on');
      const isOn = t.classList.contains('on');
      t.setAttribute('aria-checked', String(isOn));
      const inp = document.getElementById(t.dataset.for);
      if (inp) inp.value = isOn ? 'true' : 'false';
    }

    t.addEventListener('click', _activate);
    t.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); _activate(); }
    });
  });
}

/**
 * toggleOpt(toggleId, hiddenInputId)
 * Shared helper used by scan and settings pages. Toggles the visual .toggle
 * element and keeps the paired hidden input value in sync.
 */
function toggleOpt(toggleId, hiddenInputId) {
  const t = document.getElementById(toggleId);
  if (!t) return;
  t.classList.toggle('on');
  const inp = document.getElementById(hiddenInputId);
  if (inp) inp.value = t.classList.contains('on') ? 'true' : 'false';
}

/* ═══════════════════════════════════
   Tabs
═══════════════════════════════════ */
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const g = btn.dataset.group;
      document.querySelectorAll(`.tab-btn[data-group="${g}"]`).forEach(b => b.classList.remove('active'));
      document.querySelectorAll(`.tab-panel[data-group="${g}"]`).forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(btn.dataset.target)?.classList.add('active');
    });
  });
}

/* ═══════════════════════════════════
   Modal  (with focus trap)
═══════════════════════════════════ */
let _modalFocusTrap = null;

function openModal(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.add('open');
  el.setAttribute('role', 'dialog');
  el.setAttribute('aria-modal', 'true');
  const focusable = el.querySelectorAll(
    'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'
  );
  const first = focusable[0];
  const last  = focusable[focusable.length - 1];
  if (first) first.focus();
  _modalFocusTrap = e => {
    if (e.key !== 'Tab') return;
    if (e.shiftKey) { if (document.activeElement === first) { e.preventDefault(); last?.focus(); } }
    else            { if (document.activeElement === last)  { e.preventDefault(); first?.focus(); } }
  };
  document.addEventListener('keydown', _modalFocusTrap);
}

function closeModal(id) {
  document.getElementById(id)?.classList.remove('open');
  if (_modalFocusTrap) { document.removeEventListener('keydown', _modalFocusTrap); _modalFocusTrap = null; }
}

document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
    if (_modalFocusTrap) { document.removeEventListener('keydown', _modalFocusTrap); _modalFocusTrap = null; }
  }
});

/* ═══════════════════════════════════
   Password Show/Hide
═══════════════════════════════════ */
function togglePassword(inputId) {
  const inp  = document.getElementById(inputId);
  const icon = document.querySelector(`[data-eye="${inputId}"], [onclick*="togglePassword('${inputId}')"]`);
  if (!inp) return;
  if (inp.type === 'password') { inp.type = 'text';     if (icon) icon.textContent = '🙈'; }
  else                         { inp.type = 'password'; if (icon) icon.textContent = '👁'; }
}

/* ═══════════════════════════════════
   SIDEBAR (desktop collapse + mobile drawer)
═══════════════════════════════════ */
const _isMobile = () => window.innerWidth <= 768;
let _sbCollapsed  = false;
let _sbDrawerOpen = false;

function _initSidebar() {
  if (localStorage.getItem('sbCollapsed') === '1') {
    _sbCollapsed = true;
    document.getElementById('app-shell')?.classList.add('sb-collapsed');
    
    // Set aria state correctly on init
    document.querySelectorAll('.sidebar-toggle-btn').forEach(btn => {
      btn.classList.add('is-open');
      btn.setAttribute('aria-expanded', 'false');
    });
  }
}

function toggleSidebar() {
  _isMobile() ? (_sbDrawerOpen ? _closeMobileDrawer() : _openMobileDrawer()) : _toggleDesktopCollapse();
}

function _toggleDesktopCollapse() {
  _sbCollapsed = !_sbCollapsed;
  document.getElementById('app-shell')?.classList.toggle('sb-collapsed', _sbCollapsed);
  
  // Manage ARIA states when collapsed/expanded
  document.querySelectorAll('.sidebar-toggle-btn').forEach(btn => {
    btn.classList.toggle('is-open', _sbCollapsed);
    btn.setAttribute('aria-expanded', _sbCollapsed ? 'false' : 'true');
  });
  
  localStorage.setItem('sbCollapsed', _sbCollapsed ? '1' : '0');
}

function _openMobileDrawer() {
  document.getElementById('sidebar')?.classList.add('sidebar-open');
  document.getElementById('sidebar-overlay')?.classList.add('overlay-open');
  document.body.style.overflow = 'hidden';
  _sbDrawerOpen = true;
  
  const mobileToggle = document.getElementById('mobile-sidebar-toggle-btn');
  if(mobileToggle) mobileToggle.setAttribute('aria-expanded', 'true');
}

function closeSidebar()      { _closeMobileDrawer(); }
function _closeMobileDrawer() {
  document.getElementById('sidebar')?.classList.remove('sidebar-open');
  document.getElementById('sidebar-overlay')?.classList.remove('overlay-open');
  document.body.style.overflow = '';
  _sbDrawerOpen = false;
  
  const mobileToggle = document.getElementById('mobile-sidebar-toggle-btn');
  if(mobileToggle) mobileToggle.setAttribute('aria-expanded', 'false');
}

function onNavClick() { if (_isMobile()) _closeMobileDrawer(); }

// ── Utilities & Authentication ──

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => { clearTimeout(timeout); func(...args); };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

async function doLogout() {
  try { await fetch('/api/v1/auth/logout', { method: 'POST' }); } catch (e) {}
  window.location.href = '/login';
}

/* ═══════════════════════════════════
   Button Ripple
═══════════════════════════════════ */
function _initRipple() {
  document.addEventListener('click', e => {
    const btn = e.target.closest('.btn');
    if (!btn || btn.disabled || btn.classList.contains('btn--loading')) return;

    const wave   = document.createElement('span');
    const rect   = btn.getBoundingClientRect();
    const size   = Math.max(rect.width, rect.height) * 2;
    wave.className = 'ripple-wave';
    wave.style.cssText = [
      'width:'  + size + 'px',
      'height:' + size + 'px',
      'left:'   + (e.clientX - rect.left  - size / 2) + 'px',
      'top:'    + (e.clientY - rect.top   - size / 2) + 'px',
    ].join(';');
    btn.appendChild(wave);
    wave.addEventListener('animationend', () => wave.remove(), { once: true });
  });
}

/* ═══════════════════════════════════
   Button Loading Helper
═══════════════════════════════════ */
/**
 * setButtonLoading(btn, loading)
 * Toggles the .btn--loading class and disabled state.
 * The original text is stored in data-label and restored on un-load.
 */
function setButtonLoading(btn, loading) {
  if (!btn) return;
  if (loading) {
    btn.dataset.label = btn.textContent.trim();
    btn.classList.add('btn--loading');
    btn.disabled = true;
  } else {
    btn.classList.remove('btn--loading');
    btn.disabled = false;
  }
}

// ── Bind Global Listeners ──
window.addEventListener('resize', debounce(() => {
  if (!_isMobile()) _closeMobileDrawer();
}, 150));

document.addEventListener('keydown', e => { if (e.key === 'Escape') { _closeMobileDrawer(); closeModal(); } });

/* ═══════════════════════════════════
   CLOCK
═══════════════════════════════════ */
function _startClock() {
  const tick = () => {
    const el = document.getElementById('topbar-time');
    if (el) el.textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
    setTimeout(tick, 1000);
  };
  tick();
}

/* ═══════════════════════════════════
   Confirm Modal  (Promise-based)
═══════════════════════════════════ */
/**
 * window.showConfirm(title, message, confirmLabel)
 * Uses the #confirm-modal in base.html.
 * Returns a Promise<boolean> — true if the user clicked the confirm button.
 */
window.showConfirm = function showConfirm(title, message, confirmLabel) {
  return new Promise(resolve => {
    const modal     = document.getElementById('confirm-modal');
    const titleEl   = document.getElementById('confirm-title');
    const msgEl     = document.getElementById('confirm-msg');
    const okBtn     = document.getElementById('confirm-ok-btn');
    const cancelBtn = document.getElementById('confirm-cancel-btn');
    if (!modal) { resolve(window.confirm(message)); return; }

    if (titleEl) titleEl.textContent = title || 'Confirm';
    if (msgEl)   msgEl.textContent   = message || 'Are you sure?';
    if (okBtn)   okBtn.textContent   = confirmLabel || 'Confirm';

    // Focus trap helpers
    const _focusable = modal.querySelectorAll('button:not([disabled])');
    const _first = _focusable[0];
    const _last  = _focusable[_focusable.length - 1];

    function _trapFocus(e) {
      if (e.key !== 'Tab') return;
      if (e.shiftKey) { if (document.activeElement === _first) { e.preventDefault(); _last?.focus(); } }
      else            { if (document.activeElement === _last)  { e.preventDefault(); _first?.focus(); } }
    }
    function _escapeKey(e) { if (e.key === 'Escape') _close(false); }

    modal.style.display = 'flex';
    requestAnimationFrame(() => {
      modal.style.opacity = '1';
      const inner = modal.querySelector('.modal');
      if (inner) inner.style.transform = 'translateY(0)';
      cancelBtn?.focus();  // focus Cancel by default (safer default)
    });

    document.addEventListener('keydown', _trapFocus);
    document.addEventListener('keydown', _escapeKey);

    function _close(result) {
      modal.style.opacity = '0';
      const inner = modal.querySelector('.modal');
      if (inner) inner.style.transform = 'translateY(20px)';
      setTimeout(() => { modal.style.display = 'none'; }, 200);
      okBtn.removeEventListener('click', _ok);
      cancelBtn.removeEventListener('click', _cancel);
      document.removeEventListener('keydown', _trapFocus);
      document.removeEventListener('keydown', _escapeKey);
      resolve(result);
    }
    function _ok()     { _close(true);  }
    function _cancel() { _close(false); }

    okBtn.addEventListener('click', _ok);
    cancelBtn.addEventListener('click', _cancel);
  });
};

/* ═══════════════════════════════════
   Sidebar keyboard navigation
═══════════════════════════════════ */
/**
 * Up/Down arrow keys move focus between nav items in the sidebar.
 * Home/End jump to first/last. Works even when sidebar is collapsed
 * (the items are still focusable via keyboard even if visually icon-only).
 */
function _initNavKeyboard() {
  const nav = document.getElementById('sidebar-nav');
  if (!nav) return;
  nav.addEventListener('keydown', e => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp' &&
        e.key !== 'Home' && e.key !== 'End') return;
    const items = [...nav.querySelectorAll('.nav-item')];
    if (!items.length) return;
    const idx = items.indexOf(document.activeElement);
    e.preventDefault();
    if      (e.key === 'Home')      items[0].focus();
    else if (e.key === 'End')       items[items.length - 1].focus();
    else if (e.key === 'ArrowDown') items[Math.min(idx + 1, items.length - 1)]?.focus();
    else if (e.key === 'ArrowUp')   items[Math.max(idx - 1, 0)]?.focus();
  });
}

/* ═══════════════════════════════════
   Global click delegation
   Handles all persistent UI controls via a single document listener so they
   work regardless of HTMX content swaps or script load order.
═══════════════════════════════════ */
document.addEventListener('click', function(e) {
  if (e.target.closest('.sidebar-toggle-btn')) { toggleSidebar();   return; }
  if (e.target.closest('#sidebar-overlay'))    { closeSidebar();    return; }
  if (e.target.closest('#logout-btn'))         { doLogout();        return; }
  if (e.target.closest('#theme-toggle'))       { toggleTheme();     return; }
  if (e.target.closest('.nav-item') && _isMobile()) { _closeMobileDrawer(); }
});

/* ═══════════════════════════════════
   DOMContentLoaded
═══════════════════════════════════ */
document.addEventListener('htmx:afterSettle', () => {
  initToggles();
  initTabs();
});

document.addEventListener('DOMContentLoaded', () => {
  initToggles();
  initTabs();
  _initSidebar();
  _startClock();
  _initRipple();
  _initNavKeyboard();
});
