<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Redis;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;
use App\Events\FlightLocationUpdated;

class LiveFlightController extends Controller
{
    public function index()
    {
        $user = Auth::user();

        $friendIds = DB::table('friendships')
            ->where('status', 'accepted')
            ->where(function ($query) use ($user) {
                $query->where('user_id', $user->id)->orWhere('friend_id', $user->id);
            })
            ->get()
            ->map(function ($friendship) use ($user) {
                return $friendship->user_id === $user->id ? $friendship->friend_id : $friendship->user_id;
            })
            ->toArray();

        $friendIds[] = $user->id;

        $activeFlights = [];

        foreach ($friendIds as $id) {
            $data = Redis::get('live_flight:' . $id);

            if ($data) {
                $flightState = json_decode($data, true);

                $pathData = Redis::lrange('live_flight_path:' . $id, 0, -1);

                $flightState['path'] = array_map(function ($pt) {
                    return json_decode($pt, true);
                }, $pathData);

                $activeFlights[] = $flightState;
            }
        }

        return response()->json($activeFlights);
    }

    public function update(Request $request)
    {
        $validated = $request->validate([
            'user_id' => 'required|integer',
            'lat' => 'required|numeric',
            'lon' => 'required|numeric',
            'alt' => 'required|numeric',
            'gs' => 'required|numeric',
            'heading' => 'required|numeric',
            'timestamp' => 'required|integer',
            'landing' => 'sometimes|boolean',
        ]);

        $redisKey = 'live_flight:' . $validated['user_id'];
        $pathKey = 'live_flight_path:' . $validated['user_id'];

        Redis::setex($redisKey, 300, json_encode($validated));

        $point = json_encode([
            $validated['lat'],
            $validated['lon'],
            $validated['alt'],
            $validated['timestamp']
        ]);

        Redis::rpush($pathKey, $point);
        Redis::expire($pathKey, 300);

        broadcast(new FlightLocationUpdated($validated));

        return response()->json(['status' => 'ok']);
    }
}
