import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import json, time, os, gzip, threading, requests, argparse, logging, re
from datetime import datetime, timezone
from dotenv import load_dotenv
import sys

try:
    from pypresence import Presence as DiscordPresence
    _PYPRESENCE_AVAILABLE = True
except ImportError:
    _PYPRESENCE_AVAILABLE = False
    logging.warning("pypresence not installed — Discord Rich Presence disabled.")

logging.basicConfig(
    filename="log.txt",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def clean_text(text):
    return re.sub(r"\[.*?\]", "", text)

def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

try:
    load_dotenv(resource_path(".env"))
except Exception as e:
    logging.error(f"Dotenv load error: {e}")

_parser = argparse.ArgumentParser(description="CSABOLANTA Flight Tracker")
_parser.add_argument("--host",       type=str, default="127.0.0.1")
_parser.add_argument("--dev",        action="store_true")
_parser.add_argument("--no-webhook", action="store_true")
_parser.add_argument("--logout",     action="store_true")
ARGS = _parser.parse_args()

if ARGS.logout:
    if os.path.exists(".xtracker_token"):
        os.remove(".xtracker_token")
        print("Logged out successfully.")
    else:
        print("Not logged in.")
    sys.exit(0)

API_BASE_URL = (
    "http://xtracker.local:5173/api" if ARGS.dev
    else "https://api.csabolanta.hu/api"
)

BG          = "#0b0e14"
SIDEBAR     = "#151921"
CARD        = "#1c222d"
CARD_HOVER  = "#252d3a"
ACCENT      = "#38bdf8"
ACCENT_DIM  = "#1e6a8a"
BORDER      = "#2d3544"
MUTED       = "#94a3b8"
WHITE       = "#e2e8f0"
RED         = "#f87171"
GREEN       = "#4ade80"
YELLOW      = "#fbbf24"

_airports_cache: list | None = None


def get_aircraft_name(icao_code: str) -> str:
    if not icao_code or icao_code.strip().lower() in ("", "unknown"):
        return icao_code
    try:
        import csv
        r = requests.get(
            "https://raw.githubusercontent.com/jpatokal/openflights/master/data/planes.dat",
            timeout=8,
        )
        if r.status_code == 200:
            reader = csv.reader(r.text.splitlines())
            for row in reader:
                if len(row) >= 3 and row[2].strip().upper() == icao_code.strip().upper():
                    name = row[0].strip()
                    return name if name else icao_code
    except Exception as e:
        logging.warning(f"get_aircraft_name failed for '{icao_code}': {e}")
    return icao_code


def get_airline_name(code: str) -> str:
    if not code or code.lower() == "unknown":
        return code
    try:
        r = requests.get(
            "https://raw.githubusercontent.com/npow/airline-codes/master/airlines.json",
            timeout=5,
        )
        if r.status_code == 200:
            for airline in r.json():
                if airline.get("iata") == code or airline.get("icao") == code:
                    return airline.get("name", code)
    except Exception:
        pass
    return code


def get_nearest_airport_icao(lat: float, lon: float, max_dist_km: float = 10.0) -> str:
    import math
    global _airports_cache
    try:
        if _airports_cache is None:
            r = requests.get(
                "https://davidmegginson.github.io/ourairports-data/airports.csv",
                timeout=10,
            )
            if r.status_code != 200:
                return "N/A"
            _airports_cache = []
            for line in r.text.splitlines()[1:]:
                parts = line.split(",")
                if len(parts) < 6:
                    continue
                try:
                    icao   = parts[1].strip('"')
                    a_type = parts[2].strip('"')
                    a_lat  = float(parts[4].strip('"'))
                    a_lon  = float(parts[5].strip('"'))
                except (ValueError, IndexError):
                    continue
                if a_type not in ("large_airport", "medium_airport", "small_airport"):
                    continue
                if icao and len(icao) >= 3:
                    _airports_cache.append((icao, a_lat, a_lon))

        best_icao, best_dist_km = "N/A", float("inf")
        R = 6371.0
        for icao, a_lat, a_lon in _airports_cache:
            dlat = math.radians(a_lat - lat)
            dlon = math.radians(a_lon - lon)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(a_lat)) * math.sin(dlon/2)**2
            dist_km = 2 * R * math.asin(math.sqrt(a))
            if dist_km < best_dist_km:
                best_dist_km, best_icao = dist_km, icao

        if best_dist_km > max_dist_km:
            return "N/A"
        return best_icao
    except Exception as e:
        logging.warning(f"Airport lookup failed: {e}")
        return "N/A"


def load_provider(sim_choice, host):
    if sim_choice == "X-Plane":
        from xp_provider import XPlaneProvider
        return XPlaneProvider(ip=host)
    else:
        from msfs_provider import MSFSProvider
        return MSFSProvider()


# ═════════════════════════════════════════════════════════════════════════════
#  HELPER WIDGETS
# ═════════════════════════════════════════════════════════════════════════════

class Divider(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, height=1, fg_color=BORDER, **kwargs)
        self.pack_propagate(False)


class SectionLabel(ctk.CTkLabel):
    def __init__(self, parent, text, **kwargs):
        super().__init__(
            parent, text=text.upper(),
            font=("Consolas", 9, "bold"),
            text_color=MUTED,
            **kwargs,
        )


class AccentButton(ctk.CTkButton):
    def __init__(self, parent, **kwargs):
        kwargs.setdefault("height", 34)
        kwargs.setdefault("font", ("Consolas", 12, "bold"))
        kwargs.setdefault("text_color", "#0b0e14")
        kwargs.setdefault("corner_radius", 6)
        kwargs.setdefault("fg_color", ACCENT)
        kwargs.setdefault("hover_color", ACCENT_DIM)
        super().__init__(parent, **kwargs)


class GhostButton(ctk.CTkButton):
    def __init__(self, parent, **kwargs):
        kwargs.setdefault("height", 30)
        kwargs.setdefault("font", ("Consolas", 11))
        kwargs.setdefault("text_color", MUTED)
        kwargs.setdefault("corner_radius", 6)
        kwargs.setdefault("border_color", BORDER)
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("hover_color", CARD_HOVER)
        kwargs.setdefault("border_width", 1)
        super().__init__(parent, **kwargs)


class StyledEntry(ctk.CTkEntry):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=CARD,
            border_color=BORDER,
            text_color=WHITE,
            placeholder_text_color=MUTED,
            font=("Consolas", 12),
            corner_radius=6,
            height=34,
            **kwargs,
        )


