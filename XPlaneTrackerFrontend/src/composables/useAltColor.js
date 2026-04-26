export const FR24_STOPS = [
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

export const altToColor = (ft) => {
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