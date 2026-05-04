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







# You have already asked questions, here they are with answers:
Key questions:                                                                                                                                        
  
  Altitude (Task #1)                                                                                                                                    
  1. Want 3 alts logged each point (geometric MSL/current, indicated baro, AGL) or just 2 (current + indicated baro)? Indicated baro = altimeter w/
  pilot's QNH set. AGL useful for landing/approach analysis.                                                                                            
  2. X-Plane indicated alt source: sim/cockpit2/gauges/indicators/altitude_ft_pilot OK? MSFS: INDICATED_ALTITUDE. Confirm?
                                                                                                                                                        
  Telemetry size (Task #2)                                                                                                                              
  3. Pitch/roll/heading every point conflicts w/ "min file size". Acceptable: round pitch/roll to 1 decimal (0.1°), heading to integer (1°)? Saves ~50%
  chars.                                                                                                                                                
  4. Log mag heading + true heading separately, or true + magvar once in metadata?
                                                                                                                                                        
  Phase/event detection (Task #6)                             
  5. Stall detection: sim stall warning dataref/var (binary), or alpha threshold? Stall warning simpler + cross-sim consistent.                         
  6. Phase transitions (climb/cruise/descent): rule = VS > +500fpm climb, |VS| < 200 cruise (sustained 60s), VS < -500 descent? OK?                     
  7. Engine start: log "Engine N started" - X-Plane has per-engine N1/N2 or running flag (sim/flightmodel/engine/ENGN_running[N]). MSFS:                
  ENG_COMBUSTION:N. Confirm OK?                                                                                                                         
                                                                                                                                                        
  Timing (Task #5)                                                                                                                                      
  8. "Off-block" = first wheel movement OR first engine start, whichever earlier? Or strictly engine start if engines, fallback movement?
  9. "Final landing" detection: last touchdown where user did NOT take off again within X minutes. What X? 5min? Or detect via engine shutdown after    
  landing?                                                                                                                                              
  10. SimBrief EOBT/scheduled arrival: pull at flight start (already have fetch), store in metadata. OK?                                                
                                                                                                                                                        
  Touchdown details (Task #3)                                 
  11. "Where touched down (300m from threshold)": need runway data. Use existing rwy heading derivation logic + rwy DB lookup? Have airport DB but need 
  runway threshold coords. Use OurAirports runways.csv (similar source)? OK?                                                                            
                                
  Versioning                                                                                                                                            
  12. Schema version scheme: metadata.schema_version: 2 (int bump) or semver string "2.0.0"? Backend dispatches per version. Suggest int simpler.
  13. Old client still works on backend (shows N/A for missing fields) - confirm: backend should never reject older v1 uploads, just feature-flag the   
  new analyses.                                                                                                                                         
                                                                                                                                                        
  Notifications (Task #8)                                                                                                                               
  14. Toast lib: win10toast or winotify? Latter more modern + supports buttons. OK?
  15. Replay mode detection X-Plane: sim/time/is_in_replay dataref. MSFS: no clean equivalent — skip MSFS replay detect, only X-Plane?                  
                                                                                                                                                        
  Save-without-upload (Task #7)                                                                                                                         
  16. Stop button flow change: add 2 buttons "Stop & Upload" / "Stop & Save Only"? Or single stop → dialog asks?                                        
                                                                                                                                                        
  Frontend (Task #9-10)         
  17. Timeline component placement: new tab in FlightAnalysisPanel or extend "General" tab? Suggest new tab "Timeline" cleaner.                         
  18. Approach analysis upgrade: when v2 file present + has baro alt, recompute approach using baro alt for stabilization checks? Or only use heading   
  for runway match improvement?                                                                                                                         
                                                                                                                                                        
  Answer these, write plan to docs/plans/new-data-logging.md. No code yet.       



## Answers: 
#1
1. i dont want agl initially
2. You need to determine these, i don't know, but use files: 
- MSFS: @XPlaneTracker/msfs_simvars.txt
- X-Plane: XPlaneTracker/datarefs.json

#2
3. Lets not log pitch, roll on every point, but on events, DO log them (landing, takeoff, stall etc.). Use heading rounded to to decimal places.
4. Log mag and true heading separately, because magvar will change across the flight

#6
5. Use the absolute best way in every simulator to determine a stalled condition. It's acceptable, that it'll work better in one sim, don't dumb-down because the other sim's sdk is worse.
6. I think you can do better than that. Vs < 200 cruise is not cruise, if i am climbing at 100fpm for 10minutes i'll climb 1000ft. Come up with a better solution, and please get my confirmation and approval.
7. Also, look at the files to determine, use best way in each sim.

#5
8. first wheel movement OR first engine start, whichever earlier
9. Not within X minutes, log the last one, when the user shuts down the flight, log it. 
10. Ok

#3
11.  Use OurAirports runways.csv

Versioning
12. semver string, github tag version
13. confirmed, backend shouldnt reject old ones

Notifications
14. You can use the one that you think is better for this case, but please make sure there is no performance degradation! Also, update release file for github build to work with packages: @.github/workflows/release.yml
15. MSFS does not have replay, confirmed.

#7
16. Single stop dialog asks

Frontend #9-10
17. General tab, and timeline tab too
18. When v2 file is present has baro alt, do recompute approach please.

# Task
Now, create the plan save it to plans dir.