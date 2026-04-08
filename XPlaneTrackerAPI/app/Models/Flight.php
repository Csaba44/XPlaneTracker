<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Flight extends Model
{
    protected $fillable = [
        'callsign',
        'flight_number',
        'airline',
        'start_time',
        'file_path'
    ];
}
