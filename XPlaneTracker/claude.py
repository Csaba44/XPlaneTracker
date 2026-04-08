"""
FlightTracker - Lightweight X-Plane flight logger
Connects to X-Plane via XPlaneConnectX, logs position, detects landings,
records G-forces and FPM, saves to JSON on flight end.
"""

import json
import math
import os
import queue
import socket
import threading
import time
import tkinter as tk
from datetime import datetime, timezone
from tkinter import font as tkfont
from tkinter import ttk

# ── local import ─────────────────────────────────────────────────────────────
from XPlaneConnectX import XPlaneConnectX

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════
XP_IP   = "127.0.0.1"
XP_PORT = 49000

CONNECT_RETRY_SEC   = 5       # seconds between reconnect attempts
POSITION_INTERVAL   = 0.5    # seconds between position log entries
FAST_POLL_HZ        = 10     # subscription frequency for fast datarefs
SLOW_POLL_HZ        = 2      # subscription frequency for slower datarefs

# Landing detection thresholds
LANDING_MIN_FPM     = -50    # below this we're descending "for real" (fpm, negative = down)
LANDING_GEAR_THRESH = 0.5    # y_agl metres — below this = on ground
AIRBORNE_MIN_AGL    = 5.0    # must be above this AGL (m) before we can log a landing

# Position logging: only log if moved at least this many metres or X seconds elapsed
POS_MIN_DIST_M      = 50
POS_FORCE_SEC       = 30

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def ts_now():
    return datetime.now(timezone.utc).isoformat()

def fpm_to_rating(fpm):
    fpm = abs(fpm)
    if fpm < 60:   return "Butter 🧈"
    if fpm < 180:  return "Smooth ✅"
    if fpm < 360:  return "Firm 🟡"
    if fpm < 600:  return "Hard 🟠"
    return "Crash 💥"

def g_to_rating(g):
    if g < 1.3:  return "Soft"
    if g < 1.6:  return "Moderate"
    if g < 2.0:  return "Hard"
    return "Severe"


# ══════════════════════════════════════════════════════════════════════════════
# FLIGHT DATA MODEL
# ══════════════════════════════════════════════════════════════════════════════

class FlightData:
    def __init__(self):
        self.reset()

    def reset(self):
        self.flight_info = {
            "callsign":    "",
            "aircraft":    "",
            "airline":     "",
            "flight_number": "",
        }
        self.landings: list[dict] = []
        self.position_updates: list[dict] = []
        self._last_pos = None
        self._last_pos_time = 0.0

    def add_position(self, lat, lon, alt_msl_m, alt_agl_m, gs_ms, timestamp=None):
        now = time.monotonic()
        t   = timestamp or ts_now()

        # distance filter
        if self._last_pos:
            dist = haversine_m(self._last_pos[0], self._last_pos[1], lat, lon)
            elapsed = now - self._last_pos_time
            if dist < POS_MIN_DIST_M and elapsed < POS_FORCE_SEC:
                return False

        entry = {
            "timestamp":  t,
            "lat":        round(lat, 6),
            "lon":        round(lon, 6),
            "alt_msl_ft": round(alt_msl_m * 3.28084, 0),
            "alt_agl_ft": round(alt_agl_m * 3.28084, 1),
            "gs_kts":     round(gs_ms * 1.94384, 1),
        }
        self.position_updates.append(entry)
        self._last_pos      = (lat, lon)
        self._last_pos_time = now
        return True

    def add_landing(self, lat, lon, alt_msl_m, fpm, g_nrml):
        entry = {
            "timestamp":  ts_now(),
            "lat":        round(lat, 6),
            "lon":        round(lon, 6),
            "alt_msl_ft": round(alt_msl_m * 3.28084, 0),
            "fpm":        round(fpm, 1),
            "fpm_rating": fpm_to_rating(fpm),
            "g_nrml":     round(g_nrml, 3),
            "g_rating":   g_to_rating(g_nrml),
        }
        self.landings.append(entry)
        return entry

    def to_dict(self):
        return {
            "flight_info":       self.flight_info,
            "landings":          self.landings,
            "position_updates":  self.position_updates,
        }


# ══════════════════════════════════════════════════════════════════════════════
# SIMULATOR CONNECTION THREAD
# ══════════════════════════════════════════════════════════════════════════════