class LogBox(ctk.CTkTextbox):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=CARD,
            text_color=MUTED,
            font=("Consolas", 11),
            corner_radius=6,
            border_width=1,
            border_color=BORDER,
            wrap="none",
            **kwargs,
        )
        self.configure(state="disabled")
        self._pending = []
        self._lock = threading.Lock()
        self._flush_scheduled = False

    def append(self, line: str):
        with self._lock:
            self._pending.append(line)
        if not self._flush_scheduled:
            self._flush_scheduled = True
            self.after(80, self._flush)

    def _flush(self):
        with self._lock:
            lines, self._pending = self._pending, []
        self._flush_scheduled = False
        if not lines:
            return
        self.configure(state="normal")
        for line in lines:
            self.insert("end", line + "\n")
        total = int(self.index("end-1c").split(".")[0])
        if total > 400:
            self.delete("1.0", f"{total-400}.0")
        self.see("end")
        self.configure(state="disabled")


class StatusDot(ctk.CTkLabel):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, text="●", font=("Consolas", 14),
                         text_color=MUTED, **kwargs)

    def set_color(self, color):
        self.configure(text_color=color)


class LandingCard(ctk.CTkFrame):
    def __init__(self, parent, fpm, g_force, **kwargs):
        super().__init__(parent, fg_color=CARD, corner_radius=8,
                         border_width=1, border_color=BORDER, **kwargs)
        col = GREEN if abs(fpm) < 200 else YELLOW if abs(fpm) < 400 else RED
        ctk.CTkLabel(self, text=f"{fpm:+.0f} fpm",
                     font=("Consolas", 14, "bold"),
                     text_color=col).pack(side="left", padx=12, pady=8)
        ctk.CTkLabel(self, text=f"{g_force:.2f} G",
                     font=("Consolas", 12),
                     text_color=MUTED).pack(side="right", padx=12)


# ═════════════════════════════════════════════════════════════════════════════
#  SCREEN: LOGIN
# ═════════════════════════════════════════════════════════════════════════════

class LoginScreen(ctk.CTkFrame):
    def __init__(self, parent, on_success):
        super().__init__(parent, fg_color=BG)
        self.on_success = on_success
        self._build()

    def _build(self):
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(center, text="CSABOLANTA",
                     font=("Georgia", 32, "bold", "italic"),
                     text_color=WHITE).pack(pady=(0, 2))
        ctk.CTkLabel(center, text="X-PLANE & MSFS FLIGHT TRACKER",
                     font=("Consolas", 9, "bold"),
                     text_color=ACCENT).pack(pady=(0, 30))

        card = ctk.CTkFrame(center, fg_color=SIDEBAR, corner_radius=12,
                             border_width=1, border_color=BORDER, width=380)
        card.pack(padx=0, pady=0)
        card.pack_propagate(False)
        card.configure(height=200)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=24)

        SectionLabel(inner, "API Key").pack(anchor="w", pady=(0, 6))
        self.key_entry = StyledEntry(inner, placeholder_text="Paste your API key…",
                                     show="•", width=330)
        self.key_entry.pack(fill="x")

        self.status_lbl = ctk.CTkLabel(inner, text="",
                                        font=("Consolas", 11),
                                        text_color=RED)
        self.status_lbl.pack(pady=(8, 0))

        AccentButton(inner, text="Authenticate →",
                     command=self._auth).pack(fill="x", pady=(12, 0))

        TOKEN_FILE = ".xtracker_token"
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE) as f:
                saved = f.read().strip()
            self.key_entry.insert(0, saved)
            self.key_entry.configure(show="•")

    def _set_status(self, text, color):
        try:
            self.status_lbl.configure(text=text, text_color=color)
        except Exception:
            pass

    def _auth(self):
        token = self.key_entry.get().strip()
        if not token:
            self._set_status("Enter your API key.", YELLOW)
            return
        self._set_status("Verifying…", MUTED)

        def worker():
            try:
                r = requests.get(
                    f"{API_BASE_URL}/user",
                    headers={"Authorization": f"Bearer {token}",
                             "Accept": "application/json"},
                    timeout=8,
                )
                if r.status_code == 200:
                    user = r.json()
                    with open(".xtracker_token", "w") as f:
                        f.write(token)
                    self.after(0, self.on_success, token, user.get("name", "Pilot"), API_BASE_URL)
                else:
                    self.after(0, self._set_status, "Invalid API key.", RED)
            except Exception as e:
                self.after(0, self._set_status, f"Server error: {e}", RED)

        threading.Thread(target=worker, daemon=True).start()


# ═════════════════════════════════════════════════════════════════════════════
#  SCREEN: SETUP
# ═════════════════════════════════════════════════════════════════════════════

