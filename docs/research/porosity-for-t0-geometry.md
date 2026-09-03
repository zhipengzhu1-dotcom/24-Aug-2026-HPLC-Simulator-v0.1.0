# Total Porosity Defaults for the Geometry Estimate of $t_0$

Research notes for wayfinder ticket #33 (defensible default $\varepsilon_{total}$ values for
the dead-time-from-geometry estimator $t_0 \approx \varepsilon_{total}\,\pi r^2 L / F$).
Companion to `gradient-elution-math.md` (*GEM*) and `plate-count-from-widths.md`; format
follows those docs. Audience: whoever implements the estimator and anyone auditing the
defaults.

Every load-bearing number is tagged with the source that owns it. Anything I computed
myself is tagged **[derived]** with the arithmetic shown. Section 7 lists everything I
could **not** verify against a primary source. Units per repo convention: minutes, mL,
mm, µm; porosities are dimensionless fractions.

Scope: packed columns only — fully porous and superficially porous (core–shell)
particles. Monoliths are out of scope for v0.1.

**Headline recommendation** (details in §5): fully porous $\varepsilon_{total} = 0.62$
(band 0.52–0.70); superficially porous $\varepsilon_{total} = 0.52$ (band 0.45–0.60).

> **Amended 2026-09-03 (map ticket #39).** The lab column's measured $t_0$ that §4.3–§4.4
> were written against — 0.6 min — was retracted by the driver on 2026-08-30 (read from the
> wrong time point) and re-read on 2026-08-31 as **0.525 min** (solvent front,
> `validation/run1-chromatogram.png`; `validation/method.csv`). §4.3, §4.4, §5.2, §5.3 and
> §7 item 13 are rewritten accordingly. The defaults and bands in §5.1 are unchanged; the
> fully-porous *default-when-unknown* of §5.3 is overridden by map ticket #34.

---

## 1. Why $\varepsilon_{total}$, and the three porosities

### 1.1 What the estimator is actually computing

The column's geometric (empty-tube) volume is $V_{col} = \pi r^2 L$. Only a fraction of
it is liquid; the rest is silica. That fraction is the **total porosity**:

$$\varepsilon_{total} \equiv \frac{V_M}{V_{col}}, \qquad t_0 = \frac{V_M}{F}
= \frac{\varepsilon_{total}\,\pi r^2 L}{F}$$

This is not a derived convenience — it is the operative definition used in the primary
literature. Broeckhoven, Cabooter & Desmet (ref. 1, read in full) write it verbatim:

> "Based on the flow rate $F$, column dead time $t_0$ and geometrical column volume
> $V_{col}$, the total column porosity is calculated as $\varepsilon_T = F t_0 / V_{col}$"

So the estimator inverts exactly the equation the literature uses to *measure*
$\varepsilon_{total}$. Everything hinges on what number to put in.

### 1.2 The three porosities, and why only one of them is $\varepsilon_{total}$

Adrover & Desmet (ref. 2, read in full) give the decomposition in one line — verbatim,
with their symbols ($\varepsilon_e$ external, $\varepsilon_{int}$ internal):

> "$\varepsilon_e = V_{\Omega m}/(V_{\Omega m} + V_{\Omega part})$ is the external
> porosity of the bed, $\varepsilon_{tot} = V_{\Sigma m}/(V_{\Omega m} + V_{\Omega part})
> = \varepsilon_e + (1 - \varepsilon_e)\varepsilon_{int}$ is the total porosity of the bed"

That is:

$$\boxed{\varepsilon_{total} = \varepsilon_e + (1-\varepsilon_e)\,\varepsilon_p}$$

| symbol | name | what it measures | typical value |
|---|---|---|---|
| $\varepsilon_e$ | external / interstitial / interparticle | liquid *between* particles ÷ column volume | 0.36–0.42 (packed spheres) |
| $\varepsilon_p$ | internal / intraparticle / particle porosity | pore liquid ÷ **particle** volume | 0.40–0.50 fully porous; 0.19–0.21 core–shell (whole particle; the *shell zone alone* reads ~0.27, §3.2) |
| $\varepsilon_{total}$ | total | all liquid ÷ column volume | the number the estimator needs |

Three traps this table is meant to prevent:

1. **$\varepsilon_p$ is normalised to particle volume, not column volume.** It enters
   $\varepsilon_{total}$ multiplied by $(1-\varepsilon_e)$, so a particle porosity of 0.42
   contributes only ~0.25 to $\varepsilon_{total}$.
2. **Some sources report the porosity of the *porous zone only*.** De Luca et al. (ref. 3)
   label their column "$\varepsilon_p$: particle porous zone porosity" — for a core–shell
   particle that excludes the solid core, and it must be multiplied by the shell's volume
   fraction before use (§3.2).
3. **Vendor "particle porosity" can mean the shell volume fraction, not liquid at all.**
   Kirkland et al.'s fused-core table (ref. 4) lists "Particle porosity (%)" = 75 for
   Halo 2.7 µm — see §3.3, where I show that column is $1-\rho^3$, a *geometric* quantity.
   Plugging 0.75 into $\varepsilon_{total}$ would be badly wrong.

### 1.3 Why the band matters as much as the default

$t_0$ is not a cosmetic output. In the engine it sets $k = (t_R - t_0)/t_0$ and, through
$b_e = t_0\,\Delta\varphi\,S_e/t_G$ (GEM §2.3), the gradient steepness. **[derived]** For a
peak at $t_R = 5$ min, moving $t_0$ across the plausible core–shell range 0.45 → 0.60 min
moves $k$ from 10.1 to 7.3, a 28% change. A porosity default is therefore a scientific
input with an uncertainty that has to travel with it, not a constant to be hard-coded and
forgotten.

### 1.4 What is *not* in scope

Monoliths (external porosity $\varepsilon_e \simeq 0.65$, Cabooter et al., ref. 5,
abstract) sit far outside both bands below and are excluded by the ticket. Nothing here
applies to them.

---

## 2. Fully porous particles: measurements, default and band

### 2.1 The two components, measured

**External porosity $\varepsilon_e$.** Four independent lines agree on 0.36–0.42:

- Khirevich, Höltzel, Daneyko, Seidel-Morgenstern & Tallarek (ref. 6, abstract, verbatim):
  computer-generated monodisperse hard-sphere packings spanning "the random-close and the
  random-loose packing limit ($\varepsilon$ = 0.366–0.46)". The physical bound.
- Deridder & Desmet (ref. 7, abstract, verbatim): "a packed bed column with an external
  porosity on the order of 35–40%".
- De Luca et al. (ref. 3, Table 1, read in full): ISEC-measured $\varepsilon_e$ = **0.42**
  on a fully porous 1.9 µm Titan column, **0.41** on a core–shell 2.0 µm Halo column — i.e.
  the interstitial fraction barely changes with particle architecture, as expected.
- Jandera & Hájek (ref. 8, Table 1–2, read in full): $\varepsilon_0$ from an excluded
  1.8 MDa polystyrene standard across 18 columns, mostly **0.36–0.43**.

**Internal porosity $\varepsilon_p$ of fully porous silica.** 0.40–0.50:

- Gritti, Cavazzini, Marchetti & Guiochon (ref. 9, abstract, verbatim): "its lower
  internal porosity ($\varepsilon_p$ = 0.19 versus 0.42)" — 0.42 is the conventional
  3 µm totally porous silica-B, 0.19 the Halo shell particle.
- Song, Desmet & Cabooter (ref. 10, abstract, verbatim): for Zorbax Eclipse Plus C18,
  "the measured internal porosity values lying around $\varepsilon_{pz}$ = 0.5, whereas a
  packing of nanospheres would rather correspond to an $\varepsilon_{pz}$ of 0.4".
- De Luca et al. (ref. 3): $\varepsilon_p$ = **0.41** for the fully porous Titan 1.9 µm
  (ISEC).

### 2.2 [derived] What the decomposition predicts

Using $\varepsilon_{total} = \varepsilon_e + (1-\varepsilon_e)\varepsilon_p$ (ref. 2):

| | $\varepsilon_e$ | $\varepsilon_p$ | $\varepsilon_{total}$ |
|---|---|---|---|
| low | 0.36 | 0.40 | **0.616** |
| centre | 0.39 | 0.45 | **0.665** |
| high | 0.42 | 0.50 | **0.710** |

So structure alone predicts **0.62–0.71** for a well-packed fully porous silica column.

### 2.3 Direct measurements of $\varepsilon_{total}$

| column | $d_p$ | method | $\varepsilon_{total}$ | source |
|---|---|---|---|---|
| Titan (FPP, chiral) | 1.9 µm | ISEC | **0.66** | ref. 3, Table 1, read |
| Zorbax SB-C18, 4.6 × 250 mm | 5 µm | $F t_0/V_{col}$, uracil marker | **0.526** | ref. 1, read |
| XBridge HILIC 3.0 × 100 | 5 µm | toluene marker | 0.77 | ref. 8, read — see caveat |
| Atlantis HILIC 3.0 × 100 | 5 µm | toluene marker | 0.83 | ref. 8, read — see caveat |
| LiChrospher DIOL 4.0 × 125 | 5 µm | toluene marker | 0.70 | ref. 8, read |
| TSKgel Amide-80 2.0 × 150 | 3 µm | toluene marker | 0.60 | ref. 8, read |
| Cogent Bidentate C18 4.6 × 75 | 4 µm | toluene marker | 0.64 | ref. 8, read |
| Waters 2.1 × 50 mm, four FPP phases + one SPP | 1.6–1.8 µm | hold-up volume ≃ 80–90 µL | **0.46–0.52** [derived] | ref. 11, abstract |

**Caveat on ref. 8.** Jandera & Hájek measure $V_M$ as the elution volume of *toluene in
acetonitrile* on HILIC phases. Several of their $\varepsilon_T$ values (Luna HILIC 0.88,
Atlantis 0.83, Cogent Silica C 0.81) exceed what a packed silica bed can physically hold —
$\varepsilon_e \le 0.46$ at the random-loose limit (ref. 6) plus a fully porous
$\varepsilon_p \le 0.5$ caps $\varepsilon_{total}$ near 0.73 **[derived]**. The excess is
almost certainly toluene retention on those phases inflating $V_M$. Their *core–shell*
rows (§3.4) sit in a physically sane 0.55–0.60 and are used below; their high fully-porous
rows are reported here for completeness and excluded from the band. Their Table 1 also
carries transcription errors ($V_{column}$ for YMC Triart DIOL 2.1 × 150 printed as
1.25 mL where the geometry gives 0.52 mL **[derived]**), a further reason to weight it
lightly.

**[derived] on ref. 11.** Gritti, McDonald & Gilar state "a series of short 2.1 mm × 50 mm
columns (hold-up volume ≃ 80–90 µL) packed with 1.8 µm HSS-T3, 1.7 µm BEH-C18, 1.7 µm
CSH-C18, 1.6 µm CORTECS-C18+, and 1.7 µm BEH-C4 particles". $V_{col} = \pi(0.105)^2(5)$
= 0.1732 mL = 173.2 µL, so $\varepsilon_{total}$ = 80/173.2 = 0.462 to 90/173.2 = 0.520.
The range is quoted across five columns of two architectures and cannot be split by
architecture, but it does bound *both* — and it is the only measurement I found on
Waters sub-2 µm narrow-bore hardware, i.e. the closest published analogue to the lab
column of §4.

### 2.4 The practitioner rule, and what porosity it hides

Dolan (ref. 12, first section read verbatim from the page; the remainder as rendered by
the fetch tool before the registration wall):

> "a column packed with fully porous particles has a total column porosity of about 60%.
> In other words, 60% of the column is filled with mobile phase and 40% is occupied by the
> silica particles."

from which he gives $V_M = 0.5\times10^{-3}\,L\,d_c^2$ (mL, mm, mm), accurate "within
±10%". **[derived]** That formula does *not* encode 0.60: dividing by $\pi r^2 L$ gives
$\varepsilon_{total} = 0.5/(\pi/4) = 0.6366$, independent of dimensions (checked at
4.6 × 150, 2.1 × 100 and 2.1 × 50 mm — all 0.6366). The textbook rule of thumb every
chromatographer uses is therefore an $\varepsilon_{total} = 0.637$ estimator with a stated
±10% band, i.e. **0.57–0.70**. Worth knowing, because users will compare the app's number
against this rule.

### 2.5 Recommendation for fully porous

**Default $\varepsilon_{total} = 0.62$. Band 0.52–0.70.**

- 0.62 sits at the bottom of the structural prediction (0.62–0.71, §2.2), just below
  Dolan's 0.637 rule (§2.4), and below the ISEC-measured 0.66 (ref. 3).
- Choosing the *low* end of the structural range is deliberate: SPEC §4 makes geometry a
  fallback below a measured marker $t_0$, and §4.1 below shows that ordering only holds if
  the default is at or under the column's true porosity.
- The band's floor is set by the marker-based measurements (0.526, ref. 1; 0.46–0.52
  [derived] from ref. 11), which run consistently *below* the structural value. That gap
  is real and is discussed in §4.2 — a $t_0$ marker samples somewhat less than the full
  liquid volume, while ISEC and pycnometry capture all of it.
