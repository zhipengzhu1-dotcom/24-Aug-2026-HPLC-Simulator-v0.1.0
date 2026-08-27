# Fitting the Plate Count $N$ from Measured Peak Widths

Research notes for build ticket #23 ("Fit plate count N from measured peak widths").
Companion to `gradient-elution-math.md` (the normative math; cited as *GEM* with its
section numbers). Audience: whoever implements the fit in `src/hplcsim/width.py` and
anyone auditing the numbers.

Every equation and claim is tagged with the source that owns it. Equations I derived
myself are tagged **[derived]** with the derivation shown. Section 7 lists everything I
could **not** verify against a primary source. Conventions follow GEM §0: the engine
works in the natural-log convention ($S_e$, $b_e$); base-10 $S = S_e/\ln 10$ is
display-only. Where the 2.303 slip can enter, it is called out.

---

## 0. Purpose and context from the build

### 0.1 What the engine did before this ticket

As of `main` at `1d7d883`, before #23 landed (the closing note of §6 records what
changed): `width.py` implements GEM §5.1 with the exact half-height constant:

$$\sigma_t = \frac{G\,t_0\,(1+k_e)}{\sqrt N}, \qquad
W_{1/2} = \sqrt{8\ln 2}\;\sigma_t, \qquad W = 4\,\sigma_t$$

with $G(p)$ from GEM §5.2 in the natural-log convention ($p = b_e k_0/(1+k_0)$, settled
against measured widths in GEM §5.4), $G = 1$ outside the gradient regime (GEM §4.1,
§4.2), and $N$ a single global knob defaulting to $N = L/(h\,d_p)$ with $h = 2$ — 31 250
for the lab column (100 mm, 1.6 µm). `peak_width(..., plate_count=None)` stamps
`PeakWidth.plate_count_is_default`; `resolution_table` takes one global `plate_count`;
`Peak` already carries `w_half_run1` / `w_half_run2`; `fit_peak` returns
`FitResult(params, beta, ...)`; $b_e$ lives only in `retention.gradient_steepness`. The
reality test `test_resolution_is_uniformly_optimistic_with_a_defaulted_plate_count` pins
the $R_s$ optimism of the defaulted $N$ to the band (1.1, 1.6) and was written to fail the
day $N$ is fitted. Baseline main: 143 tests, ruff/format/mypy clean.

### 0.2 Numbers already computed with the engine (not re-derived here)

All on `validation/run1–4.csv` under the shipped natural-log $G$ convention
($t_G$ = 15/25/45/60 min; runs 1–2 are the scouting pair, runs 3–4 held out):

| | Unknown-1 | Unknown-2 | Unknown-3 |
|---|---|---|---|
| implied $N$ per run ($t_G$ = 15/25/45/60) | 15299 / 15860 / 15126 / 15023 | 14846 / 16426 / 13827 / 19336 | 25836 / 24064 / 22235 / 26648 |
| fitted $N$ from the scouting pair (geometric mean of the two implied $N$) | **15212** | **14327** | **23968** |
| implied reduced plate height $h = L/(N d_p)$ (default assumes 2) | 4.11 | 4.36 | 2.61 |
| held-out $W_{1/2}$ predicted/measured, $t_G$ = 25 | 1.021 | 1.071 | 1.002 |
| held-out $W_{1/2}$ predicted/measured, $t_G$ = 60 | 0.994 | 1.162 | 1.054 |

- Arithmetic and harmonic means of the two implied $N$ agree with the geometric mean
  within 0.5%; least squares in absolute $\sigma$ differs by 2–5%; run1-only and
  run2-only bracket them. The default $N$ gave $W_{1/2}$ ratios of 0.69–0.92.
- Held-out $R_s$ with fitted $N$ vs measured (from measured $t_R$ and $W_{1/2}$):
  $t_G$ = 25 pairs −4.5% / −4.4% (absolute −1.5 / −4.5 $R_s$ units); $t_G$ = 60 pairs
  −6.5% / −10.0% (absolute −2.4 / −11.6). The earlier handoff's "1.5–11.7 absolute $R_s$
  units" is the correct statement; the ticket's "~1.5–11.7%" is a units slip. With fitted
  $N$ the error is slightly *pessimistic* (ratios 0.955/0.956 at $t_G$ = 25, 0.935/0.900
  at $t_G$ = 60), so the (1.1, 1.6) guard flips as designed.
- Measured $R_s$ at $t_G$ = 25 carries ±9–13% uncertainty (−9.1..+11.1% and −10.0..+12.5%
  pair by pair) because `run3.csv` records $W_{1/2}$ to two decimals (0.05/0.05/0.04); at $t_G$ = 60 (three decimals) it is ±0.5%.
  So at $t_G$ = 25 the fitted-$N$ $R_s$ lies inside the measurement band; at $t_G$ = 60
  the −6.5% / −10% is real.
- SPEC §10's $R_s \pm 0.3$ bar remains unmet: absolute errors 1.5–11.6 ≫ 0.3, and the
  sample sits at $R_s$ 30–116.

---

## 1. What DryLab and its peers do with measured widths

### 1.1 DryLab — Molnár (2002), read in full

Ref. 1 (publisher PDF hosted by the Molnár Institute, extracted with `pdftotext`) makes
four separate statements. Verbatim, with section:

- **§2 Theoretical concepts:** *"Column performance was characterized by the A-value of
  the Knox equation or later by changing the plate number. Individual peak widths and
  peak asymmetry factors were introduced later to be able to adjust DryLab models to the
  real experiments even better and to mimic peak shapes and resolution more precisely
  [14–18]."* (Refs. 14–18 there are 1986 Snyder/Dolan papers, including Quarry, Grob &
  Snyder, *Anal. Chem.* 58 (1986) 907.)
