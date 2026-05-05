<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Validation\Rule;

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

        $html = "
        <div style=\"font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;\">
            <h2>You've been invited to Csabolanta!</h2>
            <p><strong>{$inviterName}</strong> has invited you to join Csabolanta.</p>
            <p>Click the button below to create your account and set your password:</p>
            <div style=\"margin: 30px 0;\">
                <a href=\"{$registerUrl}\" style=\"display: inline-block; padding: 12px 24px; background-color: #38bdf8; color: #1c222d; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;\">Create Account</a>
            </div>
            <p style=\"margin-top: 20px; font-size: 12px; color: #666;\">If the button doesn't work, copy and paste this link into your browser: <br> <a href=\"{$registerUrl}\" style=\"color: #38bdf8;\">{$registerUrl}</a></p>
        </div>";

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
}
