<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;

class FriendController extends Controller
{
    // List all accepted friends
    public function index()
    {
        $user = Auth::user();
        return response()->json($user->friends);
    }

    // Search for users to add (excluding yourself)
    public function search(Request $request)
    {
        $query = $request->input('query');

        if (!$query) {
            return response()->json([]);
        }

        $users = User::where('id', '!=', Auth::id())
            ->where(function ($q) use ($query) {
                $q->where('name', 'LIKE', "%{$query}%")
                    ->orWhere('email', 'LIKE', "%{$query}%");
            })
            ->limit(10)
            ->get();

        return response()->json($users);
    }

    // Send a friend request (or auto-accept for now)
    public function store(Request $request)
    {
        $request->validate([
            'friend_id' => 'required|exists:users,id'
        ]);

        $userId = Auth::id();
        $friendId = $request->friend_id;

        if ($userId == $friendId) {
            return response()->json(['message' => 'You cannot add yourself.'], 400);
        }

        // Check if a relationship already exists in either direction
        $exists = DB::table('friendships')
            ->where(function ($query) use ($userId, $friendId) {
                $query->where('user_id', $userId)->where('friend_id', $friendId);
            })
            ->orWhere(function ($query) use ($userId, $friendId) {
                $query->where('user_id', $friendId)->where('friend_id', $userId);
            })
            ->exists();

        if ($exists) {
            return response()->json(['message' => 'Friendship or request already exists.'], 400);
        }

        // Create the friendship. 
        // Note: Setting status to 'accepted' instantly for testing, 
        // you can change this to 'pending' when you build the accept UI.
        DB::table('friendships')->insert([
            'user_id' => $userId,
            'friend_id' => $friendId,
            'status' => 'accepted',
            'created_at' => now(),
            'updated_at' => now(),
        ]);

        return response()->json(['message' => 'Friend added successfully.']);
    }

    // Remove a friend
    public function destroy($friendId)
    {
        $userId = Auth::id();

        DB::table('friendships')
            ->where(function ($query) use ($userId, $friendId) {
                $query->where('user_id', $userId)->where('friend_id', $friendId);
            })
            ->orWhere(function ($query) use ($userId, $friendId) {
                $query->where('user_id', $friendId)->where('friend_id', $userId);
            })
            ->delete();

        return response()->json(['message' => 'Friend removed.']);
    }
}
