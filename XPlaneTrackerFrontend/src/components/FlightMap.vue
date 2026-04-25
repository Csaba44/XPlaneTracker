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

const mapContainer = ref(null);
const isChartVisible = ref(false);
const showConnections = ref(false);
const chartRef = ref(null);
let map = null;
let pathLayers = [];
let connectionLayers = [];
let hoverMarker = null;

const runwayCache = new Map();
const pendingRequests = new Set();

// Airport coordinate cache
const airportCoordCache = new Map();
let airportsJsonData = null;

const localCacheKey = (lat, lon) => `${Math.round(lat * 100) / 100},${Math.round(lon * 100) / 100}`;

// FlightRadar24-matching altitude → colour interpolator (input: feet)
const FR24_STOPS = [
  { ft: 0, r: 255, g: 255, b: 255 },
  { ft: 300, r: 255, g: 224, b: 98 },
  { ft: 700, r: 255, g: 234, b: 0 },
  { ft: 1000, r: 240, g: 255, b: 0 },
  { ft: 1300, r: 204, g: 255, b: 0 },
  { ft: 2000, r: 66, g: 255, b: 0 },
  { ft: 2600, r: 30, g: 255, b: 0 },
  { ft: 3300, r: 0, g: 255, b: 12 },
  { ft: 3900, r: 0, g: 255, b: 54 },
  { ft: 4900, r: 0, g: 255, b: 114 },
  { ft: 6600, r: 0, g: 255, b: 156 },
  { ft: 8200, r: 0, g: 255, b: 210 },
  { ft: 9800, r: 0, g: 255, b: 228 },
  { ft: 11500, r: 0, g: 234, b: 255 },
  { ft: 13100, r: 0, g: 192, b: 255 },
  { ft: 14800, r: 0, g: 168, b: 255 },
  { ft: 16400, r: 0, g: 150, b: 255 },
  { ft: 18000, r: 0, g: 120, b: 255 },
  { ft: 19700, r: 0, g: 84, b: 255 },
  { ft: 21300, r: 0, g: 48, b: 255 },
  { ft: 23000, r: 0, g: 30, b: 255 },
  { ft: 24600, r: 0, g: 0, b: 255 },
  { ft: 26200, r: 18, g: 0, b: 255 },
  { ft: 27900, r: 36, g: 0, b: 255 },
  { ft: 29500, r: 54, g: 0, b: 255 },
  { ft: 31200, r: 78, g: 0, b: 255 },
  { ft: 32800, r: 96, g: 0, b: 255 },
  { ft: 34400, r: 120, g: 0, b: 255 },
  { ft: 36100, r: 150, g: 0, b: 255 },
  { ft: 37700, r: 174, g: 0, b: 255 },
  { ft: 39400, r: 216, g: 0, b: 255 },
  { ft: 41000, r: 255, g: 0, b: 228 },
  { ft: 42600, r: 255, g: 0, b: 0 },
];

const altToColor = (ft) => {
  if (ft <= FR24_STOPS[0].ft) {
    const s = FR24_STOPS[0];
    return `rgb(${s.r},${s.g},${s.b})`;
  }
  if (ft >= FR24_STOPS[FR24_STOPS.length - 1].ft) {
    const s = FR24_STOPS[FR24_STOPS.length - 1];
    return `rgb(${s.r},${s.g},${s.b})`;
  }
  for (let i = 1; i < FR24_STOPS.length; i++) {
    if (ft <= FR24_STOPS[i].ft) {
      const lo = FR24_STOPS[i - 1],
        hi = FR24_STOPS[i];
      const t = (ft - lo.ft) / (hi.ft - lo.ft);
      const r = Math.round(lo.r + t * (hi.r - lo.r));
      const g = Math.round(lo.g + t * (hi.g - lo.g));
      const b = Math.round(lo.b + t * (hi.b - lo.b));
      return `rgb(${r},${g},${b})`;
    }
  }
};

