import L from "leaflet";
import api from "../config/api";
import { bearing, destination, distanceM, offsetPolyline, designatorToHeading, angleDiff } from "./useGeo";

const runwayCache = new Map();
const pendingRequests = new Set();
const EXTENDED_CENTERLINE_NM = 15;
const NM_TO_M = 1852;

export const drawExtendedCenterline = (el, map, pathLayers) => {
  if (el.type !== "way" || !el.geometry || el.geometry.length < 2) return;
  const cl = el.geometry.map((g) => [g.lat, g.lon]);
  const leTh = cl[0];
  const heTh = cl[cl.length - 1];
  const leInward = bearing(leTh[0], leTh[1], heTh[0], heTh[1]);
  const heInward = bearing(heTh[0], heTh[1], leTh[0], leTh[1]);
  const distM = EXTENDED_CENTERLINE_NM * NM_TO_M;
  const leExtEnd = destination(leTh[0], leTh[1], (leInward + 180) % 360, distM);
  const heExtEnd = destination(heTh[0], heTh[1], (heInward + 180) % 360, distM);
  const style = {
    color: "#94a3b8",
    weight: 1,
    opacity: 0.35,
    dashArray: "6 8",
    interactive: false,
    pane: "extendedCenterlinePane",
  };
  pathLayers.push(L.polyline([leTh, leExtEnd], style).addTo(map));
  pathLayers.push(L.polyline([heTh, heExtEnd], style).addTo(map));
};

export const drawDisplacedThreshold = (el, map, pathLayers) => {
  if (el.type !== "way" || !el.geometry || el.geometry.length < 2) return;
  const cl = el.geometry.map((g) => [g.lat, g.lon]);
  const widthM = el.tags?.width ? parseFloat(el.tags.width) : 45;
  const half = widthM / 2;

  const inwardBrg = bearing(cl[0][0], cl[0][1], cl[cl.length - 1][0], cl[cl.length - 1][1]);
  const perpBrg = (inwardBrg + 90) % 360;
  const oppBrg = (inwardBrg + 180) % 360;
  const pavementEnd = cl[0];
  const landingThreshold = cl[cl.length - 1];
  const displaceM = distanceM(pavementEnd[0], pavementEnd[1], landingThreshold[0], landingThreshold[1]);

  // Fill background black
  const right = offsetPolyline(cl, half);
  const left = offsetPolyline(cl, -half);
  pathLayers.push(L.polygon([...right, ...[...left].reverse()], {
    color: "transparent", fillColor: "#111111", fillOpacity: 1,
    interactive: false, pane: "runwaysPane"
  }).addTo(map));

  // Edge lines
  [right, left].forEach((edge) => {
    pathLayers.push(L.polyline(edge, { color: "#ffffff", weight: 2, opacity: 0.9, interactive: false, pane: "runwaysPane" }).addTo(map));
  });

  // Solid bar at pavement end
  const barL = destination(pavementEnd[0], pavementEnd[1], (perpBrg + 180) % 360, half * 0.85);
  const barR = destination(pavementEnd[0], pavementEnd[1], perpBrg, half * 0.85);
  pathLayers.push(L.polyline([barL, barR], {
    color: "#ffffff", weight: 3, opacity: 1, interactive: false, pane: "runwaysPane"
  }).addTo(map));

  // Arrows pointing inward
  const arrowCount = Math.max(1, Math.floor(displaceM / 60));
  const arrowHalfW = half * 0.03;      // was 0.18 — much slimmer
  const arrowBodyLen = 24;              // was 18 — taller
  const arrowHeadLen = 10;             // was 12
  const lateralSlots = [0];            // was [-half * 0.35, half * 0.35] — single centered arrow

  for (let i = 0; i < arrowCount; i++) {
    const alongDist = (i + 0.5) * (displaceM / arrowCount);
    const base = destination(pavementEnd[0], pavementEnd[1], inwardBrg, alongDist);

    for (const latOff of lateralSlots) {
      const center = destination(base[0], base[1], perpBrg, latOff);
      const tail = destination(center[0], center[1], oppBrg, arrowBodyLen / 2);
      const head = destination(center[0], center[1], inwardBrg, arrowBodyLen / 2);
      const tL = destination(tail[0], tail[1], (perpBrg + 180) % 360, arrowHalfW);
      const tR = destination(tail[0], tail[1], perpBrg, arrowHalfW);
      const hL = destination(head[0], head[1], (perpBrg + 180) % 360, arrowHalfW);
      const hR = destination(head[0], head[1], perpBrg, arrowHalfW);
      const wL = destination(head[0], head[1], (perpBrg + 180) % 360, arrowHalfW * 2.2);
      const wR = destination(head[0], head[1], perpBrg, arrowHalfW * 2.2);
      const tip = destination(head[0], head[1], inwardBrg, arrowHeadLen);
      pathLayers.push(L.polygon([tL, tR, hR, wR, tip, wL, hL], {
        color: "transparent", fillColor: "#ffffff", fillOpacity: 0.85,
        interactive: false, pane: "runwaysPane",
      }).addTo(map));
    }
  }

  // Solid bar at landing threshold
  const thrL = destination(landingThreshold[0], landingThreshold[1], (perpBrg + 180) % 360, half * 0.85);
  const thrR = destination(landingThreshold[0], landingThreshold[1], perpBrg, half * 0.85);
  pathLayers.push(L.polyline([thrL, thrR], {
    color: "#ffffff", weight: 3, opacity: 1, interactive: false, pane: "runwaysPane"
  }).addTo(map));
};

export const drawRunway = (el, map, pathLayers) => {
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

  const leThreshold = cl[0];
  const heThreshold = cl[cl.length - 1];

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

  const trueLEInward = bearing(leThreshold[0], leThreshold[1], heThreshold[0], heThreshold[1]);
  const trueHEInward = bearing(heThreshold[0], heThreshold[1], leThreshold[0], leThreshold[1]);
  drawTDZBars(leThreshold, trueLEInward);
  drawTDZBars(heThreshold, trueHEInward);

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

export const fetchAndDrawRunways = async (lat, lon, map, pathLayers) => {
  const localCacheKey = (lat, lon) => `${Math.round(lat * 100) / 100},${Math.round(lon * 100) / 100}`;
  const key = localCacheKey(lat, lon);
  if (runwayCache.has(key)) {
    const cached = runwayCache.get(key);
    cached.filter(el => el.tags?.runway !== "displaced_threshold").forEach((el) => {
      drawRunway(el, map, pathLayers);
      drawExtendedCenterline(el, map, pathLayers);
    });
    cached.filter(el => el.tags?.runway === "displaced_threshold").forEach((el) => drawDisplacedThreshold(el, map, pathLayers));
    return;
  }
  if (pendingRequests.has(key)) return;
  pendingRequests.add(key);
  try {
    const response = await api.get(`/api/runways?lat=${lat}&lon=${lon}`);
    const data = response.data;
    if (data.elements) {
      runwayCache.set(key, data.elements);
      data.elements.filter(el => el.tags?.runway !== "displaced_threshold").forEach((el) => {
        drawRunway(el, map, pathLayers);
        drawExtendedCenterline(el, map, pathLayers);
      });
      data.elements.filter(el => el.tags?.runway === "displaced_threshold").forEach((el) => drawDisplacedThreshold(el, map, pathLayers));
    }
  } catch (err) {
    console.error(err);
  } finally {
    pendingRequests.delete(key);
  }
};

export { pendingRequests };