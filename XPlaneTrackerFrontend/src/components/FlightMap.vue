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
// Helpers
// ---------------------------------------------------------------------------

const getColor = (alt) => {
  if (alt < 1000) return "#ef4444";
  if (alt < 5000) return "#f97316";
  if (alt < 15000) return "#eab308";
  if (alt < 25000) return "#22c55e";
  if (alt < 35000) return "#06b6d4";
  return "#3b82f6";
};

/**
 * Returns a new [lat, lon] that is `distanceM` metres away from [lat, lon]
 * in the direction of `bearingDeg` (0 = north, clockwise).
 */
const destinationPoint = (lat, lon, bearingDeg, distanceM) => {
  const R = 6378137; // Earth radius in metres
  const δ = distanceM / R;
  const θ = (bearingDeg * Math.PI) / 180;
  const φ1 = (lat * Math.PI) / 180;
  const λ1 = (lon * Math.PI) / 180;

  const φ2 = Math.asin(Math.sin(φ1) * Math.cos(δ) + Math.cos(φ1) * Math.sin(δ) * Math.cos(θ));
  const λ2 = λ1 + Math.atan2(Math.sin(θ) * Math.sin(δ) * Math.cos(φ1), Math.cos(δ) - Math.sin(φ1) * Math.sin(φ2));

  return [(φ2 * 180) / Math.PI, (((λ2 * 180) / Math.PI + 540) % 360) - 180];
};

/**
 * Bearing in degrees from point A to point B.
 */
const bearing = (lat1, lon1, lat2, lon2) => {
  const φ1 = (lat1 * Math.PI) / 180;
  const φ2 = (lat2 * Math.PI) / 180;
  const Δλ = ((lon2 - lon1) * Math.PI) / 180;
  const y = Math.sin(Δλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
};

/**
 * Offset an array of [lat,lon] points perpendicular to their track by
 * `offsetM` metres (positive = right, negative = left).
 */
const offsetPolyline = (points, offsetM) => {
  return points.map((pt, i) => {
    // Use the segment before or after to get a local bearing
    const prev = points[Math.max(0, i - 1)];
    const next = points[Math.min(points.length - 1, i + 1)];
    const brg = bearing(prev[0], prev[1], next[0], next[1]);
    const perpBearing = (brg + 90) % 360;
    return destinationPoint(pt[0], pt[1], perpBearing, offsetM);
  });
};

/**
 * Distance in metres between two [lat,lon] points (Haversine).
 */
const distanceM = (lat1, lon1, lat2, lon2) => {
  const R = 6378137;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
};

// ---------------------------------------------------------------------------
// Map init
// ---------------------------------------------------------------------------

const initMap = () => {
  map = L.map(mapContainer.value, { zoomControl: false }).setView([47.0, 19.0], 7);
  L.control.zoom({ position: "bottomright" }).addTo(map);

  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { subdomains: "abcd", maxZoom: 20 }).addTo(map);
};

// ---------------------------------------------------------------------------
// Runway rendering
// ---------------------------------------------------------------------------

