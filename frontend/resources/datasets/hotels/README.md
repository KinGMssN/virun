# Hotels dataset (OpenStreetMap, ODbL — attribution required)

One JSON per city: `kashmir`, `goa`, `hyderabad`, `visakhapatnam`,
`mumbai`, `delhi`, `bengaluru`. Each file: `{ city, count, source, hotels[] }`
with `name, type, lat, lng, stars, rooms, phone, website, address`.

Used by:

- Frontend agent demo (`frontend/agent.html` + `js/agent.js`) — sample data,
  booking buttons are mocks.
- Backend agent service (`backend/app/agent/tools.py::search_hotels`).

Do not treat entries as bookable inventory — connect a real booking API
(e.g. Amadeus) for that. Regenerate with
`virun-assets/resources/datasets/hotels/build_hotels.py` (+ the 3-city
extension used for Mumbai/Delhi/Bengaluru).