- **§5 Eluent influence:** *"A gradient multi-parameter version was not yet possible at
  that time. One had to use different plate numbers in different areas in DryLab I/mp.
  Later, peak widths were introduced, which allowed a big step forward, namely to use
  gradient runs in the computerized modelling process."*
- **§9 pH influence:** *"In cases of gradient elution, it helped to subdivide the
  chromatogram into three ranges: front, middle and final third and using different plate
  numbers in these regions [88]. The demand for pH modelling in gradient elution could be
  first satisfied after the introduction of measured peak widths as input data and cubic
  spline modelling functions became available."*
- **§16 Accuracy in pH-dependent prediction:** *"In the later stages of the development,
  Snyder found a solution to use measured peak widths to model the peak widths correctly.
  Experimental results were in good agreement with DryLab predictions. The average
  deviation between predicted and experimental retention times of 16 bands was less than
  8 s [89]."*

**Correction to GEM §5.1:** the substance there is right, but the "front/middle/final
third" sentence is Molnár's **§9**, not §16; §16 holds the "Snyder found a solution"
sentence. Refs. [88] (Molnár, *LC·GC Int.* 10 (1997) 32) and [89] (Bilke, Molnár &
Gernet, *J. Chromatogr. A* 729 (1996) 189) are the primary evidence for the transition;
neither was reachable (§7).

**What Molnár does *not* say:** whether DryLab derives one $N$ per peak, one per run, or
a smooth function across the chromatogram. The only hint is *"measured peak widths as
input data and cubic spline modelling functions"* — which suggests something is
interpolated across the chromatogram rather than collapsed to a single column constant;
what is splined is not stated. The numerics are proprietary (GEM §10 item 11); the
vendor page (ref. 12) says only *"DryLab predicts peak width and retention times with
>99% accuracy!"* and describes no mechanism.

**Per-peak width input is confirmed independently.** Tyteca, Veuthey, Desmet, Guillarme
& Fekete (ref. 13, read in full): *"Importing the experimental retention times, peak
widths and asymmetries into a modelling software (e.g. DryLab), a quadratic
two-dimensional model and resolution map can be fitted."* On accuracy: *"An average
retention time prediction error of 1.0% was found for this approach. The average Rs
prediction error, which also includes peak width and peak symmetry errors, was 16.1%."*
The same review maps the field: *"Different software packages have been commercialised,
employing empirical models (DryLab, Osiris) or a combination of ab initio and empirical
models (ChromSword, ACD/Chromgenius)."*

### 1.2 ACD/LC Simulator, ChromSword, Osiris

- **ACD/Labs** — the one reachable technical document is an application note (ref. 14,
  read in full). It models *"retention and peak width of proteins and peptides"*, and
  reports *"The deviation between calculated and experimental peak width is less than 22%
  for both RPC and IEC. This is similar to what previously has been reported in the
  literature for small molecules."* Per-protein width errors under one condition run from
  −6% to +21% — widths are evaluated per compound — and it warns that if the gradient
  does not start at strong retention, *"significant errors in peak width can be expected
  due to poor focusing of the sample."* Whether $N$ is per peak or per column is not
  described.
- **ChromSword** — vendor site (ref. 15) lists products, no technical documentation;
  Chromatography Today articles by Galushko et al. returned HTTP 403 (§7).
- **Osiris (Datalys)** — `datalys.net` does not resolve; the distributor page (ref. 16)
  says only that it simulates chromatograms from at most 12 experiments (§7).

### 1.3 The academic implementations: one $N$ per column

Every peer-reviewed implementation I could read treats $N$ as a single column property
sourced independently of the gradient widths:

- **Wang, Stoll, Schellinger & Carr (2006), ref. 2**, Eq. 15 verbatim: *"$W_{1/2} =
  2.35\,G\,t_0(1+k'_f)/\sqrt N$ (15) where N is the isocratic plate number and G is the
  gradient band compression factor"*; then *"Changes in column efficiency (N) as a
  function of flow rate were accounted by using the van Deemter equation. The
  coefficients of the van Deemter equation (A, B, C) were determined from an experimental
  flow curve obtained for the column used in this study."* Extra-column broadening is
  added as explicit variances (§2.2), not folded into $N$.
- **Guillarme et al. (2022), ref. 3**, Eq. 13 *"$w = 4t_0/\sqrt N \times
  (1+2.3b)/(2.3b)$"* *"where N is the maximum plate number that can be reached with the
  selected column (van Deemter minimum)"* — assumed, with the caveat quoted in §2.1.
- **Hao, Li, Deng et al. (2021), ref. 6**, Eq. 21 *"$W = 4Gt_0(1+k_{\varphi_R})/\sqrt{N_c}$
  ... where $N_c$ is the number of theoretical plates of the column."*
- **Gilar & Neue (2007), ref. 9** (abstract): *"Constants derived from isocratic
  experiments were utilized in a mathematical model based on gradient theory."*

**So:** per-compound *width input* is standard (DryLab; ACD evaluates widths per
compound), but per-compound *$N$* as an explicit fitted parameter is documented nowhere I
could reach, and the academic default is one column $N$, measured isocratically or
assumed. The engine's per-compound $N$ is a design choice with precedent in spirit, not a
citable algorithm.

### 1.4 The pharmacopoeial position: $N$ is an isocratic quantity

USP–NF ⟨621⟩ *Chromatography*, Stage 4 harmonized text official December 1, 2022
(ref. 10, read in full): *"Plate number (N) (number of theoretical plates): A number
indicative of column performance (column efficiency) can only be calculated from data
obtained under either isothermal, isocratic, or isodense conditions, depending on the
technique, as the plate number, using the following equation, the values of $t_R$ and
$W_h$ being expressed in the same units: $N = 5.54\,(t_R/W_h)^2$ ... $W_h$ = peak width
at half-height (h/2). The plate number varies with the component as well as with the
column, the column temperature, the mobile phase, and the retention time."*
Practitioners agree. Kromidas (ref. 17): *"in the ideal case the peak width remains
constant. For this reason, in conjunction with the gradient speaking of a 'plate number'
is not allowed. The plate number, a measure of band broadening, is defined only for
isocratic conditions."* Dolan (ref. 18): *"There isn't an easy way to calculate N for
gradients, so we have to take a different approach"* — use *"peak width or width at
half-height as a measure of column performance in gradient elution."*

Consequence: what ticket #23 fits is **not** a pharmacopoeial plate number. It is the
model parameter $N$ of GEM §5.1 — the isocratic-equivalent efficiency that, with $G$ and
$k_e$, reproduces the measured gradient width. Name it that way in the UI.

---

## 2. Why apparent $N$ differs per compound on one column

USP ⟨621⟩'s *"The plate number varies with the component"* is the regulatory
acknowledgement. Three mechanisms trace to primary sources.

### 2.1 The solute's diffusion coefficient enters the plate height

Wang et al. (ref. 2) take $N$ from the column's van Deemter curve and feed the **solute**
diffusion coefficient separately: *"The solute diffusion coefficient was calculated as a
function of temperature and eluent composition using the Wilke-Chang correlation."*
Gilar & Neue (ref. 9, abstract): *"the maximum peak capacity is achieved at flow rates
between 0.15 and 1.0 mL/min, depending on the molecular weight of the analyte."*
Guillarme et al. (ref. 3): *"Obviously, with proteins, N values are expected to be much
lower at the (non-optimal) flow rate that was used in this work."* The mechanism (the C
term scales with $u\,d_p^2/D_m$, so slower-diffusing solutes lose more plates at a given
flow) is textbook — IMLC 3rd ed. §2.4.1.1 (ref. 19) — but that chapter was not readable
(§7).

### 2.2 Extra-column dispersion adds a variance that is not the column's

Wang et al. Eq. 17 (ref. 2, verbatim): *"$\sigma^2_{total} = \sigma^2_{column} +
\sigma^2_{extra} = \sigma^2_{column} + (\sigma^2_{t,pc} + \sigma^2_d + \sigma^2_\tau)$"*
(post-column tubing, detector cell, time constant), noting *"Peak broadening upstream of
the column under gradient conditions is usually negligible given that the solute is well
retained in the initial eluent."* Gritti & Guiochon (ref. 20, abstract) measured the
consequence on 2.1 mm × sub-2 µm columns: apparent efficiency only 75–85% of the column's
maximum for weakly retained compounds ($k \simeq 1$) but above 95% for $k > 4$.

**[derived] Apparent $N$ with extra-column variance.** With
$\sigma_{col} = G t_0 (1+k_e)/\sqrt{N_{col}}$ and $\sigma^2_{obs} = \sigma^2_{col} +
\sigma^2_{ec}$, the inverse form of §4 returns

$$N_{app} \equiv \frac{G^2 t_0^2 (1+k_e)^2}{\sigma^2_{obs}}
= \frac{N_{col}}{1 + N_{col}\,\sigma^2_{ec}\,/\,\big(G^2 t_0^2 (1+k_e)^2\big)}$$

(i) $N_{app}$ is **instrument-inclusive** — the number that predicts widths on *this*
instrument, which is what the engine wants — and smaller than the column's intrinsic $N$,
consistent with the lab column's $h$ = 2.6–4.4 against the $h$ = 2 default. (ii) The
penalty scales as $1/(1+k_e)^2$: isocratically only early peaks pay it (Gritti &
Guiochon's $k \simeq 1$), but in gradient elution every peak elutes at a small
$k_e \approx 1/b_e$ (GEM §2.3), so **every peak pays it, and steeper gradients pay
more**. That is the finding of Vanderlinden, Broeckhoven, Vanderheyden & Desmet
(ref. 21, abstract, verbatim): *"the steeper the gradient, the more pronounced the
extra-column band broadening losses become ... all peaks in the chromatogram are strongly
affected (around a factor of 1.9 increase in relative peak width) when running steep
gradients, while usually only the first eluting peak was affected in the isocratic mode
or when running shallow gradients."*

Because $k_e$ differs per compound (through $S_e$ in $b_e = t_0\Delta\varphi S_e/t_G$),
$N_{app}$ differs per compound even for identical $N_{col}$ — and since $b_e$ changes
with $t_G$, a compound's $N_{app}$ is not strictly constant across runs. GEM §5.4 found a
0.92% drift over a fourfold $t_G$ range and a best-fit $\sigma_{ec}$ of zero on the lab
instrument, so there the effect sits below the quantisation floor; on an instrument with
larger extra-column volume it would appear as a trend of implied $N$ with $t_G$ — the
diagnostic of §6 item 3.

A tension worth naming: Kromidas (ref. 17) writes that *"a suboptimal hardware (system
dead space), which with isocratic separations leads to broad peaks, is not as noticeable
with gradient separations"* — a statement about how chromatograms look; Vanderlinden et
al. measure the *relative* width penalty and find it larger under steep gradients. The
quantitative primary source is Vanderlinden.

