<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Storage;

class AirportDataController extends Controller
{
    private const OURAIRPORTS_FIELDS = [
        'le_ident', 'he_ident',
        'le_latitude_deg', 'le_longitude_deg',
        'he_latitude_deg', 'he_longitude_deg',
        'le_displaced_threshold_ft', 'he_displaced_threshold_ft',
        'le_elevation_ft', 'he_elevation_ft',
        'le_heading_degT', 'he_heading_degT',
        'length_ft', 'width_ft', 'surface',
    ];

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

    public function getOurAirportsRunways(Request $request, $icao)
    {
        $icao = strtoupper($icao);
        $cacheKey = "ourairports_rwy_{$icao}";

        $cached = Cache::get($cacheKey);
        if ($cached !== null) {
            return response()->json(['runways' => $cached]);
        }

        try {
            $csvPath = $this->ensureOurAirportsCsv();
        } catch (\Throwable $e) {
            return response()->json(['runways' => [], 'error' => 'OurAirports CSV unavailable'], 200);
        }

        $rows = $this->extractRunwaysForIcao($csvPath, $icao);
        Cache::put($cacheKey, $rows, now()->addDays(30));

        return response()->json(['runways' => $rows]);
    }

    private function ensureOurAirportsCsv(): string
    {
        $relPath = 'ourairports/runways.csv';
        $absPath = storage_path('app/' . $relPath);
        $stampKey = 'ourairports_csv_stamp';

        if (file_exists($absPath) && Cache::has($stampKey)) {
            return $absPath;
        }

        $dir = dirname($absPath);
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }

        $url = config('services.ourairports.runways_csv_url');
        $response = Http::timeout(60)->withOptions(['sink' => $absPath])->get($url);

        if (!$response->successful()) {
            if (file_exists($absPath)) {
                @unlink($absPath);
            }
            throw new \RuntimeException('Failed to download OurAirports runways.csv');
        }

        Cache::put($stampKey, true, now()->addDays(30));
        return $absPath;
    }

    private function extractRunwaysForIcao(string $csvPath, string $icao): array
    {
        $fh = fopen($csvPath, 'r');
        if ($fh === false) {
            return [];
        }

        $header = fgetcsv($fh);
        if ($header === false) {
            fclose($fh);
            return [];
        }
        $colIndex = array_flip($header);

        $airportIdentIdx = $colIndex['airport_ident'] ?? null;
        $closedIdx = $colIndex['closed'] ?? null;
        if ($airportIdentIdx === null) {
            fclose($fh);
            return [];
        }

        $rows = [];
        while (($row = fgetcsv($fh)) !== false) {
            if (($row[$airportIdentIdx] ?? '') !== $icao) {
                continue;
            }
            if ($closedIdx !== null && ($row[$closedIdx] ?? '0') === '1') {
                continue;
            }

            $out = [];
            foreach (self::OURAIRPORTS_FIELDS as $field) {
                $idx = $colIndex[$field] ?? null;
                $out[$field] = $idx !== null ? ($row[$idx] ?? '') : '';
            }
            $rows[] = $out;
        }
        fclose($fh);

        return $rows;
    }
}
