// XSSniper — Auth pages logic (login, register, password flows)

/* ── Field validators ─────────────────────────────────────────────────────── */
function validateUsername(inp) {
  const v   = inp.value.trim();
  const err = document.getElementById('err-username');
  const ok  = /^[a-zA-Z0-9_]{3,20}$/.test(v);
  inp.classList.toggle('input-ok',    ok && v.length > 0);
  inp.classList.toggle('input-error', !ok && v.length > 0);
  if (err) {
    if      (!v.length)               err.style.display = 'none';
    else if (v.length < 3)            showErr(err, 'At least 3 characters required');
    else if (v.length > 20)           showErr(err, 'Maximum 20 characters');
    else if (!/^[a-zA-Z0-9_]+$/.test(v)) showErr(err, 'Only letters, numbers and underscores');
    else                              err.style.display = 'none';
  }
}

function validateEmail(inp) {
  const v   = inp.value.trim();
  const err = document.getElementById('err-email');
  const ok  = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
  inp.classList.toggle('input-ok',    ok);
  inp.classList.toggle('input-error', !ok && v.length > 0);
  if (err) {
    if (!ok && v.length > 0) showErr(err, 'Enter a valid email address');
    else                     err.style.display = 'none';
  }
}

function validateConfirm(inp) {
  const pass = document.getElementById('reg-pass')?.value || '';
  const err  = document.getElementById('err-confirm');
  const ok   = inp.value === pass && inp.value.length > 0;
  inp.classList.toggle('input-ok',    ok);
  inp.classList.toggle('input-error', !ok && inp.value.length > 0);
  if (err) {
    if (inp.value.length > 0 && inp.value !== pass) showErr(err, 'Passwords do not match');
    else err.style.display = 'none';
  }
}

function showErr(el, msg) {
  el.textContent   = '⚠ ' + msg;
  el.style.display = 'block';
}

/* ── Password strength ────────────────────────────────────────────────────── */
function updateStrength(val) {
  const wrap = document.getElementById('pw-strength-wrap');
  if (!wrap) return;
  wrap.style.display = val.length > 0 ? 'block' : 'none';

  const rules = {
    len:     val.length >= 6,
    num:     /[0-9]/.test(val),
    special: /[^A-Za-z0-9]/.test(val),
  };

  Object.entries(rules).forEach(([key, met]) => {
    const el = document.getElementById('rule-' + key);
    if (el) el.classList.toggle('met', met);
  });

  const score  = Object.values(rules).filter(Boolean).length;
  const segs   = ['ps1','ps2','ps3','ps4'].map(id => document.getElementById(id));
  const label  = document.getElementById('pw-label');
  const levels = [
    { cls:'s-weak',   text:'Weak — too easy to guess',   color:'#f43f5e' },
    { cls:'s-fair',   text:'Fair — add a number',        color:'#f59e0b' },
    { cls:'s-good',   text:'Good — add a special char',  color:'#22d3ee' },
    { cls:'s-strong', text:'Strong — great password! ✓', color:'#00ff88' },
  ];
  const lvl = levels[score] || levels[0];
  segs.forEach((s, i) => {
    if (!s) return;
    s.className = 'pw-seg';
    if (i < score) s.classList.add(lvl.cls);
  });
  if (label) { label.textContent = lvl.text; label.style.color = lvl.color; }

  const inp = document.getElementById('reg-pass');
  if (inp) {
    inp.classList.remove('input-error', 'input-ok');
    if (score === 3)      inp.classList.add('input-ok');
    else if (val.length)  inp.classList.add('input-error');
  }
}

/* ── Login ────────────────────────────────────────────────────────────────── */
async function doLogin(event) {
  event.preventDefault();
  const login    = document.getElementById('login-input').value.trim();
  const password = document.getElementById('login-pass').value;
  const errEl    = document.getElementById('login-error');
  const btn      = document.getElementById('login-btn');

  if (!login)    { showAuthErr(errEl, 'Please enter your email or username'); return; }
  if (!password) { showAuthErr(errEl, 'Please enter your password'); return; }

  errEl.style.display = 'none';
  setButtonLoading(btn, true);

  try {
    await api('POST', '/api/v1/auth/login', { login, password });
    setButtonLoading(btn, false);
    btn.textContent      = '✓ ACCESS GRANTED';
    btn.style.background = 'var(--accent)';
    btn.style.color      = '#040e08';
    setTimeout(() => { window.location.href = '/'; }, 800);
  } catch (err) {
    showAuthErr(errEl, err.message);
    setButtonLoading(btn, false);
    shakCard();
  }
}

/* ── Register ─────────────────────────────────────────────────────────────── */
async function doRegister(event) {
  event.preventDefault();
  const username = document.getElementById('reg-username').value.trim();
  const email    = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-pass').value;
  const confirm  = document.getElementById('reg-confirm').value;
  const errEl    = document.getElementById('reg-error');
  const sucEl    = document.getElementById('reg-success');
  const btn      = document.getElementById('reg-btn');

  errEl.style.display = 'none';
  sucEl.style.display = 'none';

  if (!username || username.length < 3)        return showAuthErr(errEl, 'Username must be at least 3 characters');
  if (!/^[a-zA-Z0-9_]+$/.test(username))       return showAuthErr(errEl, 'Username: only letters, numbers and underscores');
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return showAuthErr(errEl, 'Please enter a valid email address');
  if (password.length < 6)                     return showAuthErr(errEl, 'Password must be at least 6 characters');
  if (!/[0-9]/.test(password))                 return showAuthErr(errEl, 'Password needs at least one number (0–9)');
  if (!/[^A-Za-z0-9]/.test(password))          return showAuthErr(errEl, 'Password needs at least one special character (!@#$…)');
  if (password !== confirm)                    return showAuthErr(errEl, 'Passwords do not match');

  setButtonLoading(btn, true);

  try {
    await api('POST', '/api/v1/auth/register', { username, email, password, confirm });
    sucEl.textContent   = '✓ Account created! Redirecting to login…';
    sucEl.style.display = 'block';
    setTimeout(() => { window.location.href = '/login'; }, 1500);
  } catch (err) {
    showAuthErr(errEl, err.message);
    setButtonLoading(btn, false);
  }
}

function showAuthErr(el, msg) {
  el.textContent   = '⚠ ' + msg;
  el.style.display = 'block';
  shakCard();
}

function shakCard() {
  const card = document.querySelector('.auth-card');
  if (!card) return;
  card.style.animation = 'none';
  requestAnimationFrame(() => { card.style.animation = 'shake 0.4s ease'; });
  setTimeout(() => card.style.animation = '', 400);
}
