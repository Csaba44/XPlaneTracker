<?php

namespace App\Http\Controllers;

use App\Models\Flight;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;

class LeaderboardController extends Controller
{
    public function index()
    {
        // Fetch flights from ONLY the last 30 days
        $flights = Flight::with('user:id,name')
            ->where('created_at', '>=', now()->subDays(30))
            ->get(['id', 'user_id', 'arr_icao', 'aircraft_type', 'file_path']);

        $airports = [];
        $userHours = [];
        $disk = Storage::disk('public');

        foreach ($flights as $flight) {
            if (!$flight->file_path || !$disk->exists($flight->file_path)) {
                continue;
            }

            try {
                $content = gzdecode($disk->get($flight->file_path));
                $data = json_decode($content, true);
                $landings = $data['landings'] ?? [];
                $path = $data['path'] ?? [];
            } catch (\Exception $e) {
                continue;
            }

            // --- Calculate Flight Duration for "Most Flown Hours" ---
            if (!empty($path) && count($path) > 1) {
                $firstPoint = $path[0];
                $lastPoint = end($path);

                // Timestamp is index 0 in the path array: [timestamp, lat, lon, alt, speed]
                $durationSeconds = $lastPoint[0] - $firstPoint[0];

                if ($durationSeconds > 0) {
                    $userId = $flight->user_id;
                    if (!isset($userHours[$userId])) {
                        $userHours[$userId] = [
                            'user_id' => $userId,
                            'user_name' => $flight->user->name ?? 'Unknown',
                            'total_seconds' => 0
                        ];
                    }
                    $userHours[$userId]['total_seconds'] += $durationSeconds;
                }
            }

            // --- Calculate Top Landings (Ignoring Bounces) ---
            if (empty($landings) || empty($flight->arr_icao)) continue;

            // 1. Sort landings chronologically
            usort($landings, function ($a, $b) {
                return ($a['timestamp'] ?? 0) <=> ($b['timestamp'] ?? 0);
            });

            $sequences = [];
            $lastTime = 0;

            // 2. Group landings separated by at least 60 seconds
            foreach ($landings as $landing) {
                $t = $landing['timestamp'] ?? 0;

                // If it has been more than 60s since the last touchdown, it's a new sequence
                if ($t - $lastTime > 60) {
                    $sequences[] = $landing; // Save the INITIAL touchdown of this sequence
                }

                // Update lastTime to the bounce's time so the 60s window rolls
                $lastTime = $t;
            }

            // 3. The actual arrival is the first touchdown of the final sequence
            $actualTouchdown = end($sequences);

            if (!$actualTouchdown) continue;

            $airports[$flight->arr_icao][] = [
                'flight_id' => $flight->id,
                'user_id' => $flight->user_id,
                'user_name' => $flight->user->name ?? 'Unknown',
                'aircraft_type' => $flight->aircraft_type,
                'fpm' => $actualTouchdown['fpm'] ?? 0,
                'g_force' => $actualTouchdown['g_force'] ?? 0,
            ];
        }

        $airportLeaderboards = [];

        foreach ($airports as $icao => $airportFlights) {
            // Rule: at least 2 unique users must have flown here
            $uniqueUsers = collect($airportFlights)->pluck('user_id')->unique()->count();

            if ($uniqueUsers >= 2) {
                // Get the best FPM per user
                $topFpm = collect($airportFlights)
                    ->sortBy(function ($f) {
                        return abs($f['fpm']);
                    })
                    ->unique('user_id') // Ensure only the user's personal best is shown
                    ->take(5)
                    ->values();

                // Get the best G-Force per user
                $topG = collect($airportFlights)
                    ->sortBy('g_force')
                    ->unique('user_id') // Ensure only the user's personal best is shown
                    ->take(5)
                    ->values();

                $airportLeaderboards[] = [
                    'icao' => strtoupper($icao),
                    'top_fpm' => $topFpm,
                    'top_g' => $topG,
                ];
            }
        }

        // Format the Most Flown Hours output
        $topHours = collect($userHours)->map(function ($u) {
            $u['hours'] = round($u['total_seconds'] / 3600, 2);
            return $u;
        })->sortByDesc('total_seconds')->take(10)->values(); // Top 10 pilots

        return response()->json([
            'airports' => collect($airportLeaderboards)->sortBy('icao')->values(),
            'top_hours' => $topHours
        ]);
    }
}