class SetupScreen(ctk.CTkFrame):
    def __init__(self, parent, user_name, on_start):
        super().__init__(parent, fg_color=BG)
        self.user_name = user_name
        self.on_start = on_start
        self._sb_data = {}
        self._sb_raw = {}
        self._sb_resolving = 0
        self._build()

    def _build(self):
        bar = ctk.CTkFrame(self, fg_color=SIDEBAR, height=52,
                           corner_radius=0, border_width=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkLabel(bar, text="CSABOLANTA",
                     font=("Georgia", 16, "bold", "italic"),
                     text_color=WHITE).pack(side="left", padx=20)
        ctk.CTkLabel(bar, text=f"Welcome, {self.user_name}",
                     font=("Consolas", 11), text_color=ACCENT).pack(side="right", padx=20)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=40, pady=30)

        left = ctk.CTkFrame(body, fg_color=SIDEBAR, corner_radius=12,
                            border_width=1, border_color=BORDER)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))

        right = ctk.CTkFrame(body, fg_color=SIDEBAR, corner_radius=12,
                             border_width=1, border_color=BORDER)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        self._build_sim_col(left)
        self._build_flight_col(right)

        AccentButton(self, text="▶  Start Tracking",
                     command=self._start, height=44,
                     font=("Consolas", 14, "bold")).pack(
            fill="x", padx=40, pady=(0, 30))

    def _build_sim_col(self, parent):
        p = ctk.CTkFrame(parent, fg_color="transparent")
        p.pack(fill="both", expand=True, padx=20, pady=20)

        SectionLabel(p, "Simulator").pack(anchor="w", pady=(0, 8))
        self.sim_var = ctk.StringVar(value="X-Plane")
        for sim in ("X-Plane", "MSFS 2024"):
            rb = ctk.CTkRadioButton(p, text=sim, variable=self.sim_var, value=sim,
                                    font=("Consolas", 12),
                                    text_color=WHITE,
                                    fg_color=ACCENT,
                                    border_color=BORDER)
            rb.pack(anchor="w", pady=3)

        Divider(p).pack(fill="x", pady=14)

        SectionLabel(p, "Host IP (X-Plane)").pack(anchor="w", pady=(0, 6))
        self.host_entry = StyledEntry(p, placeholder_text="127.0.0.1")
        self.host_entry.insert(0, ARGS.host)
        self.host_entry.pack(fill="x")

        Divider(p).pack(fill="x", pady=14)

        SectionLabel(p, "SimBrief Pilot ID").pack(anchor="w", pady=(0, 6))
        sb_row = ctk.CTkFrame(p, fg_color="transparent")
        sb_row.pack(fill="x")
        self.sb_entry = StyledEntry(sb_row, placeholder_text="Optional…")
        self.sb_entry.pack(side="left", fill="x", expand=True)

        saved_sb = ""
        if os.path.exists(".simbrief_id"):
            with open(".simbrief_id") as f:
                saved_sb = f.read().strip()
        if saved_sb:
            self.sb_entry.insert(0, saved_sb)

        GhostButton(sb_row, text="Fetch", width=64,
                    command=self._fetch_sb).pack(side="left", padx=(6, 0))

        self.sb_status = ctk.CTkLabel(p, text="", font=("Consolas", 10),
                                       text_color=MUTED)
        self.sb_status.pack(anchor="w", pady=(4, 0))

    def _build_flight_col(self, parent):
        p = ctk.CTkFrame(parent, fg_color="transparent")
        p.pack(fill="both", expand=True, padx=20, pady=20)

        SectionLabel(p, "Flight Details").pack(anchor="w", pady=(0, 12))

        fields = [
            ("Callsign",      "callsign"),
            ("Flight Number", "flight_no"),
            ("Airline",       "airline"),
            ("Registration",  "reg"),
            ("Aircraft Type", "ac_type"),
            ("Route",         "route"),
        ]
        self._entries = {}
        for label, key in fields:
            SectionLabel(p, label).pack(anchor="w", pady=(0, 4))
            e = StyledEntry(p, placeholder_text="—")
            e.pack(fill="x", pady=(0, 8))
            self._entries[key] = e

    def _fetch_sb(self):
        sb_id = self.sb_entry.get().strip()
        if not sb_id:
            self.sb_status.configure(text="Enter a Pilot ID first.", text_color=YELLOW)
            return
        self.sb_status.configure(text="Fetching…", text_color=MUTED)
        self.update()
        try:
            with open(".simbrief_id", "w") as f:
                f.write(sb_id)
            url = f"https://www.simbrief.com/api/xml.fetcher.php?userid={sb_id}&json=1"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                d = r.json()
                gen  = d.get("general", {})
                ac   = d.get("aircraft", {})
                atc  = d.get("atc", {})
                orig = d.get("origin", {})
                dest = d.get("destination", {})
                times = d.get("times", {})
                weights = d.get("weights", {})
                fuel = d.get("fuel", {})

                airline_code = gen.get("icao_airline", "")
                flight_no    = gen.get("flight_number", "")
                callsign     = atc.get("callsign") or f"{airline_code}{flight_no}"
                ac_type_raw  = ac.get("icaocode", "")

                orig_icao  = orig.get("icao_code", "")
                dest_icao  = dest.get("icao_code", "")
                raw_route  = gen.get("route", "")
                full_route = " ".join(filter(None, [orig_icao, raw_route, dest_icao]))

                def _int(v):
                    try:
                        return int(v) if v else None
                    except (TypeError, ValueError):
                        return None

                self._sb_raw = {
                    "eobt":               _int(times.get("sched_out")),
                    "sched_out":          _int(times.get("sched_out")),
                    "sched_off":          _int(times.get("sched_off")),
                    "sched_on":           _int(times.get("sched_on")),
                    "sched_in":           _int(times.get("sched_in")),
                    "sched_block_sec":    _int(times.get("sched_block")),
                    "est_block_sec":      _int(times.get("est_block")),
                    "planned_route":      full_route,
                    "planned_oew":        _int(weights.get("oew")),
                    "planned_zfw":        _int(weights.get("est_zfw")),
                    "planned_tow":        _int(weights.get("est_tow")),
                    "planned_ldw":        _int(weights.get("est_ldw")),
                    "planned_block_fuel": _int(fuel.get("plan_ramp")),
                    "planned_takeoff_fuel": _int(fuel.get("plan_takeoff")),
                    "planned_landing_fuel": _int(fuel.get("plan_landing")),
                    "planned_distance_nm": _int(gen.get("air_distance")),
                }

                self._sb_data = {
                    "callsign":           callsign,
                    "full_flight_number": f"{airline_code}{flight_no}",
                    "airline":            airline_code,
                    "ac_type":            ac_type_raw,
                    "reg":                ac.get("reg", ""),
                    "route":              full_route,
                    "dep":                orig_icao,
                    "arr":                dest_icao,
                }

                for key, val in [
                    ("callsign",  callsign),
                    ("flight_no", f"{airline_code}{flight_no}"),
                    ("reg",       ac.get("reg", "")),
                    ("route",     full_route),
                    ("ac_type",   ac_type_raw),
                    ("airline",   airline_code),
                ]:
                    self._entries[key].delete(0, "end")
                    self._entries[key].insert(0, val)

                if airline_code:
                    self.sb_status.configure(text="✔ SimBrief loaded, resolving airline…", text_color=GREEN)
                    def resolve_airline(code=airline_code):
                        full_name = get_airline_name(code)
                        self._sb_data["airline"] = full_name
                        def update():
                            self._entries["airline"].delete(0, "end")
                            self._entries["airline"].insert(0, full_name)
                            self.sb_status.configure(text="✔ SimBrief data loaded", text_color=GREEN)
                        self.after(0, update)
                    threading.Thread(target=resolve_airline, daemon=True).start()
                else:
                    self.sb_status.configure(text="✔ SimBrief data loaded", text_color=GREEN)
            else:
                self.sb_status.configure(text="Flight plan not found.", text_color=RED)
        except Exception as e:
            self.sb_status.configure(text=f"Error: {e}", text_color=RED)

    def _sb_resolve_done(self, field, value):
        if field is not None and value is not None:
            self._entries[field].delete(0, "end")
            self._entries[field].insert(0, value)
        self._sb_resolving -= 1
        if self._sb_resolving <= 0:
            self.sb_status.configure(text="✔ SimBrief data loaded", text_color=GREEN)

    def _start(self):
        ac_type_raw = self._entries["ac_type"].get().strip() or "unknown"

        cfg = {
            "sim":          self.sim_var.get(),
            "host":         self.host_entry.get().strip() or "127.0.0.1",
            "callsign":     self._entries["callsign"].get().strip() or "unknown",
            "flight_no":    self._entries["flight_no"].get().strip() or "unknown",
            "airline":      self._entries["airline"].get().strip() or "unknown",
            "reg":          self._entries["reg"].get().strip(),
            "ac_type":      ac_type_raw,
            "ac_type_full": "",
            "route":        self._entries["route"].get().strip(),
            "dep":          self._sb_data.get("dep", ""),
            "arr":          self._sb_data.get("arr", ""),
            "sb_raw":       self._sb_raw if self._sb_raw else None,
        }

        def resolve_and_start():
            cfg["ac_type_full"] = get_aircraft_name(ac_type_raw)
            self.after(0, self.on_start, cfg)

        threading.Thread(target=resolve_and_start, daemon=True).start()


