<?php

namespace App\Http\Controllers;

use App\Models\FlapMapping;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class FlapMappingController extends Controller
{
    public function index(Request $request)
    {
        $request->validate([
            'simulator' => 'required|string',
            'aircraft_icao' => 'required|string|size:4',
        ]);

        if ($request->aircraft_icao === 'unknown') {
            return response()->json([]);
        }

        $query = FlapMapping::where('simulator', $request->simulator)
            ->where('aircraft_icao', $request->aircraft_icao)
            ->where('is_approved', true);

        return response()->json($query->get());
    }

    public function store(Request $request)
    {
        $request->validate([
            'simulator' => 'required|string',
            'aircraft_icao' => 'required|string|size:4',
            'flap_index' => 'required|string',
            'label' => 'required|string|max:50',
        ]);

        if ($request->aircraft_icao === 'unknown') {
            return response()->json(['message' => 'Cannot create mappings for unknown aircraft.'], 422);
        }

        // Check if an approved mapping already exists
        $exists = FlapMapping::where('simulator', $request->simulator)
            ->where('aircraft_icao', $request->aircraft_icao)
            ->where('flap_index', $request->flap_index)
            ->where('is_approved', true)
            ->exists();

        if ($exists) {
            return response()->json(['message' => 'An approved mapping already exists.'], 409);
        }

        $mapping = FlapMapping::create([
            'simulator' => $request->simulator,
            'aircraft_icao' => $request->aircraft_icao,
            'flap_index' => $request->flap_index,
            'label' => $request->label,
            'is_approved' => false,
            'user_id' => Auth::id(),
        ]);

        return response()->json($mapping, 201);
    }

    public function adminIndex()
    {
        return response()->json(FlapMapping::with('user')->orderBy('created_at', 'desc')->get());
    }

    public function approve(FlapMapping $flapMapping)
    {
        $flapMapping->update(['is_approved' => true]);
        return response()->json($flapMapping);
    }

    public function reject(FlapMapping $flapMapping)
    {
        $flapMapping->delete();
        return response()->json(null, 204);
    }
}
