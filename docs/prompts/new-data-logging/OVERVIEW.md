# Overview

Inside @XPlaneTracker directory, I have a python application, that tracks the user's movements. It currently only tracks basic data.

# Tasks

Your main task is to implement the below features, while preserving existing logic, especially(!!) landing rate monitoring!

# Task #1

Please confirm, what type of altitude does it log. It does not log the same thing that is on my correctly set altimeter, i want to also log that, it needs to work with weather set to real & also with simulated non-real weather setting in both MSFS and X-Plane. The currently logged altitude should also be logged along with that.

# Task #2
Log the true and magnetic heading of the aircraft as well.

# Task #3
When landing, also log the ICAO code of the airport where the user have landed on.

# Task #4
Discord log: Instead of ICAO code, show full airport name, eg.: Budapest Liszt Ferenc International Airport
Instead of full route, show Departure airport name - Arrival airport name, with a discord flag emoji - Closes github issue #14

# Task #5
Log the following data in the metadata section:
- 