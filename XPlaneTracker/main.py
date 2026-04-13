import json
import time
import os
import gzip
import threading
import requests
import argparse
from datetime import datetime
from XPlaneConnectX import XPlaneConnectX

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.prompt import Prompt
from rich.live import Live
from rich.layout import Layout

console = Console()

log_lines = []

def log(msg):
    log_lines.append(msg)
    if len(log_lines) > 300:
        log_lines.pop(0)

def header():
    title = Text("CSABOLANTA", style="bold magenta")
    subtitle = Text("X-Plane Flight Tracker", style="dim")
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
        warn("Logged out automatically. Please run the script again to provide a new API key.")
        exit(1)

except requests.exceptions.RequestException as e:
    err(f"Failed to connect to the server for authentication: {e}")
    exit(1)

HOST_IP = args.host

console.print(
    Panel(
        f"[bold]X-Plane IP:[/bold] [cyan]{HOST_IP}[/cyan]\n"
        f"[bold]API Endpoint:[/bold] [green]{API_FLIGHTS_URL}[/green]",
        border_style="blue",
        box=box.ROUNDED
    )
)

callsign = Prompt.ask("[bold magenta]Enter callsign[/bold magenta]", default="unknown").strip() or "unknown"
flight_number = Prompt.ask("[bold magenta]Enter flight number[/bold magenta]", default="unknown").strip() or "unknown"
airline = Prompt.ask("[bold magenta]Enter airline[/bold magenta]", default="unknown").strip() or "unknown"

os.makedirs("flights", exist_ok=True)

xpc = XPlaneConnectX(ip=HOST_IP)

drefs_to_subscribe = [
    ("sim/flightmodel/position/latitude", 50),
    ("sim/flightmodel/position/longitude", 50),
    ("sim/flightmodel/position/elevation", 50),
    ("sim/flightmodel/failures/onground_any", 50),
    ("sim/flightmodel/position/vh_ind_fpm", 50),
    ("sim/flightmodel2/misc/gforce_normal", 50),
    ("sim/flightmodel/position/groundspeed", 50)
]

step("Subscribing to X-Plane DataRefs...")
xpc.subscribeDREFs(drefs_to_subscribe)
ok("Subscribed successfully.")

flight_path_data = {
    "metadata": {
        "callsign": callsign,
        "flight_number": flight_number,
        "airline": airline,
        "start_time": datetime.now().isoformat(),
        "columns": ["timestamp", "lat", "lon", "alt", "speed"]
    },
    "path": [],
    "landings": []
}

def landing_monitor():
    was_on_ground = True
    fpm_buffer = []
    
    time.sleep(2)
    
    while True:
        onground_data = xpc.current_dref_values.get("sim/flightmodel/failures/onground_any", {})
        fpm_data = xpc.current_dref_values.get("sim/flightmodel/position/vh_ind_fpm", {})
        gforce_data = xpc.current_dref_values.get("sim/flightmodel2/misc/gforce_normal", {})
        
        onground_val = onground_data.get("value")
        fpm_val = fpm_data.get("value")
        gforce_val = gforce_data.get("value")
        
        if onground_val is not None and fpm_val is not None and gforce_val is not None:
            is_on_ground = bool(onground_val == 1.0)
            
            fpm_buffer.append(fpm_val)
            if len(fpm_buffer) > 10:
                fpm_buffer.pop(0)
                
            if not was_on_ground and is_on_ground:
                touchdown_fpm = min(fpm_buffer)
                
                max_g = gforce_val
                end_time = time.time() + 1.0
                while time.time() < end_time:
                    current_g_data = xpc.current_dref_values.get("sim/flightmodel2/misc/gforce_normal", {})
                    current_g = current_g_data.get("value")
                    if current_g is not None and current_g > max_g:
                        max_g = current_g
                    time.sleep(0.02)
                
                lat_dref = xpc.current_dref_values.get("sim/flightmodel/position/latitude", {})
                lon_dref = xpc.current_dref_values.get("sim/flightmodel/position/longitude", {})
                lat = lat_dref.get("value", 0)
                lon = lon_dref.get("value", 0)
                
                landing(
                    f"[bold green]LANDING RECORDED[/bold green]\n\n"
                    f"[bold]Touchdown:[/bold] {touchdown_fpm:.0f} FPM\n"
                    f"[bold]Max G:[/bold] {max_g:.2f} G\n"
                    f"[bold]Position:[/bold] {lat:.5f}, {lon:.5f}"
                )
                
                log(
                    f"[bold green]LANDING[/bold green] "
                    f"Touchdown: {touchdown_fpm:.0f} FPM | MaxG: {max_g:.2f} | Pos: {lat:.5f},{lon:.5f}"
                )
                
                flight_path_data["landings"].append({
                    "timestamp": round(time.time(), 2),
                    "fpm": round(touchdown_fpm, 2),
                    "g_force": round(max_g, 2),
                    "lat": round(lat, 5),
                    "lon": round(lon, 5)
                })
                
            was_on_ground = is_on_ground
            
        time.sleep(0.02)

