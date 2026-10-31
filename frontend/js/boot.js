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

  /* sign in: demo accounts are checked locally; other demo logins still open a dashboard */
  var sform = document.getElementById('signinForm');
  if (sform) sform.addEventListener('submit', function (e) {
    e.preventDefault();
    var typedName = document.getElementById('signinName').value.trim();
    var typedEmail = document.getElementById('signinEmail').value.trim().toLowerCase();
    var typedPass = document.getElementById('signinPassword') ? document.getElementById('signinPassword').value : '';
    var err = document.getElementById('signinError');
    var match = null;
    if (D.demoAccounts) D.demoAccounts.forEach(function (a) {
      if (typedEmail === a.email.toLowerCase() || typedEmail === a.username.toLowerCase() || typedName.toLowerCase() === a.username.toLowerCase()) match = a;
    });
    if (match && typedPass !== match.password) {
      if (err) { err.textContent = 'Wrong demo password for ' + match.name + '. Use the demo account button below to fill it in.'; err.classList.remove('hidden'); }
      return;
    }
    if (match) {
      V.store.set('username', match.name);
      V.store.set('email', match.email);
      V.store.set('role', match.role);
      V.store.set('demo_account', match.id);
      if (match.city && D.cityData[match.city]) V.setCity(match.city);
      if (match.role === 'guide' && !V.store.getJSON('guide_cities', null)) V.store.setJSON('guide_cities', [match.city]);
    } else {
      V.store.set('username', typedName || 'Traveler');
      V.store.set('email', typedEmail);
      var srole2 = document.getElementById('signinRole');
      V.store.set('role', srole2 ? srole2.value : 'tourist');
      try { localStorage.removeItem('virun_demo_account'); } catch (_) {}
    }
    var srole = document.getElementById('signinRole');
    var role = match ? match.role : (srole ? srole.value : 'tourist');
    location.href = role === 'guide' ? 'guide-dashboard.html' : 'tourist-dashboard.html';
  });
  /* demo account picker: fills the sign-in form, password field is masked */
  document.querySelectorAll('[data-demo]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var a = null;
      if (D.demoAccounts) D.demoAccounts.forEach(function (x) { if (x.id === btn.getAttribute('data-demo')) a = x; });
      if (!a) return;
      var n = document.getElementById('signinName'), em = document.getElementById('signinEmail'),
        pw = document.getElementById('signinPassword'), ro = document.getElementById('signinRole');
      if (n) n.value = a.name; if (em) em.value = a.email; if (pw) pw.value = a.password; if (ro) ro.value = a.role;
      var err = document.getElementById('signinError'); if (err) err.classList.add('hidden');
    });
  });
  /* reset demo: clear ALL demo login, signup, requests, choices, and consent in this browser */
  document.querySelectorAll('[data-reset-demo]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (!window.confirm('Clear all demo data in this browser? This removes demo login, signup, guide requests, chat messages, known cities, availability, journey, and cookie choice.')) return;
      try {
        var keys = [];
        for (var i = 0; i < localStorage.length; i++) keys.push(localStorage.key(i));
        keys.forEach(function (k) { if (k && k.indexOf('virun_') === 0) localStorage.removeItem(k); });
        sessionStorage.clear();
      } catch (_) {}
      location.href = 'index.html';
    });
  });
  /* sign out: clear demo account only, keep city and journey */
  document.querySelectorAll('[data-signout]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      try { localStorage.removeItem('virun_username'); localStorage.removeItem('virun_role'); localStorage.removeItem('virun_email'); localStorage.removeItem('virun_demo_account'); } catch (_) {}
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
    var demoRows = (D.demoAccounts || []).filter(function (a) { return a.role === 'guide'; }).map(function (a, i) {
      var already = getRequests().some(function (r) { return r.guide === a.name && r.status === 'Requested'; });
      return '<div class="list-row"><div><h3>' + a.name + ' · ' + a.city + '</h3><p>' + a.tours + ' · ' + a.languages + '</p><p class="small">' + a.priceOffline + ' · ' + a.priceOnline + ' · Demo guide account.</p></div>' +
        '<button class="btn small" type="button" data-demo-guide="' + i + '"' + (already ? ' disabled' : '') + '>' + (already ? 'Requested' : 'Request guide') + '</button></div>';
    }).join('');
    guideList.innerHTML = demoRows + D.guideSample.examples.map(function (ex, i) {
      var already = getRequests().some(function (r) { return r.tour === ex.title && r.status === 'Requested'; });
      return '<div class="list-row"><div><h3>' + ex.title + '</h3><p>' + city + ' · ' + ex.meta + ' · ' + ex.detail + '</p><p class="small">Sample guide offer, languages English, Telugu, Hindi.</p></div>' +
        '<button class="btn small" type="button" data-request="' + i + '"' + (already ? ' disabled' : '') + '>' + (already ? 'Requested' : 'Request guide') + '</button></div>';
    }).join('');
    guideList.querySelectorAll('[data-demo-guide]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var guides = (D.demoAccounts || []).filter(function (a) { return a.role === 'guide'; });
        var a = guides[Number(btn.getAttribute('data-demo-guide'))];
        var reqs = getRequests();
        reqs.push({ id: 'req-' + Date.now(), city: a.city, tour: a.tours, meta: a.priceOffline, guide: a.name, traveler: V.store.get('username', 'Traveler'), status: 'Requested', created: new Date().toLocaleDateString() });
        saveRequests(reqs);
        btn.disabled = true; btn.textContent = 'Requested';
        renderMyRequests();
      });
    });
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

  /* trip chat: local demo chat, saved in this browser only */
  var chatLog = document.getElementById('chatLog');
  var chatForm = document.getElementById('chatForm');
  if (chatLog && chatForm) {
    var chatMsgs = V.store.getJSON('chat_messages', null);
    if (!chatMsgs) {
      chatMsgs = [
        { from: 'Guide', text: 'I am at the meeting point near the first stop.' },
        { from: 'You', text: 'I have checked in and can see the route status.' },
        { from: 'Guide', text: 'Great. We can begin when you are ready.' }
      ];
    }
    function renderChat() {
      var me = V.store.get('username', 'You');
      chatLog.innerHTML = chatMsgs.map(function (m) {
        var mine = m.from === me || m.from === 'You';
        return '<div class="bubble' + (mine ? ' me' : '') + '">' + m.text + '</div>';
      }).join('');
      chatLog.scrollTop = chatLog.scrollHeight;
    }
    renderChat();
    chatForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var input = document.getElementById('chatInput');
      var text = input.value.trim(); if (!text) return;
      chatMsgs.push({ from: V.store.get('username', 'You'), text: text });
      V.store.setJSON('chat_messages', chatMsgs);
      input.value = ''; renderChat();
    });
  }


  /* payment: frontend only, Pay with, Pay, paying, paid. No money, no Stripe, no Razorpay */
  var payForm = document.getElementById('paymentForm');
  if (payForm) {
    var storedPay = V.store.getJSON('payment_demo', null);
    var payNote = document.getElementById('paymentNote');
    if (storedPay && payNote) payNote.style.display = 'block';
    payForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var method = 'UPI';
      var checked = payForm.querySelector('input[name="payMethod"]:checked');
      if (checked) method = checked.value;
      var btn = document.getElementById('payBtn');
      btn.disabled = true; btn.textContent = 'Paying... demo only, no money moved';
      setTimeout(function () {
        V.store.setJSON('payment_demo', { method: method, amount: 1200, status: 'paid-demo', date: new Date().toLocaleDateString() });
        V.store.set('trip_status', 'paid');
        btn.textContent = 'Paid, demo';
        var succ = document.getElementById('paymentSuccess');
        var pm = document.getElementById('paidMethod');
        if (pm) pm.textContent = method;
        if (succ) succ.classList.remove('hidden');
        succ.scrollIntoView();
      }, 1500);
    });
  }
  /* active trip: mark complete, then review unlocks */
  var completeBtn = document.getElementById('completeTripBtn');
  if (completeBtn) {
    function refreshComplete() {
      var done = V.store.get('trip_status', '') === 'completed';
      var note = document.getElementById('completeTripNote');
      var link = document.getElementById('reviewLink');
      if (done) {
        completeBtn.textContent = 'Trip completed, demo';
        completeBtn.disabled = true;
        if (note) note.textContent = 'Trip marked complete in this demo browser. Review and rating are now open.';
        if (link) link.style.display = 'inline-flex';
      }
    }
    refreshComplete();
    completeBtn.addEventListener('click', function () {
      var reqs = V.store.getJSON('guide_requests', []);
      var guide = reqs.length && reqs[reqs.length - 1].guide ? reqs[reqs.length - 1].guide : '';
      var pay = V.store.getJSON('payment_demo', null);
      V.store.setJSON('completed_trip', { city: V.getCity(), date: new Date().toLocaleDateString(), guide: guide, amount: 1200, method: pay ? pay.method : 'Not paid in demo' });
      V.store.set('trip_status', 'completed');
      refreshComplete();
    });
  }
  /* trip history: show completed trip, if any */
  var historyList = document.getElementById('historyList');
  if (historyList) {
    var ct = V.store.getJSON('completed_trip', null);
    var empty = document.getElementById('historyEmpty');
    if (ct) {
      if (empty) empty.style.display = 'none';
      historyList.innerHTML = '<article class="card"><h2 style="margin-top:0">' + ct.city + ' trip, completed, demo</h2><p>Date: ' + ct.date + ' · Guide: ' + (ct.guide || 'Not picked in demo') + ' · Payment shown: ' + ct.method + ' · Rs 1,200 demo amount, no money moved.</p><div class="action-row"><a class="btn" href="review.html">Leave a review and rating</a><a class="btn secondary" href="reviews.html">See reviews</a></div></article>';
    }
  }
  /* review: rating, gated on a completed trip, saved in this browser */
  var reviewForm = document.getElementById('reviewForm');
  if (reviewForm) {
    var completed = V.store.get('trip_status', '') === 'completed';
    var locked = document.getElementById('reviewLocked');
    if (!completed) {
      if (locked) locked.style.display = 'block';
      reviewForm.querySelectorAll('input, textarea, select, button').forEach(function (el) { el.disabled = true; });
    } else {
      var rating = 0;
      var ratingNote = document.getElementById('ratingNote');
      reviewForm.querySelectorAll('[data-star]').forEach(function (b) {
        b.addEventListener('click', function () {
          rating = Number(b.getAttribute('data-star'));
          if (ratingNote) ratingNote.textContent = rating + ' star' + (rating > 1 ? 's' : '') + ' picked.';
        });
      });
      var ct2 = V.store.getJSON('completed_trip', null);
      var guideInput = document.getElementById('reviewGuide');
      if (ct2 && ct2.guide && guideInput) guideInput.value = ct2.guide;
      reviewForm.addEventListener('submit', function (e) {
        e.preventDefault();
        if (!rating) { if (ratingNote) ratingNote.textContent = 'Pick a star rating first.'; return; }
        var revs = V.store.getJSON('reviews_demo', []);
        revs.push({ guide: guideInput ? guideInput.value : '', rating: rating, good: document.getElementById('reviewGood').value, improve: document.getElementById('reviewBad').value, again: document.getElementById('reviewAgain').value, by: V.store.get('username', 'Traveler'), date: new Date().toLocaleDateString() });
        V.store.setJSON('reviews_demo', revs);
        location.href = 'trip-history.html';
      });
    }
  }
  /* reviews page: show saved demo reviews, not skeleton fakes */
  var reviewsList = document.getElementById('reviewsList');
  if (reviewsList) {
    var revs2 = V.store.getJSON('reviews_demo', []);
    reviewsList.innerHTML = revs2.length ? revs2.map(function (r) {
      return '<article class="card"><h3 style="margin-top:0">' + r.rating + ' stars · ' + (r.guide || 'Guide, demo') + '</h3><p>' + r.good + '</p><p class="small">By ' + r.by + ' · ' + r.date + ' · Demo review, saved in this browser.</p></article>';
    }).join('') : '<p>No demo reviews yet in this browser. Complete a trip, then leave a review and rating.</p>';
  }
  /* KYC: frontend only, full ID number is never stored, only type + last 4 */
  var kycForm = document.getElementById('kycForm');
  if (kycForm) {
    function showKyc() {
      var s = V.store.getJSON('kyc_demo', null);
      var el = document.getElementById('kycStatus');
      if (!el) return;
      if (!s) { el.innerHTML = '<strong>Status: Pending review</strong><br>Frontend demo only.'; return; }
      if (s.status === 'verified-demo') el.innerHTML = '<strong>Status: Verified, demo preview</strong><br>Frontend view only. This does not mean a real check passed. Document: ' + s.doc + (s.last4 ? ' · Last 4: ' + s.last4 : '') + '.';
      else el.innerHTML = '<strong>Status: Submitted, demo, pending review</strong><br>Frontend view only. Document: ' + s.doc + (s.last4 ? ' · Last 4: ' + s.last4 : '') + '. Cities: ' + (s.cities.length ? s.cities.join(', ') : 'None picked') + '.';
    }
    showKyc();
    kycForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var raw = document.getElementById('kycId').value.trim();
      var cities = [];
      kycForm.querySelectorAll('.kyc-city:checked').forEach(function (c) { cities.push(c.value); });
      V.store.setJSON('kyc_demo', { doc: document.getElementById('kycDoc').value, last4: raw ? raw.slice(-4) : '', cities: cities, status: 'submitted' });
      document.getElementById('kycId').value = '';
      showKyc();
    });
    var previewBtn = document.getElementById('kycPreviewBtn');
    if (previewBtn) previewBtn.addEventListener('click', function () {
      var s = V.store.getJSON('kyc_demo', null) || { doc: document.getElementById('kycDoc').value, last4: '', cities: [] };
      s.status = 'verified-demo';
      V.store.setJSON('kyc_demo', s);
      showKyc();
    });
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
