export const bearing = (lat1, lon1, lat2, lon2) => {
  const toRad = (d) => (d * Math.PI) / 180;
  const φ1 = toRad(lat1),
    φ2 = toRad(lat2);
  const Δλ = toRad(lon2 - lon1);
  const y = Math.sin(Δλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
};

export const destination = (lat, lon, brg, distM) => {
  const R = 6378137;
  const δ = distM / R;
  const θ = (brg * Math.PI) / 180;
  const φ1 = (lat * Math.PI) / 180;
  const λ1 = (lon * Math.PI) / 180;
  const φ2 = Math.asin(Math.sin(φ1) * Math.cos(δ) + Math.cos(φ1) * Math.sin(δ) * Math.cos(θ));
  const λ2 = λ1 + Math.atan2(Math.sin(θ) * Math.sin(δ) * Math.cos(φ1), Math.cos(δ) - Math.sin(φ1) * Math.sin(φ2));
  return [(φ2 * 180) / Math.PI, (((λ2 * 180) / Math.PI + 540) % 360) - 180];
};

export const distanceM = (lat1, lon1, lat2, lon2) => {
  const R = 6378137;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
};

export const offsetPolyline = (points, offsetM) => {
  return points.map((pt, i) => {
    const prev = points[Math.max(0, i - 1)];
    const next = points[Math.min(points.length - 1, i + 1)];
    const brg = bearing(prev[0], prev[1], next[0], next[1]);
    return destination(pt[0], pt[1], (brg + 90) % 360, offsetM);
  });
};

export const designatorToHeading = (des) => {
  if (!des) return null;
  const num = parseInt(des.replace(/[^0-9]/g, ""), 10);
  if (isNaN(num)) return null;
  return (num * 10) % 360;
};

export const angleDiff = (a, b) => {
  const d = Math.abs((a - b + 360) % 360);
  return d > 180 ? 360 - d : d;
};

export const toleranceForGS = (gs) => {
  if (gs < 50) return 0.000015;
  if (gs < 150) return 0.000015;
  if (gs < 300) return 0.00007;
  return 0.00015;
};

export const rdpPerpendicularDist = (point, lineStart, lineEnd) => {
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

export const rdpAdaptive = (points, tolerances) => {
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

export const nearestPointOnPolyline = (latlng, points) => {
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