# ═════════════════════════════════════════════════════════════════════════════
#  DIALOG: STOP
# ═════════════════════════════════════════════════════════════════════════════

class StopDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_upload, on_save_only, on_cancel):
        super().__init__(parent)
        self.on_upload    = on_upload
        self.on_save_only = on_save_only
        self.on_cancel    = on_cancel

        self.title("Flight Stopped")
        self.geometry("380x210")
        self.resizable(False, False)
        self.configure(fg_color=SIDEBAR)

        self.after(100, self.grab_set)
        self.after(150, self.lift)
        self.after(150, self.focus_force)

        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Flight stopped.",
                     font=("Georgia", 16, "bold"),
                     text_color=WHITE).pack(pady=(28, 4))
        ctk.CTkLabel(self, text="What would you like to do?",
                     font=("Consolas", 11),
                     text_color=MUTED).pack(pady=(0, 20))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack()
        AccentButton(row, text="Upload now",  command=self._upload).pack(side="left", padx=6)
        GhostButton(row,  text="Save only",   command=self._save).pack(side="left", padx=6)
        GhostButton(row,  text="Cancel",      command=self._cancel).pack(side="left", padx=6)

    def _upload(self):
        self.destroy()
        if self.on_upload:
            self.on_upload()

    def _save(self):
        self.destroy()
        if self.on_save_only:
            self.on_save_only()

    def _cancel(self):
        self.destroy()
        if self.on_cancel:
            self.on_cancel()


# ═════════════════════════════════════════════════════════════════════════════
#  SCREEN: TRACKING
# ═════════════════════════════════════════════════════════════════════════════

