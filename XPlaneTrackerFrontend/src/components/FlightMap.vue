<script setup>
import { ref, watch, onMounted, computed } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import api from "../config/api";

import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent, TitleComponent } from "echarts/components";
import VChart from "vue-echarts";

import { altToColor } from "../composables/useAltColor";
import { distanceM, toleranceForGS, rdpAdaptive, nearestPointOnPolyline } from "../composables/useGeo";
import { getAirportCoords } from "../composables/useAirports";
import { fetchAndDrawRunways, pendingRequests } from "../composables/useRunways";
import { fetchAndDrawAirportFeatures } from "../composables/useAirportFeatures";

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, TitleComponent]);

const props = defineProps({
  flightData: {
    type: Object,
    default: null,
  },
  flights: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["setSearchQuery"]);

// Helper for local storage
const getStorage = (key, defaultVal) => {
  try {
    const item = localStorage.getItem(key);
    return item !== null ? JSON.parse(item) : defaultVal;
  } catch {
    return defaultVal;
  }
};

const mapContainer = ref(null);
const isChartVisible = ref(false);
const showConnections = ref(false);
const chartRef = ref(null);

// Layers state synced with localStorage
const mapLayer = ref(getStorage("flightMap_layer", "dark"));
const showRunways = ref(getStorage("flightMap_showRunways", true));
const showTaxiways = ref(getStorage("flightMap_showTaxiways", true));
const showStands = ref(getStorage("flightMap_showStands", false));
const showGates = ref(getStorage("flightMap_showGates", false));

const isLayersMenuOpen = ref(false);

let map = null;
let pathLayers = [];
let connectionLayers = [];
let featureLayers = [];
let hoverMarker = null;
let tileLayerDark = null;
let tileLayerSatellite = null;

// Tracks which airport coords have had features drawn so we can redraw on toggle
const drawnFeatureCoords = [];

const chartData = computed(() => {
  if (!props.flightData?.path) return [];
  let totalDist = 0;
  const result = [];
  props.flightData.path.forEach((p, i) => {
    if (i > 0) {
      const prev = props.flightData.path[i - 1];
      totalDist += distanceM(prev[1], prev[2], p[1], p[2]);
    }
    result.push({ dist: (totalDist / 1852).toFixed(2), alt: p[3], gs: p[4] || 0, coord: [p[1], p[2]] });
  });
  return result;
});

const handleAxisPointer = (params) => {
  if (!params.axesInfo?.[0] || !map) return;
  const dataIndex = params.axesInfo[0].value;
  const point = chartData.value[dataIndex];
  if (!point) return;
  if (!hoverMarker) {
    const icon = L.divIcon({ className: "hover-marker-container", html: '<div class="hover-pulse"></div>', iconSize: [20, 20], iconAnchor: [10, 10] });
    hoverMarker = L.marker(point.coord, { zIndexOffset: 1000, icon }).addTo(map);
  } else {
    hoverMarker.setLatLng(point.coord);
  }
};

const clearHoverMarker = () => {
  if (hoverMarker && map) {
    map.removeLayer(hoverMarker);
    hoverMarker = null;
  }
};

const chartOptions = computed(() => ({
  backgroundColor: "transparent",
  tooltip: {
    trigger: "axis",
    backgroundColor: "#1e293b",
    borderColor: "#475569",
    textStyle: { color: "#fff", fontSize: 11, fontFamily: "monospace" },
    formatter: (params) => {
      const data = chartData.value[params[0].dataIndex];
      return `DIST: ${data.dist} NM<br/>ALT: ${data.alt} FT<br/>GS: ${data.gs} KTS`;
    },
  },
  grid: { left: "5%", right: "5%", bottom: "15%", top: "10%", containLabel: true },
  xAxis: {
    type: "category",
    data: chartData.value.map((d) => d.dist),
    axisLine: { lineStyle: { color: "#475569" } },
    axisLabel: { color: "#94a3b8", fontSize: 10 },
  },
  yAxis: {
    type: "value",
    splitLine: { lineStyle: { color: "#334155", type: "dashed" } },
    axisLabel: { color: "#94a3b8", fontSize: 10 },
  },
  series: [
    {
      data: chartData.value.map((d) => d.alt),
      type: "line",
      smooth: true,
      symbol: "none",
      lineStyle: { color: "#06b6d4", width: 2 },
      areaStyle: {
        color: {
          type: "linear",
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: "rgba(6, 182, 212, 0.4)" },
            { offset: 1, color: "rgba(6, 182, 212, 0)" },
          ],
        },
      },
    },
  ],
}));

