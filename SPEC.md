# HPLC Gradient Method Simulator — Specification

The destination of the [wayfinder map (#1)](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/1) (v0.1) and of [map #41](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/41) (v0.2, gradient freedom). Every section links the ticket holding its decision detail. Status: **v0.1 built and validated; v0.2 gradient freedom approved — ready to cut build tickets.** Where a v0.2 paragraph changes a v0.1 rule it says so; everything unmarked is v0.1 and stands.

## 1. Purpose and audience

A Python simulator for **working chromatographers making real method-development decisions** ([map](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/1)). The user enters two gradient scouting runs; the app fits per-peak retention parameters; it then predicts retention times, peak widths, resolution, and the rendered chromatogram for any candidate linear gradient. Quantitative honesty beats visual polish throughout. v0.1 serves a single user locally ([#6](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/6)).

**Already validated on real data**: the exact algorithm specified here, run against the driver's Acquity H-Class / CORTECS 2.1×100 dataset ([#8](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/8)), blindly predicted a tG = 25 min confirmation run to **0.42% average |ΔtR|** and a tG = 60 min out-of-bracket run to **0.34%** — inside the trust bar by ~5× (at the measured t0 = 0.525 min; 0.35% and 0.26% pre-build at 0.6).

**v0.2's gradient freedom was validated the same way, before it is built** ([#46](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/46)): eleven held-out runs on two samples — raised starts, a lowered end, peaks eluting in a hold, one two-segment programme and a triplicate — scored blind against pre-registered predictions. The numbers are in §10.

## 2. Scope

**In (v0.1):** reversed-phase gradient elution; two-run fit; prediction of linear gradients (tG and initial hold) within the calibrated %B range; chromatogram rendering; resolution table; diagnostics; session save/load.

**In (v0.2, [map #41](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/41), scope [#42](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/42)):** **gradient freedom** — the candidate gradient is a *programme*: its own start %B, initial hold and one or more linear segments (a flat segment is a hold), independent of the scouting runs, which keep their two-run design. With it: the composition-window diagnostics (§6, 1 and 7–9), the Cockpit's programme tables and chromatogram overlay (§7), the session file's programme rows (§8) and the acceptance bar that validates it (§10).

**Out of this effort entirely** ([map](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/1)): quantitation features (calibration, LOD/LOQ, SST reporting); instrument control / CDS connectivity.

**Deferred to named cycles** (§11): everything else, including ≥2-run regression, CSV import, temperature, pH, hosting, the resolution map, column DB, structure-based prediction. A third scouting run at a raised start — which would calibrate a φ0 correction — is a v0.3 item, not a v0.2 one (§10).

## 3. Science model ([#2](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/2); v0.2 programme: [#42](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/42), [#58](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/58))

Normative detail with derivations, symbol table, and citations: `docs/research/gradient-elution-math.md` (branch `research/gradient-math` — merge into main during build).

- **Retention model**: linear solvent strength (LSS). **Internal convention: natural log** — ln k = ln k0 − S_e·(φ − φ0); **display convention: base-10** (S = S_e / ln 10) since chromatographers read S ≈ 2–6. The log-base trap is the #1 implementation hazard; the convention boundary lives in exactly one display-layer function.
- **Gradient retention** (linear ramp, pre-gradient isocratic period τ = t_D + t_init):
  tR = τ + t0 + (t0 / b_e) · ln[b_e·(k0 − τ/t0) + 1], with b_e = t0·Δφ·S_e / tG.
- **Gradient programme** (v0.2): a candidate is φ0, an initial hold t_init, and an ordered list of linear segments, each a duration and an end composition; a segment whose end composition repeats the previous one is a hold. The composition arriving at the column inlet is the pump programme delayed by t_D. Retention is the fundamental gradient equation (research doc §2.1) walked **piecewise**: the band's migration fraction x advances through each ramp by the §2.2 closed form with k taken at the segment's entry composition and b_e,seg = t0·Δφ_seg·S_e / duration (signed: a descending segment slows the band), through each hold isocratically at 1/(t0·k), and the segment in which x reaches 1 gives tR in closed form; a band still on-column after the last segment finishes isocratically at the final composition (the existing post-gradient branch, §4.2 of the research doc). The derivation is re-derived from den Uijl 2021 Eq. 7–8 (research doc ref. 4) and recorded in `docs/research/gradient-elution-math.md` at build; AutoLC-BO's implementation is read, never ported (CC BY-NC-SA — `docs/research/github-hplc-simulators.md` §6). **A one-segment programme takes v0.1's closed-form path and is bitwise identical to it**; the walker is entered only for two or more segments and is checked against numerical integration of §2.1 (§10). **The segment count is open** — the closed form is exact at any count, so there is no cap and nothing in the app is keyed to the count; what is validated is recorded in §10, not stamped per candidate.
- **Two-run fit** (per peak, independent): no exact closed form exists. Algorithm: closed-form large-k0 seed, then 1-D root-find (Brent) on the run-2 residual; round-trip the fitted (k0, S_e) against both input tR to ≤1e-8 as a self-check. The closed form alone is forbidden as a final answer (138% S error at k0 = 8).
- **Edge cases** get explicit branches, not one formula: elution during dwell/hold; elution after gradient end (G = 1 there, no band compression); very early eluters (k ≈ 1 territory → low-confidence badge); degenerate inputs (tG1 = tG2 → refuse). v0.2 adds: elution during a *later* hold or after the last segment ends (G = 1; the per-peak wash-eluted badge, §6 diagnostic 9), and a segment that starts after a peak has eluted, which changes that peak by exactly zero.
- **Peak width**: σ_t = (t0 / √N)·(1 + k_e)·G; band-compression factor G per the research doc. **N is per peak, measured-first** ([#23](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/23)): fitted from that peak's scouting W½ when entered — the inverse of the width equation, one N per peak as the geometric mean of what each width implies (`docs/research/plate-count-from-widths.md` §3–§4) — otherwise the global knob, otherwise the column-based default. A fitted N is an apparent, instrument-inclusive efficiency conditional on the calibrated G: not the column's intrinsic N, and not a pharmacopoeial plate number. **Hazard status — RESOLVED** (#17; evidence in research doc §5.4): the convention was calibrated against the measured W½ in `validation/run1–4.csv`. Holding one column's plate count constant across a fourfold range of gradient steepness works to 1.2% under the natural-log reading and to 3.8–9.4% under every alternative, including the ×ln 10 mirror (at the measured t0 = 0.525 min; 0.92% and 5–13% at the 0.6 the fixtures first carried — [#24](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/24)); confirmed on runs 3–4, which are held out of the fit. Peaks without widths still carry the second uncertainty: a defaulted N is column geometry, not the column's real efficiency.
- **Band compression for a programme** (v0.2): G is taken from the segment in which the band elutes — p formed from that segment's b_e,seg and the k at the band's entry to it — and G = 1 for a band leaving in a hold or after the last segment. The cumulative band-compression integral that #42 named (Hao et al. Eq. 10, research doc §5.2) was considered and deferred: this rule is the approximation shipped. It is unvalidated by any multi-segment width measurement and §10 makes no Rs claim for multi-segment; a one-segment programme reproduces v0.1's G exactly.
- **Resolution**: Rs = (tR₂ − tR₁) / (2·(σ₁ + σ₂)) per adjacent pair; critical pair = minimum Rs.

## 4. Input contract ([#4](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/4))

**Method constants** (one block, shared by both scouting runs — identical except tG):

| Field | Rule |
|---|---|
| Column length / i.d. / particle | mm / mm / µm; metadata + basis for estimates |
| Flow F | mL/min |
| t0 | **measured-first**: marker time (min) primary. Geometry estimate as labeled fallback, **autofilled** into the field and stamped `t0_is_measured = False`; typing over it flips the source back to measured. The estimate is `t0 = ε_total · (π/4) d_c² L / F`, ε_total selected by **declared packing architecture** — fully porous 0.62 (band 0.52–0.70), core–shell 0.52 (band 0.45–0.60), `docs/research/porosity-for-t0-geometry.md` §5.1. It needs the column i.d. and length only. **Architecture is never inferred, and there is no default**: undeclared raises a typed error naming the field, as `default_plate_count` does for a missing column length. The band is a caption beside the field, never a ± on a fitted parameter ([#24](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/24), [#34](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/34)) |
| t0 marker | free text captured with a measured t0: what was injected and which point of its trace was read ("uracil, apex"; "solvent front, first disturbance"). Warned when absent, a solvent disturbance, or an inorganic salt (`docs/research/dead-time-from-geometry.md` §5.2) — a dead time without its marker has no provenance |
| Extra-column volume | **derived readout**, whenever a measured t0 and a declared architecture coexist. The app reports implied ε_total = F·t0 / V_col and implied V_ec = F·(t0 − t0,geom) as a statement of fact, not a warning: geometry excludes V_ec by construction, so a measured t0 **above** the geometry estimate is the expected ordering. Warnings fire only on ε_total > 1 (hard), ε_total outside [0.35, 0.80], V_ec negative (usually a mis-declared architecture), or V_ec ≥ 80 µL (marker likely retained) |
| Dwell | required, no silent default; entered as t_D (min) or V_D (mL, ÷F); in-app measurement guidance |
| Scouting gradient | %B start, %B end (UI 0–100; φ internal), optional initial hold t_init (min); one linear segment, shared by both scouting runs. **Unchanged in v0.2** ([#46](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/46) decision 9): the two runs sharing φ0/φf/t_init is what makes the two-run fit well-posed, so `fit.py::_check_runs_are_a_scouting_pair` stays. Freedom is a property of the candidate |
| Temperature | °C, metadata only (fixed-T model); sample-manager temp optional provenance |
| Plate count N | **per peak, measured-first** (the t0 posture): fitted from the peak's W½ when entered; otherwise the global knob; otherwise the column-based default, stamped lower-confidence ([#23](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/23)) |

**Runs**: exactly two; only tG differs; recommend tG and ~3·tG; spacing-ratio warning < 2.5, strong < 1.2, never a hard block.

**Per peak**: tR in run 1 and run 2 mandatory (min). Optional: name (auto P1…Pn), **per-run area** (raw or % — normalized to shares internally; [#7](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/7)/[#8](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/8) refinements), width-at-half-height W½ (min).

**Prediction targets** (v0.2, [#42](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/42), [#45](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/45), [#58](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/58)): **any gradient programme** — its own %B start, initial hold, and one or more linear segments each given as a duration and an end %B (a flat segment is a hold), entered as a No. / Time / %B table (§7). The %B range is free of the scouting runs' and the segment count is open. Leaving a peak's calibrated composition window — there is no method-level window — is warned about (§6, 1 and 7–9), never refused. (v0.1 allowed tG and t_init only, within the scouting φ0→φf range.)

**Validation posture**: warnings over blocks; per-peak sanity tR > t0; tG values must differ; every segment duration positive. A candidate whose %B range differs from the scouting runs' is a **warning**, on entry and on session load — `session.py::_check_candidate` no longer raises ([#44](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/44)).

## 5. Peak tracking ([#5](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/5))

Manual and implicit: **one row per compound**, tR(run 1) and tR(run 2) side by side — the chromatographer pairs peaks while typing. The app checks rather than performs the pairing: area-share disagreement warning (default threshold ~30% relative change, measured against the first run's share — on the lab dataset peak 2 moves 40.9% and fires, peak 3 moves 26.7% and does not, peak 1 moves 22.8%; a good live test, and the two peaks the integrator mis-measured are the two the check ranks highest); elution-order crossing flags for confirmation; rows missing either tR stay visible as "untracked — not fitted", excluded from fit/prediction/resolution with a visible count; within-run co-elution entry legal (area check relaxes). The engine receives only confirmed, complete pairs.

## 6. Diagnostics ([#9](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/9); v0.2: [#44](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/44), [#58](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/58))

Six ship in v0.1; v0.2 re-expresses 1 and adds 7–9:

1. **Steepness extrapolation** (v0.1's tG extrapolation, re-expressed on s\* by [#44](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/44): elution composition depends on the candidate only through the steepness s\* = t0·Δφ/tG — `docs/research/composition-extrapolation.md` §7.2 — so the tG bracket and the composition bracket are one guard). Each ramp segment's s\* (s\*_seg = t0·|Δφ_seg| / duration) is bracketed against the scouting pair's [s\*₂, s\*₁]; the overshoot is measured in **window-widths**, log_β(s\*_edge / s\*_cand), one method-level number identical for every peak (S_e cancels). **Gentle** from 0 to ~0.6 window-widths outside, **strong** beyond, and the strong tier keeps its remedy: confirm by injection, or move a scouting run out to meet it. Flat segments are holds and are never bracketed (s\* = 0 has no position in a steepness bracket); the tier is that of the worst segment **in which at least one peak is predicted to elute**, so an inert trailing wash cannot fire it, and the diagnostic is silent when every peak leaves in a hold or after the programme ends ([#58](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/58)). No boundary margin on the segment attribution. Identical to the v0.1 tG bracket for every v0.1 session. Provenance ([#55](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/55), re-pinned 2026-09-03 at t0 = 0.525): 0.6 is **v0.1 continuity** — log₃ 2 = 0.63, the "~2× outside" tier v0.1 users already have on plain t_G extrapolation — not a number the data set. The data neither support nor refute it: no on-ramp run sits beyond 0.26 window-widths, and the gentle band to 0.26 is measured harmless — three-peak run 4 (0.26 out, tG 60) scores 0.34 % avg |ΔtR| and three-peak run 6's ramp peaks (0.20 out) 0.21 %, both below the in-window run 3's 0.42 %. The one run further out, four-peak run 5 at 0.35 window-widths, elutes every peak in the post-gradient hold, where 1 is silent by [#58](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/58) and 9 speaks; its 1.51 % belongs to the hold, not to the bracket. **The strong tier is untested by real data** and stays so until a run beyond 0.6 window-widths elutes on the ramp.
2. **Early-eluter badge** (elutes near t0 + dwell + hold). Owns the initial hold.
3. **β-spacing escalation** on fit results. v0.2 adds one sentence to its message: a narrow β also narrows every peak's calibrated composition window, ln β / S_e — about 10 %B per peak on the 5 → 95 %B scouting pairs on file, and disjoint between peaks.
4. **Prediction crossing flags** (order at candidate differs from scouting runs).
5. **Width/Rs caveat banner**. The G convention is settled (§3, #17) and N is fitted wherever widths exist (#23), so the banner is scoped to peaks whose N is *defaulted*: a geometry estimate runs 0.69–0.92× on measured lab widths and 18–39% optimistic on Rs at held-out conditions, where a fitted N lands at 0.99–1.16× and −4 to −10%. The engine stamps every width with `PeakWidth.plate_count_source` (`"default"` / `"supplied"` / `"fitted"`); the banner reads `"default"`. A fitted N's `FittedPlateCount.low_confidence` (its only width came from the post-gradient regime; such a width is left out whenever the other run's is usable) is a per-peak badge, not a banner. Wording is ticket #19's. Absolute widths and Rs are caveated for defaulted peaks; the critical *pair* is not — it is identified correctly at both held-out conditions under either N.
6. **Estimated-t0 stamp** on all outputs when t0 is entered as an estimate rather than a measured marker time, worded to the two regimes rather than a bare "lower confidence": retention predictions for the fitted gradients move ~0.005% per 1% of t0 error, while the fitted S, k0 and N carry ~0.25× the t0 error and **must not be transferred to another flow rate or column** (`docs/research/dead-time-from-geometry.md` §6.2–§6.4; [#24](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/24)).
7. **φ0 departure** (v0.2, [#44](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/44); `docs/research/phi0-dependent-retention-residual.md` §7): method-level, at the candidate controls beside 1; variable Δφ0 = φ0,cand − φ0,scout in %B — the candidate's *start* against the scouting start only; a later segment that steps above the scouting start earns no term, because every mechanism left standing acts while the band sits at the head of the column ([#58](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/58)). **Gentle for any non-zero Δφ0** — the fit was never shown a run starting anywhere else; **strong from Δφ0 ≥ +10 %B** ([#55](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/55): the smallest departure measured, and at that step the retention error doubled on both samples and reached λ = 1.58 on the three-peak sample — the retention error in peak-width units (item 8), so over one peak width; no run sits between 0 and +10 %B, so the tier is untested below it). Δφ0 is a *departure*: a method scouted at 0, 2 or 75 %B is silent until its candidate starts above its own scouting start, and the absolute start is 8's business. Lowering φ0 is gentle at any amount, with a message saying there is no data either way. **No correction is fitted.** The message quotes what was observed, not a rule: on this instrument, from scouting pairs starting at 5 %B, the first 10 %B above the scouting start roughly doubled the retention error on both samples (0.42 → 0.82 % on the three-peak sample, 0.11 → 0.23 % on the four-peak); beyond that, one sample kept doubling (1.67 % at +20 %B) and the other flattened (0.26 %). **No multiplier is evaluated for the candidate** — a rule wrong on one of two samples would read as a prediction — and the message says the ladders were measured from 5 %B starts, so a pair scouted elsewhere has the guard and not the numbers. Figures at t0 = 0.525. Why a separate term: s\* is necessary, not sufficient — campaign #27's runs 3 and 5 are s\*-matched to 0.1 % and the residual still doubles; E1 (2026-09-03, at 0.525) splits four-peak run 4's excess over run 3 into +0.010 min from φ0 and +0.007 min from steepness, so the axis is φ0 at roughly a 60/40 share, and the steepness share sits inside the s\* bracket where 1 is silent by design. No φf term: φf enters elution composition only through Δφ, which 1 covers. Re-pinned by [#55](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/55) after the t0 re-baseline ([#24](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/24)); the mechanism is outside the v0.2 map's scope.
8. **Low-k0 badge** (v0.2, per peak, single tier): log₁₀ k0 at the candidate's φ0 below 2.1 — Guillarme's floor, the engine's `_LOW_K0_LOG10`. A limit of the closed form rather than of this engine's arithmetic, but a real regime signal: the one measured crossing, three-peak run 7 Unknown-1 at log₁₀ k0 ≈ 1.7, had the dataset's worst λ, 1.90 — the retention error in peak-width units, (tR,pred − tR,meas) / w (`docs/research/phi0-dependent-retention-residual.md` §6.2). One point, hence one tier. Sits beside 2 (the same physics from the other side) and does not stand in for 7 — the φ0 residual is already large at log₁₀ k0 = 3.2.
9. **Wash-eluted badge** (v0.2, per peak, single tier, [#58](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/58)): a peak predicted to leave during a *later* flat segment or after the last segment ends (`regime == "post_gradient"`) — its retention rests on k extrapolated to a composition the fit never saw. The initial hold is 2's. Evidence, cutting both ways: three-peak run 6 Unknown-3 left in the wash at 46.8 min against a pre-registered 47.0 — the extrapolation held on the one case measured, which is why this is one tier and not a stamp; it was unmarked, which is why it exists.

**What a prediction may claim** ([#44](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/44) decision 8). Inside the s\* bracket with φ0 unchanged: v0.1's claim, unchanged. Gentle on 1 or 7: numbers unchanged; the inline warning names the distance (window-widths for s\*, %B for φ0) and the fit tab names the peaks sitting outside their windows. Strong on either: keep predicting, say plainly that the LSS line was never pinned there, and **stamp Rs and the critical pair as indicative, not decision-grade** — an output stamp in the manner of 6; retention times stay shown as numbers. The ladder is driven by the worse of 1 and 7. A low-k0 or wash-eluted badge downgrades only the pairs involving that peak. **Nowhere does the app claim curvature-corrected accuracy** — two parameters cannot see curvature.

Presentation: per-peak badges (2, 4, 8, 9 — in the Flags column and the selected-peak panel), fit-page notices (3), a **per-peak composition-window readout** on the fit-parameters tab (each peak's calibrated window [φ_e,run2, φ_e,run1] in %B, its width ln β / S_e, and where the candidate puts that peak's elution composition relative to it — the per-peak fact behind 1, whose tier is method-level), result banners (5), output stamps (6, and the indicative stamp on Min. Rs, the resolution tab and the status bar), candidate-control inline warnings (1, 7) directly beneath the candidate table. The stamp's **per-pair scoping is carried on the resolution tab as an Rs-grade column** ([#74](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/74)): the method-level stamp marks every pair, a badge marks only the pairs its own peak is in, and Min. Rs and the status bar follow the **critical pair** — so a badged peak inside the critical pair downgrades the Rs the screen leads with even when neither 1 nor 7 has fired.

## 7. UI ([#7](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/7))

**Cockpit layout** (modelled on the instrument software this tool sits beside — DryLab and its
relatives — at the driver's direction during [#19](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/19);
the prototype variant on branch `prototype/main-screen` is superseded): sidebar = instrument and
column constants + N knob (its gradient block moves into the rail in v0.2). A **left rail** carries
the condition as two **No. / Time / %B tables** (v0.2, [#45](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/45), picked as variant D of
`prototype/candidate-programme`): the **scouting programme** — read-mostly, # / t₁ / t₂ / %B, one
programme at two speeds (row 2 follows row 1's %B), where the scouting tG values, hold and %B are entered — directly above the
**candidate programme** (t / %B, dynamic rows; a further segment is a further row). **No slider
pairs and no tG slider**: two controls for one number pushed the inline warnings below the fold, the
table cell steps with the keyboard, and the sweep a slider stood in for is the resolution map's job.
The two candidate-control warnings (§6, 1 and 7) sit directly beneath the candidate table. (v0.1's
rail carried scouting tG values, candidate tG and initial hold as sliders.) Below: a **Method
summary** panel (peaks fitted, untracked count, minimum Rs and its critical pair, programme length,
last peak, minimum k) and a **Selected peak** panel (tR, k at elution, W½, N and where it came from,
log10 k0, S, Rs to either neighbour). A **tabbed main view** opens on the table of peaks, then fit
parameters, resolution, and the resolution map last. The **chromatogram is pinned beneath the tabs**,
always visible. A **status bar** at the foot carries the condition on show.

Carried forward from the prototype: numbered 1→4 worksheet guidance as the **empty state**;
**sticky chromatogram** while scrolling; **fit-parameter table promoted** — it gets its own tab and
is never hidden in an expander.

**Resolution map**: the tab ships in v0.1 as an empty frame — real axes (tG × initial hold) and a
marker for the current condition, with the field deliberately blank and captioned as a later cycle (v0.7, §11).
The engine can already sweep it, which is exactly the reason: a filled contour would be
indistinguishable on screen from a map a chromatographer could pick a method from, and a plot that
would be acted on has to be data.

**Chromatogram**: sum of Gaussians. Where areas exist a peak's **area** carries its share — a
detector trace conserves area, so a broader peak is drawn shorter for the same amount injected;
where they do not, every peak is drawn to the same height, which claims nothing about amounts.
Peak labels; hover values. Rs is colour-coded on the conventional reading (1.5 baseline separation,
2.0 robustness target) — a display convention, explicitly not one of §6's thresholded diagnostics.

**Programme overlay** (v0.2, [#45](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/45)): the candidate programme is drawn **solid** on a right-hand
%B axis with the scouting programmes **dashed**, so "as run" and "predicted" are distinct where the
prediction is read as well as where it is typed; each peak carries a marker at its elution
composition with its calibrated composition window as the whisker. **Always on**, never behind a
toggle — the strong-tier states are when it must be seen. Both programmes are drawn on the
chromatogram's own time base, which is the **detector's**: the pump's programme delayed by
t_D + t0, the same expression the gradient-end marker uses. That is what makes the picture
readable rather than merely adjacent — every peak's marker lies *on* the candidate curve,
because the composition a band leaves the column in is the composition arriving at the detector
at that instant, on a ramp, on a descending leg and in a hold alike. What the reader then judges
is the marker against its own **whisker**: a marker outside it is a peak being predicted at a
composition the fit was never shown, which is the per-peak fact behind §6's diagnostic 1
([#74](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/74)). The **axis range is its own always-open
strip**: a pinned row between the chromatogram and the status bar with x start, x end, y start,
y end and Reset, never inside the plot's own scroll. Spacing is compact enough that at 1440 × 900
both tables, both inline warnings, the chromatogram with its overlay and the axis strip are on
screen (build items [#61](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/61), [#62](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/62)).

## 8. Session persistence ([#12](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/12); v0.2: [#47](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/47))

Single human-readable JSON, **inputs only** — the fit recomputes on load. Save = download button; load = sidebar uploader. No server-side store, no auto-save in v0.1.

```json
{
  "schema_version": 2,
  "app_version": "0.2.0",
  "session_name": "…",
  "method": { "column_length_mm": 100, "column_id_mm": 2.1, "particle_um": 1.6,
              "flow_ml_min": 0.4, "temperature_c": 45, "t0_min": 0.525,
              "t0_source": "measured|estimated", "t0_marker": "uracil, apex",
              "particle_architecture": "fully_porous|core_shell", "dwell_min": 0.9375,
              "pct_b_start": 5, "pct_b_end": 95, "hold_min": 0.5, "plate_count": 12000 },
  "runs": [ { "tg_min": 15, "name": "…" }, { "tg_min": 45 } ],
  "peaks": [ { "name": "…", "tr_run1_min": 9.855, "tr_run2_min": 20.831,
               "area_run1": 13352, "area_run2": 13401,
               "w_half_run1_min": 0.033, "w_half_run2_min": 0.061 } ],
  "untracked_peaks": [ { "name": "…", "tr_run1_min": 13.204, "area_run1": 8801 } ],
  "candidate": { "pct_b_start": 15, "hold_min": 0.5,
                 "segments": [ { "tg_min": 25, "pct_b_end": 55 }, { "tg_min": 5, "pct_b_end": 95 } ] }
}
```

Mandatory: `schema_version` (a version this app knows — 1 or 2 — else the file is rejected),
`app_version`, and per block `flow_ml_min`, `t0_min`, `dwell_min`, `pct_b_start`, `pct_b_end`,
each run's `tg_min`, each peak's two retention times, and the candidate's `pct_b_start` and its
`segments` — at least one, each with `tg_min` and `pct_b_end`. Everything else is optional and
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

And one taken in [#47](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/47) (v0.2):

- **The candidate is a programme, and `schema_version` becomes 2.** `candidate` carries its own
  `pct_b_start`, `hold_min` and a `segments` list — one row per segment, `tg_min` and
  `pct_b_end`, a hold being a segment whose `pct_b_end` repeats the composition before it — the
  same rows as the rail's table (§7), so the file stays a transcript of what was typed. This
  restructures the block rather than adding a key, which is why the version moves where #21's
  did not. A version-1 file is still read: its two-field candidate becomes one segment over the
  scouting range, exactly what it meant, and every file written is version 2; the exact-match
  rule becomes a known-version rule. The scouting gradient stays stored once in `method`, and
  the candidate's range no longer has to equal it — the check that enforced that is a warning
  at load ([#44](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/44)), delivered as §6's diagnostics once the session is on screen. `t0_marker` and
  `particle_architecture` in `method` are #24's two optional fields, absent when unset.

## 9. Architecture and stack ([#6](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/6))

Python ≥ 3.12 · uv · ruff · mypy (strict on the engine and on the app's logic layer; only the Streamlit entry point is excluded) · pytest. **Thin Streamlit app over a pure engine library** — the engine imports no UI code and is what the test suite targets.

```
src/hplcsim/      # the engine: a pure library, importing no UI code
  model.py        # Method, Gradient, Run, Peak, PeakRow, RetentionParams; v0.2: Programme,
                  # Segment;
                  # the φ and log-convention boundaries
  retention.py    # predict_retention(params, method, gradient) -> RetentionResult (regime branches);
                  # v0.2: the piecewise programme walker, entered only for ≥ 2 segments
  fit.py          # fit_peaks(peaks, method, run1, run2) -> list[FitResult]  (seed + Brent)
  width.py        # peak_width, fit_plate_count -> PeakWidth, FittedPlateCount (G, and N per peak)
  resolution.py   # resolution_table(...) -> ResolutionTable (adjacent pairs, critical pair)
  dead_time.py    # t0 from column geometry, and the reverse check on a measured t0 (#24)
  session.py      # JSON schema v2 load/save + validation (reads v1)
streamlit_app.py  # the app's entry point — at the root because `streamlit run` puts the
                  # script's own folder on sys.path, so an entry point inside app/ cannot
                  # import app.pipeline at all
app/              # the Cockpit: depends on the engine, never the reverse
  screen_state.py # the only module that touches Streamlit's per-session store: the Keys
                  # registry, the accessor every touch goes through, and §8's restore
  entry.py        # what the user typed: the peak table split, the rail's programme tables,
                  # SPEC §4's two entry conversions
  pipeline.py     # fit -> prediction, Streamlit-free (what the app's tests target)
  diagnostics.py  # §5's entry checks and §6's nine diagnostics, thresholds and wording
  chromatogram.py # the Gaussian sum, the resolution-map frame (filled at v0.7), v0.2's programme overlay
  tables.py       # the display frames; the base-10 display boundary
  panels.py       # the left rail's label/value blocks
  session_io.py   # §8's file <-> the screen's inputs; the download's filename
  worksheet.py    # §7's guided empty state: the four steps, and when each is done
tests/          # three-layer suite (§10)
validation/     # lab datasets (committed) — protocol + method.csv + run1..7.csv;
                # Validation_2/ (the four-peak sample); run-sheets/ (pre-registered predictions)
docs/research/  # merged research docs (normative math + datasets)
```

## 10. Validation and acceptance ([#9](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/9), [#3](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/3), [#8](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/8))

Automated three-layer bar (pytest, red until met):

1. **Internal**: closed form vs numerical integration of the fundamental gradient equation ≤ 1e-10; synthetic round-trip of the fit ≤ 1e-8.
2. **Reference**: reproduce the Guillarme 2022 worked spreadsheet ≤ 1e-6 (catches convention slips).
3. **Reality**: den Uijl Sets X and Y (`docs/research/validation-datasets.md`, incl. the corrected Set X cell): median |ΔtR| ≤ 0.5%, worst ≤ 2%, **mean signed error ≤ 0.2%**.

End-to-end trust bar — **already passed pre-build** on the lab dataset and re-asserted as a test: predict `run3.csv` from runs 1–2 within avg |ΔtR| ≤ 2%, worst ≤ 5%, order correct (measured: 0.42% / 0.61% / ✓); `run4.csv` as the extrapolation case (measured: 0.34%). Rs ± 0.3 **is met**, on the near-critical-pair sample the criterion always needed ([#49](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/49), `validation/Validation_2/`); on *this* sample it stays out of reach, for a reason about the sample and not the model (#17; re-evaluated with fitted N in #23). Runs 3–4 carry W½, so measured Rs at a held-out condition exists and the comparison was made. #17's obstacle — a defaulted N leaving the engine 18–39% optimistic on Rs — is closed: with N fitted from the scouting widths, held-out Rs lands at 0.954 / 0.954× measured at tG = 25 (inside the ±9–13% that run 3's two-decimal W½ can resolve) and 0.925 / 0.890× at tG = 60 (a real residual against three-decimal widths) — 1.6–12.7 absolute Rs units low, where the default was 12–24 high. What remains is the obstacle that was always second, detailed in research doc §6: the sample's pairs sit at Rs 30–116, where ±0.3 is a 0.3–1% tolerance no width model meets and no method decision needs; the bar needed a sample containing a near-critical pair, and #49 supplies one — four compounds inside a 0.5 min window, critical pair at Rs 1.75–1.78, every adjacent pair inside ±0.3 at two held-out conditions. **What is asserted instead**: the critical pair is identified correctly at both held-out conditions under either N; fitted-N widths within 0.9–1.25× and Rs within 0.85–1.05× of measured, with the tG = 25 Rs inside its measurement band and the tG = 60 residual pinned as outside it; the defaulted-N optimism band kept for the width-less path; and the ±0.3 miss *on this sample* pinned as a number, so its size cannot drift unremarked. Residual note: signed bias flips between conditions (+0.42% / −0.34%) — mild LSS curvature, chromatographically negligible. All figures at the measured t0 = 0.525 min (re-baselined 2026-09-03, [#24](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/24)); the pre-build figures were at 0.6.

**v0.2 gradient freedom bar** ([#46](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/46), one row added by [#58](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/58)). Every number is at the measured t0 = 0.525 min (the [#24](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/24) re-baseline, [PR #67](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/pull/67), which landed before the tag as the bar required; #46 recorded the same bar at the former 0.6) and the instrument's dwell of 0.375 mL, fitted on each sample's own scouting pair. [#55](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/55) re-pinned the provisional thresholds on 2026-09-03. The tag waits for no further injections (driver, 2026-09-03).

1. **Retention, two layers.** Layer one: the v0.1 coarse bar (avg |ΔtR| ≤ 2 %, worst ≤ 5 %, order correct) on every held-out run of both samples — three-peak runs 3, 4, 5, 7 and the two ramp peaks of run 6; four-peak runs 3, 4, 5, 6, E1 and the E4 replicates. Layer two: each run's **mean signed residual pinned** at its measured value, tolerance the sample's repeatability floor — **0.002 min** on the four-peak sample (run 3's triplicate, `E4_Run3.csv`), measured at φ0 = 5 %B and *assumed* at the raised start; if a later raised-start replicate spreads wider, the floor is the larger of the two. The three-peak sample has no replicates, so its runs stay pinned within #46's interim ± 0.10 %. Per sample, the residual at a raised φ0 is not below the residual at the scouting φ0. **The doubling rule is not asserted.**
2. **Diagnostics — fire / silent on named runs.** 1 fires gentle on three-peak run 6 (0.20 window-widths, its ramp peaks) and three-peak run 4 (0.26) and is silent elsewhere — E1 included, and **four-peak run 5** too (0.35 window-widths below the bracket, but every peak elutes in the hold and none on the ramp, [#58](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/58)); its strong tier is untested. 7 is strong on every run starting above 5 %B (three-peak 5, 6, 7; four-peak 4, 5, 6) and silent on every run starting at 5 %B. 8 fires on three-peak run 7 Unknown-1 (log₁₀ k0 = 1.74) and nowhere else. 9 fires on all four peaks of four-peak run 5 and on three-peak run 6 Unknown-3, and nowhere else. The post-gradient regime flag is set on all four peaks of four-peak run 5 and on three-peak run 6 Unknown-3.
3. **The falsifiable numbers behind the stamp** (re-pinned by [#55](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/55), 2026-09-03, at t0 = 0.525). (a) Per sample, every run **strong on 7 with its s\* inside the scouting bracket** has a mean |ΔtR| above every unstamped run — 0.82 % (run 5) and 1.67 % (run 7) against 0.42 % (run 3) on the three-peak sample; 0.23 % (run 4) and 0.26 % (run 6) against 0.14 % (E1) on the four-peak — what makes *indicative, not decision-grade* honest. Scoped to 7 because 1's strong tier has no run to assert on, and to in-bracket runs because a run carrying both guards is not ordered by |ΔtR|: three-peak run 6 (strong on 7, gentle on 1) scores 0.21 % on its ramp peaks, below run 3, because its two biases have opposite signs — a shallow s\* pulls early (run 4 at a similar s\* sits at −0.106 min) and a raised start pushes late (run 5 at the same start sits at +0.115) — and partly cancel at +0.039 min. Recorded, not asserted: the stamp marks what the fit was never shown, not a guaranteed larger error. Four-peak run 5 is stamped and likewise not ordered: its s\* is outside the bracket, and its −0.511 min is the hold's (item 5), not a bracket effect. (b) **No unstamped run exceeds 0.5 % mean |ΔtR|** on either sample — 0.5 % borrows layer 3's bar on the den Uijl sets (a median |ΔtR| there, a mean here), so one number serves the reference data and the bench data. Largest today: three-peak run 3 at 0.42 % (in-window, no guard fires; 0.35 % at the former 0.6) and four-peak E1 at 0.14 %. Both samples' tests pin the ceiling against the same constant ([#75](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/75)); the three-peak sample is where it binds.
4. **Multi-segment.** (a) One segment takes v0.1's path and is **bitwise identical** to v0.1; a one-segment programme pushed through the walker agrees to 1e-12. (b) Two or more segments: the walker against numerical integration of the fundamental gradient equation ≤ 1e-10. (c) **Inertness**: a segment that starts after a peak has eluted changes that peak's prediction by exactly zero — asserted on four-peak run 5 and on Unknown-1/2 of three-peak run 6. (d) One reality point: three-peak run 6 Unknown-3 at **46.8 min**, pre-registered at 47.0, inside the coarse bar and pinned. Multi-segment is validated on one peak of one sample at two segments; the count is open (§3) and this is the whole of what it rests on. **No Rs claim for multi-segment.**
5. **Rs ± 0.3 extends** to four-peak runs 4, 5, 6 and E1, the worst miss pinned per run as a tripwire (0.05 / 0.06 / 0.12 / 0.03), band set by the width replicates: a raised start up to 20 %B and peaks eluting in a hold, one sample. The sharper claim — predicted Rs inside the instrument's repeatability band — holds on **every on-ramp condition**; run 5, whose peaks elute in the post-gradient hold, sits 0.009–0.020 below the band on all three pairs at t0 = 0.525 (worst miss 0.054, still 5× inside ±0.3), because in a hold t0 enters the retention time directly instead of being absorbed by the fit — pinned as the one off-ramp exception (`_V2_REPEATABILITY_SHORTFALL`). Run 5 is also the case where the stamp is conservative — strong on 7, Rs inside ±0.3 anyway, because peaks in a hold move together; the stamp is about what the fit was shown, not about one outcome.
6. **Held-out reuse.** Three-peak runs 3 and 4 keep asserting gradient-time extrapolation at fixed φ; they assert nothing about composition coverage.
7. **Scouting design unchanged.** Two runs; `_check_runs_are_a_scouting_pair` stays. A third run at a raised φ0 would calibrate a correction the research rules out (right on one sample, wrong on the other) and is a v0.3 item.
8. **E1 and E4 are asserted as measurements**, never as outcomes. E1 (5 → 85 %B, tG 20: +0.026 min, two fifths of the way from run 3's +0.019 toward run 4's +0.036 at t0 = 0.525 — axis predominantly φ0, steepness a smaller share) joins the held-out set under 1, 2 and 5; E4's spread is the floor in 1.

Already wired ([PR #64](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/pull/64), re-pinned at 0.525 by [PR #67](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/pull/67)): four-peak runs 5, 6, E1 and the E4 replicates on items 1, 3, 5 and 8. The three-peak runs 5–7 are wired too ([#75](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/75), on items 1 and 3). Left to the build: item 2 in full, and item 4.

## 11. Roadmap ([#10](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/10))

v0.2 gradient freedom (changed φ0/φf + multi-segment) → **v0.3 CSV import + auto peak-matching + ≥2-run regression (a factor-shaped run table, φ modelled only) + isocratic mode — the next cycle** → v0.4 temperature (2×2; the 1/T form is this cycle's decision) → v0.5 colleague hosting + sharing → v0.6 pKa/logD advice (optional structure per peak, open predictor with the aqueous-to-mobile-phase correction, a readout the fit never reads) → v0.7 pH (three-run design; the cycle decides whether its runs bracket the pKa or avoid it) → v0.8 resolution map / optimizer, as a filled map over live axes (tG × φf, temperature, pH), with the candidate history → v0.9 column and instrument profiles ([#26](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/26), map [#103](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/103)) + geometry-only programme translation + column selectivity DB → v0.10+ structure-based retention prediction. Flow rate and ternary composition are not axes ([#117](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/117), parked). Re-ordered 2026-09-06 against the ACD benchmark ([#114](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/114)); index [#116](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/116).

## 12. Assets

- Research: `research/gradient-math`, `research/validation-datasets` branches (merged into `docs/research/` at v0.1 build start)
- Research (v0.2, on main): `docs/research/composition-extrapolation.md` (the window law and the s\* bracket), `phi0-dependent-retention-residual.md` (the φ0 term), `github-hplc-simulators.md` §5.3 / §6 (the licence ruling on multi-segment), `dead-time-from-geometry.md` and `porosity-for-t0-geometry.md` (t0, for #24)
- UI prototype: `prototype/main-screen` (throwaway; the Cockpit decision is what carries forward)
- UI screenshots of what ships: `docs/screenshots/`, at 1440 × 900 per build ticket — [#62](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/62) (compact spacing and the axis strip), [#73](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/73) (the paired programme tables), [#74](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/74) (the overlay, the composition-window readout and the indicative stamp, on the trap case and a two-segment candidate). Compaction and overlay decisions are checked in a real browser, not in `AppTest`, which has no frontend.
- Programme prototype (v0.2): `prototype/candidate-programme` (throwaway; variant D is the decision, screenshots under `prototype/screenshots/`; `prototype/programme.py` is never ported — multi-segment retention belongs in the engine) and `prototype/candidate-phi` (the parallel attempt, stood down 2026-09-03, kept as a record); the pick page: https://claude.ai/code/artifact/37245417-410f-4730-9407-419ddb87a56b
- Resolution-map prototype: `prototype/resolution-map` (throwaway; three panes over an engine-computed sweep, built for the parked map — superseded as a design, kept as proof that the sweep, the flip location and the co-elution zone all compute)
- Resolution-map target (v0.8 after the 2026-09-06 re-ordering; driver 2026-09-02): a **filled heat map** — colour = critical Rs over two live axes, dashed contour at Rs 1.5 and solid at 2.0, a rail of Legend / Cursor / Pinned point / Method cards, hover to read, click to pin. Reference: `14-Aug-2026 HPLC Simulator/prototype/resolution-map.html?variant=A`. The gate is a second **modelled** axis: temperature (v0.4) is the cheap one, pH (v0.7) the discriminating one for ionisables, and §11 keeps the map after both so it is drawn once, over live axes. Map #28's other gate, a dataset with a critical pair, is met by `validation/Validation_2/` ([#49](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/49)). The initial hold moves the critical Rs by under 1% on the lab dataset ([#30](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/30)).
- Lab datasets: `validation/` (three-peak sample: scouting runs 1–2, held-out 3–7) and `validation/Validation_2/` (four-peak sample: scouting 1–2, held-out 3–6, E1, the E4 triplicate) on main; pre-registered run sheets under `validation/run-sheets/`; the bench sheet the v0.2 runs were made from: https://claude.ai/code/artifact/ea08d1b3-79d5-4b7e-82a0-664a7c9d7eec
- Decision record: [wayfinder map #1](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/1) and its ten closed tickets; [map #28](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/28) (resolution map, parked, four decisions preserved); [map #41](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/41) (gradient freedom, v0.2 — its closed tickets hold the decision detail behind every v0.2 paragraph above)