class TrackingScreen(ctk.CTkFrame):
    def __init__(self, parent, cfg, token, api_base, user_name):
        super().__init__(parent, fg_color=BG)
        self.cfg       = cfg
        self.token     = token
        self.api_base  = api_base
        self.user_name = user_name

        from version import APP_VERSION, SCHEMA_VERSION
        from flight_state import FlightStateMachine
        from flight_aggregator import FlightAggregator

        meta = {
            "schema_version":        SCHEMA_VERSION,
            "app_version":           APP_VERSION,
            "callsign":              cfg["callsign"],
            "flight_number":         cfg["flight_no"],
            "airline":               cfg["airline"],
            "aircraft_registration": cfg["reg"],
            "aircraft_type":         cfg["ac_type"],
            "route":                 cfg.get("route", ""),
            "simulator":             cfg["sim"],
            "start_time":            datetime.now().isoformat(),
            "columns": ["timestamp", "lat", "lon", "alt", "speed",
                        "alt_baro", "heading_true", "heading_mag"],
        }

        if cfg.get("sb_raw"):
            meta["simbrief"] = cfg["sb_raw"]

        self.flight_path_data = {
            "metadata": meta,
            "path":     [],
            "landings": [],
            "events":   [],
            "phases":   [],
        }

        self._state_machine = FlightStateMachine()
        self._state_machine.set_replay_callback(self._on_replay_detected)
        self._aggregator = FlightAggregator()

        self.current_telemetry = {}
        self.landing_buffer = []
        self.buffer_lock = threading.Lock()
        self.buffer_timer = None
        self._tracking = True
        self._provider = None
        self._stop_dialog_open = False

        self._last_lat = self._last_lon = self._last_alt = self._last_speed = None
        self._last_log_time = 0
        self._last_autosave_time = time.time()

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("flights", exist_ok=True)
        self._base_filename = f"flights/flight_{cfg['callsign']}_{ts}"

        self._build()
        self._start_tracking()

    def _on_replay_detected(self):
        from notifications import notify
        notify("Replay Detected",
               "Replay mode active — your flight is still recording but won't reflect real piloting.")

    def _build(self):
        bar = ctk.CTkFrame(self, fg_color=SIDEBAR, height=52, corner_radius=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        left_bar = ctk.CTkFrame(bar, fg_color="transparent")
        left_bar.pack(side="left", padx=16, pady=8)
        ctk.CTkLabel(left_bar, text="CSABOLANTA",
                     font=("Georgia", 15, "bold", "italic"),
                     text_color=WHITE).pack(side="left")
        ctk.CTkLabel(left_bar, text=" / TRACKING",
                     font=("Consolas", 11), text_color=ACCENT).pack(side="left")
        if ARGS.dev:
            ctk.CTkLabel(left_bar, text=" [DEV]",
                         font=("Consolas", 11, "bold"),
                         text_color=YELLOW).pack(side="left")
        if ARGS.no_webhook:
            ctk.CTkLabel(left_bar, text=" [NO WEBHOOK]",
                         font=("Consolas", 10),
                         text_color=MUTED).pack(side="left")

        right_bar = ctk.CTkFrame(bar, fg_color="transparent")
        right_bar.pack(side="right", padx=16)
        self.status_dot = StatusDot(right_bar)
        self.status_dot.pack(side="left", padx=(0, 6))
        self.status_lbl = ctk.CTkLabel(right_bar, text="Connecting…",
                                        font=("Consolas", 11), text_color=MUTED)
        self.status_lbl.pack(side="left")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)

        sidebar = ctk.CTkFrame(body, fg_color=SIDEBAR, corner_radius=12,
                               border_width=1, border_color=BORDER, width=220)
        sidebar.pack(side="left", fill="y", padx=(0, 12))
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        telem = ctk.CTkFrame(right, fg_color=SIDEBAR, corner_radius=10,
                              border_width=1, border_color=BORDER, height=70)
        telem.pack(fill="x", pady=(0, 10))
        telem.pack_propagate(False)
        self._build_telemetry(telem)

        log_header = ctk.CTkFrame(right, fg_color="transparent", height=24)
        log_header.pack(fill="x")
        SectionLabel(log_header, "Live Log").pack(side="left")

        self.logbox = LogBox(right)
        self.logbox.pack(fill="both", expand=True)

        GhostButton(self, text="■  Stop & Upload",
                    text_color=RED, border_color=RED,
                    hover_color="#2a1a1a",
                    command=self._stop).pack(fill="x", padx=16, pady=(8, 12))

    def _build_sidebar(self, parent):
        p = ctk.CTkFrame(parent, fg_color="transparent")
        p.pack(fill="both", expand=True, padx=14, pady=14)

        badge = ctk.CTkFrame(p, fg_color=CARD, corner_radius=8,
                              border_width=1, border_color=BORDER)
        badge.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(badge, text=self.cfg["callsign"],
                     font=("Georgia", 18, "bold"), text_color=WHITE).pack(pady=(10, 2))
        ctk.CTkLabel(badge, text=self.cfg["flight_no"],
                     font=("Consolas", 10), text_color=ACCENT).pack(pady=(0, 4))
        ctk.CTkLabel(badge, text=self.cfg["ac_type"],
                     font=("Consolas", 10), text_color=MUTED).pack(pady=(0, 4))

        route_str = self.cfg.get("route", "")
        if route_str:
            parts = route_str.split()
            route_display = f"{parts[0]} → {parts[-1]}" if len(parts) >= 2 else route_str
            ctk.CTkLabel(badge, text=route_display,
                         font=("Consolas", 9), text_color=MUTED).pack(pady=(0, 10))
        else:
            badge.pack_configure(pady=(0, 14))

        Divider(p).pack(fill="x", pady=(0, 12))

        SectionLabel(p, "Landings").pack(anchor="w", pady=(0, 8))
        self.landings_frame = ctk.CTkScrollableFrame(p, fg_color="transparent",
                                                      height=240,
                                                      scrollbar_button_color=BORDER)
        self.landings_frame.pack(fill="x")

        self._no_landing_lbl = ctk.CTkLabel(
            self.landings_frame,
            text="Waiting for touchdown…",
            font=("Consolas", 10),
            text_color=MUTED,
        )
        self._no_landing_lbl.pack(pady=10)

        Divider(p).pack(fill="x", pady=12)

        SectionLabel(p, "Stats").pack(anchor="w", pady=(0, 8))
        self._stat_labels = {}
        for key in ("Points recorded", "Landings", "Autosaves"):
            row = ctk.CTkFrame(p, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=key, font=("Consolas", 10),
                         text_color=MUTED).pack(side="left")
            lbl = ctk.CTkLabel(row, text="0", font=("Consolas", 10, "bold"),
                               text_color=WHITE)
            lbl.pack(side="right")
            self._stat_labels[key] = lbl

        self._autosave_count = 0

    def _build_telemetry(self, parent):
        fields = [("LAT", "lat"), ("LON", "lon"), ("ALT", "alt"), ("GS", "gs")]
        self._telem_labels = {}
        inner = ctk.CTkFrame(parent, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=16)
        for i, (label, key) in enumerate(fields):
            col = ctk.CTkFrame(inner, fg_color="transparent")
            col.grid(row=0, column=i*2, padx=(0, 4), pady=12, sticky="ns")
            ctk.CTkLabel(col, text=label, font=("Consolas", 9, "bold"),
                         text_color=MUTED).pack()
            lbl = ctk.CTkLabel(col, text="—", font=("Consolas", 14, "bold"),
                               text_color=WHITE)
            lbl.pack()
            self._telem_labels[key] = lbl
            if i < len(fields)-1:
                sep = ctk.CTkFrame(inner, fg_color=BORDER, width=1)
                sep.grid(row=0, column=i*2+1, sticky="ns", pady=12, padx=8)

        for c in range(len(fields)*2-1):
            inner.columnconfigure(c, weight=1 if c % 2 == 0 else 0)

    def _start_tracking(self):
        def worker():
            try:
                self._provider = load_provider(self.cfg["sim"], self.cfg["host"])
                self._provider.connect()
                self._update_status("● Tracking", GREEN)
                self._log(f"Connected to {self.cfg['sim']}")
                rpc.update(
                    callsign=self.cfg.get("callsign", ""),
                    aircraft=self.cfg.get("ac_type_full") or self.cfg.get("ac_type", ""),
                    registration=self.cfg.get("reg", ""),
                    airline=self.cfg.get("airline", ""),
                    dep=self.cfg.get("dep", ""),
                    arr=self.cfg.get("arr", ""),
                    state="Flying",
                )
            except Exception as e:
                self._update_status("✖ Connection failed", RED)
                self._log(f"ERROR: {e}")
                return

            threading.Thread(target=self._landing_monitor, daemon=True).start()

            while self._tracking:
                try:
                    data = self._provider.get_telemetry()
                    self.current_telemetry = data

                    if "error" in data:
                        self._log(f"ERROR: {data['error']}")
                        time.sleep(2)
                        continue

                    lat   = data.get("lat")
                    lon   = data.get("lon")
                    alt   = data.get("alt")
                    speed = data.get("gs")
                    now   = time.time()

                    self._aggregator.tick(data, now)

                    self._state_machine.tick(data, now)
                    new_events = self._state_machine.get_and_clear_events()
                    if new_events:
                        self.flight_path_data["events"].extend(new_events)
                    new_phases = self._state_machine.get_and_clear_phases()
                    if new_phases:
                        self.flight_path_data["phases"].extend(new_phases)

                    if now - self._last_autosave_time > 120:
                        self._autosave()

                    self.after(0, self._update_telem, lat, lon, alt, speed)

                    if lat is not None and lon is not None:
                        should_record = False
                        state_changed = (lat != self._last_lat or lon != self._last_lon
                                         or alt != self._last_alt or speed != self._last_speed)
                        safe_speed = speed or 0

                        if safe_speed == 0:
                            if state_changed:
                                should_record = True
                        else:
                            interval = 0.5 if safe_speed > 350 else 0.25 if safe_speed >= 250 else 0.1
                            if (now - self._last_log_time) >= interval:
                                should_record = True

                        if should_record:
                            alt_baro     = data.get("alt_baro")
                            heading_true = data.get("heading_true")
                            heading_mag  = data.get("heading_mag")

                            ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                            self._log(
                                f"{ts_str}  LAT:{lat:.5f}  LON:{lon:.5f}  ALT:{alt}ft  GS:{safe_speed}kts"
                            )
                            self.flight_path_data["path"].append([
                                round(now, 2),
                                round(lat, 5),
                                round(lon, 5),
                                alt,
                                safe_speed,
                                int(alt_baro) if alt_baro is not None else None,
                                round(heading_true, 1) if heading_true is not None else None,
                                round(heading_mag, 1) if heading_mag is not None else None,
                            ])
                            self._last_lat, self._last_lon = lat, lon
                            self._last_alt, self._last_speed = alt, speed
                            self._last_log_time = now

                            self.after(0, self._update_stats)

                    time.sleep(0.1)
                except Exception as e:
                    logging.error(f"Telemetry loop error: {e}")
                    time.sleep(0.5)

        threading.Thread(target=worker, daemon=True).start()

    def _landing_monitor(self):
        was_on_ground = True
        while self._tracking:
            try:
                data = self.current_telemetry
                on_ground = data.get("on_ground")
                if on_ground is not None:
                    if not was_on_ground and on_ground:
                        fpm     = data.get("fpm", 0)
                        g_force = data.get("gforce", 0)
                        lat     = data.get("lat", 0)
                        lon     = data.get("lon", 0)
                        pitch   = data.get("pitch")
                        roll    = data.get("roll")
                        ias     = data.get("ias")
                        gs_val  = data.get("gs")
                        hdg     = data.get("heading_true")

                        self._log(f"LANDING  {fpm:+.0f} FPM  {g_force:.2f}G")

                        landing_entry = {
                            "timestamp": round(time.time(), 2),
                            "fpm":       round(fpm, 2),
                            "g_force":   round(g_force, 2),
                            "lat":       round(lat, 5),
                            "lon":       round(lon, 5),
                        }
                        if pitch is not None:
                            landing_entry["pitch"] = round(pitch, 1)
                        if roll is not None:
                            landing_entry["roll"] = round(roll, 1)
                        if ias is not None:
                            landing_entry["ias"] = int(ias)
                        if gs_val is not None:
                            landing_entry["gs"] = int(gs_val)

                        def enrich_landing(entry=landing_entry, cur_lat=lat, cur_lon=lon, cur_hdg=hdg):
                            import airport_db as adb
                            ap = adb.nearest_airport(cur_lat, cur_lon, max_dist_km=15.0)
                            if ap:
                                entry["airport_icao"] = ap["icao"]
                                entry["airport_name"] = ap["name"]
                                if cur_hdg is not None:
                                    rwy_ident, offset_m = adb.nearest_runway_with_threshold(
                                        ap["icao"], cur_lat, cur_lon, cur_hdg
                                    )
                                    if rwy_ident:
                                        entry["runway_ident"] = rwy_ident
                                    if offset_m is not None:
                                        entry["touchdown_offset_m"] = offset_m
                            entry["rollout_m"] = self._measure_rollout()

                        threading.Thread(target=enrich_landing, daemon=True).start()

                        self.flight_path_data["landings"].append(landing_entry)
                        self.after(0, self._add_landing_card, fpm, g_force)

                        with self.buffer_lock:
                            self.landing_buffer.append({"fpm": fpm, "g": g_force})
                            if self.buffer_timer is None:
                                self.buffer_timer = threading.Timer(10.0, self._send_webhook)
                                self.buffer_timer.start()

                    was_on_ground = on_ground
            except Exception as e:
                logging.error(f"Landing monitor error: {e}")
            time.sleep(0.1)

    def _measure_rollout(self) -> int | None:
        start = time.time()
        gs_samples = []
        low_speed_start = None
        while self._tracking:
            data = self.current_telemetry
            gs = data.get("gs") or 0
            on_ground = data.get("on_ground", True)
            if not on_ground:
                break
            gs_samples.append(gs)
            if gs < 30:
                if low_speed_start is None:
                    low_speed_start = time.time()
                elif time.time() - low_speed_start >= 5.0:
                    break
            else:
                low_speed_start = None
            if time.time() - start > 180:
                break
            time.sleep(0.1)
        if not gs_samples:
            return None
        avg_gs_kts = sum(gs_samples) / len(gs_samples)
        duration_s = len(gs_samples) * 0.1
        rollout_nm = avg_gs_kts * (duration_s / 3600.0)
        return int(rollout_nm * 1852)

    def _add_landing_card(self, fpm, g_force):
        if self._no_landing_lbl:
            self._no_landing_lbl.destroy()
            self._no_landing_lbl = None
        card = LandingCard(self.landings_frame, fpm, g_force)
        card.pack(fill="x", pady=(0, 4))

    def _update_telem(self, lat, lon, alt, speed):
        def fmt(v, decimals=5):
            return f"{v:.{decimals}f}" if v is not None else "—"
        self._telem_labels["lat"].configure(text=fmt(lat, 5))
        self._telem_labels["lon"].configure(text=fmt(lon, 5))
        self._telem_labels["alt"].configure(text=fmt(alt, 0) if alt is not None else "—")
        self._telem_labels["gs"].configure(text=f"{int(speed or 0)} kts")

    def _update_status(self, text, color):
        self.after(0, lambda: (
            self.status_lbl.configure(text=text, text_color=color),
            self.status_dot.set_color(color),
        ))

    def _update_stats(self):
        pts = len(self.flight_path_data["path"])
        ldg = len(self.flight_path_data["landings"])
        self._stat_labels["Points recorded"].configure(text=str(pts))
        self._stat_labels["Landings"].configure(text=str(ldg))
        self._stat_labels["Autosaves"].configure(text=str(self._autosave_count))

    def _log(self, msg: str):
        logging.info(clean_text(msg))
        self.logbox.append(msg)

    def _autosave(self):
        path = f"{self._base_filename}_autosaved.json.gz"
        self._save_to_disk(path)
        self._autosave_count += 1
        self._log("AUTOSAVE — data synced to disk")
        self.after(0, self._update_stats)
        self._last_autosave_time = time.time()

    def _save_to_disk(self, path):
        try:
            with gzip.open(path, "wt", encoding="utf-8") as f:
                json.dump(self.flight_path_data, f, separators=(",", ":"))
        except Exception as e:
            self._log(f"Disk save error: {e}")

    def _send_webhook(self):
        if ARGS.no_webhook:
            with self.buffer_lock:
                self.landing_buffer = []
                self.buffer_timer = None
            return
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            return
        meta = self.flight_path_data.get("metadata", {})
        last = self.flight_path_data["landings"][-1] if self.flight_path_data["landings"] else {}
        arr_icao = last.get("airport_icao") or get_nearest_airport_icao(last.get("lat", 0), last.get("lon", 0))
        with self.buffer_lock:
            lines = [f"**{l['fpm']:.0f} fpm** | **{l['g']:.2f} g**" for l in self.landing_buffer]
            payload = {
                "embeds": [{
                    "title": f"{self.user_name} muro phral megérkezett, shavale!",
                    "description": "\n".join(lines),
                    "color": 0x38bdf8,
                    "fields": [
                        {"name": "Callsign",     "value": meta.get("callsign", "N/A"),                "inline": True},
                        {"name": "Flight No",    "value": meta.get("flight_number", "N/A"),           "inline": True},
                        {"name": "Registration", "value": meta.get("aircraft_registration") or "N/A", "inline": True},
                        {"name": "Aircraft",     "value": meta.get("aircraft_type", "N/A"),           "inline": True},
                        {"name": "Simulator",    "value": meta.get("simulator", "N/A"),               "inline": True},
                        {"name": "Route",        "value": meta.get("route") or "N/A",                 "inline": True},
                        {"name": "Arrival ICAO", "value": arr_icao,                                   "inline": True},
                    ],
                    "footer": {"text": "csabolanta.hu"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }]
            }
            try:
                requests.post(webhook_url, json=payload, timeout=5)
            except Exception as e:
                self._log(f"Webhook error: {e}")
            self.landing_buffer = []
            self.buffer_timer = None

    def _finalize_metadata(self):
        now = time.time()
        self._state_machine.finalize(now)
        new_phases = self._state_machine.get_and_clear_phases()
        if new_phases:
            self.flight_path_data["phases"].extend(new_phases)

        sched_in = None
        sb = self.flight_path_data["metadata"].get("simbrief")
        if sb:
            sched_in = sb.get("sched_in")

        agg = self._aggregator.finalize(sched_in=sched_in)
        meta = self.flight_path_data["metadata"]
        if agg.get("timing"):
            meta["timing"] = agg["timing"]
        if agg.get("summary"):
            meta["summary"] = agg["summary"]
        if agg.get("weights"):
            meta["weights"] = agg["weights"]
        if agg.get("fuel"):
            meta["fuel"] = agg["fuel"]

    def _do_stop_tracking(self):
        self._tracking = False
        rpc.set_idle()
        if self._provider:
            try:
                self._provider.close()
            except Exception:
                pass
        self._finalize_metadata()
        self._update_status("Stopped", MUTED)

    def _stop(self):
        if self._stop_dialog_open:
            return
        self._stop_dialog_open = True

        final   = f"{self._base_filename}.json.gz"
        autosave = f"{self._base_filename}_autosaved.json.gz"

        def on_upload():
            self._stop_dialog_open = False
            self._do_stop_tracking()
            self._save_to_disk(final)
            self._log(f"Saved → {final}")
            if os.path.exists(autosave):
                try:
                    os.remove(autosave)
                except Exception:
                    pass
            self._update_status("Uploading…", YELLOW)
            app_root = self.winfo_toplevel()
            UploadDialog(self, final, self.token, self.api_base,
                         self.cfg.get("reg", ""), self.cfg.get("ac_type", ""),
                         self.cfg.get("route", ""),
                         on_done=lambda: app_root.after(0, app_root._show_setup))

        def on_save():
            self._stop_dialog_open = False
            self._do_stop_tracking()
            self._save_to_disk(final)
            self._log(f"Saved → {final}")
            if os.path.exists(autosave):
                try:
                    os.remove(autosave)
                except Exception:
                    pass
            app_root = self.winfo_toplevel()
            app_root.after(0, app_root._show_setup)

        def on_cancel():
            self._stop_dialog_open = False

        StopDialog(self, on_upload=on_upload, on_save_only=on_save, on_cancel=on_cancel)


# ═════════════════════════════════════════════════════════════════════════════
#  DIALOG: UPLOAD
# ═════════════════════════════════════════════════════════════════════════════

class UploadDialog(ctk.CTkToplevel):
    def __init__(self, parent, filepath, token, api_base, reg, ac_type, route="", on_done=None):
        super().__init__(parent)
        self.filepath = filepath
        self.token    = token
        self.api_base = api_base
        self.reg      = reg
        self.ac_type  = ac_type
        self.route    = route
        self.on_done  = on_done

        self.title("Upload Flight")
        self.geometry("420x260")
        self.resizable(False, False)
        self.configure(fg_color=SIDEBAR)

        self.after(100, self.grab_set)
        self.after(150, self.lift)
        self.after(150, self.focus_force)

        self._build()
        self._upload()

    def _build(self):
        ctk.CTkLabel(self, text="Uploading Flight",
                     font=("Georgia", 16, "bold"), text_color=WHITE).pack(pady=(24, 4))
        ctk.CTkLabel(self, text=os.path.basename(self.filepath),
                     font=("Consolas", 10), text_color=MUTED).pack()

        self.progress = ctk.CTkProgressBar(self, fg_color=CARD,
                                            progress_color=ACCENT, height=6,
                                            corner_radius=3)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=32, pady=(20, 8))
        self.progress.start()

        self.status_lbl = ctk.CTkLabel(self, text="Connecting…",
                                        font=("Consolas", 11), text_color=MUTED)
        self.status_lbl.pack()

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=(20, 0))

    def _upload(self):
        def worker():
            try:
                with open(self.filepath, "rb") as f:
                    files = {"flight_file": (os.path.basename(self.filepath), f, "application/gzip")}
                    data = {}
                    if self.reg:     data["aircraft_registration"] = self.reg
                    if self.ac_type: data["aircraft_type"] = self.ac_type
                    if self.route:   data["route"] = self.route
                    r = requests.post(
                        f"{self.api_base}/flights", files=files, data=data,
                        headers={"Authorization": f"Bearer {self.token}",
                                 "Accept": "application/json"},
                        timeout=30,
                    )
                if r.status_code == 201:
                    self.after(0, self._success)
                else:
                    self.after(0, self._fail, f"HTTP {r.status_code}")
            except Exception as e:
                self.after(0, self._fail, str(e))

        threading.Thread(target=worker, daemon=True).start()

    def _success(self):
        self.progress.stop()
        self.progress.set(1)
        self.status_lbl.configure(text="✔ Upload successful!", text_color=GREEN)

        AccentButton(self.btn_frame, text="Delete local file",
                     command=self._delete_and_close).pack(side="left", padx=6)
        GhostButton(self.btn_frame, text="Keep file",
                    command=self._keep_and_close).pack(side="left", padx=6)

    def _keep_and_close(self):
        self.destroy()
        if self.on_done:
            self.on_done()

    def _fail(self, reason):
        self.progress.stop()
        self.status_lbl.configure(text=f"✖ Upload failed: {reason}", text_color=RED)
        GhostButton(self.btn_frame, text="Close", command=self.destroy).pack()

    def _delete_and_close(self):
        try:
            os.remove(self.filepath)
        except Exception:
            pass
        self.destroy()
        if self.on_done:
            self.on_done()


