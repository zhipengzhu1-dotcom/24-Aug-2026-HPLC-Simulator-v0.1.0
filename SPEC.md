# HPLC Gradient Method Simulator — v0.1 Specification

The destination of the [wayfinder map (#1)](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/1). Every section links the ticket holding its decision detail. Status: **approved spec — ready to build.**

## 1. Purpose and audience

A Python simulator for **working chromatographers making real method-development decisions** ([map](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/1)). The user enters two gradient scouting runs; the app fits per-peak retention parameters; it then predicts retention times, peak widths, resolution, and the rendered chromatogram for any candidate linear gradient. Quantitative honesty beats visual polish throughout. v0.1 serves a single user locally ([#6](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/6)).

**Already validated on real data**: the exact algorithm specified here, run against the driver's Acquity H-Class / CORTECS 2.1×100 dataset ([#8](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/8)), blindly predicted a tG = 25 min confirmation run to **0.35% average |ΔtR|** and a tG = 60 min out-of-bracket run to **0.26%** — inside the trust bar by ~5×.

## 2. Scope

**In (v0.1):** reversed-phase gradient elution; two-run fit; prediction of linear gradients (tG and initial hold) within the calibrated %B range; chromatogram rendering; resolution table; diagnostics; session save/load.

**Out of this effort entirely** ([map](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/1)): quantitation features (calibration, LOD/LOQ, SST reporting); instrument control / CDS connectivity.

**Deferred to named cycles** (§11): everything else, including changed φ0/φf prediction, multi-segment gradients, ≥2-run regression, CSV import, temperature, pH, hosting, column DB, structure-based prediction.

## 3. Science model ([#2](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/2))

Normative detail with derivations, symbol table, and citations: `docs/research/gradient-elution-math.md` (branch `research/gradient-math` — merge into main during build).

- **Retention model**: linear solvent strength (LSS). **Internal convention: natural log** — ln k = ln k0 − S_e·(φ − φ0); **display convention: base-10** (S = S_e / ln 10) since chromatographers read S ≈ 2–6. The log-base trap is the #1 implementation hazard; the convention boundary lives in exactly one display-layer function.
- **Gradient retention** (linear ramp, pre-gradient isocratic period τ = t_D + t_init):
  tR = τ + t0 + (t0 / b_e) · ln[b_e·(k0 − τ/t0) + 1], with b_e = t0·Δφ·S_e / tG.
- **Two-run fit** (per peak, independent): no exact closed form exists. Algorithm: closed-form large-k0 seed, then 1-D root-find (Brent) on the run-2 residual; round-trip the fitted (k0, S_e) against both input tR to ≤1e-8 as a self-check. The closed form alone is forbidden as a final answer (138% S error at k0 = 8).
- **Edge cases** get explicit branches, not one formula: elution during dwell/hold; elution after gradient end (G = 1 there, no band compression); very early eluters (k ≈ 1 territory → low-confidence badge); degenerate inputs (tG1 = tG2 → refuse).
- **Peak width**: σ_t = (t0 / √N)·(1 + k_e)·G; band-compression factor G per the research doc. **N is per peak, measured-first** ([#23](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/23)): fitted from that peak's scouting W½ when entered — the inverse of the width equation, one N per peak as the geometric mean of what each width implies (`docs/research/plate-count-from-widths.md` §3–§4) — otherwise the global knob, otherwise the column-based default. A fitted N is an apparent, instrument-inclusive efficiency conditional on the calibrated G: not the column's intrinsic N, and not a pharmacopoeial plate number. **Hazard status — RESOLVED** (#17; evidence in research doc §5.4): the convention was calibrated against the measured W½ in `validation/run1–4.csv`. Holding one column's plate count constant across a fourfold range of gradient steepness works to 0.92% under the natural-log reading and to 5–13% under every alternative, including the ×ln 10 mirror; confirmed on runs 3–4, which are held out of the fit. Peaks without widths still carry the second uncertainty: a defaulted N is column geometry, not the column's real efficiency.
- **Resolution**: Rs = (tR₂ − tR₁) / (2·(σ₁ + σ₂)) per adjacent pair; critical pair = minimum Rs.

## 4. Input contract ([#4](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/4))

**Method constants** (one block, shared by both scouting runs — identical except tG):

| Field | Rule |
|---|---|
| Column length / i.d. / particle | mm / mm / µm; metadata + basis for estimates |
| Flow F | mL/min |
| t0 | **measured-first**: marker time (min) primary; geometry estimate as labeled fallback that stamps predictions lower-confidence |
| Dwell | required, no silent default; entered as t_D (min) or V_D (mL, ÷F); in-app measurement guidance |
| Gradient | %B start, %B end (UI 0–100; φ internal), optional initial hold t_init (min); single linear segment |
| Temperature | °C, metadata only (fixed-T model); sample-manager temp optional provenance |
| Plate count N | **per peak, measured-first** (the t0 posture): fitted from the peak's W½ when entered; otherwise the global knob; otherwise the column-based default, stamped lower-confidence ([#23](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/23)) |

**Runs**: exactly two; only tG differs; recommend tG and ~3·tG; spacing-ratio warning < 2.5, strong < 1.2, never a hard block.

**Per peak**: tR in run 1 and run 2 mandatory (min). Optional: name (auto P1…Pn), **per-run area** (raw or % — normalized to shares internally; [#7](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/7)/[#8](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/8) refinements), width-at-half-height W½ (min).

**Prediction targets**: any linear gradient varying tG and t_init within the scouting φ0→φf range.

**Validation posture**: warnings over blocks; per-peak sanity tR > t0; tG values must differ.

## 5. Peak tracking ([#5](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/5))

Manual and implicit: **one row per compound**, tR(run 1) and tR(run 2) side by side — the chromatographer pairs peaks while typing. The app checks rather than performs the pairing: area-share disagreement warning (default threshold ~30% relative change, measured against the first run's share — on the lab dataset peak 2 moves 40.9% and fires, peak 3 moves 26.7% and does not, peak 1 moves 22.8%; a good live test, and the two peaks the integrator mis-measured are the two the check ranks highest); elution-order crossing flags for confirmation; rows missing either tR stay visible as "untracked — not fitted", excluded from fit/prediction/resolution with a visible count; within-run co-elution entry legal (area check relaxes). The engine receives only confirmed, complete pairs.

## 6. Diagnostics ([#9](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/9))

All six ship in v0.1:

1. **tG extrapolation**: info flag when candidate tG leaves [tG1, tG2]; strong warning beyond ~2× outside. (Lab evidence: 1.33× outside scored 0.26% — the near-bracket flag stays gentle.)
2. **Early-eluter badge** (elutes near t0 + dwell + hold).
3. **β-spacing escalation** on fit results.
4. **Prediction crossing flags** (order at candidate differs from scouting runs).
5. **Width/Rs caveat banner**. The G convention is settled (§3, #17) and N is fitted wherever widths exist (#23), so the banner is scoped to peaks whose N is *defaulted*: a geometry estimate runs 0.69–0.92× on measured lab widths and 18–39% optimistic on Rs at held-out conditions, where a fitted N lands at 0.99–1.16× and −4 to −10%. The engine stamps every width with `PeakWidth.plate_count_source` (`"default"` / `"supplied"` / `"fitted"`); the banner reads `"default"`. A fitted N's `FittedPlateCount.low_confidence` (its only width came from the post-gradient regime; such a width is left out whenever the other run's is usable) is a per-peak badge, not a banner. Wording is ticket #19's. Absolute widths and Rs are caveated for defaulted peaks; the critical *pair* is not — it is identified correctly at both held-out conditions under either N.
6. **Estimated-t0 stamp** on all outputs when the geometry fallback was used.

Presentation: per-peak badges (2, 4), fit-page notices (3), result banners (5), output stamps (6), candidate-control inline warnings (1).

## 7. UI ([#7](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/7))

**Cockpit layout** (modelled on the instrument software this tool sits beside — DryLab and its
relatives — at the driver's direction during [#19](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/19);
the prototype variant on branch `prototype/main-screen` is superseded): sidebar = method constants
+ N knob. A narrow **left rail** carries the condition — scouting tG values, candidate tG and
initial hold — above a **Method summary** panel (peaks fitted, untracked count, minimum Rs and its
critical pair, run time, minimum k) and a **Selected peak** panel (tR, k at elution, W½, N and where
it came from, log10 k0, S, Rs to either neighbour). A **tabbed main view** holds resolution map,
table of peaks, fit parameters and resolution. The **chromatogram is pinned beneath the tabs**,
always visible. A **status bar** at the foot carries the condition on show.

Carried forward from the prototype: numbered 1→4 worksheet guidance as the **empty state**;
**sticky chromatogram** while scrolling; **fit-parameter table promoted** — it gets its own tab and
is never hidden in an expander.

**Resolution map**: the tab ships in v0.1 as an empty frame — real axes (tG × initial hold) and a
marker for the current condition, with the field deliberately blank and captioned as v0.2 (§11).
The engine can already sweep it, which is exactly the reason: a filled contour would be
indistinguishable on screen from a map a chromatographer could pick a method from, and a plot that
would be acted on has to be data.

**Chromatogram**: sum of Gaussians. Where areas exist a peak's **area** carries its share — a
detector trace conserves area, so a broader peak is drawn shorter for the same amount injected;
where they do not, every peak is drawn to the same height, which claims nothing about amounts.
Peak labels; hover values. Rs is colour-coded on the conventional reading (1.5 baseline separation,
2.0 robustness target) — a display convention, explicitly not one of §6's thresholded diagnostics.

## 8. Session persistence ([#12](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/12))

Single human-readable JSON, **inputs only** — the fit recomputes on load. Save = download button; load = sidebar uploader. No server-side store, no auto-save in v0.1.

```json
{
  "schema_version": 1,
  "app_version": "0.1.0",
  "session_name": "…",
  "method": { "column_length_mm": 100, "column_id_mm": 2.1, "particle_um": 1.6,
              "flow_ml_min": 0.4, "temperature_c": 45, "t0_min": 0.6,
              "t0_source": "measured|estimated", "dwell_min": 0.9375,
              "pct_b_start": 5, "pct_b_end": 95, "hold_min": 0.5, "plate_count": 12000 },
  "runs": [ { "tg_min": 15, "name": "…" }, { "tg_min": 45 } ],
  "peaks": [ { "name": "…", "tr_run1_min": 9.855, "tr_run2_min": 20.831,
               "area_run1": 13352, "area_run2": 13401,
               "w_half_run1_min": 0.033, "w_half_run2_min": 0.061 } ],
  "untracked_peaks": [ { "name": "…", "tr_run1_min": 13.204, "area_run1": 8801 } ],
  "candidate": { "tg_min": 25, "hold_min": 0.5 }
}
```

Mandatory: `schema_version` (exact match, else the file is rejected), `app_version`, and per
block `flow_ml_min`, `t0_min`, `dwell_min`, `pct_b_start`, `pct_b_end`, each run's `tg_min`,
each peak's two retention times, and the candidate's `tg_min`. Everything else is optional and
simply absent when unset — including the whole `untracked_peaks` table, whose own rows have no
mandatory field. `runs` holds exactly two; the gradient they share is stored once, in `method`.
Rejection is hard and names the field — a corrupt or unknown-schema *file* has no usable
reading, which is separate from §4's warnings-over-blocks posture on user entry.

Two decisions taken while building ([#18](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/18)), reflected above:

- **`peaks` is a top-level table, one row per compound**, both runs side by side — not nested
  inside each run. That is what peak tracking produces (§5); nesting would force name-based
  re-matching on load, and names are optional.
- **Dwell is stored as `dwell_min`**, not a volume. V_D ÷ F is an entry-boundary conversion
  (§4); keeping it out of the file makes the stored dwell independent of a later flow edit and
  the round trip exact.

And one taken in [#21](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/21):

- **Half-paired rows have their own table, `untracked_peaks`.** §5 keeps a row missing either
  tR visible as "untracked — not fitted" while insisting the engine receives only complete
  pairs, so `peaks` cannot hold one and, before this, the file dropped it silently — and
  mid-entry is exactly when a session gets saved. Its rows are the same shape as a `peaks` row
  with both retention times optional; **at most one** tR per row, and a row carrying both is
  refused on save and on load, because it is a tracked peak in the wrong table and the visible
  count would then be wrong. `schema_version` stays **1**: the key is additive, so every file
  written before it still loads, and a session with nothing half-paired writes no such table
  at all. The cost, accepted: a reader older than #21 would take such a file and drop those
  rows silently — which this app is not, and there is one app.

## 9. Architecture and stack ([#6](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/6))

Python ≥ 3.12 · uv · ruff · mypy (strict on the engine and on the app's logic layer; only the Streamlit entry point is excluded) · pytest. **Thin Streamlit app over a pure engine library** — the engine imports no UI code and is what the test suite targets.

```
src/hplcsim/      # the engine: a pure library, importing no UI code
  model.py        # Method, Gradient, Run, Peak, RetentionParams; the φ and log-convention boundaries
  retention.py    # predict_retention(params, method, gradient) -> RetentionResult (regime branches)
  fit.py          # fit_peaks(peaks, method, run1, run2) -> list[FitResult]  (seed + Brent)
  width.py        # peak_width, fit_plate_count -> PeakWidth, FittedPlateCount (G, and N per peak)
  resolution.py   # resolution_table(...) -> ResolutionTable (adjacent pairs, critical pair)
  session.py      # JSON schema v1 load/save + validation
streamlit_app.py  # the app's entry point — at the root because `streamlit run` puts the
                  # script's own folder on sys.path, so an entry point inside app/ cannot
                  # import app.pipeline at all
app/              # the Cockpit: depends on the engine, never the reverse
  pipeline.py     # entry -> fit -> prediction, Streamlit-free (what the app's tests target)
  diagnostics.py  # §5's entry checks and §6's six diagnostics, thresholds and wording
  chromatogram.py # the Gaussian sum, and the v0.2 resolution-map frame
  tables.py       # the display frames; the base-10 display boundary
  panels.py       # the left rail's label/value blocks
  session_io.py   # §8's file <-> the screen's inputs; the download's filename
  worksheet.py    # §7's guided empty state: the four steps, and when each is done
tests/          # three-layer suite (§10)
validation/     # lab dataset (committed) — protocol + method.csv + run1..4.csv
docs/research/  # merged research docs (normative math + datasets)
```

## 10. Validation and acceptance ([#9](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/9), [#3](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/3), [#8](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/8))

Automated three-layer bar (pytest, red until met):

1. **Internal**: closed form vs numerical integration of the fundamental gradient equation ≤ 1e-10; synthetic round-trip of the fit ≤ 1e-8.
2. **Reference**: reproduce the Guillarme 2022 worked spreadsheet ≤ 1e-6 (catches convention slips).
3. **Reality**: den Uijl Sets X and Y (`docs/research/validation-datasets.md`, incl. the corrected Set X cell): median |ΔtR| ≤ 0.5%, worst ≤ 2%, **mean signed error ≤ 0.2%**.

End-to-end trust bar — **already passed pre-build** on the lab dataset and re-asserted as a test: predict `run3.csv` from runs 1–2 within avg |ΔtR| ≤ 2%, worst ≤ 5%, order correct (measured: 0.35% / 0.53% / ✓); `run4.csv` as the extrapolation case (measured: 0.26%). Rs ± 0.3 **is not met** (#17; re-evaluated with fitted N in #23). Runs 3–4 carry W½, so measured Rs at a held-out condition exists and the comparison was made. #17's obstacle — a defaulted N leaving the engine 18–39% optimistic on Rs — is closed: with N fitted from the scouting widths, held-out Rs lands at 0.955 / 0.956× measured at tG = 25 (inside the ±9–13% that run 3's two-decimal W½ can resolve) and 0.935 / 0.900× at tG = 60 (a real residual against three-decimal widths) — 1.5–11.6 absolute Rs units low, where the default was 13–26 high. What remains is the obstacle that was always second, detailed in research doc §6: the sample's pairs sit at Rs 30–116, where ±0.3 is a 0.3–1% tolerance no width model meets and no method decision needs; the bar needs a sample containing a near-critical pair. **What is asserted instead**: the critical pair is identified correctly at both held-out conditions under either N; fitted-N widths within 0.9–1.25× and Rs within 0.85–1.05× of measured, with the tG = 25 Rs inside its measurement band and the tG = 60 residual pinned as outside it; the defaulted-N optimism band kept for the width-less path; and the unmet ±0.3 pinned as a number, so this sentence fails the day it stops being true. Residual note: signed bias flips between conditions (+0.35% / −0.26%) — mild LSS curvature, chromatographically negligible.

## 11. Roadmap ([#10](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/10))

v0.2 resolution map / optimizer (max-of-minimum Rs over swept tG/hold) → v0.3 gradient freedom (changed φ0/φf + multi-segment) → v0.4 CSV import + auto peak-matching + ≥2-run regression (+ isocratic mode) → v0.5 temperature (2×2) → v0.6 colleague hosting + sharing → v0.7 pH (three-run design) → v0.8 column selectivity DB + method transfer → v0.9+ structure-based (pKa/logD) prediction.

## 12. Assets

- Research: `research/gradient-math`, `research/validation-datasets` branches (merge into `docs/research/` at build start)
- UI prototype: `prototype/main-screen` (throwaway; the Cockpit decision is what carries forward)
- Lab dataset: `validation/` on main
- Decision record: [wayfinder map #1](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/1) and its ten closed tickets
