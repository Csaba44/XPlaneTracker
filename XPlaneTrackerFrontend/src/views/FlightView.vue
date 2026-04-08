<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import api from "../config/api";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const router = useRouter();
const authStore = useAuthStore();

const flights = ref([]);
const map = ref(null);
const pathLayers = ref([]);
const selectedFlightId = ref(null);
const generatedApiKey = ref(null);

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
    const response = await api.get("/api/flights");
    flights.value = response.data;
  } catch (error) {
    console.error(error);
  }
};

const viewFlight = async (id) => {
  selectedFlightId.value = id;
  try {
    const response = await api.get(`/api/flights/${id}`);
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
      const icon = L.divIcon({
        html: `<div class="bg-flight-accent w-8 h-8 rounded-full flex items-center justify-center border-2 border-white shadow-lg shadow-cyan-500/50">
                <i class="fa-solid fa-plane-arrival text-white text-xs"></i>
               </div>`,
        className: "custom-div-icon",
        iconSize: [32, 32],
        iconAnchor: [16, 32],
      });

      const marker = L.marker([landing.lat, landing.lon], { icon }).addTo(map.value);

      marker.bindPopup(
        `
        <div class="bg-flight-sidebar text-slate-300 p-4 rounded-lg border border-flight-border min-w-[160px] shadow-xl">
          <div class="flex items-center space-x-2 mb-3 border-b border-flight-border pb-2 pr-6">
             <i class="fa-solid fa-location-dot text-flight-accent"></i>
             <h3 class="font-bold text-white text-sm uppercase tracking-wider">Touchdown</h3>
          </div>
          <div class="space-y-2">
            <p class="text-[11px] flex justify-between gap-6">
              <span class="text-slate-500 font-medium">Vertical:</span> 
              <span class="font-mono text-flight-accent font-bold">${landing.fpm} FPM</span>
            </p>
            <p class="text-[11px] flex justify-between gap-6">
              <span class="text-slate-500 font-medium">G-Force:</span> 
              <span class="font-mono text-flight-accent font-bold">${landing.g_force}G</span>
            </p>
          </div>
        </div>
      `,
        {
          className: "flight-popup",
          maxWidth: 300,
        },
      );
      pathLayers.value.push(marker);
    });

    if (segments.length > 0) {
      const group = new L.featureGroup(segments);
      map.value.fitBounds(group.getBounds(), { padding: [100, 100] });
    }
  } catch (error) {
    console.error(error);
  }
};

const handleLogout = async () => {
  try {
    await authStore.logout();
    router.push("/login");
  } catch (error) {
    console.error(error);
  }
};

const generateApiKey = async () => {
  try {
    const response = await api.post("/api/tokens/create");
    generatedApiKey.value = response.data.token;
  } catch (error) {
    console.error(error);
  }
};

onMounted(async () => {
  if (!authStore.user) {
    await authStore.fetchUser();
  }
  await fetchFlights();
  initMap();
});
</script>

<template>
  <div class="flex h-screen w-screen bg-flight-bg text-slate-300 overflow-hidden font-sans">
    <aside class="w-85 flex flex-col bg-flight-sidebar border-r border-flight-border z-[1000] shadow-2xl">
      <div class="p-8 pb-6">
        <div class="flex items-center space-x-3 mb-6">
          <div class="w-2 h-8 bg-flight-accent rounded-full shadow-[0_0_10px_#38bdf8]"></div>
          <div>
            <h1 class="text-2xl font-black text-white tracking-tighter italic leading-none">X-TRACKER</h1>
            <p class="text-[10px] text-flight-accent uppercase font-bold tracking-widest mt-1">Muro phralenge 🍀</p>
          </div>
        </div>

        <div class="flex flex-col space-y-2 mb-4">
          <div class="flex items-center justify-between bg-flight-card border border-flight-border p-3 rounded-lg">
            <div class="flex flex-col">
              <span class="text-[9px] uppercase tracking-widest text-slate-500 font-bold">Szia testvér!</span>
              <span class="text-xs text-white font-bold truncate max-w-[120px]">
                {{ authStore.user?.email || "Pilot" }}
              </span>
            </div>
            <button @click="handleLogout" class="bg-red-500/10 hover:bg-red-500 text-red-500 hover:text-white transition-colors p-2 rounded-md cursor-pointer flex items-center justify-center" title="Logout">
              <i class="fa-solid fa-right-from-bracket text-xs"></i>
            </button>
          </div>

          <button @click="generateApiKey" class="w-full bg-flight-accent/10 hover:bg-flight-accent text-flight-accent hover:text-white border border-flight-accent transition-colors p-2 rounded-lg text-xs font-bold uppercase tracking-wider cursor-pointer">Generate API Key</button>

          <div v-if="generatedApiKey" class="bg-black/50 p-3 rounded-lg border border-flight-border mt-2">
            <p class="text-[10px] text-red-400 font-bold uppercase mb-1">Vigyázz rá testvérem, el ne lopják a cigányok!</p>
            <code class="text-[10px] text-flight-accent break-all select-all">{{ generatedApiKey }}</code>
          </div>
        </div>
      </div>

      <div class="flex-grow overflow-y-auto px-4 pb-4 space-y-3">
        <div v-if="flights.length === 0" class="text-center py-20 text-slate-600 italic">
          <p class="text-sm">Searching for flight logs...</p>
        </div>

        <div v-for="flight in flights" :key="flight.id" @click="viewFlight(flight.id)" :class="['p-5 rounded-xl cursor-pointer transition-all duration-300 border group', selectedFlightId === flight.id ? 'bg-flight-card border-flight-accent shadow-[0_0_20px_rgba(56,189,248,0.1)]' : 'bg-transparent border-transparent hover:bg-flight-card-hover']">
          <div class="flex justify-between items-center mb-3">
            <span :class="['text-xl font-bold transition-colors', selectedFlightId === flight.id ? 'text-flight-accent' : 'text-white group-hover:text-flight-accent']">
              {{ flight.callsign }}
            </span>
            <span class="text-[10px] bg-flight-bg text-flight-accent border border-flight-accent/30 px-2 py-1 rounded font-mono">
              {{ flight.flight_number }}
            </span>
          </div>
          <div class="flex justify-between items-end text-xs text-slate-500">
            <div class="flex flex-col">
              <span class="text-slate-400 font-medium">{{ flight.airline }}</span>
              <span class="text-[10px]">{{ new Date(flight.start_time).toLocaleDateString() }}</span>
            </div>
            <i class="fa-solid fa-chevron-right text-slate-700 group-hover:text-flight-accent transition-colors"></i>
          </div>
        </div>
      </div>

      <div class="p-6 bg-black/40 border-t border-flight-border">
        <h4 class="text-[10px] font-bold text-slate-500 mb-4 uppercase tracking-widest flex items-center"><i class="fa-solid fa-layer-group mr-2 text-flight-accent"></i> Altitude MSL (FT)</h4>
        <div class="grid grid-cols-2 gap-x-4 gap-y-2">
          <div v-for="tier in altitudeTiers" :key="tier.alt" class="flex items-center space-x-3">
            <div class="w-2.5 h-2.5 rounded-sm" :style="{ backgroundColor: tier.color }"></div>
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
