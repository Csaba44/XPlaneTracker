<?php

use Illuminate\Support\Facades\Broadcast;
use Illuminate\Support\Facades\DB;

Broadcast::channel('live-flight.{pilotId}', function ($user, $pilotId) {
    if ($user->id === (int) $pilotId) {
        return true;
    }

    return DB::table('friendships')
        ->where('status', 'accepted')
        ->where(function ($query) use ($user, $pilotId) {
            $query->where('user_id', $user->id)->where('friend_id', $pilotId)
                ->orWhere('user_id', $pilotId)->where('friend_id', $user->id);
        })
        ->exists();
});
