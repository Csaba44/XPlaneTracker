<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Flight extends Model
{
    protected $fillable = [
        'user_id',
        'callsign',
        'flight_number',
        'airline',
        'start_time',
        'file_path'
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }
}
