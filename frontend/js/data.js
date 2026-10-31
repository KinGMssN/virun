/* Virun shared data — static frontend demo (no backend calls). */
(function () {
  'use strict';
  var imageRoot = location.pathname.indexOf('/spaces/v2/') !== -1
    ? 'assets/resources/images/'
    : 'resources/images/';

  var cityCoords = {
    Kashmir: [34.0837, 74.7973], Goa: [15.4909, 73.8278],
    Hyderabad: [17.3850, 78.4867], Visakhapatnam: [17.6868, 83.2185],
    Mumbai: [19.0760, 72.8777], Delhi: [28.6139, 77.2090],
    Bengaluru: [12.9716, 77.5946]
  };

  var cityPhotoCounts = {
    Kashmir: 10, Goa: 15, Hyderabad: 10, Visakhapatnam: 10,
    Mumbai: 3, Delhi: 3, Bengaluru: 3
  };

  var goaPhotoNames = ['Baga Beach', 'Aguada Fort', 'Basilica of Bom Jesus',
    'Chapora Fort at sunset', 'Dudhsagar Falls', 'Palolem Beach', 'Old Goa churches',
    'Anjuna Beach', 'Fontainhas', 'Reis Magos Fort', 'Colva Beach', 'Arambol',
    'Mangueshi Temple', 'Miramar Beach', 'Cabo de Rama'];

  /* Mock transport options — the marked swap-in point for the team's booking API. */
  var mockTransportOptions = [
    { id: 'train-t101', kind: 'Train', name: 'Demo Rail T-101', depart: '06:20', arrive: '19:15', duration: '12h 55m', fare: 510, seats: 42, className: 'Second sitting' },
    { id: 'train-t204', kind: 'Train', name: 'Demo Night Rail T-204', depart: '17:20', arrive: '05:40', duration: '12h 20m', fare: 865, seats: 18, className: 'Sleeper' },
    { id: 'bus-b310', kind: 'Bus', name: 'Demo State Bus B-310', depart: '19:30', arrive: '08:00', duration: '12h 30m', fare: 980, seats: 12, className: 'Super luxury' },
    { id: 'bus-b422', kind: 'Bus', name: 'Demo Sleeper B-422', depart: '21:00', arrive: '08:30', duration: '11h 30m', fare: 1450, seats: 7, className: 'AC sleeper' }
  ];

  var journeyCities = ['Visakhapatnam', 'Hyderabad', 'Vijayawada', 'Chennai', 'Bengaluru', 'Goa'];

  function img(path) { return imageRoot + path; }

  var cityData = {
    Kashmir: { key: 'kashmir', accent: '#7DD3FC', image: img('kashmir/photos/kashmir_01.jpg') },
    Goa: {
      key: 'goa', accent: '#2DD4BF', image: img('goa/photos/goa_beach_hero.jpg'),
      images: [img('goa/photos/goa_beach_hero.jpg')].concat(
        Array.from({ length: 15 }, function (_, i) {
          return img('goa/photos/goa_' + String(i + 1).padStart(2, '0') + '.jpg');
        }))
    },
    Hyderabad: { key: 'hyderabad', accent: '#F59E0B', image: img('hyderabad/photos/hyderabad_01.jpg') },
    Visakhapatnam: { key: 'visakhapatnam', accent: '#38BDF8', image: img('visakhapatnam/photos/visakhapatnam_01.jpg') },
    Mumbai: { key: 'mumbai', accent: '#F472B6', image: img('mumbai/photos/mumbai_01.jpg') },
    Delhi: { key: 'delhi', accent: '#A78BFA', image: img('delhi/photos/delhi_01.jpg') },
    Bengaluru: { key: 'bengaluru', accent: '#34D399', image: img('bengaluru/photos/bengaluru_01.jpg') }
  };

  /* Sample guide persona for the guide dashboard demo. */
  var guideSample = {
    previousWorks: [
      { title: 'Old City heritage walk', city: 'Hyderabad', detail: 'Charminar, Laad Bazaar and Chowmahalla — 4 hours, offline' },
      { title: 'Coastal sunrise tour', city: 'Visakhapatnam', detail: 'Rushikonda Beach and Kailasagiri — 3 hours, offline' },
      { title: 'Fort stories video call', city: 'Goa', detail: 'Aguada Fort history session — 45 minutes, online' }
    ],
    knownCities: ['Visakhapatnam', 'Hyderabad', 'Goa', 'Vijayawada'],
    examples: [
      { title: 'City orientation walk', meta: '3 hours · Offline · Rs 600', detail: 'First-day route: landmarks, food streets and local transport basics.' },
      { title: 'Heritage deep-dive', meta: 'Full day · Offline · Rs 1,200', detail: 'Forts, old quarters and stories, with a lunch stop.' },
      { title: 'Plan-my-day video call', meta: '45 minutes · Online · Rs 150', detail: 'Route review and local tips before the trip.' }
    ]
  };


  /* Demo accounts, browser only. Passwords are demo only, checked locally,
     never sent to a server. Real accounts need live Supabase, still pending. */
  var demoAccounts = [
    { id: 'guide-vizag', role: 'guide', name: 'Priya Reddy', username: 'priya.vizag', email: 'priya.vizag@virun.demo', password: 'Vizag@123', city: 'Visakhapatnam', languages: 'Telugu, English, Hindi', tours: 'Coastal sunrise tour, RK Beach heritage walk', priceOnline: 'Rs 400 for 45 minutes online', priceOffline: 'Rs 1,200 for a full day offline' },
    { id: 'guide-kashmir', role: 'guide', name: 'Imran Sheikh', username: 'imran.kashmir', email: 'imran.kashmir@virun.demo', password: 'Kashmir@123', city: 'Kashmir', languages: 'Hindi, English, Kashmiri', tours: 'Gulmarg adventure day, Dal Lake heritage walk', priceOnline: 'Rs 600 for 45 minutes online', priceOffline: 'Rs 2,000 for a full day offline' },
    { id: 'guide-bengaluru', role: 'guide', name: 'Arjun Rao', username: 'arjun.bengaluru', email: 'arjun.bengaluru@virun.demo', password: 'Bengaluru@123', city: 'Bengaluru', languages: 'Kannada, English, Hindi', tours: 'City orientation walk, Lalbagh and old Bengaluru walk', priceOnline: 'Rs 500 for 45 minutes online', priceOffline: 'Rs 1,500 for a full day offline' },
    { id: 'tourist-rohan', role: 'tourist', name: 'Rohan Mehta', username: 'rohan.tourist', email: 'rohan.mehta@virun.demo', password: 'Tourist@123', city: 'Kashmir', homeCity: 'Mumbai', wants: 'Kashmir adventure trip' },
    { id: 'tourist-sneha', role: 'tourist', name: 'Sneha Patel', username: 'sneha.tourist', email: 'sneha.patel@virun.demo', password: 'Tourist@123', city: 'Visakhapatnam', homeCity: 'Hyderabad', wants: 'Visakhapatnam heritage trip' },
    { id: 'tourist-vikram', role: 'tourist', name: 'Vikram Singh', username: 'vikram.tourist', email: 'vikram.singh@virun.demo', password: 'Tourist@123', city: 'Bengaluru', homeCity: 'Delhi', wants: 'Bengaluru city trip' },
    { id: 'tourist-divya', role: 'tourist', name: 'Divya Kumar', username: 'divya.tourist', email: 'divya.kumar@virun.demo', password: 'Tourist@123', city: 'Goa', homeCity: 'Chennai', wants: 'Goa beach trip' }
  ];

  window.VirunData = {
    imageRoot: imageRoot, cityCoords: cityCoords, cityPhotoCounts: cityPhotoCounts,
    goaPhotoNames: goaPhotoNames, mockTransportOptions: mockTransportOptions,
    journeyCities: journeyCities, cityData: cityData, guideSample: guideSample, demoAccounts: demoAccounts, img: img
  };
})();
