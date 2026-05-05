Task #1
Your task is to create two similar features below the approach analysis part.
Inside the analysis panel @XPlaneTrackerFrontend/src/components/FlightAnalysisPanel.vue you will implement a similar feature to my image.
- @docs/prompts/touchdown-analysis/landing-rwy.png (data from bottom, only need: rate, gforce, runway, td point (no%), speed, pitch, roll (add it))
- @docs/prompts/touchdown-analysis/takeoff-rwy.png only need liftoff speed, pitch, roll, runway, takeoff roll, climb rate, max centerline dev


The green point marks the point of the touchdown or liftoff.

Landing: The light-green marking shows the TDZ. You should also show the aiming point accurately. Please plan out how you'll do these ACCURATELY.
Please display everything in meters instead of feet. You should be aware that while most runways are 45m wide, there are exceptions! What source will you use? Use caching if a new one.

Task #2
On the approach analysis the user should be able to toggle to show flaps and gear down events (please log gear down as event too in py - also make sure it is displayed in the timeline @XPlaneTrackerFrontend/src/components/FlightTimelineTab.vue and also on the flight map as an event)

# main task
PLease ask your questions, and create a plan to @docs/plans