// --- Geometry helpers ---
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

// --- Path simplification ---
const toleranceForGS = (gs) => {
  if (gs < 50) return 0.000015;
  if (gs < 150) return 0.000015;
  if (gs < 300) return 0.00007;
  return 0.00015;
};

const rdpPerpendicularDist = (point, lineStart, lineEnd) => {
  const [px, py] = [point[1], point[0]];
  const [x1, y1] = [lineStart[1], lineStart[0]];
  const [x2, y2] = [lineEnd[1], lineEnd[0]];
  const dx = x2 - x1,
    dy = y2 - y1;
  const lenSq = dx * dx + dy * dy;
  if (lenSq === 0) return Math.hypot(px - x1, py - y1);
  const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / lenSq));
  return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
};

const rdpAdaptive = (points, tolerances) => {
  if (points.length <= 2) return points;
  let maxDist = 0,
    maxIdx = 0;
  for (let i = 1; i < points.length - 1; i++) {
    const d = rdpPerpendicularDist(points[i], points[0], points[points.length - 1]);
    if (d > maxDist) {
      maxDist = d;
      maxIdx = i;
    }
  }
  const segTolerance = Math.min(tolerances[0], tolerances[tolerances.length - 1]);
  if (maxDist > segTolerance) {
    const left = rdpAdaptive(points.slice(0, maxIdx + 1), tolerances.slice(0, maxIdx + 1));
    const right = rdpAdaptive(points.slice(maxIdx), tolerances.slice(maxIdx));
    return [...left.slice(0, -1), ...right];
  }
  return [points[0], points[points.length - 1]];
};

const nearestPointOnPolyline = (latlng, points) => {
  let minDist = Infinity,
    nearest = null,
    nearestIdx = 0;
  for (let i = 0; i < points.length; i++) {
    const d = Math.hypot(points[i][0] - latlng.lat, points[i][1] - latlng.lng);
    if (d < minDist) {
      minDist = d;
      nearest = points[i];
      nearestIdx = i;
    }
  }
  return { point: nearest, idx: nearestIdx };
};

// --- Chart ---
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
  if (!params.axesInfo || !map) return;
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