- Roughly a third of the spread is bonding/pore-volume chemistry (§2.6); the rest is
  packing density and the definition of $V_M$.

### 2.6 How much of the spread is bonding and pore volume?

**[derived]**, inverting $\varepsilon_p = (\varepsilon_{total}-\varepsilon_e)/(1-\varepsilon_e)$
at a fixed, well-packed $\varepsilon_e = 0.40$: the fully porous band 0.55 → 0.70 maps to
$\varepsilon_p$ = 0.25 → 0.50. The measured $\varepsilon_p$ span for fully porous silica is
0.40–0.50 (ref. 9: 0.42; ref. 10: ~0.5 measured, 0.4 for a nanosphere packing; ref. 3:
0.41), which alone moves $\varepsilon_{total}$ by 0.60 → 0.70, i.e. **about two-thirds of
the band is particle pore volume and its occupancy by bonded phase**; the remaining third
is packing density ($\varepsilon_e$ 0.36–0.42 moves $\varepsilon_{total}$ by ~0.04 at fixed
$\varepsilon_p$). Mechanistically the bonded ligand occupies pore volume — the same reason
Gritti's conventional silica reads 0.42 rather than the ~0.5 of a stripped particle
(ref. 10 strip the phase with TFA precisely to remove this). Wide-pore and low-surface-area
phases sit low; high-surface-area 90–120 Å phases sit high. No source I could reach
tabulates $\varepsilon_{total}$ by bonding chemistry on one silica, so this split is
**[derived]** arithmetic on measured component ranges, not a citable decomposition.