const initMap = () => {
  map = L.map(mapContainer.value, { zoomControl: false }).setView([47.0, 19.0], 7);
  L.control.zoom({ position: "bottomright" }).addTo(map);
  map.createPane("runwaysPane").style.zIndex = 390;
  map.createPane("flightPathPane").style.zIndex = 410;
  map.createPane("connectionsPane").style.zIndex = 380;
  map.createPane("taxiwaysPane").style.zIndex = 385;
  map.createPane("standsPane").style.zIndex = 395;
  map.createPane("gatesPane").style.zIndex = 396;

  tileLayerDark = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { maxZoom: 20 });
  tileLayerSatellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { maxZoom: 20, attribution: "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community" });

  // Load initial map based on saved preference
  if (mapLayer.value === "satellite") {
    tileLayerSatellite.addTo(map);
  } else {
    tileLayerDark.addTo(map);
  }

  // Load initial runway visibility based on saved preference
  if (!showRunways.value) {
    map.getPane("runwaysPane").style.display = "none";
  }
};

const clearMap = () => {
  if (!map) return;
  const layers = pathLayers.splice(0);
  pendingRequests.clear();
  requestAnimationFrame(() => {
    layers.forEach((l) => map.removeLayer(l));
  });
};

const clearConnections = () => {
  if (!map) return;
  const layers = connectionLayers.splice(0);
  requestAnimationFrame(() => {
    layers.forEach((l) => map.removeLayer(l));
  });
};

const clearFeatures = () => {
  if (!map) return;
  const layers = featureLayers.splice(0);
  requestAnimationFrame(() => {
    layers.forEach((l) => map.removeLayer(l));
  });
};

const redrawFeatures = () => {
  clearFeatures();
  if (!map) return;
  const options = {
    taxiways: showTaxiways.value,
    stands: showStands.value,
    gates: showGates.value,
  };
  const anyOn = options.taxiways || options.stands || options.gates;
  if (!anyOn) return;
  drawnFeatureCoords.forEach(({ lat, lon }) => {
    fetchAndDrawAirportFeatures(lat, lon, map, featureLayers, options);
  });
};

const fetchFeaturesForLocation = (lat, lon) => {
  const options = {
    taxiways: showTaxiways.value,
    stands: showStands.value,
    gates: showGates.value,
  };
  const anyOn = options.taxiways || options.stands || options.gates;
  if (!anyOn) return;

  const alreadyTracked = drawnFeatureCoords.some((c) => c.lat === lat && c.lon === lon);
  if (!alreadyTracked) {
    drawnFeatureCoords.push({ lat, lon });
  }
  fetchAndDrawAirportFeatures(lat, lon, map, featureLayers, options);
};

