import json
import time
import os
import gzip
import threading
import requests
import argparse
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.prompt import Prompt
from rich.live import Live
from rich.layout import Layout

from xp_provider import XPlaneProvider
from msfs_provider import MSFSProvider

console = Console()

# Global state for thread-safe telemetry
current_telemetry = {"lat": None, "on_ground": None}
log_lines = []

def log(msg):
    log_lines.append(msg)
    if len(log_lines) > 300:
        log_lines.pop(0)

def header():
    title = Text("CSABOLANTA", style="bold magenta")
    subtitle = Text("X-Plane & MSFS Flight Tracker", style="dim")
    console.print(
        Panel.fit(
            Text.assemble(title, "\n", subtitle),
            border_style="magenta",
            box=box.ROUNDED
        )
    )

def ok(msg): console.print(f"[bold green]✔[/bold green] {msg}")
def warn(msg): console.print(f"[bold yellow]⚠[/bold yellow] {msg}")
def err(msg): console.print(f"[bold red]✖[/bold red] {msg}")
def step(msg): console.print(f"[bold white]➜[/bold white] {msg}")

def tracking_banner():
    return Panel(
        "[bold green]Tracking started[/bold green]\n"
        "Press [bold red]Ctrl+C[/bold red] to stop and upload.",
        title="[bold green]Status[/bold green]",
        border_style="green",
        box=box.ROUNDED
    )

def build_landings_panel(landings):
    if not landings:
        content = "[dim]Waiting for touchdown...[/dim]"
    else:
        # Display last 2 landings
        lines = []
        for l in landings[-2:]:
            lines.append(f"• [bold green]{l['fpm']:.0f} FPM[/bold green] ({l['g_force']:.2f}G)")
        content = "\n".join(lines)
        
    return Panel(
        content,
        title="[bold green]Recent Landings[/bold green]",
        border_style="green",
        box=box.ROUNDED
    )

def build_layout():
    layout = Layout()
    layout.split(
        Layout(name="top", size=5),
        Layout(name="body")
    )
    layout["top"].split_row(
        Layout(name="status"),
        Layout(name="landings")
    )
    return layout

def build_log_panel():
    return Panel(
        "\n".join(log_lines[-30:]),
        title="[bold cyan]Live Log[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED
    )

def simulator_selector():
    console.print(Panel(
        "[bold cyan]1.[/bold cyan] X-Plane\n"
        "[bold cyan]2.[/bold cyan] MSFS 2024 / 2020",
        title="[bold magenta]Simulator Selection[/bold magenta]",
        border_style="magenta",
        box=box.ROUNDED
    ))
    choice = Prompt.ask("Choose simulator", choices=["1", "2"], default="1")
    return "X-Plane" if choice == "1" else "MSFS 2024"

# --- App Logic ---
parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="127.0.0.1")
parser.add_argument("--logout", action="store_true")
parser.add_argument("--dev", action="store_true")
args = parser.parse_args()

TOKEN_FILE = ".xtracker_token"
API_BASE_URL = "http://xtracker.local:5173/api" if args.dev else "https://api.vacchunesports.online/api"
API_FLIGHTS_URL = f"{API_BASE_URL}/flights"
API_USER_URL = f"{API_BASE_URL}/user"

header()

if args.logout:
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        ok("Logged out successfully.")
    else:
        warn("Not logged in.")
    exit(0)

# Load/Verify Token
if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, "r") as f: TOKEN = f.read().strip()
    ok("Saved API Key loaded.")
else:
    TOKEN = Prompt.ask("[bold cyan]Paste your API Key[/bold cyan]").strip()
    with open(TOKEN_FILE, "w") as f: f.write(TOKEN)

auth_headers = {'Accept': 'application/json', 'Authorization': f'Bearer {TOKEN}'}
try:
    with console.status("[bold cyan]Verifying Auth...[/bold cyan]"):
        user_res = requests.get(API_USER_URL, headers=auth_headers)
    if user_res.status_code == 200:
        ok(f"Authenticated as [bold]{user_res.json().get('name')}[/bold]")
    else:
        err("Invalid API Key."); os.remove(TOKEN_FILE); exit(1)
except Exception as e:
    err(f"Server error: {e}"); exit(1)

sim_choice = simulator_selector()
provider = XPlaneProvider(ip=args.host) if sim_choice == "X-Plane" else MSFSProvider()

step(f"Connecting to {sim_choice}...")
try:
    provider.connect()
    ok("Connected!")
