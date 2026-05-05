# Approach Analysis Bugfixes & Displaced Threshold Enhancements

## Objective
Fix the bug where a short approach segment hides the valid runway profile, correct the departure runway detection logic (which currently breaks on OMDB 12L), and properly render displaced thresholds with customizable, realistic markings.

## Scope & Impact
- **XPlaneTrackerFrontend/src/components/ApproachAnalysisTab.vue**: Modify the template to ensure the Runway Profile renders even if the lateral/vertical approach analysis fails.
- **XPlaneTrackerFrontend/src/composables/useRunwayProfile.js**: 
  - Fix departure runway matching by removing the erroneous opposite-end flip (`findOppositeEnd`), which fixes the wrong orientation AND the "Could not locate takeoff end" error seen at OMDB 12L.
  - Include `displacedM` in the data row.
  - Render the physical runway starting at `-displacedM` instead of `0`.
  - Add realistic, customizable displaced threshold markings (arrows and the threshold bar) using ECharts series.

## Proposed Solution

### 1. Fix Approach Segment Error Hiding Runway Profile
In `ApproachAnalysisTab.vue`, the Runway Profile block (`v-if="profileRows[idx]...`) is currently placed inside the `v-else` block that handles the lateral and vertical profiles. When `row.error` is true (e.g., "Approach segment too short"), the `v-else` block is skipped entirely. 
**Change**: Move the Runway Profile block outside of the `v-else` block so it is rendered independently. The layout will look like this:
- `v-if="row.error"`: Show approach analysis error.
- `v-else`: Show the lateral and vertical profile charts.
- Runway Profile block (conditionally rendered if `profileRows[idx]` exists, regardless of `row.error`).

### 2. Fix Departure Runway Detection Logic & OMDB Error
In `useRunwayProfile.js`, the `processDeparture` function incorrectly calls `findOppositeEnd(matched, candidates)`. Because `identifyRunway` already finds the correct runway matching the takeoff heading (e.g., taking off on 22L matches candidate 22L), `findOppositeEnd` flips it to the wrong end. Additionally, `findOppositeEnd` calculates the physical distance between ends, which can fail if threshold coordinates are far from the physical ends (common on huge runways like OMDB 12L), resulting in the "Could not locate takeoff end of runway" error.
**Change**: Remove the `findOppositeEnd` call completely. The runway returned by `identifyRunway` is already the correct departure runway. Assign `takeoffEnd = matched`. This simultaneously fixes the orientation bug and the OMDB 12L error.

### 3. Implement Displaced Threshold Rendering
Currently, there is **no logic** for drawing displaced thresholds. The coordinate system in `useRunwayProfile.js` simply places the threshold at `x=0` and draws the runway from `0` to `ldaM` (Available Landing Distance). For runways with a displaced threshold, the physical pavement starts *before* the threshold, which is currently ignored.
**Changes**:
1. **Pass Displaced Length**: In `processArrival` and `processDeparture`, calculate `const displacedM = runway.displacedFt * FT_TO_M` and include it in the returned row data.
2. **Adjust Runway Box**: In `buildProfileChartOption`, draw the runway box starting from `-row.displacedM` up to `row.ldaM`. Update the X-axis `min` to accommodate this.
3. **Add Tunable Constants**: Expose the following configuration object at the top of the file so you can easily customize the look:
   ```javascript
   const DISPLACED_THRESHOLD_STYLE = {
     BAR_THICKNESS_M: 3,       // Thickness of the solid white threshold bar at x=0
     ARROW_LENGTH_M: 20,       // Length of each arrow along the displaced area
     ARROW_SPAN_M: 10,         // Width of the arrow head
     ARROW_SPACING_M: 30,      // Distance between consecutive arrows
     LINE_WIDTH: 2,            // Stroke width for the markings
     COLOR: '#cbd5e1'          // Color of the markings (matching runway edge)
   }
   ```
4. **Render Markings**: Add ECharts line series to draw:
   - A thick line across the runway at `x=0` (the threshold bar).
   - A loop that draws arrows pointing towards `x=0` inside the region from `-row.displacedM` to `0`, spaced by `ARROW_SPACING_M`. 

## Verification
- Load a flight with a short approach segment; verify the Runway Profile is displayed even if the approach charts show "Approach segment too short".
- Check a departure flight at OMDB 12L; verify the orientation is 12L and the "Could not locate" error is gone.
- View the runway profile for a runway with a known displaced threshold (e.g., KJFK 04R or KSAN); verify the runway box extends into the negative X-axis and realistic arrows are drawn.


# Instructions!
Make sure the arrows have a head and a tail, they are that type of arrows ➡
Please make sure not to touch other logic, you can count the displaced thresholds length in negative numbers, please start counting the runways length from the threshold. PLease find a solution for when overflying the runway, i see the path on the runway charts, so please filter for only low altitudes (agl! an airport may be as high as 8000ft msl or more!!!!). Do not touch the landing marker logic, the TDZ position - they are designed according to this and should stay as they are @docs/plans/runway-analysis.md pay attentnion not to modify these accurate and precise logic.