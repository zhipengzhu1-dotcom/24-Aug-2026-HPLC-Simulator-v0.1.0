# Plate Count N Across Flow Rate — Can One Scouting-Flow Fit Say Anything at a Different Flow?

Research notes for issue #138. Companion to `plate-count-from-widths.md` (the fit this
document interrogates) and `gradient-elution-math.md` §5 (the width model, `_REDUCED_PLATE_HEIGHT`,
the G calibration). Conventions: minutes, mL, mm, µm — CLAUDE.md's units rule. "SPP" =
superficially porous particle = core-shell = solid-core, used interchangeably below as the
sources use them.

---

## 1. Question

`fit_plate_count` in `src/hplcsim/width.py` fits a per-peak plate count N from that peak's
measured scouting widths (`plate_count_from_width`, inverting the σ_t = G·t0·(1+k_e)/√N model)
at whatever flow the scouting pair actually ran — the lab dataset's is 0.4 mL/min, on a
2.1 × 100 mm, 1.6 µm solid-core Waters CORTECS column. That fit says nothing about flow: it is
a single number, and nothing in `width.py` or the gradient-elution-math research doc encodes
how N should move if a candidate method changes the flow rate away from 0.4 mL/min. If a
future ticket wants to predict N (and hence W½ and Rs) at a different flow from this one
scouting-flow fit, it needs either (a) a published H(u) curve shape anchored at the one
measured point, or (b) a stated, evidenced decision to hold N constant and flag the output as
flow-uncorrected. This document surveys the primary literature on both options, for sub-2 µm
solid-core/superficially-porous particles specifically, and quantifies extra-column
band-broadening on a 2.1 mm i.d. column, which is the other reason a "measured N" at 0.4
mL/min is not simply the column's intrinsic N.

---

## 2. Sources table

