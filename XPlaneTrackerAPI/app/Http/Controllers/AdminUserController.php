<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Validation\Rule;
use Illuminate\Support\Facades\View;

class AdminUserController extends Controller
{
    public function index(Request $request)
    {
        if (!$request->user() || !$request->user()->is_admin) {
            return response()->json(['error' => 'Unauthorized'], 403);
        }

        return response()->json(User::all());
    }

    public function store(Request $request)
    {
        if (!$request->user() || !$request->user()->is_admin) {
            return response()->json(['error' => 'Unauthorized'], 403);
        }

        $validated = $request->validate([
            'name' => 'nullable|string|max:255',
            'email' => 'required|string|email|max:255|unique:users|unique:user_invites',
            'is_admin' => 'boolean'
        ]);

        $token = \Illuminate\Support\Str::random(32);

        $invite = \App\Models\UserInvite::create([
            'email' => $validated['email'],
            'name' => $validated['name'] ?? null,
            'is_admin' => $validated['is_admin'] ?? false,
            'token' => $token,
            'invited_by' => $request->user()->id,
        ]);

        $domain = env('APP_URL', 'https://csabolanta.hu');
        $registerUrl = "{$domain}/register?token={$token}";
        $inviterName = $request->user()->name;

        $html = View::make('emails.invite', [
            'inviterName' => $inviterName,
            'registerUrl' => $registerUrl
        ])->render();

        \Illuminate\Support\Facades\Http::withToken(config('services.resend.key'))->post('https://api.resend.com/emails', [
            'from' => 'Csabolanta Invites <onboarding@csabolanta.hu>',
            'to' => [$validated['email']],
            'subject' => 'Join Csabolanta!',
            'html' => $html,
        ]);

        return response()->json($invite, 201);
    }

    public function update(Request $request, User $user)
    {
        if (!$request->user() || !$request->user()->is_admin) {
            return response()->json(['error' => 'Unauthorized'], 403);
        }

        $validated = $request->validate([
            'name' => 'sometimes|required|string|max:255',
            'email' => [
                'sometimes',
                'required',
                'string',
                'email',
                'max:255',
                Rule::unique('users')->ignore($user->id),
            ],
            'password' => 'nullable|string|min:8',
            'is_admin' => 'boolean'
        ]);

        if (isset($validated['name'])) {
            $user->name = $validated['name'];
        }

        if (isset($validated['email'])) {
            $user->email = $validated['email'];
        }

        if (isset($validated['is_admin'])) {
            $user->is_admin = $validated['is_admin'];
        }

        if (!empty($validated['password'])) {
            $user->password = Hash::make($validated['password']);
        }

        $user->save();

        return response()->json($user);
    }

    public function destroy(Request $request, User $user)
    {
        if (!$request->user() || !$request->user()->is_admin) {
            return response()->json(['error' => 'Unauthorized'], 403);
        }

        if ($request->user()->id === $user->id) {
            return response()->json(['error' => 'Cannot delete yourself'], 400);
        }

        $user->delete();

        return response()->json(null, 204);
    }

    public function getInvites(Request $request)
    {
        if (!$request->user() || !$request->user()->is_admin) {
            return response()->json(['error' => 'Unauthorized'], 403);
        }

        $invites = \App\Models\UserInvite::with('inviter')->orderBy('created_at', 'desc')->get();
        return response()->json($invites);
    }

    public function updateInvite(Request $request, \App\Models\UserInvite $invite)
    {
        if (!$request->user() || !$request->user()->is_admin) {
            return response()->json(['error' => 'Unauthorized'], 403);
        }

        $validated = $request->validate([
            'name' => 'nullable|string|max:255',
        ]);

        $invite->name = $validated['name'];
        $invite->save();

        // Reload the inviter relation to return it
        $invite->load('inviter');

        return response()->json($invite);
    }

    public function revokeInvite(Request $request, \App\Models\UserInvite $invite)
    {
        if (!$request->user() || !$request->user()->is_admin) {
            return response()->json(['error' => 'Unauthorized'], 403);
        }

        $invite->delete();

        return response()->json(null, 204);
    }
}