---

## 3. Superficially porous (core–shell) particles: measurements, default and band

### 3.1 Why it must be lower

The solid core is silica, not liquid. Broeckhoven et al. (ref. 1, read in full) state the
mechanism and the size verbatim:

> "when making the realistic assumption that both columns have the same external porosity
> $\varepsilon$, the lower total porosity $\varepsilon_T$ of core–shell particles (due to
> the solid core) should in fact give rise to a larger permeability. Based on values found
> for $\varepsilon_T$ in literature, the HALO particles have a 15%–25% lower total porosity
> than Acquity particles"

Confirmed structurally: De Luca et al. (ref. 3) measure $\varepsilon_e$ = 0.42 (fully
porous) versus 0.41 (core–shell) — the *interstitial* space is the same; the whole
difference is inside the particle.

### 3.2 [derived] The core–shell geometry factor

For a particle of diameter $d_p$ with a solid core of diameter $d_c$, write
$\rho = d_c/d_p$. The porous shell is a fraction $1-\rho^3$ of the particle volume, so the
particle's own porosity is

$$\varepsilon_p = (1-\rho^3)\,\varepsilon_{shell}, \qquad
\varepsilon_{total} = \varepsilon_e + (1-\varepsilon_e)(1-\rho^3)\,\varepsilon_{shell}$$

**Consistency check against ref. 3.** Their Halo 2.0 µm row gives $\varepsilon_e$ = 0.41,
porous-zone porosity 0.27, measured $\varepsilon_t$ = 0.54. Naively using 0.27 as a whole-
particle porosity gives 0.41 + 0.59(0.27) = 0.569 — 5% too high. Including the core with
$\rho$ = 0.60 gives 0.41 + 0.59(0.784)(0.27) = **0.535**, matching their 0.54 to 1%. The
geometry factor is therefore both necessary and sufficient to reconcile their numbers, and
it confirms that their tabulated $\varepsilon_p$ is a *porous-zone* porosity as their
footnote says.

$\rho^3$ for the published architectures **[derived]** from ref. 4 and ref. 9:

| particle | $d_p$ | shell | $\rho$ | $\rho^3$ (solid fraction) | $1-\rho^3$ (porous fraction) |
|---|---|---|---|---|---|
| Halo / Ascentis Express | 2.7 µm | 0.5 µm | 0.63 | 0.250 | 0.750 |
| Halo 2.0 (ref. 3 fit) | 2.0 µm | ~0.4 µm | 0.60 | 0.216 | 0.784 |
| Kinetex 1.7 | 1.7 µm | 0.23 µm | 0.735 | 0.397 | 0.603 |
| Halo 5 | 5.0 µm | 0.6 µm | 0.76 | 0.439 | 0.561 |
| Halo wide pore | 3.4 µm | 0.2 µm | 0.88 | 0.681 | 0.319 |

A quarter to a half of a core–shell particle is solid, dead volume. That is the entire
effect.

### 3.3 The vendor-table trap

Kirkland et al. (ref. 4, read in full, Table 1 verbatim):

> "Fused-core particle | Utility | Particle diameter (µm) | Porous shell thickness (µm) |
> Pore diameter (Å) | Solid core/particle diameter ratio | BET surface area (m²/g) |
> Particle porosity (%)"
> "Halo | Small molecules | 2.7 | 0.5 | 90 | 0.63 | 135 | 75"
> "Halo 5 | Small molecules | 5.0 | 0.6 | 90 | 0.71 | 90 | 56"
> "Halo wide pore | Proteins, large molecules | 3.4 | 0.2 | 400 | 0.88 | 14 | 31"
> "Halo wide pore | Proteins, large molecules | 2.7 | 0.35 | 400 | 0.74 | 29 | 59"

**[derived]** That "Particle porosity (%)" column is exactly $1-\rho^3$: 0.63 → 0.750
(printed 75), 0.88 → 0.319 (printed 31), 0.74 → 0.595 (printed 59). It is a *geometric
shell volume fraction*, not a liquid-filled porosity, and it is roughly three times the
real $\varepsilon_p$ (ref. 9 measures 0.19 for the same Halo particle whose row reads 75%).
Anyone porting this table into a porosity default would overestimate $t_0$ by ~50%.

Also **[derived]**: the Halo 5 row is internally inconsistent — a 0.6 µm shell on a 5.0 µm
particle gives a 3.8 µm core, $\rho$ = 0.76, not the printed 0.71; and the printed 56%
matches $1-0.76^3 = 0.561$, not $1-0.71^3 = 0.642$. The shell thickness and the porosity
column agree with each other; the printed ratio is the odd one out.

### 3.4 Direct measurements of $\varepsilon_{total}$

| column | $d_p$ | method | $\varepsilon_{total}$ | source |
|---|---|---|---|---|
| Ascentis Express C18, 4.6 × 250 mm | 5 µm | $Ft_0/V_{col}$, uracil marker | **0.460** | ref. 1, read |
| Halo (chiral, SPP) | 2.0 µm | ISEC | **0.54** | ref. 3, Table 1, read |
| Ascentis Express HILIC 4.6 × 100 | 2.7 µm | toluene marker | 0.60 | ref. 8, read |
| Ascentis Express CN 4.6 × 100 | 2.7 µm | toluene marker | 0.58 | ref. 8, read |
| Ascentis Express OH5 4.6 × 100 | 2.7 µm | toluene marker | 0.57 | ref. 8, read |
| Ascentis Express Phenyl-F5 4.6 × 100 | 2.7 µm | toluene marker | 0.55 | ref. 8, read |
| SPP C18, 2.1 × 150 mm | 2.7 µm | **pycnometry** | **0.48** | ref. 13, read |
| SPP C18, 1.0 × 150 mm | 2.7 µm | **pycnometry** | **0.67** | ref. 13, read |
| Waters 2.1 × 50, incl. CORTECS-C18+ 1.6 µm | 1.6 µm | hold-up volume | 0.46–0.52 [derived] | ref. 11, abstract |

Two structural results worth recording even though they are not $\varepsilon_{total}$:
Gritti & Guiochon measured Kinetex external porosities of **0.394–0.405** (ref. 14,
abstract, verbatim: "their external porosities between 0.394 and 0.405"), confirming
$\varepsilon_e \approx 0.40$ for core–shell beds; and Gritti et al. (ref. 9) measured
$\varepsilon_p$ = **0.19** for Halo 2.7 µm.