// --- Runway drawing (restored from original + displaced threshold support) ---
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
      if (angleDiff(actualBearing, leHeading) > 90) cl = [...cl].reverse();
    }
  }
  const leInward = bearing(cl[0][0], cl[0][1], cl[1][0], cl[1][1]);
  const heInward = bearing(cl[cl.length - 1][0], cl[cl.length - 1][1], cl[cl.length - 2][0], cl[cl.length - 2][1]);
  const right = offsetPolyline(cl, half);
  const left = offsetPolyline(cl, -half);
  pathLayers.push(L.polygon([...right, ...[...left].reverse()], { color: "transparent", fillColor: "#111111", fillOpacity: 1, interactive: false, pane: "runwaysPane" }).addTo(map));
  [right, left].forEach((edge) => {
    pathLayers.push(L.polyline(edge, { color: "#ffffff", weight: 2, opacity: 0.9, interactive: false, pane: "runwaysPane" }).addTo(map));
  });
  pathLayers.push(L.polyline(cl, { color: "#ffffff", weight: 1.5, opacity: 0.65, dashArray: "20 15", interactive: false, pane: "runwaysPane" }).addTo(map));

  // Displaced threshold detection: OSM tags displaced_threshold:le / displaced_threshold:he (metres)
  const leDisplaced = el.tags?.["displaced_threshold:le"] ? parseFloat(el.tags["displaced_threshold:le"]) : 0;
  const heDisplaced = el.tags?.["displaced_threshold:he"] ? parseFloat(el.tags["displaced_threshold:he"]) : 0;

  // Draws the displaced threshold zone:
  // - Transverse bar at the pavement end
  // - Solid filled arrow polygons pointing INWARD (toward landing threshold), spaced through the zone
  // - Solid transverse bar at the actual (displaced) threshold line
  const drawDisplacedZone = (pavementEnd, inwardBrg, displaceM, landingThreshold) => {
    if (displaceM <= 0) return;
    const perpBrg = (inwardBrg + 90) % 360;
    const oppBrg = (inwardBrg + 180) % 360;

    // 1. Transverse bar at pavement end
    const barL = destination(pavementEnd[0], pavementEnd[1], (perpBrg + 180) % 360, half * 0.85);
    const barR = destination(pavementEnd[0], pavementEnd[1], perpBrg, half * 0.85);
    pathLayers.push(L.polyline([barL, barR], { color: "#ffffff", weight: 2.5, opacity: 0.85, interactive: false, pane: "runwaysPane" }).addTo(map));

    // 2. Solid filled arrow polygons pointing inward (toward landing threshold)
    //    Real markings: typically 3 arrows evenly spaced laterally, repeated every ~50 m along zone
    const arrowSpacingM = Math.min(50, displaceM / 1.5);
    const arrowCount = Math.max(1, Math.round(displaceM / arrowSpacingM));
    const arrowW = half * 0.28; // half-width of arrow base
    const arrowBodyLen = 20; // shaft length
    const arrowHeadLen = 14; // head length
    const lateralSlots = [-half * 0.45, 0, half * 0.45]; // 3 columns

    for (let i = 0; i < arrowCount; i++) {
      // Place arrows so they don't crowd the pavement-end bar or the threshold bar
      const alongDist = (i + 0.5) * (displaceM / arrowCount);
      const rowCenter = destination(pavementEnd[0], pavementEnd[1], inwardBrg, alongDist);

      for (const latOff of lateralSlots) {
        const base = destination(rowCenter[0], rowCenter[1], perpBrg, latOff);

        // Tail (wide base) — at the outboard / pavement-end side of the arrow
        const tailCenter = destination(base[0], base[1], oppBrg, arrowBodyLen / 2);
        const tL = destination(tailCenter[0], tailCenter[1], (perpBrg + 180) % 360, arrowW * 0.55);
        const tR = destination(tailCenter[0], tailCenter[1], perpBrg, arrowW * 0.55);

        // Mid point (narrowing toward head)
        const midCenter = destination(base[0], base[1], inwardBrg, arrowBodyLen / 2);
        const mL = destination(midCenter[0], midCenter[1], (perpBrg + 180) % 360, arrowW * 0.55);
        const mR = destination(midCenter[0], midCenter[1], perpBrg, arrowW * 0.55);

        // Arrowhead base (wider)
        const hBase = destination(base[0], base[1], inwardBrg, arrowBodyLen);
        const hL = destination(hBase[0], hBase[1], (perpBrg + 180) % 360, arrowW);
        const hR = destination(hBase[0], hBase[1], perpBrg, arrowW);

        // Arrowhead tip (apex pointing inward)
        const tip = destination(hBase[0], hBase[1], inwardBrg, arrowHeadLen);

        // Draw as filled polygon: tail-left → mid-left → head-left → tip → head-right → mid-right → tail-right
        pathLayers.push(
          L.polygon([tL, mL, hL, tip, hR, mR, tR], {
            color: "transparent",
            fillColor: "#ffffff",
            fillOpacity: 0.85,
            interactive: false,
            pane: "runwaysPane",
          }).addTo(map),
        );
      }
    }

    // 3. Solid transverse bar at the actual (displaced) landing threshold
    const thrL = destination(landingThreshold[0], landingThreshold[1], (perpBrg + 180) % 360, half * 0.85);
    const thrR = destination(landingThreshold[0], landingThreshold[1], perpBrg, half * 0.85);
    pathLayers.push(L.polyline([thrL, thrR], { color: "#ffffff", weight: 3, opacity: 1, interactive: false, pane: "runwaysPane" }).addTo(map));
  };

  // Actual landing thresholds (shifted inward by displaced amount)
  const leThreshold = leDisplaced > 0 ? destination(cl[0][0], cl[0][1], leInward, leDisplaced) : cl[0];
  const heThreshold = heDisplaced > 0 ? destination(cl[cl.length - 1][0], cl[cl.length - 1][1], heInward, heDisplaced) : cl[cl.length - 1];

  drawDisplacedZone(cl[0], leInward, leDisplaced, leThreshold);
  drawDisplacedZone(cl[cl.length - 1], heInward, heDisplaced, heThreshold);

  const drawPianoKeys = (thresholdPt, inwardBrg) => {
    const perpBrg = (inwardBrg + 90) % 360;
    const numStripes = 8,
      spanM = widthM * 0.8,
      gap = spanM / (numStripes - 1);
    const stripeHalfW = (spanM / (numStripes * 2 - 1)) * 0.45,
      depthM = 30,
      inboardM = 6;
    for (let i = 0; i < numStripes; i++) {
      const lateralOffset = -spanM / 2 + gap * i;
      const center = destination(thresholdPt[0], thresholdPt[1], perpBrg, lateralOffset);
      const near = destination(center[0], center[1], inwardBrg, inboardM);
      const far = destination(near[0], near[1], inwardBrg, depthM);
      const p1 = destination(near[0], near[1], perpBrg, stripeHalfW);
      const p2 = destination(far[0], far[1], perpBrg, stripeHalfW);
      const p3 = destination(far[0], far[1], (perpBrg + 180) % 360, stripeHalfW);
      const p4 = destination(near[0], near[1], (perpBrg + 180) % 360, stripeHalfW);
      pathLayers.push(L.polygon([p1, p2, p3, p4], { color: "transparent", fillColor: "#ffffff", fillOpacity: 0.85, interactive: false, pane: "runwaysPane" }).addTo(map));
    }
  };
  drawPianoKeys(leThreshold, leInward);
  drawPianoKeys(heThreshold, heInward);

  const runwayLen = distanceM(leThreshold[0], leThreshold[1], heThreshold[0], heThreshold[1]);
  const tzDistances = [150, 300, 450, 600, 750, 900].filter((d) => d < runwayLen - 150);
  const barLenM = 22.5,
    barWidthM = 3,
    barLateralM = widthM * 0.2;
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
        pathLayers.push(L.polygon([p1, p2, p3, p4], { color: "transparent", fillColor: "#ffffff", fillOpacity: 0.75, interactive: false, pane: "runwaysPane" }).addTo(map));
      });
    });
  };
  drawTDZBars(leThreshold, leInward);
  drawTDZBars(heThreshold, heInward);

  if (el.tags?.ref) {
    let parts = el.tags.ref.split("/");
    let leRef = parts[0],
      heRef = parts[1];
    if (leRef && heRef) {
      const hdg1 = parseInt(leRef, 10) * 10;
      if (angleDiff(hdg1, leInward) > angleDiff(hdg1, heInward)) [leRef, heRef] = [heRef, leRef];
    }
    const addLabel = (thresholdPt, inwardBrg, label) => {
      if (!label) return;
      const pos = destination(thresholdPt[0], thresholdPt[1], inwardBrg, 55);
      const icon = L.divIcon({ html: `<div class="rwy-designator" style="transform:rotate(${inwardBrg}deg)">${label}</div>`, className: "", iconSize: [40, 20], iconAnchor: [20, 10] });
      pathLayers.push(L.marker(pos, { icon, interactive: false }).addTo(map));
    };
    addLabel(leThreshold, leInward, leRef);
    addLabel(heThreshold, heInward, heRef);
  }
};

