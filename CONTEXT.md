# hplcsim

The domain language of the HPLC gradient simulator: scouting runs in (two in v0.1/v0.2, a run table of N from v0.3), fitted retention parameters, predictions for any candidate linear gradient, and (v0.2) an optimizer over a swept range of candidates. Started during the v0.2 map; earlier terms are in SPEC.md and will migrate here as they are touched.

## Language

### The peak table

**Untracked row**:
A peak row with fewer than two explicitly paired, usable retention times. Visible and counted (SPEC §5), never sent to the fit, the prediction or the resolution table. It is a `PeakRow` that yields no `Peak` — not a separate kind of thing. A blank cell means no usable measurement for that peak in that run; it is never read as evidence the peak did not elute.
_Avoid_: incomplete peak, partial peak, half-paired peak (a row, not a peak)

### The run table

**Scouting run**:
A named record of one scouting acquisition and its linear gradient, including hold. Method constants belong to the method and apply to every run.
_Avoid_: injection, sample, condition, method

**Run table**:
The scouting runs entered for one method, sharing one block of method constants. What the chromatographer loads and pairs against. A table can contain one run; every peak is then visibly unfitted.
_Avoid_: dataset, design matrix, training set

**Design** (of a peak):
The scouting runs with an explicitly paired, usable retention time for that peak. It exists before fitting and still applies if the fit fails. Each peak has its own; its steepness spread and start-composition spread are computed on it. A fit needs at least two different gradients within the design — a different gradient elsewhere in the table is insufficient.
_Avoid_: calibration set, subset, coverage

**Steepness spread**:
Largest s* over smallest s* across a peak's design (s* = t0·Δφ/tG). Reproduces the two-run spacing ratio when only gradient time varies; the 2.5 and 1.2 warning tiers carry over. Unavailable when any run has zero steepness. It does not measure start %B or hold differences.
_Avoid_: β (in prose), spacing ratio, tG ratio

**Start-composition spread**:
The difference between the highest and lowest starting %B across a peak's design, in percentage points. A separate hazard from steepness spread; warned whenever it is non-zero, pointing at the per-run residuals.
_Avoid_: φ0 range, start range

**Replicate**:
A run whose complete gradient, hold included, equals another run's in the same table. Shows observed repeatability. Replicates can be entered in any table; they do not by themselves make a peak fittable.
_Avoid_: duplicate, repeat, timing noise

**Factor**:
A quantity the retention model is fitted against. In v0.3 there is one, mobile-phase composition; the gradient specifies how mobile-phase composition changes over time. Temperature is a method constant, not a factor, until a model form for it exists.
_Avoid_: parameter (reserved for the fitted S_e and ln k0), variable, axis

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
For one peak, the interval between the lowest and highest compositions the peak eluted at across its design. The fit pinned that peak's retention line at exactly those points; nowhere else. Every peak has its own window, the windows are narrow, and they need not overlap, so there is no method-level window.
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
The interval between the smallest and largest steepness values across a peak's design (s*, the normalised slope t0·Δφ/tG). Explicitly per peak. A candidate inside it puts the peak at an elution composition the fit was pinned at; outside it the fit is extrapolated. While the candidate keeps the scouting %B range, this is the same interval as the one between the scouting gradient times, which is how v0.1 stated it. The bracket is an interval; steepness spread is a ratio.
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

### Profiles and seed records

**Profile**:
The selectable object a method's constants come from: a column profile (geometry and packing architecture) or an instrument profile (dwell, and whatever else is the system's), chosen independently. Carries what the user owns — a measured t0, a declared dwell — with its provenance. The destination of the profiles map (#103).
_Avoid_: preset, template, column record (when the app object is meant)

**Seed record**:
One vendor-stated fact set for a column part or a published dwell figure, hand-typed from a cited public page with URL, read date and provenance. Never carries t0, V0, porosity, or a measurement of the lab's own. A profile may be seeded from a record; a record is never a profile.
_Avoid_: profile, library entry, catalogue entry, vendor data

**Provenance**:
Of a fact on a record or profile: how it was stated (a vendor spec-table field, vendor prose, unstated, or declared by a named person) together with where and when it was read. A bare enum without it is not decision-grade.
_Avoid_: source (alone), citation (alone)