**The ref. 13 pair deserves emphasis.** Handlovic et al. measured two columns of *the same*
2.7 µm SPP C18 phase, differing only in bore, by pycnometry — the most direct method
available, and one that (in their words) "do[es] not need to be corrected for the volume
of the system/connections or nonidealities in injection timing":

> "The 2.1 mm i.d. column had an empty volume of 520 µL, a void volume of 248 µL and a
> measured total porosity value of 0.48. The 1.0 mm i.d. column had an empty volume of
> 118 µL, a void volume of 78.9 µL, and a measured total porosity value of 0.67."

**[derived]** Their empty volumes match geometry exactly ($\pi(1.05)^2(150)$ = 519.5 µL;
$\pi(0.5)^2(150)$ = 117.8 µL) and their ratios reproduce the quoted porosities
(248/520 = 0.477; 78.9/118 = 0.669). So the 0.48 vs 0.67 spread is **not** an arithmetic
slip: two columns of nominally identical packing, measured by the same rigorous method,
differ by 40% in total porosity. 0.67 is above anything the core–shell structure can
support (§3.5) and most likely reflects genuinely looser packing in a 1.0 mm bore. This is
the single most important calibration on how wide an honest band has to be.

### 3.5 [derived] What the decomposition predicts

With $\varepsilon_e$ = 0.36–0.42 (§2.1, unchanged by architecture per ref. 3) and
whole-particle $\varepsilon_p$ = 0.17–0.25 (ref. 9 measures 0.19; ref. 3 implies
$0.784\times0.27$ = 0.21):

| | $\varepsilon_e$ | $\varepsilon_p$ | $\varepsilon_{total}$ |
|---|---|---|---|
| low | 0.36 | 0.17 | **0.469** |
| centre | 0.40 | 0.21 | **0.526** |
| high | 0.42 | 0.25 | **0.565** |

Structure predicts **0.47–0.57**, centred on 0.53 — in close agreement with the measured
0.46, 0.48, 0.54 and with the low end of ref. 8's 0.55–0.60 cluster. The pycnometric 0.67
of the 1.0 mm column (ref. 13) lies outside it and is treated as a packing outlier, not as
evidence about the particle.

### 3.6 Recommendation for core–shell

**Default $\varepsilon_{total} = 0.52$. Band 0.45–0.60.**

- 0.52 is the centre of the structural prediction (§3.5) and sits between the measured
  0.46/0.48 and 0.54.
- **[derived]** The ratio to the fully porous default is 0.52/0.62 = 0.84, i.e. core–shell
  16% lower. That lands inside Broeckhoven's cited "15%–25% lower" (ref. 1) and matches
  Dolan's independent estimate of "10–15% less" volume for superficially porous columns
  (ref. 12); it is also close to the like-for-like measured ratio 0.460/0.526 = 0.875
  from the single study that measured both on the same instrument (ref. 1).
- Band floor 0.45: below the lowest structural value and just under the measured 0.46.
- Band ceiling 0.60: the top of ref. 8's Ascentis Express cluster. Deliberately **not**
  stretched to ref. 13's 0.67 — that value is real but is a property of a 1.0 mm bore
  packing, not of core–shell particles, and including it would make the band useless.
- Spread attribution **[derived]**: at fixed $\varepsilon_e$ = 0.40 the band 0.45–0.60
  maps to whole-particle $\varepsilon_p$ = 0.083–0.333. Of that, the *core size* explains
  most — $1-\rho^3$ ranges 0.32 (wide pore) to 0.78 (thin core) across shipping products
  (§3.2), a factor 2.4 — while shell pore volume and bonding contribute the rest. For
  core–shell particles, **architecture dominates chemistry**, the reverse of the fully
  porous case (§2.6). A wide-pore core–shell column (Halo 3.4 µm, $1-\rho^3$ = 0.32) would
  need its own, much lower default near $0.40 + 0.60(0.32)(0.5) \approx 0.50$ at best and
  is not covered by the recommendation.

---

## 4. The extra-column caveat and the worked CORTECS check

### 4.1 The two quantities are not the same quantity

A marker $t_0$ is measured at the detector, so it contains everything between the
injector and the detector cell:

$$t_0^{marker} = \frac{\varepsilon_{total}\,V_{col} + V_{ec}}{F}
\;\ge\; \frac{\varepsilon_{total}\,V_{col}}{F} = t_0^{geometry}$$

$V_{ec}$ — connecting tubing, injector, detector cell — is not small on narrow-bore
UHPLC. Handlovic et al. (ref. 13, read in full) measured it across five commercial
LC-MS systems, verbatim:

> "The extra-column volume of these systems in their standard configuration ranged from
> 26.4 to 78.1 µL which we reduced to 9.57 to 18.7 µL by optimizing the fluidics."

Their Waters ACQUITY I-Class Plus in standard configuration measured **26.4 ± 0.2 µL**.
Column hardware itself (endfittings, frits) adds little by comparison: Gritti, McDonald &
Gilar (ref. 11, abstract) put the "column hardware volume" at "≃ 1.7 µL".

So the ordering **geometry $\le$ marker** should hold, *provided* the porosity default is
at or below the column's true porosity. That proviso is the whole reason §2.5 picked the
low end of the structural range. If the estimator's number ever comes out *above* a
measured marker $t_0$, that is a diagnosable fault condition, not a rounding difference —
either the default is too high for that phase, the entered dimensions are wrong, or the
marker eluted early (excluded from the pores).

### 4.2 The opposite bias: markers under-sample the pore volume

Working against the extra-column inflation is a real deflation. A $t_0$ marker only
reports the volume it can reach. David, Petre & Moldoveanu (ref. 15, read in full) state
it plainly:

> "it is likely that the organic tracers do not entirely penetrate the fine pores of the
> stationary phase, and therefore, their measured retention times do not represent the real
> porosity of the chromatographic bed"

and Redón, Subirats & Rosés (ref. 16, read in full) quantify how far off a badly chosen
marker can be — a solvent disturbance peak on a ZIC-HILIC column represented "about the
50% of the total exchangeable solvent volume inside the column ($V_{solvent}$,
pycnometrically measured)". This is why ref. 13 preferred pycnometry: it "do[es] not need
to be corrected for the volume of the system/connections or nonidealities in injection
timing".

Net effect on the numbers in §2–§3: marker-based $\varepsilon_{total}$ (ref. 1: 0.526 and
0.460; ref. 11 [derived]: 0.46–0.52) runs *below* structural values from ISEC and
pycnometry (ref. 3: 0.66 and 0.54). Both biases are present in any real marker
measurement and they partly cancel; which one wins depends on the marker, the mobile
phase and the plumbing. The estimator cannot resolve this — it can only present a band.

### 4.3 [derived] The worked check: the lab CORTECS column

> **Provenance (amended 2026-09-03).** First written against
> `t0,0.6,min,measured marker time`. The driver retracted 0.6 on 2026-08-30 — read from the
> wrong time point — and re-read the value on 2026-08-31 as **0.525 min**, the solvent
> front in `validation/run1-chromatogram.png`; `method.csv` now records `t0,0.525` and
> `t0_marker,solvent front`. The arithmetic below is redone at 0.525; the retracted 0.693
> is kept only where it is the point.

