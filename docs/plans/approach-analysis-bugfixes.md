# Approach Analysis — Bug Fix Plan

Scope: fix 7 reported bugs in the Approach Analysis tab. All faulty depictions are assumed to be the web app's fault, not the pilot's. Touch only the minimum necessary to fix each issue. The affected files are:

- `XPlaneTrackerFrontend/src/composables/useApproachAnalysis.js`
- `XPlaneTrackerFrontend/src/components/ApproachAnalysisTab.vue`
- `XPlaneTrackerAPI/app/Http/Controllers/AirportDataController.php`

I will not request flight data from the API unless explicitly granted permission. I will reason about behaviour from the code first; if a fix needs verification I will ask before fetching.

---

## Bug #3 — Backend: `Unsupported operand types: string * float` (LHTL/LHDC)

**Root cause.** In `AirportDataController.php:33`, the controller multiplies `length_ft`, `width_ft`, and elevation fields by `0.3048` without coercing them. The airportdb response returns these fields as **strings** (e.g. `"length_ft": ""`). On PHP 8.x, multiplying an empty/non-numeric string by a float throws `TypeError`. LHTL has empty `length_ft` / `width_ft` / `*_elevation_ft`, so the guard `isset(...)` is true (the keys exist) but the values are `""`.

**Fix.**
- Replace each `isset($rwy['…_ft'])` guard with an `is_numeric($rwy['…_ft'])` check (which correctly rejects `""` and `null`).
- Cast to `(float)` before multiplying so any numeric string is converted explicitly.
- Apply the same pattern to `length_m`, `width_m`, `le_elevation_m`, `he_elevation_m`.
- Resulting field is `null` when the source value is missing/empty (matches existing semantics for the truly-missing case).

This is a 4-line change inside the `foreach` loop. No cache/key changes needed; cached `null` outcomes for missing keys are fine.

---

## Bug #1 & Bug #2 — Approach segment ends prematurely / "too short"

Both bugs trace back to `computeApproachSegment` in `useApproachAnalysis.js`.

### Current logic (recap)
Walking backwards from the landing index, the loop breaks the segment as soon as either:
- `distNm > APPROACH_MAX_NM (20)` — fine.
- `angleDiff(trackBrg, runway.approachHeadingT) > APPROACH_ANGLE_DEG (10)` — **brittle**.

Then the segment is trimmed to end at the closest-to-threshold point.

### Why this misbehaves on long finals
1. **Single-sample noise breaks the walk.** On a 10+ nm final, GPS jitter or a brief heading wobble in one sample can make `bearing(p[i], p[i+1])` momentarily exceed 10° offset, cutting the entire upstream segment. That is Bug #1: flight 87's segment starts at 4.2 nm because somewhere around 4–5 nm there is one noisy sample that breaks alignment for one tick.
2. **`segDist < 1 m` early-skip is too tight.** When the path has dense samples on a slow approach, two consecutive points may be sub-meter apart and `bearing` becomes meaningless / jitter-dominated. The current code already skips these, but only below 1 m — bumping to a slightly larger floor (e.g. 5–10 m) makes the bearing comparison reliable.
3. **No smoothing window.** Comparing instantaneous segment bearings against the runway course is fragile.

### Why Bug #2 surfaces as "Approach segment too short"
Same root cause: if the very first backwards step (i = landingIdx-1 → landingIdx) sits in a low-velocity / high-jitter portion (flare/touchdown), `trackBrg` may be wildly off-runway, the loop never enters, and the trimmed segment ends up with <2 points → the early-return error fires. Flight 60's "10+ nm final" is silently rejected because the loop dies on its first iteration.

