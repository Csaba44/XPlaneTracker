# Approach analysis tab

## Layout

This tab will be split into two sections. The lateral profile, and the vertical profile. The two charts should be side by side, and they should look like the image reference. Image reference: @/home/csaba/projects/XPlaneTracker/.cp-images/approach_analysis.png

## Obtaining data

The flight data is described in @CLAUDE.md. The runway geometry may be fetched via GET /runways (lat, lon included in the request body (coordinates of the touchdown)). The airport and runway data is fetched via /airport/{icao}/runways. Here is an example, of what the data looks like: @docs/prompts/flight-data/airport.json and @docs/prompts/flight-data/runways.json

## Lateral profile

It will show the deviation from the localizer course. First, you need to determine which runway is the user approaching since data does not conain that. Consider what would be the best way of doing this, and put that into an implementation plan.

# Lateral Profile Chart Specification

## 1. Coordinate System (Axes)

### X-Axis: Deviation

- **Label:** `Deviation (ft)` (Centered at bottom)
- **Range:** -2,900 to 2,900
- **Center Point:** 0 (Runway Centerline)
- **Scale:** Linear
- **Major Ticks:** -2,900, -2,000, -1,000, 0, 1,000, 2,000, 2,900

### Y-Axis: Distance

- **Label:** `NM to Threshold` (Rotated 90° CCW, left side)
- **Range:** 0.0 to minimum 8.00 or whenever the aircraft was established on the final approach course (+/- 10degrees).
- **Orientation:** **Inverted**. 0.0 is at the top (destination); 8.0 (or whenever established) is at the bottom (start of approach).
- **Major Ticks:** Every 1.0 unit (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, etc.)

## 2. Visual Markings and Geometry

- **Centerline:** Vertical dashed line (light-gray) at x = 0 extending the full height of the chart.
- **LOC (Localizer) Funnel:** Two symmetrical diagonal dashed lines (light-gray) originating at the top center (0, 0) and fanning outwards as they move toward the bottom.
- **Grid:** Subtle dark-gray orthogonal grid lines aligned with major ticks.
- **Data Path:** Solid purple line representing the aircraft's lateral position.
- **Focus Indicator:** Large solid purple circle overlaying the data path at the specific point of interest.

## 3. UI Elements and Legend

- **Header:** "LATERAL PROFILE" (Top-left, uppercase).
- **Legend:**
  - Solid purple line: `Aircraft Path`
  - Dashed dark gray line: `LOC (2.5°)`
  - Dashed light gray line: `Centerline`
- **Interactive Elements:** "Reset" text label in the top-right corner.
- **Tooltip:** Floating black rounded box with a purple icon containing:
  - **Dev:** (e.g., "145ft Right")
  - **Dist:** (e.g., "6.0 NM")

## 4. Aesthetic Style

- **Theme:** Dark Mode
- **Background:** Utilize design skill to determine
- **Primary Data Color:** Vivid Purple
- **Text/Axis Color:** Muted Light Gray
- **Grid/Reference Color:** Dark Slate Gray

# Vertical Approach Profile Chart Specification

## 1. Coordinate System (Axes)

### X-Axis: Distance

- **Label:** `NM to Threshold` (Centered at bottom)
- **Range:** 8.00 or whenever the aircraft was established on the final approach course (+/- 10degrees) to 0.0nm.
- **Orientation:** **Inverted**. 0.0 is on the far right (destination/threshold); 8.00 or whatever determined is on the far left (start of approach phase)
- **Major Ticks:** every 1.0 like 8.0, 7.0, 6.0, etc.

### Primary Y-Axis: Altitude (Left)

- **Label:** `Altitude (ft)` (Rotated 90° CCW, left side)
- **Range:** 0 to (first data point altitude + 1000ft)
- **Scale:** Linear
- **Major Ticks:** Every 500 ft (0, 500, 1,000, 1,500, 2,000, 2,500, 3,000, 3,500, 4,000, 4,500, 5,000)

### Secondary Y-Axis: Groundspeed (Right)

- **Label:** `Groundspeed (kts)` (Rotated 90° CW, right side)
- **Range:** 0 to ~270 (Dynamic based on established approach speed)
- **Scale:** Linear

## 2. Visual Markings and Geometry

- **3° Glideslope Reference:** Diagonal dashed line (Grey) originating at (0.0, Threshold Elevation) and extending upward
- **GS Deviation Markers (±1 Dot):** Two dashed lines (Green) parallel to and flanking the 3° glideslope reference, representing vertical precision limits. Use Airbus and Boeing documents, to grasp what it means to be in a +/- 1 dot deviation.
- **Grid:** Subtle dark-gray orthogonal grid lines aligned with major altitude and distance ticks
- **Altitude Path:** Solid bright blue line mapping the aircraft's altitude MSL
- **Groundspeed Path:** Solid red line mapping the aircraft's deceleration relative to the secondary Y-axis

## 3. UI Elements and Legend

- **Header:** "APPROACH PROFILE" (Top-left, uppercase)
- **Legend (Interactive):**
  - Solid Blue: `Altitude (ft)`
  - Red Outline: `Groundspeed (kts)`
  - Grey Dashed: `3° Glideslope`
  - Green Dashed: `+1 Dot` / `-1 Dot`
- **Interactive Elements:** "Reset" text label in the top-right corner to restore default zoom/pan

## 4. Aesthetic Style

- **Theme:** Dark Mode
- **Background:** Utilize `bg-flight-bg` for UI consistency
- **Data Colors:**
  - **Altitude:** Electric Blue
  - **Groundspeed:** Vivid Red
- **Reference Colors:**
  - **Deviation Limit:** Emerald Green
  - **Glideslope:** Medium Grey
- **Text/Axis Color:** Muted Light Gray

Both charts should look similar, except showing different things.

# INSTRUCTIONS

Based on the information, generate an implementation plan under @docs, create a or use an existing, suitably named folder.
