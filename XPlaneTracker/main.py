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

def info(msg):
    console.print(f"[bold cyan]ℹ[/bold cyan] {msg}")

def ok(msg):
    console.print(f"[bold green]✔[/bold green] {msg}")

def warn(msg):
    console.print(f"[bold yellow]⚠[/bold yellow] {msg}")

def err(msg):
    console.print(f"[bold red]✖[/bold red] {msg}")

def step(msg):
    console.print(f"[bold white]➜[/bold white] {msg}")

def landing(msg):
    console.print(Panel(msg, border_style="green", box=box.ROUNDED))

def tracking_banner():
    return Panel(
        "[bold green]Tracking started[/bold green]\n"
        "Press [bold red]Ctrl+C[/bold red] to stop and upload flight.",
        border_style="green",
        box=box.ROUNDED
    )

def build_layout():
    layout = Layout()
    layout.split(
        Layout(name="header", size=5),
        Layout(name="body")
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
        "[bold cyan]2.[/bold cyan] MSFS 2024",
        title="[bold magenta]Simulator Selection[/bold magenta]",
        border_style="magenta",
        box=box.ROUNDED
    ))
    
    choice = Prompt.ask("Choose simulator", choices=["1", "2"], default="1")
    
    if choice == "1":
        return "X-Plane"
    return "MSFS 2024"

parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="127.0.0.1")
parser.add_argument("--logout", action="store_true")
parser.add_argument("--dev", action="store_true")
args = parser.parse_args()

TOKEN_FILE = ".xtracker_token"

if args.dev:
    API_BASE_URL = "http://xtracker.local:5173/api"
else:
    API_BASE_URL = "https://api.vacchunesports.online/api"

API_FLIGHTS_URL = f"{API_BASE_URL}/flights"
API_USER_URL = f"{API_BASE_URL}/user"

header()

if args.logout:
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        ok("Logged out successfully. Saved token has been deleted.")
    else:
        warn("You are not currently logged in.")
    exit(0)

console.print(
    Panel.fit(
        f"[bold]Mode:[/bold] {'[bold yellow]DEVELOPMENT[/bold yellow]' if args.dev else '[bold green]PRODUCTION[/bold green]'}",
        border_style="cyan",
        box=box.ROUNDED
    )
)

if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, "r") as f:
        TOKEN = f.read().strip()
    ok("Saved API Key loaded.")
else:
    warn("Authentication required.")
    console.print(
        Panel(
            "[bold]To get your API key:[/bold]\n"
            "[cyan]1.[/cyan] Log in to the CSABOLANTA web dashboard.\n"
            "[cyan]2.[/cyan] Click [bold]'Generate API Key'[/bold] in the left sidebar.",
            border_style="yellow",
            box=box.ROUNDED
        )
    )
    
    TOKEN = Prompt.ask("[bold cyan]Paste your API Key[/bold cyan]").strip()
    
    if not TOKEN:
        err("No API Key provided. Exiting.")
        exit(1)
        
    with open(TOKEN_FILE, "w") as f:
        f.write(TOKEN)
    ok("API Key saved securely.")

step("Verifying authentication...")
try:
    auth_headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {TOKEN}'
    }

    with console.status("[bold cyan]Connecting to server...[/bold cyan]", spinner="dots"):
        user_response = requests.get(API_USER_URL, headers=auth_headers)
    
    if user_response.status_code == 200:
        user_data = user_response.json()
        name = user_data.get('name', 'Testvér')
        ok(f"Authenticated as [bold]{name}[/bold].")
    else:
        err("Invalid or expired API Key.")
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        exit(1)

except requests.exceptions.RequestException as e:
    err(f"Failed to connect to the server: {e}")
    exit(1)

sim_choice = simulator_selector()

if sim_choice == "X-Plane":
    provider = XPlaneProvider(ip=args.host)
else:
    provider = MSFSProvider()

step(f"Connecting to {sim_choice}...")
try:
    provider.connect()
    ok(f"Connected to {sim_choice} successfully.")
except Exception as e:
    err(f"Could not connect to {sim_choice}: {e}")
    exit(1)

callsign = Prompt.ask("[bold magenta]Enter callsign[/bold magenta]", default="unknown").strip() or "unknown"
flight_number = Prompt.ask("[bold magenta]Enter flight number[/bold magenta]", default="unknown").strip() or "unknown"
airline = Prompt.ask("[bold magenta]Enter airline[/bold magenta]", default="unknown").strip() or "unknown"
aircraft_registration = Prompt.ask("[bold magenta]Enter aircraft registration[/bold magenta]", default="unknown").strip() or "unknown"

