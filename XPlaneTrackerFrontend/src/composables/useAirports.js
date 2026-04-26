const airportCoordCache = new Map();
let airportsJsonData = null;

export const loadAirportsJson = async () => {
  if (airportsJsonData) return airportsJsonData;
  try {
    const response = await fetch("https://raw.githubusercontent.com/mwgg/Airports/master/airports.json");
    airportsJsonData = await response.json();
    return airportsJsonData;
  } catch (e) {
    console.error("Failed to load airports.json", e);
    return {};
  }
};

export const getAirportCoords = async (icao) => {
  if (!icao) return null;
  const upper = icao.toUpperCase();
  if (airportCoordCache.has(upper)) return airportCoordCache.get(upper);

  const airports = await loadAirportsJson();
  const airport = airports[upper];
  if (airport && airport.lat != null && airport.lon != null) {
    const coords = [parseFloat(airport.lat), parseFloat(airport.lon)];
    airportCoordCache.set(upper, coords);
    return coords;
  }
  airportCoordCache.set(upper, null);
  return null;
};