FAST_DREFS = [
    ("sim/flightmodel/forces/g_nrml",           FAST_POLL_HZ),  # G-force downward
    ("sim/flightmodel/position/y_agl",           FAST_POLL_HZ),  # AGL metres
    ("sim/flightmodel/position/vh_ind_fpm",      FAST_POLL_HZ),  # VVI fpm
    ("sim/flightmodel/position/groundspeed",     FAST_POLL_HZ),  # ground speed m/s
    ("sim/flightmodel/position/indicated_airspeed", SLOW_POLL_HZ),  # IAS kts
    ("sim/flightmodel/position/local_vy",        FAST_POLL_HZ),  # inertial vy (m/s up)
]

class SimWorker(threading.Thread):
    """
    Background thread that:
      1. Connects to X-Plane (retries on failure)
      2. Subscribes to datarefs
      3. Polls position & detects landings
      4. Pushes events to a queue consumed by the GUI
    """

    def __init__(self, flight_data: FlightData, event_q: queue.Queue):
        super().__init__(daemon=True)
        self.flight_data = flight_data
        self.event_q     = event_q
        self._stop_evt   = threading.Event()

        self.xpc: XPlaneConnectX | None = None
        self.connected = False

        # landing state machine
        self._was_airborne   = False
        self._airborne_max_agl = 0.0
        self._min_fpm_during_approach = 0.0   # most negative seen before touchdown
        self._max_g_during_touch      = 1.0

        # for peak G window
        self._touch_time  = None
        self._post_touch_g: list[float] = []
        self._landing_lat = None
        self._landing_lon = None
        self._landing_alt = None

    def stop(self):
        self._stop_evt.set()

    def _log(self, msg: str, level="INFO"):
        self.event_q.put({"type": "log", "level": level, "msg": msg})

    def _try_connect(self) -> bool:
        try:
            xpc = XPlaneConnectX(ip=XP_IP, port=XP_PORT)
            xpc.subscribeDREFs(FAST_DREFS)
            time.sleep(1.2)  # allow first packets to arrive
            # Test: read y_agl — if None, sim not sending
            val = xpc.current_dref_values["sim/flightmodel/position/y_agl"]["value"]
            if val is None:
                raise ConnectionError("Simulator not responding")
            self.xpc = xpc
            return True
        except Exception as e:
            self._log(f"Connection failed: {e}", "WARN")
            return False

    def _get_dref(self, key: str):
        try:
            return self.xpc.current_dref_values[key]["value"]
        except Exception:
            return None

    def _read_aircraft_icao(self) -> str:
        """Read aircraft ICAO string via getDREF (one-time)."""
        try:
            # acf_ICAO is a string dref — XPlaneConnectX getDREF returns float for numeric
            # We'll use it as a fallback display only; string drefs aren't supported via RREF
            # so we leave this as a note: getPOSI doesn't expose it.
            # The user can fill it in manually; we'll try anyway and return empty on fail.
            return ""
        except Exception:
            return ""

    def run(self):
        self._log("SimWorker started, attempting connection …")
        while not self._stop_evt.is_set():
            if not self.connected:
                ok = self._try_connect()
                if ok:
                    self.connected = True
                    self.event_q.put({"type": "connected"})
                    self._log("✈  Connected to X-Plane!", "OK")
                else:
                    self.event_q.put({"type": "disconnected"})
                    self._log(f"Retrying in {CONNECT_RETRY_SEC}s …", "WARN")
                    for _ in range(CONNECT_RETRY_SEC * 4):
                        if self._stop_evt.is_set():
                            return
                        time.sleep(0.25)
                    continue

            # ── main poll loop ────────────────────────────────────────────
            try:
                self._poll()
            except Exception as e:
                self._log(f"Poll error: {e} — reconnecting …", "ERR")
                self.connected = False
                self.xpc = None
                self.event_q.put({"type": "disconnected"})

            time.sleep(0.1)   # 10 Hz poll ceiling — easy on CPU

    def _poll(self):
        y_agl   = self._get_dref("sim/flightmodel/position/y_agl")
        g_nrml  = self._get_dref("sim/flightmodel/forces/g_nrml")
        fpm     = self._get_dref("sim/flightmodel/position/vh_ind_fpm")
        gs_ms   = self._get_dref("sim/flightmodel/position/groundspeed")
        ias_kts = self._get_dref("sim/flightmodel/position/indicated_airspeed")

        if y_agl is None:
            return

        on_ground = y_agl < LANDING_GEAR_THRESH

        # ── position update ───────────────────────────────────────────────
        # Use getPOSI only for lat/lon/alt (blocking call, but cheap)
        # We throttle this to once per POSITION_INTERVAL at most
        now = time.monotonic()
        if not hasattr(self, "_last_posi_time"):
            self._last_posi_time = 0.0

        if now - self._last_posi_time >= POSITION_INTERVAL:
            self._last_posi_time = now
            try:
                pos = self.xpc.getPOSI()
                lat, lon, alt_msl = pos[0], pos[1], pos[2]
                agl = y_agl if y_agl is not None else 0.0
                gs  = gs_ms if gs_ms is not None else 0.0
                added = self.flight_data.add_position(lat, lon, alt_msl, agl, gs)
                if added:
                    self._log(
                        f"Position  {lat:.4f}°N {lon:.4f}°E  "
                        f"ALT {alt_msl*3.28084:.0f}ft  AGL {agl*3.28084:.0f}ft  "
                        f"GS {gs*1.94384:.0f}kts"
                    )
                    self.event_q.put({
                        "type": "position",
                        "lat": lat, "lon": lon,
                        "alt_ft": alt_msl * 3.28084,
                        "agl_ft": agl * 3.28084,
                        "gs_kts": gs * 1.94384,
                        "ias_kts": ias_kts or 0.0,
                        "fpm": fpm or 0.0,
                        "g": g_nrml or 1.0,
                    })
                    # cache for landing record
                    self._landing_lat  = lat
                    self._landing_lon  = lon
                    self._landing_alt  = alt_msl
            except Exception as e:
                self._log(f"getPOSI error: {e}", "WARN")

        # ── landing detection state machine ───────────────────────────────
        if g_nrml is None or fpm is None:
            return

        agl_ft = y_agl * 3.28084

        if not on_ground:
            self._was_airborne = True
            self._airborne_max_agl = max(self._airborne_max_agl, agl_ft)
            # track minimum (most negative) fpm in last 30ft
            if agl_ft < 200 and fpm < self._min_fpm_during_approach:
                self._min_fpm_during_approach = fpm
            self._touch_time  = None
            self._post_touch_g = []

        else:  # on ground
            if self._was_airborne and self._airborne_max_agl > AIRBORNE_MIN_AGL * 3.28084:
                # touchdown just happened (first ground frame after flight)
                if self._touch_time is None:
                    self._touch_time = now
                    self._max_g_during_touch = g_nrml
                    landing_fpm = self._min_fpm_during_approach if self._min_fpm_during_approach < -10 else fpm
                    self._log(
                        f"🛬 Landing detected!  FPM={landing_fpm:.0f}  G={g_nrml:.2f}  "
                        f"({fpm_to_rating(landing_fpm)})",
                        "OK"
                    )
                    # save with last known position
                    if self._landing_lat is not None:
                        entry = self.flight_data.add_landing(
                            self._landing_lat, self._landing_lon, self._landing_alt or 0,
                            landing_fpm, g_nrml
                        )
                        self.event_q.put({"type": "landing", "data": entry})

                    # reset for next flight segment
                    self._was_airborne = False
                    self._airborne_max_agl = 0.0
                    self._min_fpm_during_approach = 0.0

                else:
                    # track peak G for a couple of seconds post-touch
                    if now - self._touch_time < 3.0:
                        self._max_g_during_touch = max(self._max_g_during_touch, g_nrml)


