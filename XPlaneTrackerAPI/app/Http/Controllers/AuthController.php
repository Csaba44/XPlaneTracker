<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Validation\ValidationException;

class AuthController extends Controller
{
    /**
     * Get invite details by token.
     */
    public function getInvite($token)
    {
        $invite = \App\Models\UserInvite::where('token', $token)->first();

        if (!$invite) {
            return response()->json(['error' => 'Invalid or expired invite token'], 404);
        }

        return response()->json([
            'email' => $invite->email,
            'name' => $invite->name,
        ]);
    }

    /**
     * Register a new user with an invite token.
     */
    public function register(Request $request)
    {
        $validated = $request->validate([
            'token' => 'required|string',
            'name' => 'required|string|max:255',
            'password' => 'required|string|min:8|confirmed',
        ]);

        $invite = \App\Models\UserInvite::where('token', $validated['token'])->first();

        if (!$invite) {
            return response()->json(['error' => 'Invalid or expired invite token'], 404);
        }

        // Check if user already exists (edge case)
        if (\App\Models\User::where('email', $invite->email)->exists()) {
            return response()->json(['error' => 'User with this email already exists'], 400);
        }

        $user = \App\Models\User::create([
            'name' => $validated['name'],
            'email' => $invite->email,
            'password' => \Illuminate\Support\Facades\Hash::make($validated['password']),
            'is_admin' => $invite->is_admin,
        ]);

        $invite->delete();

        return response()->json(['message' => 'Registration successful', 'user' => $user], 201);
    }

    /**
     * Handle an authentication attempt.
     */
    public function login(Request $request)
    {
        $credentials = $request->validate([
            'email' => ['required', 'email'],
            'password' => ['required'],
        ]);

        if (Auth::attempt($credentials)) {
            // Regenerate the session to prevent session fixation attacks
            $request->session()->regenerate();

            return response()->json([
                'message' => 'Login successful',
                'user' => Auth::user()
            ]);
        }

        // If auth fails, throw a standard validation exception
        throw ValidationException::withMessages([
            'email' => ['The provided credentials do not match our records.'],
        ]);
    }

    /**
     * Log the user out of the application.
     */
    public function logout(Request $request)
    {
        Auth::guard('web')->logout();

        // Invalidate the session and regenerate the CSRF token
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return response()->json([
            'message' => 'Logged out successfully'
        ], 200);
    }

    public function createToken(Request $request)
    {
        $request->user()->tokens()->where('name', 'xtracker-cli')->delete();

        $token = $request->user()->createToken('xtracker-cli');

        return response()->json([
            'token' => $token->plainTextToken
        ]);
    }

    /**
     * Get the authenticated user.
     */
    public function user(Request $request)
    {
        return response()->json($request->user());
    }
}
