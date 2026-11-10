// GapKeep site: the language. Runs first, before the page is drawn.
// The choice made with the EN / PT links is kept in localStorage (no
// cookies). Without one, the browser's preferred language decides, on
// arrival from elsewhere only: links inside the site are never redirected.
(function () {
  var d = document.documentElement;
  d.className += ' js';
  var lang = d.getAttribute('data-lang');
  var path = location.pathname;
  if (!lang || /^\/(ide\/|logo-concepts)/.test(path)) return;
  var want = null;
  try { want = localStorage.getItem('gapkeep-lang'); } catch (e) {}
  if (want !== 'en' && want !== 'pt-BR') {
    want = null;
    var list = navigator.languages || [navigator.language || ''];
    for (var i = 0; i < list.length && !want; i++) {
      var l = String(list[i]).toLowerCase();
      if (l.indexOf('pt') === 0) want = 'pt-BR';
      else if (l.indexOf('en') === 0) want = 'en';
    }
  }
  if (!want || want === lang) return;
  var inside = false;
  try { inside = !!document.referrer && new URL(document.referrer).origin === location.origin; } catch (e) {}
  if (inside) return;
  var target = want === 'pt-BR' ? '/pt-br' + path : path.replace(/^\/pt-br\//, '/');
  location.replace(target + location.search + location.hash);
})();
