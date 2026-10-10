/* Virun shared utilities — same behavior as the single-file build. */
(function () {
  'use strict';
  var D = window.VirunData;

  function esc(s) {
    return String(s).replace(/[&<>'"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c];
    });
  }

  var ICONS = {
    home: '<path d="M3 11.5 12 4l9 7.5V21h-6v-6H9v6H3z"/>',
    plan: '<path d="M5 3h14v18H5zM8 8h8M8 12h8M8 16h5"/>',
    guide: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-5 3.5-8 8-8s8 3 8 8"/>',
    feed: '<rect x="3" y="3" width="8" height="8"/><rect x="13" y="3" width="8" height="8"/><rect x="3" y="13" width="8" height="8"/><rect x="13" y="13" width="8" height="8"/>',
    profile: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-5 3.5-8 8-8s8 3 8 8"/>',
    arrow: '<path d="m9 18 6-6-6-6"/>',
    shield: '<path d="M12 3 4 6v5c0 5 3.4 8.7 8 10 4.6-1.3 8-5 8-10V6z"/><path d="m9 12 2 2 4-5"/>',
    plane: '<path d="m2 16 20-9-7 13-3-6-10 2zM12 14 9 9"/>'
  };
  function icon(n) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      (ICONS[n] || ICONS.arrow) + '</svg>';
  }

  function imageAsset(path) { return D.img(path); }
  function photo(c, n) {
    var k = c.toLowerCase();
    return imageAsset(k + '/photos/' + k + '_' + String(n).padStart(2, '0') + '.jpg');
  }
  function photoName(c, n) {
    return c === 'Goa' ? D.goaPhotoNames[n - 1] : c + ' travel scene ' + n;
  }
  function avatar() {
    return '<div class="avatar" aria-hidden="true"><svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3"><circle cx="32" cy="22" r="12"/><path d="M10 58c2-14 10-22 22-22s20 8 22 22"/></svg></div>';
  }

  /* ---- session state (replaces the old in-memory vars) ---- */
  var store = {
    get: function (k, fb) { try { var v = localStorage.getItem('virun_' + k); return v === null ? fb : v; } catch (e) { return fb; } },
    set: function (k, v) { try { localStorage.setItem('virun_' + k, v); } catch (e) {} },
    getJSON: function (k, fb) { try { var v = localStorage.getItem('virun_' + k); return v ? JSON.parse(v) : fb; } catch (e) { return fb; } },
    setJSON: function (k, v) { try { localStorage.setItem('virun_' + k, JSON.stringify(v)); } catch (e) {} }
  };
  function getCity() { return store.get('city', 'Goa'); }
  function setCity(c) { store.set('city', c); }
  function getUserName() { return store.get('username', 'Traveler'); }
  function getJourney() {
    return store.getJSON('journey', { from: 'Visakhapatnam', to: 'Hyderabad', date: '', mode: 'all' });
  }

  /* ---- destination theme (full-page photo + accent + weather) ---- */
  function applyTheme(app) {
    var city = getCity(), data = D.cityData[city] || D.cityData.Goa;
    document.documentElement.style.setProperty('--accent', data.accent);
    var scene = document.getElementById('scene');
    if (scene) {
      scene.innerHTML = '';
      scene.style.backgroundImage = 'none';
      if (city === 'Goa' && app) {
        scene.innerHTML = data.images.map(function (src, i) {
          return '<span class="scene-slide" style="background-image:url(&quot;' + src + '&quot;);animation-delay:' + (i * 6) + 's"></span>';
        }).join('');
      } else {
        scene.style.backgroundImage = "url('" + data.image + "')";
      }
    }
    document.querySelectorAll('[data-fill="city"]').forEach(function (el) { el.textContent = city; });
    document.querySelectorAll('[data-fill="username"]').forEach(function (el) { el.textContent = getUserName(); });
  }

  /* ---- live weather badges (Open-Meteo, no key) ---- */
  function wxIcon(code) {
    var sun = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
    var cloud = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.5 19a4.5 4.5 0 0 0 0-9 6 6 0 0 0-11.6 1.6A4 4 0 0 0 7 19h10.5z"/></svg>';
    var rain = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.5 15a4.5 4.5 0 0 0 0-9 6 6 0 0 0-11.6 1.6A4 4 0 0 0 7 15h10.5z"/><path d="M8 18v2M12 17v3M16 18v2"/></svg>';
    var storm = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.5 14a4.5 4.5 0 0 0 0-9 6 6 0 0 0-11.6 1.6A4 4 0 0 0 7 14h10.5z"/><path d="M12 14l-3 5h4l-2 3"/></svg>';
    var snow = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M4 6l16 12M20 6 4 18M12 6l-2-2M12 6l2-2M12 18l-2 2M12 18l2 2"/></svg>';
    var fog = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 10h16M6 14h12M8 18h8"/></svg>';
    if (code === 0 || code === 1) return sun;
    if (code === 2 || code === 3 || code === 45 || code === 48) return cloud;
    if (code >= 51 && code <= 67) return rain;
    if (code >= 71 && code <= 77) return snow;
    if (code >= 80 && code <= 82) return rain;
    if (code >= 95) return storm;
    if (code === 45 || code === 48) return fog;
    return cloud;
  }
  function hydrateWeather() {
    document.querySelectorAll('[data-wx]').forEach(function (el) {
      if (el.getAttribute('data-done')) return;
      el.setAttribute('data-done', '1');
      var c = el.getAttribute('data-wx'), co = D.cityCoords[c];
      if (!co) return;
      fetch('https://api.open-meteo.com/v1/forecast?latitude=' + co[0] + '&longitude=' + co[1] + '&current=temperature_2m,weather_code')
        .then(function (r) { return r.json(); })
        .then(function (d) {
          var t = Math.round(d.current.temperature_2m);
          el.innerHTML = wxIcon(d.current.weather_code) + '<span>' + t + '&deg;</span>';
        })
        .catch(function () { el.innerHTML = '<span>--&deg;</span>'; });
    });
  }

  /* ---- weather particles on app pages (per-city treatments) ---- */
  var particles = [], raf = null;
  function stopWeather() { if (raf) { cancelAnimationFrame(raf); raf = null; } }
  function startWeather() {
    stopWeather();
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var c = document.getElementById('weather');
    if (!c) return;
    var x = c.getContext('2d'), d = Math.min(2, devicePixelRatio || 1), w, h;
    function size() {
      w = innerWidth; h = innerHeight;
      c.width = w * d; c.height = h * d;
      c.style.width = w + 'px'; c.style.height = h + 'px';
      x.setTransform(d, 0, 0, d, 0, 0);
    }
    size();
    particles = [];
    var n = Math.min(95, Math.floor(w / 9));
    for (var i = 0; i < n; i++) particles.push({ x: (i * 73) % w, y: (i * 119) % h, s: 2 + i % 5, v: .35 + (i % 7) * .09, o: .25 + (i % 6) * .08, p: i * .8 });
    function draw() {
      x.clearRect(0, 0, w, h);
      var k = (D.cityData[getCity()] || D.cityData.Goa).key, t = performance.now() / 1000;
      particles.forEach(function (q) {
        if (k === 'kashmir') {
          q.y += q.v * 2; q.x += Math.sin(t + q.p) * .2; if (q.y > h + 8) q.y = -8;
          x.fillStyle = 'rgba(255,255,255,' + q.o + ')'; x.beginPath(); x.arc(q.x, q.y, q.s * .65, 0, Math.PI * 2); x.fill();
        } else if (k === 'goa') {
          q.y -= q.v * .35; q.x += Math.sin(t * .45 + q.p) * .18; if (q.y < -8) q.y = h + 8;
          x.fillStyle = 'rgba(255,205,96,' + (q.o * .72) + ')'; x.beginPath(); x.arc(q.x, q.y, q.s * 1.2, 0, Math.PI * 2); x.fill();
        } else if (k === 'hyderabad') {
          q.y -= q.v * 1.2; if (q.y < -30) q.y = h + 30;
          x.strokeStyle = 'rgba(245,158,11,' + (q.o * .35) + ')'; x.lineWidth = 1.2; x.beginPath();
          x.moveTo(q.x + Math.sin(t * 2 + q.p) * 7, q.y);
          x.quadraticCurveTo(q.x - 8, q.y + 10, q.x + Math.cos(t + q.p) * 7, q.y + 22); x.stroke();
        } else {
          q.x += q.v * 1.4; q.y += Math.sin(t + q.p) * .15; if (q.x > w + 15) q.x = -15;
          x.strokeStyle = 'rgba(125,211,252,' + (q.o * .5) + ')'; x.lineWidth = 1.4; x.beginPath();
          x.moveTo(q.x, q.y); x.lineTo(q.x + q.s * 4, q.y + Math.sin(q.p) * 3); x.stroke();
        }
      });
      raf = requestAnimationFrame(draw);
    }
    draw();
  }

  /* ---- scroll-reveal motion ---- */
  function setupMotion() {
    var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    var nodes = document.querySelectorAll('#main .card,#main .metric,#main .section-head,#main .page-head,#main .list-row,#main figure');
    nodes.forEach(function (el, i) {
      el.classList.add('reveal');
      el.style.setProperty('--stagger', ((i % 7) * .08) + 's');
    });
    if (reduce) { nodes.forEach(function (el) { el.classList.add('is-visible'); }); }
    else if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) { if (entry.isIntersecting) { entry.target.classList.add('is-visible'); io.unobserve(entry.target); } });
      }, { threshold: .12 });
      nodes.forEach(function (el) { io.observe(el); });
    } else { nodes.forEach(function (el) { el.classList.add('is-visible'); }); }
    requestAnimationFrame(function () {
      document.querySelectorAll('.progress>i').forEach(function (el) { el.classList.add('bar-animate'); });
    });
  }

  function footerHTML() {
    return '<footer class="public-footer"><div class="footer-inner"><div><strong>Plan with context. Travel with local knowledge.</strong><div class="footer-note">Photos: Wikimedia Commons. Map data: OpenStreetMap contributors.</div></div><div class="footer-links"><a href="pricing.html">Pricing</a><a href="explore.html">Explore</a><a href="reviews.html">Reviews</a><a href="about-team.html">About Team</a><a href="privacy.html">Privacy Policy</a><a href="terms.html">Terms and Conditions</a></div></div></footer>';
  }

  window.Virun = {
    esc: esc, icon: icon, imageAsset: imageAsset, photo: photo, photoName: photoName,
    avatar: avatar, store: store, getCity: getCity, setCity: setCity,
    getUserName: getUserName, getJourney: getJourney, applyTheme: applyTheme,
    hydrateWeather: hydrateWeather, startWeather: startWeather, stopWeather: stopWeather,
    setupMotion: setupMotion, footerHTML: footerHTML
  };
})();
