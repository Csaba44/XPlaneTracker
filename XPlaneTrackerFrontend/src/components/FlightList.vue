<template>
  <div style="display: flex; flex-direction: column; height: 100vh">
    <div style="padding: 20px; border-bottom: 1px solid #ccc">
      <h2>Recorded Flights</h2>
      <div v-if="flights.length === 0">No flights found.</div>
      <ul v-else style="display: flex; gap: 10px; list-style: none; padding: 0; overflow-x: auto">
        <li v-for="flight in flights" :key="flight.id" style="white-space: nowrap; border: 1px solid #ddd; padding: 10px">
          <strong>{{ flight.callsign }}</strong> ({{ flight.flight_number }})
          <button @click="viewFlight(flight.id)" style="margin-left: 10px">View Path</button>
        </li>
      </ul>
    </div>

    <div id="map" style="flex-grow: 1"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from "vue";
import api from "../config/api";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const flights = ref([]);
const map = ref(null);
const pathLayers = ref([]);

const getColor = (alt) => {
  if (alt < 1000) return "#ff0000";
  if (alt < 5000) return "#ff7800";
  if (alt < 15000) return "#ffff00";
  if (alt < 25000) return "#00ff00";
  if (alt < 35000) return "#00ffff";
  return "#0000ff";
};

const initMap = () => {
  map.value = L.map("map").setView([47.0, 19.0], 7);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors",
  }).addTo(map.value);
};

const clearMap = () => {
  pathLayers.value.forEach((layer) => map.value.removeLayer(layer));
  pathLayers.value = [];
};

const fetchFlights = async () => {
  try {
    const response = await api.get("/flights");
    flights.value = response.data;
  } catch (error) {
    console.error(error);
  }
};

const viewFlight = async (id) => {
  try {
    const response = await api.get(`/flights/${id}`);
    const data = response.data;

    clearMap();

    const points = data.path;
    const segments = [];

    for (let i = 0; i < points.length - 1; i++) {
      const start = points[i];
      const end = points[i + 1];

      const poly = L.polyline(
        [
          [start[1], start[2]],
          [end[1], end[2]],
        ],
        {
          color: getColor(start[3]),
          weight: 4,
          opacity: 0.8,
        },
      ).addTo(map.value);

      pathLayers.value.push(poly);
      segments.push(poly);
    }

    data.landings.forEach((landing) => {
      const marker = L.circleMarker([landing.lat, landing.lon], {
        radius: 8,
        fillColor: "#ffffff",
        color: "#000",
        weight: 2,
        fillOpacity: 1,
      }).addTo(map.value);

      marker.bindPopup(`
        <strong>Landing Recorded</strong><br>
        FPM: ${landing.fpm}<br>
        G-Force: ${landing.g_force}G
      `);

      pathLayers.value.push(marker);
    });

    if (segments.length > 0) {
      const group = new L.featureGroup(segments);
      map.value.fitBounds(group.getBounds());
    }
  } catch (error) {
    console.error(error);
  }
};

onMounted(async () => {
  await fetchFlights();
  initMap();
});
</script>

<style>
.leaflet-container {
  background: #242424;
}
</style>
