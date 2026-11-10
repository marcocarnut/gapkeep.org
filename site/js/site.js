// GapKeep site: the little it needs. No libraries, nothing from elsewhere.
(function () {
  'use strict';
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  // The language links remember the choice.
  document.querySelectorAll('.langs a[data-lang]').forEach(function (a) {
    a.addEventListener('click', function () {
      try { localStorage.setItem('gapkeep-lang', a.getAttribute('data-lang')); } catch (e) {}
    });
  });

  // The menu on small screens.
  var toggle = document.querySelector('.nav-toggle');
  if (toggle) {
    var list = document.getElementById(toggle.getAttribute('aria-controls'));
    var set = function (open) {
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.classList.toggle('nav-open', open);
    };
    toggle.addEventListener('click', function () { set(toggle.getAttribute('aria-expanded') !== 'true'); });
    list.addEventListener('click', function (e) { if (e.target.closest('a')) set(false); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') { set(false); toggle.focus(); }
    });
  }

  // Sections rise into view as they are reached (not with reduced motion).
  var items = document.querySelectorAll('.reveal');
  if (!reduce && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px' });
    items.forEach(function (el) { io.observe(el); });
  } else {
    items.forEach(function (el) { el.classList.add('in'); });
  }

  // The app gallery: previous / next buttons scroll it by one card.
  document.querySelectorAll('[data-scroller]').forEach(function (box) {
    var track = box.querySelector('.track');
    box.querySelectorAll('[data-dir]').forEach(function (b) {
      b.addEventListener('click', function () {
        var card = track.querySelector('.card');
        var step = card ? card.getBoundingClientRect().width + 16 : 300;
        track.scrollBy({ left: step * Number(b.getAttribute('data-dir')), behavior: reduce ? 'auto' : 'smooth' });
      });
    });
  });

  // Works offline once visited (sw.js). Only on https or this machine.
  if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === '127.0.0.1' || location.hostname === 'localhost')) {
    window.addEventListener('load', function () { navigator.serviceWorker.register('/sw.js').catch(function () {}); });
  }
})();
