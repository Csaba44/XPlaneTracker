"""
CSABOLANTA Flight Tracker — CustomTkinter GUI
Matches exact flow of original CLI app, with sleek dark UI.
"""

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

# ── Logging ──────────────────────────────────────────────────────────────────
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

# ── CLI Arguments (parsed before GUI launches) ────────────────────────────────
_parser = argparse.ArgumentParser(description="CSABOLANTA Flight Tracker")
_parser.add_argument("--host",       type=str, default="127.0.0.1",
                     help="X-Plane UDP host IP (default: 127.0.0.1)")
_parser.add_argument("--dev",        action="store_true",
                     help="Use local dev API (xtracker.local:5173)")
_parser.add_argument("--no-webhook", action="store_true",
                     help="Disable Discord webhook notifications")
_parser.add_argument("--logout",     action="store_true",
                     help="Clear saved API token and exit")
ARGS = _parser.parse_args()

# Handle --logout immediately, before GUI starts
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

# ── Theme constants ───────────────────────────────────────────────────────────
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
                    icao = parts[1].strip('"')
                    a_type = parts[2].strip('"')
                    a_lat = float(parts[4].strip('"'))
                    a_lon = float(parts[5].strip('"'))
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
            logging.warning(f"Nearest airport {best_icao} is {best_dist_km:.1f}km away, exceeds {max_dist_km}km limit")
            return "N/A"

        return best_icao
    except Exception as e:
        logging.warning(f"Airport lookup failed: {e}")
        return "N/A"
    
# ── Providers (lazy import so missing deps don't crash GUI startup) ────────────
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
    """High-performance scrolling log — batches UI updates."""
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
        # keep last 400 lines
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

        # Logo
        ctk.CTkLabel(center, text="CSABOLANTA",
                     font=("Georgia", 32, "bold", "italic"),
                     text_color=WHITE).pack(pady=(0, 2))
        ctk.CTkLabel(center, text="X-PLANE & MSFS FLIGHT TRACKER",
                     font=("Consolas", 9, "bold"),
                     text_color=ACCENT).pack(pady=(0, 30))

        # Card
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

        # Pre-fill saved token
        TOKEN_FILE = ".xtracker_token"
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE) as f:
                saved = f.read().strip()
            self.key_entry.insert(0, saved)
            self.key_entry.configure(show="•")

    def _set_status(self, text, color):
        """Safe status update — no-ops if widget was already destroyed."""
        try:
            self.status_lbl.configure(text=text, text_color=color)
        except Exception:
            pass

    def _auth(self):
        token = self.key_entry.get().strip()
        if not token:
            self._set_status("Enter your API key.", YELLOW)
            return
        self._set_status("Verifying\u2026", MUTED)

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
#  SCREEN: SETUP (sim, simbrief, flight info)
# ═════════════════════════════════════════════════════════════════════════════

