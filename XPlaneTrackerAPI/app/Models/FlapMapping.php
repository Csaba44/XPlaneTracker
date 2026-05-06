<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class FlapMapping extends Model
{
    protected $fillable = [
        'simulator',
        'aircraft_icao',
        'flap_index',
        'label',
        'is_approved',
        'user_id',
    ];

    protected $casts = [
        'is_approved' => 'boolean',
    ];

    public function user()
    {
        return $this->belongsTo(User::class);
    }
}
