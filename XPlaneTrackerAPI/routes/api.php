<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\FlightController;
use App\Http\Controllers\AuthController;

// Public routes
Route::post('/login', [AuthController::class, 'login']);

Route::post('/login', [AuthController::class, 'login']);

Route::middleware('auth:sanctum')->group(function () {

    Route::post('/logout', [AuthController::class, 'logout']);
    Route::get('/user', [AuthController::class, 'user']);
    Route::post('/tokens/create', [AuthController::class, 'createToken']);

    Route::get('/flights', [FlightController::class, 'index']);
    Route::post('/flights', [FlightController::class, 'store']);
    Route::get('/flights/{flight}', [FlightController::class, 'show']);
    Route::put('/flights/{flight}', [FlightController::class, 'update']);
    Route::delete('/flights/{flight}', [FlightController::class, 'destroy']);
});
