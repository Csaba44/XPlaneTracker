<script setup>
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import api from "../config/api";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const route = useRoute();
const map = ref(null);
const flightData = ref(null);
const isLoading = ref(true);
const isError = ref(false);

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

const loadSharedFlight = async () => {
  try {
    const id = route.params.id;
    const response = await api.get(`/api/flights/${id}`);
    const data = response.data;
    flightData.value = data.metadata;

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
    });

    if (segments.length > 0) {
      const group = new L.featureGroup(segments);
      map.value.fitBounds(group.getBounds(), { padding: [100, 100] });
    }
  } catch (error) {
    console.error(error);
    isError.value = true;
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  initMap();
  loadSharedFlight();
});
</script>

<template>
  <div class="flex h-screen w-screen bg-flight-bg text-slate-300 overflow-hidden font-sans">
    <div v-if="isLoading" class="absolute inset-0 z-[2000] bg-flight-bg flex flex-col items-center justify-center">
      <i class="fa-solid fa-spinner fa-spin text-4xl text-flight-accent mb-4"></i>
      <p class="text-slate-400 uppercase tracking-widest font-bold text-sm">Loading Flight Data...</p>
    </div>

    <div v-if="isError" class="absolute inset-0 z-[2000] bg-flight-bg flex flex-col items-center justify-center">
      <i class="fa-solid fa-triangle-exclamation text-5xl text-red-500 mb-4"></i>
      <p class="text-white font-bold text-xl mb-2">Flight Not Found</p>
      <p class="text-slate-500 mb-6 text-sm">This flight log might have been deleted or doesn't exist.</p>
      <router-link to="/" class="bg-flight-accent hover:bg-sky-400 text-flight-bg font-black px-6 py-3 rounded-xl transition-all uppercase tracking-widest text-xs"> Go Home </router-link>
    </div>

    <aside class="w-85 flex flex-col bg-flight-sidebar border-r border-flight-border z-[1000] shadow-2xl">
      <div class="p-8 pb-6 border-b border-flight-border">
        <div class="flex items-center space-x-3 mb-6">
          <div class="w-2 h-8 bg-flight-accent rounded-full shadow-[0_0_10px_#38bdf8]"></div>
          <div>
            <h1 class="text-2xl font-black text-white tracking-tighter italic leading-none">X-TRACKER</h1>
            <p class="text-[10px] text-flight-accent uppercase font-bold tracking-widest mt-1">Shared Flight</p>
          </div>
        </div>
      </div>

      <div class="flex-grow p-6">
        <div v-if="flightData" class="space-y-6">
          <div>
            <p class="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">Callsign</p>
            <p class="text-2xl font-black text-white">{{ flightData.callsign }}</p>
          </div>
          <div>
            <p class="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">Flight Number</p>
            <p class="text-lg font-mono text-flight-accent">{{ flightData.flight_number }}</p>
          </div>
          <div>
            <p class="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">Airline</p>
            <p class="text-md text-slate-300">{{ flightData.airline }}</p>
          </div>
          <div>
            <p class="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-1">Date Recorded</p>
            <p class="text-sm text-slate-400">{{ new Date(flightData.start_time).toLocaleString() }}</p>
          </div>
        </div>
      </div>

      <div class="p-6 bg-black/40 border-t border-flight-border flex flex-col space-y-6">
        <div>
          <h4 class="text-[10px] font-bold text-slate-500 mb-4 uppercase tracking-widest flex items-center"><i class="fa-solid fa-layer-group mr-2 text-flight-accent"></i> Altitude MSL (FT)</h4>
          <div class="grid grid-cols-2 gap-x-4 gap-y-2">
            <div v-for="tier in altitudeTiers" :key="tier.alt" class="flex items-center space-x-3">
              <div class="w-2.5 h-2.5 rounded-sm" :style="{ backgroundColor: tier.color }"></div>
              <span class="text-[11px] text-slate-400 font-medium">{{ tier.label }}</span>
            </div>
          </div>
        </div>

        <router-link to="/" class="w-full text-center bg-flight-card hover:bg-flight-accent border border-flight-border hover:border-flight-accent text-slate-300 hover:text-white transition-all p-3 rounded-xl text-xs font-bold uppercase tracking-wider block"> Get Your Own Tracker </router-link>
      </div>
    </aside>

    <main class="flex-grow relative">
      <div id="map"></div>
    </main>
  </div>
</template>
