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
