/* Virun navigation bars — injected per page by boot.js. */
(function () {
  'use strict';
  function publicNav(active) {
    var links = [
      ['index.html', 'Home'], ['pricing.html', 'Pricing'], ['explore.html', 'Explore'],
      ['reviews.html', 'Reviews'], ['about-team.html', 'Team']
    ];
    return '<header class="public-nav"><nav class="nav-inner" aria-label="Primary"><div class="nav-links">' +
      links.map(function (l) {
        return '<a class="nav-link' + (active === l[0] ? ' active' : '') + '" href="' + l[0] + '">' + l[1] + '</a>';
      }).join('') +
      '</div><div class="nav-links"><a class="nav-link' + (active === 'signin.html' ? ' active' : '') +
      '" href="signin.html">Sign In</a><a class="btn coral small" href="signup.html">Create Account</a></div></nav></header>';
  }

  function cityOptions(selected) {
    return Object.keys(window.VirunData.cityData).map(function (c) {
      return '<option' + (c === selected ? ' selected' : '') + '>' + c + '</option>';
    }).join('');
  }

  function appNav(active) {
    var V = window.Virun;
    var links = [
      ['tourist-dashboard.html', 'Dashboard'], ['journey-search.html', 'Train &amp; Bus'],
      ['discovery.html', 'Discover'], ['tourist-profile.html', 'Profile']
    ];
    return '<header class="app-top"><div class="app-top-inner">' +
      '<div class="trip-switch"><label for="citySelect">Choose My Trip</label>' +
      '<select id="citySelect">' + cityOptions(V.getCity()) + '</select></div>' +
      '<nav class="desktop-links">' +
      links.map(function (l) {
        return '<a class="nav-link' + (active === l[0] ? ' active' : '') + '" href="' + l[0] + '">' + l[1] + '</a>';
      }).join('') + '</nav>' +
      '<a class="btn small" href="active-trip.html">Active trip</a></div></header>';
  }

  function guideNav(active) {
    var V = window.Virun;
    var links = [
      ['guide-dashboard.html', 'Dashboard'], ['guide-requests.html', 'Requests'],
      ['guide-earnings.html', 'Earnings'], ['guide-profile.html', 'Profile']
    ];
    return '<header class="app-top"><div class="app-top-inner">' +
      '<div class="trip-switch"><label for="citySelect">Guide city</label>' +
      '<select id="citySelect">' + cityOptions(V.getCity()) + '</select></div>' +
      '<nav class="desktop-links">' +
      links.map(function (l) {
        return '<a class="nav-link' + (active === l[0] ? ' active' : '') + '" href="' + l[0] + '">' + l[1] + '</a>';
      }).join('') + '</nav>' +
      '<a class="btn small" href="guide-requests.html">Booking queue</a></div></header>';
  }

  function mobileNav(active) {
    var V = window.Virun;
    var items = [
      ['tourist-dashboard.html', 'home', 'Home'], ['journey-search.html', 'plan', 'Travel'],
      ['discovery.html', 'feed', 'Discover'], ['tourist-profile.html', 'profile', 'Profile']
    ];
    return '<nav class="bottom-nav" aria-label="Mobile app">' +
      items.map(function (x) {
        return '<a class="' + (active === x[0] ? 'active' : '') + '" href="' + x[0] + '">' + V.icon(x[1]) + '<span>' + x[2] + '</span></a>';
      }).join('') + '</nav>';
  }

  window.VirunNav = {
    publicNav: publicNav, appNav: appNav, guideNav: guideNav, mobileNav: mobileNav
  };
})();
