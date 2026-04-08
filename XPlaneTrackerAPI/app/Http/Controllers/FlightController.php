<?php

namespace App\Http\Controllers;

use App\Models\Flight;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;

class FlightController extends Controller
{
    public function index()
    {
        return response()->json(Flight::all());
    }

    public function store(Request $request)
    {
        $request->validate([
            'flight_file' => 'required|file'
        ]);

        $file = $request->file('flight_file');

        $content = gzdecode(file_get_contents($file->getRealPath()));
        $data = json_decode($content, true);

        $path = $file->store('flights');

        $flight = Flight::create([
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
        $path = storage_path('app/private/' . $flight->file_path);

        if (!file_exists($path)) {
            $path = storage_path('app/' . $flight->file_path);
        }

        if (!file_exists($path)) {
            return response()->json(['error' => 'File not found'], 404);
        }

        return response()->file($path, [
            'Content-Type' => 'application/json',
            'Content-Encoding' => 'gzip',
        ]);
    }

    public function update(Request $request, Flight $flight)
    {
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
        Storage::delete($flight->file_path);
        $flight->delete();

        return response()->json(null, 204);
    }
}