### 2.3 Band compression is itself uncertain at the 10% level

Neue, Marchand & Snyder (ref. 7, abstract): *"Previous reports suggest that peak widths
in linear gradient elution are consistently larger than predicted by theory; however, if
gradient compression is ignored, experiment and theory are in reasonable agreement ... It
is concluded that the concept of gradient compression is correct."* Alvarez-Segura et al.
(ref. 8, abstract): *"The mean compression factor obtained experimentally was higher than
expected, with mean values of 0.98 and 1.02 for the Zorbax and Chromolith columns,
whereas the predicted values were 0.87 and 0.92."* Hao, Liu & Shen (ref. 5) find
LSS-based widths consistently under-predict measured ones, the error falling from ~7% to
~2% under a quadratic solvent-strength model.

Consequence: residual error in $G$ is **absorbed into the fitted $N$** ($N \propto G^2$:
a 5% $G$ error is a 10% $N$ error). Harmless for prediction as long as the same $G$
convention is used to fit and to predict — which is why GEM §5.4 chose the convention by
the *constancy* of implied $N$ across $t_G$ rather than by any absolute width. The fitted
$N$ is conditional on the shipped $G$; say so in the docstring.

### 2.4 The lab data in this light

Unknown-3's $N$ (≈24 000) is 1.6× that of Unknowns 1–2 (≈15 000). Extra-column dispersion
cannot be the reason — Unknown-3 has the *narrowest* peaks (0.025 min at $t_G$ = 15) and
would be penalised most, not least. What remains is intrinsic: a different $D_m$ (§2.1),
a different retention mechanism, or unresolved co-elution broadening Unknowns 1–2 (GEM
§5.4 already flagged their $t_G$ = 45 areas). **Judgement:** this is exactly the case in
which one global $N$ misrepresents the sample and a per-compound $N$ is warranted.

---

## 3. Combining two width measurements into one $N$

### 3.1 Setting

For compound $j$ in scouting run $i \in \{1,2\}$:

$$W_i = c\,a_i\,N^{-1/2}, \qquad c = \sqrt{8\ln 2}, \qquad a_i = G_i\,t_0\,(1+k_{e,i})$$

$a_i$ is fully determined by the retention fit (GEM §2.3, §5.2): in the natural-log
convention $k_e = k_0/\big(b_e(k_0 - \tau/t_0)+1\big)$ and $p = b_e k_0/(1+k_0)$; in
base-10 notation the same numbers read with $2.303\,b$ (GEM §0). The 2.303 slip does not
touch the estimator, but it enters $a_i$ through both $G$ and $k_e$, and **$N \propto
a_i^2$ squares it**: the 10–15% $G$ error of GEM §10 item 5 would have become a 20–30%
$N$ error [derived]. Define the implied plate count of each width $N_i = (c\,a_i/W_i)^2$
and $x_i = W_i/(c\,a_i) = N_i^{-1/2}$.

### 3.2 [derived] Maximum likelihood under each error model

The governing principle — weights inversely proportional to each observation's variance,
unweighted least squares assuming a constant error standard deviation — is NIST/SEMATECH
e-Handbook §4.1.4.3 (ref. 22): *"weights that are inversely proportional to the variance
at each level of the explanatory variables yields the most precise parameter estimates
possible."*

**(a) Constant relative error** ($W_i = c a_i N^{-1/2}(1+\varepsilon_i)$, $\varepsilon_i$
i.i.d. small; exact if multiplicative-lognormal). Then $\ln W_i = \ln(c a_i) -
\tfrac12\ln N + \varepsilon_i$ with constant variance, so ML = ordinary least squares in
$\ln W$:

$$\min_N \sum_i \Big(\ln W_i - \ln(c a_i) + \tfrac12 \ln N\Big)^2
\;\Rightarrow\; \ln\hat N = \frac{1}{n}\sum_i \ln N_i
\;\Rightarrow\; \boxed{\hat N = \Big(\prod_i N_i\Big)^{1/n}}$$

the **geometric mean of the implied $N$** — what the build computed (15212 / 14327 /
23968). Scale-free, invariant to fitting $N$, $\sqrt N$ or $1/\sqrt N$, and consistent
with the statistic GEM §5.4 used to choose the $G$ convention (the CV of implied $N$ is a
log-scale scatter).

**(b) Constant absolute error** ($W_i = c a_i N^{-1/2} + \delta_i$, $\delta_i$ i.i.d.).
ML = ordinary least squares in $W$, linear in $x = N^{-1/2}$:

$$\min_x \sum_i (W_i - c a_i x)^2 \;\Rightarrow\;
\hat x = \frac{\sum_i a_i^2\, x_i}{\sum_i a_i^2}
\;\Rightarrow\; \boxed{\hat N = \Big(\frac{c\sum_i a_i^2}{\sum_i a_i W_i}\Big)^2}$$

an $a_i^2$-weighted mean of the implied $1/\sqrt{N_i}$: the **wider peak dominates**.
With $\beta = 3$ the lab widths give $W_2/W_1$ = 2.64–2.84, so run 2 carries
$(W_2/W_1)^2 \approx$ 7–8× the weight of run 1. This is the "least squares in absolute
$\sigma$" of §0.2, which differed from (a) by 2–5% in $N$.

