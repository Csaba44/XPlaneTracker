import json
import time
import os
import gzip
import requests
from datetime import datetime
from XPlaneConnectX import XPlaneConnectX

API_URL = "http://127.0.0.1:8000/api/flights"

callsign = input("Enter callsign (optional): ").strip() or "unknown"
flight_number = input("Enter flight number (optional): ").strip() or "unknown"
airline = input("Enter airline (optional): ").strip() or "unknown"

os.makedirs("flights", exist_ok=True)

xpc = XPlaneConnectX()

drefs_to_subscribe = [
    ("sim/flightmodel/position/latitude", 50),
    ("sim/flightmodel/position/longitude", 50),
    ("sim/flightmodel/position/elevation", 50)
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
    "path": []
}

last_lat = None
last_lon = None
last_alt = None

try:
    while True:
        lat_data = xpc.current_dref_values["sim/flightmodel/position/latitude"]
        lon_data = xpc.current_dref_values["sim/flightmodel/position/longitude"]
        alt_data = xpc.current_dref_values["sim/flightmodel/position/elevation"]

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
            headers = {'Accept': 'application/json'}
            response = requests.post(API_URL, files=files, headers=headers)

        if response.status_code == 201:
            print("Upload successful!")
            os.remove(filename)
            print(f"Deleted local file: {filename}")
        else:
            print(f"Upload failed with status code {response.status_code}.")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to the server. The file was kept locally. Error: {e}")