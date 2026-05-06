<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('flap_mappings', function (Blueprint $table) {
            $table->id();
            $table->string('simulator');
            $table->string('aircraft_icao')->nullable();
            $table->string('flap_index');
            $table->string('label');
            $table->boolean('is_approved')->default(false);
            $table->foreignId('user_id')->nullable()->constrained()->nullOnDelete();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('flap_mappings');
    }
};
