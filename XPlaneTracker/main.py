import json
import time
import os
import gzip
import threading
import requests
import argparse
from datetime import datetime
from XPlaneConnectX import XPlaneConnectX

parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="127.0.0.1")
parser.add_argument("--logout", action="store_true")
args = parser.parse_args()

TOKEN_FILE = ".xtracker_token"
API_BASE_URL = "https://api.vacchunesports.online/api"
API_FLIGHTS_URL = f"{API_BASE_URL}/flights"
API_USER_URL = f"{API_BASE_URL}/user"

if args.logout:
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        print("Logged out successfully. Saved token has been deleted.")
    else:
        print("You are not currently logged in.")
    exit(0)

print(f"--- CSABOLANTA ---")

if os.path.exists(TOKEN_FILE):
    with open(TOKEN_FILE, "r") as f:
        TOKEN = f.read().strip()
else:
    print("Authentication required.")
    print("To get your API key:")
    print("1. Log in to the CSABOLANTA web dashboard.")
    print("2. Click 'Generate API Key' in the left sidebar.")
    
    TOKEN = input("\nPaste your API Key here: ").strip()
    
    if not TOKEN:
        print("No API Key provided. Exiting.")
        exit(1)
        
    with open(TOKEN_FILE, "w") as f:
        f.write(TOKEN)
    print("API Key saved securely.\n")

print("Verifying authentication...")
try:
    auth_headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {TOKEN}'
    }
    user_response = requests.get(API_USER_URL, headers=auth_headers)
    
    if user_response.status_code == 200:
        user_data = user_response.json()
        name = user_data.get('name', 'Testvér')
        print(f"Hallo, {name}!\n")
    else:
        print("Invalid or expired API Key.")
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        print("Logged out automatically. Please run the script again to provide a new API key.")
        exit(1)
except requests.exceptions.RequestException as e:
    print(f"Failed to connect to the server for authentication: {e}")
    exit(1)

HOST_IP = args.host

print(f"XPlane IP: {HOST_IP}")
print(f"API: {API_FLIGHTS_URL}")

callsign = input("Enter callsign (optional): ").strip() or "unknown"
flight_number = input("Enter flight number (optional): ").strip() or "unknown"
airline = input("Enter airline (optional): ").strip() or "unknown"

os.makedirs("flights", exist_ok=True)

xpc = XPlaneConnectX(ip=HOST_IP)

drefs_to_subscribe = [
    ("sim/flightmodel/position/latitude", 50),
    ("sim/flightmodel/position/longitude", 50),
    ("sim/flightmodel/position/elevation", 50),
    ("sim/flightmodel/failures/onground_any", 50),
    ("sim/flightmodel/position/vh_ind_fpm", 50),
    ("sim/flightmodel2/misc/gforce_normal", 50)
]

xpc.subscribeDREFs(drefs_to_subscribe)

flight_path_data = {
    "metadata": {
        "callsign": callsign,
        "flight_number": flight_number,
        "airline": airline,
        "start_time": datetime.now().isoformat(),
        "columns": ["timestamp", "lat", "lon", "alt"]
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
                
                print(f"\n---> LANDING RECORDED: {touchdown_fpm:.0f} FPM, {max_g:.2f} G <---")
                
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

try:
    while True:
        lat_data = xpc.current_dref_values.get("sim/flightmodel/position/latitude", {})
        lon_data = xpc.current_dref_values.get("sim/flightmodel/position/longitude", {})
        alt_data = xpc.current_dref_values.get("sim/flightmodel/position/elevation", {})

        lat = lat_data.get("value")
        lon = lon_data.get("value")
        alt = alt_data.get("value")

        if lat is not None and lon is not None and alt is not None:
            lat = round(lat, 5)
            lon = round(lon, 5)
            alt = int(alt * 3.28084)

            if lat != last_lat or lon != last_lon or alt != last_alt:
                current_time = round(time.time(), 2)
                formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                
                print(f"[{formatted_time}] Lat: {lat}, Lon: {lon}, Alt: {alt} ft")
                
                flight_path_data["path"].append([current_time, lat, lon, alt])
                
                last_lat = lat
                last_lon = lon
                last_alt = alt
                
        time.sleep(0.5)

except KeyboardInterrupt:
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"flights/flight_{callsign}_{timestamp_str}.json.gz"
    
    with gzip.open(filename, "wt", encoding="utf-8") as outfile:
        json.dump(flight_path_data, outfile, separators=(',', ':'))
        
    print(f"\nData saved to {filename}")

    try:
        print(f"Uploading {filename} to server...")
        with open(filename, 'rb') as f:
            files = {'flight_file': (os.path.basename(filename), f, 'application/gzip')}
            response = requests.post(API_FLIGHTS_URL, files=files, headers=auth_headers)

        if response.status_code == 201:
            print("Upload successful!")
            os.remove(filename)
            print(f"Deleted local file: {filename}")
        elif response.status_code == 401:
            print("Upload failed: Unauthorized. Your API key might be invalid or expired.")
            print("Run the script with --logout to clear it and provide a new one.")
        else:
            print(f"Upload failed with status code {response.status_code}.")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to the server. The file was kept locally. Error: {e}")