monitor_thread = threading.Thread(target=landing_monitor, daemon=True)
monitor_thread.start()

last_lat = None
last_lon = None
last_alt = None

layout = build_layout()

try:
    with Live(layout, refresh_per_second=10, screen=False):
        layout["header"].update(tracking_banner())

        while True:
            lat_data = xpc.current_dref_values.get("sim/flightmodel/position/latitude", {})
            lon_data = xpc.current_dref_values.get("sim/flightmodel/position/longitude", {})
            alt_data = xpc.current_dref_values.get("sim/flightmodel/position/elevation", {})
            speed_data = xpc.current_dref_values.get("sim/flightmodel/position/groundspeed", {})

            lat = lat_data.get("value")
            lon = lon_data.get("value")
            alt = alt_data.get("value")
            speed_ms = speed_data.get("value")

            if lat is not None and lon is not None and alt is not None and speed_ms is not None:
                lat = round(lat, 5)
                lon = round(lon, 5)
                alt = int(alt * 3.28084)
                speed_kts = int(speed_ms * 1.94384)

                if lat != last_lat or lon != last_lon or alt != last_alt:
                    formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    
                    log(
                        f"[dim]{formatted_time}[/dim] "
                        f"[bold cyan]LAT[/bold cyan]: {lat}  "
                        f"[bold cyan]LON[/bold cyan]: {lon}  "
                        f"[bold yellow]ALT[/bold yellow]: {alt} ft  "
                        f"[bold green]GS[/bold green]: {speed_kts} kts"
                    )
                    
                    flight_path_data["path"].append([round(time.time(), 2), lat, lon, alt, speed_kts])
                    
                    last_lat = lat
                    last_lon = lon
                    last_alt = alt

            layout["body"].update(build_log_panel())
            time.sleep(0.5)

except KeyboardInterrupt:
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"flights/flight_{callsign}_{timestamp_str}.json.gz"
    
    with gzip.open(filename, "wt", encoding="utf-8") as outfile:
        json.dump(flight_path_data, outfile, separators=(',', ':'))
    
    ok(f"Data saved to [bold]{filename}[/bold]")

    try:
        step(f"Uploading {filename} to server...")

        with console.status("[bold cyan]Uploading flight...[/bold cyan]", spinner="earth"):
            with open(filename, 'rb') as f:
                files = {'flight_file': (os.path.basename(filename), f, 'application/gzip')}
                response = requests.post(API_FLIGHTS_URL, files=files, headers=auth_headers)

        if response.status_code == 201:
            ok("Upload successful!")
            
            delete_choice = Prompt.ask(
                "\n[bold yellow]Do you want to delete the local flight file?[/bold yellow]", 
                choices=["y", "n"], 
                default="y"
            )
            
            if delete_choice.lower() == 'y':
                os.remove(filename)
                ok(f"Deleted local file: {filename}")
            else:
                info(f"Local file kept: {filename}")
                
        elif response.status_code == 401:
            err("Upload failed: Unauthorized. Your API key might be invalid or expired.")
            warn("Run the script with --logout to clear it and provide a new one.")
            info(f"The file was kept locally: {filename}")
        else:
            err(f"Upload failed with status code {response.status_code}.")
            console.print(response.text)
            info(f"The file was kept locally: {filename}")
            
    except requests.exceptions.RequestException as e:
        err(f"Failed to connect to the server. The file was kept locally. Error: {e}")