const drawFlight = (data) => {
  clearMap();
  drawnFeatureCoords.splice(0);
  clearFeatures();
  if (!map || !data?.path) return;

  const rawPath = data.path;
  const coordsForRDP = rawPath.map((p) => [p[1], p[2]]);
  const tolerances = rawPath.map((p) => toleranceForGS(p[4] || 0));
  const simplifiedCoords = rdpAdaptive(coordsForRDP, tolerances);

  const coordKey = (lat, lon) => `${lat.toFixed(6)},${lon.toFixed(6)}`;
  const pointMap = new Map(rawPath.map((p) => [coordKey(p[1], p[2]), p]));
  const reducedPath = simplifiedCoords.map((coord) => pointMap.get(coordKey(coord[0], coord[1])) || [null, coord[0], coord[1], 0, 0]);

  const allPoints = reducedPath.map((p) => [p[1], p[2]]);
  const allAltitudes = reducedPath.map((p) => p[3] || 0);
  const allSpeeds = reducedPath.map((p) => p[4] || 0);

  const RGB_MERGE_DELTA = 6;

  const parseRgb = (rgbStr) => {
    const m = rgbStr.match(/rgb\((\d+),(\d+),(\d+)\)/);
    return m ? { r: +m[1], g: +m[2], b: +m[3] } : { r: 0, g: 0, b: 0 };
  };

  const rgbClose = (a, b) => Math.abs(a.r - b.r) <= RGB_MERGE_DELTA && Math.abs(a.g - b.g) <= RGB_MERGE_DELTA && Math.abs(a.b - b.b) <= RGB_MERGE_DELTA;

  const colorGroups = [];
  let curGroup = null;

  for (let i = 0; i < reducedPath.length - 1; i++) {
    const altMid = (allAltitudes[i] + allAltitudes[i + 1]) / 2;
    const color = altToColor(altMid);
    const rgb = parseRgb(color);

    if (!curGroup || !rgbClose(curGroup.rgb, rgb)) {
      if (curGroup) {
        curGroup.points.push(allPoints[i]);
        curGroup.altitudes.push(allAltitudes[i]);
        curGroup.speeds.push(allSpeeds[i]);
      }
      curGroup = { color, rgb, points: [allPoints[i]], altitudes: [allAltitudes[i]], speeds: [allSpeeds[i]] };
      colorGroups.push(curGroup);
    }
    curGroup.points.push(allPoints[i + 1]);
    curGroup.altitudes.push(allAltitudes[i + 1]);
    curGroup.speeds.push(allSpeeds[i + 1]);
  }

  const flightLayerGroup = L.layerGroup();

  colorGroups.forEach((group) => {
    if (group.points.length < 2) return;

    const poly = L.polyline(group.points, {
      color: group.color,
      weight: 4,
      opacity: 0.95,
      lineCap: "butt",
      lineJoin: "round",
      pane: "flightPathPane",
    });

    poly.on("mousemove", (e) => {
      const { idx } = nearestPointOnPolyline(e.latlng, group.points);
      poly.bindTooltip(`<div class="font-mono text-xs"><b>ALT:</b> ${group.altitudes[idx]} ft<br><b>GS:</b> ${group.speeds[idx] || "N/A"} KTS</div>`, { sticky: true, className: "flight-path-tooltip", permanent: false }).openTooltip(e.latlng);
    });
    poly.on("mouseout", () => poly.closeTooltip());

    flightLayerGroup.addLayer(poly);
    pathLayers.push(poly);
  });

  flightLayerGroup.addTo(map);

  if (data.path && data.path.length > 0) {
    const departurePoint = data.path[0];
    fetchAndDrawRunways(departurePoint[1], departurePoint[2], map, pathLayers);
    fetchFeaturesForLocation(departurePoint[1], departurePoint[2]);
  }

  if (data.landings?.length) {
    data.landings.forEach((landing) => {
      const icon = L.divIcon({
        html: `<div class="bg-flight-accent w-8 h-8 rounded-full flex items-center justify-center border-2 border-white shadow-lg shadow-cyan-500/50"><i class="fa-solid fa-plane-arrival text-white text-xs"></i></div>`,
        className: "custom-div-icon",
        iconSize: [32, 32],
        iconAnchor: [16, 32],
      });
      const marker = L.marker([landing.lat, landing.lon], { icon }).addTo(map);
      marker.bindPopup(
        `<div class="bg-flight-sidebar text-slate-300 p-4 rounded-lg border border-flight-border min-w-[160px] shadow-xl">
          <div class="flex items-center space-x-2 mb-3 border-b border-flight-border pb-2 pr-6"><i class="fa-solid fa-location-dot text-flight-accent"></i><h3 class="font-bold text-white text-sm uppercase tracking-wider">Touchdown</h3></div>
          <div class="space-y-2">
            <p class="text-[11px] flex justify-between gap-6"><span class="text-slate-500 font-medium">Vertical:</span><span class="font-mono text-flight-accent font-bold">${landing.fpm} FPM</span></p>
            <p class="text-[11px] flex justify-between gap-6"><span class="text-slate-500 font-medium">G-Force:</span><span class="font-mono text-flight-accent font-bold">${landing.g_force}G</span></p>
          </div>
        </div>`,
        { className: "flight-popup", maxWidth: 300 },
      );
      pathLayers.push(marker);
      fetchAndDrawRunways(landing.lat, landing.lon, map, pathLayers);
      fetchFeaturesForLocation(landing.lat, landing.lon);
    });
  }

  if (allPoints.length > 0) {
    map.fitBounds(L.latLngBounds(allPoints), { padding: [100, 100] });
  }
};

