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

        // Collect all unique registrations that exist
        $registrations = $flights
            ->pluck('aircraft_registration')
            ->filter()
            ->unique()
            ->values()
            ->all();

        // Fetch all photos in one request, cached per registration
        $photos = $this->getPhotosForRegistrations($registrations);

        // Attach photo data to each flight
        $flights = $flights->map(function ($flight) use ($photos) {
            $reg = $flight->aircraft_registration;
            $flight->photo = $reg ? ($photos[$reg] ?? null) : null;
            return $flight;
        });

        return response()->json($flights);
    }

    public function show(Flight $flight)
    {
        $disk = Storage::disk('public');

        if (!$disk->exists($flight->file_path)) {
            return response()->json(['error' => 'File not found'], 404);
        }

        if ($flight->aircraft_registration) {
            $photos = $this->getPhotosForRegistrations([$flight->aircraft_registration]);
            $flight->photo = $photos[$flight->aircraft_registration] ?? null;
        } else {
            $flight->photo = null;
        }

        $content = gzdecode(file_get_contents($disk->path($flight->file_path)));
        $flightData = json_decode($content, true);

        return response()->json([
            'flight' => $flight,
            'file_url' => $disk->url($flight->file_path),
            'data' => $flightData,
        ]);
    }

    /**
     * Fetch photos for multiple registrations from the worker.
     * Results are cached per-registration for 24 hours in the DB.
     *
     * @param  string[]  $registrations
     * @return array<string, mixed>  keyed by registration
     */
    private function getPhotosForRegistrations(array $registrations): array
    {
        if (empty($registrations)) return [];

        $photos = [];
        $toFetch = [];

        // Check cache first for each registration
        foreach ($registrations as $reg) {
            $cacheKey = 'jetphotos_' . strtoupper($reg);
            $cached = Cache::get($cacheKey);

            if ($cached !== null) {
                $photos[$reg] = $cached;
            } else {
                $toFetch[] = $reg;
            }
        }

        // Fetch all uncached registrations in a single worker request
        if (!empty($toFetch)) {
            $workerUrl = rtrim(config('services.jetphotos.worker_url'), '/');
            $regsParam = implode(',', $toFetch);

            try {
                $response = Http::timeout(15)
                    ->get("{$workerUrl}/", [
                        'registrations' => $regsParam,
                    ]);

                if ($response->successful()) {
                    $data = $response->json();

                    foreach ($toFetch as $reg) {
                        $photoData = $data[$reg] ?? null;
                        $cacheKey = 'jetphotos_' . strtoupper($reg);

                        // Cache for 24h — aircraft photos rarely change
                        Cache::put($cacheKey, $photoData, now()->addHours(24));
                        $photos[$reg] = $photoData;
                    }
                }
            } catch (\Exception $e) {
                // Worker unreachable — return nulls, don't crash the response
                foreach ($toFetch as $reg) {
                    $photos[$reg] = null;
                }
            }
        }

        return $photos;
    }

    // --- All other methods unchanged below ---

    public function friendsFlights()
    {
        $user = Auth::user();
        $friendIds = $user->friends->pluck('id')->toArray();

        $flights = Flight::with('user:id,name')
            ->whereIn('user_id', $friendIds)
            ->latest()
            ->get();

        $registrations = $flights
            ->pluck('aircraft_registration')
            ->filter()
            ->unique()
            ->values()
            ->all();

        $photos = $this->getPhotosForRegistrations($registrations);

        $flights = $flights->map(function ($flight) use ($photos) {
            $reg = $flight->aircraft_registration;
            $flight->photo = $reg ? ($photos[$reg] ?? null) : null;
            return $flight;
        });

        return response()->json($flights);
    }

    public function store(Request $request)
    {
        $request->validate([
            'flight_file'            => 'required|file',
            'aircraft_registration'  => 'nullable|string|max:255',
            'aircraft_type'          => 'nullable|string|max:255',
            'route'                  => 'nullable|string|max:2048',
        ]);

        $file    = $request->file('flight_file');
        $content = gzdecode(file_get_contents($file->getRealPath()));
        $data    = json_decode($content, true);
        $path    = $file->store('flights', 'public');

        $dep_icao = null;
        if (!empty($data['path'])) {
            $firstPoint = $data['path'][0];
            $dep_icao   = $this->getNearestIcao($firstPoint[1], $firstPoint[2]);
        }

        $arr_icao = null;
        if (!empty($data['landings'])) {
            $lastLanding = end($data['landings']);
            $arr_icao    = $this->getNearestIcao($lastLanding['lat'], $lastLanding['lon']);
        }

        $flight = Flight::create([
            'user_id'                => Auth::id(),
            'callsign'               => $data['metadata']['callsign']               ?? 'unknown',
            'flight_number'          => $data['metadata']['flight_number']          ?? 'unknown',
            'airline'                => $data['metadata']['airline']                ?? 'unknown',
            'aircraft_registration'  => $request->input('aircraft_registration')    ?? $data['metadata']['aircraft_registration'] ?? null,
            'aircraft_type'          => $request->input('aircraft_type')            ?? $data['metadata']['aircraft_type']         ?? null,
            'route'                  => $request->input('route')                    ?? $data['metadata']['route']                 ?? null,
            'dep_icao'               => $dep_icao,
            'arr_icao'               => $arr_icao,
            'start_time'             => $data['metadata']['start_time']             ?? null,
            'file_path'              => $path,
            'schema_version'         => $data['metadata']['schema_version']         ?? null,
        ]);

        return response()->json($flight, 201);
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

    public function download(Flight $flight)
    {
        if ($flight->user_id !== Auth::id()) {
            return response()->json(['error' => 'Unauthorized action.'], 403);
        }

        $disk = Storage::disk('public');

        if (!$disk->exists($flight->file_path)) {
            return response()->json(['error' => 'File not found'], 404);
        }

        $callsign  = $flight->callsign  ?? 'unknown';
        $timestamp = $flight->start_time
            ? \Carbon\Carbon::parse($flight->start_time)->format('Ymd_His')
            : 'unknown';

        $filename = "flight_{$callsign}_{$timestamp}.json.gz";

        return response()->download($disk->path($flight->file_path), $filename, [
            'Content-Type' => 'application/gzip',
        ]);
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
}
