/* ===== Utilities ===== */

function formatTime(iso) {
  if (!iso) return '-';
  // Backend stores UTC without 'Z' suffix — force JS to parse as UTC
  if (!iso.endsWith('Z') && !iso.includes('+')) iso += 'Z';
  var d = new Date(iso);
  return d.toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function formatDuration(ms) {
  if (ms == null) return '-';
  if (ms < 1000) return ms + 'ms';
  if (ms < 60000) return (ms / 1000).toFixed(1) + 's';
  return Math.floor(ms / 60000) + 'm ' + Math.round((ms % 60000) / 1000) + 's';
}

function makeStatusBadge(status) {
  var badge = document.createElement('span');
  var map = {
    success: 'badge-success', failed: 'badge-danger', running: 'badge-info',
    timeout: 'badge-warning', skipped: 'badge-gray', pending: 'badge-gray',
  };
  badge.className = 'badge ' + (map[status] || 'badge-gray');
  badge.textContent = status;
  return badge;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* ===== Pagination ===== */

function makePagination(page, pageSize, total) {
  var totalPages = Math.ceil(total / pageSize);
  if (totalPages <= 1) return null;
  var div = document.createElement('div');
  div.className = 'pagination';

  var info = document.createElement('span');
  info.textContent = (page - 1) * pageSize + 1 + '-' + Math.min(page * pageSize, total) + ' of ' + total;
  div.appendChild(info);

  var btns = document.createElement('div');
  btns.className = 'page-btns';
  if (page > 1) {
    var prev = document.createElement('button');
    prev.className = 'btn btn-sm';
    prev.textContent = 'Prev';
    prev.onclick = function() { goPage(page - 1); };
    btns.appendChild(prev);
  }
  var label = document.createElement('span');
  label.style.padding = '0 8px';
  label.textContent = 'Page ' + page + '/' + totalPages;
  btns.appendChild(label);
  if (page < totalPages) {
    var next = document.createElement('button');
    next.className = 'btn btn-sm';
    next.textContent = 'Next';
    next.onclick = function() { goPage(page + 1); };
    btns.appendChild(next);
  }
  div.appendChild(btns);
  return div;
}

/* ===== Theme ===== */

var THEME_KEY = 'acs-theme';

function getTheme() {
  return localStorage.getItem(THEME_KEY) || 'system';
}

function setTheme(theme) {
  localStorage.setItem(THEME_KEY, theme);
  applyTheme(theme);
  updateThemeButtons();
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
}

function updateThemeButtons() {
  var theme = getTheme();
  document.querySelectorAll('.theme-btn').forEach(function(btn) {
    btn.classList.toggle('active', btn.getAttribute('data-theme') === theme);
  });
}

/* ===== Sidebar ===== */

var NAV_LINKS = [
  { id: 'dashboard',  href: '/dashboard/',              icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>', label: 'Dashboard' },
  { id: 'tasks',      href: '/dashboard/tasks.html',    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 14l2 2 4-4"/></svg>', label: 'Tasks' },
  { id: 'executions', href: '/dashboard/executions.html', icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>', label: 'Executions' },
];

function getActiveNavId() {
  var path = window.location.pathname;
  // Exact match first
  for (var i = 0; i < NAV_LINKS.length; i++) {
    if (path === NAV_LINKS[i].href) return NAV_LINKS[i].id;
  }
  // Prefix match — but only for non-dashboard pages
  for (var i = 1; i < NAV_LINKS.length; i++) {
    if (path.indexOf(NAV_LINKS[i].href) === 0) return NAV_LINKS[i].id;
  }
  // task-detail.html / execution-detail.html fall under their parent pages
  if (path.indexOf('/dashboard/task') === 0) return 'tasks';
  if (path.indexOf('/dashboard/execution') === 0) return 'executions';
  return 'dashboard';
}

function initLayout() {
  var container = document.querySelector('.sidebar-container');
  if (!container) return;

  // Brand
  var brand = document.createElement('div');
  brand.className = 'sidebar-brand';
  var iconDiv = document.createElement('div');
  iconDiv.className = 'brand-icon';
  iconDiv.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>';
  brand.appendChild(iconDiv);
  var brandText = document.createElement('span');
  brandText.className = 'brand-text';
  brandText.textContent = 'Cron Server';
  brand.appendChild(brandText);
  container.appendChild(brand);

  // Nav
  var nav = document.createElement('nav');
  nav.className = 'sidebar-nav';
  var activeId = getActiveNavId();
  NAV_LINKS.forEach(function(link) {
    var a = document.createElement('a');
    a.href = link.href;
    if (link.id === activeId) a.className = 'active';
    var iconSpan = document.createElement('span');
    iconSpan.className = 'nav-icon';
    iconSpan.textContent = ''; // clear
    a.appendChild(iconSpan);
    iconSpan.outerHTML = link.icon;
    var label = document.createElement('span');
    label.className = 'nav-label';
    label.textContent = link.label;
    a.appendChild(label);
    nav.appendChild(a);
  });
  container.appendChild(nav);

  // Theme footer
  var footer = document.createElement('div');
  footer.className = 'sidebar-footer';
  var toggle = document.createElement('div');
  toggle.className = 'theme-toggle';
  [['light', '\u2600'], ['dark', '\u263D'], ['system', '\u2699']].forEach(function(item) {
    var btn = document.createElement('button');
    btn.className = 'theme-btn';
    btn.setAttribute('data-theme', item[0]);
    btn.title = item[0].charAt(0).toUpperCase() + item[0].slice(1);
    btn.textContent = item[1];
    btn.onclick = function() { setTheme(item[0]); };
    toggle.appendChild(btn);
  });
  footer.appendChild(toggle);
  container.appendChild(footer);

  // Apply saved theme
  applyTheme(getTheme());
  updateThemeButtons();
}

document.addEventListener('DOMContentLoaded', initLayout);
