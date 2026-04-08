<?php

namespace App\Http\Controllers;

use App\Models\Flight;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Auth;

class FlightController extends Controller
{
    public function index()
    {
        // Only return flights belonging to the currently authenticated user
        $flights = Flight::where('user_id', Auth::id())->get();
        return response()->json($flights);
    }

    public function store(Request $request)
    {
        $request->validate([
            'flight_file' => 'required|file'
        ]);

        $file = $request->file('flight_file');

        $content = gzdecode(file_get_contents($file->getRealPath()));
        $data = json_decode($content, true);

        $path = $file->store('flights', 'public');

        $flight = Flight::create([
            'user_id' => Auth::id(), // Assign the flight to the logged-in user
            'callsign' => $data['metadata']['callsign'] ?? 'unknown',
            'flight_number' => $data['metadata']['flight_number'] ?? 'unknown',
            'airline' => $data['metadata']['airline'] ?? 'unknown',
            'start_time' => $data['metadata']['start_time'] ?? null,
            'file_path' => $path
        ]);

        return response()->json($flight, 201);
    }

    public function show(Flight $flight)
    {
        // NO AUTHORIZATION CHECK HERE
        // Anyone who has the flight ID/URL can fetch this file.

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
        // Check if the user owns this flight
        if ($flight->user_id !== Auth::id()) {
            return response()->json(['error' => 'Unauthorized action.'], 403);
        }

        $flight->update($request->only([
            'callsign',
            'flight_number',
            'airline',
            'start_time'
        ]));

        return response()->json($flight);
    }

    public function destroy(Flight $flight)
    {
        // Check if the user owns this flight
        if ($flight->user_id !== Auth::id()) {
            return response()->json(['error' => 'Unauthorized action.'], 403);
        }

        Storage::disk('public')->delete($flight->file_path);
        $flight->delete();

        return response()->json(null, 204);
    }
}
