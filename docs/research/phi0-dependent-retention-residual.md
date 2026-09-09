# What makes an LSS retention residual grow with φ₀?

Research notes on a systematic, φ₀-dependent over-prediction of t_R seen when the
engine's two-run LSS fit is used to predict held-out runs that start at higher
%B. A dwell-volume error has been ruled out in-repo. Audience: whoever designs
the v0.2 φ₀ freedom and its honesty diagnostics.

Every claim is tagged **[verified]** (I opened the primary source and the
statement is what it says), **[verified, abstract]** (the authors' own published
abstract only), **[derived]** (my own algebra or my own arithmetic on this
repository's data), or **[could not verify]**. §9 lists everything I could not
establish. Nothing here is described from a search-result snippet.

Survey date: 2026-09-02.

**Log convention.** Per CLAUDE.md, retention math is in the natural-log
convention (S_e, b_e); base-10 (S, log₁₀ k₀) appears only where a source or the
lab sheet uses it, always flagged. S_e = ln(10)·S ≈ 2.303·S. φ is a fraction 0–1;
%B is 100φ.

**Headline.** The dominant discriminator in this repository's own data is not the
offset-vs-slope contrast the ticket expected. It is that **campaign #27 already
contains an s\*-matched pair** — run 3 (t_G 25, 5→95 %B) and run 5 (t_G 22.2,
15→95 %B) have s\* = 0.02160 and 0.02162 and predicted elution compositions
agreeing to 0.1 %B — **and the residual still doubles between them** (§1.4). Every
mechanism I could simulate (curvature, t₀ error, extra-column offset, τ error,
residual organic at injection) acts *only* through s\*, and therefore predicts the
same residual for that pair. None of them can be the cause. §2 says what is left.

---

## 0. Method and coverage

**What I did [derived].** I re-derived the whole result from `validation/` rather
than taking it on trust: an independent implementation of the engine's closed
form and of its two-run fit (§1.1), an independent *exact* integrator for the
fundamental equation of gradient elution (§1.2), and a forward-simulation
mechanism scan in which a known perturbation generates synthetic scouting runs,
the LSS fit is run on them, and the resulting held-out residual pattern is read
off (§3). That scan is the load-bearing evidence of this document, because the
literature does not contain the experiment (§9 item 1).

**Repository data used.** `validation/method.csv`,
`validation/Validation_2/4peaks_run1..run4.csv` (the four-peak sample: scouting
t_G 15/40 min, held-out t_G 20 min at φ₀ = 5 and 15 %B),
`validation/runs-combined.csv` and `validation/run5.csv`, `run7.csv` (campaign
#27: scouting t_G 15/45 min, held-out at φ₀ = 5/15/25 %B). t₀ = 0.6 min,
V_D = 0.375 mL → t_D = 0.9375 min, t_init = 0.5 min, τ = 1.4375 min, as the fits
use. (`method.csv` records a driver-read t₀ = 0.525 min that the fits do **not**
use; §3.4 shows why that matters and §8 raises it.)

**Sources opened in full [verified].** Guillarme et al. 2022 (J. Sep. Sci. 45,
3276–3285) via PMC9543774 and den Uijl et al. 2021 (J. Chromatogr. A 1636,
461780; J. Sep. Sci. 44, 88–114 via PMC7821232) were already read end-to-end for
issue #43 and are reused here rather than re-read — see
`docs/research/composition-extrapolation.md` §0 for that provenance. New reading
for this ticket is listed in §9 with its outcome.

**What I did not do.** I did not run the test suite, did not touch any engine,
spec or test file, and did not port or execute third-party code. The only code
run was my own arithmetic, in a scratch directory, on this repository's data.

**What this document deliberately does not claim.** It does not name a single
proven cause. §3 eliminates five candidates quantitatively and §2/§5 say what
survives and how one injection would decide it.

---

## 1. The observation, re-derived

### 1.1 Validation_2: the numbers check out exactly [derived]

Fitting each peak from `4peaks_run1.csv` (t_G 15) + `4peaks_run2.csv` (t_G 40),
5→95 %B, with the engine's own closed form
t_R = τ + t₀ + (t₀/b_e)·ln(b_e(k₀ − τ/t₀) + 1) and b_e = t₀·Δφ·S_e/t_G:

| peak | S_e | S (base-10) | log₁₀ k_w | log₁₀ k₀ at 5 %B |
|---|---|---|---|---|
| 1 | 11.4059 | 4.9535 | 3.9575 | 3.7098 |
| 2 | 11.4025 | 4.9520 | 3.9857 | 3.7381 |
| 3 | 11.3310 | 4.9210 | 4.0249 | 3.7789 |
| 4 | 11.3324 | 4.9216 | 4.0451 | 3.7990 |

Predicting the two held-out t_G = 20 min runs:

| | peak 1 | peak 2 | peak 3 | peak 4 | mean | spread |
|---|---|---|---|---|---|---|
| **run 3, φ₀ = 5 %B** residual (min) | +0.0130 | +0.0125 | +0.0116 | +0.0120 | **+0.01224** | 0.00141 |
| as % of t_R | +0.079 | +0.076 | +0.069 | +0.071 | +0.074 | |
| predicted φ_e (%B) | 69.57 | 70.16 | 71.34 | 71.74 | | |
| **run 4, φ₀ = 15 %B** residual (min) | +0.0297 | +0.0283 | +0.0266 | +0.0261 | **+0.02769** | 0.00356 |
| as % of t_R | +0.193 | +0.182 | +0.168 | +0.164 | +0.177 | |
| predicted φ_e (%B) | 68.54 | 69.13 | 70.30 | 70.71 | | |

This reproduces the ticket's stated +0.012 / +0.028 min, the S ≈ 4.92–4.95,
log₁₀ k₀ ≈ 3.71–3.80, the 68–72 %B elution window, and both spreads (0.0014 /
0.0036 min) exactly. **The arithmetic in the ticket is right.** Ratio of means:
**2.26**.

### 1.2 The exact integral agrees with the closed form [derived]

The engine's closed form is the analytic solution of
∫₀^{t_R−t₀} dt / k(φ_col(t)) = t₀, with φ_col the composition arriving at the
column head (the pump program delayed by t_D). I implemented that integral
numerically with `scipy.integrate.quad` + `brentq` and, feeding it a pure LSS
k(φ), it reproduces the closed form to < 1e-4 min at every condition used below.
So the mechanism scan of §3 is comparing like with like: the only difference
between "truth" and "model" in each scan row is the perturbation being tested,
not the integration.

### 1.3 Campaign #27: the numbers also check out, and add a third φ₀ [derived]

Fitting from `run1.csv` (t_G 15) + `run2.csv` (t_G 45), 5→95 %B:
S_e = 11.7019 / 11.4894 / 11.9250 (S = 5.08 / 4.99 / 5.18), log₁₀ k_w = 3.013 /
3.493 / 5.014.

| held-out run | φ₀ | Δφ | t_G | s\* | mean residual (min) | mean residual (%) | per-peak (%) |
|---|---|---|---|---|---|---|---|
| run 3 | 5 %B | 0.90 | 25 | 0.02160 | +0.0567 | **+0.355** | +0.534 / +0.425 / +0.105 |
| run 5 | 15 %B | 0.80 | 22.2 | 0.02162 | +0.1025 | **+0.729** | +1.005 / +0.747 / +0.436 |
| run 7 | 25 %B | 0.70 | 25 | 0.01680 | +0.1802 | **+1.519** | +2.496 / +1.606 / +0.456 |

Again exactly the ticket's 0.35 / 0.73 / 1.52 %. Successive ratios **2.086** and
**2.082** — the residual is very close to *geometric* in φ₀, doubling every
10 %B. Validation_2's 2.26 over the same 10 %B step agrees. **Two independent
samples on the same instrument give ≈ ×2.1 per 10 %B of φ₀** [derived].

### 1.4 The sharpest fact in the dataset: run 3 and run 5 are s\*-matched [derived]

`run5.csv` was designed (correctly) with t_G = 22.2 min so that
s\* = t₀·Δφ/t_G = 0.6 × 0.80 / 22.2 = 0.02162 matches run 3's
0.6 × 0.90 / 25 = 0.02160 — a 0.1 % match.

Under LSS with the large-k₀ approximation the elution composition depends on the
gradient **only** through s\*
(`composition-extrapolation.md` §7.2, Guillarme Eq. 8), and indeed the engine
predicts φ_e = 47.6 / 57.9 / 85.4 %B for run 3 and 47.6 / 57.9 / **85.5** %B for
run 5 — the same place on each peak's ln k line, to 0.1 %B.

**Same s\*, same predicted elution composition, same calibrated window, same
column, same sample — and the mean residual goes from +0.355 % to +0.729 %.**

This is a completed experiment, not a proposal, and it is the strongest
discriminator this repository owns. Every mechanism I could simulate in §3 —
including curvature — moves retention only through s\*, and therefore predicts
run 3 and run 5 residuals that agree to a few thousandths of a minute. They
differ by 0.046 min. §2 draws the consequence.

What run 3 vs run 5 does **not** separate is φ₀ from Δφ: run 5 changed both
(5→15 %B start, 0.90→0.80 span) in order to hold s\* fixed. §5 gives the single
injection that separates them.

---

## 2. What the shape of the residual implies before any literature is consulted

Three structural facts [all derived], stated before the candidate list because
they eliminate most of it.

**2.1 The dwell/hold sensitivity and the pre-gradient migration term are the same
quantity, and both are bounded by k_e/k₀.** Differentiating the closed form,
∂t_R/∂τ = 1 − 1/[b_e(k₀ − τ/t₀) + 1] = **1 − k_e/k₀** — the ticket's expression,
confirmed. The *whole* pre-gradient migration correction (the "−τ/t₀" inside the
logarithm — the isocratic-hold term) is of size τ·k_e/k₀. So a single number
bounds two of the ticket's five candidates at once.

For Validation_2, k_e/k₀ = 6.3e-4 (φ₀ = 5 %B) and 2.2e-3 (φ₀ = 15 %B). The entire
hold term is therefore 0.0009 min and 0.0032 min. **Both are smaller than the
residual they would have to explain, and their difference (0.0023 min) is 15 % of
the excess to be explained (0.0155 min).** Neither a dwell error nor a
mis-modelled isocratic hold can produce this on the Validation_2 sample. To close
the 0.0155 min gap by dwell alone would need δτ ≈ 9.7 min (V_D wrong by ~3.9 mL).

**2.2 I partly disagree with the ticket's dwell argument as stated, and the
disagreement makes the conclusion stronger, not weaker.** The claim that
∂t_R/∂τ "is within 0.2 % of 1 at every condition" is true for Validation_2 but
**false for campaign #27**: k_e/k₀ reaches 2.2e-2 for run 5 peak 1 and
**8.8e-2 for run 7 peak 1** (log₁₀ k₀ = 1.74 there — below Guillarme's 2.1 floor,
`composition-extrapolation.md` §5.2). On campaign #27 alone a dwell error is *not*
excluded by insensitivity: solving δτ·Δ(k_e/k₀) = excess residual gives
δτ ≈ 2.4 min from run 5 and ≈ 1.9 min from run 7 — suspiciously consistent.

What kills it is the **cross-dataset** test [derived]: the same δτ must explain
Validation_2, where it would have to be ≈ 9.7 min. 2 min and 10 min are not the
same number, and 2 min is already 0.8 mL of dwell on an Acquity H-Class. **Dwell
is ruled out — by the inconsistency between the two samples, not by insensitivity
alone.** Anyone re-running the argument on campaign #27 in isolation would find it
does not close, so it is worth recording the correct form. (Per the ticket's
constraint, nothing here recommends changing V_D = 0.375 mL.)

**2.3 A wrong k at the scouting φ₀ is invisible to the fit, and only φ₀ freedom
can see it.** Both scouting runs start at 5 %B, so they share one k₀. The two-run
fit has two free parameters (k_w, S_e) and two observations; an error in k(0.05)
common to both runs is absorbed exactly into k_w with S_e unchanged. Therefore:

- a prediction at φ₀ = 5 %B carries **no** penalty from a wrong k(0.05);
- a prediction at φ₀ = 15 %B uses k(0.15) = k(0.05)·e^{−S_e·0.10}, i.e. it asserts
  that ln k falls by exactly S_e·Δφ₀ between the two starting compositions;
- so **the φ₀ axis is the first thing that tests the fitted line anywhere near the
  low-φ end**, and it tests it as a *slope over [φ₀_scout, φ₀_candidate]*, not as
  a value.

Inverting the sensitivity ∂t_R/∂ln k₀ = t₀·k_e (= 1.95 and 2.19 min for
Validation_2 peak 1), the observed excess of 0.0155 min at φ₀ = 15 %B corresponds
to the true ln k falling **0.0071 more** than the fitted line says over 5→15 %B —
a local slope of 11.48 against the fitted 11.41, i.e. the true ln k vs φ curve is
**0.6 % steeper at 5–15 %B than the two-run fit's effective slope**, which is
pinned at 63–72 %B. Steeper at low φ than at high φ is exactly the sign of the
curvature the literature reports (§4). **The magnitude required is sub-1 %.**

**2.4 The offset-to-slope contrast is real but weak evidence, and the peaks are
partly co-eluting.** The Validation_2 spreads (0.0014 → 0.0036 min) are 1.4 and
3.6 units of the 0.001 min recording granularity, over four peaks that are 0.07 to
0.10 min apart with W½ ≈ 0.023–0.035 min — R_s ≈ 1.6–2.4, i.e. a partly
overlapping cluster whose apex positions carry an integration bias that itself
changes when the cluster spreads out (it does: W½ grows from ~0.024 to ~0.033 min
between run 3 and run 4). I would not build a mechanism argument on 0.0036 min
from four apexes in a cluster at that resolution. **Campaign #27 gives the same
"falls with retention" signature far above any such doubt** — run 7's residual
falls +2.50 % → +1.61 % → +0.46 % across peaks eluting at 46 / 56 / 83 %B, a
0.13 min spread — so the *shape* claim survives; it just should be sourced to
#27, not to the 4-peak cluster. §3 shows what it discriminates.

---

## 3. Mechanism scan: forward-simulating each candidate

### 3.1 The method [derived]

For each candidate mechanism I take the four Validation_2 peaks, define a "true"
system carrying that perturbation, generate synthetic scouting runs (t_G 15 and
40, 5→95 %B) from it with the exact integrator of §1.2, run the engine's two-run
LSS fit on those synthetic runs exactly as the app would, and then predict three
held-out runs and report the residual against the same true system:

- **5 %B**: t_G 20, 5→95 %B — the real run 3 condition (s\* = 0.0270);
- **15 %B**: t_G 20, 15→95 %B — the real run 4 condition (s\* = 0.0240);
- **5→85**: t_G 20, 5→85 %B — *not yet run on the bench*. It has **the same Δφ
  (0.80), the same t_G and the same s\* (0.0240) as the 15 %B run and the same φ₀
  as the 5 %B run.** It is the discriminator of §5.

"Spread" is the largest-minus-smallest residual across the four peaks;
"rise"/"fall" is whether the residual grows or shrinks with retention order.

### 3.2 The scan [derived]

| mechanism | φ₀=5 %B | φ₀=15 %B | ratio | spread @15 %B | across peaks | 5→85 %B |
|---|---|---|---|---|---|---|
| **OBSERVED** | **+0.0122** | **+0.0277** | **2.26** | **0.0036** | **falls** | **?** |
| truth = model (control) | −0.0000 | −0.0000 | — | 0.0000 | — | −0.0000 |
| quadratic curvature S₂ = +6 | +0.0142 | +0.0191 | 1.34 | 0.0013 | rises | +0.0185 |
| quadratic curvature S₂ = +10 | +0.0213 | +0.0281 | 1.32 | 0.0028 | rises | +0.0277 |
| quadratic curvature S₂ = −6 | −0.0263 | −0.0495 | 1.88 | 0.0045 | rises | −0.0350 |
| quadratic curvature S₂ = −10 | −0.0731 | −0.1916 | 2.62 | 0.0343 | rises | −0.0986 |
| t₀ truly 0.525 (fit uses 0.6) | −0.0066 | −0.0087 | 1.30 | 0.0000 | — | −0.0084 |
| t₀ truly 0.65 | +0.0044 | +0.0058 | 1.30 | 0.0000 | — | +0.0056 |
| t₀ truly 0.70 | +0.0089 | +0.0115 | 1.30 | 0.0000 | — | +0.0112 |
| t₀ truly 0.80 | +0.0177 | +0.0230 | 1.30 | 0.0001 | — | +0.0224 |
| extra-column offset +0.05 min | +0.0044 | +0.0058 | 1.30 | 0.0000 | — | +0.0056 |
| extra-column offset +0.10 min | +0.0088 | +0.0116 | 1.31 | 0.0001 | — | +0.0112 |
| τ truly 1.1375 (fit uses 1.4375) | −0.0266 | −0.0347 | 1.31 | 0.0002 | — | −0.0336 |
| τ truly 1.7375 | +0.0265 | +0.0353 | 1.33 | 0.0003 | — | +0.0335 |
| τ truly 2.4375 | +0.0878 | +0.1202 | 1.37 | 0.0012 | — | +0.1109 |
| residual organic at injection, +0.5 %B | −0.0000 | +0.0001 | — | 0.0000 | — | — |
| residual organic at injection, +2.0 %B | −0.0000 | +0.0006 | — | 0.0000 | — | — |

Quadratic truth is parameterised as ln k = ln k_w − S_e·φ + S₂(φ−a)(φ−b) with
a = 0.635, b = 0.721 (the two scouting elution compositions), so S₂ > 0 is the
ordinary convex case — ln k steeper at low φ, flatter at high φ. S₂ = ±6 changes
the local S_e by about ±5 over the full φ range, i.e. it is already strong
curvature. "Residual organic at injection" raises the composition seen by the
column during the hold by the stated amount.

### 3.3 What the scan eliminates [derived]

1. **Every timing error — t₀, extra-column volume, τ — gives ratio 1.30–1.37 and
   essentially zero spread across peaks.** The ratio is remarkably invariant to
   which timing quantity is wrong and by how much. The observed 2.26 is not in
   that family, and the observed 0.0036 min spread is two orders of magnitude
   above what a timing error of the observed *mean* size produces. (To generate a
   0.0036 min spread by a τ error you need δτ ≈ 3 min, which puts the mean
   residual near 0.4 min.)
2. **Convex curvature has the right sign but the wrong ratio, the wrong spread
   direction and the wrong magnitude balance.** S₂ = +10 reaches the observed
   φ₀ = 15 %B residual but then predicts +0.0213 min at φ₀ = 5 %B where +0.0122
   is observed; and its residual *rises* with retention order where the observed
   one falls. Concave curvature (S₂ < 0) reaches ratio ≈ 2.3 only at S₂ ≈ −8, but
   with the residual negative — under-prediction — which is not what happens.
3. **Residual organic left on the column at injection is numerically dead.** At
   log₁₀ k₀ ≈ 3.7 the band does not move during the hold whatever the composition
   is; even 2 %B of residual organic moves t_R by 0.0006 min. This is the same
   arithmetic as §2.1 and it disposes of the naive "incomplete re-equilibration"
   story — *as a mobile-phase-composition effect*. It says nothing about a
   stationary-phase-state effect (§4.4), which this simulation cannot represent.
4. **Pressure/viscosity and preferential-solvation effects, in so far as they act
   as a composition-dependent multiplier on k, are curvature.** Any perturbation
   expressible as k → k·g(φ) is ln k → ln k + ln g(φ) and lands in row 2 of the
   scan; if g is smooth over 5–95 %B it is captured by the quadratic rows. They
   are not a separate escape route.
5. **A linear miscalibration of the pump's %B is invisible.** If the delivered
   composition is φ' = αφ + γ, then ln k = ln k_w − S_e(αφ+γ) is again exactly LSS
   in the programmed φ with rescaled parameters, so the fit absorbs it completely
   [derived, algebra]. Only a *non-linear* proportioning error survives, and that
   is curvature again.

### 3.4 One thing the scan does establish about the φ₀ = 5 %B baseline [derived]

The +0.0122 min at φ₀ = 5 %B is an *interpolation* residual (t_G = 20 sits inside
[15, 40]) and it is comfortably explained by any of several small errors: convex
curvature at S₂ ≈ +5, a true t₀ near 0.67 min rather than the 0.6 the fits use, an
extra-column offset near 0.07 min, or τ larger by ~0.15 min. `method.csv` records
a driver-read t₀ = 0.525 min that the fits do not use; the scan says that swapping
0.6 → 0.525 would turn the residual from +0.0066 into −0.0066, i.e. **the sign of
the baseline residual is a direct function of the unresolved t₀ question (#24)**.
That is worth knowing before anyone reads meaning into ±0.012 min.

It also means the two residuals should be treated as two facts, not one: a
φ₀-independent baseline of about +0.012 min, and a **φ₀-driven excess** of about
+0.0155 min per 10 %B on this sample. Only the second needs a new mechanism.

### 3.5 The decisive test: campaign #27's run 3 and run 5 are the same gradient, translated [derived]

This is the strongest result in the document and it needs no retention model at
all.

Run 3's composition ramp rate at the column is Δφ/t_G = 0.90/25 = 0.036000 φ/min;
run 5's is 0.80/22.2 = 0.036036 φ/min. **The same slope to 0.1 %.** Both have the
same t₀, the same t_D and the same 0.5 min hold. So the composition profile
arriving at the column head in run 5 is exactly run 3's profile **translated
2.79 min earlier**: run 5 starts where run 3 is 2.79 min into its ramp.

For a peak that does not migrate measurably during that extra 2.79 min at 5–15 %B,
**every retention model whatsoever — LSS, quadratic, Neue–Kuss, log-log,
mixed-mode — predicts that it elutes exactly 2.79 min earlier in run 5 than in
run 3.** The prediction is a property of the gradient program, not of k(φ).

How immobile is "immobile"? The head-stretch contribution to the migration
integral is (1/rate)·(1/S_e)·[1/k(0.15) − 1/k(0.05)], against t₀ = 0.6 min:

| peak | log₁₀ k_w | head-stretch share of the integral | shift the model expects | shift observed | excess |
|---|---|---|---|---|---|
| 1 | 3.013 | 1.5 % | 2.771 min | 13.787 − 10.980 = **2.807** | +0.036 |
| 2 | 3.493 | 0.5 % | 2.783 min | 16.658 − 13.843 = **2.815** | +0.032 |
| 3 | 5.014 | **0.016 %** | 2.797 min | 24.358 − 21.495 = **2.863** | **+0.066** |

For **peak 3 the correction is 3.6e-4 min** — utterly negligible — so its expected
shift of 2.797 min is model-independent. It shifts by 2.863 min. **The extra
0.066 min (0.3 % of t_R) cannot be produced by any k(φ) whatsoever.**

This is the cleanest statement of the problem I can make: *the residual is not a
retention-model error*. Something outside k(φ) changed between a run that started
at 5 %B and a run that started at 15 %B and otherwise saw an identical
composition programme. Candidates that survive it are in §4.4.

**Caveat, stated plainly [derived].** The translation argument assumes the two
runs' t₀, flow, dwell and hold were in fact identical, and that the pump delivered
the programmed 0.036000 and 0.036036 φ/min faithfully. A 0.1 % flow difference is
0.02 min on a 22 min retention — a quarter of peak 3's excess. The argument is
strong but it is one comparison of two single injections. §5 says how to make it
safe.

---

## 4. What the literature documents

### 4.1 φ₀ is the *most* retention-sensitive instrument variable there is [verified]

The directly relevant primary source is **Beyaz, Fan, Carr & Schellinger 2014**
(J. Chromatogr. A 1371, 90–105), free full text at PMC4388777. It is a precision
study — it asks which instrument variables control retention *reproducibility* in
gradient RPLC — and its answer is φ₀. Verbatim from the full text:

> "The initial mobile phase composition is always more important than the final
> mobile phase composition."

> "Changes in ϕo will change the retention time more than do changes in ϕf, tG
> and F"

> "Changes in the initial mobile phase change both k′_o and the gradient steepness"

> "For all three solute sets a 0.001 volume fraction change in ϕf shifts retention
> time on average by 0.007 min… Note that on average retention is almost five
> times as sensitive to a change in ϕo as to a change in ϕf."

> "the retention time shifts by 0.02 min − 0.04 min when initial mobile phase
> composition is controlled to within 0.001 VF."

Their practical recommendation is to *avoid the problem*: "The most reproducible
results will be obtained by starting the gradient at 100% A solvent and preparing
the A solvent gravimetrically." Their own instrument's dwell was determined as
0.34 mL.

**What this establishes and what it does not [derived].** It establishes that a
0.1 %B error in the delivered starting composition is worth tens of milliseconds
to tens of seconds of retention — i.e. that φ₀ is exactly the axis on which a
small delivery or model error becomes visible. It does **not** establish a
φ₀-dependent *bias* in LSS prediction: their variable is run-to-run scatter at a
nominally fixed φ₀, not accuracy when φ₀ is deliberately changed. That experiment
I could not find (§9 item 1).

**Scaled to this column [derived].** On the Validation_2 method the model's own
∂t_R/∂φ₀ is (15.423 − 16.386)/0.10 = −9.6 min per unit φ₀, i.e. **0.0096 min per
0.001 VF** — a factor 2–4 below Beyaz's sets (they used longer columns and longer
gradients). Inverting: the +0.0155 min φ₀-excess on Validation_2 corresponds to
0.0016 VF = **0.16 %B** of composition error, and campaign #27's +0.066 min for
peak 3 corresponds to 0.0024 VF = **0.24 %B**. Both are *inside* a normal
quaternary pump's composition-accuracy specification. The effect is small in
physical terms; it is only large relative to a two-run fit's ambitions.

### 4.2 Curvature in ln k vs φ: documented, right sign, wrong size [verified / derived]

That ln k vs φ is curved and that the log-linear model is a local approximation is
settled; `composition-extrapolation.md` §4.1 collects the verified statements
(den Uijl 2021 ×2, Guillarme 2022, Baeza-Baeza 2013) and they are not re-quoted
here. Two are directly on this ticket's question:

- **Baeza-Baeza et al. 2013** [verified, abstract] is the only paper I found whose
  stated variable is the initial modifier concentration: the quadratic model gives
  "accurate predictions of the retention time **for a wide range of initial
  concentrations of organic modifier and gradient slopes, with errors usually
  below 1-2%**", with LSS explicitly limited to "relatively small concentration
  ranges of modifier". Read as a claim about LSS, it says the log-linear model is
  *expected* to degrade when φ₀ is varied. Full text still unobtainable (§9).
- **Neue & Kuss 2010** [verified, abstract] offer their model for "the simultaneous
  exploration of temperature, **gradient starting composition** and gradient
  slopes" — again naming φ₀ as the axis LSS does not own.

**Sign check [derived].** The residual requires the true ln k curve to be about
0.5–1.0 % *steeper* over 5–15 %B than the effective slope the two-run fit measures
at 63–72 %B (§2.3). Steeper at low φ, flatter at high φ **is** the ordinary convex
RP curvature, so the sign of the observed effect is the sign curvature predicts.
That is why curvature is the natural first suspect — and why §3.2/§3.5 are worth
taking seriously when they say it cannot be the answer here: §3.2 shows curvature
strong enough to reach the observed magnitude also over-shoots the φ₀ = 5 %B
baseline and has the wrong per-peak slope; §3.5 shows the campaign-#27 residual
survives a comparison in which *every* k(φ) cancels.

### 4.3 Re-equilibration: the numbers, and what they do and do not cover [verified]

**Schellinger, Stoll & Carr 2005** (J. Chromatogr. A 1064, 143–156) and **2008**
(J. Chromatogr. A 1192, 41–53), abstracts via PubMed:

> "excellent repeatability (+/-0.002 min in retention time) is achieved with at
> most 2 column volumes" — while full equilibration requires substantially more,
> and the process is "more thermodynamically limited than kinetically controlled".

> "two column volumes of re-equilibration with initial eluent suffices to provide
> acceptable repeatability (no worse than 0.004min)" for a 15 cm × 4.6 mm column,
> with "truly extraordinary repeatability often as good as 0.0004min" under
> optimal conditions.

Beyaz 2014 repeats the figure from the full text: "It is possible to achieve run
to run gradient elution retention reproducibility to ± 0.002 min (standard
deviation) in a bit more than two column volumes of re-equilibration."

**Critically, all of these are *repeatability* statements at a fixed φ₀** [derived].
They say a partly-equilibrated column is *reproducibly* partly-equilibrated. They
say nothing about whether the retention of a partly-equilibrated column agrees
with that of a fully-equilibrated one — indeed the 2005 paper's own distinction
between "run-to-run repeatability and full equilibration" implies it does not.
**A column re-equilibrated 6 column volumes toward 5 %B and one re-equilibrated
6 column volumes toward 15 %B are two different stationary phases, both
reproducible.** That is the loophole every one of these papers leaves open, and
it is the loophole §3.5's translation argument points at.

**On this method [derived].** V_M ≈ t₀·F = 0.6 × 0.4 = 0.24 mL. The recorded
gradient tables give a re-equilibration hold of 3.4–4.0 min = 1.36–1.60 mL =
**5.7–6.7 column volumes** — above Schellinger's 2 CV repeatability threshold,
below the ">20 CV" they associate with full equilibration, and **below
`validation/PROTOCOL.md`'s own instruction of "≥ 10 column volumes"** (§8).

### 4.4 Sample-solvent mismatch and volume overload: documented, modelled, not excluded [verified, abstract]

**Rutan, Jeong, Carr, Stoll & Weber 2021** (J. Chromatogr. A 1653, 462376) extend
the LSS and Neue–Kuss closed forms "to account for effects of sample volume
overload and a mismatch between the sample solvent and the initial mobile phase
composition for the gradient", treating "elution across four zones of the gradient
profile — elution in the sample solvent, elution in the initial (isocratic) mobile
phase caused by the gradient delay volume, elution during a linear gradient, and
elution post-gradient". They also note "there have been errors in expressions
reported in the literature".

**Why this matters here [derived].** The injection is 10 µL of 50:50 water:ACN
(`method.csv`) into V_M ≈ 240 µL — **4 % of the column's mobile-phase volume, at
50 %B into a 5 %B or 15 %B eluent.** This is precisely the regime their paper
exists for. And it is an *initial-condition* effect, not a property of φ_col(t):
**it is the one candidate on the list that the §3.5 translation argument does not
exclude**, because the plug's strength relative to the surrounding eluent differs
between a 5 %B start and a 15 %B start. Its sign is arguable in both directions —
the analyte migrates inside an identical 50 %B plug in both runs, but the plug
disperses into a stronger background in the 15 %B run — and I did not model it
(§9 item 4). It is cheap to test (§5, E3), and `method.csv` already carries the
driver's note "consider diluting 1:1 with water or 2-3 uL injection".

### 4.5 Preferential solvation: real, but the citation I found is normal-phase [verified, abstract]

**Jandera 2002** (J. Chromatogr. A 965, 239–261) reports that in normal-phase
gradient HPLC, retention "can be calculated accurately when appropriate
corrections are adopted for gradient dwell volume and preferential solvent
adsorption", giving prediction errors under 2–3 %. Preferential adsorption of the
stronger solvent onto the stationary phase distorts the composition profile the
solute actually experiences relative to the programmed one — exactly the class of
mechanism §3.5 leaves standing, since it is a column-state effect rather than a
k(φ) effect. **But this is a normal-phase paper**, where the effect is far larger
than in RP, and I did not find an RP paper quantifying it for gradient prediction
(§9 item 5). It is listed here as a mechanism *class* with a real citation, not as
a quantified RP candidate.

### 4.6 Pressure and viscous heating [could not verify]

I did not obtain a primary source quantifying the pressure dependence of k for
small molecules on sub-2 µm columns and could not put a number on it (§9 item 6).
What can be said without one [derived]: the water–ACN viscosity maximum sits near
10–20 % ACN, so a run starting at 15 %B begins nearer the pressure maximum than
one starting at 5 %B — but both bands are immobile at those compositions and both
elute at 68–72 %B, where the pressure and temperature are the same. Any pressure
effect acting through k is a composition-dependent multiplier on k, i.e.
curvature (§3.3 item 4). I do not consider it a live candidate, but I could not
close it with a source.

---

## 5. Minimal new experiments

### 5.1 What the existing runs already decide [derived]

| question | decided by runs already in `validation/`? |
|---|---|
| Is it a dwell error? | **Yes — no.** §2.1/§2.2: no single δτ fits both samples (needs ≈2 min for #27, ≈10 min for Validation_2). |
| Is it a mis-modelled isocratic hold / pre-gradient migration? | **Yes — no.** §2.1: the whole term is ≤0.003 min at φ₀ ≤ 15 %B. |
| Is it an s\* / gradient-steepness effect? | **Yes — no.** §1.4: run 3 and run 5 are s\*-matched to 0.1 % and the residual still doubles. |
| Is it any k(φ) model error (curvature, Neue–Kuss, quadratic)? | **Yes — no,** for campaign #27. §3.5: the run 3 → run 5 translation is violated by 0.066 min on a peak whose head-stretch correction is 3.6e-4 min. |
| Is it a linear %B miscalibration? | **Yes — no.** §3.3 item 5: absorbed exactly by the fit. |
| Is it φ₀, or is it Δφ? | **No.** Perfectly confounded in every run on file. → **E1**. |
| Is it column state / re-equilibration end-point? | **No.** → **E2**. |
| Is it sample-solvent mismatch / volume overload? | **No.** → **E3**. |
| What is the repeatability floor? | **No.** Every held-out condition is a single injection. → **E4**. |

### 5.2 E1 — the flagship: separate φ₀ from Δφ. **One injection.**

On the **Validation_2 sample and column**, run **5 → 85 %B over t_G = 20 min**,
0.5 min initial hold, everything else identical to `4peaks_run4.csv`.

|  | run 3 (have) | run 4 (have) | **E1 (new)** |
|---|---|---|---|
| φ₀ | 5 %B | 15 %B | **5 %B** |
| φ_f | 95 %B | 95 %B | **85 %B** |
| Δφ | 0.90 | 0.80 | **0.80** |
| t_G | 20 | 20 | **20** |
| s\* = t₀Δφ/t_G | 0.0270 | 0.0240 | **0.0240** |
| b_e (peak 1) | 0.3080 | 0.2737 | **0.2737** |

E1 shares **φ₀ with run 3** and **Δφ, t_G, s\*, b_e with run 4**. It is the single
missing cell of the 2×2.

**What each hypothesis predicts** (from the §3.2 scan's own 5→85 column):

| if the cause is… | E1 residual |
|---|---|
| curvature, t₀ error, extra-column, τ error — anything acting through s\* | **≈ +0.028 min** (like run 4) |
| genuinely φ₀ — column state, injection mismatch, φ₀ delivery | **≈ +0.012 min** (like run 3) |

Those are 0.016 min apart, ~11× the 0.0014 min spread seen within run 3 and ~8×
Schellinger's ±0.002 min repeatability figure. **One injection separates them.**

**Feasibility check [derived].** Under LSS with s\* = 0.0240 the predicted elution
compositions are 68.5 / 69.1 / 70.3 / 70.7 %B — the same as run 4's, and
comfortably below φ_f = 85 %B, so all four peaks stay in the gradient regime and
nothing is confounded by a post-gradient branch. (This is *why* the Validation_2
sample must be used and not campaign #27's, whose peak 3 elutes at 85.4 %B and
would go post-gradient at φ_f = 85 %B.)

Run E1 **bracketed by a repeat of run 4** in the same sequence, so the comparison
does not rest on data taken weeks apart.

### 5.3 E2 — column state. **Two injections.**

Repeat run 3 and run 4 with the re-equilibration hold extended from ~3.4 min
(5.7 CV) to ~12 min (20 CV), the figure Schellinger et al. associate with
approaching full equilibration (§4.3). If the residual difference between the two
φ₀ values shrinks, the re-equilibration end-point is implicated; if it does not
move, column state is out. This also brings the method into line with
`PROTOCOL.md`'s own "≥ 10 column volumes" (§8 item 4).

### 5.4 E3 — injection. **Two injections.**

Repeat run 3 and run 4 with the sample diluted 1:1 in water (making the diluent
25 %B) or with a 2 µL injection instead of 10 µL. §4.4 says this is the only
candidate the translation argument does not kill. If the φ₀ excess collapses, it
is sample-solvent mismatch / volume overload and the fix is a method rule, not an
engine change.

### 5.5 E4 — the floor. **Four injections.**

Triplicate run 3 and triplicate run 4 (six total, minus the two already held). No
held-out condition in `validation/` has a replicate, so the repeatability of this
method is currently **unknown**, and §6 has to borrow a literature figure to
stand in for it. This is the cheapest run on the list and it is a precondition for
believing any of the others. **Do E4 in the same sequence as E1.**

### 5.6 E5 — re-do the decisive pair properly. **Two injections.**

Repeat campaign #27's run 3 (5→95, t_G 25) and run 5 (15→95, t_G 22.2)
back-to-back, bracketed. The 0.066 min translation violation of §3.5 is currently
one injection against one injection; it is the strongest result in this document
and it deserves a second measurement.

**Total: eleven injections, of which E1 + E4 (five injections, one sequence) carry
most of the information.**

---

## 6. Is 0.012 min just the noise floor?

**Short answer [derived]: on Validation_2, yes at φ₀ = 5 %B and no at
φ₀ = 15 %B — and campaign #27 is not noise at any φ₀.**

### 6.1 Against the published accuracy expectations [verified, reused from #43]

| bar | source | Validation_2 @5 %B | Validation_2 @15 %B | #27 @5/15/25 %B |
|---|---|---|---|---|
| interpolation "mostly less than 0.5 %" (Set X) | den Uijl 2021 | 0.074 % ✅ | 0.177 % ✅ | 0.36 / 0.73 ❌ / 1.52 ❌ |
| interpolation "almost all below 0.2 %" (Set Y, high-precision) | den Uijl 2021 | 0.074 % ✅ | 0.177 % ✅ | all ❌ |
| method development needs "(well) within 1 %" | den Uijl 2021 review | ✅ | ✅ | ✅ / ✅ / ❌ |
| run-to-run repeatability achievable | Schellinger 2005/2008, Beyaz 2014 | ±0.002 min | ±0.002 min | ±0.002 min |

The Validation_2 baseline of **+0.012 min = 0.074 %** is below every published
*accuracy* expectation — but it is **six times** the best published *repeatability*
(±0.002 min), so it is a real systematic offset, not scatter. §3.4 shows it is
fully accounted for by the unresolved t₀ question alone. **It does not need a
mechanism.** The φ₀ = 15 %B value does, and all of campaign #27 does.

### 6.2 The metric that actually matters: λ, error in peak widths [derived]

`composition-extrapolation.md` §3.2 adopts Guillarme's λ = (t_R,pred − t_R,exp)/w
with λ ≤ 0.5 as the acceptance bar. Taking w = 4σ = 1.699·W½ from the recorded
half-heights:

| run | mean W½ | w = 4σ | mean residual | **λ** |
|---|---|---|---|---|
| Validation_2 run 3, φ₀ = 5 %B | 0.0300 | 0.0510 | 0.0122 | **0.24** ✅ |
| Validation_2 run 4, φ₀ = 15 %B | 0.0333 | 0.0565 | 0.0277 | **0.49** ⚠️ |
| #27 run 7, φ₀ = 25 %B, peak 1 | 0.071 | 0.121 | 0.2305 | **1.90** ❌ |
| #27 run 7, peak 2 | 0.135 | 0.229 | 0.2062 | **0.90** ❌ |
| #27 run 7, peak 3 | 0.053 | 0.090 | 0.1039 | **1.15** ❌ |

**At φ₀ = 15 %B the Validation_2 prediction is already sitting on Guillarme's
λ = 0.5 line**, and campaign #27 at φ₀ = 25 %B is at λ = 0.9–1.9, which in
Guillarme's own words is the regime "where predicted and experimental peaks would
be fully baseline resolved". For a four-peak cluster 0.10–0.15 min wide, that is
not cosmetic. **Only the φ₀ = 5 %B number is noise; everything above it is a
decision-grade error.** (The w = 4σ convention is my assumption — Guillarme's
paper defines w from the maximum plate number and I did not re-open it for this
ticket; a different convention scales the whole column but not the ordering.)

### 6.3 The empirical law, and the honest limit on it [derived]

**Amended 2026-09-09 (#134).** The ×2.1 figure was fitted on short baselines at
t₀ = 0.6 min. Both of those conditions have since changed and the law is weaker
than it looked. The amended result is stated first; the original reading is kept
beneath it, because §7 rests on the part of it that survived.

**The amended law.** Held-out runs on Validation_2 now span φ₀ = 5 → 75 %B. Refit
on one footing (engine at `main`, t₀ = 0.525 min, fit from `4peaks_run1.csv` +
`4peaks_run2.csv` only), the mean over-prediction per run is:

| φ₀ | run | departure from the scouting start | pred − meas |
|---|---|---|---|
| 5 %B | run 3 | — | +0.019 min |
| 5 %B | E1 | — | +0.026 min |
| 15 %B | run 4 | +10 %B | +0.036 min |
| 25 %B | run 6 | +20 %B | +0.044 min |
| 50 %B | φ₀-50 | +45 %B | +0.246 min |
| 75 %B | φ₀-75 | +70 %B | **−0.084 min** |

Least squares in ln(residual) over the four φ₀ from 5 to 50 %B, averaging the two
5 %B runs, gives

> residual (min) = e^(−4.174 + 0.05322·%B) → **×1.70 per 10 %B**

reproducing those four points to −10 % / +32 %. The multiplicative *form*
survives; the *exponent* does not. Two things moved it off ×2.1:

1. **The t₀ rebaseline (#24).** The same Validation_2 step that gave ×2.26 at
   t₀ = 0.6 min gives **×1.63** at t₀ = 0.525 min. §7.7 warned that any reading
   of this baseline was hostage to #24. It was.
2. **The lever arm.** Per-step ratios are 1.63 (5→15), 1.21 (15→25) and 1.99
   (25→50) — scatter of about ±30 % around 1.70, not the tight agreement two
   adjacent short steps suggested. Extrapolating the old ×2.1–2.26 from φ₀ 5 to
   50 %B predicts +0.63 to +0.87 min against a measured +0.246: **too large by
   2.6–3.6×**.

**The law has a ceiling, and it lies between +45 and +70 %B of departure.** At
φ₀ = 75 %B the ×1.70 law predicts +0.83 min and the residual is **−0.084 min** —
it changes sign. That is not a larger version of the same drift: three of the four
bands leave the column during the initial hold, before the ramp reaches the column
head, at k_e = 2.19–2.80, on or below the k ≫ 1 floor the closed form assumes. The
gain law describes the gradient regime, and stops describing anything once the
bands stop eluting on the ramp.

**Where SPEC §10's bar breaks.** Measured: the two-run fit holds to a **+20 %B
departure** from the scouting start (mean |Δt_R| 0.26 % against a 2 % bar) and
fails at **+45 %B** (2.81 %). The crossing is bracketed by measurement, not
measured — the ×1.70 law places it near a +40 %B departure, i.e. a candidate
starting around 45 %B against a scouting pair that started at 5 %B. That figure is
an interpolation between two runs and must not be quoted as a threshold.

**What has not changed: the two datasets still disagree on size.** For the same
5 → 15 %B step the φ₀ excess is 0.0155 min (Validation_2) and 0.046 min (campaign
#27); as an equivalent composition error, 0.16 %B and 0.24 %B; as an equivalent
error in fitted S_e, 0.47 % and 1.04 %. **A single calibrated correction fitted to
one would still be wrong by a factor of 3 on the other.** The 50 and 75 %B runs
were made on Validation_2 alone, so they do not narrow that gap — they widen the
range over which it is untested. §7.1's recommendation to report the hazard rather
than correct for it stands, and stands more firmly.

**Provenance of the two new runs, and a caveat unique to them.** Measured
2026-09-08 at t_G 20, 50 → 95 %B and 75 → 95 %B, 0.5 min initial hold, the scouting
method otherwise unchanged; peak tables from the driver's `08Sep2026 Results.xlsx`
and the `.arw` exports under `validation/Waters Data/` (untracked). No run sheet
preceded either injection, so neither was pre-registered. **The transcribed CSVs
are not in this repository** — they were prepared and then withdrawn at the
driver's instruction on 2026-09-09. Unlike every other number in this document,
these two runs cannot be re-derived from `validation/`.

**The original reading, superseded above [2026-09-02].** Both samples gave **×2.1
per 10 %B of φ₀** — 2.086 and 2.082 for campaign #27's two successive steps, 2.26
for Validation_2's one step — and the residual was *multiplicative* in φ₀: a
**gain** on whatever produces the baseline residual, not an additive term bolted on
top. That was called the most robust quantitative statement in this document and
also its sharpest unexplained fact: no mechanism in §3 has a sensitivity growing
faster than ×1.4 per 10 %B, the timing family pinned at ×1.30. The gain reading
survives at the amended exponent; ×1.4 still does not reach ×1.70, so the §3 gap
is narrowed, not closed.

---

## 7. Consequence for hplcsim [derived]

**Everything in this section is post-v0.1.0.** Per the repo's scope rule, none of
it belongs in an open v0.1 build ticket; it is material for the v0.2 φ₀-freedom
work (`composition-extrapolation.md` §10 / issues #44, #46) and for a new ticket
covering §5's bench runs.

**7.1 Do not fit a correction.** *(Amended 2026-09-09, #134.)* The two datasets
disagree by a factor of 3–4 on the *size* of the residual (§6.3), and they no
longer agree closely on the *ratio* either: at t₀ = 0.525 min the exponent is
×1.70 per 10 %B across φ₀ 5–50 %B with ±30 % scatter between steps, and it
reverses sign entirely by φ₀ = 75 %B. A correction calibrated on either dataset
would be wrong on the other *and* would be extrapolated outside its own measured
range at exactly the starting compositions a user is most likely to try. The
recommendation is unchanged and better supported than when it was written:
predict honestly and annotate.

**7.2 φ₀ is a third axis, distinct from t_G and from s\*, and the repo currently
has no diagnostic for it.** `composition-extrapolation.md` §10.1 establishes that
the t_G question and the composition question collapse into one s\* question, and
recommends a single s\*-bracket diagnostic. **§1.4 shows that is not sufficient**:
campaign #27's run 3 and run 5 have matching s\*, so an s\*-bracket diagnostic
scores them identically, and their residuals differ by a factor of two. Whatever
v0.2 ships must carry a **separate φ₀-distance term**, not folded into s\*.

**7.3 The existing φ₀ guard does not fire here, so it is not the guard needed.**
`composition-extrapolation.md` §10.1(d) proposes flagging peaks whose log₁₀ k₀ at
the candidate φ₀ falls below Guillarme's 2.1 floor. On Validation_2 at
φ₀ = 15 %B, log₁₀ k₀ = 3.21 — a long way above the floor — and the prediction is
still at λ ≈ 0.5. The k_i floor is a real guard against a *different* failure
(the large-k₀ approximation collapsing); it does not cover this one. Campaign #27
run 7 peak 1 does fall below it (log₁₀ k₀ = 1.74), which is consistent with that
peak having the worst λ (1.90) — so keep the guard, but do not treat it as
covering φ₀ generally.

**7.4 An interim rule — withdrawn 2026-09-09 (#134).** This section proposed
telling the user that *"every 10 %B you raise the starting composition above the
scouting runs' roughly doubles the retention error"*, from an expected penalty of
the in-bracket residual × 2.1^(Δφ₀/0.10). **Do not ship that sentence.** E1 has
since been run, and so have held-out starts at φ₀ = 25, 50 and 75 %B: the exponent
is ×1.70 rather than ×2.1, it scatters ±30 % between steps, and at a +70 %B
departure the residual changes sign — so the rule mispredicts by 2.6–3.6× at a
+45 %B departure and gets the *direction* wrong at +70 %B (§6.3).

Per the repository's rule against unevidenced numbers in user-facing warnings, the
defensible statement is the measured bracket rather than an exponent: **the fit is
known to hold to a +20 %B departure from the scouting start, and to fail SPEC §10's
mean bar by a +45 %B departure.** Stated as a departure, with a worked example: a
scouting pair that started at 5 %B supports a candidate starting at 25 %B; a
candidate starting at 50 %B is outside anything the fit has been shown to do. Where
the crossing lies between those two is interpolated, not measured, and should not
appear in warning text.

**7.5 Keep warnings over blocks.** Nothing here justifies refusing a prediction at
raised φ₀. At φ₀ = 15 %B the error is 0.18 % of t_R; it matters because the peaks
are 0.1 min apart, not because the number is large. The right behaviour is to
predict, show λ, and say that the fit was never shown any run starting above
5 %B.

**7.6 For the acceptance bar (#46).** Add E1 (§5.2) as a fourth reality check: its
residual must land near run 3's, not run 4's, if the φ₀ story is real — and either
outcome is informative, so it belongs in the bar whichever way it goes. Predicted
E1 retention times, for the bench sheet: **17.922 / 18.068 / 18.363 / 18.463 min**
(all four peaks in the gradient regime; gradient end at the detector 22.04 min).

**7.7 Settle t₀ first.** §3.4: swapping the fits from t₀ = 0.6 to the driver-read
0.525 min flips the sign of the φ₀ = 5 %B baseline residual (+0.0066 → −0.0066 in
the scan). Any interpretation of a ±0.012 min baseline is hostage to issue #24.
This is a reason to close #24 before, not after, the φ₀ work.

---

## 8. Corrections and additions to existing repository documents

1. **The ticket's dwell argument needs restating** [derived, §2.2]. "∂t_R/∂τ is
   within 0.2 % of 1 at every condition" is true for Validation_2 but **false for
   campaign #27**, where k_e/k₀ reaches 2.2 % (run 5, peak 1) and **8.8 %** (run 7,
   peak 1). On campaign #27 alone the dwell hypothesis does *not* self-refute: it
   closes at δτ ≈ 1.9–2.4 min. What refutes it is that Validation_2 would need
   δτ ≈ 9.7 min. **The correct argument is cross-dataset inconsistency, not
   insensitivity.** Worth fixing wherever the insensitivity form is recorded, so
   nobody re-derives it on #27 and concludes the dwell is wrong after all. (No
   change to V_D = 0.375 mL is proposed or implied.)
2. **`composition-extrapolation.md` §10.1(a)** — the recommendation to generalise
   the bracket diagnostic from t_G to s\* and "**not** add a second, parallel φ
   diagnostic" should be amended. §1.4 is a counter-example produced by this
   repository's own bench data: two runs matched in s\* to 0.1 % whose residuals
   differ 2×. s\* is necessary and not sufficient; φ₀ needs its own term (§7.2).
3. **`composition-extrapolation.md` §10.3, run B/C table** — run 5 as actually
   executed (15→95 %B, t_G 22.2) is **s\*-matched to run 3**, which makes it a far
   more valuable run than the table credits: it is the completed version of the
   "run A" falsification test that §10.3 called the flagship, and its answer is
   that s\*-invariance **fails** by a factor of two in residual. That should be
   recorded next to the run A recommendation.
4. **`validation/PROTOCOL.md` line 19/62 vs the recorded gradient tables**
   [derived, §4.3]. The protocol asks for "≥ 10 column volumes" of
   re-equilibration. With V_M ≈ t₀·F = 0.24 mL, the recorded 3.4–4.0 min holds at
   0.4 mL/min are **5.7–6.7 CV**. The runs on file do not meet the repo's own
   protocol. Given that the re-equilibration end-point (5 vs 15 vs 25 %B) is one of
   the two surviving candidate mechanisms, this is worth fixing before more φ₀ runs
   are collected, not after.

   **Amended 2026-09-09 (#134): eliminated as a *mechanism*; the protocol gap
   stands.** The held-out run at φ₀ = 75 %B settles the end-point question
   directly. `4peaks_run6.csv`'s own note records that re-equilibration
   deliberately ends at 5 %B. Had the column head still been at 5 %B at injection,
   no band could move until the 75 %B front arrived at t_D = 0.9375 min, putting
   the earliest possible elution at 0.9375 + t₀(1 + k) = 2.61 min for Unknown-1.
   It was measured at **1.788 min**, against 1.675 min predicted for a column
   fully equilibrated at 75 %B. The column was at φ₀. At φ₀ = 50 %B the same
   mechanism pushes the wrong way — an under-equilibrated column elutes *later*
   than predicted, and the engine over-predicts there. Re-equilibration is
   therefore not available as an explanation at either start, which leaves §2's
   other survivor alone. The protocol gap itself (5.7–6.7 CV against the stated
   ≥ 10 CV) is untouched by this and still worth closing.
5. **`validation/Validation_2/` has no `method.csv` or protocol note of its own.**
   The four-peak dataset's column, mobile phase, injection volume and diluent are
   inferred from the parent `validation/method.csv`. If they differ in any respect
   the cross-dataset comparison in §6.3 is weaker than stated. Worth one line in
   the folder.
6. **`gradient-elution-math.md`** could usefully record the identity
   1 − ∂t_R/∂τ = k_e/k₀ = 1/[b_e(k₀ − τ/t₀) + 1] and the fact that **the same
   quantity is both the dwell sensitivity and the size of the entire pre-gradient
   migration correction** (§2.1). One number then bounds two error sources at once,
   which is exactly the arithmetic this ticket needed.
7. **`SPEC.md` §6, diagnostic 7 (φ₀ departure) — its message numbers are
   superseded** [derived, §6.3, 2026-09-09]. The specified message quotes *"the
   first 10 %B above the scouting start roughly doubled the retention error on
   both samples (0.42 → 0.82 %… 0.11 → 0.23 %)"* and *"one sample kept doubling
   (1.67 % at +20 %B) and the other flattened (0.26 %)"*. Those figures stand as
   measurements, but the **doubling reading does not survive** the four-peak
   sample's new points: the exponent across φ₀ 5–50 %B is ×1.70 per 10 %B, the
   per-step ratios scatter 1.21–1.99, and the residual reverses sign by
   φ₀ = 75 %B. SPEC's surrounding design is unaffected and correct — no correction
   is fitted, no multiplier is evaluated for the candidate, and the message quotes
   observations rather than a rule — so this is a **numbers refresh inside an
   unchanged diagnostic**, not a redesign. Two further facts belong in the same
   refresh: the strong tier at Δφ₀ ≥ +10 %B is now backed by a run that fails
   SPEC §10's mean bar at a **+45 %B departure with no diagnostic firing at all**
   (s\* on the bracket edge, elution composition inside the scouting window,
   widths within 1 %); and §10 item 5's Rs claim is still scoped to "a raised start
   up to 20 %B". This belongs to the v0.3 amendment (#145), not to any open v0.2
   ticket. Note the constraint in §6.3's provenance paragraph: **the two underlying
   runs are not in the repository**, so the refresh cannot be made from
   `validation/` as it stands.

---

## 9. What I could NOT establish

1. **The direct experiment does not appear to exist.** I found no paper that fits
   an LSS model at one gradient starting composition and reports prediction error
   against held-out runs at *other* starting compositions. Beyaz 2014 (§4.1) is the
   closest and it measures *precision at fixed φ₀*, not accuracy across φ₀.
   Baeza-Baeza 2013's abstract claims the nearest thing and I could not open it.
   **Everything in §2, §3 and §5 is this repository's own arithmetic, not a
   literature measurement.**
2. **I have not identified the mechanism.** §3 and §3.5 eliminate dwell, the
   isocratic hold, t₀, extra-column volume, every s\*-mediated error, all
   curvature/k(φ) model error (for campaign #27), and linear %B miscalibration.
   What survives is a two-item list — column state / re-equilibration end-point,
   and sample-solvent mismatch / volume overload — plus "instrument gradient
   fidelity in a way that depends on the program rather than the instantaneous
   composition", which I could not make precise. **§5's E1 does not identify the
   mechanism either; it only tells you whether the axis is φ₀ or Δφ.** E2 and E3 are
   the mechanism tests and both may come back negative.
3. **Baeza-Baeza et al. 2013 full text** — still unobtained, as in #43 (§9 item 3
   there). It remains the single most on-topic paper: its stated variable is the
   initial modifier concentration. The φ₀ range they tested and their LSS-vs-
   quadratic error split are unknown to me.
4. **I did not model sample-solvent mismatch or volume overload numerically.**
   Rutan et al. 2021 publish closed forms for it (§4.4); implementing them was out
   of scope for this ticket and I do not know the sign, let alone the size, of the
   effect for a 10 µL 50 %B injection into 5 %B vs 15 %B on a 2.1 mm column. This
   is the most under-analysed live candidate in the document.
5. **No RP quantification of preferential solvent adsorption in gradient
   prediction.** The Jandera 2002 citation in §4.5 is normal-phase. I could not
   find an RP equivalent giving a magnitude, so the mechanism class is named but
   unsized.
6. **No primary source for the pressure dependence of k on sub-2 µm columns**
   (§4.6). I did not pursue it hard, having convinced myself it reduces to
   curvature.
7. **Beyaz et al. 2014 was read through the fetch tool's extraction of the PMC
   full text, with verbatim sentences requested and returned**, not by my own
   reading of a PDF end to end. The quotes in §4.1 are marked [verified] on that
   basis; the surrounding figures, tables and their column dimensions I did not
   see. In particular **I do not know their column geometry or gradient times**, so
   the statement in §4.1 that their sensitivity is 2–4× this method's is my
   inference from the numbers, not something they say.
8. **Schellinger 2005/2008, Neue & Kuss 2010, Baeza-Baeza 2013, Rutan et al. 2021
   and Jandera 2002 are abstracts only.** No figure, table or per-compound number
   from any of them is claimed here.
9. **The per-peak "offset vs slope" contrast is weaker evidence than the ticket
   assumed** (§2.4). Validation_2's four peaks are a partly overlapping cluster
   (R_s ≈ 1.6–2.4) whose resolution changes between the two runs, so a 0.0036 min
   spread across four apexes recorded to 0.001 min is not safe ground. The
   qualitative claim survives because campaign #27 reproduces it at ten times the
   size, but I would not weight the 4-peak spread heavily. **This is a partial
   disagreement with the ticket's framing.**
10. **No replicate exists for any held-out condition**, so the repeatability of
    this method is unmeasured and §6 substitutes a literature figure (±0.002 min).
    Every ratio in this document rests on single injections. E4 (§5.5) fixes this
    and should be run first.
11. **The §3.5 translation argument assumes identical t₀, flow, dwell and hold
    between campaign #27's run 3 and run 5**, and that the pump realised
    0.036000 and 0.036036 φ/min faithfully. A 0.3 % flow or t₀ difference would
    account for a large fraction of peak 3's 0.066 min violation. The argument is
    the strongest thing here and it rests on two single injections; E5 exists for
    that reason.
12. **The λ figures in §6.2 use w = 4σ = 1.699·W½**, my convention. Guillarme's
    own w is derived from the maximum plate number and I did not re-open their
    paper for this ticket; a different convention rescales that column uniformly.
13. **Nothing was executed from any third-party project**, no engine, spec or test
    file was modified, and the test suite was not run. The only code run was my own
    arithmetic on `validation/` data, in a scratch directory.

---

## References

All accessed 2026-09-02.

1. **Beyaz, A.; Fan, W.; Carr, P. W.; Schellinger, A. P.** "Instrument parameters
   controlling retention precision in gradient elution reversed-phase liquid
   chromatography." *J. Chromatogr. A* **1371** (2014) 90–105.
   [doi:10.1016/j.chroma.2014.09.085](https://doi.org/10.1016/j.chroma.2014.09.085);
   full text [PMC4388777](https://pmc.ncbi.nlm.nih.gov/articles/PMC4388777/) —
   **the most on-topic source found**: φ₀ dominates φ_f, t_G and F; retention ~5×
   more sensitive to φ₀ than φ_f; 0.001 VF in φ₀ ⇒ 0.02–0.04 min; ±0.002 min
   reproducibility in "a bit more than two column volumes". Read via fetch-tool
   extraction with verbatim quotes (§9 item 7).
2. **Schellinger, A. P.; Stoll, D. R.; Carr, P. W.** "High speed gradient elution
   reversed-phase liquid chromatography." *J. Chromatogr. A* **1064** (2005)
   143–156. [doi:10.1016/j.chroma.2004.12.017](https://doi.org/10.1016/j.chroma.2004.12.017);
   abstract via PubMed [PMID 15739882](https://pubmed.ncbi.nlm.nih.gov/15739882/) —
   repeatability vs full equilibration; ±0.002 min at ≤2 column volumes;
   equilibration "more thermodynamically limited than kinetically controlled".
   **Abstract only.**
3. **Schellinger, A. P.; Stoll, D. R.; Carr, P. W.** "High-speed gradient elution
   reversed-phase liquid chromatography of bases in buffered eluents. Part I.
   Retention repeatability and column re-equilibration." *J. Chromatogr. A*
   **1192** (2008) 41–53.
   [doi:10.1016/j.chroma.2008.01.062](https://doi.org/10.1016/j.chroma.2008.01.062);
   abstract via PubMed [PMID 18294643](https://pubmed.ncbi.nlm.nih.gov/18294643/) —
   two column volumes suffice for "no worse than 0.004 min"; best case
   "0.0004 min". **Abstract only.**
4. **Rutan, S. C.; Jeong, L. N.; Carr, P. W.; Stoll, D. R.; Weber, S. G.**
   "Closed form approximations to predict retention times and peak widths in
   gradient elution under conditions of sample volume overload and sample solvent
   mismatch." *J. Chromatogr. A* **1653** (2021) 462376.
   [doi:10.1016/j.chroma.2021.462376](https://doi.org/10.1016/j.chroma.2021.462376);
   abstract via PubMed [PMID 34293516](https://pubmed.ncbi.nlm.nih.gov/34293516/) —
   four-zone closed forms including the sample-solvent-mismatch zone; "there have
   been errors in expressions reported in the literature". **Abstract only.**
5. **Jandera, P.** "Gradient elution in normal-phase high-performance liquid
   chromatographic systems." *J. Chromatogr. A* **965** (2002) 239–261.
   [doi:10.1016/S0021-9673(01)01323-1](https://doi.org/10.1016/S0021-9673(01)01323-1);
   abstract via PubMed [PMID 12236529](https://pubmed.ncbi.nlm.nih.gov/12236529/) —
   dwell-volume *and* preferential-solvent-adsorption corrections give prediction
   errors under 2–3 %. **Normal phase, abstract only** (§4.5).
6. **Guillarme, D.; Bouvarel, T.; Rouvière, F.; Heinisch, S.** *J. Sep. Sci.*
   **45** (2022) 3276–3285. [PMC9543774](https://pmc.ncbi.nlm.nih.gov/articles/PMC9543774/) —
   s\*, the large-k elution-composition identity, the λ ≤ 0.5 metric and the
   log k_i > 2.1 floor. Read in full for issue #43; reused here on that
   provenance, not re-read.
7. **den Uijl, M. J.; Schoenmakers, P. J.; Schulte, G. K.; Stoll, D. R.;
   van Bommel, M. R.; Pirok, B. W. J.** *J. Chromatogr. A* **1636** (2021) 461780 —
   interpolation errors "mostly less than 0.5 %" (Set X) and "almost all… below
   0.2 %" (Set Y); the five-model zoo. Read in full for #43; reused.
8. **den Uijl, M. J.; Schoenmakers, P. J.; Pirok, B. W. J.; van Bommel, M. R.**
   *J. Sep. Sci.* **44** (2021) 88–114. [PMC7821232](https://pmc.ncbi.nlm.nih.gov/articles/PMC7821232/) —
   the "(well) within 1 %" accuracy bar; LSS "only applicable to the narrow linear
   range". Read in full for #43; reused.
9. **Baeza-Baeza, J. J.; Ortiz-Bolsico, C.; Torres-Lapasió, J. R.;
   García-Álvarez-Coque, M. C.** *J. Chromatogr. A* **1284** (2013) 28–35;
   abstract via PubMed [PMID 23453677](https://pubmed.ncbi.nlm.nih.gov/23453677/) —
   quadratic model accurate to 1–2 % "for a wide range of initial concentrations of
   organic modifier"; LSS limited to "relatively small concentration ranges".
   **Abstract only, full text still unobtained** (§9 item 3).
10. **Neue, U. D.; Kuss, H.-J.** *J. Chromatogr. A* **1217** (2010) 3794–3803;
    abstract via PubMed [PMID 20444458](https://pubmed.ncbi.nlm.nih.gov/20444458/) —
    explicit support for varying "gradient starting composition". **Abstract only.**
11. This repository's own prior work: `docs/research/composition-extrapolation.md`
    (§0 provenance, §1 the window law, §3.2 λ, §4.1 curvature, §5.2 the log k_i
    floor, §7.2 s\*-invariance, §10), `docs/research/gradient-elution-math.md`
    (§2.1–2.3, §4.1–4.3, §7), `src/hplcsim/retention.py`, `validation/method.csv`,
    `validation/PROTOCOL.md`, `validation/run1.csv`–`run7.csv`,
    `validation/runs-combined.csv`, `validation/Validation_2/4peaks_run1..run4.csv`.

---

*Compiled 2026-09-02. Research only — no engine, spec or test file was modified.*