From `validation/method.csv`: Waters CORTECS UPLC Shield RP18, 2.1 × 100 mm, 1.6 µm
(core–shell), $F$ = 0.4 mL/min, $t_0$ = 0.525 min (solvent front), on a Waters ACQUITY
UPLC H-Class.

$$V_{col} = \pi r^2 L = \pi (0.105\;\text{cm})^2 (10\;\text{cm}) = 0.34636\;\text{mL}$$
$$V_M^{apparent} = t_0 F = 0.525 \times 0.4 = 0.210\;\text{mL}$$
$$\varepsilon_{total}^{apparent} = 0.210/0.34636 = \mathbf{0.606}$$

**0.606 sits just above the core–shell band (0.45–0.60) and below the fully porous default
(0.62)** — exactly where §4.1 says a marker-measured value should sit, since it carries
$V_{ec}$ on top of the column's own void. Three checks:

1. **The architecture can hold it, once plumbing is removed.** For any $V_{ec}$ in
   ref. 13's 26–78 µL range, the column's own porosity is $(0.210 - V_{ec})/0.3464$ =
   **0.38–0.53** — inside or below the core–shell band, never in the fully porous one.
   (Inverting §1.2 on the *apparent* 0.606 at $\varepsilon_e$ = 0.40 would need
   $\varepsilon_p$ = 0.34, above any measured core–shell particle — the sign that the
   apparent value contains something that is not column void.)
2. **The same particle measures in range on the same hardware family.** Ref. 11's
   2.1 × 50 mm Waters columns including 1.6 µm CORTECS-C18+ give $\varepsilon_{total}$ =
   0.46–0.52 **[derived]** — consistent with a column porosity near 0.52 plus ~30 µL of
   plumbing here.
3. **The excess volume is the right size for plumbing.** At the recommended
   $\varepsilon$ = 0.52 the column holds 180 µL, leaving 210 − 180 = **30 µL**; at the band
   ceiling 0.60 → 208 µL, leaving **2 µL**; at the band floor 0.45 → 156 µL, leaving
   **54 µL**. Ref. 13's stock-configuration ACQUITY I-Class Plus measured 26.4 µL and their
   five-system range was 26–78 µL.

**What the estimator would predict** at each porosity, for this column:

| $\varepsilon_{total}$ | column void (µL) | predicted $t_0$ (min) | vs measured 0.525 | implied $V_{ec}$ (µL) |
|---|---|---|---|---|
| 0.45 (band floor) | 156 | 0.390 | −26% | +54 |
| 0.52 (**default**) | 180 | **0.450** | **−14%** | **+30** |
| 0.60 (band ceiling) | 208 | 0.520 | −1% | +2 |
| 0.606 (apparent) | 210 | 0.525 | 0% | 0 |
| 0.62 (fully porous default, wrong architecture) | 215 | 0.537 | +2% | **−5 — impossible** |
| 0.693 (apparent under the retracted 0.6) | 240 | 0.600 | +14% | **−30 — impossible** |

### 4.4 Reading the discrepancy honestly

The 30 µL between the core–shell default and the measured time has the same four possible
contributors as before, but none of them now has to carry anything unusual:

1. **Extra-column volume** (§4.1): 26–78 µL on stock UHPLC (ref. 13). Accounts for the
   whole gap on its own. The H-Class's own $V_{ec}$ has never been measured (§7 item 13).
2. **Precision of the read.** 0.525 was read from a chromatogram image; the precision of
   that read is not recorded. At ±0.01 min the apparent porosity spans 0.595–0.618
   **[derived]** — ±2%, and no conclusion here moves.
3. **The marker is a solvent front.** No marker compound was injected; `t0_marker` reads
   "solvent front". Ref. 16 and `dead-time-from-geometry.md` §5.2 record that solvent
   disturbances are discouraged as hold-up markers, and they may read early or late (§4.2).
   A uracil injection with the time-point convention written down would make the value
   audit-grade; it is on the bench follow-up list.
4. **Packing.** Ref. 13's 2.1 mm / 1.0 mm pair (0.48 vs 0.67 by pycnometry) shows that
   nominally identical narrow-bore packings genuinely differ; a column porosity anywhere in
   0.45–0.53 is consistent with the measurement.

**Judgement.** The lab column's true $\varepsilon_{total}$ is most likely 0.45–0.53 and the
measured 0.525 min is that void plus roughly 30 µL of plumbing. The measured $t_0$ should be
used — SPEC §4 is measured-first, and the marker time is what the instrument delivers to
the detector, which is the $t_0$ the retention model needs — and the geometry fallback
should not be tuned to reproduce it. The first version of this section, written against
the retracted 0.6, attributed a 32–60 µL gap entirely to extra-column volume; the #24
comment of 2026-08-30 flagged that attribution as confounded by the mis-read, and it was:
roughly 30 µL of the apparent gap was the wrong time point, and the remainder is ordinary
plumbing.

### 4.5 What this implies for how the estimator presents its number

1. **Present the band, not just the point.** Report $t_0$ = 0.45 min (0.39–0.52) for this
   column, not "0.45 min". The band is ±15% and users must see it.
2. **Never silently exceed a marker.** If both a marker $t_0$ and a geometry estimate
   exist, and geometry > marker, warn (repo convention: warnings over blocks). The
   inequality of §4.1 says that should not happen.
3. **State the direction of the bias.** The geometry estimate deliberately excludes
   extra-column volume, so it will read low against any marker measurement — typically by
   10–30% on a 2.1 mm column. Say so in the UI next to the estimate; it prevents a user
   "correcting" a correct estimate.
4. **Ask for the marker identity when a marker $t_0$ is entered.** §4.4 item 3 is a data
   quality gap in the project's own validation set, not just a general caution.
5. **Keep the existing lower-confidence stamp** (SPEC §4, §5 item 6, `t0_source`). Nothing
   found here justifies promoting a geometry estimate to equal standing with a marker: the
   honest band is ±15%, and $t_0$ propagates into $k$ (28% for the band, §1.3) and into
   $b_e$.

---

## 5. Recommendation table for the estimator

### 5.1 The defaults

| architecture | default $\varepsilon_{total}$ | credible band | basis |
|---|---|---|---|
| **Fully porous** (BEH, Hypersil, Zorbax, XBridge, HSS, Luna…) | **0.62** | **0.52 – 0.70** | structural 0.62–0.71 [derived, §2.2]; ISEC 0.66 (ref. 3); marker 0.526 (ref. 1); Dolan's rule = 0.637 [derived, ref. 12] |
| **Superficially porous / core–shell** (CORTECS, Kinetex, Halo, Ascentis Express, Poroshell, Accucore) | **0.52** | **0.45 – 0.60** | structural 0.47–0.57 [derived, §3.5]; ISEC 0.54 (ref. 3); marker 0.460 (ref. 1); pycnometry 0.48 (ref. 13); toluene 0.55–0.60 (ref. 8) |
| *Wide-pore core–shell* ($\rho \ge 0.85$, e.g. Halo 3.4 µm 400 Å) | *not covered* | — | $1-\rho^3$ = 0.32 (ref. 4) puts it below the core–shell band [derived, §3.6] |
| *Monolith* | *out of scope* | — | $\varepsilon_e \simeq 0.65$ alone (ref. 5) |

