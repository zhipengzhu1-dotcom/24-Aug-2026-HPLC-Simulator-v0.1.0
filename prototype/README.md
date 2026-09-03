# PROTOTYPE — how the candidate's φ range enters the Cockpit (wayfinder ticket #45)

Throwaway. **Never merges to main**; the decision is what carries forward, the same
posture as `prototype/main-screen` and `prototype/resolution-map`.

## Run it

```
uv run --extra app streamlit run streamlit_app.py
```

Then flip with the URL, or the switcher at the foot of the sidebar:

| | |
|---|---|
| `?variant=A` | **Range beside the sliders** — sidebar keeps the scouting %B ("as run"); the rail's Candidate block gains a %B range slider under tG and hold, plus a "↺ scouting" reset; extra segments in an expander table; the programme drawn as a small φ-vs-time sparkline in the rail |
| `?variant=B` | **Programme table, paired** — the ACD/DryLab shape (#56): the scouting programme leaves the sidebar and becomes a No./Time/%B table at the top of the rail (two time columns — one programme at two speeds); the candidate is a second table of the same shape beneath it, dynamic rows, **no sliders**; the programme is the table and nothing else |
| `?variant=C` | **Segments stacked, drawn on the chromatogram** — start %B, hold, then one block per segment ("to %B over min") with ＋/−; the programme is overlaid on the pinned chromatogram on a right-hand %B axis — candidate solid, scouting dashed — with each peak's elution composition as a diamond and its calibrated window as the whisker |
| `?data=lab` | `validation/` runs 1+2 — three peaks, 5→95 %B, tG 15/45 (default) |
| `?data=v2` | `validation/Validation_2` runs 1+2 — four peaks inside 0.5 min, near-critical pair, tG 15/40 |
| `?data=own` | whatever is typed in; no demo load |

All three variants carry the four surfaces #44 decided, in the places it decided:

1. **Two candidate-control inline warnings** under the controls: diagnostic 1 on s\*
   (overshoot in window-widths; gentle to 0.6, strong beyond) and diagnostic 7, the φ0
   departure (gentle for any departure, strong from 10 %B, the doubling rule quoted).
2. **One readout row per peak on the Fit parameters tab**: calibrated window in %B, its
   width, the candidate's elution composition for that peak, and its standing.
3. **One per-peak badge**, "low k0 at φ0", in the table of peaks' Flags column and the
   selected-peak panel, when log10 k0 at the candidate start is below 2.1.
4. **One output stamp** — *indicative, not decision-grade* — on Min. Rs in the Method
   summary, the resolution tab, and the status bar, when 1 or 7 is strong; a low-k0
   badge downgrades only that peak's pairs.

Things to try: raise the start to 15 %B (gentle) and 25 %B (strong) on either dataset;
narrow the range to 15→55 at tG 25 (inside the tG bracket, outside the s\* bracket —
#44's worked example); add a second segment to 95 %B over 5 min and watch the late peak
move off the ramp end; on Validation_2, push the start until a peak earns the low-k0
badge.

## What is real and what is not

Real: the fit, the sidebar, the chromatogram, every single-segment number. A one-segment
programme is passed to the engine as an ordinary `Gradient` and predicted by
`hplcsim.retention.predict_retention` — the prototype computes nothing for it.

Real to floating point, but not the engine: **multi-segment** retention.
`prototype/programme.py` walks the programme piece by piece with the closed form of each
linear piece, under the v0.1 closed form's own assumptions (the band sees the inlet
composition delayed by the dwell; elution one t0 after the band reaches the outlet). A
one-segment programme reproduces the engine to 1e-14 min — `check_single_segment_matches_engine`
— which is #46's internal-consistency bar demonstrated, not the v0.2 engine (den Uijl
Eq. 7–8 is #47's business). Multi-segment **widths** take G from the segment the band
left during, with k at that segment's start: an approximation, marked "prototype
arithmetic" in the status bar.

Not real: the thresholds. 0.6 window-widths, 10 %B and log10 k0 < 2.1 are #44's
provisional numbers; #55 re-pins them after E1, E4 and the t0 re-baseline.

Known rough edges, deliberately left: the session-file save refuses a candidate whose %B
range differs from the scouting runs' — that is v0.1's `_check_candidate`, which #44
already decided becomes a warning path; the sidebar's "Not saveable yet" is the truthful
v0.1 state. The tG-extrapolation diagnostic is replaced, not removed, so the engine's own
`tg_extrapolation` never shows here.

## Where it touches the real app

`streamlit_app.py`, eleven small hunks, all commented `PROTOTYPE #45`: the import; the
demo restore and the switcher in `main`; the rail (a `RailContext`, the scouting runs
and the candidate controls routed through the pane, a rail slot for variant A's
sparkline); `repredict` after `run_cockpit` and `rediagnose` after `diagnose`; the
sidebar's gradient block yielding to the rail in variant B; the Rs stamp in the
Method summary, the resolution tab and the status bar; the fit-tab readout; the
chromatogram title and variant C's overlay. `src/hplcsim` is untouched.
