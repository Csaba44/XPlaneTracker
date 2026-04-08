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

// Cache so the same airport isn't fetched twice (keyed by rounded lat/lon)
const runwayCache = new Map();

// Overpass mirror list — tried in order, first success wins
const OVERPASS_MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://overpass.private.coffee/api/interpreter"];

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

/**
 * Bearing (degrees, 0=N clockwise) from A → B.
 */
const bearing = (lat1, lon1, lat2, lon2) => {
  const toRad = (d) => (d * Math.PI) / 180;
  const φ1 = toRad(lat1),
    φ2 = toRad(lat2);
  const Δλ = toRad(lon2 - lon1);
  const y = Math.sin(Δλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
};

/**
 * Point that is `distM` metres from [lat,lon] on bearing `brg`.
 */
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

/**
 * Haversine distance in metres between two points.
 */
const distanceM = (lat1, lon1, lat2, lon2) => {
  const R = 6378137;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
};

/**
 * Shift every point in a [lat,lon][] array by `offsetM` metres perpendicular
 * to the local track direction. Positive = right, negative = left.
 */
const offsetPolyline = (points, offsetM) => {
  return points.map((pt, i) => {
    const prev = points[Math.max(0, i - 1)];
    const next = points[Math.min(points.length - 1, i + 1)];
    const brg = bearing(prev[0], prev[1], next[0], next[1]);
    return destination(pt[0], pt[1], (brg + 90) % 360, offsetM);
  });
};

// ---------------------------------------------------------------------------
// Runway drawing
// ---------------------------------------------------------------------------

/**
 * Convert a runway designator like "31L", "04R", "09" to its magnetic
 * heading in degrees (the direction the aircraft faces when landing on it).
 * Designator number × 10 gives the heading; we ignore L/R/C for this.
 */
const designatorToHeading = (des) => {
  if (!des) return null;
  const num = parseInt(des.replace(/[^0-9]/g, ""), 10);
  if (isNaN(num)) return null;
  return (num * 10) % 360;
};

/**
 * Angular difference between two bearings (0–180).
 */
const angleDiff = (a, b) => {
  const d = Math.abs((a - b + 360) % 360);
  return d > 180 ? 360 - d : d;
};

const drawRunway = (el) => {
  if (el.type !== "way" || !el.geometry || el.geometry.length < 2) return;

  // cl[0] may be either threshold — we'll sort it out below
  let cl = el.geometry.map((g) => [g.lat, g.lon]);
  const widthM = el.tags?.width ? parseFloat(el.tags.width) : 45;
  const half = widthM / 2;

  // --- Determine correct geometry direction from designator numbers ---
  // OSM ref = "leDesignator/heDesignator", e.g. "04R/22L"
  // leDesignator is the LOW-end (smaller number, e.g. 04).
  // We want cl[0] to be the low-end threshold.
  // Strategy: the bearing FROM cl[0] TO cl[1] should be close to leDesignator × 10.
  if (el.tags?.ref) {
    const [leRef] = el.tags.ref.split("/");
    const leHeading = designatorToHeading(leRef);
    if (leHeading !== null) {
      const actualBearing = bearing(cl[0][0], cl[0][1], cl[cl.length - 1][0], cl[cl.length - 1][1]);
      // If the geometry runs the wrong way, reverse it
      if (angleDiff(actualBearing, leHeading) > 90) {
        cl = [...cl].reverse();
      }
    }
  }

  // Now cl[0] = low-end threshold (leRef side), cl[last] = high-end (heRef side)
  const leInward = bearing(cl[0][0], cl[0][1], cl[1][0], cl[1][1]);
  const heInward = bearing(cl[cl.length - 1][0], cl[cl.length - 1][1], cl[cl.length - 2][0], cl[cl.length - 2][1]);

  // ── 1. Asphalt base ──────────────────────────────────────────────────────
  const right = offsetPolyline(cl, half);
  const left = offsetPolyline(cl, -half);
  pathLayers.push(
    L.polygon([...right, ...[...left].reverse()], {
      color: "transparent",
      fillColor: "#111111",
      fillOpacity: 1,
      interactive: false,
    }).addTo(map),
  );

  // ── 2. Solid white edge lines ────────────────────────────────────────────
  [right, left].forEach((edge) => {
    pathLayers.push(L.polyline(edge, { color: "#ffffff", weight: 2, opacity: 0.9, interactive: false }).addTo(map));
  });

  // ── 3. Dashed white centreline ───────────────────────────────────────────
  pathLayers.push(
    L.polyline(cl, {
      color: "#ffffff",
      weight: 1.5,
      opacity: 0.65,
      dashArray: "20 15",
      interactive: false,
    }).addTo(map),
  );

  // ── 4. Threshold piano keys ───────────────────────────────────────────────
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
        }).addTo(map),
      );
    }
  };

  drawPianoKeys(cl[0], leInward);
  drawPianoKeys(cl[cl.length - 1], heInward);

  // ── 5. Touchdown zone bars ────────────────────────────────────────────────
  // ICAO standard: twin rectangular bars parallel to the centreline,
  // offset left and right. Starting 150 m from threshold, every 150 m, up to 900 m.
  const runwayLen = distanceM(cl[0][0], cl[0][1], cl[cl.length - 1][0], cl[cl.length - 1][1]);
  const tzDistances = [150, 300, 450, 600, 750, 900].filter((d) => d < runwayLen - 150);

  // Bar dimensions (ICAO Annex 14):
  // 22.5 m long (along runway), 3 m wide, centred ~8 m either side of CL
  const barLenM = 22.5;
  const barWidthM = 3;
  const barLateralM = widthM * 0.2; // lateral centre offset from CL

  const drawTDZBars = (thresholdPt, inwardBrg) => {
    const perpBrg = (inwardBrg + 90) % 360;

    tzDistances.forEach((dist) => {
      const along = destination(thresholdPt[0], thresholdPt[1], inwardBrg, dist);

      [-barLateralM, barLateralM].forEach((latOff) => {
        // Centre of this individual bar
        const bc = destination(along[0], along[1], perpBrg, latOff);

        // Corners: half-length along inwardBrg, half-width along perpBrg
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
          }).addTo(map),
        );
      });
    });
  };

  drawTDZBars(cl[0], leInward);
  drawTDZBars(cl[cl.length - 1], heInward);

  // ── 6. Designator labels ─────────────────────────────────────────────────
  // OSM ref = "leDesignator/heDesignator" e.g. "04R/22L"
  // leRef → placed at cl[0]        facing leInward
  // heRef → placed at cl[last]     facing heInward
  if (el.tags?.ref) {
    const [leRef, heRef] = el.tags.ref.split("/");

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
// Overpass fetch with mirror fallback + caching
// ---------------------------------------------------------------------------

const cacheKey = (lat, lon) => `${Math.round(lat * 100) / 100},${Math.round(lon * 100) / 100}`;

const fetchOverpass = async (query) => {
  for (const mirror of OVERPASS_MIRRORS) {
    try {
      const res = await fetch(`${mirror}?data=${encodeURIComponent(query)}`, {
        signal: AbortSignal.timeout(12000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn(`Overpass mirror failed (${mirror}):`, err.message);
    }
  }
  throw new Error("All Overpass mirrors failed");
};

const fetchAndDrawRunways = async (lat, lon) => {
  const key = cacheKey(lat, lon);

  if (runwayCache.has(key)) {
    runwayCache.get(key).forEach(drawRunway);
    return;
  }

  const query = `[out:json];way["aeroway"="runway"](around:4000,${lat},${lon});out geom tags;`;

  try {
    const data = await fetchOverpass(query);
    if (!data.elements?.length) return;
    runwayCache.set(key, data.elements);
    data.elements.forEach(drawRunway);
  } catch (err) {
    console.error("Could not load runway data:", err.message);
  }
};

// ---------------------------------------------------------------------------
// Map init
// ---------------------------------------------------------------------------

const initMap = () => {
  map = L.map(mapContainer.value, { zoomControl: false }).setView([47.0, 19.0], 7);
  L.control.zoom({ position: "bottomright" }).addTo(map);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    subdomains: "abcd",
    maxZoom: 20,
  }).addTo(map);
};

// ---------------------------------------------------------------------------
// Flight path + landings
// ---------------------------------------------------------------------------

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
      { color: getColor(point[3]), weight: 4, opacity: 0.9, lineCap: "round" },
    ).addTo(map);
    pathLayers.push(poly);
    segments.push(poly);
  });

  if (data.landings?.length) {
    const fetched = new Set();

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

      const key = cacheKey(landing.lat, landing.lon);
      if (!fetched.has(key)) {
        fetched.add(key);
        fetchAndDrawRunways(landing.lat, landing.lon);
      }
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
