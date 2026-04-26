// XSSniper Frontend TS — core application layer
// Strict typed interfaces mapping legacy backend stats

interface DailyActivity {
  label: string;
  scans: number;
  vulns: number;
}

interface AppStats {
  total: number;
  vulns: number;
  clean: number;
  health: number;
}
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
/* ═══════════════════════════════════
   API Helper (Typed)
═══════════════════════════════════ */
async function api<T>(method: string, url: string, data: any = null): Promise<T> {
  const opts: RequestInit = { method, headers: { 'Content-Type': 'application/json' } };
  if (data) opts.body = JSON.stringify(data);
  const res = await fetch(url, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json() as Promise<T>;
}

/* ═══════════════════════════════════
   Toast Notifications
═══════════════════════════════════ */
function toast(msg, type) {
  type = type || 'info';
  const icons: Record<string, string>      = { success: '✓', error: '✗', info: 'ℹ', warning: '⚠' };
  const iconColors: Record<string, string> = { success: '#00e87a', error: '#ff4466', info: '#22d3ee', warning: '#ffb020' };

  const el = document.createElement('div') as HTMLDivElement;
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
   Custom Modals & Friction
═══════════════════════════════════ */
function showConfirm(title: string, message: string, btnText: string = 'Confirm'): Promise<boolean> {
  return new Promise(resolve => {
    const overlay = document.getElementById('confirm-modal') as HTMLElement;
    const box = overlay.querySelector('.modal') as HTMLElement;
    
    document.getElementById('confirm-title')!.textContent = title;
    document.getElementById('confirm-msg')!.textContent = message;
    const okBtn = document.getElementById('confirm-ok-btn') as HTMLButtonElement;
    okBtn.textContent = btnText;

    const cleanup = () => {
      overlay.style.opacity = '0';
      box.style.transform = 'translateY(20px)';
      setTimeout(() => overlay.style.display = 'none', 200);
      okBtn.replaceWith(okBtn.cloneNode(true));
      const cancelBtn = document.getElementById('confirm-cancel-btn')!;
      cancelBtn.replaceWith(cancelBtn.cloneNode(true));
    };

    overlay.style.display = 'flex';
    // Trigger reflow
    void overlay.offsetWidth;
    overlay.style.opacity = '1';
    box.style.transform = 'translateY(0)';

    document.getElementById('confirm-cancel-btn')!.addEventListener('click', () => { cleanup(); resolve(false); }, { once: true });
    okBtn.addEventListener('click', () => { cleanup(); resolve(true); }, { once: true });
  });
}

// Attach globally for inline HTML usage if necessary
(window as any).showConfirm = showConfirm;

/* ═══════════════════════════════════
   Toggle Switches
═══════════════════════════════════ */
function initToggles() {
  document.querySelectorAll<HTMLElement>('.toggle').forEach(t => {
    t.addEventListener('click', () => {
      t.classList.toggle('on');
      const inp = document.getElementById(t.dataset.for!) as HTMLInputElement;
      if (inp) inp.value = t.classList.contains('on') ? 'true' : 'false';
    });
  });
}

/* ═══════════════════════════════════
   Tabs
═══════════════════════════════════ */
function initTabs() {
  document.querySelectorAll<HTMLElement>('.tab-btn').forEach(btn => {
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
let _modalFocusTrap: ((e: KeyboardEvent) => void) | null = null;

function openModal(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.add('open');
  el.setAttribute('role', 'dialog');
  el.setAttribute('aria-modal', 'true');
  const focusable = Array.from(el.querySelectorAll<HTMLElement>(
    'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'
  ));
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

function closeModal(id?: string) {
  if (id) {
    document.getElementById(id)?.classList.remove('open');
  } else {
    document.querySelectorAll('.modal-overlay.open').forEach(el => el.classList.remove('open'));
  }
  if (_modalFocusTrap) { document.removeEventListener('keydown', _modalFocusTrap); _modalFocusTrap = null; }
}

document.addEventListener('click', (e: MouseEvent) => {
  const target = e.target as HTMLElement;
  if (target && target.classList && target.classList.contains('modal-overlay')) {
    target.classList.remove('open');
    if (_modalFocusTrap) { document.removeEventListener('keydown', _modalFocusTrap); _modalFocusTrap = null; }
  }
});

/* ═══════════════════════════════════
   Password Show/Hide
═══════════════════════════════════ */
function togglePassword(inputId: string) {
  const inp  = document.getElementById(inputId) as HTMLInputElement | null;
  const icon = document.querySelector(`[data-eye="${inputId}"], [onclick*="togglePassword('${inputId}')"]`);
  if (!inp) return;
  if (inp.type === 'password') { inp.type = 'text';     if (icon) icon.textContent = '🙈'; }
  else                         { inp.type = 'password'; if (icon) icon.textContent = '👁'; }
}

/* ═══════════════════════════════════
   SIDEBAR (desktop collapse + mobile drawer)
═══════════════════════════════════ */
const _isMobile = (): boolean => window.innerWidth <= 768;
let _sbCollapsed: boolean  = false;
let _sbDrawerOpen: boolean = false;

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

function debounce<T extends (...args: any[]) => void>(func: T, wait: number) {
  let timeout: ReturnType<typeof setTimeout>;
  return function executedFunction(this: any, ...args: Parameters<T>) {
    const later = () => { clearTimeout(timeout); func.apply(this, args); };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

async function doLogout() {
  try { await fetch('/api/v1/auth/logout', { method: 'POST' }); } catch (e) {}
  window.location.href = '/login';
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
   DOMContentLoaded
═══════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  initToggles();
  initTabs();
  _initSidebar();
  _startClock();

  // Clean initialization of UI elements (removing raw inline HTML onclick handlers)
  const overlay = document.getElementById('sidebar-overlay');
  if (overlay) overlay.addEventListener('click', closeSidebar);

  document.querySelectorAll('.sidebar-toggle-btn').forEach(btn => btn.addEventListener('click', toggleSidebar));
  document.querySelectorAll('.nav-item').forEach(item => item.addEventListener('click', onNavClick));
  
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) themeToggle.addEventListener('click', toggleTheme);

  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) logoutBtn.addEventListener('click', doLogout);
});
