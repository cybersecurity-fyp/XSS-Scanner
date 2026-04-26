/**
 * core/theme.js — Light/dark theme management.
 * Must be loaded in <head> to prevent flash of wrong theme.
 */
var Theme = (function () {
  'use strict';

  var KEY = 'xss-theme';

  function _detect() {
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches)
      ? 'light' : 'dark';
  }

  function set(t) {
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem(KEY, t);
    var btn = document.getElementById('theme-toggle');
    if (btn) btn.setAttribute('data-theme', t);
  }

  function toggle() {
    set(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  }

  function init() {
    var saved = localStorage.getItem(KEY) || _detect();
    set(saved);
  }

  return { init: init, set: set, toggle: toggle };
})();

// Global shortcuts called from base.html onclick attributes
function setTheme(t)    { Theme.set(t); }
function toggleTheme()  { Theme.toggle(); }

// Apply theme immediately on script parse (before DOMContentLoaded)
Theme.init();
