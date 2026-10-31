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

  /* sign in: demo only, role decides the landing page */
  var sform = document.getElementById('signinForm');
  if (sform) sform.addEventListener('submit', function (e) {
    e.preventDefault();
    V.store.set('username', document.getElementById('signinName').value.trim() || 'Traveler');
    V.store.set('email', document.getElementById('signinEmail').value.trim());
    var srole = document.getElementById('signinRole');
    V.store.set('role', srole ? srole.value : 'tourist');
    location.href = (srole && srole.value === 'guide') ? 'guide-dashboard.html' : 'tourist-dashboard.html';
  });
  /* sign out: clear demo account only, keep city and journey */
  document.querySelectorAll('[data-signout]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      try { localStorage.removeItem('virun_username'); localStorage.removeItem('virun_role'); localStorage.removeItem('virun_email'); } catch (_) {}
      location.href = 'index.html';
    });
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
    V.store.set('email', document.getElementById('accountEmail').value.trim());
    var role = document.getElementById('accountRole').value;
    V.store.set('role', role);
    var acity = document.getElementById('accountCity');
    if (acity && acity.value.trim()) V.setCity(acity.value.trim());
    location.href = role === 'guide' ? 'guide-dashboard.html' : 'tourist-dashboard.html';
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

  /* guide dashboard: known-city chips, saved in this browser */
  var savedCities = V.store.getJSON('guide_cities', null);
  document.querySelectorAll('[data-knc]').forEach(function (chip) {
    if (savedCities) chip.classList.toggle('picked', savedCities.indexOf(chip.textContent.trim()) !== -1);
    chip.addEventListener('click', function () {
      chip.classList.toggle('picked');
      var picked = [];
      document.querySelectorAll('[data-knc].picked').forEach(function (c) { picked.push(c.textContent.trim()); });
      V.store.setJSON('guide_cities', picked);
    });
  });
  /* guide dashboard: availability toggle, saved in this browser */
  var avail = document.getElementById('availToggle');
  if (avail) {
    var savedAvail = V.store.get('guide_available', null);
    if (savedAvail !== null) {
      var onSaved = savedAvail === 'true';
      avail.setAttribute('aria-pressed', String(onSaved));
      avail.querySelector('span').textContent = onSaved ? 'Available now' : 'Off duty';
    }
    avail.addEventListener('click', function () {
      var on = avail.getAttribute('aria-pressed') === 'true';
      avail.setAttribute('aria-pressed', String(!on));
      avail.querySelector('span').textContent = on ? 'Off duty' : 'Available now';
      V.store.set('guide_available', String(!on));
    });
  }
  /* tourist dashboard: sample guide offers and demo requests, browser only */
  function getRequests() { return V.store.getJSON('guide_requests', []); }
  function saveRequests(r) { V.store.setJSON('guide_requests', r); }
  var guideList = document.getElementById('guideList');
  if (guideList && D.guideSample) {
    var city = V.getCity();
    guideList.innerHTML = D.guideSample.examples.map(function (ex, i) {
      var already = getRequests().some(function (r) { return r.tour === ex.title && r.status === 'Requested'; });
      return '<div class="list-row"><div><h3>' + ex.title + '</h3><p>' + city + ' · ' + ex.meta + ' · ' + ex.detail + '</p><p class="small">Sample guide offer, languages English, Telugu, Hindi.</p></div>' +
        '<button class="btn small" type="button" data-request="' + i + '"' + (already ? ' disabled' : '') + '>' + (already ? 'Requested' : 'Request guide') + '</button></div>';
    }).join('');
    guideList.querySelectorAll('[data-request]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var ex = D.guideSample.examples[Number(btn.getAttribute('data-request'))];
        var reqs = getRequests();
        reqs.push({ id: 'req-' + Date.now(), city: V.getCity(), tour: ex.title, meta: ex.meta, traveler: V.store.get('username', 'Traveler'), status: 'Requested', created: new Date().toLocaleDateString() });
        saveRequests(reqs);
        btn.disabled = true; btn.textContent = 'Requested';
        renderMyRequests();
      });
    });
  }
  function renderMyRequests() {
    var el = document.getElementById('myRequests');
    if (!el) return;
    var reqs = getRequests();
    el.innerHTML = reqs.length ? reqs.map(function (r) {
      return '<div class="list-row"><div><h3>' + r.tour + '</h3><p>' + r.city + ' · ' + r.meta + ' · ' + r.created + '</p></div><span class="tag">' + r.status + '</span></div>';
    }).join('') : '<p>No demo requests yet. Use Find a guide above.</p>';
  }
  renderMyRequests();
  var clearBtn = document.getElementById('clearRequests');
  if (clearBtn) clearBtn.addEventListener('click', function () { saveRequests([]); renderMyRequests(); if (guideList) location.reload(); });
  /* guide requests page: stored requests, plus a sample if none exist */
  var requestList = document.getElementById('requestList');
  if (requestList) {
    var stored = getRequests();
    function renderRequests() {
      stored = getRequests();
      if (!stored.length) {
        requestList.innerHTML = '<div class="list-row"><div><span class="tag">Sample request</span><h3 style="margin-top:8px">Three-day ' + V.getCity() + ' trip</h3><p>Sample only. Traveler details are hidden until a real connection exists.</p></div><div class="action-row"><button class="btn" type="button" data-sample="Accepted">Accept</button><button class="btn secondary" type="button" data-sample="Rejected">Reject</button></div></div>';
        requestList.querySelectorAll('[data-sample]').forEach(function (b) {
          b.addEventListener('click', function () { b.closest('.list-row').querySelector('h3').textContent = 'Sample request: ' + b.getAttribute('data-sample'); });
        });
        return;
      }
      requestList.innerHTML = stored.map(function (r) {
        return '<div class="list-row"><div><h3>' + r.tour + '</h3><p>' + r.city + ' · ' + r.meta + ' · Traveler: ' + r.traveler + ' · ' + r.created + '</p></div><div class="action-row"><span class="tag">' + r.status + '</span>' +
          (r.status === 'Requested' ? '<button class="btn small" type="button" data-decide="Accepted" data-id="' + r.id + '">Accept</button><button class="btn secondary small" type="button" data-decide="Rejected" data-id="' + r.id + '">Reject</button>' : '') + '</div></div>';
      }).join('');
      requestList.querySelectorAll('[data-decide]').forEach(function (b) {
        b.addEventListener('click', function () {
          var reqs = getRequests();
          reqs.forEach(function (r) { if (r.id === b.getAttribute('data-id')) r.status = b.getAttribute('data-decide'); });
          saveRequests(reqs); renderRequests();
        });
      });
    }
    renderRequests();
  }
  /* guide dashboard: request summary */
  var summary = document.getElementById('guideRequestSummary');
  if (summary) {
    var pending = getRequests().filter(function (r) { return r.status === 'Requested'; }).length;
    summary.textContent = pending ? pending + ' demo request(s) waiting in this browser.' : 'No demo requests yet in this browser. A tourist request from the tourist dashboard will appear here.';
  }

  /* cookie consent (team's implementation, ported from their index.html) */
  var COOKIE_CONSENT_VERSION = '2026-10-11-v1';
  function initCookieConsent() {
    var banner = document.getElementById('cookieConsent');
    if (!banner) return;
    try {
      var saved = JSON.parse(localStorage.getItem('virun_cookie_consent') || 'null');
      if (saved && saved.version === COOKIE_CONSENT_VERSION) {
        banner.hidden = true;
        var checkbox = document.getElementById('analyticsConsent');
        if (checkbox) checkbox.checked = !!saved.analytics;
      } else banner.hidden = false;
    } catch (_) { banner.hidden = false; }
  }
  function chooseCookieConsent(analytics) {
    try { localStorage.setItem('virun_cookie_consent', JSON.stringify({ version: COOKIE_CONSENT_VERSION, essential: true, analytics: !!analytics, decided_at: new Date().toISOString() })); } catch (_) {}
    var banner = document.getElementById('cookieConsent');
    if (banner) banner.hidden = true;
  }
  function showCookieConsent() {
    var banner = document.getElementById('cookieConsent');
    if (!banner) return;
    var checkbox = document.getElementById('analyticsConsent');
    try {
      var saved = JSON.parse(localStorage.getItem('virun_cookie_consent') || 'null');
      if (checkbox) checkbox.checked = !!(saved && saved.analytics);
    } catch (_) { if (checkbox) checkbox.checked = false; }
    banner.hidden = false;
  }
  document.querySelectorAll('[data-consent-choice]').forEach(function (button) {
    button.addEventListener('click', function () {
      var checkbox = document.getElementById('analyticsConsent'),
        choice = button.getAttribute('data-consent-choice'),
        analytics = choice === 'all' || (choice === 'preferences' && checkbox && checkbox.checked);
      chooseCookieConsent(analytics);
    });
  });
  var cookieSettings = document.getElementById('cookieSettings');
  if (cookieSettings) cookieSettings.addEventListener('click', showCookieConsent);
  initCookieConsent();
})();
