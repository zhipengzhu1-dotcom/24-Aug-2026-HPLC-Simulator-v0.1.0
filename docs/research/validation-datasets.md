# Validation datasets for the two-run gradient fit engine

Research output for issue #3. Purpose: give the v0.1 engine (two linear-gradient
scouting runs → fit LSS parameters → predict retention at a third condition)
a set of published, numerically complete worked examples that can be turned
into unit tests **without re-fetching anything**. Every number an engine test
needs is transcribed below.

Status: **three fully-numeric examples secured** (two independent measured
datasets + one exact reference-implementation round-trip), plus one partial
example kept for its acceptance-tolerance value.

## Summary

| # | Source | Access | Input runs | Third condition | Complete? |
|---|---|---|---|---|---|
| 1 | den Uijl et al. 2021, Set X | CC BY, supplement | 8 gradient times × 23 compounds × 10 replicates | measured tR at any other tG | **Yes** |
| 2 | den Uijl et al. 2021, Set Y | CC BY, supplement | 10 gradient times × 19 compounds × 10 replicates | measured tR at any other tG | **Yes** |
| 3 | Guillarme et al. 2022, supplementary Excel | CC BY, supplement | 3 gradient times × 4 compounds | predicted tR + fitted S/log k0 | **Yes** (exact reference values) |
| 4 | Kormány et al. 2021 (DryLab, apixaban) | CC BY | not published | predicted vs measured tR, 9 compounds × 7 conditions | Partial — input tR and t0 missing |

Examples 1 and 2 test the engine against **measured** reality (does the physics
come out right?). Example 3 tests the **arithmetic** against a published
reference implementation to machine precision (is the equation implemented
right?). Both kinds of test are worth having; example 3 is the one to write
first, because it fails loudly and unambiguously.

## Model and conventions used throughout

All derived numbers in this document use the Snyder linear-solvent-strength
(LSS) gradient equation with dwell time and an optional pre-gradient isocratic
hold. Retention factor vs. organic fraction φ:

```
log k(φ) = log k_w − S·φ
```

Gradient retention time, for a linear ramp φ0 → φf over tG:

```
Δφ    = φf − φ0
b     = t0 · Δφ · S / tG          (gradient steepness)
k_i   = k_w · 10^(−S·φ0)          (retention factor at the initial composition)
delay = tD + t_init               (dwell time + pre-gradient isocratic hold)
tR    = t0 + delay + (tG / (S·Δφ)) · log10( 2.303·b·(k_i − delay/t0) + 1 )
```

This inverts in closed form, which is what makes an exact two-run fit cheap —
no 2-D optimiser is required:

```
G    = 10^( (tR − t0 − delay)·S·Δφ / tG )
k_i  = (G − 1) / (2.303·b) + delay/t0
```

Given two runs, solve the scalar equation `k_i(run1, S) = k_i(run2, S)` for `S`
by bisection over S (a bracket of roughly 0.05–200 covers everything in these
datasets), then back out `k_i` and `k_w`. This is the procedure used to produce
every "derived" table below.

Note the `2.303·b·(k_i − delay/t0) + 1` form: it carries both the `+1` term and
the dwell-volume correction. It is the exact form used by the Guillarme/Heinisch
reference spreadsheet (example 3), and reproducing that spreadsheet's outputs to
~1e-15 confirms the transcription.

---

## Example 1 — den Uijl et al. 2021, Set X

The strongest dataset available openly: a systematic scanning-gradient study
published under CC BY with the **complete raw peak tables** (every replicate of
every compound at every gradient time) in the supplementary material.

