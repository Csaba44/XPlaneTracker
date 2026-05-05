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
        if (!Schema::hasColumn('flights', 'schema_version')) {
            Schema::table('flights', function (Blueprint $table) {
                $table->string('schema_version', 20)->nullable()->after('file_path');
            });
        }
    }

    public function down(): void
    {
        Schema::table('flights', function (Blueprint $table) {
            $table->dropColumn('schema_version');
        });
    }
};
