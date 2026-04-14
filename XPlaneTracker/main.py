import json
import time
import os
import gzip
import threading
import requests
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv
import sys

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.prompt import Prompt
from rich.live import Live
from rich.layout import Layout

from xp_provider import XPlaneProvider
from msfs_provider import MSFSProvider

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

load_dotenv(resource_path(".env"))

console = Console()

current_telemetry = {"lat": None, "on_ground": None}
log_lines = []
user_name = "Pilot"
user_id = -1

landing_buffer = []
buffer_lock = threading.Lock()
buffer_timer = None

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

def info(msg): console.print(f"[bold cyan]ℹ[/bold cyan] {msg}")
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

def send_landing_webhook():
    global landing_buffer, buffer_timer

    if args.no_webhook:
        with buffer_lock:
            landing_buffer = []
            buffer_timer = None
        return

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url or not landing_buffer:
        return

    metadata = flight_path_data.get("metadata", {})

    with buffer_lock:
        title = f"{user_name} muro phral megérkezett, shavale!"
        
        description_lines = []
        for i, l in enumerate(landing_buffer):
            prefix = "" if i == 0 else "Bounce: "
            description_lines.append(f"**{prefix}{l['fpm']:.0f} fpm** | **{l['g']:.2f} g**")
        
        payload = {
            "embeds": [{
                "title": title,
                "description": "\n".join(description_lines),
                "color": 0x38bdf8,
                "fields": [
                    {"name": "Callsign", "value": metadata.get("callsign", "N/A"), "inline": True},
                    {"name": "Flight Number", "value": metadata.get("flight_number", "N/A"), "inline": True},
                    {"name": "Registration", "value": metadata.get("aircraft_registration", "N/A"), "inline": True},
                    {"name": "Simulator", "value": metadata.get("simulator", "N/A"), "inline": True},
                ],
                "footer": {
                    "text": "csabolanta.hu"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        }

        try:
            requests.post(webhook_url, json=payload, timeout=5)
        except Exception as e:
            log(f"[bold red]Webhook Error:[/bold red] {e}")

        landing_buffer = []
        buffer_timer = None

parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="127.0.0.1")
parser.add_argument("--logout", action="store_true")
parser.add_argument("--dev", action="store_true")
parser.add_argument("--no-webhook", action="store_true", help="Disable Discord webhook notifications")
args = parser.parse_args()

TOKEN_FILE = ".xtracker_token"
API_BASE_URL = "http://xtracker.local:5173/api" if args.dev else "https://api.csabolanta.hu/api"
API_FLIGHTS_URL = f"{API_BASE_URL}/flights"
API_USER_URL = f"{API_BASE_URL}/user"
API_LIVE_URL = f"{API_BASE_URL}/flights/live"

header()

if args.logout:
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        ok("Logged out successfully.")
    else:
        warn("Not logged in.")
    sys.exit(0)

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
        user_data = user_res.json()
        user_name = user_data.get('name', 'Pilot')
        user_id = user_data.get('id')
        ok(f"Authenticated as [bold]{user_name}[/bold]")
    else:
        err("Invalid API Key.")
        os.remove(TOKEN_FILE)
        console.input("[bold yellow]Press Enter to exit...[/bold yellow]")
        sys.exit(1)
except Exception as e:
    err(f"Server error: {e}")
    console.input("[bold yellow]Press Enter to exit...[/bold yellow]")
    sys.exit(1)

sim_choice = simulator_selector()
provider = XPlaneProvider(ip=args.host) if sim_choice == "X-Plane" else MSFSProvider()

step(f"Connecting to {sim_choice}...")
try:
    provider.connect()
    ok("Connected!")
except Exception as e:
    err(f"Connection failed: {e}")
    console.input("[bold yellow]Press Enter to exit...[/bold yellow]")
    sys.exit(1)

callsign = Prompt.ask("[bold magenta]Callsign[/bold magenta]", default="unknown")
flight_no = Prompt.ask("[bold magenta]Flight Number[/bold magenta]", default="unknown")
airline = Prompt.ask("[bold magenta]Airline[/bold magenta]", default="unknown")
reg = Prompt.ask("[bold magenta]Registration[/bold magenta]", default="unknown")

timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
base_filename = f"flights/flight_{callsign}_{timestamp_str}"
os.makedirs("flights", exist_ok=True)

flight_path_data = {
    "metadata": {
        "callsign": callsign, "flight_number": flight_no, "airline": airline,
        "aircraft_registration": reg, "simulator": sim_choice,
        "start_time": datetime.now().isoformat(),
        "columns": ["timestamp", "lat", "lon", "alt", "speed"]
    },
    "path": [], "landings": []
}

def save_flight_to_disk(target_path, data):
    with gzip.open(target_path, "wt", encoding="utf-8") as f:
        json.dump(data, f, separators=(',', ':'))

def landing_monitor():
    global current_telemetry, landing_buffer, buffer_timer
    was_on_ground = True
    while True:
        data = current_telemetry
        on_ground = data.get("on_ground")
        
        if on_ground is not None:
            if not was_on_ground and on_ground:
                touchdown_fpm = data.get("fpm", 0)
                g_force = data.get('gforce', 0)
                
                log(f"[bold green]LANDING[/bold green] {touchdown_fpm:.0f} FPM")
                
                flight_path_data["landings"].append({
                    "timestamp": round(time.time(), 2), "fpm": round(touchdown_fpm, 2),
                    "g_force": round(g_force, 2),
                    "lat": round(data.get('lat', 0), 5), "lon": round(data.get('lon', 0), 5)
                })

                with buffer_lock:
                    landing_buffer.append({'fpm': touchdown_fpm, 'g': g_force})
                    if buffer_timer is None:
                        buffer_timer = threading.Timer(10.0, send_landing_webhook)
                        buffer_timer.start()

            was_on_ground = on_ground
        time.sleep(0.1)

threading.Thread(target=landing_monitor, daemon=True).start()


def live_heartbeat():
    while True:
        time.sleep(5.0)
        data = current_telemetry
        lat = data.get("lat")
        lon = data.get("lon")
        
        if lat is None or lon is None:
            continue

        payload = {
            "user_id": user_id,
            "lat": lat,
            "lon": lon,
            "alt": data.get("alt", 0),
            "gs": data.get("gs", 0),
            "heading": data.get("heading", 0),
            "timestamp": int(time.time()),
            "landing": False
        }

        try:
            requests.post(API_LIVE_URL, json=payload, headers=auth_headers, timeout=3)
        except Exception:
            pass

threading.Thread(target=live_heartbeat, daemon=True).start()

last_lat, last_lon, last_alt, last_speed = None, None, None, None
last_log_time = 0
last_autosave_time = time.time()
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

            if now - last_autosave_time > 120:
                autosave_path = f"{base_filename}_autosaved.json.gz"
                save_flight_to_disk(autosave_path, flight_path_data)
                log("[bold blue]AUTOSAVE[/bold blue] Data synced to disk.")
                last_autosave_time = now

            if lat is not None and lon is not None:
                should_record = False
                state_changed = (lat != last_lat or lon != last_lon or alt != last_alt or speed != last_speed)

                if speed == 0:
                    if state_changed:
                        should_record = True
                else:
                    interval = 0.1
                    if speed > 350:
                        interval = 0.5
                    elif speed >= 250:
                        interval = 0.25
                        
                    if (now - last_log_time) >= interval:
                        should_record = True

                if should_record:
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
    final_filename = f"{base_filename}.json.gz"
    autosave_filename = f"{base_filename}_autosaved.json.gz"
    
    save_flight_to_disk(final_filename, flight_path_data)
    ok(f"Final data saved to [bold]{final_filename}[/bold]")
    
    if os.path.exists(autosave_filename):
        os.remove(autosave_filename)
        info("Cleanup: Autosave file removed.")
    
    try:
        with console.status("[bold cyan]Uploading flight...[/bold cyan]"):
            with open(final_filename, 'rb') as f:
                files = {'flight_file': (os.path.basename(final_filename), f, 'application/gzip')}
                response = requests.post(API_FLIGHTS_URL, files=files, headers=auth_headers)

        if response.status_code == 201:
            ok("Upload successful!")
            if Prompt.ask("\n[bold yellow]Delete local file?[/bold yellow]", choices=["y", "n"], default="y") == 'y':
                os.remove(final_filename)
                ok("Local file deleted.")
        else:
            err(f"Upload failed: {response.status_code}")
            console.input("[bold yellow]Press Enter to exit...[/bold yellow]")
    except Exception as e:
        err(f"Upload error: {e}")
        console.input("[bold yellow]Press Enter to exit...[/bold yellow]")
    
    provider.close()