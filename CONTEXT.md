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