# ══════════════════════════════════════════════════════════════════════════════
# GUI
# ══════════════════════════════════════════════════════════════════════════════

DARK_BG    = "#0d1117"
PANEL_BG   = "#161b22"
BORDER     = "#30363d"
ACCENT     = "#58a6ff"
ACCENT2    = "#3fb950"
WARN       = "#d29922"
ERR_COL    = "#f85149"
TEXT_MAIN  = "#e6edf3"
TEXT_DIM   = "#8b949e"
TEXT_LOG   = "#cdd9e5"
FONT_MONO  = ("Consolas", 10)
FONT_UI    = ("Segoe UI", 10)
FONT_LABEL = ("Segoe UI", 9)
FONT_BIG   = ("Segoe UI", 18, "bold")
FONT_MED   = ("Segoe UI", 12, "bold")


class FlightTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FlightTracker")
        self.configure(bg=DARK_BG)
        self.resizable(True, True)
        self.minsize(780, 580)

        self.flight_data = FlightData()
        self.event_q     = queue.Queue()
        self.sim_worker: SimWorker | None = None
        self.flight_active = False

        self._build_ui()
        self._start_worker()
        self._poll_queue()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        # top bar: connection status + title
        top = tk.Frame(self, bg=DARK_BG, pady=6)
        top.pack(fill=tk.X, padx=12)

        tk.Label(top, text="✈  FlightTracker", font=("Segoe UI", 14, "bold"),
                 bg=DARK_BG, fg=ACCENT).pack(side=tk.LEFT)

        self._status_dot = tk.Label(top, text="●", font=("Segoe UI", 16),
                                    bg=DARK_BG, fg=ERR_COL)
        self._status_dot.pack(side=tk.RIGHT, padx=(4, 0))
        self._status_lbl = tk.Label(top, text="Disconnected", font=FONT_UI,
                                    bg=DARK_BG, fg=ERR_COL)
        self._status_lbl.pack(side=tk.RIGHT)

        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill=tk.X, padx=0)

        # main area: left panel + console
        main = tk.Frame(self, bg=DARK_BG)
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        left = tk.Frame(main, bg=DARK_BG, width=310)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left.pack_propagate(False)

        right = tk.Frame(main, bg=DARK_BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_flight_info(left)
        self._build_live_data(left)
        self._build_landing_summary(left)
        self._build_controls(left)
        self._build_console(right)

    def _panel(self, parent, title):
        outer = tk.Frame(parent, bg=PANEL_BG, bd=0, highlightbackground=BORDER,
                         highlightthickness=1)
        outer.pack(fill=tk.X, pady=(0, 8))
        tk.Label(outer, text=title, font=("Segoe UI", 9, "bold"),
                 bg=PANEL_BG, fg=TEXT_DIM).pack(anchor=tk.W, padx=10, pady=(7, 3))
        inner = tk.Frame(outer, bg=PANEL_BG)
        inner.pack(fill=tk.X, padx=10, pady=(0, 8))
        return inner

    def _labeled_entry(self, parent, label, row, default=""):
        tk.Label(parent, text=label, font=FONT_LABEL, bg=PANEL_BG,
                 fg=TEXT_DIM).grid(row=row, column=0, sticky=tk.W, pady=2)
        var = tk.StringVar(value=default)
        e = tk.Entry(parent, textvariable=var, font=FONT_UI,
                     bg="#21262d", fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                     relief=tk.FLAT, highlightbackground=BORDER,
                     highlightthickness=1, width=20)
        e.grid(row=row, column=1, sticky=tk.EW, padx=(8, 0), pady=2)
        parent.columnconfigure(1, weight=1)
        return var

    def _build_flight_info(self, parent):
        p = self._panel(parent, "FLIGHT INFO")
        self._var_callsign = self._labeled_entry(p, "Callsign",     0)
        self._var_aircraft = self._labeled_entry(p, "Aircraft",     1)
        self._var_airline  = self._labeled_entry(p, "Airline",      2)
        self._var_flightno = self._labeled_entry(p, "Flight No.",   3)

    def _build_live_data(self, parent):
        p = self._panel(parent, "LIVE DATA")
        self._live_labels = {}
        rows = [
            ("ALT",  "— ft MSL"),
            ("AGL",  "— ft"),
            ("IAS",  "— kts"),
            ("GS",   "— kts"),
            ("VVI",  "— fpm"),
            ("G",    "—"),
        ]
        for i, (k, default) in enumerate(rows):
            tk.Label(p, text=k, font=("Segoe UI", 9), bg=PANEL_BG,
                     fg=TEXT_DIM, width=5, anchor=tk.W).grid(row=i, column=0, sticky=tk.W)
            lbl = tk.Label(p, text=default, font=("Segoe UI", 11, "bold"),
                           bg=PANEL_BG, fg=TEXT_MAIN, anchor=tk.W)
            lbl.grid(row=i, column=1, sticky=tk.W, padx=(6, 0))
            self._live_labels[k] = lbl

    def _build_landing_summary(self, parent):
        p = self._panel(parent, "LANDINGS")
        self._landing_text = tk.Text(p, height=5, bg="#21262d", fg=TEXT_MAIN,
                                     font=FONT_MONO, relief=tk.FLAT, state=tk.DISABLED,
                                     wrap=tk.WORD)
        self._landing_text.pack(fill=tk.X)
        # tags
        self._landing_text.tag_config("good",  foreground=ACCENT2)
        self._landing_text.tag_config("warn",  foreground=WARN)
        self._landing_text.tag_config("bad",   foreground=ERR_COL)

    def _build_controls(self, parent):
        p = tk.Frame(parent, bg=DARK_BG)
        p.pack(fill=tk.X, pady=(4, 0))

        self._btn_flight = tk.Button(p, text="▶  Start Flight",
                                     font=("Segoe UI", 10, "bold"),
                                     bg=ACCENT2, fg="#0d1117",
                                     activebackground="#2ea043",
                                     relief=tk.FLAT, cursor="hand2",
                                     padx=12, pady=6,
                                     command=self._toggle_flight)
        self._btn_flight.pack(fill=tk.X)

    def _build_console(self, parent):
        tk.Label(parent, text="CONSOLE", font=("Segoe UI", 9, "bold"),
                 bg=DARK_BG, fg=TEXT_DIM).pack(anchor=tk.W)

        frame = tk.Frame(parent, bg=PANEL_BG, highlightbackground=BORDER,
                         highlightthickness=1)
        frame.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        self._console = tk.Text(frame, bg=PANEL_BG, fg=TEXT_LOG,
                                font=FONT_MONO, relief=tk.FLAT,
                                state=tk.DISABLED, wrap=tk.WORD,
                                pady=6, padx=8)
        sb = tk.Scrollbar(frame, command=self._console.yview, bg=PANEL_BG,
                          troughcolor=PANEL_BG)
        self._console.config(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._console.pack(fill=tk.BOTH, expand=True)

        # colour tags
        self._console.tag_config("INFO", foreground=TEXT_LOG)
        self._console.tag_config("OK",   foreground=ACCENT2)
        self._console.tag_config("WARN", foreground=WARN)
        self._console.tag_config("ERR",  foreground=ERR_COL)

    # ── worker ────────────────────────────────────────────────────────────────

    def _start_worker(self):
        self.sim_worker = SimWorker(self.flight_data, self.event_q)
        self.sim_worker.start()

    # ── event loop ────────────────────────────────────────────────────────────

    def _poll_queue(self):
        try:
            while True:
                evt = self.event_q.get_nowait()
                self._handle_event(evt)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)   # check 10×/s — lightweight

    def _handle_event(self, evt):
        t = evt["type"]

        if t == "log":
            self._console_append(evt["msg"], evt.get("level", "INFO"))

        elif t == "connected":
            self._set_status(True)
            # try to pre-fill aircraft type
            self.after(1500, self._try_prefill_aircraft)

        elif t == "disconnected":
            self._set_status(False)

        elif t == "position":
            self._update_live(evt)

        elif t == "landing":
            self._add_landing_entry(evt["data"])

    def _try_prefill_aircraft(self):
        """Attempt to read acf_ICAO once connected if field is empty."""
        if not self.sim_worker or not self.sim_worker.connected:
            return
        if self._var_aircraft.get().strip():
            return   # user already filled it
        try:
            # getDREF returns float for numeric drefs; acf_ICAO is a byte string dref
            # XPlaneConnectX doesn't natively handle string drefs, so we skip silently
            pass
        except Exception:
            pass

    # ── UI updates ────────────────────────────────────────────────────────────

    def _set_status(self, connected: bool):
        if connected:
            self._status_dot.config(fg=ACCENT2)
            self._status_lbl.config(text="Connected", fg=ACCENT2)
        else:
            self._status_dot.config(fg=ERR_COL)
            self._status_lbl.config(text="Disconnected", fg=ERR_COL)

    def _update_live(self, evt):
        def fmt(v, dec=0, unit=""):
            if v is None: return "—"
            return f"{v:.{dec}f}{unit}"

        self._live_labels["ALT"].config(text=fmt(evt.get("alt_ft"), 0, " ft"))
        self._live_labels["AGL"].config(text=fmt(evt.get("agl_ft"), 0, " ft"))
        self._live_labels["IAS"].config(text=fmt(evt.get("ias_kts"), 1, " kts"))
        self._live_labels["GS"].config( text=fmt(evt.get("gs_kts"),  1, " kts"))

        fpm = evt.get("fpm", 0)
        sign = "+" if fpm >= 0 else ""
        self._live_labels["VVI"].config(text=f"{sign}{fpm:.0f} fpm")

        g = evt.get("g", 1.0)
        g_col = ACCENT2 if g < 1.3 else WARN if g < 1.8 else ERR_COL
        self._live_labels["G"].config(text=f"{g:.2f} G", fg=g_col)

    def _add_landing_entry(self, entry: dict):
        fpm    = entry["fpm"]
        rating = entry["fpm_rating"]
        g      = entry["g_nrml"]
        n      = len(self.flight_data.landings)
        line   = f"#{n}  {rating}  {fpm:.0f} fpm  {g:.2f}G\n"

        tag = "good"
        if abs(fpm) > 360: tag = "warn"
        if abs(fpm) > 600: tag = "bad"

        self._landing_text.config(state=tk.NORMAL)
        self._landing_text.insert(tk.END, line, tag)
        self._landing_text.see(tk.END)
        self._landing_text.config(state=tk.DISABLED)

    def _console_append(self, msg: str, level="INFO"):
        now = datetime.now().strftime("%H:%M:%S")
        line = f"[{now}] {msg}\n"
        self._console.config(state=tk.NORMAL)
        self._console.insert(tk.END, line, level)
        # cap at 500 lines to avoid memory growth
        line_count = int(self._console.index("end-1c").split(".")[0])
        if line_count > 500:
            self._console.delete("1.0", "50.0")
        self._console.see(tk.END)
        self._console.config(state=tk.DISABLED)

    # ── flight control ────────────────────────────────────────────────────────

    def _toggle_flight(self):
        if not self.flight_active:
            self._start_flight()
        else:
            self._end_flight()

    def _start_flight(self):
        self.flight_active = True
        self.flight_data.reset()

        # copy flight info from fields
        self.flight_data.flight_info = {
            "callsign":      self._var_callsign.get().strip().upper(),
            "aircraft":      self._var_aircraft.get().strip().upper(),
            "airline":       self._var_airline.get().strip(),
            "flight_number": self._var_flightno.get().strip().upper(),
        }

        self._btn_flight.config(text="■  End Flight", bg=ERR_COL, fg="white",
                                activebackground="#b22222")
        self._console_append("──── Flight started ────", "OK")
        self._console_append(
            f"Callsign: {self.flight_data.flight_info['callsign'] or '(none)'}  "
            f"Aircraft: {self.flight_data.flight_info['aircraft'] or '(none)'}",
            "INFO"
        )

        # Reset sim worker's landing state
        if self.sim_worker:
            self.sim_worker._was_airborne   = False
            self.sim_worker._airborne_max_agl = 0.0
            self.sim_worker._min_fpm_during_approach = 0.0
            self.sim_worker._touch_time = None

    def _end_flight(self):
        self.flight_active = False
        self._btn_flight.config(text="▶  Start Flight", bg=ACCENT2, fg="#0d1117",
                                activebackground="#2ea043")
        self._console_append("──── Flight ended, saving … ────", "OK")
        self._save_flight()

    def _save_flight(self):
        """Save to JSON on a background thread to avoid UI stutter."""
        data = self.flight_data.to_dict()
        data["metadata"] = {
            "saved_at": ts_now(),
            "generator": "FlightTracker",
        }

        callsign = self.flight_data.flight_info.get("callsign") or "UNKNOWN"
        stamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"flight_{callsign}_{stamp}.json"

        def _write():
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self.event_q.put({"type": "log", "level": "OK",
                                  "msg": f"Saved → {filename}  "
                                         f"({len(data['position_updates'])} positions, "
                                         f"{len(data['landings'])} landings)"})
            except Exception as e:
                self.event_q.put({"type": "log", "level": "ERR",
                                  "msg": f"Save failed: {e}"})

        threading.Thread(target=_write, daemon=True).start()

    def on_close(self):
        if self.sim_worker:
            self.sim_worker.stop()
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = FlightTrackerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()