| Author(s)/Year | Venue | What it establishes | Link/DOI |
|---|---|---|---|
| Gritti, F.; Shiner, S. J.; Fairchild, J. N.; Guiochon, G. (2014) | *J. Chromatogr. A* **1334**, 30–43 | Kinetic performance of a prototype 2.1×100 mm, 1.6 µm SPP column (the CORTECS-precursor format): eddy dispersion controls ≥66% of overall HETP beyond the optimum velocity; intrinsic efficiency >400,000 plates/m. **Abstract only** — paywalled (403 on ScienceDirect; consistent with `dead-time-from-geometry.md` §3.4, which flagged this exact paper as unread). | [doi:10.1016/j.chroma.2014.01.065](https://doi.org/10.1016/j.chroma.2014.01.065) |
| Gritti, F.; Shiner, S.; Fairchild, J. N.; Guiochon, G. (2014) | *J. Sep. Sci.*, DOI below | **The single most directly relevant number found**: three production 2.1×100 mm columns packed with 1.6 µm superficially porous **CORTECS-C18+** particles, measured h_min = 1.42, 1.57, 1.75 (naphthalene, ACN/water 75:25, 295 K, I-Class ACQUITY); average intrinsic efficiency 395,000 plates/m. **Abstract only** — Wiley returned HTTP 403 (as `dead-time-from-geometry.md` §3.4 already found). | [doi:10.1002/jssc.201400703](https://doi.org/10.1002/jssc.201400703) |
| Gritti, F.; Guiochon, G. (2014) | *J. Chromatogr. A* **1333**, 60–69, "Rapid development of core–shell column technology" | 31 narrow- and wide-bore columns, four SPP brands, particle sizes 4.6→1.3 µm: optimum reduced plate height h_min rises slightly from 1.6 to 1.9 as particle size falls from 4.6 to 1.3 µm. Measured on an Agilent 1290 Infinity with extra-column volume variance **13.6 ± 0.3 µL²** (an optimized, low-dispersion instrument, not the driver's Acquity H-Class). **Abstract only.** | [doi:10.1016/j.chroma.2014.01.061](https://doi.org/10.1016/j.chroma.2014.01.061) |
| Gritti, F.; Guiochon, G. (2014) | *J. Chromatogr. A* **1327**, 49–56, "Accurate measurements of the true column efficiency and of the instrument band broadening contributions" | A protocol for separating true column HETP from instrument (extra-column) variance, validated specifically on 2.1×100 mm columns packed with 2.7 µm Halo-ES-C18 **and a 1.6 µm core-shell prototype** (same family as CORTECS); column HETP reproducible within 5% across different instruments once the instrument term is removed — i.e., without removing it, cross-instrument HETP is *not* reproducible. **Abstract only.** | [doi:10.1016/j.chroma.2013.12.003](https://doi.org/10.1016/j.chroma.2013.12.003) |
| Gritti, F.; Guiochon, G. (2012) | *J. Chromatogr. A* **1252**, 31–44, "Repeatability of the efficiency of columns packed with sub-3 µm core–shell particles. Part I" | 2.6 µm Kinetex-C18, twelve columns, **both 2.1×100 mm and 4.6×100 mm formats**: at the highest reduced velocity tested, RSD of the eddy-dispersion term was ~7% (small molecules) / ~3% (insulin) for the 2.1 mm i.d. columns vs. ~15% / ~5% for 4.6 mm i.d. — column-to-column packing variability, not extra-column dispersion, but shows the 2.1 mm format is *more* reproducible in eddy term here (opposite direction from the extra-column story). **Abstract only.** | [doi:10.1016/j.chroma.2012.05.072](https://doi.org/10.1016/j.chroma.2012.05.072) |
| Broeckhoven, K.; Cabooter, D.; Desmet, G. (2013) | *J. Pharm. Anal.* **3**, 313–323 | **Read in full (open access, PMC).** Van Deemter form (A/B/C, longitudinal diffusion + mobile/stationary mass transfer); measured h_min ≈ 1.4 (reduced) for a 5 µm SPP column (butyrophenone, k≈6.2) vs. h_min = 2.0 for 5 µm FPP; states SPP particles "routinely achieve" reduced h of 1.5–1.8 (citing other studies within, 1.1–1.3 in some); B-term ~25–50% lower and A-term substantially lower for SPP vs. FPP, C-term difference marginal; SPP column tolerates 3–4× its own optimum velocity while still matching or beating the FPP column *at the FPP's own optimum* (h(SPP, 3–4×ν_opt) ≤ h_min(FPP) = 2.0, i.e. ≤1.43× its own h_min — see §4). Extra-column contribution: <1% for 4.6 mm i.d. columns, **up to 5% for the 2.1 mm i.d. column (2.7 µm SPP)**. Not CORTECS/1.6 µm; nearest-available fully-read primary source on the SPP shape. | [doi:10.1016/j.jpha.2012.12.006](https://doi.org/10.1016/j.jpha.2012.12.006), [PMC5760962](https://pmc.ncbi.nlm.nih.gov/articles/PMC5760962/) |
| Fekete, S.; Fekete, J. (2011) | *J. Chromatogr. A* **1218** (31), 5286–5291 | Title and scope confirmed by abstract: quantifies extra-column peak-variance impact, as a function of flow rate, on 5 cm long narrow-bore (2–2.1 mm) columns packed with core-shell, sub-2 µm FPP, and monolith particles, across several commercial LC systems, via kinetic plots. **No numeric values extractable from the abstract alone** — full text paywalled, not fetchable here. | [doi:10.1016/j.chroma.2011.06.045](https://doi.org/10.1016/j.chroma.2011.06.045) |
| Fekete, S.; Oláh, E.; Fekete, J. (2012) | *J. Chromatogr. A* **1228**, 57–71, "Fast liquid chromatography: The domination of core-shell and very fine particles" | Review (142 references) of core-shell/fine-particle fast-LC kinetics. Confirmed to exist and its scope; **no numeric coefficients extractable from the abstract**, full text paywalled. | [doi:10.1016/j.chroma.2011.09.050](https://doi.org/10.1016/j.chroma.2011.09.050) |
| DeStefano, J. J.; Schuster, S. A.; Lawhorn, J. M.; Kirkland, J. J. (2012) | *J. Chromatogr. A* **1258**, 76–83 | Performance characteristics of SPP particles (2.7 µm Fused-Core matches sub-2 µm FPP efficiency at ~half the backpressure); reduced plate height varies with particle diameter and shell thickness. **Abstract only, qualitative** — no numeric h_min/A/B/C extractable. | [doi:10.1016/j.chroma.2012.08.036](https://doi.org/10.1016/j.chroma.2012.08.036) |
| Cabooter, D.; Fanigliulo, A.; Bellazzi, G.; Allieri, B.; Rottigni, A.; Desmet, G. (2010) | *J. Chromatogr. A* **1217** (44), 7074–7081 | Links particle-size-distribution narrowness of commercial SPP packings to A-term and h_min via a near-linear trend, across several commercial FPP/SPP brands. **No numeric A/B/C table extractable from the abstract.** | [doi:10.1016/j.chroma.2010.09.008](https://doi.org/10.1016/j.chroma.2010.09.008) |
| Broeckhoven, K.; Desmet, G. (2021) | *J. Sep. Sci.* **44** (1), 323–339, "Methods to determine the kinetic performance limit of contemporary chromatographic techniques" | Review of the kinetic-plot method (efficiency-vs-flow-rate data combined with column permeability) for determining the time/efficiency performance limit across LC/GC/SFC. Confirms the *methodology* the question's point 4 is really asking about (turning one H(u) measurement set into a performance prediction) exists and is an active review topic; **no CORTECS-specific or 1.6 µm-specific numbers found in the abstract**, full text paywalled. | [doi:10.1002/jssc.202000779](https://doi.org/10.1002/jssc.202000779) |
| van Deemter, J. J.; Zuiderweg, F. J.; Klinkenberg, A. (1956) | *Chem. Eng. Sci.* **5** (6), 271–289 | The original van Deemter equation, H = A + B/u + Cu. Classic citation for the functional form used throughout below; not fetched (pre-DOI-era paywalled scan), the equation itself is standard and reproduced from secondary textbook restatement. | [doi:10.1016/0009-2509(56)80003-1](https://doi.org/10.1016/0009-2509(56)80003-1) |
| Knox, J. H. (1977) | *J. Chromatogr. Sci.* **15** (9), 352–364, "Practical aspects of LC theory" | The reduced Knox equation, h = Aν^(1/3) + B/ν + Cν. **Not fetchable** — no open-access copy found (checked Europe PMC, empty result; Unpaywall: closed, no repository copy). Equation form only, taken from its standard restatement in later open sources (e.g. the Broeckhoven/Cabooter/Desmet 2013 paper above, which uses the equivalent van Deemter form). | [doi:10.1093/chromsci/15.9.352](https://doi.org/10.1093/chromsci/15.9.352) — not fetchable |
| Horváth, S.; Gritti, F.; Kormány, R.; Horváth, K. (2019) | *Molecules* **24**, 2849 | Core-shell porosity structure (already cited in this repo's `dead-time-from-geometry.md` §2.3); re-cited here only for the ε_T = 0.52 core-shell porosity convention used in §4's u calculation. Read in full, open access. | [doi:10.3390/molecules24152849](https://doi.org/10.3390/molecules24152849), [PMC6695945](https://pmc.ncbi.nlm.nih.gov/articles/PMC6695945/) |
| Waters Corporation, WKB51838 | support.waters.com KB article | "What is the difference between BEH C18 and CORTECS C18 packings?" — states pore diameter (BEH 130 Å vs. CORTECS 90 Å) but **no van Deemter, h_min, or efficiency numbers**. Read directly. | [support.waters.com/KB_Chem/Columns/WKB51838](https://support.waters.com/KB_Chem/Columns/WKB51838_What_is_the_difference_between_BEH_C18_and_CORTECS_C18_packings) |
| Waters CORTECS product/technology pages | waters.com | Attempted directly (`waters.com/nextgen/.../cortecs-columns.html`); **timed out on every fetch attempt** in this session and could not be read. No CORTECS application note or white paper with a van Deemter curve or numeric h_min/ν_opt was located (via Bing and DuckDuckGo proxy searches, WebSearch itself being unavailable this session — see §7). | not fetchable this session |

---

## 3. H(u) forms

**van Deemter** (van Deemter, Zuiderweg & Klinkenberg 1956):

$$H = A + \frac{B}{u} + C\,u$$

with $H$ the plate height (length), $u$ the (linear) mobile-phase velocity, $A$ the eddy-dispersion
term, $B$ the longitudinal-diffusion term, $C$ the (combined mobile + stationary phase) mass-transfer
resistance term.

**Knox** (reduced form, Knox 1977 — equation form only; not itself fetched, see sources table):

$$h = A\,\nu^{1/3} + \frac{B}{\nu} + C\,\nu, \qquad \nu = \frac{u\,d_p}{D_m}, \qquad h = \frac{H}{d_p}$$

with $\nu$ the reduced velocity and $h$ the reduced plate height. $A\nu^{1/3}$ rather than a flat $A$
is Knox's refinement for the velocity-dependence of eddy dispersion at low $\nu$; at the $\nu$ most
methods run at, both forms behave similarly and the literature below mixes both without incident.

**Reduced coefficients found, by source and particle** (h_min / ν_opt where minimizing $h(\nu)=A+B/\nu+C\nu$
gives the standard [derived] identities $h_{\min} = A + 2\sqrt{BC}$, $\nu_{opt} = \sqrt{B/C}$ — none of
the sources below report full $A,B,C$ triples for a sub-2 µm core-shell particle; every number found is
an $h_{\min}$-only figure):

| Particle | Format | h_min | Source | CORTECS-specific? |
|---|---|---|---|---|
| **1.6 µm SPP, CORTECS-C18+** | 2.1×100 mm, 3 production columns | **1.42, 1.57, 1.75** (naphthalene, ACN/water 75:25, 295 K) | Gritti, Shiner, Fairchild, Guiochon, *J. Sep. Sci.* (2014) | **Yes — exact particle and column format** |
| SPP, 4 brands, 4.6→1.3 µm | narrow/wide-bore, various | 1.6 (at 4.6 µm) rising to 1.9 (at 1.3 µm) | Gritti & Guiochon, *J. Chromatogr. A* **1333** (2014) 60–69 | No — brackets 1.6 µm between two other sizes, not measured directly |
| 5 µm SPP (unnamed brand) | not stated (4.6 mm inferred) | ≈1.4 (butyrophenone, k≈6.2) | Broeckhoven, Cabooter, Desmet (2013) | No — 5 µm, not sub-2 µm |
| 5 µm FPP (comparison) | same paper | 2.0 | Broeckhoven, Cabooter, Desmet (2013) | No |
| SPP, general (multiple studies cited within) | various | "routinely 1.5–1.8", some as low as 1.1–1.3 | Broeckhoven, Cabooter, Desmet (2013), citing other work | No |

**No source found reports a numeric A, B, C triple, or a numeric ν_opt or u_opt, for the CORTECS
1.6 µm particle or for any sub-2 µm core-shell particle.** Every accessible source states h_min alone
(the value at whatever velocity that source ran its optimum-velocity experiment, itself not stated in
mL/min or mm/s in any of the abstracts read). This is a real gap, not a rounding-off: without A, B and
C (or equivalently h_min *and* ν_opt), the shape of h(ν) away from the minimum cannot be reconstructed
numerically — only bounded, qualitatively, by what the sources say about the curve's flatness (§4, §6a).
The two full papers most likely to contain the missing numbers (Gritti, Shiner, Fairchild & Guiochon,
*J. Chromatogr. A* **1334** (2014) 30–43, and the *J. Sep. Sci.* companion) were both confirmed
paywalled in this repo's own prior research (`dead-time-from-geometry.md` §3.4) and again in this
session (HTTP 403 on ScienceDirect and Wiley).

---

## 4. Worked numeric estimate

### 4.1 Linear velocity at each candidate flow

Using this project's own established core-shell total-porosity convention, ε_T = 0.52
(`docs/research/dead-time-from-geometry.md` §3.1–3.2, itself resting on Broeckhoven, Cabooter &
Desmet's measured 0.460 for a 2.7 µm SPP column and Waters' own 0.49 SPP constant), and the
2.1×100 mm column cross-section already used in that doc ($A_{col} = \pi(0.105\text{ cm})^2 =
0.034636\text{ cm}^2$):

$$u = \frac{F}{A_{col}\cdot\varepsilon_T}$$

| F (mL/min) | u (mm/s) | F / F(0.4) |
|---|---|---|
| 0.2 | 1.85 | 0.50 |
| 0.3 | 2.78 | 0.75 |
| 0.4 (scouting) | 3.70 | 1.00 |
| 0.5 | 4.63 | 1.25 |
| 0.6 | 5.55 | 1.50 |

**[derived]**, computed with the arithmetic shown; not itself sourced beyond the ε_T convention.
Because ν = u·dp/Dm and dp, Dm are both fixed for one column and one analyte, ν scales exactly
with F — the ratio column above is also the ratio of reduced velocities, independent of Dm's actual
value. This is useful because it means the *shape* argument in §4.2 needs no diffusion-coefficient
estimate to state the ±50% excursion in reduced-velocity terms; it only needs one to place ν(0.4)
on an absolute h(ν) curve, which §3 already flagged as unavailable.

**What could not be checked**: whether 0.4 mL/min (ν = ν(0.4)) sits at, above, or below this
column's actual ν_opt. A rough plausibility check using a generic literature small-molecule
diffusion coefficient (order 1×10⁻⁵ cm²/s, not sourced to a CORTECS- or naphthalene-specific
measurement on this instrument) gives ν(0.4) ≈ 6, which would sit near or modestly above a
typical FPP/SPP ν_opt (commonly quoted in the 3–6 range in review-level literature) — but this
placement rests on an unsourced Dm and is not asserted as fact, only offered as a plausibility
note.

### 4.2 What the literature bounds, without a fitted curve

The clean quantitative curve fit is not available (§3), but two primary numbers bound the
question of how *bad* an extrapolation by ±50% flow could be:

- **The largest evidenced degradation, at a much larger excursion.** Broeckhoven, Cabooter &
  Desmet (2013): a 5 µm SPP column at 3–4× its own optimum velocity still matches or beats a 5
  µm FPP column at the FPP's *own* optimum, i.e. $h(\text{SPP},\,3\text{–}4\times\nu_{opt}) \le
  h_{\min}(\text{FPP}) = 2.0$, against the SPP's own $h_{\min} \approx 1.4$. That bounds the SPP
  column's own degradation at 3–4× its optimum velocity to **at most a 43% rise in h** ($2.0/1.4 =
  1.43$) — for a 5 µm particle, not 1.6 µm, and for a 3–4× excursion, not the ±50% (1.5×/0.5×) this
  question asks about. It is the only quantified upper bound found in the accessible literature on
  how far a core-shell van Deemter curve can be pushed before serious efficiency loss.
- **Confirmation the curve is genuinely flatter than fully-porous, mechanistically.**
  Broeckhoven, Cabooter & Desmet (2013) again: the B-term (longitudinal diffusion) is 25–50% lower
  for SPP vs. FPP and the A-term (eddy dispersion) is "substantially reduced," with only the C-term
  (mass-transfer resistance) comparable — meaning *both* directions away from ν_opt (lower flow →
  B-term-dominated; higher flow → C-term-dominated) are less penalized for a core-shell particle
  than for a fully-porous one of the same size. Gritti, Shiner, Fairchild & Guiochon (2014, *J.
  Chromatogr. A* **1334**) adds, for the actual 1.6 µm prototype: eddy dispersion (the flow-independent
  A-term) already controls ≥66% of HETP beyond the optimum velocity — meaning the flow-dependent
  terms (B/ν and Cν together) are ≤34% of H there, on this exact particle.

**A ±50% flow change is a much smaller perturbation than the 3–4× excursion the 43%-h-rise bound
was measured on.** By the shape of any van Deemter/Knox curve (both terms in $B/\nu + C\nu$ are
monotonic and the curve is convex), the h-increase at ±50% must be smaller than at ±(3–4)×
ν_opt — but *how much* smaller is not stated by any source found; nothing here converts "43% at
3–4×" into a number at 1.5×. **This is the honest limit of what the literature search
supports**: qualitatively, ±50% should cost markedly less than 43% in h (and hence in N), because
core-shell curves are reported flat over a wide range and because 1.5× is a much smaller multiple
than 3–4×; quantitatively, no source gives the number.

### 4.3 Propagation to W½ and Rs, shown parametrically

$W_{1/2} \propto 1/\sqrt N$ and, for two adjacent peaks whose N is assumed to move together and
whose spacing/width sum otherwise holds, $R_s \propto \sqrt N$ (`gradient-elution-math.md` §6).
If N changes by a fraction $x$ (i.e. $N_{new} = N(1-x)$ for a flow-induced increase in h, since
$N = L/(h\,d_p)$):

$$\frac{W_{1/2,new}}{W_{1/2}} = \frac{1}{\sqrt{1-x}}, \qquad \frac{R_{s,new}}{R_s} = \sqrt{1-x}$$

Illustrative brackets (not a specific literature-sourced prediction — $x$ is not known for a
±50% flow change, per §4.2), anchored at $R_s = 1.75$ (SPEC §10's near-critical-pair figure):

| x (hypothetical N loss) | W½ multiplier | Rs at 1.75 | ΔRs |
|---|---|---|---|
| 5% | 1.026× | 1.706 | −0.045 |
| 10% | 1.054× | 1.660 | −0.090 |
| 20% | 1.118× | 1.565 | −0.185 |
| 30% | 1.195× | 1.463 | −0.287 |
| 43% (the sourced 3–4×-ν_opt bound, §4.2) | 1.325× | 1.321 | −0.429 |

**Reading this table honestly**: if the true N-loss at ±50% flow turns out to be in the
single-digit-to-teens percent — which the qualitative flatness evidence in §4.2 makes plausible
but does not establish — the resulting Rs miss stays comfortably inside SPEC's ±0.3 bar. If it
turns out to be anywhere near the 30–43% range that the literature *does* evidence, but only for
a 3–4× excursion on a 5 µm (not 1.6 µm) particle, the ±0.3 bar would be breached. **No source
in this search distinguishes between these two possibilities for a ±50% flow change on a 1.6 µm
CORTECS column.**

---

## 5. Extra-column caveat, sized for 2.1 mm i.d.

Two primary numbers, both already in the sources table, size this directly:

- Broeckhoven, Cabooter & Desmet (2013), read in full: **extra-column contribution to band
  broadening was <1% for their 4.6 mm i.d. columns and up to 5% for their 2.1 mm i.d. column**
  (2.7 µm SPP) — a fivefold-plus jump from widening the bore alone, on the same instrument.
- Gritti & Guiochon (2014, *J. Chromatogr. A* **1333**): an optimized Agilent 1290 Infinity has
  extra-column volume variance $\sigma_{ec}^2 = 13.6 \pm 0.3\ \mu\text{L}^2$ — a state-of-the-art,
  low-dispersion instrument, **not** the driver's Acquity H-Class, whose own $\sigma_{ec}^2$ was
  not found anywhere in this search (a real gap; see §7).

**[derived]**, using that one quantified $\sigma_{ec}^2$ and the project's own width model
($\sigma_t = t0(1+k_e)/\sqrt N$, $G=1$ for an isocratic estimate) at $t0 = 0.525$ min, $N =
15{,}000$ (order of the fitted Unknown-1 value in `plate-count-from-widths.md` §0.2), converting
$\sigma_{ec}^2$ from volume to time via $\sigma_{ec,t} = \sigma_{ec,V}/F$:

| F (mL/min) | k_e = 1 | k_e = 3 | k_e = 5 |
|---|---|---|---|
| 0.2 | 53.6% | 22.4% | 11.4% |
| 0.4 | 53.6% | 22.4% | 11.4% |
| 0.6 | 53.6% | 22.4% | 11.4% |

The extra-column variance *fraction* is flow-independent in this idealization — because both
$\sigma_{ec,t}$ and $\sigma_{col,t}$ (with $t0 \propto 1/F$ and N held fixed) scale as $1/F$, their
ratio does not move with flow. That is a real, if narrow, mathematical result [derived], not a
citation — and it only holds exactly if N truly is flow-independent, which §4 is explicit that
this document cannot confirm one way or the other. **The headline number**: even on an optimized
modern UHPLC instrument, an early-eluting peak ($k_e=1$) on this column geometry can have roughly
**half its observed variance from the instrument, not the column** — before even asking whether N
itself moves with flow. A peak that retains more strongly ($k_e=5$) sees a much smaller (~11%)
extra-column fraction. This means the N `fit_plate_count` recovers from the 0.4 mL/min scouting
widths is, exactly as `FittedPlateCount`'s own docstring in `width.py` already states, "an
*apparent*, instrument-inclusive efficiency" — not the column's intrinsic N — and this document's
quantification (using a different, low-dispersion instrument's $\sigma_{ec}^2$) is consistent with,
and sizes, that existing caveat. **What is not sourced**: the driver's own Acquity H-Class
$\sigma_{ec}^2$; the illustrative fraction above should not be read as this instrument's actual
number.

---

## 6. Two candidate rules, compared

### (a) Anchor a published H(u) shape at the one measured N, rescale to the new flow

**What exists**: strong *qualitative* literature that core-shell/SPP van Deemter curves are
unusually flat compared to fully-porous ones, in both the low-ν (B-term) and high-ν (C-term)
directions (Broeckhoven, Cabooter & Desmet 2013), and one *quantified but distant* bound — at most
a 43% h-rise at 3–4× the optimum velocity, on a 5 µm (not 1.6 µm) SPP particle. Nothing quantifies
the shape at a ±50% excursion, and nothing quantifies it for the 1.6 µm CORTECS particle
specifically (the two papers that measured this exact particle, Gritti/Shiner/Fairchild/Guiochon
*J. Chromatogr. A* **1334** and the *J. Sep. Sci.* companion, report only h_min values, not full
A/B/C or ν_opt — §3).

**What is missing to implement this today**: A, B, C (or h_min *and* ν_opt) for the 1.6 µm CORTECS
particle at this exact column format, and a molecular diffusion coefficient for whatever analyte is
being predicted (needed to place a candidate flow's u on the reduced-velocity axis at all). Absent
those, "anchor the shape and rescale" cannot be more than an order-of-magnitude qualitative
argument (§4.2) — it cannot presently be turned into a specific, defensible N(F) formula for this
engine without either (i) obtaining the full text of the two paywalled CORTECS-specific papers, or
(ii) running a real experiment (a third scouting run at a different flow) and fitting the shape
empirically, which is the same posture SPEC already takes toward a φ0-correction third run
(SPEC §12, "a v0.3 item, not a v0.2 one").

**Evidence on resulting error, if attempted anyway with borrowed (non-CORTECS) coefficients**:
none found. No source in this search fits a generic or borrowed van Deemter/Knox curve to one
point on a *different* column and reports the resulting error against that column's own measured
N at a second flow. The literature validates van Deemter/Knox fits made *from multiple
measured points on the same column* (that is what a kinetic-plot method is); it does not validate
single-point-anchored extrapolation using someone else's coefficients, which is the specific
operation this engine would need to perform.

### (b) Hold N constant across flow, stamp the prediction flow-uncorrected

**What exists**: the honest error of this fallback is, by definition, exactly the true (unknown)
N-change with flow — the same quantity §4 could not pin down. What the literature *does* support
is a bound on how bad "roughly constant" can be expected to be within a plateau: Broeckhoven,
Cabooter & Desmet's "3–4× its optimum velocity" plateau claim is the closest published statement of
a usable-flow-range width, but it is phrased as an **inter-particle-type comparison** (SPP vs. FPP,
each at its own reference point), not as "N stays within X% of its value at flow F across a
3–4× range" — re-read carefully in §4.2, it does *not* directly support "N is flat within a 3–4×
flow range on the same column," only that SPP's h at 3–4×ν_opt is still ≤ FPP's own h_min. No
source found states a %-constancy band for N itself over any specific flow multiple, for any
sub-2 µm core-shell column.

**Evidence on resulting error in N and Rs**: the same table as §4.3 applies directly, since "hold N
constant" is the x = 0 row: if the true N-change at ±50% flow is small (single digits to
low teens percent, per the qualitative flatness evidence), holding N constant costs little; if it
is nearer the 30–43% range seen at the much larger 3–4× excursion on a 5 µm particle, holding N
constant would understate the true W½ change and overstate Rs by a margin that breaches SPEC's
±0.3 bar. **Nothing in the accessible literature settles which regime a ±50% excursion on this
1.6 µm, 2.1×100 mm column actually falls into.**

**Comparative verdict**: rule (b) is strictly simpler and no less evidenced than rule (a) at
present, because rule (a) cannot currently be executed with sourced, CORTECS-specific
coefficients — it would have to borrow coefficients from a different particle size/brand, an
operation with *no* found evidence quantifying its own error. Rule (b)'s error is unknown but at
least honestly nameable as "the true flow-dependence of N, unmeasured here"; rule (a)'s error, if
attempted with borrowed coefficients, would compound that same unknown with an *additional*,
similarly unquantified cross-particle transfer error. Per CLAUDE.md's "warnings over blocks"
posture, a flow-uncorrected stamp is a warning-shaped answer; an unvalidated cross-particle H(u)
transfer is not obviously more honest, only more complicated.

---

## 7. Open points / could not verify

1. **No A, B, C (or h_min-and-ν_opt pair) for CORTECS 1.6 µm, or for any sub-2 µm core-shell
   particle, was found anywhere in the accessible literature.** Every source gives h_min alone.
   The two papers most likely to contain it (Gritti, Shiner, Fairchild & Guiochon, *J. Chromatogr.
   A* **1334** (2014) 30–43, and its *J. Sep. Sci.* companion) are both confirmed paywalled, exactly
   as `dead-time-from-geometry.md` §3.4 already found for the same two papers researching a
   different question (porosity). This is the same "single most valuable unread source" gap that
   doc already flagged, now confirmed relevant to a second question.
2. **No numeric u_opt or ν_opt in physical units was found for CORTECS 1.6 µm or any 1.6 µm
   core-shell particle.** §4.1's placement of 0.4 mL/min at ν≈6 rests on an unsourced generic
   diffusion coefficient and is explicitly not asserted as fact.
3. **No source quantifies the N-change (or h-change) at a ±50% flow excursion specifically**, on
   any core-shell column of any particle size. The only quantified bound found (43% h-rise) is at
   a 3–4× excursion on a 5 µm SPP particle — both the excursion size and the particle size differ
   from what the question asks about. §4.2 and §4.3 are explicit that extrapolating that number
   down to ±50% is not evidenced, only plausible by the shape argument.
4. **No source was found quantifying prediction-vs-measured N or H error for anchoring a borrowed
   (different-particle) van Deemter/Knox curve at one measured point and rescaling to a new flow**
   — the exact operation candidate rule (a) in §6 would need to perform. This appears to be a real
   gap in the literature searched, not merely an access problem: the kinetic-plot method validates
   multi-point fits on the *same* column, which is a different claim.
5. **The driver's own Acquity H-Class extra-column variance ($\sigma_{ec}^2$) was not found.**
   §5's worked fraction uses Gritti & Guiochon's Agilent 1290 Infinity figure (13.6 ± 0.3 µL²), a
   different, low-dispersion instrument, as the only quantified $\sigma_{ec}^2$ located; it is
   offered as an illustrative order-of-magnitude bound, not as this instrument's number.
6. **SPEC's ±0.3 Rs accuracy bar** (SPEC §10, "Rs ± 0.3") has no evidence located, one way or the
   other, bearing on whether it holds across a flow change — every existing validation number cited
   in SPEC and in `gradient-elution-math.md`/`plate-count-from-widths.md` is at the *same* flow
   rate (0.4 mL/min) across different gradient times, never across a flow change. This document's
   §4.3 table is the closest available bracketing of that question, and it brackets both inside and
   outside the ±0.3 bar depending on an x this search could not pin down.
7. **No Waters CORTECS application note, technology brief, or white paper with a van Deemter curve
   or numeric h_min/ν_opt was located.** The CORTECS product pages on waters.com timed out on every
   fetch attempt in this session (both the general product page and the columns page); Bing- and
   DuckDuckGo-proxied searches (the WebSearch tool itself was unavailable for the remainder of this
   session — its budget was exhausted early on) surfaced only generic Waters corporate and KB pages,
   none with the needed numbers. This is recorded as "not fetchable this session," not as evidence
   that no such document exists.
8. **Knox's 1977 paper itself was not fetchable** (no repository copy via Europe PMC or Unpaywall);
   the Knox equation form quoted in §3 is taken from its standard restatement in the
   Broeckhoven/Cabooter/Desmet (2013) open-access paper and other secondary use, not read directly
   from Knox (1977).
9. **The Gritti & Guiochon (2012) "Repeatability" paper's 2.1 mm vs. 4.6 mm RSD figures (§2, §5)
   describe column-to-column packing variability in the eddy-dispersion term, not extra-column
   instrument dispersion.** It is included because it is the only found source directly comparing
   2.1 mm and 4.6 mm formats on the same particle batch, but it should not be read as an
   extra-column band-broadening number — that distinction is made explicitly in §5 to avoid
   conflating the two.

---

*Compiled 2026-09-08, for issue #138. Research only; no engine, SPEC, or app changes made or
proposed. WebSearch was exhausted early in this session (200/200 calls used by prior activity in
the same session budget); every source above was located via WebFetch against Europe PMC's REST
search API, the Crossref REST API, Unpaywall's REST API, and direct/PMC full-text fetches, plus
Bing- and DuckDuckGo-proxied result pages for the Waters-specific search (§7 item 7) — not via the
WebSearch tool itself.*
