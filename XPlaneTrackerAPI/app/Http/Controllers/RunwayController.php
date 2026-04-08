<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Cache;

class RunwayController extends Controller
{
    public function getRunways(Request $request)
    {
        $request->validate([
            'lat' => 'required|numeric',
            'lon' => 'required|numeric',
        ]);

        // Round coordinates to 2 decimal places (~1.1km grid) 
        // This ensures a landing on 04R and 22L at the same airport use the exact same cache file.
        $lat = round($request->lat, 2);
        $lon = round($request->lon, 2);

        $cacheKey = "runways_data_{$lat}_{$lon}";

        // 1. Check if we already have this airport saved
        if (Cache::has($cacheKey)) {
            return response()->json(Cache::get($cacheKey));
        }

        // 2. If not cached, prepare the Overpass bounding box query
        $offsetLat = 0.025;
        $offsetLon = 0.035;
        $s = $lat - $offsetLat;
        $n = $lat + $offsetLat;
        $w = $lon - $offsetLon;
        $e = $lon + $offsetLon;

        $query = "[out:json][timeout:15];way[\"aeroway\"=\"runway\"]({$s},{$w},{$n},{$e});out geom tags;";

        // 3. Define the mirrors in order of preference
        $mirrors = [
            'https://overpass.kumi.systems/api/interpreter',
            'https://overpass-api.de/api/interpreter',
            'https://overpass.private.coffee/api/interpreter'
        ];

        $runwayData = null;

        // 4. Try each mirror until one works
        foreach ($mirrors as $mirror) {
            try {
                // Http::retry(2, 500) means if it gets a 504, it waits half a second and tries the SAME mirror again once.
                // If it still fails, it throws an exception and the catch block moves it to the NEXT mirror.
                $response = Http::timeout(10)
                    ->retry(2, 500, function ($exception, $request) {
                        return $exception->getCode() === 504 || $exception->getCode() === 502;
                    })
                    ->get($mirror, ['data' => $query]);

                if ($response->successful()) {
                    $runwayData = $response->json();
                    break; // Success! Exit the mirror loop.
                }
            } catch (\Exception $e) {
                // Connection timeout or failure, simply continue to the next mirror in the array
                continue;
            }
        }

        // 5. Save and Return
        if ($runwayData && !empty($runwayData['elements'])) {
            // Cache it for 30 days. We use put() instead of remember() so we don't accidentally cache an empty failure.
            Cache::put($cacheKey, $runwayData, now()->addDays(30));
            return response()->json($runwayData);
        }

        // If all mirrors failed or returned nothing
        return response()->json(['error' => 'Runway data unavailable. All Overpass mirrors failed.'], 502);
    }
}
