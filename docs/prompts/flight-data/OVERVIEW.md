# Overview

This new feature will be a new menu option inside the FlightMap.vue component, a new button just like "Kapcsolatok". It will replace the flight map view (or overlay it) and it will display different analysis tabs. On the top, the user can switch between different tabs. The following types of analyses will be eventually included:

- General data
- Departure analysis
- Approach analysis

Our development may or may not follow the order described here. You will need to first create all of the tabs, first with no data, just a text saying its empty. The first thing we will work on is @docs/prompts/flight-data/APPROACH.md. Other prompts will later follow when this feature is done.

# Workflow

- **Charts**: All charts should use a package, whatever is the most suitable for the job. If needed, you can install new chart packages along with the existing ones. It should be draggable and zoomable.
- **Units**: All runway lengths are in METERS, all height, elevation and altitude is in FEET.
