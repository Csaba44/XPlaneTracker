<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Cache;

class AirportDataController extends Controller
{
    public function getAirportRunways(Request $request, $icao)
    {
        $icao = strtoupper($icao);
        $cacheKey = "airport_full_data_{$icao}";

        if (Cache::has($cacheKey)) {
            return response()->json(Cache::get($cacheKey));
        }

        $token = config('services.airportdb.token');
        $response = Http::get("https://airportdb.io/api/v1/airport/{$icao}", [
            'apiToken' => $token
        ]);

        if ($response->failed()) {
            return response()->json(['error' => 'Failed to fetch airport data'], $response->status());
        }

        $data = $response->json();

        if (isset($data['runways'])) {
            foreach ($data['runways'] as &$rwy) {
                $rwy['length_m'] = is_numeric($rwy['length_ft'] ?? null) ? round((float) $rwy['length_ft'] * 0.3048, 2) : null;
                $rwy['width_m'] = is_numeric($rwy['width_ft'] ?? null) ? round((float) $rwy['width_ft'] * 0.3048, 2) : null;

                $rwy['le_elevation_m'] = is_numeric($rwy['le_elevation_ft'] ?? null) ? round((float) $rwy['le_elevation_ft'] * 0.3048, 2) : null;
                $rwy['he_elevation_m'] = is_numeric($rwy['he_elevation_ft'] ?? null) ? round((float) $rwy['he_elevation_ft'] * 0.3048, 2) : null;
            }
        }

        Cache::put($cacheKey, $data, now()->addDays(30));

        return response()->json($data);
    }
}