class SetupScreen(ctk.CTkFrame):
    def __init__(self, parent, user_name, on_start):
        super().__init__(parent, fg_color=BG)
        self.user_name = user_name
        self.on_start = on_start
        self._sb_data = {}
        self._build()

    def _build(self):
        # ── Header bar
        bar = ctk.CTkFrame(self, fg_color=SIDEBAR, height=52,
                           corner_radius=0, border_width=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        ctk.CTkLabel(bar, text="CSABOLANTA",
                     font=("Georgia", 16, "bold", "italic"),
                     text_color=WHITE).pack(side="left", padx=20)
        ctk.CTkLabel(bar, text=f"Welcome, {self.user_name}",
                     font=("Consolas", 11), text_color=ACCENT).pack(side="right", padx=20)

        # ── Two-column setup
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

        # ── Start button
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
                gen = d.get("general", {})
                ac  = d.get("aircraft", {})
                atc = d.get("atc", {})
                orig = d.get("origin", {})
                dest = d.get("destination", {})
                airline_code = gen.get("icao_airline", "")
                flight_no    = gen.get("flight_number", "")
                callsign     = atc.get("callsign") or f"{airline_code}{flight_no}"

                # Build full route string: ORIG route DEST
                orig_icao = orig.get("icao_code", "")
                dest_icao = dest.get("icao_code", "")
                raw_route = gen.get("route", "")
                full_route = " ".join(filter(None, [orig_icao, raw_route, dest_icao]))

                self._sb_data = {
                    "callsign": callsign,
                    "full_flight_number": f"{airline_code}{flight_no}",
                    "airline": airline_code,
                    "ac_type": ac.get("icaocode", ""),
                    "reg": ac.get("reg", ""),
                    "route": full_route,
                }
                for key, val in [
                    ("callsign", callsign),
                    ("flight_no", f"{airline_code}{flight_no}"),
                    ("reg", ac.get("reg", "")),
                    ("ac_type", ac.get("icaocode", "")),
                    ("route", full_route),
                ]:
                    self._entries[key].delete(0, "end")
                    self._entries[key].insert(0, val)
                self.sb_status.configure(text="✔ SimBrief data loaded", text_color=GREEN)
            else:
                self.sb_status.configure(text="Flight plan not found.", text_color=RED)
        except Exception as e:
            self.sb_status.configure(text=f"Error: {e}", text_color=RED)

    def _start(self):
        cfg = {
            "sim":       self.sim_var.get(),
            "host":      self.host_entry.get().strip() or "127.0.0.1",
            "callsign":  self._entries["callsign"].get().strip() or "unknown",
            "flight_no": self._entries["flight_no"].get().strip() or "unknown",
            "airline":   self._entries["airline"].get().strip() or "unknown",
            "reg":       self._entries["reg"].get().strip(),
            "ac_type":   self._entries["ac_type"].get().strip() or "unknown",
            "route":     self._entries["route"].get().strip(),
        }
        self.on_start(cfg)


# ═════════════════════════════════════════════════════════════════════════════
#  SCREEN: TRACKING
# ═════════════════════════════════════════════════════════════════════════════

class TrackingScreen(ctk.CTkFrame):
    def __init__(self, parent, cfg, token, api_base, user_name):
        super().__init__(parent, fg_color=BG)
        self.cfg = cfg
        self.token = token
        self.api_base = api_base
        self.user_name = user_name

        self.flight_path_data = {
            "metadata": {
                "callsign":              cfg["callsign"],
                "flight_number":         cfg["flight_no"],
                "airline":               cfg["airline"],
                "aircraft_registration": cfg["reg"],
                "aircraft_type":         cfg["ac_type"],
                "route":                 cfg.get("route", ""),
                "simulator":             cfg["sim"],
                "start_time":            datetime.now().isoformat(),
                "columns": ["timestamp", "lat", "lon", "alt", "speed"],
            },
            "path": [],
            "landings": [],
        }

        self.current_telemetry = {}
        self.landing_buffer = []
        self.buffer_lock = threading.Lock()
        self.buffer_timer = None
        self._tracking = True
        self._provider = None

        self._last_lat = self._last_lon = self._last_alt = self._last_speed = None
        self._last_log_time = 0
        self._last_autosave_time = time.time()

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("flights", exist_ok=True)
        self._base_filename = f"flights/flight_{cfg['callsign']}_{ts}"

        self._build()
        self._start_tracking()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        # Header
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

        # Body: sidebar + log
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Left sidebar
        sidebar = ctk.CTkFrame(body, fg_color=SIDEBAR, corner_radius=12,
                               border_width=1, border_color=BORDER, width=220)
        sidebar.pack(side="left", fill="y", padx=(0, 12))
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        # Right: telemetry + log
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        # Telemetry strip
        telem = ctk.CTkFrame(right, fg_color=SIDEBAR, corner_radius=10,
                              border_width=1, border_color=BORDER, height=70)
        telem.pack(fill="x", pady=(0, 10))
        telem.pack_propagate(False)
        self._build_telemetry(telem)

        # Log
        log_header = ctk.CTkFrame(right, fg_color="transparent", height=24)
        log_header.pack(fill="x")
        SectionLabel(log_header, "Live Log").pack(side="left")

        self.logbox = LogBox(right)
        self.logbox.pack(fill="both", expand=True)

        # Stop button
        GhostButton(self, text="■  Stop & Upload",
                    text_color=RED, border_color=RED,
                    hover_color="#2a1a1a",
                    command=self._stop).pack(fill="x", padx=16, pady=(8, 12))

    def _build_sidebar(self, parent):
        p = ctk.CTkFrame(parent, fg_color="transparent")
        p.pack(fill="both", expand=True, padx=14, pady=14)

        # Flight badge
        badge = ctk.CTkFrame(p, fg_color=CARD, corner_radius=8,
                              border_width=1, border_color=BORDER)
        badge.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(badge, text=self.cfg["callsign"],
                     font=("Georgia", 18, "bold"), text_color=WHITE).pack(pady=(10, 2))
        ctk.CTkLabel(badge, text=self.cfg["flight_no"],
                     font=("Consolas", 10), text_color=ACCENT).pack(pady=(0, 4))
        ctk.CTkLabel(badge, text=self.cfg["ac_type"],
                     font=("Consolas", 10), text_color=MUTED).pack(pady=(0, 4))

        # Show route in badge if available (truncated)
        route_str = self.cfg.get("route", "")
        if route_str:
            # Show just origin → destination if long, else full
            parts = route_str.split()
            if len(parts) >= 2:
                route_display = f"{parts[0]} → {parts[-1]}"
            else:
                route_display = route_str
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

    # ── Tracking core ─────────────────────────────────────────────────────────

    def _start_tracking(self):
        def worker():
            try:
                self._provider = load_provider(self.cfg["sim"], self.cfg["host"])
                self._provider.connect()
                self._update_status("● Tracking", GREEN)
                self._log(f"Connected to {self.cfg['sim']}")
                rpc.update(
                    callsign=self.cfg.get("callsign", ""),
                    aircraft=self.cfg.get("ac_type", ""),
                    registration=self.cfg.get("reg", ""),
                    state="Flying",
                )
            except Exception as e:
                self._update_status("✖ Connection failed", RED)
                self._log(f"ERROR: {e}")
                return

            # Landing monitor
            threading.Thread(target=self._landing_monitor, daemon=True).start()

            # Telemetry loop
            while self._tracking:
                try:
                    data = self._provider.get_telemetry()
                    self.current_telemetry = data

                    if "error" in data:
                        self._log(f"ERROR: {data['error']}")
                        time.sleep(2)
                        continue

                    lat  = data.get("lat")
                    lon  = data.get("lon")
                    alt  = data.get("alt")
                    speed = data.get("gs")
                    now  = time.time()

                    # Autosave every 2 min
                    if now - self._last_autosave_time > 120:
                        self._autosave()

                    # Update telemetry display (throttled via after)
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
                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                            self._log(
                                f"{ts}  LAT:{lat:.5f}  LON:{lon:.5f}  ALT:{alt}ft  GS:{safe_speed}kts"
                            )
                            self.flight_path_data["path"].append(
                                [round(now, 2), round(lat, 5), round(lon, 5), alt, safe_speed]
                            )
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
                        self._log(f"LANDING  {fpm:+.0f} FPM  {g_force:.2f}G")
                        self.flight_path_data["landings"].append({
                            "timestamp": round(time.time(), 2),
                            "fpm": round(fpm, 2),
                            "g_force": round(g_force, 2),
                            "lat": round(data.get("lat", 0), 5),
                            "lon": round(data.get("lon", 0), 5),
                        })
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
        arr_icao = get_nearest_airport_icao(last.get("lat", 0), last.get("lon", 0)) if last else "N/A"
        with self.buffer_lock:
            lines = [f"**{l['fpm']:.0f} fpm** | **{l['g']:.2f} g**" for l in self.landing_buffer]
            payload = {
                "embeds": [{
                    "title": f"{self.user_name} muro phral megérkezett, shavale!",
                    "description": "\n".join(lines),
                    "color": 0x38bdf8,
                    "fields": [
                        {"name": "Callsign",     "value": meta.get("callsign", "N/A"),               "inline": True},
                        {"name": "Flight No",    "value": meta.get("flight_number", "N/A"),          "inline": True},
                        {"name": "Registration", "value": meta.get("aircraft_registration") or "N/A","inline": True},
                        {"name": "Aircraft",     "value": meta.get("aircraft_type", "N/A"),          "inline": True},
                        {"name": "Simulator",    "value": meta.get("simulator", "N/A"),              "inline": True},
                        {"name": "Route",        "value": meta.get("route") or "N/A",                "inline": True},
                        {"name": "Arrival ICAO", "value": arr_icao,                                  "inline": True},
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

    # ── Stop & upload ─────────────────────────────────────────────────────────

    def _stop(self):
        self._tracking = False
        rpc.clear()
        if self._provider:
            try:
                self._provider.close()
            except Exception:
                pass

        final = f"{self._base_filename}.json.gz"
        autosave = f"{self._base_filename}_autosaved.json.gz"
        self._save_to_disk(final)
        self._log(f"Saved → {final}")

        if os.path.exists(autosave):
            try:
                os.remove(autosave)
            except Exception:
                pass

        self._update_status("Uploading…", YELLOW)

        # Find the App root to navigate back to setup after upload
        app_root = self.winfo_toplevel()
        UploadDialog(self, final, self.token, self.api_base,
                     self.cfg.get("reg", ""), self.cfg.get("ac_type", ""),
                     self.cfg.get("route", ""),
                     on_done=lambda: app_root.after(0, app_root._show_setup))


# ═════════════════════════════════════════════════════════════════════════════
#  DIALOG: UPLOAD
# ═════════════════════════════════════════════════════════════════════════════

class UploadDialog(ctk.CTkToplevel):
    def __init__(self, parent, filepath, token, api_base, reg, ac_type, route="", on_done=None):
        super().__init__(parent)
        self.filepath = filepath
        self.token = token
        self.api_base = api_base
        self.reg = reg
        self.ac_type = ac_type
        self.route = route
        self.on_done = on_done

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

# Replace with your own Discord application client ID from
# https://discord.com/developers/applications
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")

class RichPresenceManager:
    """Runs pypresence synchronously in its own thread with its own event loop.
    Uses nest_asyncio to prevent 'event loop already running' conflicts."""

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
        """Call fn(*args, **kwargs) whether it's sync or async."""
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
        print(f"[RPC] worker started, client_id={DISCORD_CLIENT_ID}")

        while self._running:
            # ── Connect ───────────────────────────────────────────────────
            if not self._connected:
                try:
                    self._rpc = DiscordPresence(DISCORD_CLIENT_ID)
                    self._call(self._rpc.connect)
                    self._connected = True
                    print("[RPC] connected to Discord!")
                    logging.info("Discord RPC connected.")
                    # Set idle presence immediately so Discord registers the app
                    try:
                        self._call(self._rpc.update,
                                   details="Repülőzzünk, shavale! 🍀",
                                   state="Waiting for flight…",
                                   large_image="csabolanta",
                                   large_text="CSABOLANTA Flight Tracker",
                                   instance=False)
                        print("[RPC] idle presence set")
                    except Exception as ie:
                        print(f"[RPC] idle presence failed: {ie}")
                except Exception as e:
                    print(f"[RPC] connect failed: {e}")
                    logging.warning(f"Discord RPC connect failed: {e}")
                    self._rpc = None
                    self._connected = False
                    time.sleep(15)
                    continue

            # ── Send pending update ───────────────────────────────────────
            with self._lock:
                kwargs = self._pending_update
                self._pending_update = None

            if kwargs is not None:
                try:
                    if kwargs == {}:
                        self._call(self._rpc.clear)
                        print("[RPC] presence cleared")
                    else:
                        self._call(self._rpc.update, **kwargs)
                        print(f"[RPC] presence updated OK: {kwargs.get('details')} / {kwargs.get('state')}")
                except Exception as e:
                    print(f"[RPC] update/clear failed: {e}")
                    logging.warning(f"Discord RPC update failed: {e}")
                    self._connected = False
                    self._rpc = None
                    continue

            time.sleep(0.5)

        # Cleanup
        try:
            if self._rpc and self._connected:
                self._call(self._rpc.close)
        except Exception:
            pass

    def update(self, callsign="", aircraft="", registration="", state="Flying"):
        if not _PYPRESENCE_AVAILABLE:
            return
        details = callsign if callsign and callsign != "unknown" else "In flight"
        parts = [p for p in [aircraft, registration] if p and p != "unknown"]
        ac_str = " · ".join(parts)
        with self._lock:
            self._pending_update = dict(
                details=details,
                state=ac_str if ac_str else "CSABOLANTA",
                large_image="csabolanta",
                large_text="CSABOLANTA Flight Tracker",
                start=int(time.time()),
                instance=False,
            )

    def clear(self):
        with self._lock:
            self._pending_update = None
        if not _PYPRESENCE_AVAILABLE or not self._connected or not self._rpc:
            return
        # Schedule a clear on next worker tick via sentinel
        with self._lock:
            self._pending_update = {}  # empty dict = clear signal

    def stop(self):
        self._running = False

# Global RPC instance — created once, shared across screens
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

        # Try to silently auth with saved token before showing login screen
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
        # Token invalid or network error — fall through to login
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


# ═════════════════════════════════════════════════════════════════════════════
#  ENTRY
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()