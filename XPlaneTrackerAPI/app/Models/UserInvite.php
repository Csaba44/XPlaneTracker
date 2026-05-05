<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class UserInvite extends Model
{
    protected $fillable = [
        'email',
        'name',
        'is_admin',
        'token',
        'invited_by',
    ];

    public function inviter()
    {
        return $this->belongsTo(User::class, 'invited_by');
    }
}
