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

// ---------------------------------------------------------------------------
// Cache & Network State
// ---------------------------------------------------------------------------
// Stores the actual runway data elements so they survive flight switching
const runwayCache = new Map();
// Prevents duplicate parallel API calls if a pilot lands twice at the same airport
const pendingRequests = new Set();

const localCacheKey = (lat, lon) => `${Math.round(lat * 100) / 100},${Math.round(lon * 100) / 100}`;

// ---------------------------------------------------------------------------
// Colour helper
// ---------------------------------------------------------------------------
const getColor = (alt) => {
  if (alt < 1000) return "#ef4444";
  if (alt < 5000) return "#f97316";
  if (alt < 15000) return "#eab308";
  if (alt < 25000) return "#22c55e";
  if (alt < 35000) return "#06b6d4";
  return "#3b82f6";
};

// ---------------------------------------------------------------------------
// Spherical geometry helpers
// ---------------------------------------------------------------------------
const bearing = (lat1, lon1, lat2, lon2) => {
  const toRad = (d) => (d * Math.PI) / 180;
  const φ1 = toRad(lat1),
    φ2 = toRad(lat2);
  const Δλ = toRad(lon2 - lon1);
  const y = Math.sin(Δλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
};

const destination = (lat, lon, brg, distM) => {
  const R = 6378137;
  const δ = distM / R;
  const θ = (brg * Math.PI) / 180;
  const φ1 = (lat * Math.PI) / 180;
  const λ1 = (lon * Math.PI) / 180;
  const φ2 = Math.asin(Math.sin(φ1) * Math.cos(δ) + Math.cos(φ1) * Math.sin(δ) * Math.cos(θ));
  const λ2 = λ1 + Math.atan2(Math.sin(θ) * Math.sin(δ) * Math.cos(φ1), Math.cos(δ) - Math.sin(φ1) * Math.sin(φ2));
  return [(φ2 * 180) / Math.PI, (((λ2 * 180) / Math.PI + 540) % 360) - 180];
};

const distanceM = (lat1, lon1, lat2, lon2) => {
  const R = 6378137;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
};

const offsetPolyline = (points, offsetM) => {
  return points.map((pt, i) => {
    const prev = points[Math.max(0, i - 1)];
    const next = points[Math.min(points.length - 1, i + 1)];
    const brg = bearing(prev[0], prev[1], next[0], next[1]);
    return destination(pt[0], pt[1], (brg + 90) % 360, offsetM);
  });
};

const designatorToHeading = (des) => {
  if (!des) return null;
  const num = parseInt(des.replace(/[^0-9]/g, ""), 10);
  if (isNaN(num)) return null;
  return (num * 10) % 360;
};

const angleDiff = (a, b) => {
  const d = Math.abs((a - b + 360) % 360);
  return d > 180 ? 360 - d : d;
};

// ---------------------------------------------------------------------------
// Runway Drawing Logic
// ---------------------------------------------------------------------------
const drawRunway = (el) => {
  if (el.type !== "way" || !el.geometry || el.geometry.length < 2) return;

  let cl = el.geometry.map((g) => [g.lat, g.lon]);
  const widthM = el.tags?.width ? parseFloat(el.tags.width) : 45;
  const half = widthM / 2;

  if (el.tags?.ref) {
    const [leRef] = el.tags.ref.split("/");
    const leHeading = designatorToHeading(leRef);
    if (leHeading !== null) {
      const actualBearing = bearing(cl[0][0], cl[0][1], cl[cl.length - 1][0], cl[cl.length - 1][1]);
      if (angleDiff(actualBearing, leHeading) > 90) {
        cl = [...cl].reverse();
      }
    }
  }

  const leInward = bearing(cl[0][0], cl[0][1], cl[1][0], cl[1][1]);
  const heInward = bearing(cl[cl.length - 1][0], cl[cl.length - 1][1], cl[cl.length - 2][0], cl[cl.length - 2][1]);

  const right = offsetPolyline(cl, half);
  const left = offsetPolyline(cl, -half);

  // Asphalt
  pathLayers.push(
    L.polygon([...right, ...[...left].reverse()], {
      color: "transparent",
      fillColor: "#111111",
      fillOpacity: 1,
      interactive: false,
      pane: "runwaysPane",
    }).addTo(map),
  );

  // Edges
  [right, left].forEach((edge) => {
    pathLayers.push(
      L.polyline(edge, {
        color: "#ffffff",
        weight: 2,
        opacity: 0.9,
        interactive: false,
        pane: "runwaysPane",
      }).addTo(map),
    );
  });

  // Centerline
  pathLayers.push(
    L.polyline(cl, {
      color: "#ffffff",
      weight: 1.5,
      opacity: 0.65,
      dashArray: "20 15",
      interactive: false,
      pane: "runwaysPane",
    }).addTo(map),
  );

  // Piano Keys
  const drawPianoKeys = (thresholdPt, inwardBrg) => {
    const perpBrg = (inwardBrg + 90) % 360;
    const numStripes = 8;
    const spanM = widthM * 0.8;
    const gap = spanM / (numStripes - 1);
    const stripeHalfW = (spanM / (numStripes * 2 - 1)) * 0.45;
    const depthM = 30;
    const inboardM = 6;

    for (let i = 0; i < numStripes; i++) {
      const lateralOffset = -spanM / 2 + gap * i;
      const center = destination(thresholdPt[0], thresholdPt[1], perpBrg, lateralOffset);
      const near = destination(center[0], center[1], inwardBrg, inboardM);
      const far = destination(near[0], near[1], inwardBrg, depthM);

      const p1 = destination(near[0], near[1], perpBrg, stripeHalfW);
      const p2 = destination(far[0], far[1], perpBrg, stripeHalfW);
      const p3 = destination(far[0], far[1], (perpBrg + 180) % 360, stripeHalfW);
      const p4 = destination(near[0], near[1], (perpBrg + 180) % 360, stripeHalfW);

      pathLayers.push(
        L.polygon([p1, p2, p3, p4], {
          color: "transparent",
          fillColor: "#ffffff",
          fillOpacity: 0.85,
          interactive: false,
          pane: "runwaysPane",
        }).addTo(map),
      );
    }
  };

  drawPianoKeys(cl[0], leInward);
  drawPianoKeys(cl[cl.length - 1], heInward);

  // TDZ Bars
  const runwayLen = distanceM(cl[0][0], cl[0][1], cl[cl.length - 1][0], cl[cl.length - 1][1]);
  const tzDistances = [150, 300, 450, 600, 750, 900].filter((d) => d < runwayLen - 150);
  const barLenM = 22.5;
  const barWidthM = 3;
  const barLateralM = widthM * 0.2;

  const drawTDZBars = (thresholdPt, inwardBrg) => {
    const perpBrg = (inwardBrg + 90) % 360;

    tzDistances.forEach((dist) => {
      const along = destination(thresholdPt[0], thresholdPt[1], inwardBrg, dist);

      [-barLateralM, barLateralM].forEach((latOff) => {
        const bc = destination(along[0], along[1], perpBrg, latOff);
        const fwd = destination(bc[0], bc[1], inwardBrg, barLenM / 2);
        const aft = destination(bc[0], bc[1], (inwardBrg + 180) % 360, barLenM / 2);

        const p1 = destination(fwd[0], fwd[1], perpBrg, barWidthM / 2);
        const p2 = destination(aft[0], aft[1], perpBrg, barWidthM / 2);
        const p3 = destination(aft[0], aft[1], (perpBrg + 180) % 360, barWidthM / 2);
        const p4 = destination(fwd[0], fwd[1], (perpBrg + 180) % 360, barWidthM / 2);

        pathLayers.push(
          L.polygon([p1, p2, p3, p4], {
            color: "transparent",
            fillColor: "#ffffff",
            fillOpacity: 0.75,
            interactive: false,
            pane: "runwaysPane",
          }).addTo(map),
        );
      });
    });
  };

  drawTDZBars(cl[0], leInward);
  drawTDZBars(cl[cl.length - 1], heInward);

  // Labels
  if (el.tags?.ref) {
    let parts = el.tags.ref.split("/");
    let leRef = parts[0];
    let heRef = parts[1];

    if (leRef && heRef) {
      const hdg1 = parseInt(leRef, 10) * 10;
      if (angleDiff(hdg1, leInward) > angleDiff(hdg1, heInward)) {
        [leRef, heRef] = [heRef, leRef];
      }
    }

    const addLabel = (thresholdPt, inwardBrg, label) => {
      if (!label) return;
      const pos = destination(thresholdPt[0], thresholdPt[1], inwardBrg, 55);
      const icon = L.divIcon({
        html: `<div class="rwy-designator" style="transform:rotate(${inwardBrg}deg)">${label}</div>`,
        className: "",
        iconSize: [40, 20],
        iconAnchor: [20, 10],
      });
      pathLayers.push(L.marker(pos, { icon, interactive: false }).addTo(map));
    };

    addLabel(cl[0], leInward, leRef);
    addLabel(cl[cl.length - 1], heInward, heRef);
  }
};

// ---------------------------------------------------------------------------
// Backend Proxy Fetching & Local Memory
// ---------------------------------------------------------------------------
const fetchAndDrawRunways = async (lat, lon) => {
  const key = localCacheKey(lat, lon);

  // 1. If we already downloaded this airport, just re-draw it from memory!
  if (runwayCache.has(key)) {
    runwayCache.get(key).forEach(drawRunway);
    return;
  }

  // 2. If a network request is currently running for this airport, don't start a second one
  if (pendingRequests.has(key)) return;
  pendingRequests.add(key);

  const url = `/api/runways?lat=${lat}&lon=${lon}`;

  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}`);

    const data = await response.json();

    if (data.elements && data.elements.length > 0) {
      // 3. Save the data to local memory so it survives flight-switching
      runwayCache.set(key, data.elements);

      // 4. Draw it on the map
      data.elements.forEach(drawRunway);
    }
  } catch (err) {
    console.error("Could not load runway data from backend proxy:", err.message);
  } finally {
    // Clear the pending lock so it can be retried later if it failed
    pendingRequests.delete(key);
  }
};

// ---------------------------------------------------------------------------
// Map Init & Core Render
// ---------------------------------------------------------------------------
const initMap = () => {
  map = L.map(mapContainer.value, { zoomControl: false }).setView([47.0, 19.0], 7);
  L.control.zoom({ position: "bottomright" }).addTo(map);

  map.createPane("runwaysPane");
  map.getPane("runwaysPane").style.zIndex = 390;

  map.createPane("flightPathPane");
  map.getPane("flightPathPane").style.zIndex = 410;

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    subdomains: "abcd",
    maxZoom: 20,
  }).addTo(map);
};

const clearMap = () => {
  if (!map) return;
  pathLayers.forEach((l) => map.removeLayer(l));
  pathLayers = [];
};

const drawFlight = (data) => {
  clearMap();
  if (!map || !data?.path) return;

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
        pane: "flightPathPane",
      },
    ).addTo(map);
    pathLayers.push(poly);
    segments.push(poly);
  });

  if (data.landings?.length) {
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
        `<div class="bg-flight-sidebar text-slate-300 p-4 rounded-lg border border-flight-border min-w-[160px] shadow-xl">
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
        </div>`,
        { className: "flight-popup", maxWidth: 300 },
      );
      pathLayers.push(marker);

      // Trigger the backend API call for this landing
      fetchAndDrawRunways(landing.lat, landing.lon);
    });
  }

  if (segments.length > 0) {
    const group = new L.featureGroup(segments);
    map.fitBounds(group.getBounds(), { padding: [100, 100] });
  }
};

watch(
  () => props.flightData,
  (newData) => drawFlight(newData),
  { deep: true },
);

onMounted(() => {
  initMap();
  if (props.flightData) drawFlight(props.flightData);
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

.rwy-designator {
  color: #ffffff;
  font-family: "Arial Narrow", Arial, sans-serif;
  font-size: 13px;
  font-weight: 900;
  text-align: center;
  letter-spacing: 0.05em;
  text-shadow:
    0 0 4px rgba(0, 0, 0, 0.9),
    0 0 8px rgba(0, 0, 0, 0.7);
  white-space: nowrap;
  transform-origin: center center;
  user-select: none;
}
</style>
