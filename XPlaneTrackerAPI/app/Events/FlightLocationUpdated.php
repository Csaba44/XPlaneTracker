<?php

namespace App\Events;

use Illuminate\Broadcasting\PrivateChannel;
use Illuminate\Contracts\Broadcasting\ShouldBroadcastNow;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class FlightLocationUpdated implements ShouldBroadcastNow
{
    use Dispatchable, SerializesModels;

    public array $flightData;

    public function __construct(array $flightData)
    {
        $this->flightData = $flightData;
    }

    public function broadcastOn(): array
    {
        return [
            new PrivateChannel('live-flight.' . $this->flightData['user_id']),
        ];
    }

    public function broadcastAs(): string
    {
        return 'flight.updated';
    }
}
