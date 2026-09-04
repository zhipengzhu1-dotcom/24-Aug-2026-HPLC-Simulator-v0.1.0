# Lab protocol — scouting + confirmation runs for engine validation

Bench-ready consolidation of [issue #8](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/8), the input contract ([#4](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/4)), and both research docs ([#2](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/2), [#3](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/3)). Fill the CSV templates in this folder as you go.

## What this data is for

The v0.1 engine fits per-peak retention parameters from **runs 1–2** and must then predict **run 3** (which it never sees) within: average |ΔtR| ≤ 2%, worst peak ≤ 5%, correct elution order, critical-pair Rs ± 0.3 (the trust bar from [#9](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/9)). Sloppy dwell/t0 values — not the engine — are the usual reason such bars fail (+1% systematic bias per dropped term), which is why steps 1–2 exist.

## 1 · Characterize the instrument (once)

- **Dwell volume VD** — with the column replaced by a zero-dead-volume union: A = water, B = water + ~0.1% acetone; detector ~265 nm; program a sharp linear gradient 0→100 %B at your normal flow. tD = time from gradient start to the **midpoint** of the absorbance rise; VD = tD × F. Record both.
- **Dead time t0** — with the column installed: inject an unretained marker (uracil or thiourea) under any isocratic condition; t0 = its retention time at the flow you will use. Record the marker used.
- Record instrument make/model (the dwell volume belongs to the instrument, not the method).

## 2 · Fix the shared method (identical in all three runs)

One column, one flow, one temperature, one mobile-phase pair, one gradient **range** (φ0 → φf), one initial hold, one injection volume. Only **tG differs** between runs. Record in `method.csv`: column length / i.d. / particle size, F, T, %B start, %B end, initial hold time, injection volume, sample identity.

Keep injection volume constant — the area-based tracking check depends on it. Re-equilibrate ≥ 10 column volumes between runs.

> **Gap on record (noted 2026-09-03 under [#54](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/54), from #52 §4.3).** Every gradient table recorded in this folder through 2026-09-03 — campaign #27's runs 5–7, and `Validation_2/` runs 1–6, E1 and E4 — holds the return composition for 3.4–4.0 min at 0.4 mL/min: 1.36–1.60 mL, **≈ 5.7–6.7 column volumes** at V_M ≈ t0·F = 0.24 mL (6.5–7.6 at the driver's t0 of 0.525 min). That is above the ~2 CV Schellinger et al. show suffices for *repeatability* and below this protocol's ≥ 10 CV. Runs 1–4 of campaign #27 carry no gradient table and are assumed the same. The runs on file therefore do not meet the protocol, and the re-equilibration end-point is one of the two mechanisms #52 left standing for the φ0-dependent residual. The instruction stands as written: the next sequence holds ≥ 10 CV — **6.0 min at 0.4 mL/min on this column** — and records it ([#53](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/53)).

## 3 · Run the three gradients

| Run | Purpose | Gradient time |
|---|---|---|
| Run 1 | scouting (fit input) | tG — your normal, e.g. 15 min |
| Run 2 | scouting (fit input) | **≈ 3 × tG** — e.g. 45 min (β ≈ 3 is load-bearing; β < 2.5 degrades the fit) |
| Run 3 | confirmation (never shown to the fit) | a third value **inside** the bracket, e.g. ≈ 1.7 × tG (25 min for 15/45). *Optional bonus:* a fourth run outside the bracket (e.g. 60 min) to probe extrapolation warnings. |

## 4 · Record per-peak data (each run's CSV)

For every peak you can assign, per run: **tR (min, 2+ decimals)**, **area %**, and compound name/label. Pair the same compound across runs (elution order may change — that's fine and useful; note it if seen).

**At least one peak in at least one run: width at half height W½ (min).** This single measurement settles the band-compression G log-base convention that literature access could not (a 10–15 % width effect) — more widths are better.

If a peak can't be assigned in some run (co-elution, below detection), leave that cell empty — do not guess.

## 5 · Commit

Fill `method.csv`, `run1.csv`, `run2.csv`, `run3.csv` (and `run4.csv` if run) in this folder, commit, and note completion on [issue #8](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/8) — that closes the last blocker before spec assembly.

## Worked example (A = 0.1% formic acid in water, B = acetonitrile, 5 → 95 %B)

All runs share the range 5 → 95 %B and the same initial hold (0.5 min shown; 0 is fine — keep it identical). Only tG changes. Wash and re-equilibration are part of the instrument method but are **not** entered into the simulator.

**Run 1 — scouting, tG = 15 min**

| Time (min) | %B | Segment |
|---|---|---|
| 0.00 | 5 | initial hold |
| 0.50 | 5 | hold ends |
| 15.50 | 95 | linear ramp (tG = 15) ← modeled |
| 18.50 | 95 | wash — not modeled |
| 18.60 | 5 | return |
| ~33 | 5 | re-equilibrate ≥ 10 column volumes — not modeled |

- **Run 2 — scouting, tG = 45 min** (β = 3): ramp 0.50 → 45.50 min, 5 → 95 %B; same wash/re-equil pattern.
- **Run 3 — confirmation, tG = 25 min** (≈ 1.7×, inside the bracket): ramp 0.50 → 25.50 min.
- **Run 4 — optional, tG = 60 min** (outside the bracket): ramp 0.50 → 60.50 min, probes extrapolation warnings.

Simulator inputs from these tables: %B start = 5, %B end = 95, t_init = 0.5 min, tG = 15 / 45 / 25 (/ 60).

Notes: adding 0.1% FA to the acetonitrile too is your chromatographic choice — the model is indifferent, but use the same bottles for all runs. Re-equilibration: ≥ 10 column volumes ≈ 15 min at 1 mL/min on a 150 × 4.6 mm column (Vm ≈ 1.5 mL); scale to your column and flow — on the 100 × 2.1 mm column in `method.csv` at 0.4 mL/min (Vm ≈ 0.24 mL) that is 6.0 min, not the 3.4–4.0 min the recorded programmes hold (see §2). A different shared endpoint (80 or 100 %B) is fine if identical across runs.