# ═════════════════════════════════════════════════════════════════════════════
#  DISCORD RICH PRESENCE
# ═════════════════════════════════════════════════════════════════════════════

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")


class RichPresenceManager:
    def __init__(self):
        self._rpc = None
        self._running = False
        self._connected = False
        self._pending_update = None
        self._lock = threading.Lock()
        self._thread = None

    def start(self):
        if not _PYPRESENCE_AVAILABLE:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True, name="rpc-thread")
        self._thread.start()

    @staticmethod
    def _call(fn, *args, **kwargs):
        import asyncio, inspect
        result = fn(*args, **kwargs)
        if inspect.isawaitable(result):
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(result)
            finally:
                loop.close()
        return result

    def _worker(self):
        while self._running:
            if not self._connected:
                try:
                    self._rpc = DiscordPresence(DISCORD_CLIENT_ID)
                    self._call(self._rpc.connect)
                    self._connected = True
                    logging.info("Discord RPC connected.")
                    try:
                        rpc.set_idle()
                    except Exception as ie:
                        logging.warning(f"RPC idle presence failed: {ie}")
                except Exception as e:
                    logging.warning(f"Discord RPC connect failed: {e}")
                    self._rpc = None
                    self._connected = False
                    time.sleep(15)
                    continue

            with self._lock:
                kwargs = self._pending_update
                self._pending_update = None

            if kwargs is not None:
                try:
                    if kwargs == {}:
                        self._call(self._rpc.clear)
                    else:
                        self._call(self._rpc.update, **kwargs)
                except Exception as e:
                    logging.warning(f"Discord RPC update failed: {e}")
                    self._connected = False
                    self._rpc = None
                    continue

            time.sleep(0.5)

        try:
            if self._rpc and self._connected:
                self._call(self._rpc.close)
        except Exception:
            pass

    def update(self, callsign="", aircraft="", registration="", airline="", dep="", arr="", state="Flying"):
        if not _PYPRESENCE_AVAILABLE:
            return
        route_part = f"  |  {dep} → {arr}" if dep and arr else ""
        details = (
            f"{callsign}{route_part}"
            if callsign and callsign != "unknown"
            else f"In flight{route_part}"
        )
        parts = [p for p in [airline, aircraft, registration] if p and p != "unknown"]
        state_str = " · ".join(parts) if parts else "CSABOLANTA"

        with self._lock:
            self._pending_update = dict(
                details=details,
                state=state_str,
                large_image="csabolanta",
                large_text="CSABOLANTA Flight Tracker",
                start=int(time.time()),
                instance=False,
            )

    def set_idle(self):
        with self._lock:
            self._pending_update = dict(
                details="Repülőzzünk, shavale! 🍀",
                state="Waiting for flight…",
                large_image="csabolanta",
                large_text="CSABOLANTA Flight Tracker",
                instance=False,
            )

    def clear(self):
        with self._lock:
            self._pending_update = {}

    def stop(self):
        self._running = False


