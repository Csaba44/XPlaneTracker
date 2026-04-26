<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Cache;

class AirportFeaturesController extends Controller
{
    public function getFeatures(Request $request)
    {
        $request->validate([
            'lat' => 'required|numeric',
            'lon' => 'required|numeric',
        ]);

        $lat = round($request->lat, 2);
        $lon = round($request->lon, 2);

        $cacheKey = "airport_features_{$lat}_{$lon}";

        if (Cache::has($cacheKey)) {
            return response()->json(Cache::get($cacheKey));
        }

        $offsetLat = 0.025;
        $offsetLon = 0.035;
        $s = $lat - $offsetLat;
        $n = $lat + $offsetLat;
        $w = $lon - $offsetLon;
        $e = $lon + $offsetLon;

        $query = "[out:json][timeout:25];("
            . "way[\"aeroway\"=\"taxiway\"]({$s},{$w},{$n},{$e});"
            . "way[\"aeroway\"=\"taxilane\"]({$s},{$w},{$n},{$e});"
            . "node[\"aeroway\"=\"parking_position\"]({$s},{$w},{$n},{$e});"
            . "way[\"aeroway\"=\"parking_position\"]({$s},{$w},{$n},{$e});"
            . "node[\"aeroway\"=\"gate\"]({$s},{$w},{$n},{$e});"
            . "way[\"aeroway\"=\"terminal\"]({$s},{$w},{$n},{$e});"
            . ");out geom tags;";

        $mirrors = [
            'https://overpass.kumi.systems/api/interpreter',
            'https://overpass-api.de/api/interpreter',
            'https://overpass.private.coffee/api/interpreter',
        ];

        $featureData = null;

        foreach ($mirrors as $mirror) {
            try {
                $response = Http::timeout(15)
                    ->retry(2, 500, function ($exception, $request) {
                        return $exception->getCode() === 504 || $exception->getCode() === 502;
                    })
                    ->get($mirror, ['data' => $query]);

                if ($response->successful()) {
                    $featureData = $response->json();
                    break;
                }
            } catch (\Exception $e) {
                continue;
            }
        }

        if ($featureData && !empty($featureData['elements'])) {
            Cache::put($cacheKey, $featureData, now()->addDays(30));
            return response()->json($featureData);
        }

        return response()->json(['error' => 'Airport feature data unavailable.'], 502);
    }
}
