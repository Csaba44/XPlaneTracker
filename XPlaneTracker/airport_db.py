import os
import csv
import math
import logging
import requests

_CACHE_DIR = os.path.join("flights", ".cache")
_AIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
_RUNWAYS_URL = "https://davidmegginson.github.io/ourairports-data/runways.csv"

_airports: list = None
_runways: list = None


def _load_airports():
    global _airports
    if _airports is not None:
        return
    os.makedirs(_CACHE_DIR, exist_ok=True)
    cache = os.path.join(_CACHE_DIR, "airports.csv")
    if not os.path.exists(cache):
        try:
            r = requests.get(_AIRPORTS_URL, timeout=15)
            if r.status_code == 200:
                with open(cache, "w", encoding="utf-8") as f:
                    f.write(r.text)
        except Exception as e:
            logging.warning(f"airport_db: download airports.csv failed: {e}")
            _airports = []
            return
    _airports = []
    try:
        with open(cache, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    _airports.append({
                        "id": row.get("id", "").strip(),
                        "icao": row.get("ident", "").strip().strip('"'),
                        "lat": float(row["latitude_deg"]),
                        "lon": float(row["longitude_deg"]),
                        "name": row.get("name", "").strip().strip('"'),
                        "iso_country": row.get("iso_country", "").strip().strip('"'),
                    })
                except (ValueError, KeyError):
                    continue
    except Exception as e:
        logging.warning(f"airport_db: read airports.csv failed: {e}")
        _airports = []


def _load_runways():
    global _runways
    if _runways is not None:
        return
    os.makedirs(_CACHE_DIR, exist_ok=True)
    cache = os.path.join(_CACHE_DIR, "runways.csv")
    if not os.path.exists(cache):
        try:
            r = requests.get(_RUNWAYS_URL, timeout=15)
            if r.status_code == 200:
                with open(cache, "w", encoding="utf-8") as f:
                    f.write(r.text)
        except Exception as e:
            logging.warning(f"airport_db: download runways.csv failed: {e}")
            _runways = []
            return
    _runways = []
    try:
        with open(cache, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    def _f(k):
                        v = row.get(k, "").strip()
                        return float(v) if v else None
                    _runways.append({
                        "airport_id": row.get("airport_id", "").strip(),
                        "le_ident": row.get("le_ident", "").strip(),
                        "he_ident": row.get("he_ident", "").strip(),
                        "le_lat": _f("le_latitude_deg"),
                        "le_lon": _f("le_longitude_deg"),
                        "he_lat": _f("he_latitude_deg"),
                        "he_lon": _f("he_longitude_deg"),
                        "le_hdg": _f("le_heading_degT"),
                        "he_hdg": _f("he_heading_degT"),
                    })
                except (ValueError, KeyError):
                    continue
    except Exception as e:
        logging.warning(f"airport_db: read runways.csv failed: {e}")
        _runways = []


def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(max(0, a)))


def nearest_airport(lat: float, lon: float, max_dist_km: float = 15.0) -> dict | None:
    _load_airports()
    best = None
    best_dist = float("inf")
    for ap in _airports:
        d = _haversine_m(lat, lon, ap["lat"], ap["lon"])
        if d < best_dist:
            best_dist = d
            best = ap
    if best and best_dist <= max_dist_km * 1000:
        return best
    return None


def nearest_runway_with_threshold(airport_icao: str, lat: float, lon: float, heading_true: float):
    _load_airports()
    _load_runways()

    airport_id = None
    for ap in _airports:
        if ap["icao"] == airport_icao:
            airport_id = ap["id"]
            break
    if not airport_id:
        return None, None

    best_rwy = None
    best_ident = None
    best_end = None
    best_hdg_diff = float("inf")

    for rwy in _runways:
        if rwy["airport_id"] != airport_id:
            continue
        for end in ("le", "he"):
            hdg = rwy[f"{end}_hdg"]
            if hdg is None:
                continue
            diff = abs(((heading_true - hdg) + 180) % 360 - 180)
            if diff < best_hdg_diff:
                best_hdg_diff = diff
                best_rwy = rwy
                best_ident = rwy[f"{end}_ident"]
                best_end = end

    if not best_rwy or best_hdg_diff > 45:
        return None, None

    thr_lat = best_rwy[f"{best_end}_lat"]
    thr_lon = best_rwy[f"{best_end}_lon"]
    if thr_lat is None or thr_lon is None:
        return best_ident, None

    offset_m = int(_haversine_m(lat, lon, thr_lat, thr_lon))
    return best_ident, offset_m


def airport_full_name(icao: str) -> str | None:
    _load_airports()
    for ap in _airports:
        if ap["icao"] == icao:
            return ap["name"]
    return None


def country_flag_emoji(icao: str) -> str:
    _load_airports()
    for ap in _airports:
        if ap["icao"] == icao:
            iso = ap.get("iso_country", "")
            if len(iso) == 2 and iso.isalpha():
                return chr(ord(iso[0].upper()) + 127397) + chr(ord(iso[1].upper()) + 127397)
    return ""