const drawRunway = (el) => {
  if (el.type !== "way" || !el.geometry || el.geometry.length < 2) return;

  const centerlineLatLngs = el.geometry.map((g) => [g.lat, g.lon]);

  // Parse width from OSM tag (metres). Fall back to 45 m if missing.
  const widthM = el.tags?.width ? parseFloat(el.tags.width) : 45;
  const halfWidth = widthM / 2;

  // --- 1. Asphalt / tarmac base polygon ---
  const rightEdge = offsetPolyline(centerlineLatLngs, halfWidth);
  const leftEdge = offsetPolyline(centerlineLatLngs, -halfWidth);
  const footprint = [...rightEdge, ...[...leftEdge].reverse()];

  const basePoly = L.polygon(footprint, {
    color: "transparent",
    fillColor: "#1a1a1a", // very dark asphalt
    fillOpacity: 1,
    interactive: false,
  }).addTo(map);
  pathLayers.push(basePoly);

  // --- 2. White solid edge lines ---
  const rightLine = L.polyline(rightEdge, {
    color: "#ffffff",
    weight: 2,
    opacity: 0.85,
    interactive: false,
  }).addTo(map);
  pathLayers.push(rightLine);

  const leftLine = L.polyline(leftEdge, {
    color: "#ffffff",
    weight: 2,
    opacity: 0.85,
    interactive: false,
  }).addTo(map);
  pathLayers.push(leftLine);

  // --- 3. White dashed centreline ---
  const centerline = L.polyline(centerlineLatLngs, {
    color: "#ffffff",
    weight: 1.5,
    opacity: 0.7,
    dashArray: "20, 15",
    interactive: false,
  }).addTo(map);
  pathLayers.push(centerline);

  // --- 4. Touchdown zone bars ---
  // ICAO standard: first bar at 150 m from threshold, then every 150 m,
  // stopping at 900 m. Bar length = 22.5 m (half runway width, capped at 22.5 m).
  const runwayLengthM = distanceM(centerlineLatLngs[0][0], centerlineLatLngs[0][1], centerlineLatLngs[centerlineLatLngs.length - 1][0], centerlineLatLngs[centerlineLatLngs.length - 1][1]);

  const tzBarLengthM = Math.min(halfWidth * 0.8, 22.5);
  const tzOffsets = [150, 300, 450, 600, 750, 900].filter((d) => d < runwayLengthM - 150);

  // Draw TDZ bars from both thresholds
  [0, centerlineLatLngs.length - 1].forEach((endIdx) => {
    const isLowEnd = endIdx === 0;
    const thresholdPt = centerlineLatLngs[endIdx];
    const nextPt = centerlineLatLngs[isLowEnd ? 1 : centerlineLatLngs.length - 2];
    const inwardBearing = bearing(thresholdPt[0], thresholdPt[1], nextPt[0], nextPt[1]);
    const perpBearing = (inwardBearing + 90) % 360;

    tzOffsets.forEach((dist) => {
      const barCenter = destinationPoint(thresholdPt[0], thresholdPt[1], inwardBearing, dist);
      const barLeft = destinationPoint(barCenter[0], barCenter[1], perpBearing, tzBarLengthM);
      const barRight = destinationPoint(barCenter[0], barCenter[1], (perpBearing + 180) % 360, tzBarLengthM);

      // Two parallel bars, each 5 m wide of the centre (ICAO TDZ style)
      [
        [5, 10],
        [-5, -10],
      ].forEach(([innerOff, outerOff]) => {
        const p1 = destinationPoint(barLeft[0], barLeft[1], inwardBearing, innerOff);
        const p2 = destinationPoint(barLeft[0], barLeft[1], inwardBearing, outerOff);
        const p3 = destinationPoint(barRight[0], barRight[1], inwardBearing, outerOff);
        const p4 = destinationPoint(barRight[0], barRight[1], inwardBearing, innerOff);

        const bar = L.polygon([p1, p2, p3, p4], {
          color: "transparent",
          fillColor: "#ffffff",
          fillOpacity: 0.75,
          interactive: false,
        }).addTo(map);
        pathLayers.push(bar);
      });
    });
  });

  // --- 5. Threshold piano keys ---
  // 8 alternating white bars across the full width at each end
  [0, centerlineLatLngs.length - 1].forEach((endIdx) => {
    const isLowEnd = endIdx === 0;
    const thresholdPt = centerlineLatLngs[endIdx];
    const nextPt = centerlineLatLngs[isLowEnd ? 1 : centerlineLatLngs.length - 2];
    const inwardBearing = bearing(thresholdPt[0], thresholdPt[1], nextPt[0], nextPt[1]);
    const perpBearing = (inwardBearing + 90) % 360;

    const numStripes = 8;
    const stripeWidthM = (widthM * 0.8) / (numStripes * 2 - 1); // white stripes only
    const stripeDepthM = 30;
    const startOffset = 6; // metres inboard from threshold

    for (let i = 0; i < numStripes; i++) {
      // Position each stripe symmetrically from centre
      const lateralOffsets = [-1, 1].map((side) => side * ((stripeWidthM * (i * 2)) / 2 + stripeWidthM / 2 - (widthM * 0.8) / 2 + widthM * 0.4));

      // Simpler: evenly spread numStripes across 80% of runway width
      const totalSpan = widthM * 0.8;
      const gap = totalSpan / (numStripes - 1);
      const lateralCenter = -totalSpan / 2 + gap * i;

      const stripeCenterBase = destinationPoint(thresholdPt[0], thresholdPt[1], perpBearing, lateralCenter);
      const stripeStart = destinationPoint(stripeCenterBase[0], stripeCenterBase[1], inwardBearing, startOffset);
      const stripeEnd = destinationPoint(stripeStart[0], stripeStart[1], inwardBearing, stripeDepthM);

      const halfBarW = stripeWidthM * 0.45;
      const p1 = destinationPoint(stripeStart[0], stripeStart[1], perpBearing, halfBarW);
      const p2 = destinationPoint(stripeEnd[0], stripeEnd[1], perpBearing, halfBarW);
      const p3 = destinationPoint(stripeEnd[0], stripeEnd[1], (perpBearing + 180) % 360, halfBarW);
      const p4 = destinationPoint(stripeStart[0], stripeStart[1], (perpBearing + 180) % 360, halfBarW);

      const stripe = L.polygon([p1, p2, p3, p4], {
        color: "transparent",
        fillColor: "#ffffff",
        fillOpacity: 0.85,
        interactive: false,
      }).addTo(map);
      pathLayers.push(stripe);
    }
  });

  // --- 6. Runway designator labels ---
  if (el.tags?.ref) {
    const [leRef, heRef] = el.tags.ref.split("/");

    const addDesignatorLabel = (pt, nextPt, label) => {
      if (!label) return;
      const brg = bearing(pt[0], pt[1], nextPt[0], nextPt[1]);
      const markerPt = destinationPoint(pt[0], pt[1], brg, 60);

      const icon = L.divIcon({
        html: `<div class="rwy-designator" style="transform: rotate(${brg}deg)">${label}</div>`,
        className: "",
        iconSize: [40, 20],
        iconAnchor: [20, 10],
      });
      const m = L.marker(markerPt, { icon, interactive: false }).addTo(map);
      pathLayers.push(m);
    };

    addDesignatorLabel(centerlineLatLngs[0], centerlineLatLngs[1], leRef);
    addDesignatorLabel(centerlineLatLngs[centerlineLatLngs.length - 1], centerlineLatLngs[centerlineLatLngs.length - 2], heRef);
  }
};

// ---------------------------------------------------------------------------
// Overpass fetch
// ---------------------------------------------------------------------------

const fetchAndDrawRunways = async (lat, lon) => {
  const query = `
    [out:json];
    way["aeroway"="runway"](around:4000,${lat},${lon});
    out geom tags;
  `;
  const url = `https://overpass-api.de/api/interpreter?data=${encodeURIComponent(query)}`;

  try {
    const response = await fetch(url);
    const data = await response.json();
    if (!data.elements?.length) return;
    data.elements.forEach(drawRunway);
  } catch (err) {
    console.error("Overpass API error:", err);
  }
};

// ---------------------------------------------------------------------------
// Flight path + landings
// ---------------------------------------------------------------------------

const clearMap = () => {
  if (!map) return;
  pathLayers.forEach((layer) => map.removeLayer(layer));
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

      fetchAndDrawRunways(landing.lat, landing.lon);
    });
  }

  if (segments.length > 0) {
    const group = new L.featureGroup(segments);
    map.fitBounds(group.getBounds(), { padding: [100, 100] });
  }
};

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

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

/* Runway designator numbers */
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
