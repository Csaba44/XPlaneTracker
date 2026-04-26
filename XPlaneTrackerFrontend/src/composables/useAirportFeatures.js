import L from "leaflet";
import api from "../config/api";

const featureCache = new Map();
const pendingFeatureRequests = new Set();

const localCacheKey = (lat, lon) => `${Math.round(lat * 100) / 100},${Math.round(lon * 100) / 100}`;

const drawTaxiways = (elements, map, featureLayers) => {
  elements
    .filter((el) => (el.type === "way") && (el.tags?.aeroway === "taxiway" || el.tags?.aeroway === "taxilane"))
    .forEach((el) => {
      if (!el.geometry || el.geometry.length < 2) return;
      const coords = el.geometry.map((g) => [g.lat, g.lon]);
      const isTaxilane = el.tags?.aeroway === "taxilane";

      const line = L.polyline(coords, {
        color: "#f59e0b",
        weight: isTaxilane ? 1.5 : 2.5,
        opacity: 0.85,
        interactive: !!el.tags?.ref,
        pane: "taxiwaysPane",
      });

      if (el.tags?.ref) {
        line.bindTooltip(`<span class="taxiway-label">${el.tags.ref}</span>`, {
          permanent: false,
          sticky: true,
          className: "taxiway-tooltip",
        });
      }

      line.addTo(map);
      featureLayers.push(line);

      if (el.tags?.ref && el.geometry.length >= 2) {
        const midIdx = Math.floor(el.geometry.length / 2);
        const midPt = el.geometry[midIdx];
        const icon = L.divIcon({
          html: `<div class="taxiway-label-marker">${el.tags.ref}</div>`,
          className: "",
          iconSize: null,
          iconAnchor: [0, 0],
        });
        const marker = L.marker([midPt.lat, midPt.lon], { icon, interactive: false, pane: "taxiwaysPane" });
        marker.addTo(map);
        featureLayers.push(marker);
      }
    });
};

const drawStands = (elements, map, featureLayers) => {
  elements
    .filter((el) => el.tags?.aeroway === "parking_position")
    .forEach((el) => {
      let latlng = null;

      if (el.type === "node") {
        latlng = [el.lat, el.lon];
      } else if (el.type === "way" && el.geometry?.length > 0) {
        const lats = el.geometry.map((g) => g.lat);
        const lons = el.geometry.map((g) => g.lon);
        latlng = [
          lats.reduce((a, b) => a + b, 0) / lats.length,
          lons.reduce((a, b) => a + b, 0) / lons.length,
        ];
      }

      if (!latlng) return;

      const label = el.tags?.ref || el.tags?.name || "";

      const icon = L.divIcon({
        html: `<div class="stand-marker">${label}</div>`,
        className: "",
        iconSize: null,
        iconAnchor: [0, 0],
      });

      const marker = L.marker(latlng, { icon, interactive: true, pane: "standsPane" });

      const tooltipParts = [];
      if (el.tags?.ref) tooltipParts.push(`<b>Stand:</b> ${el.tags.ref}`);
      if (el.tags?.name) tooltipParts.push(`<b>Name:</b> ${el.tags.name}`);
      if (el.tags?.["aeroway:type"]) tooltipParts.push(`<b>Type:</b> ${el.tags["aeroway:type"]}`);

      if (tooltipParts.length > 0) {
        marker.bindTooltip(tooltipParts.join("<br>"), {
          className: "stand-tooltip",
          sticky: false,
          direction: "top",
          offset: [0, -4],
        });
      }

      marker.addTo(map);
      featureLayers.push(marker);
    });
};

const drawGates = (elements, map, featureLayers) => {
  elements
    .filter((el) => el.tags?.aeroway === "gate")
    .forEach((el) => {
      if (el.type !== "node" || el.lat == null || el.lon == null) return;

      const label = el.tags?.ref || el.tags?.name || "?";

      const icon = L.divIcon({
        html: `<div class="gate-marker"><i class="fa-solid fa-door-open"></i><span>${label}</span></div>`,
        className: "",
        iconSize: null,
        iconAnchor: [0, 0],
      });

      const marker = L.marker([el.lat, el.lon], { icon, interactive: true, pane: "gatesPane" });

      const tooltipParts = [];
      if (el.tags?.ref) tooltipParts.push(`<b>Gate:</b> ${el.tags.ref}`);
      if (el.tags?.name) tooltipParts.push(`<b>Name:</b> ${el.tags.name}`);

      if (tooltipParts.length > 0) {
        marker.bindTooltip(tooltipParts.join("<br>"), {
          className: "gate-tooltip",
          sticky: false,
          direction: "top",
          offset: [0, -4],
        });
      }

      marker.addTo(map);
      featureLayers.push(marker);
    });
};

export const fetchAndDrawAirportFeatures = async (lat, lon, map, featureLayers, options = { taxiways: true, stands: true, gates: true }) => {
  const key = localCacheKey(lat, lon);

  if (featureCache.has(key)) {
    const elements = featureCache.get(key);
    if (options.taxiways) drawTaxiways(elements, map, featureLayers);
    if (options.stands) drawStands(elements, map, featureLayers);
    if (options.gates) drawGates(elements, map, featureLayers);
    return;
  }

  if (pendingFeatureRequests.has(key)) return;
  pendingFeatureRequests.add(key);

  try {
    const response = await api.get(`/api/airport-features?lat=${lat}&lon=${lon}`);
    const data = response.data;
    if (data.elements) {
      featureCache.set(key, data.elements);
      if (options.taxiways) drawTaxiways(data.elements, map, featureLayers);
      if (options.stands) drawStands(data.elements, map, featureLayers);
      if (options.gates) drawGates(data.elements, map, featureLayers);
    }
  } catch (err) {
    console.error(err);
  } finally {
    pendingFeatureRequests.delete(key);
  }
};