const fetchAndDrawRunways = async (lat, lon) => {
  const key = localCacheKey(lat, lon);
  if (runwayCache.has(key)) {
    runwayCache.get(key).forEach(drawRunway);
    return;
  }
  if (pendingRequests.has(key)) return;
  pendingRequests.add(key);
  try {
    const response = await api.get(`/api/runways?lat=${lat}&lon=${lon}`);
    const data = response.data;
    if (data.elements) {
      runwayCache.set(key, data.elements);
      data.elements.forEach(drawRunway);
    }
  } catch (err) {
    console.error(err);
  } finally {
    pendingRequests.delete(key);
  }
};

const initMap = () => {
  map = L.map(mapContainer.value, { zoomControl: false }).setView([47.0, 19.0], 7);
  L.control.zoom({ position: "bottomright" }).addTo(map);
  map.createPane("runwaysPane").style.zIndex = 390;
  map.createPane("flightPathPane").style.zIndex = 410;
  map.createPane("connectionsPane").style.zIndex = 380;
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { maxZoom: 20 }).addTo(map);
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

const drawFlight = (data) => {
  clearMap();
  if (!map || !data?.path) return;

  const rawPath = data.path;
  const coordsForRDP = rawPath.map((p) => [p[1], p[2]]);
  const tolerances = rawPath.map((p) => toleranceForGS(p[4] || 0));
  const simplifiedCoords = rdpAdaptive(coordsForRDP, tolerances);

  const coordKey = (lat, lon) => `${lat.toFixed(6)},${lon.toFixed(6)}`;
  const pointMap = new Map(rawPath.map((p) => [coordKey(p[1], p[2]), p]));
  const reducedPath = simplifiedCoords.map((coord) => pointMap.get(coordKey(coord[0], coord[1])) || [null, coord[0], coord[1], 0, 0]);

  // Flat arrays for the simplified path — used for per-segment rendering and tooltip lookup
  const allPoints = reducedPath.map((p) => [p[1], p[2]]);
  const allAltitudes = reducedPath.map((p) => p[3] || 0);
  const allSpeeds = reducedPath.map((p) => p[4] || 0);

  const flightLayerGroup = L.layerGroup();

  // One short polyline per segment, coloured by the interpolated midpoint altitude.
  // Segments share endpoints so they join seamlessly; lineCap "butt" avoids
  // round caps that would poke out from under the next segment's colour.
  for (let i = 0; i < reducedPath.length - 1; i++) {
    const altMid = (allAltitudes[i] + allAltitudes[i + 1]) / 2;
    const color = altToColor(altMid);

    const seg = L.polyline([allPoints[i], allPoints[i + 1]], { color, weight: 4, opacity: 0.95, lineCap: "butt", lineJoin: "round", pane: "flightPathPane" });

    seg.on("mousemove", (e) => {
      const { idx } = nearestPointOnPolyline(e.latlng, allPoints);
      seg.bindTooltip(`<div class="font-mono text-xs"><b>ALT:</b> ${allAltitudes[idx]} ft<br><b>GS:</b> ${allSpeeds[idx] || "N/A"} KTS</div>`, { sticky: true, className: "flight-path-tooltip", permanent: false }).openTooltip(e.latlng);
    });
    seg.on("mouseout", () => seg.closeTooltip());

    flightLayerGroup.addLayer(seg);
    pathLayers.push(seg);
  }

  flightLayerGroup.addTo(map);

  if (data.path && data.path.length > 0) {
    const departurePoint = data.path[0];
    fetchAndDrawRunways(departurePoint[1], departurePoint[2]);
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
      fetchAndDrawRunways(landing.lat, landing.lon);
    });
  }

  if (allPoints.length > 0) {
    map.fitBounds(L.latLngBounds(allPoints), { padding: [100, 100] });
  }
};

