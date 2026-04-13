<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('friendships', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->foreignId('friend_id')->constrained('users')->cascadeOnDelete();
            $table->enum('status', ['pending', 'accepted'])->default('pending');
            $table->timestamps();

            // Prevent users from sending multiple requests to the same person
            $table->unique(['user_id', 'friend_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('friendships');
    }
};
