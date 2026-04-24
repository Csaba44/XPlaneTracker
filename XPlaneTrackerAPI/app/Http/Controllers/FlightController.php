<?php

namespace App\Http\Controllers;

use App\Models\Flight;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;

class FlightController extends Controller
{
    public function index()
    {
        $flights = Flight::where('user_id', Auth::id())
            ->latest()
            ->get();

        return response()->json($flights);
    }

    private function getDistanceInMeters($lat1, $lon1, $lat2, $lon2)
    {
        $earthRadius = 6371000;
        $latDelta = deg2rad($lat2 - $lat1);
        $lonDelta = deg2rad($lon2 - $lon1);

        $angle = 2 * asin(sqrt(pow(sin($latDelta / 2), 2) + cos(deg2rad($lat1)) * cos(deg2rad($lat2)) * pow(sin($lonDelta / 2), 2)));

        return $angle * $earthRadius;
    }

    private function getNearestIcao($lat, $lon)
    {
        if (!$lat || !$lon) return null;

        if (!Storage::exists('airports.json')) {
            $response = Http::get('https://raw.githubusercontent.com/mwgg/Airports/master/airports.json');

            if ($response->successful()) {
                Storage::put('airports.json', $response->body());
            } else {
                return null;
            }
        }

        $airports = json_decode(Storage::get('airports.json'), true);

        if (empty($airports)) return null;

        $closestIcao = null;
        $minDistance = 5000;

        foreach ($airports as $airport) {
            if (empty($airport['icao']) || empty($airport['lat']) || empty($airport['lon'])) continue;

            $distance = $this->getDistanceInMeters($lat, $lon, $airport['lat'], $airport['lon']);

            if ($distance < $minDistance) {
                $minDistance = $distance;
                $closestIcao = $airport['icao'];
            }
        }

        return $closestIcao;
    }

    public function friendsFlights()
    {
        $user = Auth::user();
        $friendIds = $user->friends->pluck('id')->toArray();

        $flights = Flight::with('user:id,name')
            ->whereIn('user_id', $friendIds)
            ->latest()
            ->get();

        return response()->json($flights);
    }

    public function store(Request $request)
    {
        $request->validate([
            'flight_file' => 'required|file',
            'aircraft_registration' => 'nullable|string|max:255',
            'aircraft_type' => 'nullable|string|max:255'
        ]);

        $file = $request->file('flight_file');
        $content = gzdecode(file_get_contents($file->getRealPath()));
        $data = json_decode($content, true);
        $path = $file->store('flights', 'public');

        $dep_icao = null;
        if (!empty($data['path'])) {
            $firstPoint = $data['path'][0];
            $dep_icao = $this->getNearestIcao($firstPoint[1], $firstPoint[2]);
        }

        $arr_icao = null;
        if (!empty($data['landings'])) {
            $lastLanding = end($data['landings']);
            $arr_icao = $this->getNearestIcao($lastLanding['lat'], $lastLanding['lon']);
        }

        $flight = Flight::create([
            'user_id' => Auth::id(),
            'callsign' => $data['metadata']['callsign'] ?? 'unknown',
            'flight_number' => $data['metadata']['flight_number'] ?? 'unknown',
            'airline' => $data['metadata']['airline'] ?? 'unknown',
            'aircraft_registration' => $request->input('aircraft_registration') ?? $data['metadata']['aircraft_registration'] ?? null,
            'aircraft_type' => $request->input('aircraft_type') ?? $data['metadata']['aircraft_type'] ?? null,
            'dep_icao' => $dep_icao,
            'arr_icao' => $arr_icao,
            'start_time' => $data['metadata']['start_time'] ?? null,
            'file_path' => $path
        ]);

        return response()->json($flight, 201);
    }

    public function show(Flight $flight)
    {
        $disk = Storage::disk('public');

        if (!$disk->exists($flight->file_path)) {
            return response()->json(['error' => 'File not found'], 404);
        }

        $absolutePath = $disk->path($flight->file_path);

        return response()->file($absolutePath, [
            'Content-Type' => 'application/json',
            'Content-Encoding' => 'gzip',
        ]);
    }

    public function update(Request $request, Flight $flight)
    {
        if ($flight->user_id !== Auth::id()) {
            return response()->json(['error' => 'Unauthorized action.'], 403);
        }

        $validated = $request->validate([
            'callsign' => 'nullable|string|max:255',
            'flight_number' => 'nullable|string|max:255',
            'airline' => 'nullable|string|max:255',
            'aircraft_registration' => 'nullable|string|max:255',
            'aircraft_type' => 'nullable|string|max:255',
            'dep_icao' => 'nullable|alpha_num|max:10',
            'arr_icao' => 'nullable|alpha_num|max:10',
            'start_time' => 'nullable|date'
        ]);

        if (isset($validated['dep_icao'])) {
            $validated['dep_icao'] = strtoupper($validated['dep_icao']);
        }
        if (isset($validated['arr_icao'])) {
            $validated['arr_icao'] = strtoupper($validated['arr_icao']);
        }

        $flight->update($validated);

        return response()->json($flight);
    }

    public function destroy(Flight $flight)
    {
        if ($flight->user_id !== Auth::id()) {
            return response()->json(['error' => 'Unauthorized action.'], 403);
        }

        Storage::disk('public')->delete($flight->file_path);
        $flight->delete();

        return response()->json(null, 204);
    }
}