const computeConnections = (flightList) => {
  const pairMap = new Map();

  for (const flight of flightList) {
    const dep = flight.dep_icao;
    const arr = flight.arr_icao;

    if (!dep || !arr || dep === "NULL" || arr === "NULL") continue;

    const key = [dep.toUpperCase(), arr.toUpperCase()].sort().join("_");
    const depUpper = dep.toUpperCase();
    const arrUpper = arr.toUpperCase();

    if (!pairMap.has(key)) {
      pairMap.set(key, {
        icao1: [dep.toUpperCase(), arr.toUpperCase()].sort()[0],
        icao2: [dep.toUpperCase(), arr.toUpperCase()].sort()[1],
        depUpper,
        arrUpper,
        count: 1,
      });
    } else {
      pairMap.get(key).count++;
    }
  }

  return Array.from(pairMap.values());
};

const drawConnections = async () => {
  clearConnections();
  if (!map || !showConnections.value) return;

  const connections = computeConnections(props.flights);

  const airportDots = new Map();

  for (const conn of connections) {
    const coords1 = await getAirportCoords(conn.icao1);
    const coords2 = await getAirportCoords(conn.icao2);

    if (!coords1 || !coords2) continue;

    airportDots.set(conn.icao1, coords1);
    airportDots.set(conn.icao2, coords2);

    const label = `${conn.icao1} – ${conn.icao2} (${conn.count} járat)`;

    const visLine = L.polyline([coords1, coords2], {
      color: "#94a3b8",
      weight: 2,
      opacity: 0.5,
      dashArray: "6 4",
      interactive: false,
      pane: "connectionsPane",
    });

    const hitLine = L.polyline([coords1, coords2], {
      color: "#000",
      weight: 18,
      opacity: 0,
      pane: "connectionsPane",
    });

    hitLine.bindTooltip(label, {
      sticky: true,
      className: "connection-tooltip",
      permanent: false,
    });

    hitLine.on("mouseover", function () {
      visLine.setStyle({ color: "#e2e8f0", opacity: 0.9, weight: 3 });
    });

    hitLine.on("mouseout", function () {
      visLine.setStyle({ color: "#94a3b8", opacity: 0.5, weight: 2 });
    });

    hitLine.on("click", (e) => {
      L.DomEvent.stop(e);
      const el = hitLine.getElement?.();
      if (el) el.blur();
      const dep = conn.icao1.toLowerCase();
      const arr = conn.icao2.toLowerCase();
      const filterText = `dep:${dep} arr:${arr} dep:${arr} arr:${dep}`;
      emit("setSearchQuery", filterText);
    });

    visLine.addTo(map);
    hitLine.addTo(map);
    connectionLayers.push(visLine, hitLine);
  }

  for (const [icao, coords] of airportDots) {
    const ring = L.circleMarker(coords, {
      radius: 6,
      color: "#94a3b8",
      weight: 1.5,
      fillColor: "#1e293b",
      fillOpacity: 1,
      opacity: 0.6,
      interactive: false,
      pane: "connectionsPane",
    });

    const dot = L.circleMarker(coords, {
      radius: 3,
      color: "transparent",
      fillColor: "#94a3b8",
      fillOpacity: 0.8,
      interactive: false,
      pane: "connectionsPane",
    });

    ring.addTo(map);
    dot.addTo(map);
    connectionLayers.push(ring, dot);
  }
};

watch(
  () => props.flightData,
  (newData) => drawFlight(newData),
  { deep: true },
);

watch(showConnections, (val) => {
  if (val) {
    drawConnections();
  } else {
    clearConnections();
  }
});

watch(
  () => props.flights,
  () => {
    if (showConnections.value) {
      drawConnections();
    }
  },
  { deep: true },
);

// Watchers that save state to localStorage
watch(mapLayer, (val) => {
  localStorage.setItem("flightMap_layer", JSON.stringify(val));
  if (!map) return;
  if (val === "satellite") {
    map.removeLayer(tileLayerDark);
    tileLayerSatellite.addTo(map);
  } else {
    map.removeLayer(tileLayerSatellite);
    tileLayerDark.addTo(map);
  }
});

watch(showRunways, (val) => {
  localStorage.setItem("flightMap_showRunways", JSON.stringify(val));
  if (!map) return;
  map.getPane("runwaysPane").style.display = val ? "" : "none";
});

