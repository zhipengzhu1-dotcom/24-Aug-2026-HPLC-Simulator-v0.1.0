# Estimating the Dead Time $t_0$ from Column Geometry

Research notes for the geometry fallback promised by SPEC §4 ("**measured-first**: marker
time (min) primary; geometry estimate as labeled fallback that stamps predictions
lower-confidence") and by SPEC §6 diagnostic 6 ("**Estimated-t0 stamp** on all outputs when
the geometry fallback was used"). No such estimator exists in the engine: `Method` carries
`t0_is_measured` and `session.py` round-trips `t0_source`, but nothing computes the
fallback. This document establishes what it should be.

Companion to `gradient-elution-math.md` (the normative math; cited as *GEM* with its
section numbers) and `plate-count-from-widths.md` (cited as *PCW*). Audience: whoever
implements the estimator and anyone auditing its numbers.

Every equation and claim is tagged with the source that owns it. Equations I derived myself
are tagged **[derived]** with the derivation shown. Numbers I computed with the engine are
tagged **[computed]** and the script is reproducible from §6. Section 8 lists everything I
could **not** verify against a primary source. Units follow CLAUDE.md: minutes, mL, mm, µm,
°C; $\varphi$ is a fraction 0–1.

---

## 1. Symbol table

| Symbol | Meaning | Units | Notes |
|---|---|---|---|
| $t_0$ | column dead time; engine's `Method.t0` | min | USP ⟨621⟩ calls this the **hold-up time** $t_M$ (§2.1) |
| $V_M$ | column hold-up (void, dead) volume | mL | $=F\,t_0$ |
| $F$ | flow rate | mL/min | |
| $L$ | column length | mm | |
| $d_c$ | column internal diameter | mm | |
| $V_{\text{col}}$ | geometric volume of the empty tube, $\tfrac{\pi}{4}d_c^2L$ | mL | 0.34636 mL for 2.1 × 100 mm |
| $\varepsilon_T$ | **total** porosity of the packed bed | — | interstitial **+** intraparticle |
| $\varepsilon_e$ | external (interstitial, interparticle) porosity | — | ~0.4 for a well-packed bed (§3.3) |
| $\varepsilon_p$ | intraparticle (pore) porosity of the particles | — | |
| $\rho$ | core-to-particle diameter ratio of a core-shell particle | — | $\rho=0$ fully porous, $\rho=1$ non-porous |
| $d_p$ | particle diameter | µm | |
| $\tau$ | $t_D + t_{\text{init}}$, pre-gradient isocratic period (GEM §1) | min | 1.4375 min for the lab method |
| $b_e$ | gradient steepness, natural-log (GEM §1.3) | — | $=t_0\Delta\varphi S_e/t_G$ |
| $k_0,\;S_e$ | the fitted per-peak LSS parameters (GEM §1.1) | — | |

---

## 2. The relation, and which porosity it takes

### 2.1 $V_M = F\,t_0$ is pharmacopoeial; the geometric form is not

USP–NF ⟨621⟩ *Chromatography* (Stage 4 harmonized, official 2022-12-01; ref. 1, read
directly) defines the quantity the engine calls $t_0$ and gives exactly one way to get a
volume from it. Verbatim:

> **Hold-up time ($t_M$):** Time required for elution of an unretained component (see
> Figure 1, baseline scale being in minutes or seconds).
>
> **Hold-up volume ($V_M$):** Volume of the mobile phase required for elution of an
> unretained component. It may be calculated from the hold-up time and the flow rate ($F$)
> in milliliters per minute using the following equation: $V_M = t_M \times F$

and the retention factor is defined against it, $k = (t_R - t_M)/t_M$, with $V_M$ named
"volume of the mobile phase". **⟨621⟩ never estimates $V_M$ from column dimensions.** The
pharmacopoeial position is that the hold-up volume is a *measured* quantity — the same
posture ⟨621⟩ takes on plate count (PCW §1.4), and the reason SPEC §4 is measured-first.

So the geometric form is an engineering estimate, not a compendial one, and it must be
labelled as such. Its sources are the manufacturers (§3.1) and the column-characterisation
literature (§3.2).

### 2.2 The geometric form and what $\varepsilon$ denotes

$$\boxed{\;t_0 \;=\; \frac{V_M}{F} \;=\; \frac{\varepsilon_T\,\pi\,(d_c/2)^2\,L}{F}\;}$$

The relation is stated as $\varepsilon_T = F t_0 / V_{\text{col}}$ — the same equation
rearranged — as Eq. 9 of Broeckhoven, Cabooter & Desmet, *J. Pharm. Anal.* **3** (2013)
313–323 (ref. 2, read in full, open access):

> "Based on the flow rate $F$, column dead time $t_0$ and geometrical column volume
> $V_{\text{col}}$, the total column porosity is calculated as $\varepsilon_T = F t_0 /
> V_{\text{col}}$ (9)"

**$\varepsilon$ is the total porosity — interstitial plus intraparticle — and that is the
right one for dead time.** Three independent statements:

1. **The manufacturer says so explicitly.** Waters' column knowledge-base article
   WKB28079 (ref. 3, read directly), which gives the estimate the engine should implement,
   states of its own formulas: *"The formulas shown above merely reflect an estimate of the
   void volume of a packed column (interstitial volume plus the pore volume)."*
2. **The chromatographer's definition demands it.** $t_0$ is the elution time of an
   unretained, *totally permeating* marker (⟨621⟩'s "unretained component", §2.1). Such a
   molecule samples the pores as well as the interstitial space, so its elution volume is
   $\varepsilon_T V_{\text{col}}$. Interstitial-only porosity is the elution volume of a
   *totally excluded* molecule — which ⟨621⟩ names separately and only for size-exclusion
   work: *"Retention time of an unretained compound ($t_0$): In size-exclusion
   chromatography, retention time of a component whose molecules are larger than the
   largest gel pores."* **Note the collision of notation**: ⟨621⟩'s $t_0$ is the *excluded*
   (interstitial) time; the engine's `Method.t0` is ⟨621⟩'s $t_M$. The engine's name follows
   LSS practice (GEM §1), not ⟨621⟩.
3. **The retention model requires it.** GEM's whole apparatus is built on
   $k = (t_R - t_0)/t_0$ and $b_e = t_0\Delta\varphi S_e/t_G$. Both inherit $t_0$ from the
   $k$ definition, and $k$ is defined against the totally-permeating marker (⟨621⟩ again).
   Using $\varepsilon_e$ would define a different $k$ and silently rescale every fitted
   parameter.

Using the interstitial value would understate $t_0$ by roughly the ratio
$\varepsilon_e/\varepsilon_T$ — about 40% low on a fully porous column and about 15% low on
a core-shell one, on the numbers of §3.

### 2.3 Structural decomposition — where the two porosities meet

For a bed of core-shell particles with a non-porous core of relative radius $\rho$ and a
shell of porosity $\varepsilon_{\text{shell}}$, Horváth, Gritti, Kormány & Horváth,
*Molecules* **24** (2019) 2849 (ref. 4, read in full, open access; Gritti is at Waters) give
the structure as their Eqs. 4–5:

$$\varepsilon_p = \varepsilon_{\text{shell}}\,(1-\rho^3), \qquad
\varepsilon_T = \varepsilon_e + (1-\varepsilon_e)\,\varepsilon_p$$

(their Eq. 5 is written for the general bi-layer particle,
$\varepsilon_T = \varepsilon_e + (1-\varepsilon_e)[\varepsilon_o(1-\beta^3) +
\varepsilon_i(\beta^3-\rho^3)]$; the single-shell case is $\beta = 1$.) Their Table 1 uses
$\varepsilon_e = 0.4$ as the external porosity of a packed bed.

This is the mechanism behind the fully-porous/core-shell split of §3: the solid core
removes the fraction $\rho^3$ of the particle's volume from the accessible pore space, and
$\varepsilon_T$ falls with it. Setting $\rho = 0$ recovers the fully porous case. **This
equation is why the constant must be particle-type dependent**, and it is the only
mechanistic handle the engine has if a specific column's $\varepsilon_T$ is ever wanted.

---

## 3. What constant should a simulator assume?

### 3.1 The manufacturer's own numbers — and they differ by particle type

Waters KB article WKB28079, *"How do I determine column void volume?"* (ref. 3, read
directly; the article's own tag list includes **CORTECS**, ACQUITY UPLC, XBridge, XTerra).
Verbatim, complete:

> For columns with fully porous packings, use the formula pi * (r)² * L * **0.66**.
> For columns with superficially porous packings, use the formula pi * (r)² * L * **0.49**.
> […] The column radius and length units are in centimeters. […] The formulas shown above
> merely reflect an estimate of the void volume of a packed column (interstitial volume plus
> the pore volume). To understand what the actual column void volume is for a particular
> column installed on a particular system, you must make an injection with a compound that
> does not retain on the packing material.

So: **$\varepsilon_T = 0.66$ fully porous, $\varepsilon_T = 0.49$ superficially porous**,
from the vendor that makes CORTECS, in a document that names CORTECS. The 0.49 is a 26%
reduction on the fully-porous constant, and Waters itself insists the estimate is not a
substitute for a marker injection.

Note that the widely-quoted "$\varepsilon \approx 0.65$–$0.70$" rule of thumb sits at or
just above Waters' fully-porous 0.66; I could not source the 0.70 end of it to a primary
document (§8).

### 3.2 Measured total porosities

| Column | Particle | $\varepsilon_T$ | How measured | Source |
|---|---|---|---|---|
| Zorbax SB-C18, 4.6 × 250 mm, 5 µm | fully porous | **0.526** | $Ft_0/V_{\text{col}}$, uracil marker | ref. 2 |
| Ascentis Express C18, 4.6 × 250 mm, 5 µm | superficially porous | **0.460** | $Ft_0/V_{\text{col}}$, uracil marker | ref. 2 |
| HALO SPP vs. ACQUITY FPP | — | SPP **15–25% lower** than FPP | literature survey | ref. 2 |

Ref. 2 verbatim: *"For the Zorbax and Ascentis Express columns, values for $\varepsilon_T$
of 0.526 and 0.460 respectively were found"*, and *"Based on values found for
$\varepsilon_T$ in literature […] the HALO particles have a 15%–25% lower total porosity
than Acquity particles"*.

Two things follow, and they pull in opposite directions:

- **The direction of the fully-porous/core-shell split is confirmed** by an independent
  peer-reviewed measurement and by a literature survey: core-shell columns really do have
  lower $\varepsilon_T$, by 13% (0.460 vs 0.526 on ref. 2's own pair) to 15–25% (its survey)
  to 26% (Waters' constants).
- **The absolute level is not agreed.** Waters says 0.66 for fully porous; ref. 2 measured
  0.526 on a fully porous column — Waters' constant is **+25% high** against that
  measurement. For core-shell, Waters says 0.49 against ref. 2's measured 0.460 — **+6.5%
  high**. A ±25% spread between two primary sources on the *same particle class* is the
  honest accuracy floor of any geometry estimate (§5).

### 3.3 External porosity, for reference

Ref. 4's Table 1 takes $\varepsilon_e = 0.4$ for a packed bed. A search summary of Gritti &
Guiochon's Kinetex work reported external porosities of 0.394–0.405 for 4.6 µm Kinetex
particles, but I could not reach that paper's text and do not rely on it (§8). Combining
$\varepsilon_e = 0.4$ with the measured $\varepsilon_T$ of §3.2 through §2.3's Eq. 5 implies
$\varepsilon_p \approx 0.21$ (Zorbax) and $\varepsilon_p \approx 0.10$ (Ascentis Express) —
both lower than the ~0.5 one would expect of a mesoporous silica shell, which is a sign that
the measured $\varepsilon_T$ values of ref. 2 sit at the low end of the plausible range (its
marker was uracil, which under-reads — §5.2). **Flagged, not resolved** (§8).

### 3.4 CORTECS specifically

I could **not** find a primary source stating the core diameter, shell thickness, particle
porosity or total porosity of the Waters CORTECS 1.6 µm particle. Waters' product and
particle-technology pages describe it qualitatively ("solid-core", "lower particle
porosity") without numbers; the two peer-reviewed characterisations of exactly this
packing —

- Gritti, Shiner, Fairchild & Guiochon, *J. Chromatogr. A* **1334** (2014) 30–43,
  *"Evaluation of the kinetic performance of new prototype 2.1 mm × 100 mm narrow-bore
  columns packed with 1.6 µm superficially porous particles"* (ref. 5), and
- Gritti et al., *J. Sep. Sci.* (2014), *"Characterization and kinetic performance of
  2.1 × 100 mm production columns packed with new 1.6 µm superficially porous particles"*
  (ref. 6)

— are the exact column format the app defaults to, written by Waters-affiliated authors, and
both are paywalled (ScienceDirect and Wiley returned HTTP 403; ref. 5's abstract was read via
Europe PMC and contains no porosity figure). **This is the single most valuable unread source
for this ticket** (§8 item 1).

Consequently the engine's core-shell constant rests on Waters' generic 0.49, not on anything
specific to CORTECS 1.6 µm.

---

## 4. The driver's column: what the measured $t_0$ implies

This is the one piece of measured ground truth on the exact column the app defaults to, so
it is worked in full.

### 4.1 The arithmetic

From `validation/method.csv`: column 2.1 mm i.d. × 100 mm, particle 1.6 µm, $F$ = 0.4
mL/min, `t0,0.6,min,measured marker time`.

$$V_{\text{col}} = \frac{\pi}{4}d_c^2 L = \frac{\pi}{4}(0.21\;\text{cm})^2(10\;\text{cm}) = 0.34636\;\text{mL}$$
$$V_M = F\,t_0 = 0.4 \times 0.6 = 0.24000\;\text{mL}$$
$$\varepsilon_T = \frac{V_M}{V_{\text{col}}} = \frac{0.24000}{0.34636} = \boxed{0.6929}$$

**[computed]** — this confirms the driver's independent calculation exactly.

### 4.2 The sweep, against every candidate constant

| $\varepsilon_T$ | provenance | predicted $t_0$ (min) | vs. measured 0.6 min |
|---|---|---|---|
| 0.70 | common rule of thumb (unsourced, §8) | 0.6061 | **+1.0%** |
| **0.6929** | **implied by the measured $t_0$** | **0.6000** | **—** |
| 0.66 | **Waters, fully porous** (ref. 3) | 0.5715 | **−4.8%** |
| 0.65 | low end of the rule of thumb | 0.5628 | −6.2% |
| 0.55 | — | 0.4762 | −20.6% |
| 0.526 | measured, Zorbax FPP (ref. 2) | 0.4555 | −24.1% |
| 0.50 | — | 0.4330 | −27.8% |
| **0.49** | **Waters, superficially porous** (ref. 3) | **0.4243** | **−29.3%** |
| 0.460 | measured, Ascentis Express SPP (ref. 2) | 0.3983 | −33.6% |

**The measured $t_0$ behaves like a fully porous column, not a solid-core one.** It lands
4.8% above Waters' fully-porous constant and 41% above Waters' own core-shell constant for
the very product line Waters makes. Applying the correct-by-provenance constant (0.49, the
column *is* CORTECS solid-core) would put $t_0$ out by **−29.3%**.

### 4.3 Which of the explanations survives

Four candidate explanations, tested:

**(a) The marker was retained.** For a candidate $\varepsilon_T$, the retention factor the
marker would have to carry to reach 0.6 min is $k = 0.6/t_0(\varepsilon_T) - 1$:

| $\varepsilon_T$ | implied marker $k$ | implied excess volume |
|---|---|---|
| 0.66 | 0.050 | 11.4 µL |
| 0.526 | 0.317 | 57.8 µL |
| 0.49 | 0.414 | 70.3 µL |

**[derived/computed].** `method.csv` records `t0_marker` as **blank** — nobody wrote down
which marker was used, though `PROTOCOL.md` §1 instructs "uracil or thiourea". A uracil $k$
of 0.05 on a shield-phase C18 at high aqueous is unremarkable; a $k$ of 0.41 is not a
"marker" at all. So marker retention can comfortably absorb the gap to the *fully-porous*
constant and cannot plausibly absorb the gap to the core-shell one.

**(b) Extra-column volume was included.** A marker time measured at the detector includes
the instrument's injector-to-detector volume, which is not column void volume. To explain
$\varepsilon_T = 0.49$ this would have to be **70 µL** — implausible for an ACQUITY UPLC
H-Class, an instrument built for 2.1 mm columns whose whole design goal is a small
extra-column volume. To explain 0.66 it need only be **11 µL**, which is entirely ordinary.
I did not find a primary Waters figure for the H-Class extra-column volume (§8), so this is
argued from the order of magnitude, not from a cited number.

**(c) 0.6 min is rounded.** It is recorded to one decimal while every retention time in
`run1–4.csv` carries three. At ±0.05 min the implied $\varepsilon_T$ spans
**0.635–0.751** **[computed]** — a ±8.3% band that still never comes near 0.49.

**(d) CORTECS 1.6 µm is not well described by the generic 0.49.** Possible, and untestable
here: §3.4 found no primary source for the particle's geometry. Inverting §2.3's Eq. 5 with
$\varepsilon_e = 0.4$ and a shell porosity of 0.5, $\varepsilon_T = 0.693$ would require
$\rho \approx 0.28$ — a core just 0.45 µm across in a 1.6 µm particle, which is not a
solid-core particle in any meaningful sense **[derived]**. So (d) alone cannot carry the gap
either.

**Verdict.** No single explanation reaches from 0.49 to 0.693; (a) and (b) together
comfortably reach from 0.66 to 0.693. The most defensible reading is that **the driver's
measured 0.6 min is a marker-plus-system time roughly consistent with a fully porous
constant, and is therefore an over-estimate of the true CORTECS column hold-up volume by
something between 5% and 40%** — but it is what the retention fit was calibrated on, and
§6 shows that is what actually matters. The honest statement for the UI is the one in §7
item 5: report the implied $\varepsilon_T$ back to the user and let them see that 0.693 is
not a solid-core number.

---

## 5. How close does the estimate land, and how markers mislead

### 5.1 The geometry estimate

There is no published study I could reach that measures "geometric estimate vs. measured
$t_0$" as a distribution over many columns (§8). What the primary sources do support is a
band assembled from disagreements:

| Comparison | Error of the estimate |
|---|---|
| Waters 0.66 vs. measured 0.526 (Zorbax FPP, ref. 2) | **+25%** |
| Waters 0.49 vs. measured 0.460 (Ascentis Express SPP, ref. 2) | **+6.5%** |
| Waters 0.49 vs. measured 0.693 (driver's CORTECS, §4) | **−29%** |
| Waters 0.66 vs. measured 0.693 (driver's CORTECS, §4) | **−4.8%** |

**So: ±25–30% is the honest band to quote for a geometry estimate, and the sign is not
predictable.** Rimmer, Simmons & Dorsey, *J. Chromatogr. A* **965** (2002) 219–232 (ref. 7,
abstract read) put the field's state bluntly and it has not been superseded:

> "The seemingly simple process of measuring the mobile phase volume, $V_0$, in
> reversed-phase liquid chromatography has eluded unambiguous agreement for over 25 years.
> Examples exist in the literature where the reported volume is physically impossible,
> either equal to or larger than the empty column volume, or being so small that it would
> represent a total porosity of half the theoretical limit for well-packed columns. […] At
> this time, there is still no consensus for the best method of measurement, and workers are
> urged to critically examine values they measure, to insure they are at least physically
> possible."

That last clause is a directly implementable engine feature (§7 item 5).

### 5.2 How the markers themselves mislead

The measured $t_0$ is not a gold standard either. Primary evidence, worst first:

- **Marker choice moves the answer by tens of percent.** Ribar, Lukšič & Kralj Cigić,
  *J. Chromatogr. A* **1706** (2023) 464245 (ref. 8, abstract read) compared uracil,
  phloroglucinol and N,N-dimethylformamide against deuterated acetonitrile as an
  isotopically-labelled mobile-phase component, on C8 and C18, over 25 compositions:
  > "the composition of the mobile phase has been shown to have a significant effect on
  > deuterated acetonitrile and other investigated void volume markers, demonstrating the
  > fact that both void volume markers and acetonitrile itself exhibit retention-like
  > behaviour. […] The comparison of void volumes, obtained with conventional neutral void
  > volume markers, revealed the former to be **24–36% lower** than the void volume obtained
  > using deuterated acetonitrile"

  Conventional markers **under-read** $V_M$ — which is the opposite direction from the
  driver's column, and makes §4's excess harder to explain by porosity alone.
- **Methods disagree systematically.** Gritti, Kazakevich & Guiochon, *J. Chromatogr. A*
  **1161** (2007) 157–169 (ref. 9, abstract read) compared three non-destructive methods
  (packing-material accounting, static pycnometry, minor-disturbance):
  > "The experimental results of these three non-destructive methods are compared. They
  > exhibit significant, systematic differences. Pycnometry underestimates $V_M$ by a few
  > percent for adsorbents having a high carbon content. The results of the MDM method depend
  > strongly on the choice of the binary solution used and may underestimate or overestimate
  > $V_M$."
- **Organic markers do not fully permeate.** David, Petre & Moldoveanu, *Molecules* **30**
  (2025) 2062 (ref. 10, read in full, open access):
  > "it is likely that the organic tracers do not entirely penetrate the fine pores of the
  > stationary phase, and therefore, their measured retention times do not represent the real
  > porosity of the chromatographic bed"

  and on residual retention: *"Comparison of $t_0$ values obtained by various alternatives
  in RP-LC with organic tracers shows that there are differences explained by a very weak
  interaction still existing between the molecules of organic tracers and functionalities
  from the stationary phase."*
- **Salt markers measure the wrong porosity outright.** Ref. 10: *"at low concentrations of
  these salts found in the injected sample (below $10^{-3}$ moles/L), their ions can not
  penetrate into the fine pore space of stationary phase particles due to the Donnan
  salt-exclusion effect. The retention volume of NaNO₃ in this case indicates only the
  **external porosity** of the stationary phase."* — i.e. a dilute nitrate injection returns
  $\varepsilon_e$, not $\varepsilon_T$, and would under-read $t_0$ by ~40% on a fully porous
  column. **Do not accept a nitrate/bromide marker time as $t_0$ without a warning.**
- **In uracil's favour**, ref. 10 reports it is at least *stable*: *"There is practically no
  influence of mobile phase composition or temperature on the retention time measured for
  uracil in RP-LC"*, across the compositions and 15–50 °C of their Figs. 1–3, and it is
  *"more often used due to its convenient UV detection and the stability of stock
  solutions"*. Stable is not the same as correct — ref. 8 puts uracil-class markers 24–36%
  below the thermodynamic $V_M$ — but for the engine's purpose (a $t_0$ that the $k$
  definition is anchored to) a *reproducible* marker is exactly what is wanted. See §6.4.
- **Solvent disturbance peaks are worse.** Redón, Subirats & Rosés, *Molecules* **28** (2023)
  1372 (ref. 11, abstract read): *"The injection of pure solvents to produce minor base-line
  disturbance as hold-up markers is strongly discouraged, since solvent peaks are complex to
  interpret and depend on the ionic strength of the eluent."* Relevant because Agilent's LC
  handbook (ref. 12, read) suggests exactly that shortcut: *"You can estimate your column
  void volume by looking at a chromatogram and measuring the time from the start of the
  chromatogram to the first disturbance on the baseline."*

---

## 6. What a $t_0$ error costs this engine

### 6.1 Where $t_0$ enters

From GEM §2.2 and §1.3, $t_0$ appears in four places in the prediction:

$$t_R = \tau + \underbrace{t_0}_{\text{(i)}} + \frac{t_0}{b_e}\ln\!\Big[b_e\Big(k_0 - \underbrace{\frac{\tau}{t_0}}_{\text{(iii)}}\Big) + 1\Big],
\qquad b_e = \underbrace{\frac{t_0\,\Delta\varphi\,S_e}{t_G}}_{\text{(ii)}}$$

**[derived] The key cancellation.** Substituting (ii) into the prefactor,

$$\frac{t_0}{b_e} = \frac{t_G}{\Delta\varphi\,S_e}$$

**$t_0$ vanishes from the prefactor entirely.** What is left is

$$t_R = \tau + t_0 + \frac{t_G}{\Delta\varphi S_e}\,\ln\!\Big[\frac{\Delta\varphi S_e}{t_G}\big(t_0k_0 - \tau\big) + 1\Big]$$

so for a well-retained peak ($t_0k_0 \gg \tau$) the model depends on $t_0$ only through the
**product $t_0k_0$** and the bare additive $+t_0$. The two-run fit determines $S_e$ from the
*shape* of the $t_R$-versus-$t_G$ response and $t_0k_0$ from its *level*; a wrong $t_0$ is
therefore absorbed into $k_0$ with the product nearly preserved, and the prediction barely
moves. This is a genuine near-invariance of the model, not an accident of the data.

### 6.2 Case A — the v0.1 path: fit and predict with the same (wrong) $t_0$

The engine always refits from the scouting runs (SPEC §8: session persistence is
inputs-only, the fit recomputes on load), so a wrong $t_0$ is wrong *consistently*. Refitting
all three lab compounds from `run1.csv`/`run2.csv` and predicting the held-out
`run3.csv` ($t_G$ = 25, inside the bracket) and `run4.csv` ($t_G$ = 60, outside it):

| $t_0$ | implied $\varepsilon_T$ | $\Delta t_0$ | $\Delta S$ (U1) | $\Delta k_0$ (U1) | $\Delta N$ (U1) | $\Delta t_R$ run 3 (U1/U2/U3) | $\Delta t_R$ run 4 (U1/U2/U3) |
|---|---|---|---|---|---|---|---|
| 0.360 | 0.416 | −40% | −9.65% | +26.4% | +8.40% | +0.249/+0.211/+0.148% | −0.318/−0.263/−0.172% |
| 0.4243 | 0.490 | −29.3% | −7.24% | +14.8% | +6.11% | +0.182/+0.155/+0.108% | −0.233/−0.193/−0.126% |
| 0.480 | 0.554 | −20% | −5.05% | +8.04% | +4.15% | +0.125/+0.106/+0.074% | −0.160/−0.132/−0.086% |
| 0.540 | 0.624 | −10% | −2.59% | +3.09% | +2.06% | +0.062/+0.053/+0.037% | −0.080/−0.066/−0.043% |
| **0.600** | **0.693** | **0** | — | — | — | — | — |
| 0.660 | 0.762 | +10% | +2.72% | −1.58% | −2.04% | −0.063/−0.053/−0.037% | +0.081/+0.066/+0.043% |
| 0.720 | 0.832 | +20% | +5.59% | −1.87% | −4.05% | −0.126/−0.106/−0.074% | +0.162/+0.133/+0.086% |
| 0.840 | 0.970 | +40% | +11.8% | +1.14% | −8.00% | −0.252/−0.213/−0.148% | +0.325/+0.266/+0.172% |

**[computed]** with the shipped engine (`fit_peak` + `predict_retention` + the #23 fitted
$N$), $\tau$ = 1.4375 min, 5 → 95 %B.

Local elasticities $\mathrm{d}\ln X/\mathrm{d}\ln t_0$ at $t_0$ = 0.6 **[computed]**:

| quantity | U1 | U2 | U3 |
|---|---|---|---|
| predicted $t_R$, $t_G$ = 25 (inside bracket) | −0.0063 | −0.0053 | −0.0037 |
| predicted $t_R$, $t_G$ = 60 (outside bracket) | +0.0080 | +0.0066 | +0.0043 |
| fitted $S$ | +0.265 | +0.255 | +0.261 |
| fitted $k_0$ | −0.229 | +0.010 | +0.944 |
| fitted $N$ | −0.205 | −0.198 | −0.202 |

Read as: **≈ 0.005% of predicted-$t_R$ error per 1% of $t_0$ error** — two orders of
magnitude smaller than the error itself. Even the −29.3% error of adopting Waters'
core-shell constant moves every held-out prediction by less than **0.24%**. Measured
against the real held-out data rather than against the $t_0$ = 0.6 prediction, the average
|Δ$t_R$| degrades only from **0.355% / 0.257%** (runs 3 / 4, the SPEC §1 figures) to
**0.504% / 0.441%**, worst peak 0.72% **[computed]** — still inside SPEC's 2% average / 5%
worst trust bar by ~4×.

**Is it systematic?** Yes — every peak moves in the same direction at a given $t_0$, and
monotonically. But the direction *flips with the extrapolation side*: inside the scouting
bracket ($t_G$ = 25) a low $t_0$ makes predictions late; outside it ($t_G$ = 60) a low $t_0$
makes them early. That is the signature of a fit that is pinned at the two scouting points
and pivoting between them — the $t_0$ error cannot move the two anchors, only the
interpolation between and beyond them. So it is a systematic bias, but a tiny one that
partly *cancels* rather than compounding.

**Early eluters do not change this.** Synthesising peaks with $k_0$ = 5, 10, 20, 50, 200 at
$S_e$ = 11.7 and refitting at $t_0 \pm 20\%$ gives held-out $t_R$ errors of +0.06%, +0.13%,
+0.16%, +0.17%, +0.14% respectively **[computed]** — the $\tau/t_0$ term (iii) is the one
place a small $k_0$ could have bitten, and it does not, even at $\tau/t_0 = 2.4$ as on this
method.

**What a wrong $t_0$ actually corrupts is the science readout, not the chromatogram.**
Adopting $\varepsilon_T = 0.49$ on this column moves the reported $S$ by −7% on all three
compounds (5.08 → 4.71, 4.99 → 4.64, 5.18 → 4.81) and $k_0$ by +15%, +8%, −16%, and the
fitted $N$ by +6% **[computed]**. $S$ is what a chromatographer reads to judge whether a
compound is small-molecule-like (GEM §1.2's 1.7–6.3 range); a systematic 7% shift in it is a
real defect even though the predicted chromatogram is untouched.

### 6.3 Case B — the dangerous one: $t_0$ wrong only at prediction time

If parameters fitted under one $t_0$ are used to predict under another, the cancellation of
§6.1 is broken and the error is **two orders of magnitude larger**. Fitting at $t_0$ = 0.6
and predicting run 3 at a different $t_0$ **[computed]**:

| $t_0$ used to predict | $\Delta t_R$ run 3, U1/U2/U3 |
|---|---|
| 0.42 (−30%) | −6.89 / −5.83 / −4.05% |
| 0.48 (−20%) | −4.17 / −3.53 / −2.52% |
| 0.54 (−10%) | −1.71 / −1.46 / −1.15% |
| 0.66 (+10%) | +2.61 / +2.17 / +1.26% |
| 0.72 (+20%) | +4.54 / +3.79 / +2.34% |
| 0.78 (+30%) | +6.35 / +5.31 / +3.35% |

Elasticities **[computed]**: +0.214 (U1), +0.180 (U2), +0.120 (U3) — i.e. **≈ 0.12–0.21% of
predicted-$t_R$ error per 1% of $t_0$ error, same sign as the $t_0$ error, systematic across
every peak, and worst for the least-retained one.** A 20% $t_0$ error blows the SPEC 2%
average bar on its own.

**Engine consequence.** The mismatched case must be made unreachable. It is, today, by SPEC
§8's inputs-only persistence — the fit recomputes on load from the same stored $t_0$. The
rule to protect is: **never carry fitted `RetentionParams` across a change of `Method.t0`
without refitting.** Anything that would break it — a saved-parameters format, a "what if
$t_0$ were…" slider, method transfer to a second column — inherits Case B's 0.12–0.21%
per 1%.

### 6.4 Why this changes the posture on the geometry fallback

The measured-first rule of SPEC §4 is right, but §6.2 shows *why* it is right, and it is not
the reason one would guess. A geometry $t_0$ does not wreck the predicted chromatogram —
within v0.1's scope (same column, same flow, same $\varphi_0/\varphi_f$; only $t_G$ and the
hold vary) it is nearly free. What it wrecks is:

1. **the reported $S$ and $k_0$** (§6.2), which is what the lower-confidence stamp should
   actually be warning about;
2. **anything outside v0.1's scope.** Change the flow or the column and the fit no longer
   travels with its own error — that is Case B.

So the stamp's wording matters: *"$t_0$ estimated from geometry — retention predictions for
these gradients are barely affected, but the fitted $S$, $k_0$ and $N$ carry a systematic
error of roughly 0.25× the $t_0$ error, and the parameters should not be transferred to a
different flow rate or column."* That is a more useful and more honest warning than a bare
"lower confidence".

---

## 7. Recommendations for the engine

1. **Implement the estimator as** **[ref. 3]**

   $$V_M\;[\text{mL}] = \varepsilon_T \cdot \frac{\pi}{4}\,d_c^2\,L \times 10^{-3},
   \qquad t_0\;[\text{min}] = \frac{V_M}{F}$$

   with $d_c$, $L$ in **mm** and $F$ in **mL/min** — the repo's units. The single numeric
   constant is

   $$\frac{\pi}{4}\times 10^{-3} = 7.853981633974483\times 10^{-4}\;\;\text{mL}\cdot\text{mm}^{-3}$$

   so `v_m = eps * 7.853981633974483e-4 * d_c_mm**2 * l_mm`. Do not hard-code a rounded
   0.000785; write it as `math.pi / 4.0 / 1000.0`, in keeping with GEM §6's insistence on
   exact constants.

2. **Two porosity constants, selected by particle type** (ref. 3, §3.1):

   | packing | $\varepsilon_T$ |
   |---|---|
   | fully porous | **0.66** |
   | superficially porous / solid-core | **0.49** |

   This needs an input the engine does not have: `Method` carries `column_length_mm`,
   `column_id_mm` and `particle_um` but no particle-type flag. Add one
   (`particle_is_solid_core: bool | None = None`). **When it is unknown, use 0.66 and warn**
   — it is the milder assumption in both directions (§4.2 shows the fully-porous constant is
   within 5% on the one column we can check, while the core-shell constant is 29% out) and
   ⟨621⟩ offers no default at all. *Judgement*, on ref. 3's two constants plus §4.

3. **Raise the estimator only when `column_id_mm` is present.** `default_plate_count` in
   `width.py` is the precedent: it raises a typed `ValueError` naming the missing field
   rather than inventing a geometry. Do the same, and note that `column_id_mm` is currently
   optional metadata that nothing consumes — this ticket makes it load-bearing.

4. **Keep the measured-first precedence and the existing stamp.** `Method.t0_is_measured`
   and `session.py`'s `t0_source` already exist and already round-trip; the estimator feeds
   the `False` branch. This is the same precedence PCW §5 adopted for $N$ by analogy with
   this very rule — the analogy now runs in both directions.

5. **The most valuable feature is the reverse check, not the estimate.** When the user
   enters a *measured* $t_0$, compute the implied $\varepsilon_T = Ft_0/V_{\text{col}}$ and
   show it. Warn when it falls outside a plausible band. Ref. 7 asks for exactly this —
   *"workers are urged to critically examine values they measure, to insure they are at
   least physically possible"* — and on the driver's own dataset it fires usefully: 0.693 on
   a solid-core column is 41% above the manufacturer's own constant, which is worth saying
   out loud. Suggested tiers, *judgement* grounded in §3 and §5:

   - $\varepsilon_T > 1$: impossible — hard fail (more mobile phase than empty tube).
   - $\varepsilon_T$ outside $[0.35, 0.80]$: strong warning — likely a wrong flow rate, a
     retained marker, or a units slip.
   - $\varepsilon_T$ more than ~15% above the constant for the declared particle type: warn
     that the marker may be retained or the time may include extra-column volume (§4.3).
   - $\varepsilon_T$ near $\varepsilon_e \approx 0.4$ on a fully porous column: warn that a
     size-excluded marker (dilute nitrate/bromide) measures interstitial volume only
     (ref. 10, §5.2).

6. **Warn on the marker, and capture it.** `method.csv` has a `t0_marker` column and it is
   blank. Make it an input, and warn when it is absent or is an inorganic salt (§5.2). The
   marker identity is provenance the $t_0$ number is meaningless without.

7. **Say what the estimate costs, using §6's numbers, not a generic hedge.** The stamp
   should distinguish the two regimes: predictions of *these* gradients are affected at the
   ~0.005%-per-1% level (§6.2), while the fitted $S$/$k_0$/$N$ carry ~0.25× the $t_0$ error
   and must not be transferred to another flow or column (§6.3).

8. **Never let fitted parameters cross a change in `Method.t0`.** §6.3 is the only place a
   $t_0$ error is expensive. SPEC §8's inputs-only persistence already protects this; add a
   test that pins it, so a future "save the fit" feature cannot silently open the hole.

9. **Tests worth writing.** (a) the estimator against ref. 3's own worked geometry; (b) the
   2.1 × 100 mm figures of §4.1 — $V_{\text{col}}$ = 0.34636 mL, $\varepsilon_T$ = 0.6929 —
   as a reality test on the lab column; (c) the §6.2 insensitivity band, as a held-out
   prediction test: refit at $t_0 \times 0.7$ and assert every run-3/run-4 prediction still
   lands within 0.3% of the $t_0$ = 0.6 prediction; (d) the §6.3 elasticity, asserted as the
   *large* number, so the two regimes are pinned apart and a regression that starts reusing
   parameters across $t_0$ is caught.

---

## 8. What I could NOT verify

1. **CORTECS 1.6 µm's actual geometry or porosity.** No primary source found for the core
   diameter, shell thickness, particle porosity or total porosity of the particle in the
   driver's column. The two papers that would settle it — Gritti, Shiner, Fairchild &
   Guiochon, *J. Chromatogr. A* **1334** (2014) 30–43 (ref. 5) and Gritti et al.,
   *J. Sep. Sci.* (2014) (ref. 6), both on 2.1 × 100 mm columns of 1.6 µm superficially
   porous particles, both Waters-affiliated — are paywalled (ScienceDirect and Wiley HTTP
   403). Only ref. 5's abstract was read, via Europe PMC; it contains no porosity figure.
   **This is the first thing to read if anyone gets library access.** Everything §3.4 and
   §4.3(d) say about CORTECS rests on Waters' *generic* superficially-porous constant.
2. **The provenance of the "$\varepsilon \approx 0.65$–0.70" rule of thumb.** Waters' 0.66
   is sourced (ref. 3); the 0.70 figure that circulates alongside it is not. Snyder &
   Kirkland, *Introduction to Modern Liquid Chromatography*, 2nd ed. (ref. 13) was read: it
   defines total porosity as its Eq. 5.5 on p. 220, but **the equation itself is an image
   that did not survive text extraction**, and I found no numeric rule of thumb in that
   edition. The 3rd edition (Snyder/Kirkland/Dolan 2010) is paywalled — as in GEM §10 item 1
   and PCW §7 item 8, only its table of contents has ever been readable in this project.
3. **Any published "geometry estimate vs. measured $t_0$" study.** §5.1's ±25–30% band is
   *assembled by me* from four pairwise comparisons across refs. 2, 3 and the lab data. No
   source states an accuracy figure for the geometric estimate directly. Waters (ref. 3)
   says only that its formulas "merely reflect an estimate" and gives no tolerance; the
   "±15%" figure that appeared in a search-result summary of that page is **not in the
   page's text** — I re-fetched it in full and it is absent. Do not quote it.
4. **The internal consistency of ref. 2's measured $\varepsilon_T$.** §3.3 shows that
   combining its 0.526/0.460 with $\varepsilon_e = 0.4$ implies shell porosities well below
   what a mesoporous silica should have. Either $\varepsilon_e$ is lower than 0.4 on those
   columns, or the uracil marker under-read (ref. 8's 24–36%), or both. Unresolved.
5. **Gritti & Guiochon's Kinetex external porosities (0.394–0.405).** Reported only in a
   search-result summary; the paper (*J. Chromatogr. A* **1217** (2009), "Performance of
   columns packed with the new shell particles, Kinetex-C18") returned HTTP 403. **Not
   relied on** — §3.3 uses ref. 4's $\varepsilon_e = 0.4$ instead, which was read directly.
6. **ACQUITY UPLC H-Class extra-column volume.** §4.3(b) argues 70 µL is implausible and
   11 µL ordinary for that instrument, from the order of magnitude of a 2.1 mm-column UHPLC.
   I found no Waters technical document stating the figure. The argument is *judgement*, not
   a citation.
7. **The dwell time in `method.csv` is not measured.** `dwell_volume,0.375,mL,"from
   instrument spec sheet, NOT measured"`, giving $t_D$ = 0.9375 min. §6's numbers all use
   it, and $\tau = t_D + t_{\text{init}} = 1.4375$ min is 2.4 × $t_0$ on this method —
   larger than $t_0$ itself. GEM §7.6 and Molnár (GEM §3.4 step 1) are both emphatic that
   dwell must be *measured*. An error in $\tau$ enters the same equation as $t_0$ but is
   **not** absorbed by the fit the way $t_0$ is (it appears additively as well as through
   $\tau/t_0$), so it is likely the more expensive of the two unmeasured instrument
   constants. **Not analysed here — it deserves its own ticket.**
8. **The marker used for the driver's $t_0$.** `method.csv`'s `t0_marker` field is blank.
   `PROTOCOL.md` §1 instructs "uracil or thiourea" and to "Record the marker used"; it was
   not recorded. Every reading of §4.3 is weaker for it.
9. **Whether 0.6 min is a measurement or a rounded/estimated value.** `method.csv` labels it
   "measured marker time", and I take that at face value, but it is recorded to one decimal
   where every retention time in the same dataset carries three. §4.3(c) quantifies the
   rounding band; it does not resolve the question.
10. **Ph. Eur. 2.2.46 and JP 2.00 hold-up definitions.** Only USP–NF ⟨621⟩ was read (ref. 1).
    PCW §3.4 established that the three are harmonized on the plate-count constant, so they
    are very likely harmonized here too, but that is inference.
11. **MDPI HTML.** `mdpi.com` returned HTTP 403 for refs. 10 and 11; both were read through
    their PubMed Central mirrors instead (ref. 10 in full, ref. 11 abstract only). LCGC
    (`chromatographyonline.com`) was not attempted — it has returned 403 for every URL in
    this project (GEM §10 item 6, PCW §7 item 9) — so its "Harmonization of Experimental
    Methods Used to Measure the True Hold-Up Volume of Liquid Chromatography Columns" is
    unread, and no LCGC text is relied on anywhere in this document.

---

## References

"Read" = full text read directly; otherwise abstract/metadata only.

1. **USP–NF ⟨621⟩ Chromatography**, Stage 4 Harmonization, official 2022-12-01.
   [USP PDF](https://www.usp.org/sites/default/files/usp/document/harmonization/gen-chapter/harmonization-november-2021-m99380.pdf) — read.
   Definitions of hold-up time $t_M$, hold-up volume $V_M = t_M F$, retention factor
   $k = (t_R-t_M)/t_M$, and the SEC-only $t_0$/$V_0$ for a totally excluded compound.
2. **Broeckhoven, K.; Cabooter, D.; Desmet, G.** "Kinetic performance comparison of fully and
   superficially porous particles with sizes ranging between 2.7 µm and 5 µm: Intrinsic
   evaluation and application to a pharmaceutical test compound." *J. Pharm. Anal.* **3**
   (2013) 313–323. [doi:10.1016/j.jpha.2012.12.006](https://doi.org/10.1016/j.jpha.2012.12.006);
   [PMC5760962](https://pmc.ncbi.nlm.nih.gov/articles/PMC5760962/) — read.
   Eq. 9 ($\varepsilon_T = Ft_0/V_{\text{col}}$) and the measured 0.526 / 0.460.
3. **Waters Corporation**, "How do I determine column void volume? — WKB28079."
   [support.waters.com](https://support.waters.com/KB_Chem/Columns/WKB28079_How_do_I_determine_column_void_volume) — read.
   The 0.66 / 0.49 constants, the "interstitial volume plus the pore volume" definition, and
   the instruction to measure with a non-retained marker. Tagged CORTECS by Waters.
4. **Horváth, S.; Gritti, F.; Kormány, R.; Horváth, K.** "Theoretical Analysis of Efficiency
   of Multi-Layer Core-Shell Stationary Phases in the High Performance Liquid Chromatography
   of Large Biomolecules." *Molecules* **24** (2019) 2849.
   [doi:10.3390/molecules24152849](https://doi.org/10.3390/molecules24152849);
   [PMC6695945](https://pmc.ncbi.nlm.nih.gov/articles/PMC6695945/) — read.
   Eqs. 1–5 (core-shell porosity structure) and Table 1 ($\varepsilon_e = 0.4$).
5. **Gritti, F.; Shiner, S. J.; Fairchild, J. N.; Guiochon, G.** "Evaluation of the kinetic
   performance of new prototype 2.1 mm × 100 mm narrow-bore columns packed with 1.6 µm
   superficially porous particles." *J. Chromatogr. A* **1334** (2014) 30–43.
   [doi:10.1016/j.chroma.2014.01.065](https://doi.org/10.1016/j.chroma.2014.01.065) —
   **abstract only** (§8 item 1).
6. **Gritti, F.; et al.** "Characterization and kinetic performance of 2.1 × 100 mm production
   columns packed with new 1.6 µm superficially porous particles." *J. Sep. Sci.* (2014).
   [doi:10.1002/jssc.201400703](https://doi.org/10.1002/jssc.201400703) — **not read**
   (Wiley HTTP 403).
7. **Rimmer, C. A.; Simmons, C. R.; Dorsey, J. G.** "The measurement and meaning of void
   volumes in reversed-phase liquid chromatography." *J. Chromatogr. A* **965** (2002)
   219–232. [doi:10.1016/S0021-9673(02)00730-6](https://doi.org/10.1016/S0021-9673(02)00730-6) —
   abstract read (Europe PMC).
8. **Ribar, D.; Lukšič, M.; Kralj Cigić, I.** "Towards an accurate method for column void
   volume determination using liquid chromatography-mass spectrometry." *J. Chromatogr. A*
   **1706** (2023) 464245.
   [doi:10.1016/j.chroma.2023.464245](https://doi.org/10.1016/j.chroma.2023.464245) —
   abstract read (Europe PMC). The 24–36% marker deficit.
9. **Gritti, F.; Kazakevich, Y.; Guiochon, G.** "Measurement of hold-up volumes in
   reverse-phase liquid chromatography: Definition and comparison between static and dynamic
   methods." *J. Chromatogr. A* **1161** (2007) 157–169.
   [doi:10.1016/j.chroma.2007.05.102](https://doi.org/10.1016/j.chroma.2007.05.102) —
   abstract read (Europe PMC).
10. **David, V.; Petre, J.; Moldoveanu, S. C.** "Challenges in the Measurement of the Volume
    of Phases for HPLC Columns." *Molecules* **30** (2025) 2062.
    [doi:10.3390/molecules30092062](https://doi.org/10.3390/molecules30092062);
    [PMC12073774](https://pmc.ncbi.nlm.nih.gov/articles/PMC12073774/) — read.
    Marker behaviour, Donnan exclusion, pycnometry, homologous-series extrapolation.
11. **Redón, L.; Subirats, X.; Rosés, M.** "Evaluation of Hold-Up Volume Determination
    Methods and Markers in Hydrophilic Interaction Liquid Chromatography." *Molecules* **28**
    (2023) 1372. [doi:10.3390/molecules28031372](https://doi.org/10.3390/molecules28031372);
    [PMC9920175](https://pmc.ncbi.nlm.nih.gov/articles/PMC9920175/) — abstract read.
12. **Agilent Technologies**, *The LC Handbook: Guide to LC Columns and Method Development*.
    [PDF](https://sglab.net/wp-content/uploads/2019/07/Agilent_LC-Handbook.pdf) — read
    (extracted with `pdftotext`). Contains the gradient equation in $V_M$ form and the
    baseline-disturbance shortcut for estimating void volume (§5.2); **no porosity constant
    and no geometric void-volume formula.**
13. **Snyder, L. R.; Kirkland, J. J.** *Introduction to Modern Liquid Chromatography*,
    2nd ed., Wiley (1979). Total porosity is Eq. 5.5, p. 220 — read, but the equation
    survives only as an unextractable image (§8 item 2). 3rd ed.
    (Snyder/Kirkland/Dolan 2010, ISBN 978-0-470-16754-0) — **not read**, paywalled, as in
    GEM §10 item 1.

---

*Compiled 2026-08-30. Research only; no engine changes.*
