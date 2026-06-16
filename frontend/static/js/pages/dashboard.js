// XSSniper — Dashboard page logic

function _initDashboard() {
  if (!document.getElementById('activityChart')) return;
  _animateStatCounters();
  _initCharts();
  _formatDates();
}

document.addEventListener('DOMContentLoaded', _initDashboard);
document.addEventListener('htmx:afterSettle', _initDashboard);

/* ── Format ISO dates in activity list ──────────────────────────────────── */
function _formatDates() {
  document.querySelectorAll('.activity-meta').forEach(el => {
    el.textContent = el.textContent.replace(
      /(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})/g,
      iso => {
        try {
          return new Date(iso).toLocaleString('en-GB', {
            day: '2-digit', month: 'short', year: 'numeric',
            hour: '2-digit', minute: '2-digit', hour12: false,
          });
        } catch { return iso; }
      }
    );
  });
}

/* ── Stat counter count-up animation ────────────────────────────────────── */
function _animateStatCounters() {
  document.querySelectorAll('.stat-value').forEach(el => {
    const unitEl = el.querySelector('.stat-value-unit');

    // Parse from textContent (includes unit text) — just grab the leading integer
    const raw = parseInt(el.textContent, 10);
    if (isNaN(raw) || raw === 0) return;

    // Build a dedicated text node for the number so the unit <span> is untouched
    const numNode = document.createTextNode('0');
    el.textContent = '';       // clear
    el.appendChild(numNode);   // add counter node
    if (unitEl) el.appendChild(unitEl); // restore unit span

    const duration = Math.min(900, 200 + raw * 18); // ease longer for larger numbers
    const start    = performance.now();

    (function step(now) {
      const t     = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out-cubic
      numNode.nodeValue = String(Math.round(raw * eased));
      if (t < 1) requestAnimationFrame(step);
    }(performance.now()));
  });
}

function _initCharts() {
  const cs        = getComputedStyle(document.documentElement);
  const isDark    = document.documentElement.getAttribute('data-theme') !== 'light';
  const accent    = cs.getPropertyValue('--accent').trim()   || '#00e87a';
  const danger    = cs.getPropertyValue('--danger').trim()   || '#ff4466';
  const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';
  const tickColor = cs.getPropertyValue('--textDim').trim()  || '#4d5f80';
  const ttBg      = cs.getPropertyValue('--bg2').trim()      || '#111827';
  const ttBorder  = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)';
  const titleColor= cs.getPropertyValue('--text').trim()     || '#f0f4ff';
  const bgSurface = cs.getPropertyValue('--bg').trim()       || '#080c12';

  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
  Chart.defaults.font.size   = 11;

  // Read data securely via JSON script block
  const rawDailyData = document.getElementById('chart-daily-data')?.textContent;
  if (!rawDailyData) return;
  const _daily = JSON.parse(rawDailyData);

  const activityEl = document.getElementById('activityChart');
  if (activityEl) {
    new Chart(activityEl, {
      type: 'line',
      data: {
        labels: _daily.map(d => d.label),
        datasets: [
          {
            label: 'Scans',
            data:  _daily.map(d => d.scans),
            borderColor: accent, backgroundColor: accent + '12',
            borderWidth: 2, pointBackgroundColor: accent,
            pointBorderColor: bgSurface, pointRadius: 4,
            tension: 0.4, fill: true,
          },
          {
            label: 'Vulns',
            data:  _daily.map(d => d.vulns),
            borderColor: danger, backgroundColor: danger + '0d',
            borderWidth: 2, pointBackgroundColor: danger,
            pointBorderColor: bgSurface, pointRadius: 4,
            tension: 0.4, fill: true,
          },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: ttBg, borderColor: ttBorder, borderWidth: 1,
            titleColor, bodyColor: tickColor, padding: 10, cornerRadius: 8,
          },
        },
        scales: {
          x: { grid: { color: gridColor }, ticks: { color: tickColor } },
          y: { grid: { color: gridColor }, ticks: { color: tickColor, stepSize: 1 }, beginAtZero: true },
        },
      },
    });
  }

  const vulnChartEl = document.getElementById('vulnChart');
  if (vulnChartEl) {
    const vulns = parseInt(vulnChartEl.dataset.vulns || '0', 10);
    const total = parseInt(vulnChartEl.dataset.total || '0', 10);
    const clean = Math.max(0, total - vulns);

    new Chart(vulnChartEl, {
      type: 'doughnut',
      data: {
        labels: ['Vulnerable', 'Clean'],
        datasets: [{
          data:            vulns + clean > 0 ? [vulns, clean] : [0, 1],
          backgroundColor: [danger + 'bf', accent + '99'],
          borderColor:     [danger, accent],
          borderWidth:     1.5,
          hoverOffset:     5,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '74%',
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: ttBg, borderColor: ttBorder, borderWidth: 1,
            titleColor, bodyColor: tickColor, padding: 10, cornerRadius: 8,
          },
        },
      },
    });
  }
}