**(c) Arithmetic mean of implied $N$** is least squares in the variable $N_i$ with equal
weights, i.e. it assumes $N_i$ itself has constant variance — no physical error process
does that. It is harmless only because for two values $N(1\pm r)$ the three means differ
at second order: $\text{AM} = N$, $\text{GM} \approx N(1-r^2/2)$, $\text{HM} = N(1-r^2)$.
With $r$ = 0.02–0.05 (the scouting pairs) the spread is 0.02–0.25% — the build's
"within 0.5%".

**(d) The unifying form.** Weighted least squares in $\ln W$ with $w_i =
1/\mathrm{Var}(\ln W_i)$, $\mathrm{Var}(\ln W_i) \approx s_{rel}^2 + q^2/(12\,W_i^2)$ for
a CDS rounding to a step $q$ (uniform rounding error has variance $q^2/12$). Relative
error dominant → constant $w_i$ → (a); rounding dominant → $w_i \propto W_i^2$ → behaves
like (b). For the lab data ($q$ = 0.001 min) rounding is ±1.5% half-width on a 0.033-min
peak ($\sigma \approx 0.9\%$) and ±0.6% on 0.087 min ($\sigma \approx 0.3\%$); GEM §5.4's
0.92% CV of implied $N$ across four runs bounds the *total* relative error near 1%. So on
this data the two error models are the same size and no estimator beats another by more
than the 2–5% already observed. A width recorded to two decimals (run 3: ±10%) carries
40–100× the variance of a three-decimal one and should be down-weighted or excluded —
which (d) does automatically if entry precision is captured.

### 3.3 Recommendation on the estimator

Use (a) — **least squares in $\ln W$, the geometric mean of the implied $N$** — and
report the ratio $N_1/N_2$ alongside. It is ML for the error process that scales with
width, it is the estimator GEM §5.4's convention choice was made under, and the
alternatives differ by less than any published width-prediction accuracy (Hao 2–7%,
Tyteca 16% on $R_s$, ACD <22%). Upgrade to (d) only if entry precision is ever carried per
width. **Judgement** on the derivations above — no published treatment of estimating $N$
from *two gradient widths* was found (§7).

### 3.4 The pharmacopoeial constant: 5.54, not 5.545

Read directly (refs. 10, 11): USP ⟨621⟩ and JP 2.00 both print $N = 5.54\,(t_R/W_h)^2$,
JP adding *"This test is harmonized with the European Pharmacopoeia and the U. S.
Pharmacopeia"* — so Ph. Eur. 2.2.46 carries the same constant (inferred; the Ph. Eur.
text was not read, §7). The Gaussian-exact constant is $8\ln 2 = 5.5452$; "5.545" in
secondary sources is that value to four figures, and USP's 5.54 makes the pharmacopoeial
$N$ **0.093% lower** than the Gaussian-exact one — negligible, but it is why the engine's
$\sqrt{8\ln 2}$ and a CDS "USP plate count" never agree to the last digit. Shimadzu's
technical page (ref. 23) records the history: the half-height formula was 5.55 until
*"The Japanese Pharmacopoeia 15th revision issued in April 2006 changed the coefficient
from 5.55 to 5.54"*, and *"DAB, BP, and EP pharmacopeias use the Half Peak Height
Method."* USP's resolution is $R_s = 1.18\,(t_{R2}-t_{R1})/(W_{h1}+W_{h2})$ (exact
$\sqrt{8\ln2}/2 = 1.1774$; GEM §6).

---

## 4. The inverse form and the regime caveats

### 4.1 [derived] The inverse

Rearranging Wang Eq. 15 with the exact constant:

$$N = \left(\frac{\sqrt{8\ln 2}\;G\,t_0\,(1+k_e)}{W_{1/2}}\right)^{2}$$

No reachable primary source writes this as an estimator from gradient widths. The
closest: GEM §5.4 itself (which uses exactly this quantity per run as its $G$-convention
statistic); Hao, Liu & Shen (ref. 5), whose Eq. 9 relates $\sigma_t$ to an *"apparent
theoretical plate height"* through the composition history; Alvarez-Segura et al.
(ref. 8), who measure *"efficiency ... in linear gradient elution, where the mean
retention factor is kept constant at each assayed flow"* (abstract only); and Broeckhoven
& Desmet's tutorial (ref. 24), whose abstract promises *"the concepts of plate count and
plate height in this elution mode"* and *"an overview of how these [extra-column]
contributions can be experimentally evaluated"* (paywalled).

### 4.2 [derived] The hold regime reduces to the pharmacopoeial $N$ exactly

If the band leaves before the gradient arrives (GEM §4.1: $k_0 \le \tau/t_0$), then
$G = 1$, $k_e = k_0$ and $t_R = t_0(1+k_0)$, so

$$N = \left(\frac{\sqrt{8\ln2}\,t_0(1+k_0)}{W_{1/2}}\right)^2 = 8\ln 2\left(\frac{t_R}{W_{1/2}}\right)^2$$

— the USP ⟨621⟩ formula with the exact constant. A hold-regime width is the *cleanest*
$N$ the engine can get (no $G$, no $k_e$ model) and a legitimate isocratic plate number in
the pharmacopoeial sense. Such a peak carries no retention information (GEM §4.1), but
its width is still usable — for that compound's $N$ only.

### 4.3 The post-gradient regime is an approximation, not an isocratic measurement

