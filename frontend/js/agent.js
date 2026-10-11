/* Virun Agent demo — agentic chat over the repo's own datasets.
   Tries the real backend (/api/agent/chat); falls back to an in-browser
   mock agent that uses the same logic and the same hotels JSON files.
   Nothing here claims a real booking. */
(function () {
  'use strict';
  var CITIES = ['kashmir', 'goa', 'hyderabad', 'visakhapatnam', 'mumbai', 'delhi', 'bengaluru'];
  var CITY_LABEL = { kashmir: 'Kashmir', goa: 'Goa', hyderabad: 'Hyderabad', visakhapatnam: 'Visakhapatnam', mumbai: 'Mumbai', delhi: 'Delhi', bengaluru: 'Bengaluru' };
  var hotelCache = {};
  var backendLive = false;

  var log, form, input, traceEl, hotelsEl, rapidoEl, modeBadge, trackPanel, trackCanvas, trackStatus;

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function esc(s) { return String(s == null ? '' : s); }

  function addBubble(text, me) {
    var b = el('div', 'bubble' + (me ? ' me' : ''), text);
    log.appendChild(b);
    log.scrollTop = log.scrollHeight;
    return b;
  }
  function addTrace(tool, args, ok, note) {
    var row = el('div', 'agent-trace-row');
    row.appendChild(el('span', 'agent-trace-tool', '⚙ ' + tool));
    row.appendChild(el('span', 'agent-trace-args', JSON.stringify(args || {})));
    row.appendChild(el('span', 'agent-trace-' + (ok ? 'ok' : 'fail'), ok ? 'ok' : 'fail' + (note ? ' — ' + note : '')));
    traceEl.appendChild(row);
    traceEl.style.display = 'block';
  }
  function showHotels(list, city) {
    hotelsEl.innerHTML = '';
    if (!list.length) {
      hotelsEl.appendChild(el('p', 'muted', 'No hotel entries found for ' + (CITY_LABEL[city] || city) + ' in the dataset.'));
      return;
    }
    var h = el('h3', null, 'Hotels in ' + (CITY_LABEL[city] || city) + ' — sample data');
    hotelsEl.appendChild(h);
    list.forEach(function (x) {
      var c = el('article', 'card hotel-card');
      c.appendChild(el('h4', null, esc(x.name)));
      var meta = el('p', 'muted', esc(x.type || 'hotel') + (x.address ? ' · ' + x.address : ''));
      c.appendChild(meta);
      var row = el('div', 'action-row');
      var b = el('button', 'btn small', 'Book (mock)');
      b.type = 'button';
      b.addEventListener('click', function () {
        addBubble('Booking "' + x.name + '" is a mock in this demo — the team connects a real booking API next.', false);
      });
      row.appendChild(b);
      c.appendChild(row);
      hotelsEl.appendChild(c);
    });
  }
  function showRapido(r) {
    rapidoEl.innerHTML = '';
    var c = el('article', 'card');
    c.appendChild(el('h3', null, 'Rapido handoff'));
    c.appendChild(el('p', 'muted', esc(r.note || 'Rapido has no public booking API — this opens the app.')));
    var row = el('div', 'action-row');
    var b = el('button', 'btn small', 'Open Rapido (demo)');
    b.type = 'button';
    b.addEventListener('click', function () {
      var link = (r.deep_links && r.deep_links[0]) || 'https://www.rapido.bike/';
      var t = Date.now();
      var iframe = document.createElement('iframe');
      iframe.style.display = 'none';
      iframe.src = link;
      document.body.appendChild(iframe);
      setTimeout(function () {
        document.body.removeChild(iframe);
        if (Date.now() - t < 1600) window.open('https://www.rapido.bike/', '_blank');
      }, 1200);
      addBubble('Opening Rapido with your trip details (demo handoff).', false);
    });
    row.appendChild(b);
    c.appendChild(row);
    rapidoEl.appendChild(c);
  }

  /* ---------- tracking (real GPS when permitted, mock route otherwise) ---------- */
  var watchId = null, mockTimer = null, mockT = 0;
  function routePoints(w, h) {
    return [[w * 0.12, h * 0.8], [w * 0.3, h * 0.62], [w * 0.5, h * 0.66], [w * 0.68, h * 0.42], [w * 0.86, h * 0.3]];
  }
  function drawMap(px, py) {
    var cv = trackCanvas, ctx = cv.getContext('2d');
    var w = cv.width = cv.offsetWidth * 2, h = cv.height = 260;
    ctx.scale(1, 1);
    ctx.fillStyle = '#0f2b2b'; ctx.fillRect(0, 0, w, h);
    var pts = routePoints(w, h);
    ctx.strokeStyle = '#2dd4bf'; ctx.lineWidth = 6; ctx.lineJoin = 'round';
    ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
    for (var i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.stroke();
    pts.forEach(function (p, i) {
      ctx.fillStyle = '#fbbf24'; ctx.beginPath(); ctx.arc(p[0], p[1], 8, 0, 7); ctx.fill();
      ctx.fillStyle = '#0f2b2b'; ctx.font = 'bold 11px sans-serif'; ctx.textAlign = 'center';
      ctx.fillText(String(i + 1), p[0], p[1] + 4);
    });
    if (px != null) {
      ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(px, py, 12, 0, 7); ctx.fill();
      ctx.fillStyle = '#0ea5e9'; ctx.beginPath(); ctx.arc(px, py, 8, 0, 7); ctx.fill();
    }
  }
  function startTracking() {
    trackPanel.style.display = 'block';
    drawMap(null, null);
    trackStatus.textContent = 'Requesting location…';
    function onPos(p) {
      // map real GPS onto the demo route for the visual
      var t = ((p.coords.latitude % 1) + (p.coords.longitude % 1)) / 2;
      t = Math.abs(t) % 1;
      var pts = routePoints(trackCanvas.width, trackCanvas.height);
      var seg = Math.min(pts.length - 2, Math.floor(t * (pts.length - 1)));
      var f = t * (pts.length - 1) - seg;
      var x = pts[seg][0] + (pts[seg + 1][0] - pts[seg][0]) * f;
      var y = pts[seg][1] + (pts[seg + 1][1] - pts[seg][1]) * f;
      drawMap(x, y);
      trackStatus.textContent = 'Live GPS · ±' + Math.round(p.coords.accuracy || 0) + 'm';
    }
    function onErr() {
      trackStatus.textContent = 'GPS unavailable — playing mock route.';
      mockT = 0;
      mockTimer = setInterval(function () {
        mockT = (mockT + 0.01) % 1;
        var pts = routePoints(trackCanvas.width, trackCanvas.height);
        var seg = Math.min(pts.length - 2, Math.floor(mockT * (pts.length - 1)));
        var f = mockT * (pts.length - 1) - seg;
        drawMap(pts[seg][0] + (pts[seg + 1][0] - pts[seg][0]) * f,
                pts[seg][1] + (pts[seg + 1][1] - pts[seg][1]) * f);
      }, 120);
    }
    if (navigator.geolocation) {
      try { watchId = navigator.geolocation.watchPosition(onPos, onErr, { enableHighAccuracy: true, timeout: 8000 }); }
      catch (e) { onErr(); }
      setTimeout(function () { if (trackStatus.textContent === 'Requesting location…') onErr(); }, 9000);
    } else onErr();
  }
  function stopTracking() {
    if (watchId != null && navigator.geolocation) navigator.geolocation.clearWatch(watchId);
    if (mockTimer) clearInterval(mockTimer);
    watchId = null; mockTimer = null;
  }

  /* ---------- hotel data ---------- */
  function loadHotels(city) {
    if (hotelCache[city]) return Promise.resolve(hotelCache[city]);
    return fetch('resources/datasets/hotels/' + city + '.json')
      .then(function (r) { if (!r.ok) throw new Error('no data'); return r.json(); })
      .then(function (d) { hotelCache[city] = d.hotels || []; return hotelCache[city]; })
      .catch(function () { hotelCache[city] = []; return []; });
  }

  /* ---------- mock agent (same logic as backend mock mode) ---------- */
  function detectCity(low) {
    for (var i = 0; i < CITIES.length; i++) if (low.indexOf(CITIES[i]) !== -1) return CITIES[i];
    return '';
  }
  function mockAgent(message) {
    var low = message.toLowerCase();
    var city = detectCity(low) || (window.Virun ? window.Virun.getCity() : '') || '';
    if (/\bhotel|stay|room|lodge\b/.test(low)) {
      if (!city) { addBubble('Which city? I have hotel data for ' + CITIES.map(function (c) { return CITY_LABEL[c]; }).join(', ') + '.', false); return; }
      addTrace('search_hotels', { city: city, limit: 5 }, true, 'demo data');
      loadHotels(city).then(function (all) {
        showHotels(all.slice(0, 5), city);
        addBubble('Found ' + Math.min(5, all.length) + ' places in ' + CITY_LABEL[city] + ' (OpenStreetMap sample data). Booking is a mock in this demo.', false);
      });
      return;
    }
    if (/\brapido|bike|cab|ride\b/.test(low)) {
      addTrace('rapido_handoff', { pickup: city || 'current location' }, true, 'deep-link only');
      showRapido({ deep_links: ['rapido://ride', 'https://www.rapido.bike/'], note: 'Rapido has no public booking API — this opens the app with your trip details.' });
      addBubble('I can\'t book Rapido directly (no public API), but I prepared a handoff that opens the Rapido app.', false);
      return;
    }
    if (/\btrack|gps|live|where am i\b/.test(low)) {
      addTrace('tracking_session', { city: city || 'goa' }, true, 'browser GPS');
      addBubble('Starting live tracking — allow location access, or watch the mock route.', false);
      startTracking();
      return;
    }
    if (/\bplan|itinerary|trip\b/.test(low)) {
      addBubble('Tell me origin and destination — e.g. "plan Vizag to Goa, 3 days" — and I\'ll sketch the trip. Full planning is the team\'s planner API.', false);
      return;
    }
    addBubble('I can search hotels (' + CITIES.length + ' cities), track you live, and hand off to Rapido. Try "hotels in Goa".', false);
  }

  /* ---------- chat flow ---------- */
  function send(text) {
    text = (text || '').trim();
    if (!text) return;
    addBubble(text, true);
    input.value = '';
    var city = window.Virun ? window.Virun.getCity() : '';
    if (backendLive) {
      fetch('/api/agent/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, city: city })
      }).then(function (r) { return r.json(); }).then(function (d) {
        (d.tool_calls || []).forEach(function (t) { addTrace(t.tool, t.args, t.ok, t.note); });
        if (d.hotels && d.hotels.length) showHotels(d.hotels, city);
        if (d.rapido) showRapido(d.rapido);
        addBubble(d.reply || '…', false);
      }).catch(function () { mockAgent(text); });
    } else {
      setTimeout(function () { mockAgent(text); }, 350);
    }
  }

  function init() {
    log = document.getElementById('agentLog');
    form = document.getElementById('agentForm');
    input = document.getElementById('agentInput');
    traceEl = document.getElementById('agentTrace');
    hotelsEl = document.getElementById('agentHotels');
    rapidoEl = document.getElementById('agentRapido');
    modeBadge = document.getElementById('agentMode');
    trackPanel = document.getElementById('trackPanel');
    trackCanvas = document.getElementById('trackCanvas');
    trackStatus = document.getElementById('trackStatus');
    if (!log) return;
    form.addEventListener('submit', function (e) { e.preventDefault(); send(input.value); });
    document.querySelectorAll('[data-agent-chip]').forEach(function (c) {
      c.addEventListener('click', function () { send(c.getAttribute('data-agent-chip')); });
    });
    document.getElementById('trackBtn').addEventListener('click', startTracking);
    document.getElementById('trackStop').addEventListener('click', function () { stopTracking(); trackStatus.textContent = 'Stopped.'; });
    window.addEventListener('beforeunload', stopTracking);
    fetch('/api/agent/cities').then(function (r) { return r.json(); }).then(function () {
      backendLive = true;
      modeBadge.textContent = 'Live backend';
      modeBadge.classList.add('live');
    }).catch(function () {
      modeBadge.textContent = 'Demo data';
    });
    addBubble('Hi, I\'m the Virun travel agent. I can search hotels across 7 cities, track your trip live, and hand off rides to Rapido. What\'s the plan?', false);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
