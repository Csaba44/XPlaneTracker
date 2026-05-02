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
                $rwy['length_m'] = isset($rwy['length_ft']) ? round($rwy['length_ft'] * 0.3048, 2) : null;
                $rwy['width_m'] = isset($rwy['width_ft']) ? round($rwy['width_ft'] * 0.3048, 2) : null;

                $rwy['le_elevation_m'] = isset($rwy['le_elevation_ft']) ? round($rwy['le_elevation_ft'] * 0.3048, 2) : null;
                $rwy['he_elevation_m'] = isset($rwy['he_elevation_ft']) ? round($rwy['he_elevation_ft'] * 0.3048, 2) : null;

                $rwy['le_heading_degM'] = isset($rwy['le_heading_degT']) ? round($rwy['le_heading_degT'], 0) : null;
                $rwy['he_heading_degM'] = isset($rwy['he_heading_degT']) ? round($rwy['he_heading_degT'], 0) : null;
            }
        }

        Cache::put($cacheKey, $data, now()->addDays(30));

        return response()->json($data);
    }
}