**Citation.** M. J. den Uijl, P. J. Schoenmakers, G. K. Schulte, D. R. Stoll,
M. R. van Bommel, B. W. J. Pirok, "Measuring and using scanning-gradient data
for use in method optimization for liquid chromatography", *Journal of
Chromatography A* **1636** (2021) 461780. DOI
[10.1016/j.chroma.2020.461780](https://doi.org/10.1016/j.chroma.2020.461780).
Open access, CC BY 4.0.

**Numbers come from.** Supplementary material, Section S-2, Tables S-3 to S-10
(`https://ars.els-cdn.com/content/image/1-s2.0-S0021967320310542-mmc1.docx`);
conditions from Sections 2.2–2.3 and 3.1.1 of the article.

### 1.1 Conditions (Set X)

| Parameter | Value |
|---|---|
| Instrument | Agilent 1290 Infinity 2D-LC, configured for 1D operation |
| Column | Phenomenex Kinetex C18, 50 × 2.1 mm, 1.7 µm, 100 Å |
| Flow rate | 0.5 mL/min |
| Column dead time t0 | **0.262 min** (sd 0.0027 min), V0 = 131 µL, from uracil |
| Dwell volume Vd | **0.128 mL** → tD = 0.256 min at 0.5 mL/min |
| Mobile phase A | buffer/ACN 95:5 v/v → **φ_ACN = 0.05** |
| Mobile phase B | ACN/buffer 95:5 v/v → **φ_ACN = 0.95** |
| Buffer | 5 mM ammonium formate, pH 3.0 |
| Gradient program | 0 → 0.25 min isocratic 100% A; then linear to 100% B over tG |
| Pre-gradient hold t_init | **0.25 min** |
| Δφ | **0.90** (0.05 → 0.95 ACN) |
| Gradient times tG | 1.5, 3, 3.75, 4.5, 6, 7.5, 9, 12 min |
| Injection volume | 5 µL |
| Detection | DAD, 160 Hz, 10 mm Max-Light cell, V_det = 1.0 µL |
| Column temperature | **not stated in the paper** (see Gaps) |
| Replicates | 10 per gradient, recorded over several days, multiple buffer batches |

The `%B` in the gradient program is *not* the organic fraction: 100% A is 5%
ACN and 100% B is 95% ACN. An engine fed "5 → 95%" is correct; one fed
"0 → 100%" is not.

### 1.2 Measured retention times (mean of 10 replicates, min)

| Compound | tG=1.5 | tG=3 | tG=3.75 | tG=4.5 | tG=6 | tG=7.5 | tG=9 | tG=12 |
|---|---|---|---|---|---|---|---|---|
| Indigotin | 1.657 | 2.379 | 2.705 | 3.018 | 3.610 | 4.169 | 4.706 | 5.724 |
| Purpurin | 1.646 | 2.360 | 2.683 | 2.992 | 3.577 | 4.130 | 4.659 | 5.666 |
| Emodin | 1.764 | 2.590 | 2.967 | 3.329 | 4.019 | 4.673 | 5.307 | 6.515 |
| Toluene | 1.714 | 2.443 | 2.764 | 3.066 | 3.627 | 4.140 | 4.628 | 5.517 |
| Propylparaben | 1.515 | 2.109 | 2.374 | 2.625 | 3.098 | 3.538 | 3.954 | 4.740 |
| Uracil | 0.260 | 0.262 | 0.262 | 0.262 | 0.263 | 0.263 | 0.261 | 0.263 |
| Sudan I | 2.085 | 3.181 | 3.687 | 4.171 | 5.101 | 5.986 | 6.839 | 8.474 |
| Rutin | 1.083 | 1.357 | 1.483 | 1.602 | 1.829 | 2.039 | 2.243 | 2.627 |
| Martius Yellow | 1.453 | 2.017 | 2.272 | 2.514 | 2.975 | 3.406 | 3.817 | 4.589 |
| Naphthol Yellow S | 1.083 | 1.324 | 1.429 | 1.525 | 1.700 | 1.862 | 2.005 | 2.263 |
| Orange IV | 1.407 | 1.978 | 2.243 | 2.498 | 2.988 | 3.459 | 3.914 | 4.787 |
| Flavazine L | 1.386 | 1.927 | 2.178 | 2.419 | 2.882 | 3.326 | 3.751 | 4.569 |
| Picric Acid | 1.276 | 1.655 | 1.818 | 1.965 | 2.240 | 2.486 | 2.709 | 3.102 |
| Fast Red B | 1.217 | 1.621 | 1.807 | 1.983 | 2.332 | 2.666 | 2.977 | 3.570 |
| Tyramine | 0.366 | 0.366 | 0.369 | 0.369 | 0.367 | 0.367 | 0.366 | 0.367 |
| Cytosine | 0.214 | 0.215 | 0.218 | 0.217 | 0.217 | 0.216 | 0.217 | 0.218 |
| Trimethoprim | 1.027 | 1.206 | 1.279 | 1.347 | 1.472 | 1.575 | 1.673 | 1.845 |
| Propranolol | 1.237 | 1.635 | 1.812 | 1.982 | 2.303 | 2.599 | 2.886 | 3.420 |
| Peptide 1 | 0.372 | 0.371 | 0.372 | 0.372 | 0.371 | 0.372 | 0.373 | 0.371 |
| Peptide 2 | 0.988 | 1.137 | 1.198 | 1.252 | 1.353 | 1.442 | 1.526 | 1.673 |
| Peptide 3 | 1.040 | 1.290 | 1.408 | 1.521* | 1.735 | 1.936 | 2.130 | 2.514 |
| Peptide 4 | 1.081 | 1.343 | 1.460 | 1.569 | 1.774 | 1.968 | 2.155 | 2.514 |
| Peptide 5 | 1.122 | 1.436 | 1.577 | 1.711 | 1.965 | 2.203 | 2.428 | 2.859 |

\* **Data-quality correction.** In the published Table S-6 (tG = 4.5 min),
Peptide 3 replicate 7 is `2.523` while the other nine replicates are
1.520–1.522 — an obvious mis-integration in the supplement. The value above is
the mean of the other nine (1.5207). Using the published 10-replicate mean
(1.621) will make a correct engine look wrong by ~7%. This is the **only**
outlier in either dataset: a scan of all 18 peak tables for replicates
deviating >5% from their row median found exactly this one cell.

**Do not use for LSS tests:** Uracil, Cytosine, Tyramine and Peptide 1 elute at
or near t0 at every gradient time (their tR is flat across tG). They carry no
gradient information and the LSS fit is undefined for them. They *are* useful
as a negative test: the engine must never return them as a *confident* fit.

**Amended 2026-08-27 (ticket #16).** An earlier version of this paragraph said
the engine "should refuse to fit them". That overstates what SPEC permits, and
the fixtures now prove it: six of the eight cases (both sets' Uracil and
Cytosine, Set X's Tyramine and Peptide 1) do refuse, because the band leaves the
column before the gradient reaches it and the two runs are the same isocratic
measurement. But Set Y's Tyramine and Peptide 1 elute *after* t0 + τ and do move
with tG (0.3320 → 0.3456 min), so an LSS solution genuinely exists and is merely
badly conditioned. CLAUDE.md's warnings-over-blocks rule reserves hard failure
for impossibilities, so those two fit and return low-confidence with
log10 k0 ≈ −0.25 (k0 < 1). See `tests/test_reality.py`.

Replicate precision (sd of the 10 replicates) ranges from 0.0005 min for the
best-behaved peaks to 0.053 min for Fast Red B at tG = 12; the charged dyes
(Martius Yellow, Naphthol Yellow S, Picric Acid, Fast Red B) are the noisy
ones, which the paper attributes to buffer-concentration and pH sensitivity
across the multi-day acquisition.

### 1.3 Reference fit-and-predict (derived)

Fit on tG = 3 and 9 min (gradient-slope factor Γ = 3, the paper's recommended
benchmark pair), predict tG = 4.5 and 7.5 min, compare with the measured means
above. **The S / log k values below are derived here, not published** — they
are provided so a test can assert on intermediate state, but the authoritative
assertion is predicted-vs-measured tR.

| Compound | S | log k_i | log k_w | pred 4.5 | meas 4.5 | err % | pred 7.5 | meas 7.5 | err % |
|---|---|---|---|---|---|---|---|---|---|
| Indigotin | 5.30 | 2.581 | 2.846 | 3.019 | 3.019 | −0.00 | 4.173 | 4.168 | +0.13 |
| Purpurin | 5.35 | 2.570 | 2.838 | 2.993 | 2.993 | −0.01 | 4.132 | 4.128 | +0.10 |
| Emodin | 5.12 | 2.832 | 3.088 | 3.330 | 3.330 | +0.00 | 4.678 | 4.672 | +0.13 |
| Toluene | 4.02 | 2.160 | 2.361 | 3.065 | 3.068 | −0.10 | 4.145 | 4.138 | +0.16 |
| Propylparaben | 5.68 | 2.273 | 2.556 | 2.624 | 2.624 | −0.00 | 3.539 | 3.538 | +0.01 |
| Sudan I | 4.08 | 3.082 | 3.286 | 4.170 | 4.170 | +0.01 | 5.986 | 5.983 | +0.04 |
| Rutin | 16.27 | 2.409 | 3.222 | 1.597 | 1.603 | −0.31 | 2.037 | 2.038 | −0.07 |
| Martius Yellow | 6.84 | 2.463 | 2.805 | 2.508 | 2.511 | −0.12 | 3.399 | 3.400 | −0.04 |
| Naphthol Yellow S | 10.74 | 1.530 | 2.067 | 1.525 | 1.528 | −0.20 | 1.863 | 1.869 | −0.32 |
| Orange IV | 9.86 | 3.329 | 3.822 | 2.494 | 2.498 | −0.17 | 3.457 | 3.460 | −0.09 |
| Flavazine L | 9.64 | 3.112 | 3.594 | 2.416 | 2.420 | −0.17 | 3.323 | 3.327 | −0.12 |
| Picric Acid | 6.43 | 1.649 | 1.970 | 1.959 | 1.960 | −0.05 | 2.476 | 2.478 | −0.04 |
| Fast Red B | 13.72 | 3.133 | 3.820 | 1.989 | 1.983 | +0.32 | 2.669 | 2.661 | +0.30 |
| Trimethoprim | 11.01 | 1.188 | 1.738 | 1.348 | 1.347 | +0.06 | 1.578 | 1.577 | +0.08 |
| Propranolol | 9.81 | 2.306 | 2.797 | 1.980 | 1.981 | −0.06 | 2.600 | 2.601 | −0.05 |
| Peptide 2 | 12.67 | 1.099 | 1.733 | 1.256 | 1.252 | +0.33 | 1.446 | 1.443 | +0.24 |
| Peptide 3 | 23.44 | 3.043 | 4.215 | 1.513 | 1.521 | −0.50 | 1.932 | 1.936 | −0.23 |
| Peptide 4 | 14.02 | 2.020 | 2.721 | 1.568 | 1.569 | −0.06 | 1.970 | 1.968 | +0.12 |
| Peptide 5 | 13.83 | 2.375 | 3.067 | 1.706 | 1.711 | −0.27 | 2.199 | 2.202 | −0.17 |

**Aggregate: median |error| 0.11%, mean 0.14%, max 0.50% over 38 predictions.**

This matches the paper's own reported result for Set X ("the predicted
retention times deviate mostly less than 0.5% from the measured retention
times", Section 3.2.1, Fig. 3), which is good evidence that the conditions
above are transcribed correctly.

### 1.4 What this dataset catches

The pre-gradient isocratic hold is load-bearing. Re-running the same fit with
`t_init = 0` (dwell only) degrades the result by roughly an order of magnitude:

| Handling of the 0.25 min hold | median \|err\| | max \|err\| | mean signed error |
|---|---|---|---|
| Included (correct) | 0.11% | 0.50% | −0.03% |
| Ignored | 1.04% | 1.92% | +1.09% |

The signature of getting it wrong is a **systematic positive bias**, not
scatter. A regression test asserting `mean signed error < 0.2%` on Set X will
catch a dropped `t_init` or `tD` term; a test asserting only per-peak tolerance
of ±2% will not.

---

## Example 2 — den Uijl et al. 2021, Set Y

Same paper, independent dataset: different instrument, column, flow rate and
buffer, and deliberately acquired for maximum precision (single buffer batch,
three days, controlled re-equilibration). The paper describes Set Y as the
higher-precision set and Set X as "representative for common practice", so the
two make a natural pair of tests: one strict, one realistic.

### 2.1 Conditions (Set Y)

| Parameter | Value |
|---|---|
| Instrument | Agilent modules with a 2D-LC valve used for 1D operation |
| Column | Agilent Zorbax SB C18, 50 × 4.6 mm, 5 µm, 80 Å |
| Flow rate | 2.5 mL/min |
| Column dead time t0 | **0.171 min** (sd 0.0005 min), V0 = 428 µL, measured in 50/50 ACN/buffer |
| Uracil tR (measured, in-gradient) | **0.229 min** — see the t0 note below |
| Dwell volume Vd | **0.081 mL** → tD = 0.0324 min at 2.5 mL/min |
| Mobile phase A | 25 mM ammonium formate buffer, pH 3.2 |
| Mobile phase B | ACN |
| Gradient program | 5% B at 0 min, linear to 85% B over tG; no initial hold |
| Pre-gradient hold t_init | **0** |
| Δφ | **0.80** (0.05 → 0.85 ACN) |
| Gradient times tG | 1, 1.5, 3, 3.75, 4.5, 6, 7.5, 9, 12, 18 min |
| Injection | fixed internal loops, ≈150 nL |
| Detection | DAD, 80 Hz, 10 mm Max-Light cell, V_det = 1.0 µL |
| Column temperature | **not stated in the paper** |
| Replicates | 10 per gradient, single buffer batch, over three days |

**t0 convention — this matters.** The paper's stated column dead time
(0.171 min) and the measured retention of the unretained marker uracil in the
gradient runs (0.229 min) disagree by 0.058 min; the difference is
extra-column volume (≈145 µL at 2.5 mL/min — the system carried a 2D-LC
valve). Which one you feed the engine changes the answer measurably:

| t0 convention | median \|err\| | max \|err\| | mean signed error |
|---|---|---|---|
| t0 = 0.171 min (column only, no extra-column term) | 0.39% | 0.89% | **+0.41%** |
| t0 = 0.229 min (uracil tR, extra-column lumped in) | 0.16% | 0.54% | +0.04% |
| t0 = 0.171 min + 0.058 min extra-column offset | 0.16% | 0.54% | +0.04% |

The last two are numerically identical, as they should be. **Use the uracil
value (0.229 min)**, or model extra-column time explicitly. Using the bare
column dead time leaves a systematic +0.4% bias — the same failure signature as
the dropped hold in Set X, and a good argument for the engine taking t0 as a
measured marker time rather than computing it from column geometry.

For Set X the question does not arise: the stated t0 (0.262 min) and the
measured uracil tR (0.260–0.263 min) already agree, i.e. extra-column time is
already folded into the published V0.

### 2.2 Measured retention times (mean of 10 replicates, min)

Set Y peak tables list 19 compounds (Set X's 23 minus the four Set-X-only
components, plus berberine). Values at 4 decimals as published.

| Compound | tG=1 | tG=1.5 | tG=3 | tG=3.75 | tG=4.5 | tG=6 | tG=7.5 | tG=9 | tG=12 | tG=18 |
|---|---|---|---|---|---|---|---|---|---|---|
| Uracil | 0.2299 | 0.2299 | 0.2294 | 0.2289 | 0.2289 | 0.2292 | 0.2289 | 0.2290 | 0.2288 | 0.2286 |
| Tyramine | 0.3083 | 0.3182 | 0.3320 | 0.3358 | 0.3379 | 0.3418 | 0.3440 | 0.3456 | 0.3482 | 0.3498 |
| Flavazine L | 0.3600 | 0.4010 | 0.5005 | 0.5410 | 0.5764 | 0.6398 | 0.6924 | 0.7385 | 0.8149 | 0.9301 |
| Trimethoprim | 0.4937 | 0.5833 | 0.7951 | 0.8830 | 0.9627 | 1.1053 | 1.2315 | 1.3439 | 1.5424 | 1.8622 |
| Propranolol | 0.7137 | 0.8964 | 1.3707 | 1.5838 | 1.7862 | 2.1669 | 2.5232 | 2.8600 | 3.4915 | 4.6295 |
| Berberine | 0.7952 | 0.9962 | 1.5122 | 1.7424 | 1.9609 | 2.3714 | 2.7552 | 3.1193 | 3.8033 | 5.0433 |
| Propylparaben | 0.8573 | 1.0992 | 1.7212 | 1.9976 | 2.2592 | 2.7486 | 3.2038 | 3.6331 | 4.4333 | 5.8643 |
| Toluene | 1.0375 | 1.3435 | 2.1245 | 2.4679 | 2.7904 | 3.3873 | 3.9349 | 4.4451 | 5.3750 | 6.9835 |
| Sudan I | 1.3316 | 1.7426 | 2.9242 | 3.4709 | 3.9969 | 5.0040 | 5.9643 | 6.8906 | 8.6662 | 11.9944 |
| Cytosine | 0.1899 | 0.1896 | 0.1891 | 0.1890 | 0.1891 | 0.1893 | 0.1891 | 0.1890 | 0.1890 | 0.1883 |
| Naphthol Yellow S | 0.3595 | 0.4002 | 0.4994 | 0.5393 | 0.5754 | 0.6379 | 0.6904 | 0.7359 | 0.8126 | 0.9267 |
| Rutin | 0.4860 | 0.5897 | 0.8585 | 0.9796 | 1.0938 | 1.3092 | 1.5112 | 1.6997 | 2.0541 | 2.6883 |
| Martius Yellow | 0.7238 | 0.9283 | 1.4611 | 1.7010 | 1.9285 | 2.3560 | 2.7556 | 3.1321 | 3.8358 | 5.0942 |
| Orange IV | 0.7293 | 0.9475 | 1.5410 | 1.8155 | 2.0801 | 2.5883 | 3.0737 | 3.5403 | 4.4351 | 6.1069 |
| Purpurin | 0.9506 | 1.2325 | 1.9722 | 2.3072 | 2.6267 | 3.2315 | 3.8006 | 4.3418 | 5.3658 | 7.2431 |
| Emodin | 1.0399 | 1.3643 | 2.2292 | 2.6254 | 3.0059 | 3.7300 | 4.4176 | 5.0763 | 6.3327 | 8.6647 |
| Peptide 1 | 0.3065 | 0.3160 | 0.3319 | 0.3356 | 0.3389 | 0.3427 | 0.3465 | 0.3474 | 0.3523 | 0.3529 |
| Peptide 2 | 0.4500 | 0.5257 | 0.7080 | 0.7835 | 0.8532 | 0.9765 | 1.0861 | 1.1839 | 1.3608 | 1.6319 |
| Peptide 5 | 0.5740 | 0.7142 | 1.0830 | 1.2491 | 1.4082 | 1.7074 | 1.9895 | 2.2584 | 2.7686 | 3.6808 |

Cytosine's tR (0.189 min) sits *below* uracil's (0.229 min) — it is excluded on
the same grounds as in Set X, along with Uracil, Tyramine and Peptide 1.

### 2.3 Reference fit-and-predict (derived)

Fit on tG = 3 and 9 min, predict tG = 4.5 and 7.5 min, **t0 = 0.229 min**
(uracil convention), tD = 0.0324 min, t_init = 0, Δφ = 0.80, φ0 = 0.05.

| Compound | S | log k_i | log k_w | pred 4.5 | meas 4.5 | err % | pred 7.5 | meas 7.5 | err % |
|---|---|---|---|---|---|---|---|---|---|
| Flavazine L | 20.41 | 0.830 | 1.851 | 0.5745 | 0.5765 | −0.34 | 0.6908 | 0.6923 | −0.22 |
| Trimethoprim | 9.56 | 1.217 | 1.695 | 0.9638 | 0.9627 | +0.12 | 1.2324 | 1.2315 | +0.07 |
| Propranolol | 7.27 | 2.138 | 2.501 | 1.7901 | 1.7862 | +0.22 | 2.5271 | 2.5231 | +0.16 |
| Berberine | 5.88 | 2.041 | 2.335 | 1.9714 | 1.9609 | +0.54 | 2.7654 | 2.7553 | +0.36 |
| Propylparaben | 5.24 | 2.168 | 2.430 | 2.2642 | 2.2591 | +0.23 | 3.2094 | 3.2039 | +0.17 |
| Toluene | 3.72 | 2.124 | 2.310 | 2.7945 | 2.7904 | +0.15 | 3.9396 | 3.9348 | +0.12 |
| Sudan I | 3.94 | 3.052 | 3.249 | 4.0045 | 3.9973 | +0.18 | 5.9734 | 5.9642 | +0.15 |
| Naphthol Yellow S | 20.44 | 0.826 | 1.848 | 0.5731 | 0.5754 | −0.40 | 0.6886 | 0.6905 | −0.27 |
| Rutin | 15.11 | 2.077 | 2.832 | 1.0916 | 1.0939 | −0.21 | 1.5085 | 1.5112 | −0.18 |
| Martius Yellow | 7.31 | 2.325 | 2.690 | 1.9262 | 1.9285 | −0.12 | 2.7540 | 2.7555 | −0.06 |
| Orange IV | 9.58 | 3.140 | 3.619 | 2.0776 | 2.0802 | −0.13 | 3.0715 | 3.0739 | −0.08 |
| Purpurin | 5.06 | 2.453 | 2.706 | 2.6329 | 2.6266 | +0.24 | 3.8067 | 3.8006 | +0.16 |
| Emodin | 4.91 | 2.736 | 2.981 | 3.0120 | 3.0057 | +0.21 | 4.4242 | 4.4175 | +0.15 |
| Peptide 2 | 12.01 | 1.191 | 1.791 | 0.8527 | 0.8531 | −0.04 | 1.0859 | 1.0860 | −0.01 |
| Peptide 5 | 11.40 | 2.292 | 2.863 | 1.4073 | 1.4082 | −0.06 | 1.9900 | 1.9895 | +0.02 |

**Aggregate: median |error| 0.16%, mean 0.18%, max 0.54% over 30 predictions.**

### 2.4 Other test material in this paper

Because the supplement publishes all ten gradient times for both sets, this one
source also supports:

- **Interpolation vs. extrapolation.** Fit on 3 & 9, predict 1.5 (Set X) or 1
  and 18 (Set Y). The paper reports extrapolation errors up to ~4% toward
  slower gradients (Fig. 11) and notes retention in slow gradients is almost
  always *overestimated* — a directional property the engine should reproduce
  rather than a tolerance to widen.
- **Gradient-slope factor (Γ) sensitivity.** Pairs with Γ = 0.33 … 6 are all
  available. The paper's conclusion (Section 3.2.4, Fig. 9) is that proximity
  of the scouting slopes to the target slope matters *more* than the
  conventional "Γ ≥ 3" rule — worth encoding as a warning heuristic, not a
  hard constraint.
- **Replicate/precision behaviour.** 10 replicates per point support tests of
  how the fit degrades with noisy input.

---

## Example 3 — Guillarme et al. 2022 reference spreadsheet (exact round-trip)

This is the highest-value **unit** test: a published, freely distributed
reference implementation shipped pre-populated with a complete worked example,
including the fitted intermediates. Every number below was verified by
re-implementing the spreadsheet's formulas independently — agreement was to
~1e-15 (floating-point exact) on every output.

**Citation.** D. Guillarme, T. Bouvarel, F. Rouvière, S. Heinisch, "A simple
mathematical treatment for predicting linear solvent strength behavior in
gradient elution: Application to biomolecules", *Journal of Separation Science*
**45** (2022) 3276–3285. DOI
[10.1002/jssc.202200161](https://doi.org/10.1002/jssc.202200161). Open access,
CC BY. PMC: [PMC9543774](https://europepmc.org/article/MED/PMC9543774).

**Numbers come from.** Supporting information file `JSSC-45-3276-s001.XLSX`
(sheet "LSS parameters"), retrievable from
`https://www.ebi.ac.uk/europepmc/webservices/rest/PMC9543774/supplementaryFiles`.
Gradient design for the paper's compound sets is in `…-s002.docx`, Table S1.

### 3.1 Inputs

| Parameter | Value |
|---|---|
| Column length | 50 mm |
| Column diameter | 2.1 mm |
| Porosity ε | 0.62 |
| Flow rate | 0.5 mL/min |
| Dwell volume | 0.10 mL |
| φ initial | 0.05 |
| φ final | 0.95 |
| Gradient times | 5, 10, 15 min |

Derived by the spreadsheet, and both worth asserting directly:

```
t0 = (π · d² / 4 · L · ε) / (F · 1000) = 0.2147435658361303 min
tD = Vd / F                            = 0.2 min
```

Input retention times (min):

| Run | tG | compound 1 | compound 2 | compound 3 | compound 4 |
|---|---|---|---|---|---|
| 1 | 5 | 3.148 | 1.183 | 1.587 | 2.106 |
| 2 | 10 | 5.227 | 1.726 | 2.566 | 3.662 |
| 3 | 15 | 7.111 | 2.184 | 3.462 | 5.163 |

### 3.2 Expected fitted parameters

Full stored precision, for exact assertions:

| Compound | S | log k_w (water) | log k_i (at φ = 0.05) |
|---|---|---|---|
| compound 1 | 5.2693573156076159 | 3.1827480684914691 | 2.9192802027110885 |
| compound 2 | 14.849290820729498 | 2.6752867802368332 | 1.9328222392003582 |
| compound 3 | 16.975901726974396 | 4.2536161338301399 | 3.4048210474814202 |
| compound 4 | 24.461155384269425 | 8.3331553323974532 | 7.1100975631839818 |

Intermediates, if the engine exposes them (elution composition per run):

| Compound | Ce run 1 | Ce run 2 | Ce run 3 |
|---|---|---|---|
| compound 1 | 0.5419861581494966 | 0.4831030790747483 | 0.4517753860498321 |
| compound 2 | 0.1882861581494966 | 0.1680130790747483 | 0.1561553860498322 |
| compound 3 | 0.2610061581494966 | 0.2436130790747482 | 0.2328353860498322 |
| compound 4 | 0.3544261581494965 | 0.3422530790747482 | 0.3348953860498322 |

The spreadsheet's fit is a **linear regression of Ce against log β**, not an
exact two-run solve:

```
ramp_j     = Δφ / tG_j · 100                     → 18, 9, 6 (%B/min)
Ce_j       = φ0 + (ramp_j/100)·(tR_j − t0 − tD)
log β_j    = log10( ramp_j · t0 / 100 )          → −1.4128073345644301,
                                                   −1.7138373302284113,
                                                   −1.8899285892840927
a, c       = slope, intercept of Ce_j vs log β_j
S          = 1/a
log k_w    = S·c − log10(2.3·S)
log k_i    = log k_w − S·φ0
```

An engine using an exact two-run solve will land close to but not exactly on
these S values (the regression is an approximation valid when k_i is large).
Assert exactly against these numbers **only** when testing this specific
estimator; otherwise use them as a ±few-percent cross-check on S.

### 3.3 Expected prediction at the third condition

Prediction condition: **φ 0.05 → 0.80, tG = 2 min** (same column, flow, dwell).
Note this is a change of *both* gradient range and gradient time, which
exercises more of the engine than a tG-only change.

| Compound | predicted tR (min) | elution composition Ce | steepness b |
|---|---|---|---|
| compound 1 | 1.8870705193957040 | 0.6021226075848403 | 0.4243352173568546 |
| compound 2 | 0.8403321289690734 | 0.2095957111748537 | 1.1957961228679388 |
| compound 3 | 1.0278156533983409 | 0.2799020328358290 | 1.3670496263003267 |
| compound 4 | 1.2614541701542286 | 0.3675164766192868 | 1.9698283993836279 |

**The spreadsheet hard-codes 2.303 where ln 10 belongs.** Verified while building
the two-run fit (#15): reproducing the predicted tR above to ~1e-16 requires using
the literal `2.303`, and substituting the exact `ln 10` moves them by 0.9–4.0e-5 min.
So a *correct* engine cannot match this table to 1e-6, and must not be made to — the
gap is the reference's rounding, not the engine's error. The fitted intermediates
(S, log k_w, log k_i, Ce) carry no such rounding and remain exact-assertion material;
that is what `tests/test_fit.py` asserts against.

The exact prediction formula (spreadsheet cell `C29`, generalised):

```
b   = t0 · Δφ · S / tG
k_i = 10^(log k_w − S·φ0)
tR  = t0 + tD + tG/(S·Δφ) · log10( 2.303 · k_i · b · (1 − tD/(t0·k_i)) + 1 )
```

### 3.4 Self-consistency check

Feeding the fitted parameters back through the prediction formula at the three
*input* gradient times reproduces the measured input retention times to within
0.4%, confirming the input data are real measurements consistent with the LSS
model:

| Compound | tG=5 calc/meas | tG=10 calc/meas | tG=15 calc/meas |
|---|---|---|---|
| compound 1 | 3.147 / 3.148 (−0.04%) | 5.246 / 5.227 (+0.37%) | 7.108 / 7.111 (−0.04%) |
| compound 2 | 1.183 / 1.183 (−0.01%) | 1.729 / 1.726 (+0.15%) | 2.192 / 2.184 (+0.37%) |
| compound 3 | 1.588 / 1.587 (+0.04%) | 2.564 / 2.566 (−0.09%) | 3.465 / 3.462 (+0.10%) |
| compound 4 | 2.106 / 2.106 (+0.02%) | 3.661 / 3.662 (−0.02%) | 5.164 / 5.163 (+0.03%) |

The compounds are unnamed in the spreadsheet. From Table S1 of the supplement
the 5/10/15 min gradient series with φ 0.05→0.95 corresponds to the
small-molecule set (ibuprofen, the parabens) on an Acquity CSH C18 50 × 2.1 mm
1.7 µm at 30 °C, 0.5 mL/min — consistent with the conditions above, but the
mapping of "compound 1–4" to specific analytes is not stated, so treat them as
anonymous.

---

## Example 4 — Kormány et al. 2021, apixaban (partial)

A genuine DryLab modelling paper, open access, with a predicted-vs-measured
table across seven conditions. **Not usable as a two-run fit test** because the
input scouting-run retention times are not published — but valuable as evidence
for what accuracy commercial software achieves, i.e. for setting the engine's
acceptance tolerance.

**Citation.** R. Kormány, N. Rácz, S. Fekete, K. Horváth, "Development of a
Fast and Robust UHPLC Method for Apixaban In-Process Control Analysis",
*Molecules* **26** (2021) 3505. DOI
[10.3390/molecules26123505](https://doi.org/10.3390/molecules26123505).
Open access, CC BY. PMC:
[PMC8226502](https://europepmc.org/article/MED/PMC8226502).

### 4.1 Conditions

| Parameter | Value |
|---|---|
| Instrument | Waters Acquity UPLC, 5 µL loop, 500 nL flow cell |
| Column | Acquity BEH C18, 50 × 2.1 mm, 1.7 µm |
| **Dwell volume** | **0.12 mL** |
| Mobile phase | ACN / 5 mM citrate buffer (10 mM citrate stated in Results; 5 mM in Materials — the paper is internally inconsistent here) |
| Flow rate | 0.8 mL/min (nominal) |
| Detection | 280 nm |
| Injection | 1 µL, 10 µg/mL per component |
| Modelling software | DryLab v.4.3.1 + Robustness Module |
| Input design | tG1 = 1.5 min, tG2 = 4.5 min, 10%B → 80%B; T 20/50/80 °C; pH 2.8/4.0/4.6/5.2/6.4 (12-run design) |
| Operating point (OP) | tG = 3.0 min, 10%B → 80%B, T = 40 °C, pH 6.0 |
| Column dead time t0 | **not reported** |

### 4.2 Predicted vs. experimental retention times (min) — Table 2

OP is the operating point; 637/396/390/638/611/584 are six virtual-robustness
scenarios re-run experimentally. The exact tG/T/pH/flow/%B for the six numbered
scenarios are given only in the paper's Figure 5, so **only the OP column is
usable numerically**; robustness levels were tG 2.7/3.0/3.3 min, T 38/40/42 °C,
pH 5.8/6.0/6.2, flow 0.72/0.80/0.88 mL/min, %B initial 9/10/11, %B final
79/80/81.

| Compound | OP pred | OP exp | 637 pred | 637 exp | 396 pred | 396 exp | 390 pred | 390 exp | 638 pred | 638 exp | 611 pred | 611 exp | 584 pred | 584 exp |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Int6 | 0.88 | 0.89 | 0.83 | 0.83 | 0.93 | 0.94 | 0.89 | 0.89 | 0.82 | 0.83 | 0.82 | 0.83 | 0.82 | 0.82 |
| Stm1 | 1.13 | 1.13 | 1.05 | 1.04 | 1.16 | 1.16 | 1.12 | 1.12 | 1.04 | 1.03 | 1.04 | 1.04 | 1.04 | 1.03 |
| Apixaban | 1.32 | 1.32 | 1.22 | 1.21 | 1.40 | 1.40 | 1.36 | 1.36 | 1.21 | 1.22 | 1.21 | 1.22 | 1.21 | 1.21 |
| Int2 | 1.43 | 1.44 | 1.31 | 1.31 | 1.48 | 1.46 | 1.44 | 1.42 | 1.30 | 1.30 | 1.30 | 1.32 | 1.30 | 1.31 |
| Int1 | 1.69 | 1.69 | 1.54 | 1.55 | 1.76* | 1.75 | 1.72 | 1.72 | 1.53 | 1.53 | 1.53 | 1.53 | 1.53 | 1.53 |
| Int5 | 1.85 | 1.85 | 1.69 | 1.67 | 1.96 | 1.98 | 1.93 | 1.94 | 1.67 | 1.68 | 1.67 | 1.68 | 1.67 | 1.67 |
| Stm2 | 1.96 | 1.96 | 1.78 | 1.77 | 2.06 | 2.05 | 2.03 | 2.05 | 1.77 | 1.79 | 1.77 | 1.78 | 1.77 | 1.78 |
| Int4 | 2.16 | 2.16 | 1.96 | 1.95 | 2.30 | 2.30 | 2.28 | 2.29 | 1.94 | 1.95 | 1.94 | 1.94 | 1.94 | 1.95 |
| Int3 | 2.22 | 2.22 | 2.01 | 1.98 | 2.35 | 2.37 | 2.33 | 2.34 | 1.99 | 2.00 | 1.99 | 1.99 | 1.99 | 1.99 |
| R_S,crit (Int4–Int3) | 2.40 | 2.37 | 2.27 | 2.24 | 2.27 | 2.25 | 2.27 | 2.24 | 2.27 | 2.23 | 2.27 | 2.23 | 2.27 | 2.23 |

\* Published as `1,76` (comma) in the source table — a typo for 1.76.

**Useful conclusion:** across 63 predicted/experimental pairs the largest
disagreement is 0.02 min and most are 0.00–0.01 min, on retention times of
0.8–2.4 min — i.e. commercial practice lands within roughly **±1%**, and
usually much better. That is a reasonable acceptance bar for v0.1 on
interpolated conditions, and it is consistent with the ~0.1–0.2% median seen on
den Uijl's data above.

---

## Gaps and fallbacks

### What could not be secured

- **Snyder & Dolan, *High-Performance Gradient Elution* (2007).** The canonical
  source of worked two-run examples. **Paywalled**, no open chapter found. The
  book's worked tables (LSS parameter estimation from two gradient runs and
  prediction of tR under altered conditions) would be ideal but the numbers
  could not be transcribed. Cited below for the record. Its underlying model is
  the same LSS equation used throughout this document, so examples 1–3 cover
  the same ground.
- **Boswell et al. 2011 (both *J. Chromatogr. A* papers).** Both are
  **paywalled** and neither is in PMC (checked via the NCBI ID converter:
  "Identifier not found in PMC" for both PMIDs). Their method is also a
  different shape from ours: it back-calculates the instrument's actual
  gradient and flow profiles and projects retention from *isocratic* reference
  data, rather than fitting two gradient runs. Useful later if the engine grows
  gradient-deformation modelling; not a v0.1 test.
- **hplcsimulator.org / retentionprediction.org lineage.** The site is live and
  the predictor source is downloadable (`HPLC Retention Predictor src
  1.0.0-alpha1.tar.gz` via SourceForge SVN), but the site itself states the
  retention database holds only ~40 compounds and that it "is not generally
  useful as a tool to predict HPLC retention". No downloadable dataset of
  gradient runs with conditions was found on the site — only an isocratic
  database behind a web UI. Not usable as a transcribed fixture.
- **LCGC "LC Troubleshooting" columns.** chromatographyonline.com returns HTTP
  403 to automated fetches, so no numbers could be transcribed. Several
  relevant columns exist ("The Perfect Method, Part 7: The Gradient Shortcut",
  "LC Method Scaling, Part II: Gradient Separations"). Worth a manual look by a
  human with a browser if more worked examples are ever needed, but examples
  1–3 already exceed what a magazine column would provide.
- **Column temperature for den Uijl Sets X and Y** is not stated in the article
  or the supplement. Both instruments had thermostatted column compartments.
  This does not affect a two-run fit at fixed temperature (all runs in a set
  share whatever T was used), but it does block any future temperature-modelling
  test built on this data.

### Recommended test ladder

1. **Exact arithmetic** — example 3. Assert t0, tD, S, log k_w, log k_i and the
   four predicted tR values to ~1e-9. Fast, deterministic, no tolerance
   argument. If this fails, nothing else is meaningful.
2. **Physics, high precision** — example 2 (Set Y), fit 3 & 9, predict 4.5 &
   7.5, assert per-peak |error| < 1% and mean signed error < 0.2%.
3. **Physics, realistic noise** — example 1 (Set X), same structure, plus the
   explicit `t_init` regression described in §1.4.
4. **Degenerate input** — the near-t0 compounds (Uracil, Cytosine, Tyramine,
   Peptide 1 in both sets). The engine must decline to fit rather than emit
   nonsense; these rows are a ready-made fixture for that.
5. **Extrapolation warning** — fit 3 & 9, predict 18 (Set Y). Expect
   degradation to the low percent and a systematic overestimate; assert the
   engine flags extrapolation rather than asserting a tight tolerance.

### Synthetic round-trip (still worth having)

Not a fallback here — examples 1–3 make real data available — but the cheapest
possible property test and worth keeping alongside them:

1. Pick (log k_w, S) over a realistic grid: log k_w ∈ [1, 5], S ∈ [3, 25]
   (both ranges taken from the fitted values in §1.3 and §2.3, which is why
   those tables are worth keeping even though they are derived).
2. Generate tR at two gradient times with the forward equation.
3. Fit back, assert recovery of (log k_w, S) to solver tolerance.
4. Predict at a third tG, assert it matches the forward equation exactly.

This catches solver bracketing bugs, sign errors and dwell/hold mishandling
across a far wider parameter space than four published compounds do, and it
needs no network access. It cannot catch a wrong *model* — only examples 1 and
2 can do that.

## References

1. M. J. den Uijl, P. J. Schoenmakers, G. K. Schulte, D. R. Stoll, M. R. van
   Bommel, B. W. J. Pirok, "Measuring and using scanning-gradient data for use
   in method optimization for liquid chromatography", *Journal of
   Chromatography A* **1636** (2021) 461780.
   DOI: [10.1016/j.chroma.2020.461780](https://doi.org/10.1016/j.chroma.2020.461780).
   CC BY 4.0. Data used: Supplementary Material Tables S-1 to S-20
   (`1-s2.0-S0021967320310542-mmc1.docx`); conditions from Sections 2.2, 2.3,
   3.1.1; accuracy claims from Section 3.2 and Figures 3, 9, 11.
2. D. Guillarme, T. Bouvarel, F. Rouvière, S. Heinisch, "A simple mathematical
   treatment for predicting linear solvent strength behavior in gradient
   elution: Application to biomolecules", *Journal of Separation Science*
   **45** (2022) 3276–3285.
   DOI: [10.1002/jssc.202200161](https://doi.org/10.1002/jssc.202200161).
   CC BY. Data used: supporting information `JSSC-45-3276-s001.XLSX`, sheet
   "LSS parameters"; gradient design from `JSSC-45-3276-s002.docx` Table S1.
3. R. Kormány, N. Rácz, S. Fekete, K. Horváth, "Development of a Fast and
   Robust UHPLC Method for Apixaban In-Process Control Analysis", *Molecules*
   **26** (2021) 3505.
   DOI: [10.3390/molecules26123505](https://doi.org/10.3390/molecules26123505).
   CC BY. Data used: Table 2 (predicted vs. experimental tR and R_S), Section
   2.2 (design), Section 3 (Materials and Methods: column, dwell volume).
4. L. R. Snyder, J. W. Dolan, *High-Performance Gradient Elution: The Practical
   Application of the Linear-Solvent-Strength Model*, Wiley-Interscience,
   Hoboken NJ, 2007. ISBN 978-0-471-70646-5.
   DOI: [10.1002/0470055529](https://doi.org/10.1002/0470055529).
   **Paywalled — numbers not transcribed.** Canonical worked two-run examples.
5. P. G. Boswell, J. R. Schellenberg, P. W. Carr, J. D. Cohen, A. D. Hegeman,
   "Easy and accurate high-performance liquid chromatography retention
   prediction with different gradients, flow rates, and instruments by
   back-calculation of gradient and flow rate profiles", *Journal of
   Chromatography A* **1218** (2011) 6742–6749.
   DOI: [10.1016/j.chroma.2011.07.070](https://doi.org/10.1016/j.chroma.2011.07.070).
   **Paywalled, not in PMC — numbers not transcribed.**
6. P. G. Boswell, J. R. Schellenberg, P. W. Carr, J. D. Cohen, A. D. Hegeman,
   "A study on retention 'projection' as a supplementary means for compound
   identification by liquid chromatography–mass spectrometry capable of
   predicting retention with different gradients, flow rates, and instruments",
   *Journal of Chromatography A* **1218** (2011) 6732–6741.
   DOI: [10.1016/j.chroma.2011.07.105](https://doi.org/10.1016/j.chroma.2011.07.105).
   **Paywalled, not in PMC — numbers not transcribed.**
7. Retention Projection / HPLC Retention Predictor project,
   <http://www.retentionprediction.org/hplc/>. Open source (CC BY-NC-SA 3.0
   US); source archive `HPLC Retention Predictor src 1.0.0-alpha1.tar.gz`.
   Retention database limited to ~40 compounds; no transcribable gradient
   dataset published.
