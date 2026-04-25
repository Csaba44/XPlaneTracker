<?php

namespace App\Http\Controllers;

use App\Models\Flight;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;

class LeaderboardController extends Controller
{
    public function index()
    {
        // Fetch flights, but select 'file_path' instead of the non-existent 'path_data'
        $flights = Flight::with('user:id,name')
            ->whereNotNull('arr_icao')
            ->where('arr_icao', '!=', '')
            ->get(['id', 'user_id', 'arr_icao', 'aircraft_type', 'file_path']);

        $airports = [];
        $disk = Storage::disk('public');

        foreach ($flights as $flight) {
            // Check if the flight file actually exists on the disk
            if (!$flight->file_path || !$disk->exists($flight->file_path)) {
                continue;
            }

            try {
                // Read and decompress the .gz file to get the landings
                $content = gzdecode($disk->get($flight->file_path));
                $data = json_decode($content, true);
                $landings = $data['landings'] ?? [];
            } catch (\Exception $e) {
                // Skip if the file is corrupted or decoding fails
                continue;
            }

            if (empty($landings)) continue;

            // Get the best FPM (closest to 0) for this specific flight
            $bestFpmLanding = collect($landings)->sortBy(function ($l) {
                return abs($l['fpm'] ?? 99999);
            })->first();

            // Get the best G-Force (closest to 1.0) for this specific flight
            $bestGLanding = collect($landings)->sortBy(function ($l) {
                return $l['g_force'] ?? 99;
            })->first();

            $airports[$flight->arr_icao][] = [
                'flight_id' => $flight->id,
                'user_id' => $flight->user_id,
                'user_name' => $flight->user->name ?? 'Unknown',
                'aircraft_type' => $flight->aircraft_type,
                'fpm' => $bestFpmLanding['fpm'] ?? 0,
                'g_force' => $bestGLanding['g_force'] ?? 0,
            ];
        }

        $leaderboard = [];

        foreach ($airports as $icao => $airportFlights) {
            // Rule: at least 2 unique users must have flown here
            $uniqueUsers = collect($airportFlights)->pluck('user_id')->unique()->count();

            if ($uniqueUsers >= 2) {
                $topFpm = collect($airportFlights)
                    ->sortBy(function ($f) {
                        return abs($f['fpm']);
                    })
                    ->take(5)
                    ->values();

                $topG = collect($airportFlights)
                    ->sortBy('g_force')
                    ->take(5)
                    ->values();

                $leaderboard[] = [
                    'icao' => strtoupper($icao),
                    'top_fpm' => $topFpm,
                    'top_g' => $topG,
                ];
            }
        }

        // Return alphabetically sorted by airport ICAO
        return response()->json(collect($leaderboard)->sortBy('icao')->values());
    }
}
