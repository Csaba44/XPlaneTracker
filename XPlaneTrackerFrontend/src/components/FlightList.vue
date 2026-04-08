<script setup>
import { ref, onMounted } from "vue";
import api from "../config/api";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const flights = ref([]);
const map = ref(null);
const pathLayers = ref([]);
const selectedFlightId = ref(null);

const altitudeTiers = [
  { alt: 0, label: "0 - 1k", color: "#ef4444" },
  { alt: 1000, label: "1k - 5k", color: "#f97316" },
  { alt: 5000, label: "5k - 15k", color: "#eab308" },
  { alt: 15000, label: "15k - 25k", color: "#22c55e" },
  { alt: 25000, label: "25k - 35k", color: "#06b6d4" },
  { alt: 35000, label: "35k+", color: "#3b82f6" },
];

const getColor = (alt) => {
  if (alt < 1000) return "#ef4444";
  if (alt < 5000) return "#f97316";
  if (alt < 15000) return "#eab308";
  if (alt < 25000) return "#22c55e";
  if (alt < 35000) return "#06b6d4";
  return "#3b82f6";
};

const initMap = () => {
  map.value = L.map("map", { zoomControl: false }).setView([47.0, 19.0], 7);
  L.control.zoom({ position: "bottomright" }).addTo(map.value);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    subdomains: "abcd",
    maxZoom: 20,
  }).addTo(map.value);
};

const clearMap = () => {
  if (!map.value) return;
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
  selectedFlightId.value = id;
  try {
    const response = await api.get(`/flights/${id}`);
    const data = response.data;
    clearMap();
    if (!map.value) return;

    const segments = [];
    data.path.forEach((point, i) => {
      if (i === data.path.length - 1) return;
      const next = data.path[i + 1];
      const poly = L.polyline(
        [
          [point[1], point[2]],
          [next[1], next[2]],
        ],
        {
          color: getColor(point[3]),
          weight: 4,
          opacity: 0.9,
          lineCap: "round",
        },
      ).addTo(map.value);
      pathLayers.value.push(poly);
      segments.push(poly);
    });

    data.landings.forEach((landing) => {
      const marker = L.circleMarker([landing.lat, landing.lon], {
        radius: 10,
        fillColor: "#ffffff",
        color: "#38bdf8",
        weight: 3,
        fillOpacity: 1,
      }).addTo(map.value);

      marker.bindPopup(`
        <div class="p-1">
          <h3 class="font-bold text-sky-400 border-b border-gray-700 mb-2">Touchdown</h3>
          <p class="text-xs">Vertical: <span class="text-white">${landing.fpm} FPM</span></p>
          <p class="text-xs">Force: <span class="text-white">${landing.g_force}G</span></p>
        </div>
      `);
      pathLayers.value.push(marker);
    });

    if (segments.length > 0) {
      const group = new L.featureGroup(segments);
      map.value.fitBounds(group.getBounds(), { padding: [50, 50] });
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

<template>
  <div class="flex h-screen w-screen bg-flight-bg text-slate-300 overflow-hidden font-sans">
    <aside class="w-85 flex flex-col bg-flight-sidebar border-r border-flight-border z-[1000] shadow-2xl">
      <div class="p-8">
        <div class="flex items-center space-x-3">
          <div class="w-2 h-8 bg-flight-accent rounded-full"></div>
          <div>
            <h1 class="text-2xl font-black text-white tracking-tighter italic">X-TRACKER</h1>
            <p class="text-[10px] text-flight-accent uppercase font-bold tracking-widest">Live Telemetry Analysis</p>
          </div>
        </div>
      </div>

      <div class="flex-grow overflow-y-auto px-4 pb-4 space-y-3">
        <div v-if="flights.length === 0" class="text-center py-20 text-slate-600">
          <p class="text-sm">Waiting for flight data...</p>
        </div>

        <div v-for="flight in flights" :key="flight.id" @click="viewFlight(flight.id)" :class="['p-5 rounded-xl cursor-pointer transition-all duration-300 border', selectedFlightId === flight.id ? 'bg-flight-card border-flight-accent shadow-[0_0_15px_rgba(56,189,248,0.2)]' : 'bg-transparent border-transparent hover:bg-flight-card-hover hover:border-flight-border']">
          <div class="flex justify-between items-center mb-3">
            <span class="text-xl font-bold text-white group-hover:text-flight-accent">{{ flight.callsign }}</span>
            <span class="text-[10px] bg-flight-bg text-flight-accent border border-flight-accent/30 px-2 py-1 rounded font-mono">
              {{ flight.flight_number }}
            </span>
          </div>
          <div class="flex justify-between items-end text-xs text-slate-500">
            <div class="flex flex-col">
              <span class="text-slate-400 font-medium">{{ flight.airline }}</span>
              <span>{{ new Date(flight.start_time).toLocaleDateString() }}</span>
            </div>
            <i class="fas fa-chevron-right text-flight-border"></i>
          </div>
        </div>
      </div>

      <div class="p-6 bg-black/40 border-t border-flight-border">
        <h4 class="text-[10px] font-bold text-slate-500 mb-4 uppercase tracking-widest">Altitude Legend (MSL)</h4>
        <div class="grid grid-cols-2 gap-x-4 gap-y-2">
          <div v-for="tier in altitudeTiers" :key="tier.alt" class="flex items-center space-x-3">
            <div class="w-2.5 h-2.5 rounded-sm shadow-sm" :style="{ backgroundColor: tier.color }"></div>
            <span class="text-[11px] text-slate-400 font-medium">{{ tier.label }}</span>
          </div>
        </div>
      </div>
    </aside>

    <main class="flex-grow relative">
      <div id="map"></div>
    </main>
  </div>
</template>