### Fix
Inside `computeApproachSegment`:
1. Raise the no-bearing-noise floor (`segDist < 1` → `segDist < 5`) so we skip near-stationary samples.
2. Replace the single-sample bearing check with a **rolling-window mean track**: compute `trackBrg` from `path[i]` to `path[i + k]` where `k` is chosen so the window spans ≥ 100 m or ≥ 3 samples (whichever larger). This averages out GPS noise without changing the geometric meaning.
3. Allow **N consecutive out-of-cone samples before breaking** (e.g. require 3 in a row beyond `APPROACH_ANGLE_DEG`). This tolerates one-off glitches without letting a real turn slip through.
4. After the walk, before declaring "too short", widen the gate: if the walk produced fewer than 2 points but more than ~30 path samples upstream sit within 20 nm of the threshold, run a fallback that selects all points within `APPROACH_ANGLE_DEG` of runway course (without requiring contiguity), then take the longest contiguous run. This recovers Flight 60 cases where the immediate pre-landing samples are degenerate.
5. Keep the post-walk `minIdx` trim (don't change end behaviour).

Constants stay tunable at the top of the file. Bug #1 should yield a 10+ nm segment; Bug #2 should produce a valid segment instead of the error state.

---

## Bug #4 — LGAV 03R default course shows 37° but draws offset; re-entering 37 fixes it

**Root cause.** The display/state model conflates magnetic and true headings.

In `buildCandidates`:
- `approachHeadingT` = `headingT` if present, otherwise `headingM`.
- `approachHeadingM` = `headingM` if present, otherwise `headingT`.
- `magVariation` is computed but **never applied** anywhere.

In `buildRowData`:
- `detectedCourseM = Math.round(runway.approachHeadingM)` — the placeholder displayed in the input.
- The chart uses `runway.approachHeadingT` (unrounded).

In `overrideRow`:
- The user's typed value is taken as a **true heading** and assigned to `approachHeadingT`.

Result for LGAV 03R: airportdb's `le_heading_degT` and `le_heading_degM` differ by ~5° (Greece variation). The placeholder shows magnetic (≈37 rounded). The chart was drawn with the true heading (≈32). When the user types "37" and Applies, we overwrite `approachHeadingT` with 37 — which happens to be very close to the actual physical true heading of the runway, so the chart suddenly looks right. The "37 → 37" mystery is illusory: the original 37 was magnetic and the post-override 37 is treated as true.

**Fix (couples with Bug #6).** Make the input field unambiguously magnetic and apply the mag variation when feeding the chart math:

1. Rename the label and placeholder semantics: `Approach Course (°M)` (see Bug #6 details).
2. Persist `approachHeadingT`, `approachHeadingM`, and `magVariation` on the runway object (already done) but ensure `magVariation` is correctly populated even when only one of `headingT`/`headingM` is provided — fall back to a default `0` only as a last resort, otherwise use whatever delta is observable.
3. In `buildRowData`, the chart math continues to use **true** heading internally (it must — flight lat/lon math is geodetic).
4. In `overrideRow`, treat the user's input as **magnetic**: `approachHeadingT_new = (parsedCourseM + magVariation + 360) % 360`. Use `runway.magVariation` as captured from airport data.
5. Default placeholder remains `Math.round(runway.approachHeadingM)` (consistent with what charts list).

This eliminates the magnetic/true confusion, so the default-render and an Apply with the same number are now functionally identical.

---

## Bug #5 — Flight 130 lateral profile parallel-offset to the right (single runway 22, no parallel)

**Updated hypothesis (user clarified: only one runway exists at this airport, the user landed runway 22, and the rest of the picture is correct).**

Because the purple line is *parallel* to the centerline, the heading inferred for the runway is correct — what's wrong is the **lateral position of the reference centerline itself**. Per the prompt's contract ("assume the pilot was on profile, faults are the web app's fault, all flights are stabilized"), the most plausible cause is that the airportdb-supplied threshold lat/lon for runway 22 is offset by a small amount perpendicular to the actual physical centerline. The aircraft tracked the real localizer accurately; our computed centerline is shifted, so deviation = constant ≠ 0 across the whole approach.

This is purely a *reference-point* defect, not a runway-identification defect (no parallel runway exists at this airport, so the selection logic is irrelevant here).

### Fix — self-align the centerline to the established final track

Implement, downstream of `computeApproachSegment` and the Bug #7 heading refinement, an analogous **threshold lateral refinement** pass:

1. Take the last `min(0.5 nm, last 30% of the segment)` of points — the most-stable portion of the established final, where pilot tracking error is smallest.
2. Compute each point's **signed perpendicular deviation** from the DB centerline (using the already-refined `approachHeadingT` from Bug #7, falling back to the DB heading if Bug #7 didn't trigger). Sign convention: left = negative, right = positive.
3. Compute the **median** and **standard deviation** of those signed deviations.
4. **Only apply the refinement** when both conditions hold:
   - `stddev < 30 ft` (the aircraft was clearly tracking a single straight line, not weaving).
   - `|median| < 200 ft` (the implied DB error is plausible; larger gaps suggest something else is wrong and we should *not* silently shift the chart).
5. When applied, **shift the threshold lat/lon perpendicular to the runway course by `-median`** (in the appropriate direction). Concretely: compute a destination point from the original threshold using a bearing of `approachHeadingT ± 90°` and a distance of `|median|` (in feet → metres), then store that as the effective threshold for chart math (`computeLateralPoints`, `buildGsRefLines`, distance-to-threshold for `verticalAlt` / `verticalGs`).
6. Keep the original DB threshold on the runway object so the runway label and any future logic remain unchanged. Only the *effective* threshold used by the chart geometry is shifted.

### Why this is safe

- Stabilized approaches (the only kind we are told to handle) produce a tightly clustered set of perpendicular deviations near touchdown — a non-zero median there implies the *reference* is off, not the pilot.
- The `stddev < 30 ft` gate prevents shifting the centerline when the pilot was actually weaving (which would happen if our heading were also wrong, or on a non-stabilized approach not in the test set).
- The `|median| < 200 ft` cap means we don't paper over a more serious problem (e.g. wrong runway) by silently translating the chart by hundreds of feet.
- The vertical profile is unaffected by the lateral shift in any meaningful way (the along-track distance changes by ≪0.01 nm for any plausible shift).

### Why I'm dropping the parallel-runway tiebreaker work

The tiebreaker logic in `identifyRunway` (mean perpendicular over the last N points instead of the single landing point) is still a sensible improvement, but **none of the reported bugs require it**: flight 130 is a single-runway case. I will not touch `identifyRunway` as part of this bug-fix pass — keeping changes minimal per the project's "don't add features beyond what the task requires" guidance. If a future flight surfaces a true parallel-runway misidentification, we can revisit it then.

---

## Bug #6 — Magnetic input + degree-icon position

**Two changes in `ApproachAnalysisTab.vue`.**

1. **Magnetic input semantics.**
   - Change the label from `Approach Course (°T)` to `Approach Course (°M)`.
   - Wiring change handled in Bug #4 (treat input as magnetic).
   - The placeholder already shows the magnetic value, so no placeholder change.

2. **Degree-icon CSS alignment.** The course input is 28 units wide with `right-3` for the `°`; the glideslope input is 24 wide with the same offset, so visually the `°` clips the right edge of the course input. Match the styling pattern of the glideslope input exactly:
   - Add `pr-6` (or equivalent right padding) to the input itself so the typed number does not overflow under the `°`.
   - Keep `absolute right-3 top-1/2 -translate-y-1/2` for the `°` span.
   - Verify the rendered position matches the glideslope input by eye; use the same Tailwind classes for both wrappers.

Will read `.claude/skills/design` before touching the component (per CLAUDE.md) to confirm the colour tokens and spacing scale to use.

---

## Bug #7 — LZIB RW22 default course 224° is 0.3° off; 223.7° looks correct

**Root cause.** Airport DB heading values can be off by ≤1° vs the surveyed centerline. The chart treats the DB value as ground truth, so the purple line ends up systematically biased — yet the pilot was actually on the localizer.

**Fix (forgiving default).** When auto-rendering the default profile, refine the runway course from the flight data itself:

1. After `computeApproachSegment` produces the segment, compute the **median bearing** of the last `min(2 nm, half the segment)` of points (excluding any below 5 m segment distance).
2. If `angleDiff(median, runway.approachHeadingT) ≤ 1.5°`, **adopt the median as the effective `approachHeadingT`** for chart geometry only. Store the original DB heading separately so the magnetic display logic still works (Bug #4 / #6).
3. Threshold lat/lon stays from the DB.

Effect:
- Stabilized approaches (the only case we are told to handle) will self-align: a pilot tracking the actual centerline will produce a near-perfect 0-deviation purple line.
- Genuine cross-track errors (>1.5° heading offset over the final 2 nm) won't be swallowed — those still show as deviation.
- Bug #7 is solved without per-airport hacks.
- Bug #5 may also be partially mitigated as a side effect (any small DB heading inaccuracy disappears).

The 1.5° threshold is conservative; we can tune later if needed.

---

## Order of work

1. Bug #3 (backend, isolated, smallest blast radius).
2. Bug #6 — degree-icon CSS only (cheap and visible).
3. Bug #4 + Bug #6 — magnetic-input wiring (these must land together).
4. Bugs #1 / #2 — segment walker hardening (single edit in `computeApproachSegment`).
5. Bug #7 — adaptive course refinement.
6. Bug #5 — threshold-position self-alignment (depends on Bug #7's refined heading; gated by stability/magnitude checks).

After each step I'll ask the user to retest the affected flights (87, 60, LGAV 03R, 130, 120) and only request raw flight JSON if a bug doesn't resolve on inspection.

## Non-goals / not changing

- Touchdown detection, bounce filter, GS-deviation funnel math.
- The shape, axes, or styling of the charts themselves.
- The airport-identification step (`findAirportIcao`) — no bug points there.
- Caching strategy for airport data.
