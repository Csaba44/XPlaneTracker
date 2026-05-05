# Test Plan: Bounce and Touch & Go Detection

The logic for ground departures has been completely unified in `flight_state.py`. To ensure both features work across X-Plane and MSFS, follow these test scenarios.

## Pre-requisites
- Ensure the Python client (`XPlaneTracker`) is running. You can check the output JSON file in the `flights` directory after the test, or monitor the console if running via `python main.py`.
- Run the tests in both simulators sequentially: MSFS and X-Plane.

## Test Scenario 1: Normal Liftoff
1. Start at a runway.
2. Accelerate down the runway to >50 knots ground speed.
3. Rotate and liftoff.
4. **Verification**: 
   - A `liftoff` event should be logged.
   - The flight phase should transition to `climb`.

## Test Scenario 2: The Bounce (≤ 3 seconds)
1. Perform a normal approach.
2. Touchdown on the runway.
   - **Verification**: A `touchdown` event should be logged. Flight phase ends.
3. Immediately pitch up to forcefully lift off the runway within 1 to 2 seconds.
4. Let the aircraft touch down again.
5. **Verification**:
   - The brief liftoff must generate a `bounce` event.
   - It **must not** generate a `liftoff` event.
   - It **must not** transition the phase to `climb`.
   - The subsequent landing will generate a second `touchdown` event.

## Test Scenario 3: Touch and Go (3 to 10 seconds)
1. Perform a normal approach.
2. Touchdown smoothly.
   - **Verification**: A `touchdown` event is logged.
3. Keep the wheels on the ground for roughly 5 to 7 seconds while maintaining speed above 50 knots.
4. Apply takeoff thrust and lift off.
5. **Verification**:
   - A `touch_and_go` event should be logged when the aircraft lifts off.
   - It **must not** generate a `liftoff` event.
   - The flight phase should transition to `climb`.

## Edge Case Verifications
- If you touch down, decelerate below 50 knots, and *then* take off again, it will trigger a normal `liftoff`. (This is intended behavior for a taxi-back or full stop-and-go).