A band still on-column when the ramp ends (GEM §4.2) finishes isocratically at
$\varphi_f$; the engine uses $G = 1$ there. For the *inverse* this is not §4.2's case: the
band was compressed under the ramp and then broadened isocratically, so its width is
neither the compressed nor the isocratic value. The literature treats it as a separate
branch: Hao, Li, Deng et al. (ref. 6) give explicit expressions *"for $B_N = 0$"* (a
final zero-slope segment) for both retention (Eq. 11) and the compression factor
(Eq. 17); Hao, Liu & Shen (ref. 5): *"The effects of pre-elution of the solute in the
initial mobile phase on G, which are attributed to the dwelling time of the system, are
included in the Poppe equation"* — composition history matters to $G$ at both ends. Wang
et al. (ref. 2) simply refused the regime: *"We eliminated conditions requiring
backpressures larger than 380 bar and conditions where the most retained analyte eluted
after time $t_G$."*

**So the isocratic plate count does not "apply directly" to a post-gradient width**;
backing $N$ out of it with $G = 1$ inherits an unquantified model error. **Judgement:**
exclude post-gradient widths from the $N$ fit (or accept them with a low-confidence
stamp), and never let one be the *only* width a compound's $N$ rests on.

---

## 5. Precedence when both a global $N$ and per-peak widths exist

**No primary source documents an override rule.** Neither Molnár (2002), the DryLab
product page, the ACD note, nor the ChromSword/Osiris pages say what happens when a
column plate number and measured widths are both present. Three facts bear on it, none a
rule: (1) DryLab's history (§1.1) is a *replacement* of modelled plate numbers by measured
widths — chronology, not precedence logic; (2) USP ⟨621⟩ (§1.4) defines $N$ only as a
**measured** isocratic quantity and never estimates it from geometry, so the question does
not arise there; (3) SPEC §4 already takes measured-first for $t_0$ (marker time primary;
geometry estimate as a labelled, lower-confidence fallback).

Plainly: the ordering *fitted-from-widths > user-entered global $N$ > geometry default*
is **this project's convention by analogy with its own $t_0$ rule**, not a cited one.

---

## 6. Recommendations for the engine

1. **Fit $N$ per compound** from that compound's two scouting widths as the geometric
   mean of the two implied $N$ (§3.2 a, §3.3). *Sources:* per-compound width input is
   DryLab/ACD practice (§1.1–1.2); per-compound $N$ is physical (§2) and pharmacopoeially
   acknowledged (ref. 10); the estimator is [derived].
2. **Precedence** fitted > global knob > geometry default, stamped per peak
   (`plate_count_source = "fitted" | "global" | "default"`) as `t0_source` is —
   *judgement* by analogy with SPEC §4 (§5). A compound without widths falls back to the
   global knob and is stamped as such.
3. **Report the implied-$N$ ratio** $N_1/N_2$ per compound. GEM §5.4 shows a correctly
   modelled compound holds implied $N$ to ~1% across a fourfold $t_G$ range; a ratio
   beyond roughly ±10% points at a width problem — wrong regime (§4.3), integration,
   co-elution, or extra-column drift with $b_e$ (§2.2) — before it points at the model.
   *Judgement* grounded in GEM §5.4's data.
4. **Regime gating:** hold-regime widths are the cleanest input (§4.2); post-gradient
   widths excluded or low-confidence (§4.3). *Sources:* refs. 2, 5, 6 + [derived].
5. **Precision gating:** a width entered with fewer than three decimals in minutes is
   ±10% on a 0.05-min peak and should be flagged; if entry precision is ever captured,
   use the weighted form (§3.2 d). *Source:* the build's run-3 arithmetic.
6. **Name the quantity honestly** in UI and docstrings: an *apparent,
   instrument-inclusive, $G$-conditional* plate count fitted from gradient widths — not
   the column's intrinsic $N$, not a USP plate number (§1.4, §2.2, §2.3). If a "USP plate
   count" is ever displayed, use 5.54 and label it (§3.4).
7. **Keep the exact constants** ($\sqrt{8\ln2}$; natural-log $p$ in $G$): the 2.303 slip
   now enters $N$ squared (§3.1).
8. **Tests:** the (1.1, 1.6) band flips as designed; the honest replacement bar is what
   §0.2 measured — held-out $W_{1/2}$ ratios 0.99–1.16, $R_s$ inside the ±9–13%
   measurement band at $t_G$ = 25 and within −10% at $t_G$ = 60. SPEC §10's $R_s \pm 0.3$
   stays unmet for GEM §6's reasons (obstacle 2 is the sample). *Ticket's call.*

