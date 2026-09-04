# hplcsim

The domain language of the HPLC gradient simulator: two scouting runs in, fitted retention parameters, predictions for any candidate linear gradient, and (v0.2) an optimizer over a swept range of candidates. Started during the v0.2 map; earlier terms are in SPEC.md and will migrate here as they are touched.

## Language

### The peak table

**Untracked row**:
A non-blank peak table row missing one or both retention times. Visible and counted (SPEC §5), never sent to the fit, the prediction or the resolution table. It is a `PeakRow` that yields no `Peak` — not a separate kind of thing.
_Avoid_: incomplete peak, partial peak, half-paired peak (a row, not a peak)

### Resolution and the optimizer

**Critical pair**:
The adjacent peak pair with the lowest resolution at a given condition. There is exactly one per condition; it can change identity across a sweep.
_Avoid_: worst pair, limiting pair

**Run time**:
The predicted retention time of the last-eluting peak at a condition. It is not the gradient time, and not the injection-to-injection cycle (re-equilibration and washes are not modelled).
_Avoid_: cycle time, analysis time, gradient time (when the last peak is meant)

**Rs target**:
The critical-pair resolution the chromatographer asks the goal-seek to reach. Default 1.5 (baseline separation); editable.
_Avoid_: threshold, spec limit

**Goal-seek**:
The optimizer's headline answer: the swept condition with the shortest run time whose critical-pair resolution is at or above the Rs target.
_Avoid_: optimum (reserved for the ceiling)

**Ceiling**:
The swept condition that maximises the critical-pair resolution — the best this sweep can do. Shown alongside the goal-seek; run time is display-only here.
_Avoid_: optimum (ambiguous with goal-seek), max-min point

### Composition freedom

**Calibrated composition window**:
For one peak, the interval between the compositions it eluted at in the two scouting runs. The fit pinned that peak's retention line at exactly those two points; nowhere else. Every peak has its own window, the windows are narrow, and they need not overlap, so there is no method-level window.
_Avoid_: φ range (which is the gradient's sweep, not the calibration), composition range

**Window-width**:
The unit for how far a candidate sits outside the scouting bracket: the distance beyond the bracket edge divided by a peak's calibrated composition window. It comes out the same for every peak, which is why the extrapolation tier is a single method-level number.
_Avoid_: multiples of tG, times outside

**φ0 departure**:
How far the candidate's starting composition sits from the scouting runs', in %B. A separate hazard from extrapolation: two candidates can share a steepness and a composition window and still differ here.
_Avoid_: φ0 offset, start shift

**Decision-grade**:
The standing of a resolution or critical-pair number the chromatographer may act on without a confirming injection. Lost when a candidate is far outside the scouting bracket or far in φ0 departure; retention times keep being shown as numbers either way.
_Avoid_: reliable, validated

### The resolution map

**Sweep**:
The set of candidate gradients the map is drawn over: every gradient time on the slider's grid between the sweep bounds, plus the two scouting gradient times and the current candidate. The initial hold is fixed at the rail's current value and is not swept.
_Avoid_: scan, search space, grid (when the whole sweep is meant)

**Swept condition**:
One gradient in the sweep. Recommendations are always a swept condition, never a value between two.
_Avoid_: grid point, sample

**Scouting bracket**:
The interval between the two scouting runs' steepness values (s*, the normalised slope t0·Δφ/tG). A candidate inside it puts every peak at an elution composition the fit was pinned at; outside it the fit is extrapolated. While the candidate keeps the scouting %B range, this is the same interval as the one between the two scouting gradient times, which is how v0.1 stated it.
_Avoid_: calibrated range, training range, tG bracket (when the s* interval is meant)

**Extrapolation zone**:
The part of the sweep outside the scouting bracket, up to twice the bracket's span in either direction. Drawn shaded on the map. Beyond it lies the strong-warning zone, which is never swept.
_Avoid_: danger zone, unvalidated region

**Order flip**:
A gradient time at which two peaks exchange elution order. Their resolution is zero there. A prediction crossing (SPEC §6 diagnostic 4) is an order flip seen at a single candidate.
_Avoid_: crossover, inversion, swap

**Co-elution zone**:
The interval of gradient time around an order flip where the flipping pair's resolution is below the Rs target. Shaded on the map so a chromatographer sees the interval to avoid, not only the point.
_Avoid_: dead zone, trough
