<?php

namespace App\Models;

// use Illuminate\Contracts\Auth\MustVerifyEmail;
use Database\Factories\UserFactory;
use Illuminate\Database\Eloquent\Attributes\Fillable;
use Illuminate\Database\Eloquent\Attributes\Hidden;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Laravel\Sanctum\HasApiTokens;

#[Fillable(['name', 'email', 'password'])]
#[Hidden(['password', 'remember_token'])]
class User extends Authenticatable
{
    /** @use HasFactory<UserFactory> */
    use HasApiTokens, HasFactory, Notifiable;
    /**
     * Get the attributes that should be cast.
     *
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'email_verified_at' => 'datetime',
            'password' => 'hashed',
        ];
    }

    // Users that this user added
    public function friendsAdded()
    {
        return $this->belongsToMany(User::class, 'friendships', 'user_id', 'friend_id')
            ->withPivot('status')
            ->withTimestamps();
    }

    // Users that added this user
    public function friendsAddedBy()
    {
        return $this->belongsToMany(User::class, 'friendships', 'friend_id', 'user_id')
            ->withPivot('status')
            ->withTimestamps();
    }

    // A helper to get ALL accepted friends in one collection
    public function getFriendsAttribute()
    {
        $added = $this->friendsAdded()->wherePivot('status', 'accepted')->get();
        $addedBy = $this->friendsAddedBy()->wherePivot('status', 'accepted')->get();

        return $added->merge($addedBy);
    }

    public function flights(): HasMany
    {
        return $this->hasMany(Flight::class);
    }
}