watch(showTaxiways, (val) => {
  localStorage.setItem("flightMap_showTaxiways", JSON.stringify(val));
  redrawFeatures();
});

watch(showStands, (val) => {
  localStorage.setItem("flightMap_showStands", JSON.stringify(val));
  redrawFeatures();
});

watch(showGates, (val) => {
  localStorage.setItem("flightMap_showGates", JSON.stringify(val));
  redrawFeatures();
});

onMounted(() => {
  initMap();
  if (props.flightData) drawFlight(props.flightData);
});
</script>

<template>
  <main class="flex-grow relative">
    <div ref="mapContainer" class="absolute inset-0 w-full h-full z-0"></div>

    <div class="absolute top-4 right-4 z-[1000] flex flex-col items-end">
      <button @click="isLayersMenuOpen = !isLayersMenuOpen" class="bg-slate-900/90 hover:bg-slate-800 text-white px-4 py-2.5 rounded-xl border border-slate-700 shadow-2xl flex items-center gap-2 transition-all">
        <i class="fa-solid fa-map text-cyan-400"></i>
        <span class="font-bold text-xs uppercase tracking-widest">Rétegek</span>
        <i class="fa-solid fa-chevron-down text-slate-400 text-[10px] transition-transform ml-1" :class="{ 'rotate-180': isLayersMenuOpen }"></i>
      </button>

      <div v-show="isLayersMenuOpen" class="mt-2 w-48 bg-slate-900/95 border border-slate-700 rounded-xl shadow-2xl backdrop-blur-md overflow-hidden">
        <div class="flex flex-col p-1 gap-0.5">
          <button @click="mapLayer = 'dark'" :class="['flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all', mapLayer === 'dark' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-transparent']">
            <i class="fa-solid fa-moon w-3.5 text-center"></i>
            <span>Sötét</span>
            <span v-if="mapLayer === 'dark'" class="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
          </button>
          <button @click="mapLayer = 'satellite'" :class="['flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all', mapLayer === 'satellite' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-transparent']">
            <i class="fa-solid fa-satellite w-3.5 text-center"></i>
            <span>Műhold</span>
            <span v-if="mapLayer === 'satellite'" class="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
          </button>

          <div class="my-0.5 border-t border-slate-700/60"></div>

          <button @click="showRunways = !showRunways" :class="['flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all', showRunways ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-transparent']">
            <i class="fa-solid fa-plane-departure w-3.5 text-center"></i>
            <span>Pályák</span>
            <span v-if="showRunways" class="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
          </button>

          <button @click="showTaxiways = !showTaxiways" :class="['flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all', showTaxiways ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-transparent']">
            <i class="fa-solid fa-road w-3.5 text-center"></i>
            <span>Gurulóutak</span>
            <span v-if="showTaxiways" class="ml-auto w-1.5 h-1.5 rounded-full bg-amber-400"></span>
          </button>

          <button @click="showStands = !showStands" :class="['flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all', showStands ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-transparent']">
            <i class="fa-solid fa-parking w-3.5 text-center"></i>
            <span>Állóhelyek</span>
            <span v-if="showStands" class="ml-auto w-1.5 h-1.5 rounded-full bg-amber-400"></span>
          </button>
        </div>
      </div>
    </div>

    <div class="absolute bottom-6 left-6 z-[1000] flex flex-col gap-2">
      <button @click="isChartVisible = !isChartVisible" class="bg-slate-900/90 hover:bg-slate-800 text-white px-5 py-2.5 rounded-full border border-slate-700 shadow-2xl flex items-center gap-2 transition-all group">
        <i class="fa-solid fa-chart-line text-cyan-400 group-hover:scale-110 transition-transform"></i>
        <span class="font-bold text-xs uppercase tracking-widest">Grafikon</span>
      </button>

      <button @click="showConnections = !showConnections" :class="['px-5 py-2.5 rounded-full border shadow-2xl flex items-center gap-2 transition-all group', showConnections ? 'bg-cyan-500/20 hover:bg-cyan-500/30 border-cyan-500/60 text-cyan-300' : 'bg-slate-900/90 hover:bg-slate-800 border-slate-700 text-white']">
        <i :class="['fa-solid fa-route transition-transform group-hover:scale-110', showConnections ? 'text-cyan-400' : 'text-slate-400']"></i>
        <span class="font-bold text-xs uppercase tracking-widest">Kapcsolatok</span>
        <span v-if="showConnections" class="ml-1 w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_6px_#22d3ee] animate-pulse"></span>
      </button>
    </div>

    <div v-if="isChartVisible" class="absolute bottom-30 left-6 z-[1000] w-[90vw] max-w-2xl h-64 bg-slate-900/95 border border-slate-700 rounded-xl shadow-2xl backdrop-blur-md p-4">
      <div class="flex justify-between items-center mb-2 px-2">
        <h4 class="text-white text-[10px] font-black uppercase tracking-tighter opacity-50">Flight Profile</h4>
        <button @click="isChartVisible = false" class="text-slate-400 hover:text-white transition-colors"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <div class="w-full h-48">
        <v-chart ref="chartRef" class="chart" :option="chartOptions" autoresize @updateAxisPointer="handleAxisPointer" @globalout="clearHoverMarker" />
      </div>
    </div>
  </main>