except Exception as e:
    err(f"Connection failed: {e}"); exit(1)

callsign = Prompt.ask("[bold magenta]Callsign[/bold magenta]", default="unknown")
flight_no = Prompt.ask("[bold magenta]Flight Number[/bold magenta]", default="unknown")
airline = Prompt.ask("[bold magenta]Airline[/bold magenta]", default="unknown")
reg = Prompt.ask("[bold magenta]Registration[/bold magenta]", default="unknown")

flight_path_data = {
    "metadata": {
        "callsign": callsign, "flight_number": flight_no, "airline": airline, 
        "aircraft_registration": reg, "simulator": sim_choice,
        "start_time": datetime.now().isoformat(),
        "columns": ["timestamp", "lat", "lon", "alt", "speed"]
    },
    "path": [], "landings": []
}

def landing_monitor():
    global current_telemetry
    was_on_ground = True
    fpm_buffer = []
    while True:
        data = current_telemetry
        on_ground = data.get("on_ground")
        fpm = data.get("fpm")
        if on_ground is not None and fpm is not None:
            fpm_buffer.append(fpm)
            if len(fpm_buffer) > 20: fpm_buffer.pop(0)
            if not was_on_ground and on_ground:
                touchdown_fpm = min(fpm_buffer) if fpm_buffer else 0
                log(f"[bold green]LANDING[/bold green] {touchdown_fpm:.0f} FPM")
                flight_path_data["landings"].append({
                    "timestamp": round(time.time(), 2), "fpm": round(touchdown_fpm, 2),
                    "g_force": round(data.get('gforce', 0), 2),
                    "lat": round(data.get('lat', 0), 5), "lon": round(data.get('lon', 0), 5)
                })
            was_on_ground = on_ground
        time.sleep(0.1)

threading.Thread(target=landing_monitor, daemon=True).start()

# --- Main Tracking Loop ---
last_lat, last_lon, last_alt, last_speed = None, None, None, None
last_log_time = 0
layout = build_layout()

try:
    with Live(layout, refresh_per_second=10, screen=False):
        while True:
            data = provider.get_telemetry()
            current_telemetry = data
            
            if "error" in data:
                log("[bold red]ERROR:[/bold red] Pipe Disconnected. Check Simulator.")
                time.sleep(2); continue
            
            lat, lon, alt, speed = data.get("lat"), data.get("lon"), data.get("alt"), data.get("gs")
            now = time.time()

            if lat is not None and lon is not None:
                # Log on movement, speed change, or 2s heartbeat
                if (lat != last_lat or lon != last_lon or alt != last_alt or 
                    speed != last_speed or (now - last_log_time) > 2.0):
                    
                    formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    log(f"[dim]{formatted_time}[/dim] [bold cyan]LAT[/bold cyan]: {lat:.5f} [bold cyan]LON[/bold cyan]: {lon:.5f} [bold yellow]ALT[/bold yellow]: {alt}ft [bold green]GS[/bold green]: {speed}kts")
                    flight_path_data["path"].append([round(now, 2), round(lat, 5), round(lon, 5), alt, speed])
                    
                    last_lat, last_lon, last_alt, last_speed = lat, lon, alt, speed
                    last_log_time = now

            layout["status"].update(tracking_banner())
            layout["landings"].update(build_landings_panel(flight_path_data["landings"]))
            layout["body"].update(build_log_panel())
            time.sleep(0.1)

except KeyboardInterrupt:
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"flights/flight_{callsign}_{timestamp_str}.json.gz"
    os.makedirs("flights", exist_ok=True)
    
    with gzip.open(filename, "wt", encoding="utf-8") as f:
        json.dump(flight_path_data, f, separators=(',', ':'))
    ok(f"Saved locally to {filename}")
    
    try:
        with console.status("[bold cyan]Uploading flight...[/bold cyan]"):
            with open(filename, 'rb') as f:
                files = {'flight_file': (os.path.basename(filename), f, 'application/gzip')}
                response = requests.post(API_FLIGHTS_URL, files=files, headers=auth_headers)

        if response.status_code == 201:
            ok("Upload successful!")
            if Prompt.ask("\n[bold yellow]Delete local file?[/bold yellow]", choices=["y", "n"], default="y") == 'y':
                os.remove(filename)
                ok("Local file deleted.")
        else:
            err(f"Upload failed: {response.status_code}")
            console.print(response.text)
    except Exception as e:
        err(f"Upload error: {e}")
    
    provider.close()