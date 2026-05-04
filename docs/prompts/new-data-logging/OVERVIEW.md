# Overview

Inside @XPlaneTracker directory, I have a python application, that tracks the user's movements. It currently only tracks basic data.

I also got you example simbrief data at: @docs/prompts/new-data-logging/example-simbrief-response.json

# Tasks

Your main task is to implement the below features, while preserving existing logic, especially(!!) landing rate monitoring!
You should determine the best way to implement this, sometimes it's better not to log data to the file, but append to it when it is uploaded to the server. You should focus on performance keeping sub 1% CPU usage, and absolutely minimum VRAM usage by the python app. This application is performance focused, it should not disturb the main gameplay ever, even on a low-end pc. Focus on keeping file sizes minimum, but also do not change existing logic, and do not re-structure the file drastically. The backend and frontend should still work (just shows NIL information of things it does not have access to) for older versions of the app, so please determine a system, where we can append the app version number in the file metadata, and the API will be able to determine what to do with that specific version. Focus on keeping the code readable, and modular.

Please be sure to equally support X-Plane and MSFS20/24 too, and make sure both simulators follow the exact same structure in terms of datastructure of the output file. 

## Task #1

Please confirm, what type of altitude does it log. It does not log the same thing that is on my correctly set altimeter, i want to also log that, it needs to work with weather set to real & also with simulated non-real weather setting in both MSFS and X-Plane. The currently logged altitude should also be logged along with that.

## Task #2
Log the true and magnetic heading of the aircraft as well. Log pitch, roll for every position.

## Task #3
When landing, also log the ICAO code of the airport where the user have landed on. Log how long the rollout was (meters), log the pitch and the roll on landing. Log where the aircraft touched down (for example 300m from threshold).

## Task #4
Discord log: Instead of ICAO code, show full airport name, eg.: Budapest Liszt Ferenc International Airport
Instead of full route, show Departure airport name - Arrival airport name, with a discord flag emoji - Closes github issue #14

## Task #5
Log the following data in the metadata section:
- Timeline: off block time (only counts for first movement or engine start, does not matter if the user lands at another airport and in the same flight, starts moving again after shutdown), simbrief EOBT, flight time, taxi time (when the aircraft starts moving after engine start), takeoff time, landing time (final landing, where the user did not took off again after landing), taxi in time (user vacates the runway, till he comes to a full stop at the gate and does not move again), on-block time (after user stopped on the gate and did not move again), and block time (on-block - off-block time), simbrief scheduled arrival, and the difference of the actual one.
- Overall distance travelled, average groundspeed
- Weight: ZFW, TOW, LDW, Empty weight (if possible to determine EW)
- Fuel: block fuel (fuel on the ramp, in the last moment, before movement occurs), takeoff fuel, total fuel used, landing fuel, fuel flow/hr

## Task #6
Log events, such as:
- Log stalls
- Gear up/down (also log where, and at what altitude)
- Flaps extended or retracted
- Engine starts (with number, eg Engine 1 started)
- Lift-off (log pitch, max pitch, roll, ias, gs)
- Climb, cruise, descent phase logs (support GA flights, with multiple airport touch&goes too, may be more climb and cruise segments)

## Task #7
Add the option to save, but do not upload the created output when ending the flight

## Task #8
Come up with a smart system, that gives you a windows notification, when it thinks you've forgot to upload the file. If the user uses replay mode in xplane, give a notification, that he didn't upload the file. When the user stops, and shuts down the engine, it might send a notification, to not forget to upload. When exiting, ask the user if he wants to upload first, and give the same options when pressing stop flight manually.

## Task #9
Under general data tab in @XPlaneTrackerFrontend/src/components/FlightAnalysisPanel.vue, list the newly logged metadata, events, etc. Create a visually appealing design, and make sure it is readable, the user can easily find what they want.
Create a visually appealing timeline, where the user can see each event that happened, including stalls, landing, takeoff, start of taxi, etc. Show the timestamp of it too (only time, no date, show the date once on top maybe)


## Task #10
When the user uploaded a file with the new version's structure (or however you determine it), use those under approach analysis, but only if you think, using the new data (like heading, and barometric altitude) will improve the results. Use the current version as fallback, for users who did not download the newer version. Also display a message in general data for them, to update, to see these data.

## Task #11
Give me an order to test these, first, give me what should I fly in the sim, that will test all of these new capabilities in a short period of time, that exhausts every edge case, and can be done fast, I'll first use X-Plane then MSFS 2024. Then tell me what to look for in the web app.

# Instructions
Please ask me questions until you are at least 95% sure what you think, is what I really want. Create a new file with the plans under @docs/plans. Do not write any code yet.