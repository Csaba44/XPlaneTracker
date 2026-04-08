<script setup>
import { ref, watch, onMounted } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const props = defineProps({
  flightData: {
    type: Object,
    default: null,
  },
});

const mapContainer = ref(null);
let map = null;
let pathLayers = [];

const getColor = (alt) => {
  if (alt < 1000) return "#ef4444";
  if (alt < 5000) return "#f97316";
  if (alt < 15000) return "#eab308";
  if (alt < 25000) return "#22c55e";
  if (alt < 35000) return "#06b6d4";
  return "#3b82f6";
};

const initMap = () => {
  map = L.map(mapContainer.value, { zoomControl: false }).setView([47.0, 19.0], 7);
  L.control.zoom({ position: "bottomright" }).addTo(map);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    subdomains: "abcd",
    maxZoom: 20,
  }).addTo(map);
};

const clearMap = () => {
  if (!map) return;
  pathLayers.forEach((layer) => map.removeLayer(layer));
  pathLayers = [];
};

const drawFlight = (data) => {
  clearMap();
  if (!map || !data || !data.path) return;

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
    ).addTo(map);
    pathLayers.push(poly);
    segments.push(poly);
  });

  if (data.landings) {
    data.landings.forEach((landing) => {
      const icon = L.divIcon({
        html: `<div class="bg-flight-accent w-8 h-8 rounded-full flex items-center justify-center border-2 border-white shadow-lg shadow-cyan-500/50">
                <i class="fa-solid fa-plane-arrival text-white text-xs"></i>
               </div>`,
        className: "custom-div-icon",
        iconSize: [32, 32],
        iconAnchor: [16, 32],
      });

      const marker = L.marker([landing.lat, landing.lon], { icon }).addTo(map);

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
      pathLayers.push(marker);
    });
  }

  if (segments.length > 0) {
    const group = new L.featureGroup(segments);
    map.fitBounds(group.getBounds(), { padding: [100, 100] });
  }
};

watch(
  () => props.flightData,
  (newData) => {
    drawFlight(newData);
  },
  { deep: true },
);

onMounted(() => {
  initMap();
  if (props.flightData) {
    drawFlight(props.flightData);
  }
});
</script>

<template>
  <main class="flex-grow relative">
    <div ref="mapContainer" class="absolute inset-0 w-full h-full z-0"></div>
  </main>
</template>

<style>
#map {
  width: 100%;
  height: 100%;
}
</style>