flight_path_data = {
    "metadata": {
        "callsign": callsign,
        "flight_number": flight_number,
        "airline": airline,
        "aircraft_registration": aircraft_registration,
        "simulator": sim_choice,
        "start_time": datetime.now().isoformat(),
        "columns": ["timestamp", "lat", "lon", "alt", "speed"]
    },
    "path": [],
    "landings": []
}

def landing_monitor():
    global current_telemetry
    was_on_ground = True
    fpm_buffer = []
    
    while True:
        data = current_telemetry # Use shared data
        
        on_ground = data.get("on_ground")
        fpm = data.get("fpm")
        
        if on_ground is not None and fpm is not None:
            fpm_buffer.append(fpm)
            if len(fpm_buffer) > 20: # Slightly larger buffer for MSFS
                fpm_buffer.pop(0)
                
            if not was_on_ground and on_ground:
                touchdown_fpm = min(fpm_buffer) if fpm_buffer else 0
                
                landing_msg = (
                    f"[bold green]LANDING RECORDED[/bold green]\n\n"
                    f"[bold]Touchdown:[/bold] {touchdown_fpm:.0f} FPM\n"
                    f"[bold]Max G:[/bold] {data.get('gforce', 0):.2f} G"
                )
                landing(landing_msg)
                log(f"[bold green]LANDING[/bold green] {touchdown_fpm:.0f} FPM")
                
                flight_path_data["landings"].append({
                    "timestamp": round(time.time(), 2),
                    "fpm": round(touchdown_fpm, 2),
                    "g_force": round(data.get("gforce") or 0, 2),
                    "lat": round(data.get("lat") or 0, 5),
                    "lon": round(data.get("lon") or 0, 5)
                })
                
            was_on_ground = on_ground
            
        time.sleep(0.1) # Monitor doesn't need to be faster than 10Hz

monitor_thread = threading.Thread(target=landing_monitor, daemon=True)
monitor_thread.start()

last_lat, last_lon, last_alt = None, None, None
layout = build_layout()

try:
    with Live(layout, refresh_per_second=10, screen=False):
        layout["header"].update(tracking_banner())

        while True:
            data = provider.get_telemetry()
            current_telemetry = data 
            
            if "error" in data:
                log("[bold red]ERROR:[/bold red] SimConnect Pipe Disconnected. Is the sim running?")
                time.sleep(2)
                continue
            
            lat = data.get("lat")
            lon = data.get("lon")
            alt = data.get("alt")
            speed = data.get("gs")
            now = time.time()

            if lat is not None and lon is not None:
                # Trigger log if position, altitude, or speed changes, OR every 2 seconds as a heartbeat
                if (lat != last_lat or lon != last_lon or alt != last_alt or 
                    speed != last_speed or (now - last_log_time) > 2.0):
                    
                    formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    
                    log(
                        f"[dim]{formatted_time}[/dim] "
                        f"[bold cyan]LAT[/bold cyan]: {lat:.5f}  "
                        f"[bold cyan]LON[/bold cyan]: {lon:.5f}  "
                        f"[bold yellow]ALT[/bold yellow]: {alt} ft  "
                        f"[bold green]GS[/bold green]: {speed} kts"
                    )
                    
                    flight_path_data["path"].append([round(now, 2), round(lat, 5), round(lon, 5), alt, speed])
                    
                    last_lat, last_lon, last_alt, last_speed = lat, lon, alt, speed
                    last_log_time = now

            layout["body"].update(build_log_panel())
            time.sleep(0.1) # Increased frequency to 10Hz for smoother console updates

except KeyboardInterrupt:
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"flights/flight_{callsign}_{timestamp_str}.json.gz"
    os.makedirs("flights", exist_ok=True)
    
    with gzip.open(filename, "wt", encoding="utf-8") as outfile:
        json.dump(flight_path_data, outfile, separators=(',', ':'))
    
    ok(f"Data saved to [bold]{filename}[/bold]")

    try:
        with console.status("[bold cyan]Uploading flight...[/bold cyan]"):
            with open(filename, 'rb') as f:
                files = {'flight_file': (os.path.basename(filename), f, 'application/gzip')}
                response = requests.post(API_FLIGHTS_URL, files=files, headers=auth_headers)

        if response.status_code == 201:
            ok("Upload successful!")
            if Prompt.ask("\n[bold yellow]Delete local file?[/bold yellow]", choices=["y", "n"], default="y") == 'y':
                os.remove(filename)
        else:
            err(f"Upload failed: {response.status_code}")
            
    except Exception as e:
        err(f"Failed to connect to the server: {e}")
    
    provider.close()