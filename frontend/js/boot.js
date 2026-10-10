/* Per-page boot: nav, theme, weather, fills, forms. Replaces the old bind()/render(). */
(function () {
  'use strict';
  var V = window.Virun, N = window.VirunNav, D = window.VirunData;
  var body = document.body;
  var navKind = body.getAttribute('data-nav');       /* public | auth | app | guide */
  var active = body.getAttribute('data-active');     /* current file name */
  var appMode = (navKind === 'app' || navKind === 'guide');

  /* nav */
  var navEl = document.getElementById('nav');
  if (navEl) {
    if (navKind === 'public') navEl.innerHTML = N.publicNav(active);
    else if (navKind === 'app') navEl.innerHTML = N.appNav(active);
    else if (navKind === 'guide') navEl.innerHTML = N.guideNav(active);
  }
  var mobEl = document.getElementById('mobileNav');
  if (mobEl && navKind === 'app') mobEl.innerHTML = N.mobileNav(active);
  var footEl = document.getElementById('footer');
  if (footEl) footEl.innerHTML = V.footerHTML();
  body.classList.toggle('app-mode', appMode);

  /* theme + scene */
  V.applyTheme(appMode);

  /* choose-trip / destination cards set the city before following the link */
  document.querySelectorAll('[data-city]').forEach(function (el) {
    el.addEventListener('click', function () { V.setCity(el.getAttribute('data-city')); });
  });
  var citySelect = document.getElementById('citySelect');
  if (citySelect) citySelect.addEventListener('change', function () {
    V.setCity(this.value); location.reload();
  });

  /* weather badges + particles + reveal */
  V.hydrateWeather();
  if (appMode) V.startWeather(); else V.stopWeather();
  V.setupMotion();

  /* journey search */
  var swap = document.getElementById('swapRoute');
  if (swap) swap.addEventListener('click', function () {
    var f = document.getElementById('journeyFrom'), t = document.getElementById('journeyTo'), v = f.value;
    f.value = t.value; t.value = v;
  });
  var jf = document.getElementById('journeyForm');
  if (jf) jf.addEventListener('submit', function (e) {
    e.preventDefault();
    var f = document.getElementById('journeyFrom'), t = document.getElementById('journeyTo');
    t.setCustomValidity(f.value === t.value ? 'Choose a different destination.' : '');
    if (!jf.reportValidity()) return;
    var journey = {
      from: f.value, to: t.value,
      date: document.getElementById('journeyDate').value,
      mode: document.getElementById('journeyMode').value
    };
    V.store.setJSON('journey', journey);
    if (D.cityData[journey.to]) V.setCity(journey.to);
    V.store.set('transportChoice', '');
    location.href = 'transport-options.html';
  });

  /* transport option pick */
  document.querySelectorAll('[data-transport]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      V.store.set('transportChoice', btn.getAttribute('data-transport'));
      location.href = 'transport-booking.html';
    });
  });

  /* google buttons */
  [['googleSignin', 'googleHint'], ['googleSignup', 'googleSignupHint']].forEach(function (pair) {
    var button = document.getElementById(pair[0]);
    if (button && window.VirunAuth) button.addEventListener('click', function () {
      window.VirunAuth.startGoogleSignIn(button, document.getElementById(pair[1]));
    });
  });

  /* sign in */
  var sform = document.getElementById('signinForm');
  if (sform) sform.addEventListener('submit', function (e) {
    e.preventDefault();
    V.store.set('username', document.getElementById('signinName').value.trim() || 'Traveler');
    location.href = 'journey-search.html';
  });

  /* create account */
  var cform = document.getElementById('createAccountForm');
  if (cform) cform.addEventListener('submit', function (e) {
    e.preventDefault();
    var a = document.getElementById('accountPassword').value,
      b = document.getElementById('accountConfirm').value,
      err = document.getElementById('accountError');
    if (a !== b) { err.classList.remove('hidden'); document.getElementById('accountConfirm').focus(); return; }
    err.classList.add('hidden');
    V.store.set('username', document.getElementById('accountName').value.trim() || 'Traveler');
    var role = document.getElementById('accountRole').value;
    location.href = role === 'guide' ? 'guide-details.html' : 'journey-search.html';
  });

  /* tourist details */
  var tform = document.getElementById('touristDetailsForm');
  if (tform) tform.addEventListener('submit', function (e) {
    var n = document.getElementById('touristName');
    if (n && n.value.trim()) V.store.set('username', n.value.trim());
  });

  /* guide details */
  var gform = document.getElementById('guideDetailsForm');
  if (gform) gform.addEventListener('submit', function (e) {
    var n = gform.querySelector('input');
    if (n && n.value.trim()) V.store.set('username', n.value.trim());
  });

  /* generic demo forms that only navigate */
  document.querySelectorAll('form[data-goto]').forEach(function (form) {
    form.addEventListener('submit', function () { location.href = form.getAttribute('data-goto'); });
  });

  /* guide dashboard: known-city chips toggle (visual mock) */
  document.querySelectorAll('[data-knc]').forEach(function (chip) {
    chip.addEventListener('click', function () { chip.classList.toggle('picked'); });
  });
  /* guide dashboard: availability toggle (visual mock) */
  var avail = document.getElementById('availToggle');
  if (avail) avail.addEventListener('click', function () {
    var on = avail.getAttribute('aria-pressed') === 'true';
    avail.setAttribute('aria-pressed', String(!on));
    avail.querySelector('span').textContent = on ? 'Off duty' : 'Available now';
  });
})();
