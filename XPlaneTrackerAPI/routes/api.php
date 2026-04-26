<?php

use App\Http\Controllers\AdminUserController;
use App\Http\Controllers\AirportFeaturesController;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\FlightController;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\FriendController;
use App\Http\Controllers\LeaderboardController;
use App\Http\Controllers\ProfileController;
use App\Http\Controllers\RunwayController;

Route::post('/login', [AuthController::class, 'login']);

Route::get('/runways', [RunwayController::class, 'getRunways']);

Route::middleware('auth:sanctum')->group(function () {

    Route::post('/logout', [AuthController::class, 'logout']);
    Route::get('/user', [AuthController::class, 'user']);
    Route::post('/tokens/create', [AuthController::class, 'createToken']);

    Route::get('/flights', [FlightController::class, 'index']);
    Route::post('/flights', [FlightController::class, 'store']);
    Route::put('/flights/{flight}', [FlightController::class, 'update']);
    Route::delete('/flights/{flight}', [FlightController::class, 'destroy']);
    Route::get('/flights/friends', [FlightController::class, 'friendsFlights']);

    Route::get('/admin/users', [AdminUserController::class, 'index']);
    Route::post('/admin/users', [AdminUserController::class, 'store']);
    Route::put('/admin/users/{user}', [AdminUserController::class, 'update']);
    Route::delete('/admin/users/{user}', [AdminUserController::class, 'destroy']);

    Route::put('/user/profile', [ProfileController::class, 'update']);

    Route::get('/friends', [FriendController::class, 'index']);
    Route::get('/friends/requests', [FriendController::class, 'requests']);
    Route::get('/friends/search', [FriendController::class, 'search']);
    Route::post('/friends', [FriendController::class, 'store']);
    Route::patch('/friends/{friendId}/accept', [FriendController::class, 'accept']);
    Route::delete('/friends/{friendId}', [FriendController::class, 'destroy']);

    // Add this to your API routes
    Route::get('/leaderboard', [LeaderboardController::class, 'index']);

    Route::get('/airport-features', [AirportFeaturesController::class, 'getFeatures']);
});

Route::get('/flights/{flight}', [FlightController::class, 'show']);