Ratio core–shell / fully porous = 0.84, i.e. **16% less void volume** [derived] — inside
the "15%–25% lower" of ref. 1 and consistent with Dolan's "10–15% less" (ref. 12).

**Worked defaults for the lab column** (2.1 × 100 mm, $V_{col}$ = 0.3464 mL) [derived]:
core–shell 0.52 → $V_M$ = 180 µL, $t_0$ = 0.450 min at 0.4 mL/min (band 0.39–0.52 min);
fully porous 0.62 → $V_M$ = 215 µL, $t_0$ = 0.537 min (band 0.45–0.61 min).

### 5.2 How the band should be used

- **Report it.** The band is roughly ±15% either side of the default in both cases; a
  single number implies a precision the science does not support (§3.4: two columns of the
  same packing measured 0.48 and 0.67).
- **Bias is one-directional against a marker.** Geometry excludes $V_{ec}$, so a geometry
  $t_0$ should read *below* a marker $t_0$ (§4.1). Warn if it does not.
- **Do not fit the porosity to a marker.** If a marker exists it wins outright (SPEC §4);
  back-solving $\varepsilon$ from it just relabels the extra-column volume as porosity, as
  the retracted 0.693 of §4.3 showed — and as the corrected 0.606 still shows, sitting
  above the core–shell band by exactly the plumbing.

### 5.3 Which knob a user should get

Architecture is the only split the evidence supports. Recommended input model:

1. A two-value choice — *fully porous* / *core–shell* — **with no default**. This document
   originally recommended defaulting to fully porous (the larger installed base, and the
   higher, hence more conservative against a marker $t_0$, value). Map ticket #34
   (2026-08-31) overrode that: undeclared architecture makes the estimator refuse, with a
   typed error naming the field. The reason is on the lab column itself — at the corrected
   $t_0$ every fully porous constant puts the geometry estimate *above* the measured time
   (implied $V_{ec}$ −5 µL at 0.62), which is impossible, and a silent fully-porous default
   would have compared the apparent 0.606 against 0.62 and reported nothing, when the true
   comparison is against 0.52 (`dead-time-from-geometry.md` §7.2).
2. An optional numeric override for $\varepsilon_{total}$, validated against 0.30–0.80 and
   warned outside each architecture's band (warnings over blocks).
3. No attempt to infer architecture from the column name string. Vendor naming is not a
   reliable signal (CORTECS and Kinetex are core–shell; XSelect and Kinetex EVO are not
   distinguishable by pattern), and a silently wrong architecture is a 16% $t_0$ error.

Not recommended: splitting the default by particle size, pore size or bonding. §2.6 shows
bonding/pore volume dominates the fully porous spread but no reachable source tabulates it
per phase, so any finer split would be invented precision. Core diameter *would* justify a
finer core–shell split (§3.6), but $\rho$ is not on a column label.

### 5.4 What is judgement rather than citation

- The specific values 0.62 and 0.52, and the band edges, are **[derived]** consensus
  numbers over §2 and §3, not values any single source recommends as a default.
- The choice to sit the fully porous default at the *bottom* of the structural range is a
  design decision serving the geometry $\le$ marker ordering (§4.1), not a measurement.
- The 0.30–0.80 validation range in §5.3 is a sanity bound from the physical limits
  ($\varepsilon_e \le 0.46$ at the random-loose limit, ref. 6, plus a fully porous
  $\varepsilon_p \le 0.5$, ref. 10, caps $\varepsilon_{total}$ near 0.73 [derived]) with
  headroom, not a cited range.

---

## 6. References

"Read" = full text read directly (Europe PMC JATS XML unless noted); otherwise abstract or
partial page as stated.