**Where this lives (ticket #23).** `hplcsim.width.plate_count_from_width` is §4.1's
inverse, routed through `peak_width` at $N = 1$ so the forward and inverse forms cannot
drift; `fit_plate_count` / `FittedPlateCount` implement §3.3's geometric mean, the
`ratio` diagnostic of item 3 and the post-gradient rule of §4.3 (such a width is left out
when the other run's width is usable, and used with a low-confidence stamp only when it
is the peak's only width); `fit_peak`
carries the result as `FitResult.plate_count`; `PeakWidth.plate_count_source` is the
three-way stamp of item 2, and `resolution_table(plate_counts=...)` applies the
precedence of §5. `tests/test_reality.py` pins the §0.2 numbers: widths 0.9–1.25× and
$R_s$ 0.85–1.05× of measured at both held-out conditions, the $t_G$ = 25 residual inside
its measurement band, the $t_G$ = 60 residual outside it, and SPEC §10's ±0.3 as unmet.
Item 5 (precision gating) and the threshold for item 3 are left to the diagnostics
ticket (#20).

---

## 7. What I could NOT verify

1. **Snyder & Dolan, *High-Performance Gradient Elution* (2007)** — paywalled, not read
   (as GEM §10 item 1). Any account of how DryLab-class software turns widths into $N$
   would live there.
2. **Molnár refs. [88] and [89]** (Molnár, *LC·GC Int.* 10 (1997) 32; Bilke, Molnár &
   Gernet, *J. Chromatogr. A* 729 (1996) 189) — the primary evidence for the three-region
   plate numbers and the switch to measured widths; unreachable. Molnár (2002) is read in
   full; only the *mechanism* (per-peak $N$ vs. spline) is undocumented.
3. **ChromSword** — no technical documentation on the vendor site; Chromatography Today
   articles HTTP 403; ResearchGate chapter not attempted. **Osiris** — `datalys.net` does
   not resolve; distributor pages carry no technical detail. **ACD/LC Simulator** — only
   the application note (ref. 14) was readable; it does not describe the width model.
4. **Alvarez-Segura et al. (2019), ref. 8** — abstract only; the repository PDF refused
   or timed out twice. Their gradient-efficiency equation is unverified.
5. **Broeckhoven & Desmet (2022), ref. 24**, and Broeckhoven et al. (2010) kinetic-plot
   paper — ScienceDirect HTTP 403; abstracts only. The VUB portal also returned 403.
6. **Neue (2005), Neue/Marchand/Snyder (2006), Gritti & Guiochon (2010), Gilar & Neue
   (2007), Vanderlinden et al. (2016)** — abstracts only (Europe PMC REST). The Gritti &
   Guiochon percentages in §2.2 are as returned by the fetch summariser from the abstract;
   the other abstracts are quoted verbatim from the JSON.
7. **Poppe, Paanakker & Bronckhorst (1981)** — DOI confirmed via OpenAlex; not read.
8. **IMLC 3rd ed. (ref. 19)** — table of contents only, from the publisher's reading
   sample: §2.4 "Peak Width and the Column Plate Number $N$" (p. 35), §2.4.1.1
   "Band-Broadening Processes That Determine Values of $N$" (p. 39), §3.9 "Extra-Column
   Effects" (p. 131), §9.2.4.3 "Peak Width" (p. 433). No text quoted. **Neue, *HPLC
   Columns* (1997)** — not attempted; paywalled.
9. **LCGC (chromatographyonline.com)** — HTTP 403 again (Stoll's extra-column column);
   no LCGC text is relied on. Dolan's Sepscience column (ref. 18) *was* fetched; its
   quotes are as returned by the fetch tool's reading of the page.
10. **Ph. Eur. 2.2.46** — not read; its 5.54 is inferred from JP's harmonization
    statement and the Shimadzu page. USP ⟨621⟩ and JP 2.00 were read directly.
11. **Wang Eq. 15 typography** — PMC HTML again drops the radical (as GEM §10 item 12);
    $\sqrt N$ is reconstructed from dimensional consistency and from Guillarme Eq. 13 and
    Hao Eq. 21, which render with $\sqrt N$.
12. **Any published estimator of $N$ from two gradient widths** — none found; §3 is
    entirely [derived] on standard weighted-least-squares reasoning (ref. 22).
13. **Kromidas page numbers** — by the sample PDF's running heads (§1.2 quote pp. 3–4;
    §1.4 quote p. 11), not checked against the printed book.

---

## References

"Read" = full text read directly; otherwise abstract/metadata only.

1. **Molnár, I.** "Computerized design of separation strategies by reversed-phase gradient
   elution: development of DryLab software." *J. Chromatogr. A* **965** (2002) 175–194.
   [doi:10.1016/S0021-9673(02)00731-8](https://doi.org/10.1016/S0021-9673(02)00731-8);
   [PDF, Molnár Institute](https://molnar-institute.com/fileadmin/user_upload/Literature/_2002_Molnar_Compu.pdf) — read.
2. **Wang, X.; Stoll, D. R.; Schellinger, A. P.; Carr, P. W.** *Anal. Chem.* **78** (2006)
   3406–3416. [PMC2638764](https://pmc.ncbi.nlm.nih.gov/articles/PMC2638764/) — read.
3. **Guillarme, D.; Bouvarel, T.; Rouvière, F.; Heinisch, S.** *J. Sep. Sci.* **45** (2022)
   3276–3285. [doi:10.1002/jssc.202200161](https://doi.org/10.1002/jssc.202200161) — read.
4. **Neue, U. D.** "Theory of peak capacity in gradient elution." *J. Chromatogr. A* **1079**
   (2005) 153–161. [doi:10.1016/j.chroma.2005.03.008](https://doi.org/10.1016/j.chroma.2005.03.008).
5. **Hao, W.; Liu, L.; Shen, Q.** *Se Pu* **39** (2021) 10–14.
   [PMC9274839](https://pmc.ncbi.nlm.nih.gov/articles/PMC9274839/) — read (English abstract;
   Chinese body machine-extracted).
6. **Hao, W.; Li, B.; Deng, Y.; Chen, Q.; Liu, L.; Shen, Q.** "Computer aided optimization of
   multilinear gradient elution in liquid chromatography." *J. Chromatogr. A* **1635** (2021)
   461754. [doi:10.1016/j.chroma.2020.461754](https://doi.org/10.1016/j.chroma.2020.461754);
   [PDF, Molnár Institute](https://molnar-institute.com/fileadmin/user_upload/Literature/_2021_Hao_Computer_aided_optimization.pdf) — read.
7. **Neue, U. D.; Marchand, D. H.; Snyder, L. R.** "Peak compression in reversed-phase
   gradient elution." *J. Chromatogr. A* **1111** (2006) 32–39.
   [doi:10.1016/j.chroma.2006.01.104](https://doi.org/10.1016/j.chroma.2006.01.104).
8. **Alvarez-Segura, T.; Cabo-Calvet, E.; Baeza-Baeza, J. J.; García-Álvarez-Coque, M. C.**
   "Study of the column efficiency using gradient elution based on Van Deemter plots."
   *J. Chromatogr. A* **1584** (2019) 126–134.
   [doi:10.1016/j.chroma.2018.11.042](https://doi.org/10.1016/j.chroma.2018.11.042).
9. **Gilar, M.; Neue, U. D.** *J. Chromatogr. A* **1169** (2007) 139–150.
   [doi:10.1016/j.chroma.2007.09.005](https://doi.org/10.1016/j.chroma.2007.09.005).
10. **USP–NF ⟨621⟩ Chromatography**, Stage 4 Harmonization, official 2022-12-01.
    [USP PDF](https://www.usp.org/sites/default/files/usp/document/harmonization/gen-chapter/harmonization-november-2021-m99380.pdf) — read.
11. **Japanese Pharmacopoeia 2.00 Chromatography** (harmonized; PMDA English PDF).
    [pmda.go.jp](https://www.pmda.go.jp/files/000242735.pdf) — read.
12. **Molnár Institute, DryLab page.** [molnar-institute.com/drylab/](https://molnar-institute.com/drylab/) — read.
13. **Tyteca, E.; Veuthey, J.-L.; Desmet, G.; Guillarme, D.; Fekete, S.** *Analyst* (2016).
    [doi:10.1039/c6an01520d](https://doi.org/10.1039/c6an01520d);
    [PDF, Molnár Institute](https://molnar-institute.com/fileadmin/user_upload/_2016_Tyteca_Computer.pdf) — read
    (advance-article copy; volume/pages absent).
14. **Petersson, P.; Munch, J.; Euerby, M. R.; Vazhentsev, A.; McBrien, M.; Bhal, S. K.; Kassam, K.**
    "Adaption of Retention Models to Allow Optimization of Peptide and Protein Separations."
    ACD/Labs application note.
    [PDF](https://theanalyticalscientist.com/media/u5whow2y/acdlabs-app-note-6-supplied.pdf);
    [ACD/Labs page](https://www.acdlabs.com/resource/adaption-of-retention-models-to-allow-optimization-of-peptide-and-protein-separations/) — read.
15. **ChromSword** — [chromsword.com](https://www.chromsword.com/) — read; no technical docs.
16. **Osiris (Datalys)** — distributor page
    [cjlab.fr](https://www.cjlab.fr/produit/osiris-logiciel-doptimisation-pour-chromatographie-en-phase-liquide/) — read.
17. **Kromidas, S.** "Aspects of Gradient Optimization," Ch. 1 of *Gradient HPLC for
    Practitioners*, Wiley-VCH (2019), ISBN 978-3-527-34408-6.
    [Publisher sample chapter](https://application.wiley-vch.de/books/sample/352734408X_c01.pdf) — read.
18. **Dolan, J. W.** "HPLC Solutions #116: Column Efficiency for System Suitability with
    Gradients." [sepscience.com](https://www.sepscience.com/hplc-solutions-116-column-efficiency-for-system-suitability-with-gradients-6949) — fetched.
19. **Snyder, L. R.; Kirkland, J. J.; Dolan, J. W.** *Introduction to Modern Liquid
    Chromatography*, 3rd ed., Wiley (2010), ISBN 978-0-470-16754-0.
    [Reading sample (front matter)](https://content.e-bookshelf.de/media/reading/L-574079-2884cc3b11.pdf) — TOC only.
20. **Gritti, F.; Guiochon, G.** *J. Chromatogr. A* **1217** (2010) 7677–7689.
    [doi:10.1016/j.chroma.2010.10.016](https://doi.org/10.1016/j.chroma.2010.10.016).
21. **Vanderlinden, K.; Broeckhoven, K.; Vanderheyden, Y.; Desmet, G.** *J. Chromatogr. A*
    **1442** (2016) 73–82. [doi:10.1016/j.chroma.2016.03.016](https://doi.org/10.1016/j.chroma.2016.03.016).
22. **NIST/SEMATECH e-Handbook of Statistical Methods**, §4.1.4.3 "Weighted Least Squares
    Regression." [itl.nist.gov](https://www.itl.nist.gov/div898/handbook/pmd/section1/pmd143.htm) — read.
23. **Shimadzu, "Formula for Calculating the Number of Theoretical Plates."**
    [shimadzu.com](https://www.shimadzu.com/an/service-support/technical-support/liquid-chromatography/analysis-results/theoretical.html) — read.
24. **Broeckhoven, K.; Desmet, G.** *Anal. Chim. Acta* **1218** (2022) 339962.
    [doi:10.1016/j.aca.2022.339962](https://doi.org/10.1016/j.aca.2022.339962).
25. **Poppe, H.; Paanakker, J. E.; Bronckhorst, M.** *J. Chromatogr.* **204** (1981) 77–84.
    [doi:10.1016/S0021-9673(00)81641-6](https://doi.org/10.1016/S0021-9673(00)81641-6) — not read.
26. **Snyder, L. R.; Dolan, J. W.** *High-Performance Gradient Elution*, Wiley (2007),
    ISBN 978-0-471-70646-5 — not read.

---

*Compiled 2026-08-27 for build ticket #23. Branch: main (research only; no engine changes).*
