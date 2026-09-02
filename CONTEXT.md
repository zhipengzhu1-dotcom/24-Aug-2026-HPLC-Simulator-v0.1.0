# hplcsim

The domain language of the HPLC gradient simulator: two scouting runs in, fitted retention parameters, predictions for any candidate linear gradient, and (v0.2) an optimizer over a swept range of candidates. Started during the v0.2 map; earlier terms are in SPEC.md and will migrate here as they are touched.

## Language

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

### The resolution map

**Sweep**:
The set of candidate gradients the map is drawn over: every gradient time on the slider's grid between the sweep bounds, plus the two scouting gradient times and the current candidate. The initial hold is fixed at the rail's current value and is not swept.
_Avoid_: scan, search space, grid (when the whole sweep is meant)

**Swept condition**:
One gradient in the sweep. Recommendations are always a swept condition, never a value between two.
_Avoid_: grid point, sample

**Scouting bracket**:
The interval between the two scouting gradient times. Predictions inside it are interpolations; outside it they are extrapolations.
_Avoid_: calibrated range, training range

**Extrapolation zone**:
The part of the sweep outside the scouting bracket, up to twice the bracket's span in either direction. Drawn shaded on the map. Beyond it lies the strong-warning zone, which is never swept.
_Avoid_: danger zone, unvalidated region

**Order flip**:
A gradient time at which two peaks exchange elution order. Their resolution is zero there. A prediction crossing (SPEC §6 diagnostic 4) is an order flip seen at a single candidate.
_Avoid_: crossover, inversion, swap

**Co-elution zone**:
The interval of gradient time around an order flip where the flipping pair's resolution is below the Rs target. Shaded on the map so a chromatographer sees the interval to avoid, not only the point.
_Avoid_: dead zone, trough