1. **Broeckhoven, K.; Cabooter, D.; Desmet, G.** "Kinetic performance comparison of fully
   and superficially porous particles with sizes ranging between 2.7 µm and 5 µm: Intrinsic
   evaluation and application to a pharmaceutical test compound." *J. Pharm. Anal.* **3**
   (2013) 313–323. [doi:10.1016/j.jpha.2012.12.006](https://doi.org/10.1016/j.jpha.2012.12.006);
   [PMC5760962](https://pmc.ncbi.nlm.nih.gov/articles/PMC5760962/) — read.
2. **Adrover, A.; Desmet, G.** "A Hierarchical Model for Longitudinal and Intraparticle
   Diffusion Coefficients in Liquid Chromatography." *Anal. Chem.* **97** (2025) 21351–21357.
   [doi:10.1021/acs.analchem.5c02838](https://doi.org/10.1021/acs.analchem.5c02838);
   [PMC12509189](https://pmc.ncbi.nlm.nih.gov/articles/PMC12509189/) — read (used for the
   definition $\varepsilon_{tot} = \varepsilon_e + (1-\varepsilon_e)\varepsilon_{int}$).
3. **De Luca, C.; Compagnin, G.; Nosengo, C.; Mazzoccanti, G.; Gasparrini, F.; Cavazzini, A.;
   Catani, M.; Felletti, S.** "Novel insights into the dependence of adsorption-desorption
   kinetics on particle geometry in chiral chromatography." *Anal. Bioanal. Chem.* **416**
   (2024) 1809–1820. [doi:10.1007/s00216-024-05186-z](https://doi.org/10.1007/s00216-024-05186-z);
   [PMC10901921](https://pmc.ncbi.nlm.nih.gov/articles/PMC10901921/) — read (Table 1: ISEC
   $\varepsilon_t/\varepsilon_e/\varepsilon_p$ for a fully porous and a core–shell column).
4. **Kirkland, J. J.; Schuster, S. A.; Johnson, W. L.; Boyes, B. E.** "Fused-core particle
   technology in high-performance liquid chromatography: An overview." *J. Pharm. Anal.* **3**
   (2013) 303–312. [doi:10.1016/j.jpha.2013.02.005](https://doi.org/10.1016/j.jpha.2013.02.005);
   [PMC5760966](https://pmc.ncbi.nlm.nih.gov/articles/PMC5760966/) — read (Table 1 quoted
   verbatim in §3.3).
5. **Cabooter, D.; Broeckhoven, K.; Sterken, R.; Vanmessen, A.; Vandendael, I.; Nakanishi, K.;
   Deridder, S.; Desmet, G.** *J. Chromatogr. A* **1325** (2014) 72–82.
   [doi:10.1016/j.chroma.2013.11.047](https://doi.org/10.1016/j.chroma.2013.11.047) — abstract
   ("external porosity that is largely the same for both monolith generations ($\varepsilon_e\sim$0.65)").
6. **Khirevich, S.; Höltzel, A.; Daneyko, A.; Seidel-Morgenstern, A.; Tallarek, U.**
   "Structure-transport correlation for the diffusive tortuosity of bulk, monodisperse, random
   sphere packings." *J. Chromatogr. A* **1218** (2011) 6489–6497.
   [doi:10.1016/j.chroma.2011.07.066](https://doi.org/10.1016/j.chroma.2011.07.066) — abstract.
7. **Deridder, S.; Desmet, G.** *J. Chromatogr. A* **1227** (2012) 194–202.
   [doi:10.1016/j.chroma.2012.01.007](https://doi.org/10.1016/j.chroma.2012.01.007) — abstract.
8. **Jandera, P.; Hájek, T.** "A New Definition of the Stationary Phase Volume in Mixed-Mode
   Chromatographic Columns in Hydrophilic Liquid Chromatography." *Molecules* **26** (2021)
   4819. [doi:10.3390/molecules26164819](https://doi.org/10.3390/molecules26164819);
   [PMC8400792](https://pmc.ncbi.nlm.nih.gov/articles/PMC8400792/) — read (Tables 1–2:
   $V_{column}$, $V_M$, $\varepsilon_T$, $\varepsilon_0$, $\varepsilon_i$ for 18 columns;
   see the caveat in §2.3).
9. **Gritti, F.; Cavazzini, A.; Marchetti, N.; Guiochon, G.** "Comparison between the
   efficiencies of columns packed with fully and partially porous C18-bonded silica materials."
   *J. Chromatogr. A* **1157** (2007) 289–303.
   [doi:10.1016/j.chroma.2007.05.030](https://doi.org/10.1016/j.chroma.2007.05.030) — abstract
   (internal porosity 0.19 Halo vs 0.42 fully porous; Halo geometry 1.7 µm core + 0.5 µm shell).
10. **Song, H.; Desmet, G.; Cabooter, D.** *J. Chromatogr. A* **1625** (2020) 461285.
    [doi:10.1016/j.chroma.2020.461285](https://doi.org/10.1016/j.chroma.2020.461285) — abstract
    ($\varepsilon_{pz}\approx0.5$ measured on Zorbax Eclipse Plus C18).
11. **Gritti, F.; McDonald, T.; Gilar, M.** "Impact of the column hardware volume on resolution
    in very high pressure liquid chromatography non-invasive investigations." *J. Chromatogr. A*
    **1420** (2015) 54–65. [doi:10.1016/j.chroma.2015.09.079](https://doi.org/10.1016/j.chroma.2015.09.079)
    — abstract (2.1 × 50 mm Waters columns incl. 1.6 µm CORTECS-C18+, "hold-up volume ≃ 80–90 µL";
    "column hardware volume (≃ 1.7 µL)").
12. **Dolan, J. W.** "HPLC Solutions #107: Column Volume for Superficially Porous Particles."
    [sepscience.com](https://www.sepscience.com/hplc-solutions-107-column-volume-for-superficially-porous-particles-6940)
    — partially read (see §7 item 6).
13. **Handlovic, T. T.; Dhaubhadel, U.; Horáček, O.; Novák, M.; Nováková, L.; Armstrong, D. W.**
    "Implications of Extra-column Effects for Targeted or Untargeted Microflow LC-MS."
    *ACS Meas. Sci. Au* **5** (2025) 332–344.
    [doi:10.1021/acsmeasuresciau.5c00015](https://doi.org/10.1021/acsmeasuresciau.5c00015);
    [PMC12183583](https://pmc.ncbi.nlm.nih.gov/articles/PMC12183583/) — read (extra-column
    volumes of five systems; pycnometric porosities 0.48 / 0.67).
14. **Gritti, F.; Guiochon, G.** "Speed-resolution properties of columns packed with new 4.6 µm
    Kinetex-C18 core-shell particles." *J. Chromatogr. A* **1280** (2013) 35–50.
    [doi:10.1016/j.chroma.2013.01.022](https://doi.org/10.1016/j.chroma.2013.01.022) — abstract
    ("their external porosities between 0.394 and 0.405").
15. **David, V.; Petre, J.; Moldoveanu, S. C.** "Challenges in the Measurement of the Volume of
    Phases for HPLC Columns." *Molecules* **30** (2025) 2062.
    [doi:10.3390/molecules30092062](https://doi.org/10.3390/molecules30092062);
    [PMC12073774](https://pmc.ncbi.nlm.nih.gov/articles/PMC12073774/) — read (marker/tracer
    limitations; no numeric $\varepsilon_{total}$ table).
16. **Redón, L.; Subirats, X.; Rosés, M.** "Evaluation of Hold-Up Volume Determination Methods
    and Markers in Hydrophilic Interaction Liquid Chromatography." *Molecules* **28** (2023)
    1372. [doi:10.3390/molecules28031372](https://doi.org/10.3390/molecules28031372);
    [PMC9920175](https://pmc.ncbi.nlm.nih.gov/articles/PMC9920175/) — read.
17. **Fekete, S.; Ganzler, K.; Fekete, J.** "Efficiency of the new sub-2 µm core-shell
    (Kinetex™) column in practice, applied for small and large molecule separation."
    *J. Pharm. Biomed. Anal.* **54** (2011) 482–490.
    [doi:10.1016/j.jpba.2010.09.021](https://doi.org/10.1016/j.jpba.2010.09.021) — abstract
    ("1.25 µm core diameter and 0.23 µm porous silica layer").
18. **Preti, R.** "Core-Shell Columns in High-Performance Liquid Chromatography: Food Analysis
    Applications." *Int. J. Anal. Chem.* **2016** (2016) 3189724.
    [doi:10.1155/2016/3189724](https://doi.org/10.1155/2016/3189724);
    [PMC4842074](https://pmc.ncbi.nlm.nih.gov/articles/PMC4842074/) — read; corroborating only
    (its "1.7 µm solid core … 0.5 µm shell … final particle size of 2.6 µm" does not add up —
    that geometry is 2.7 µm).
19. **Baker, J. S.; Vinci, J. C.; Moore, A. D.; Colón, L. A.** "Physical characterization and
    evaluation of HPLC columns packed with superficially porous particles." *J. Sep. Sci.* **33**
    (2010) 2547–2557. [doi:10.1002/jssc.201000251](https://doi.org/10.1002/jssc.201000251) —
    abstract only (see §7 item 2).
20. **Gritti, F.; Leonardis, I.; Abia, J.; Guiochon, G.** "Physical properties and structure of
    fine core–shell particles used as packing materials for chromatography: Relationships
    between particle characteristics and column performance." *J. Chromatogr. A* **1217** (2010)
    3819–3843. [doi:10.1016/j.chroma.2010.04.026](https://doi.org/10.1016/j.chroma.2010.04.026)
    — abstract only (see §7 item 1).
21. **Zhang, Y.; Wang, X.; Mukherjee, P.** *J. Chromatogr. A* **1216** (2009) 4597–4605.
    [doi:10.1016/j.chroma.2009.03.071](https://doi.org/10.1016/j.chroma.2009.03.071) — not read;
    the source ref. 1 cites for "15%–25% lower total porosity".
22. **Guiochon, G.; Gritti, F.** "Shell particles, trials, tribulations and triumphs."
    *J. Chromatogr. A* **1218** (2011) 1915–1938.
    [doi:10.1016/j.chroma.2011.01.080](https://doi.org/10.1016/j.chroma.2011.01.080) — not read.
23. **Advanced Materials Technology / MAC-MOD**, *HALO Columns catalog* (PDF, text-extracted
    with `pdftotext`) — read; states "1.7 µm Core Size" for the 2.7 µm particle and no other
    core/shell or porosity figures.
24. **Waters Corporation**, CORTECS product pages and 2013 launch press release
    ([waters.com](https://www.waters.com/nextgen/us/en/products/columns/cortecs-columns.html),
    [prnewswire](https://www.prnewswire.com/news-releases/waters-introduces-cortecs-columns-featuring-solid-core-particle-technology-211776611.html))
    — read; qualitative only ("a solid, impermeable silica core encased in a porous silica outer
    layer"), no dimensions or porosity. See §7 item 3.

---

## 7. What I could NOT verify

1. **Gritti, Leonardis, Abia & Guiochon (2010), ref. 20** — the single most on-topic primary
   source: nine complementary characterizations of Halo and Kinetex particles including
   **inverse size-exclusion chromatography, pycnometry and total pore blocking**, exactly the
   methods the ticket names. OpenAlex reports `oa_status: closed`; ScienceDirect returns
   HTTP 403 (known failure, not retried beyond once). Abstract only — and its abstract carries
   no porosity numbers. Every core–shell porosity in §3 would ideally be checked against it.
2. **Baker, Vinci, Moore & Colón (2010), ref. 19** — the abstract states verbatim that
   "Total, external, internal, and shell porosities among the four different columns were
   evaluated and compared" for Kinetex 1.7 and 2.6 µm, Halo 2.7 µm and a sub-2 µm totally
   porous column. Those are precisely the four numbers this document needed. Wiley paywall;
   the numbers are not in the abstract. **Biggest single gap.**
3. **CORTECS core diameter and shell thickness** — not found in any source, primary or vendor.
   Waters' own pages (ref. 24) are qualitative; the `waters.com` library entry for the CORTECS
   technical brochure timed out; no peer-reviewed paper I could reach states the dimensions
   even where CORTECS columns are characterized (refs. 11, and Gritti's 2014 *J. Sep. Sci.*
   37, 3418 on 1.6 µm CORTECS production columns, whose abstract gives plate heights only).
   Consequence: §3.2's $\rho$ table has no CORTECS row, and §4.3's argument 1 is made for the
   $\rho$ = 0.6–0.74 range of comparable products rather than for the actual particle.
4. **Neue, *HPLC Columns* (1997)** — not attempted; paywalled. **Snyder, Kirkland & Dolan,
   *IMLC* 3rd ed.** — only the publisher's reading sample (front matter) is reachable, as
   already recorded in `plate-count-from-widths.md` §7 item 8. Ref. 12 (Dolan, same author) is
   the closest reachable proxy for the textbook column-volume rule, and it is a training page,
   not the textbook.
5. **LCGC / chromatographyonline.com** — HTTP 403 again. A directly on-topic article
   ("Measurement of Interstitial Space Dispersion in Packed Bed Columns: Comparison of
   Superficially Porous and Fully Porous Particles") appeared in search results and could not
   be opened. No LCGC text is relied on anywhere in this document.
6. **Ref. 12 (Dolan #107) is only partly verified.** The opening — including "a column packed
   with fully porous particles has a total column porosity of about 60%" — was read verbatim
   from the live page. The remainder (the $V_M = 0.5\times10^{-3}L d_c^2$ formula, "within
   ±10%", the 75% shell / 25% core split, "12.5%", "10–15% less") sits behind a free-
   registration wall and is quoted **as rendered by the fetch tool**, not verified verbatim.
   Same posture as `plate-count-from-widths.md` §7 item 9. The formula is independently
   corroborated by its own arithmetic (§2.4 shows it is dimensionally an $\varepsilon$ = 0.637
   estimator), which is why it is used only as corroboration.
7. **DeStefano, Boyes, Schuster & Kirkland (2014), *J. Chromatogr. A*** — a PMC record exists
   (PMC4254563) but Europe PMC returns no full-text XML and both PDF routes returned non-PDF
   payloads. Not read. It compares HALO 2 µm superficially porous against sub-2 µm fully
   porous and may carry porosity values.
8. **Ref. 11's hold-up volumes are a rounded range across five columns** ("≃ 80–90 µL") and
   could not be split per column, so the [derived] 0.46–0.52 in §2.3/§3.4 bounds both
   architectures together. How that paper defined and measured hold-up volume is also not
   stated in the abstract, and the full text was not reachable.
9. **Ref. 1's "15%–25% lower total porosity" claim** is quoted from its text but traced only as
   far as its citations [25] (ref. 21, Zhang 2009) and [31]; neither was read. The claim is
   corroborated independently by §3.5's [derived] structural bands and by ref. 12, so nothing
   rests on it alone.
10. **Ref. 8's numbers were read from the JATS table markup, and parts of that table are
    wrong.** Several $\varepsilon_T$ values are physically impossible (Luna HILIC 0.88), and
    Table 1's $V_{column}$ column disagrees with column geometry for at least two rows
    (YMC Triart DIOL, Ascentis Express CN). Only the Ascentis Express cluster (0.55–0.60) is
    used, and it is used as a band ceiling, not as a central value.
11. **Halo 2.0 µm core diameter** — not published in refs. 4 or 23 (the catalog gives a core
    size only for the 2.7 µm particle). The $\rho$ = 0.60 used in §3.2's consistency check is
    **[derived]** by fitting ref. 3's own measured numbers, not read from a source; it should
    be treated as "the value that makes their table self-consistent".
12. **No source recommends a default $\varepsilon_{total}$ for software.** None was found —
    not a textbook, not a vendor, not a modelling paper. Every value in §5 is [derived]
    consensus over §2–§3 plus the design judgement stated in §5.4.
13. **The lab column's own numbers are not fully auditable.** `validation/method.csv` now
    records `t0,0.525` (driver-read 2026-08-31 from the run-1 chromatogram, superseding the
    retracted 0.6) with `t0_marker,solvent front` — no marker compound was injected, and the
    precision of the read is not recorded. The dwell volume is the instrument's own value by
    the driver's decision of 2026-09-02, not a measurement. The extra-column volume of that
    specific ACQUITY H-Class was never measured, so §4.4's attribution of the ~30 µL excess
    to plumbing is inference from ref. 13's measurements on *other* instruments (including
    an I-Class Plus, not an H-Class), not a measurement of this one.
14. **Pharmacopoeias carry nothing on this.** USP ⟨621⟩ (read in full for
    `plate-count-from-widths.md`) defines no column porosity and offers no geometric $t_0$
    estimate; the question does not arise there. Ph. Eur. 2.2.46 not read.

---

*Compiled 2026-08-30 for wayfinder ticket #33. Amended 2026-09-03 (map ticket #39): §4.3,
§4.4, §5.2, §5.3 and §7 item 13 rewritten to the re-read $t_0$ = 0.525 min and the #34
decision. Research only; no engine changes.*