// --- Connections feature ---

const loadAirportsJson = async () => {
  if (airportsJsonData) return airportsJsonData;
  try {
    // Try the backend airports.json first (same source as backend uses)
    const response = await fetch("https://raw.githubusercontent.com/mwgg/Airports/master/airports.json");
    airportsJsonData = await response.json();
    return airportsJsonData;
  } catch (e) {
    console.error("Failed to load airports.json", e);
    return {};
  }
};

const getAirportCoords = async (icao) => {
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

// Compute unique connection pairs from flights (sorted so LHBP-LGZA and LGZA-LHBP are same pair)
const computeConnections = (flightList) => {
  const pairMap = new Map();

  for (const flight of flightList) {
    const dep = flight.dep_icao;
    const arr = flight.arr_icao;

    // Skip incomplete flights (either end is null/empty)
    if (!dep || !arr || dep === "NULL" || arr === "NULL") continue;

    // Normalize: sort alphabetically to group both directions
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

  // Collect unique airports to draw dots (deduplicated)
  const airportDots = new Map(); // icao -> coords

  for (const conn of connections) {
    const coords1 = await getAirportCoords(conn.icao1);
    const coords2 = await getAirportCoords(conn.icao2);

    if (!coords1 || !coords2) continue;

    airportDots.set(conn.icao1, coords1);
    airportDots.set(conn.icao2, coords2);

    const label = `${conn.icao1} – ${conn.icao2} (${conn.count} járat)`;

    // Visible dashed line (thin, styled)
    const visLine = L.polyline([coords1, coords2], {
      color: "#94a3b8",
      weight: 2,
      opacity: 0.5,
      dashArray: "6 4",
      interactive: false,
      pane: "connectionsPane",
    });

    // Wide invisible hit target on top for easy mouse interaction
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
      // Remove focus outline immediately after click
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

  // Draw airport dots for every unique airport in the connections
  for (const [icao, coords] of airportDots) {
    // Outer glow ring
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

    // Inner filled dot
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

onMounted(() => {
  initMap();
  if (props.flightData) drawFlight(props.flightData);
});
</script>

<template>
  <main class="flex-grow relative">
    <div ref="mapContainer" class="absolute inset-0 w-full h-full z-0"></div>

    <!-- Bottom left controls -->
    <div class="absolute bottom-6 left-6 z-[1000] flex flex-col gap-2">
      <!-- Flight chart toggle -->
      <button @click="isChartVisible = !isChartVisible" class="bg-slate-900/90 hover:bg-slate-800 text-white px-5 py-2.5 rounded-full border border-slate-700 shadow-2xl flex items-center gap-2 transition-all group">
        <i class="fa-solid fa-chart-line text-cyan-400 group-hover:scale-110 transition-transform"></i>
        <span class="font-bold text-xs uppercase tracking-widest">Grafikon</span>
      </button>

      <!-- Connections toggle -->
      <button @click="showConnections = !showConnections" :class="['px-5 py-2.5 rounded-full border shadow-2xl flex items-center gap-2 transition-all group', showConnections ? 'bg-cyan-500/20 hover:bg-cyan-500/30 border-cyan-500/60 text-cyan-300' : 'bg-slate-900/90 hover:bg-slate-800 border-slate-700 text-white']">
        <i :class="['fa-solid fa-route transition-transform group-hover:scale-110', showConnections ? 'text-cyan-400' : 'text-slate-400']"></i>
        <span class="font-bold text-xs uppercase tracking-widest">Kapcsolatok</span>
        <span v-if="showConnections" class="ml-1 w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_6px_#22d3ee] animate-pulse"></span>
      </button>
    </div>

    <!-- Chart panel -->
    <div v-if="isChartVisible" class="absolute bottom-20 left-6 z-[1000] w-[90vw] max-w-2xl h-64 bg-slate-900/95 border border-slate-700 rounded-xl shadow-2xl backdrop-blur-md p-4">
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
.chart {
  height: 100%;
  width: 100%;
}
/* Kill the ugly browser focus rectangle on clicked Leaflet SVG paths */
.leaflet-interactive:focus {
  outline: none;
}
</style>