</template>

<style>
.hover-pulse {
  width: 16px;
  height: 16px;
  background: #06b6d4;
  border: 3px solid white;
  border-radius: 50%;
  box-shadow: 0 0 15px rgba(6, 182, 212, 0.8);
  animation: marker-pulse 1.5s infinite;
}
@keyframes marker-pulse {
  0% {
    transform: scale(0.9);
    box-shadow: 0 0 0 0 rgba(6, 182, 212, 0.7);
  }
  70% {
    transform: scale(1.1);
    box-shadow: 0 0 0 10px rgba(6, 182, 212, 0);
  }
  100% {
    transform: scale(0.9);
    box-shadow: 0 0 0 0 rgba(6, 182, 212, 0);
  }
}
#map {
  width: 100%;
  height: 100%;
}
.rwy-designator {
  color: #ffffff;
  font-family: "Arial Narrow", Arial, sans-serif;
  font-size: 13px;
  font-weight: 900;
  text-align: center;
  text-shadow: 0 0 4px #000;
}
.flight-path-tooltip {
  background: #1e293b;
  color: white;
  border: 1px solid #475569;
  border-radius: 4px;
}
.connection-tooltip {
  background: #0f172a;
  color: #e2e8f0;
  border: 1px solid #334155;
  border-radius: 6px;
  font-size: 11px;
  font-family: monospace;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 4px 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
}
.taxiway-tooltip {
  background: #1c1400;
  color: #fcd34d;
  border: 1px solid #92400e;
  border-radius: 4px;
  font-size: 11px;
  font-family: monospace;
  font-weight: 700;
  padding: 2px 8px;
}
.taxiway-label-marker {
  color: #c58d00;
  font-family: "Arial Narrow", Arial, sans-serif;
  font-size: 11px;
  font-weight: 900;
  text-shadow:
    0 0 3px #000,
    0 0 6px #000;
  white-space: nowrap;
  pointer-events: none;
  transform: translate(-50%, -50%);
}
.stand-marker {
  color: #fdba74;
  font-family: "Arial Narrow", Arial, sans-serif;
  font-size: 9px;
  font-weight: 900;
  text-shadow:
    0 0 3px #000,
    0 0 5px #000;
  white-space: nowrap;
  pointer-events: none;
  transform: translate(-50%, -50%);
}
.stand-tooltip {
  background: #1c0a00;
  color: #fed7aa;
  border: 1px solid #9a3412;
  border-radius: 4px;
  font-size: 11px;
  font-family: monospace;
  padding: 3px 8px;
}
.gate-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  transform: translate(-50%, -50%);
  pointer-events: none;
}
.gate-marker i {
  color: #86efac;
  font-size: 10px;
  text-shadow: 0 0 4px #000;
}
.gate-marker span {
  color: #86efac;
  font-family: "Arial Narrow", Arial, sans-serif;
  font-size: 9px;
  font-weight: 900;
  text-shadow:
    0 0 3px #000,
    0 0 5px #000;
  white-space: nowrap;
}
.gate-tooltip {
  background: #001a08;
  color: #bbf7d0;
  border: 1px solid #166534;
  border-radius: 4px;
  font-size: 11px;
  font-family: monospace;
  padding: 3px 8px;
}
.chart {
  height: 100%;
  width: 100%;
}
.leaflet-interactive:focus {
  outline: none;
}
</style>