rpc = RichPresenceManager()


# ═════════════════════════════════════════════════════════════════════════════
#  APP ROOT
# ═════════════════════════════════════════════════════════════════════════════

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CSABOLANTA Flight Tracker")
        self.geometry("1100x720")
        self.minsize(900, 620)
        self.configure(fg_color=BG)

        self._token = None
        self._api_base = None
        self._user_name = None
        self._current_screen = None

        rpc.start()

        saved_token = ""
        if os.path.exists(".xtracker_token"):
            with open(".xtracker_token") as f:
                saved_token = f.read().strip()

        if saved_token:
            self._show_splash("Signing in…")
            threading.Thread(target=self._try_auto_auth,
                             args=(saved_token,), daemon=True).start()
        else:
            self._show_login()

    def _show_splash(self, message=""):
        self._clear()
        frame = ctk.CTkFrame(self, fg_color=BG)
        frame.pack(fill="both", expand=True)
        center = ctk.CTkFrame(frame, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(center, text="CSABOLANTA",
                     font=("Georgia", 32, "bold", "italic"),
                     text_color=WHITE).pack(pady=(0, 6))
        ctk.CTkLabel(center, text=message,
                     font=("Consolas", 11),
                     text_color=MUTED).pack()
        self._current_screen = frame

    def _try_auto_auth(self, token):
        try:
            r = requests.get(
                f"{API_BASE_URL}/user",
                headers={"Authorization": f"Bearer {token}",
                         "Accept": "application/json"},
                timeout=8,
            )
            if r.status_code == 200:
                user = r.json()
                self._token = token
                self._api_base = API_BASE_URL
                self._user_name = user.get("name", "Pilot")
                self.after(0, self._show_setup)
                return
        except Exception:
            pass
        self.after(0, self._show_login)

    def _clear(self):
        if self._current_screen:
            self._current_screen.destroy()

    def _show_login(self):
        self._clear()
        screen = LoginScreen(self, self._on_auth)
        screen.pack(fill="both", expand=True)
        self._current_screen = screen

    def _on_auth(self, token, user_name, api_base):
        self._token = token
        self._api_base = api_base
        self._user_name = user_name
        self._show_setup()

    def _show_setup(self):
        self._clear()
        screen = SetupScreen(self, self._user_name, self._on_start)
        screen.pack(fill="both", expand=True)
        self._current_screen = screen

    def _on_start(self, cfg):
        self._clear()
        screen = TrackingScreen(self, cfg, self._token, self._api_base, self._user_name)
        screen.pack(fill="both", expand=True)
        self._current_screen = screen


if __name__ == "__main__":
    app = App()
    app.mainloop()
