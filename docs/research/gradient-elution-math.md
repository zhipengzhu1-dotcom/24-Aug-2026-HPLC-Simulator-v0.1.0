# Gradient-Elution Math and the Two-Run Fit

Research notes for the v0.1 engine (gradient two-run fit-and-predict).
Resolves issue #2. Audience: whoever implements the engine (`src/hplcsim`) and anyone auditing its numbers.

Every equation below is tagged with the source that owns it. Equations I derived
myself (because no fetchable source stated them in the form the engine needs) are
tagged **[derived]** and shown with their derivation. Section 10 lists everything
I could **not** verify against a source.

---

## 0. Reading this document: the log-base trap

The single most common implementation bug in LSS code is mixing the two log
conventions. The literature uses both, often in the same paragraph.

| | base-10 convention (Snyder/Dolan/DryLab) | natural-log convention (Carr, Schoenmakers) |
|---|---|---|
| retention model | $\log_{10} k = \log_{10} k_w - S\varphi$ | $\ln k = \ln k_w - S_e\varphi$ |
| steepness | $b = \dfrac{t_0 \Delta\varphi\, S}{t_G}$ | $b_e = \dfrac{t_0 \Delta\varphi\, S_e}{t_G}$ |
| conversion | — | $S_e = \ln(10)\,S \approx 2.303\,S$, $\;b_e = 2.303\,b$ |
| where "2.3" shows up | inside every log/exp | nowhere |

Both conventions describe the same physics. **The engine should work internally in
the natural-log convention** ($S_e$, $b_e$) — the equations lose every stray 2.303
factor and the closed forms below become clean — and convert to/from base-10 $S$
only at the UI boundary, because working chromatographers quote $S$ in the base-10
sense (an $S$ of 4 means one decade of $k$ per 0.25 change in $\varphi$).

Every equation in this document is given in **both** forms where the distinction matters.

**A second trap of the same class: what $k_0$ means.** This document anchors the
per-peak state at the initial composition — $k_0 = k(\varphi_0)$, and $k_w = k(0)$
is the extrapolation to pure water (§1, §1.1). Two of the sources this document
leans on hardest use $k_0$ for the *other* quantity. Guillarme et al. (2022) write
$k_0$ for *"the (extrapolated) value of k in pure water"* — our $k_w$ — and $k_i$
for *"the retention factor under initial gradient conditions"* — our $k_0$. den Uijl
et al. (2021a, the review, ref. 4; 2021b, ref. 16) likewise write $\ln k_0$ —
*"often also denoted $\ln k_w$"* — for the pure-water intercept throughout their
model tables (§7.5). Anyone implementing Guillarme Eqs. 8–10 or den Uijl 2021b
Eqs. 1–5 against §1's symbol table will silently swap two parameters, and the swap
is not small: the two differ by $S_e\varphi_0$ in the log, a factor of
$10^{S\varphi_0}$ in $k$ — ×1.8 at 5 %B and ×32 at 30 %B for $S = 5$.
The rule is the same as for the log base: **read the source's definition of $k_0$
before lifting an equation, and translate at the boundary, never inside the maths.**
Found by #43 (`composition-extrapolation.md` §1, §4.3, §8 item 5).

---

## 1. Symbol table

| Symbol | Meaning | Units | Typical value / notes |
|---|---|---|---|
| $\varphi$ | volume fraction of strong solvent (organic modifier, "%B"/100) | dimensionless, 0–1 | |
| $\varphi_0$ | $\varphi$ at the start of the gradient (initial composition) | dimensionless | |
| $\varphi_f$ | $\varphi$ at the end of the gradient (final composition) | dimensionless | |
| $\Delta\varphi$ | $\varphi_f - \varphi_0$, gradient range | dimensionless | 0.05–1.0 |
| $\varphi_e$ | composition the band experiences **at the moment it elutes** | dimensionless | |
| $k$ | retention factor, $(t_R - t_0)/t_0$ | dimensionless | |
| $k_w$ | $k$ extrapolated to pure water ($\varphi = 0$) | dimensionless | a **fitting parameter, not a physical constant** — see §1.2 |
| $k_0$ | $k$ at the initial gradient composition $\varphi_0$; also written $k_i$, $k'_0$ | dimensionless | the parameter the two-run fit actually determines well. **Not** the $k_0$ of Guillarme et al. (2022) or den Uijl et al. (2021a, 2021b), which is this document's $k_w$ — §0 |
| $k_e$ | $k$ at the instant the band leaves the column; also $k_f$, $k^*$-adjacent | dimensionless | $\approx 1/b_e$ for well-retained solutes |
| $S$ | solvent-strength parameter, base-10 convention | dimensionless | ~1.7–6.3 for small molecules (§1.2); much larger for proteins |
| $S_e$ | solvent-strength parameter, natural-log convention | dimensionless | $=2.303\,S$ |
| $b$ | gradient steepness, base-10 | dimensionless | |
| $b_e$ | gradient steepness, natural-log | dimensionless | ~0.2–1 in typical practice |
| $t_0$ | column dead time, $V_m/F$ | min | |
| $V_m$ | column dead (void) volume | mL | |
| $F$ | flow rate | mL/min | |
| $t_D$ | instrument dwell (gradient delay) time, $V_D/F$ | min | 0.05–3 min; **must be measured per instrument** |
| $V_D$ | dwell (gradient delay) volume | mL | |
| $t_{\text{init}}$ | programmed initial isocratic hold at $\varphi_0$ | min | 0 if none |
| $\tau$ | $t_D + t_{\text{init}}$, total pre-gradient isocratic period | min | convenience symbol used throughout |
| $t_G$ | gradient time (duration of the linear ramp) | min | |
| $\beta$ | ratio of the two scouting gradient times, $t_{G,2}/t_{G,1}$ | dimensionless | **use 3** (§7) |
| $t_R$ | measured/predicted retention time | min | |
| $t'_R$ | $t_R - t_0 - \tau$, "gradient-corrected" retention time | min | |
| $B$ | gradient slope $\mathrm{d}\varphi/\mathrm{d}t = \Delta\varphi/t_G$ | min⁻¹ | |
| $N$ | column plate count (isocratic, at the elution composition) | dimensionless | |
| $G$ | band-compression factor | dimensionless | 0.7–1.0; ≤10% width effect in normal practice |
| $p$ | argument of $G$ | dimensionless | |
| $\sigma_t$ | peak standard deviation in time units | min | |
| $W$ | baseline peak width $=4\sigma_t$ | min | |
| $W_{1/2}$ | peak width at half height $=2.355\,\sigma_t$ | min | |
| $R_s$ | resolution of an adjacent pair | dimensionless | |

### 1.1 The LSS model

The linear-solvent-strength (LSS) model of reversed-phase retention:

$$\log_{10} k = \log_{10} k_w - S\varphi \qquad\Longleftrightarrow\qquad \ln k = \ln k_w - S_e\varphi$$

Source: stated as Eq. 1 of Guillarme, Bouvarel, Rouvière & Heinisch, *J. Sep. Sci.*
**45** (2022) 3276–3285 ([open access](https://doi.org/10.1002/jssc.202200161)) as
$\log k = \log k_0 - S\times C$; stated as Eq. 1 of Beyaz, Fan, Carr & Schellinger,
*J. Chromatogr. A* **1371** (2014) 90–105 ([PMC4388777](https://pmc.ncbi.nlm.nih.gov/articles/PMC4388777/))
as $\ln k' = \ln k'_w - S\phi$; stated as Eq. 6 of den Uijl, Schoenmakers, Pirok &
van Bommel, *J. Sep. Sci.* **44** (2021) 88–114 ([PMC7821232](https://pmc.ncbi.nlm.nih.gov/articles/PMC7821232/))
as $\ln k = \ln k_0 - S_{\text{LSS}}\varphi$. Originates with Snyder, Dolan & Gant,
*J. Chromatogr. A* **165** (1979) 3–30.

**Practical reparameterisation.** The engine should carry $(\ln k_0, S_e)$, *not*
$(\ln k_w, S_e)$, as the per-peak state, where

$$\ln k_0 = \ln k_w - S_e\varphi_0$$

Reason: $k_0$ is anchored inside the measured range; $k_w$ is an extrapolation to
$\varphi=0$ and is strongly correlated with $S$, so its fitted uncertainty is large
and misleading. Poole & Atapattu, *J. Chromatogr. A* **1675** (2022) 463153
([PubMed 35609444](https://pubmed.ncbi.nlm.nih.gov/35609444/)) state it bluntly:
*"Log k_w cannot be recommended as a descriptor of solute properties since it has
no clear connection to a real distribution system."* Expose $k_w$ in the UI if you
like, but fit in $k_0$.

### 1.2 Typical ranges of $S$ and $k_w$

- Poole & Atapattu (2022, above) determined $S$ across 17 methanol columns, 15
  acetonitrile columns, 7 acetone, 6 THF, 4 2-propanol, and report per-solvent
  averages (base-10 convention): **methanol 3.12 ± 0.12, acetonitrile 2.78 ± 0.18,
  acetone 2.71 ± 0.11, tetrahydrofuran 2.95 ± 0.24**, with experimentally
  determined values spanning **1.69 to 6.33**. They also find $S$ is column
  dependent, so it is "limited as a general solvent property".
- Snyder's rule of thumb for small molecules is $S \approx 0.25\,M^{0.5}$ ($M$ =
  molecular weight), giving $S\approx3.5$ at $M=200$ and $S\approx5.6$ at $M=500$ —
  consistent with Poole's range. **Attribution unverified** (see §10).
- Large biomolecules have much larger $S$ ("on-off" retention). Guillarme et al.
  (2022) build their whole method on this: the large-$k_0$ approximation of §3.2 is
  reliable for proteins and marginal for small molecules.
- A sane prior for a small-molecule simulator: $S_e \in [4, 15]$ (i.e. $S\in[1.7,6.5]$),
  $\ln k_0 > 0$. Reject fits outside a generous version of this and warn.

### 1.3 Gradient steepness $b$

$$b = \frac{t_0\,\Delta\varphi\,S}{t_G} = \frac{V_m\,\Delta\varphi\,S}{t_G\,F}
\qquad\Longleftrightarrow\qquad
b_e = \frac{t_0\,\Delta\varphi\,S_e}{t_G} = \frac{V_m\,\Delta\varphi\,S_e}{t_G\,F}$$

Source: Beyaz et al. (2014) Eq. 3, $b \equiv S\Delta\phi V_m / (F t_G)$ — exactly the
$V_m\Delta\Phi S/(t_G F)$ form named in the ticket. Same quantity as Wang, Stoll,
Schellinger & Carr, *Anal. Chem.* **78** (2006) 3406–3416
([PMC2638764](https://pmc.ncbi.nlm.nih.gov/articles/PMC2638764/)) Eq. 14,
$b = S(\varphi_{\text{final}}-\varphi_{\text{initial}})V_m/(F\,t_G)$; and Wilson,
Groskreutz & Weber, *Anal. Chem.* **88** (2016) 5112–5121
([PMC4940048](https://pmc.ncbi.nlm.nih.gov/articles/PMC4940048/)) Eq. 10,
$b = S\Delta\phi t_0/t_g$.

Guillarme et al. (2022) factor it as $b = S\cdot s^*$ (Eq. 5) with a
*solute-independent* normalised gradient slope

$$s^* = \frac{t_0\,\Delta C}{t_g} \qquad \text{(Eq. 6)}$$

This factoring is worth keeping in the code: $s^*$ is a property of the **run**,
$S$ is a property of the **peak**, and $b = S s^*$ couples them. It makes the
two-run fit fall out cleanly (§3.2).

$b$ is dimensionless. $b_e \approx 0.2$–$1$ covers most practical gradients;
$b_e \ll 1$ is a shallow gradient (isocratic-like, wide peaks, high selectivity),
$b_e \gg 1$ is a steep gradient (narrow peaks, compressed selectivity).

---

## 2. Gradient retention under LSS

### 2.1 The fundamental (general) equation

Before the LSS closed form, the general equation — because the engine will want it
for holds, multi-segment gradients, and post-gradient elution:

$$\frac{1}{B}\int_{\varphi_0}^{\varphi_0 + B\,(t_R - t_0 - \tau)} \frac{\mathrm{d}\varphi}{k(\varphi)} \;=\; t_0 - \frac{\tau}{k_0}$$

Source: den Uijl et al. (2021) Eqs. 3–4, which give this as the general form whose
solution "requires numerical integration of the retention model $k(\varphi)$".
Equivalently, in the time domain (the form to implement):

$$\int_0^{\,t_R - t_0} \frac{\mathrm{d}t}{t_0\,k\big(\varphi_{\text{in}}(t)\big)} \;=\; 1$$

where $\varphi_{\text{in}}(t)$ is the composition arriving at the **column inlet** at
time $t$ (i.e. the programmed profile delayed by $t_D$). The integrand is the
fractional column migration rate. This form is model-agnostic: swap in a quadratic
or Neue–Kuss $k(\varphi)$ and it still holds.

**Validity caveat (important).** Both forms above use the $k \gg 1$ approximation —
$1/(1+k)$ replaced by $1/k$, with the transit term $t_0$ added back explicitly as
the $-t_0$ in the integration limit. They also assume the band experiences the inlet
composition, i.e. that the gradient front sweeps past the band quickly. Both
approximations degrade for weakly retained solutes, which is precisely the
early-eluter edge case of §4.

### 2.2 The LSS closed form

Solving §2.1 with $k(\varphi) = k_0\exp(-S_e(\varphi-\varphi_0))$ and a linear ramp:

$$\boxed{\;t_R \;=\; \tau \;+\; t_0 \;+\; \frac{t_0}{b_e}\,\ln\!\Big[\,b_e\Big(k_0 - \frac{\tau}{t_0}\Big) + 1\,\Big]\;}$$

base-10 equivalent:

$$t_R \;=\; \tau + t_0 + \frac{t_0}{b}\,\log_{10}\!\Big[\,2.303\,b\Big(k_0 - \frac{\tau}{t_0}\Big) + 1\,\Big]$$

Sources — two independent statements, in the two different conventions, that agree:

- Beyaz et al. (2014) Eq. 2 (natural-log): $t_R = t_0 + t_D + \frac{t_0}{b}\ln\!\big(b(k'_0 - \frac{t_D}{t_0}) + 1\big)$, which they attribute to *"Schoenmakers and coworkers"*.
- Guillarme et al. (2022) Eq. 15 (base-10): $t_r = \frac{t_0}{b}\log\!\big[2.303\,k_i\,b\,(1 - \frac{t_D}{t_0 k_i}) + 1\big] + t_0 + t_D$. Note $2.303\,k_i b(1 - \tfrac{t_D}{t_0 k_i}) = 2.303\,b(k_i - \tfrac{t_D}{t_0})$, so the two are the same equation.

Both sources write $t_D$ where I write $\tau$. Generalising $t_D \to \tau = t_D + t_{\text{init}}$
to absorb a programmed initial hold is **[derived]** — it follows immediately from
§2.1, where the whole pre-gradient period is spent at constant $\varphi_0$ and enters
only through $\tau/k_0$. Set $t_{\text{init}}=0$ to recover the published form.

**Verification of the derivation** (worth reproducing in a unit test). Migration
fraction at time $t$, from §2.1:

$$x(t) = \frac{\tau}{t_0 k_0} + \frac{1}{t_0 k_0}\int_0^{\,t-\tau}\!\! e^{\,b_e s/t_0}\,\mathrm{d}s
 = \frac{\tau}{t_0 k_0} + \frac{e^{\,b_e (t-\tau)/t_0}-1}{k_0\,b_e}$$

Setting $x(t_R - t_0) = 1$ and solving gives exactly the boxed equation. This is the
identity the implementation should be tested against.

### 2.3 Three identities that fall out (and make good assertions)

**Retention factor at elution.**

$$k_e = \frac{k_0}{b_e\big(k_0 - \tau/t_0\big) + 1}
\qquad\text{so}\qquad
t_R = \tau + t_0 + \frac{t_0}{b_e}\ln\!\frac{k_0}{k_e}$$

Source: Wang et al. (2006) Eq. 16, $k'_f = k'_0 \big/ \{b[k'_0 - (t_D/t_0)] + 1\}$;
and Guillarme et al. (2022) Eq. 4 in the no-dwell limit, $k_e = 1/(2.3b + 1/k_i)$
(base-10), i.e. $k_e = 1/(b_e + 1/k_0)$. For a well-retained solute
$k_e \to 1/b_e$ — the gradient "chooses" the elution retention factor almost
independently of the solute. This is the theoretical basis for the $k^*$ concept.

**Elution composition.**

$$\varphi_e = \varphi_0 + \frac{\Delta\varphi}{t_G}\,\big(t_R - t_0 - \tau\big)
\qquad\text{and}\qquad
\varphi_e = \frac{1}{S}\log_{10}\!\frac{k_0'}{k_e}\Big|_{\text{referenced to }\varphi=0}$$

Source: Guillarme et al. (2022) Eq. 14 (first form, computed from a *measured* $t_R$)
and Eq. 3 (second form). The first form is the workhorse of the two-run fit (§3.2):
it converts a measured retention time into a composition with **no model parameters
at all** — only run geometry.

**Consistency check the engine should assert:** the two $\varphi_e$ expressions must
agree to floating-point tolerance for any $(k_0, S_e)$ and any run. I verified this
algebraically; it is a direct consequence of $t_R = \tau + t_0 + (t_0/b_e)\ln(k_0/k_e)$.

**Dwell / hold sensitivity** [derived]. Added 2026-09-03 under #54, from research
#52 §2.1.
Differentiating the boxed form of §2.2 with respect to $\tau$:

$$1 - \frac{\partial t_R}{\partial \tau} \;=\; \frac{1}{b_e\,(k_0 - \tau/t_0) + 1} \;=\; \frac{k_e}{k_0}$$

A dwell or hold error $\delta\tau$ therefore moves $t_R$ by $\delta\tau\,(1 - k_e/k_0)$
— nearly the whole $\delta\tau$ for a well-retained solute, and by the *same* amount
for every peak and every gradient that share $\tau$. The same ratio sizes the entire
pre-gradient migration correction: the $-\tau/t_0$ inside the logarithm contributes
$\approx \tau\,k_e/k_0$ to $t_R$ to first order (exactly
$(t_0/b_e)\ln\{[b_e k_0 + 1]/[b_e(k_0 - \tau/t_0) + 1]\}$; the isocratic-hold term
whose boundary is §4.1). One number
bounds two error sources at once. Two consequences: (i) a dwell error is common-mode
across runs whose $k_e/k_0$ are all small, so it can only be exposed by a *difference*
in $k_e/k_0$ between runs — which is why the argument must be run across datasets
(on this project's data $k_e/k_0$ is 6e-4 to 2e-3 on the four-peak sample but 8.8e-2
on the three-peak sample's run 7, and the $\delta\tau \approx 2$ min that closes the
one needs $\approx 10$ min for the other; research #52 §2.2); (ii) for a peak whose
$k_e/k_0$ is not small, the hold term is not negligible and the §4.1 boundary is close.

### 2.4 Validity limits of §2.2

The closed form is valid only while **all** of these hold:

1. $k_0 > \tau/t_0$ — the solute must still be on-column when the gradient reaches it.
   Otherwise the log argument goes ≤ 0. See §4.1.
2. $t_R \le \tau + t_G + t_0$, equivalently $\varphi_e \le \varphi_f$ — the gradient
   must still be running when the band exits. See §4.2.
3. $\log k$ is linear in $\varphi$ over $[\varphi_0, \varphi_e]$. See §7.5.
4. $k \gg 1$ over most of the migration (§2.1 caveat). Degrades for early eluters.
5. Flow rate, temperature and the gradient profile are what the method says they
   are. Beyaz et al. (2014) is an entire paper on how instrument imperfection
   breaks this; Boswell et al. (2011) back-calculate the *actual* profile rather
   than trusting the programmed one.

### 2.5 Piecewise programmes: the walker (v0.2, #70)

Added 2026-09-04 under build ticket #70, for SPEC §3's *gradient programme* — φ₀, an
initial hold $t_{\text{init}}$, and an ordered list of segments, each a duration $D_i$
and an end composition $\varphi_i$ (a repeated composition is a hold, a lower one a
descending segment). Everything here is **[derived]** from §2.1; the two published
statements it is checked against are named at the end. AutoLC-BO's implementation of
the same idea was read and not ported (CC BY-NC-SA; `github-hplc-simulators.md` §5.3,
§6.2).

**The inlet profile.** The composition arriving at the column inlet is the pump
programme delayed by the dwell: $\varphi_{\text{in}}(t) = \varphi_0$ for
$t < \tau = t_D + t_{\text{init}}$, then leg $i$ runs from
$T_i = \tau + \sum_{j<i} D_j$ to $T_i + D_i$, linear from its entry composition
$\varphi_{i-1}$ (with $\varphi_{-1} \equiv \varphi_0$) to $\varphi_i$, and after the
last leg $\varphi_{\text{in}} = \varphi_f$ for ever. That is the only place the
programme enters §2.1's time-domain form,
$\int_0^{t_R - t_0} \mathrm{d}t \,/\, (t_0\,k(\varphi_{\text{in}}(t))) = 1$.

**The walk.** Write $x(t)$ for the migration fraction (the integral so far). Because
the integrand depends on $t$ only through $\varphi_{\text{in}}$, and
$\varphi_{\text{in}}$ is linear on each leg, $x$ advances by a closed form on every leg
and the band's exit is found in the first leg where $x$ reaches 1:

1. *Dwell and initial hold* (§4.1): $x(\tau) = \tau / (t_0 k_0)$. If this is $\ge 1$ the
   band left isocratically, $t_R = t_0(1 + k_0)$, regime **isocratic hold** (`isocratic_hold`).
2. *A ramp* with entry retention $k_{\text{entry}} = k(\varphi_{i-1})$ and **signed**
   steepness $b_i = t_0\,\Delta\varphi_i\,S_e / D_i$ (the §1.3 expression with the
   leg's own $\Delta\varphi_i$ and $D_i$; negative for a descending leg). Within the
   leg, with $s$ the time since its start,

   $$x(T_i + s) = x(T_i) + \frac{e^{\,b_i s / t_0} - 1}{k_{\text{entry}}\, b_i},
   \qquad
   x(T_i + D_i) = x(T_i) + \frac{k_{\text{entry}}/k_{\text{end}} - 1}{k_{\text{entry}}\, b_i}$$

   using $e^{\,b_i D_i / t_0} = e^{\,S_e \Delta\varphi_i} = k_{\text{entry}} / k_{\text{end}}$,
   exactly §4.2's $x_G$ with the leg's quantities in place of the run's. If the end
   value is $\ge 1$, solve $x(T_i + s) = 1$:

   $$t_R = T_i + t_0 + \frac{t_0}{b_i}\,\ln\!\Big[\,1 + b_i\,k_{\text{entry}}\,\big(1 - x(T_i)\big)\Big],
   \qquad
   k_e = \frac{k_{\text{entry}}}{1 + b_i\,k_{\text{entry}}\,(1 - x(T_i))}$$

   regime **gradient** (`gradient`, ascending or descending). For a descending leg both the
   numerator and the denominator of the end-value fraction change sign, and the log
   argument is bounded below by $k_{\text{entry}}/k_{\text{end}} > 0$ whenever the band
   leaves on the leg, so the branch needs no special case.
3. *A hold* at $k_{\text{entry}}$: $x$ grows at $1 / (t_0 k_{\text{entry}})$, so
   $x(T_i + D_i) = x(T_i) + D_i / (t_0 k_{\text{entry}})$; if that is $\ge 1$,
   $t_R = T_i + t_0 + (1 - x(T_i))\, t_0\, k_{\text{entry}}$ and $k_e = k_{\text{entry}}$.
   Regime **isocratic hold** if no ramp has yet been traversed (a flat first segment at
   $\varphi_0$ is the same physics as $t_{\text{init}}$), otherwise **post-gradient**
   (`post_gradient`) — the flag SPEC §6 diagnostic 9 reads.
4. *After the last leg* (§4.2 generalised): still on-column at
   $T_{\text{end}} = \tau + \sum_i D_i$, the band finishes isocratically at
   $k_f = k(\varphi_f)$: $t_R = T_{\text{end}} + t_0 + (1 - x(T_{\text{end}}))\,t_0\,k_f$,
   regime **post-gradient**. $T_{\text{end}} + t_0$ is the programme's
   `gradient_end_time`.

**Reduction to §2.2.** With one leg, step 2 gives
$t_R = \tau + t_0 + (t_0/b_e)\ln[1 + b_e k_0 (1 - \tau/(t_0 k_0))]$, and
$b_e k_0 (1 - \tau/(t_0 k_0)) = b_e (k_0 - \tau/t_0)$: the boxed equation of §2.2,
arranged differently. The two agree to 1e-12 min on every fixture run of both bench
samples (the last bits differ because the products are formed in a different order),
which is why the engine keeps v0.1's closed form as the one-segment path — bitwise
identical to v0.1 by construction — and enters the walk only for two or more segments
(SPEC §3, §10 item 4a).

**Inertness.** The walk returns from the leg in which $x$ reaches 1 and never reads a
later one, so a segment that starts after the band has left changes its prediction by
exactly zero — a property of the algorithm, not a tolerance (SPEC §10 item 4c).

**Band compression.** $G$ is taken from the eluting leg: $p = b_i k_{\text{entry}} / (1 +
k_{\text{entry}})$ with that leg's $b_i$ and its entry $k_{\text{entry}}$, and $G = 1$ for a
band leaving in a hold or after the end (§5.3's posture). On one leg that is §5.2
unchanged. A band leaving on a *descending* leg also gets $G = 1$: Poppe's $G$ (§5.2)
is derived for a composition rising across the band and neither source here extends it
to a falling one, so nothing is claimed. This per-leg rule is SPEC §3's shipped
approximation; Hao et al. Eq. 10's cumulative integral remains deferred, and no
multi-segment width has been measured (SPEC §10 makes no $R_s$ claim for programmes).

**Validity.** Everything §2.4 says still applies leg by leg, and one caveat sharpens:
§2.1's $k \gg 1$ approximation is weakest exactly where a wash step brings a band off.
On the three-peak sample's run 6 (15 → 55 %B over 25 min, a 19.5 min hold, then a step
to 95 %B) Unknown-3 leaves the column at $k_e \approx 1.6$ in the 95 %B hold — the
walker puts it at **47.12 min against a measured 46.8** (+0.32 min, +0.69 %; the
hand-walked pre-registration was 47.0). Inside the coarse bar, and the whole of the
multi-segment evidence on file: one peak, one sample, one programme (SPEC §10 item 4d).

**Sources.** The per-segment ramp form and the post-programme isocratic tail are the
same two statements `github-hplc-simulators.md` §5.3 records as verified: den Uijl et
al. (2021, ref. 4) Eq. 7 for the pre-gradient migration $\tau / (t_0 k_0)$ and Eq. 8 for
the residual fraction after the gradient eluting isocratically at the final $k$; the
per-segment log form is what AutoLC-BO's `retention_model.py` implements for segment
$n$ and is re-derived above from §2.1 alone. Checked in `tests/test_walker.py` against
the independent quadrature oracle of `tests/numerics.py` (§11's check 1, extended to
programmes): a descending leg, a mid-programme hold, two ascending ramps, a band still
on-column after the end and one leaving in the initial hold, all to 1e-10 min.

---

## 3. The two-run fit

**Setup.** Two linear gradient runs, identical in everything (column, $F$,
$\varphi_0$, $\varphi_f$, $T$, instrument) except gradient time: $t_{G,1}$ and
$t_{G,2} = \beta\,t_{G,1}$, with $\beta = 3$ recommended (§7.1). For each tracked
peak we have $t_{R,1}$ and $t_{R,2}$; we want $(k_0, S_e)$ — two data, two unknowns.

Throughout, write $t'_{R,i} = t_{R,i} - t_0 - \tau$ and $b_{e,i} = S_e\Delta\varphi t_0/t_{G,i}$,
so that $b_{e,2} = b_{e,1}/\beta$.

### 3.1 Is there a closed form? Yes, but only approximately

The exact system is **not** closed-form solvable. From §2.2, each run gives

$$e^{\,b_{e,i} t'_{R,i}/t_0} - 1 \;=\; b_{e,i}\,A, \qquad A \equiv k_0 - \frac{\tau}{t_0}$$

Eliminating $A$ leaves one scalar equation in $b_{e,1}$ that mixes two exponentials
with incommensurate rates — transcendental, no elementary solution. So: **closed
form for the initial guess, one-dimensional root-find for the answer.**

### 3.2 Closed form (large-$k_0$ approximation) — use as the initial guess

If $b_e A \gg 1$ (well-retained solute), $e^{b_e t'_R/t_0} \gg 1$ and the "+1" drops:

$$t'_{R,i} \approx \frac{t_0}{b_{e,i}}\ln\!\big(b_{e,i}A\big)$$

Substituting $b_{e,2}=b_{e,1}/\beta$ and subtracting kills $\ln A$ entirely:

$$\boxed{\;b_{e,1} \;\approx\; \frac{t_0\,\ln\beta}{\,t'_{R,1} - t'_{R,2}/\beta\,}
\;=\; \frac{\beta\,t_0\,\ln\beta}{\,\beta\,t'_{R,1} - t'_{R,2}\,}\;}$$

and equivalently, in the composition domain,

$$\boxed{\;S_e \;\approx\; \frac{\ln\beta}{\varphi_{e,1}-\varphi_{e,2}}\;}
\qquad \varphi_{e,i} = \varphi_0 + \frac{\Delta\varphi}{t_{G,i}}\big(t_{R,i}-t_0-\tau\big)$$

Source: the composition-domain form is Guillarme et al. (2022) Eq. 16,
$\Delta C_e = \frac{1}{S}\log(s_2^*/s_1^*)$ — the two-point case of their Eqs. 8–10
regression ($C_e$ vs. $\log s^*$, slope $1/S$). Since $s_2^*/s_1^* = t_{G,1}/t_{G,2} = 1/\beta$,
this is $S = \log\beta/(\varphi_{e,1}-\varphi_{e,2})$ in base-10, i.e. the boxed
natural-log form. **The $b_{e,1}$ form is [derived]** — algebraically identical, shown
above, stated in time rather than composition because that is what the code has.

Guillarme et al. state the constraints for this approximation to hold: *"the
retention factor at the initial composition of the preliminary gradient series must
be large enough (log $k_i$ above 2.1)"* and *"the retention models must be
sufficiently linear"*; they note it is *"particularly well suited for proteins"*
and more restrictive for small molecules and peptides. **For a small-molecule
simulator, treat this as a seed, not an answer.**

How bad is it? Measured against the exact solve on synthetic data (§11), the error
in $S$ from the closed form alone:

| true $k_0$ | 8 | 20 | 50 | 500 | 5 000 | 10 000 |
|---|---|---|---|---|---|---|
| $\log_{10}k_0$ | 0.9 | 1.3 | 1.7 | 2.7 | 3.7 | 4.0 |
| error in $S$ | **138%** | **37%** | 9.6% | 0.7% | 0.1% | 0.03% |

The $\log k_i > 2.1$ threshold ($k_0 \approx 126$) is exactly where this becomes
tolerable — Guillarme et al.'s constraint is well calibrated. For small molecules
starting at low $\varphi_0$, $k_0$ in the tens is common, so **the closed form alone
is not acceptable for v0.1**; it is only a starting bracket for §3.3.

Given $b_{e,1}$, recover the other parameter **exactly** (no approximation):

$$A = \frac{e^{\,b_{e,1}t'_{R,1}/t_0}-1}{b_{e,1}},\qquad
k_0 = A + \frac{\tau}{t_0},\qquad
S_e = \frac{b_{e,1}\,t_{G,1}}{t_0\,\Delta\varphi}$$

### 3.3 Exact fit — one-dimensional root find

Define, for $b > 0$:

$$g(b) \;=\; e^{\,b\,t'_{R,1}/t_0} \;-\; 1 \;-\; \beta\Big(e^{\,b\,t'_{R,2}/(\beta t_0)} - 1\Big)$$

$g(b)=0$ is the exact two-run condition (it is $b_{e,1}A - b_{e,1}A = 0$ written
out). Solve for the positive root, then recover $A$, $k_0$, $S_e$ as in §3.2.
**[derived]** — the elimination is mine; both parent equations are sourced (§2.2).

Root-structure facts, all derivable and worth encoding as guards:

- $g(0)=0$ always. **The trivial root must be excluded**; bracket strictly above 0.
- $g'(0) = (t'_{R,1}-t'_{R,2})/t_0 < 0$, since the shallower gradient always elutes
  the peak later. So $g$ dips negative near the origin.
- $g(b)\to+\infty$ as $b\to\infty$ **iff** $t'_{R,1}/t_{G,1} > t'_{R,2}/t_{G,2}$,
  i.e. **iff** $\varphi_{e,1} > \varphi_{e,2}$: the steeper gradient must elute the
  peak at the *higher* %B.
- Under that condition the positive root is unique. If the condition fails, **the
  data admit no LSS solution** — see §7.2.

Use Brent on a bracket $[\varepsilon, b_{\max}]$ (expand $b_{\max}$ geometrically
until $g>0$), or Newton seeded from §3.2. Brent is preferable: it cannot run away,
and the function is cheap. Guard against overflow in $e^{b t'/t_0}$ by working with
$\log$-domain arithmetic or capping $b_{\max}$ at, say, $S_e = 200$ equivalent.

### 3.4 The standard algorithm order (DryLab-class)

Molnár's account of DryLab's development (*J. Chromatogr. A* **965** (2002) 175–194,
[publisher PDF](https://molnar-institute.com/fileadmin/user_upload/Literature/_2002_Molnar_Compu.pdf))
gives the workflow. Its Table 1, step 1 is explicit about the experimental design:

> *"Carry out two gradients 0→100%B (acetonitrile) with eluent A: 0.05 M phosphate,
> (or other volatile buffer for LC–MS) pH 2.1 at 40 °C in 40 and 120 min"*

— i.e. $\beta = 3$. The order the software works in:

1. **Measure the instrument, not just the sample.** $t_0$ (from $V_m$, or an
   unretained marker) and $t_D$ (dwell). Molnár §10 is emphatic that dwell volume
   must be characterised or method transfer fails: *"Method transfer can only be
   carried out correctly if the dwell volume has been measured carefully and is
   indicated in the method description of the validated gradient method."*
2. **Run the two scouting gradients** ($t_G$, $3t_G$), everything else fixed.
3. **Peak tracking** — match peak identity across the two runs *before* fitting.
   Molnár §8: *"peak tracking using peak areas turned out to be a rather simple and
   reliable technique, as long as injection volume of the sample was kept constant
   between the basic runs"*; DryLab automates this *"provided the mixture is clean
   and does not contain too many components"*. **This step is the practical
   bottleneck and the main source of wrong answers, not the arithmetic.**
4. **Per-peak fit** of $(k_0, S_e)$ — §3.2 seed, §3.3 solve. Independently per peak.
5. **Forward-predict** over a grid of candidate conditions (§5) and build the
   resolution map: $R_s$ of the *critical* (worst) pair as a function of the
   optimisation variable. Molnár Fig. 1 defines the resolution map exactly this way,
   with the critical resolution as *"the lowest of the three peaks, shown as a bold line"*.
6. **Choose the maximum of the minimum** $R_s$, preferring a broad plateau (robustness)
   over a sharp peak.

Whether DryLab internally uses the closed form or an iterative solve is proprietary
and I could not verify it (§10).

---

## 4. Edge cases

These are where naive implementations produce NaNs or silently wrong numbers.
Handle each explicitly; the general equation of §2.1 handles all of them uniformly
if you integrate numerically, but the closed form needs branching.

### 4.1 Peak elutes during the dwell / initial isocratic hold

The band spends the first $\tau = t_D + t_{\text{init}}$ minutes at constant $\varphi_0$,
so it migrates isocratically. If it reaches the outlet before the gradient arrives,
the run is isocratic *for that peak*:

$$\text{if } k_0 \le \frac{\tau}{t_0}: \qquad t_R = t_0\,(1+k_0)$$

**[derived]**, but note this is exactly the boundary at which the sourced closed form
(§2.2) breaks: its log argument $b_e(k_0-\tau/t_0)+1$ falls to 1 and then below as
$k_0 \to \tau/t_0$. The $(k_0 - \tau/t_0)$ term in Beyaz Eq. 2 exists precisely to
account for pre-gradient migration; it is the engine's job to notice when that term
goes non-positive rather than to take the log of it.

Implementation: test $k_0 \le \tau/t_0$ **first**, before evaluating anything else.

Fitting consequence: such a peak carries **no gradient information** — $t_{R,1} = t_{R,2}$
and the fit is undetermined. Detect and report "elutes in the hold; not fittable
from these runs; shorten the hold, reduce $\varphi_0$, or reduce dwell".

### 4.2 Peak elutes after the gradient ends

If the closed form returns $t_R > \tau + t_G + t_0$ (equivalently $\varphi_e > \varphi_f$),
the band was still on-column when the ramp finished, and completes its journey
isocratically at $\varphi_f$. **[derived]** from §2.1 on the identical footing as §2.2:

$$k_f = k_0\,e^{-S_e\Delta\varphi}, \qquad
x_G = \frac{\tau}{t_0 k_0} + \frac{k_0/k_f - 1}{k_0\,b_e}$$

$x_G$ is the fraction of the column traversed when the gradient ends (using
$e^{b_e t_G/t_0} = e^{S_e\Delta\varphi} = k_0/k_f$). Then:

$$\text{if } x_G \ge 1: \text{ use §2.2} \qquad\qquad
\text{if } x_G < 1: \quad t_R = \tau + t_G + t_0 + (1-x_G)\,t_0\,k_f$$

At $x_G = 1$ exactly this gives $t_R = \tau + t_G + t_0$, matching §2.2 at its
boundary — the branches join continuously, which is the test to write.

Practical note: peaks in this regime are **wide** (they finish under isocratic
conditions with no compression) and their positions are hypersensitive to $S_e$,
so predictions here are the least trustworthy in the chromatogram. Flag them.

### 4.3 Very early eluters

Peaks with small $k_0$ violate the $k\gg1$ approximation behind §2.1–2.2. Symptoms:
predicted $t_R$ systematically early, and a fit that pushes $S_e$ to implausible
values. Mitigations, in order of preference:

- Report a low-confidence flag when $k_e$ at the fitted parameters is below ~1, or
  when $t'_R < t_0$.
- Numerically integrate the exact $1/(1+k)$ form rather than the $1/k$ form:
  $\int_0^{t_R}\mathrm{d}t\big/\big(t_0(1+k(t))\big) = 1$. This costs one quadrature
  and removes the approximation. Recommended for v0.1 if the budget allows.
- Molnár §16 records that DryLab practice constrains conditions so that
  $1 < k < 20$ for the first and last peak. A simulator can't enforce that, but it
  can warn when a prediction leaves that window.

### 4.4 Very late eluters

Two distinct problems: (a) they may fall into §4.2; (b) if they do not elute at all
in the shorter scouting run, there is no $t_{R,1}$ and no fit. Treat a missing peak
in one run as "not fittable", never as a censored value silently dropped.

### 4.5 Degenerate/near-degenerate input

$t_{R,1} = t_{R,2}$ (to within measurement precision) means either §4.1 or an
unretained peak. Either way: no fit. See §7.2.

---

## 5. Peak width in gradient elution

### 5.1 The width equation

$$\sigma_t = \frac{G\,t_0\,(1+k_e)}{\sqrt{N}}
\qquad
W_{1/2} = \frac{2.355\,G\,t_0\,(1+k_e)}{\sqrt{N}}
\qquad
W = \frac{4\,G\,t_0\,(1+k_e)}{\sqrt{N}}$$

Source: Wang et al. (2006) Eq. 15, given as $W_{1/2} = 2.35\,G\,t_0(1+k'_f)/\sqrt N$
and attributed to Snyder. Same structure in Wilson et al. (2016) Eq. 4 for
$\sigma_{t,\text{col}}$. Guillarme et al. (2022) Eq. 13 gives the no-compression
version, $w = \frac{4t_0}{\sqrt N}\cdot\frac{1+2.3b}{2.3b}$ — which is the same
equation with $G=1$ and $k_e = 1/(2.3b)$, since $1 + 1/(2.3b) = (1+2.3b)/(2.3b)$.
That agreement across three papers is the cross-check that the form is right.

**Rendering caveat:** the HTML-to-text extraction of Wang Eq. 15 and Wilson Eq. 4
dropped the radical over $N$ (and Wilson's squares). I reconstructed $\sqrt N$ from
dimensional consistency with the isocratic width $W = 4t_0(1+k)/\sqrt N$ and from
Guillarme Eq. 13, which rendered cleanly and unambiguously contains $\sqrt N$.

$N$ here is the **isocratic** plate count at the elution composition. Treating $N$
as one number per column/flow-rate was the v0.1 starting point; Molnár §9 notes
DryLab originally worked around $N$ varying across the chromatogram by using
different plate numbers in the front/middle/final third, and (his §16) later solved it
properly by taking **measured peak widths as input data**. Build ticket #23 took that
route: $N$ is fitted per peak from the scouting widths — the inverse of the equation
above, one $N$ per peak as the geometric mean of what each width implies — with the
sources, the estimator and the regime caveats in `plate-count-from-widths.md`.

### 5.2 Band compression factor $G$

$$G(p) = \frac{\sqrt{\,1 + p + p^2/3\,}}{1+p},
\qquad
p = \frac{b_e\,k_0}{1+k_0}$$

Sources — two independent statements that agree exactly:

- Wilson et al. (2016) Eqs. 8–9: $G(p) = [1+p+p^2/3]^{0.5}/(1+p)$ with
  $p = k_1 b/(1+k_1)$, $b = S\Delta\phi t_0/t_g$; attributed to Snyder & Dolan,
  *High-Performance Gradient Elution* (Wiley, 2007).
- Hao, Liu & Shen, *Se Pu (Chin. J. Chromatogr.)* **39** (2021) 10–14
  ([PMC9274839](https://pmc.ncbi.nlm.nih.gov/articles/PMC9274839/)) Eq. 3:
  $G = \sqrt{p^2/3 + p + 1}\,/\,(1+p)$ with $p = k_{\varphi_0}BSt_0/(1+k_{\varphi_0})$,
  attributed to **Poppe, Paanakker & Bronckhorst, *J. Chromatogr.* 204 (1981) 77**.
  Note $B S t_0 = (\Delta\varphi/t_G)S t_0 = b$, so the two $p$ definitions are identical.

Because neither source writes a 2.303, both are in the **natural-log convention**:
$p = b_e k_0/(1+k_0)$, so $p \to b_e$ for a well-retained solute. In Snyder's base-10
notation this reads $p = 2.303\,b\,k_0/(1+k_0)$. **Getting this factor wrong changes
$G$ by ~10–15% at typical steepness** — see §10 for what I could not verify here.

Behaviour: $G(0)=1$ (no gradient, no compression); $G$ decreases monotonically with
$p$. Computed values for large $k_0$ (so $p \to b_e$):

| $b_e$ | 0.1 | 0.2 | 0.46 | 1.0 | 3.0 |
|---|---|---|---|---|---|
| $G$ | 0.955 | 0.918 | 0.847 | 0.764 | 0.661 |
| width reduction | 4.5% | 8.2% | 15.3% | 23.6% | 33.9% |

Stoll's LCGC treatment states that *"under most practical conditions, the gradient
compression factor does not affect the peak width by more than approximately 10%"*.
That is consistent **only for the usual target regime** $k^*\approx5$, i.e.
$b_e\approx0.2$, where the table gives 8.2%. Steeper gradients break the rule of
thumb: at $b_e = 1$ compression is worth nearly a quarter of the peak width.
**Do not hard-code $G$ as a ~10% correction or drop it as negligible** — compute it.
(The LCGC page was not directly fetchable; §10.)

Hao et al. also give a more general $G$ (their Eq. 10) that integrates over the
actual composition history and handles dwell time properly. Out of scope for v0.1;
worth noting if peak widths ever become the deliverable rather than a garnish.

### 5.3 What v0.1 should actually do

Compute $k_e$ from §2.3 (which already includes the dwell correction), $p$ and $G$
from §5.2, and $W$ from §5.1 with a user-supplied or column-preset $N$. Expose $N$
as a knob. Do **not** silently apply $G$ to peaks in the post-gradient regime
(§4.2) — they are not compressed; use $G=1$ there.

### 5.4 Calibration of the $G$ convention against measured widths

Added during build ticket #17, which owns this calibration. §10 item 5 flagged the
log-base convention inside $p$ as *"the highest-risk number in this document"* and
named the cheap resolution: *"check a computed $G$ against a measured peak width once
real data exists."* Done, and **resolved in favour of the natural-log reading of
§5.2** — $p = b_e k_0/(1+k_0)$.

> **History.** A first pass used only the scouting pair (runs 1–2) and could *not*
> separate the natural-log convention from its mirror; it shipped the convention on
> §5.2's two primary sources alone. The measured widths for runs 3 and 4 arrived
> afterwards and settled it. The argument below is the one that stands.

**The statistic.** A measured $W_{1/2}$ cannot test $G$ on its own: the width model
carries an unknown $N$ per compound, and any single width can be matched by moving
$N$. But **$N$ is a property of the column, not of the run.** So under the correct
convention, the $N$ implied by each of a compound's measured widths must agree across
every gradient time:

$$N_{\text{implied}} = \left(\frac{\sqrt{8\ln 2}\;G\,t_0\,(1+k_e)}{W_{1/2}}\right)^{2}
\quad\text{must be constant over } t_G$$

The scatter of $N_{\text{implied}}$ within one compound is the discriminator. It is
free of $N$ by construction and uses all four runs rather than a single ratio.

**The data.** `validation/run1–4.csv`: three compounds at $t_G$ = 15, 25, 45, 60 min.
$(k_0, S_e)$ comes from fitting runs 1–2 only, so **runs 3 and 4 are held out** — this
is a prediction test. Run 4 is what settled the question: against run 1 it gives a
**fourfold** lever on $b_e$ where the scouting pair gave threefold.

Two data-quality facts govern how the runs are weighted, both independent of the
outcome:

- **Run 3's $W_{1/2}$ is recorded to two decimals** (0.05, 0.05, 0.04) — a ±10% band
  on a 0.05 min peak against ±1.5% for the three-decimal runs. It cannot resolve a ~5%
  effect and is used only as a robustness check.
- **Only Unknown-1's areas follow the expected trend.** Peak area grows slowly with
  run time — a longer gradient keeps the band in the flow cell longer — so growth
  itself is expected, and all three compounds show it mildly (1.08×, 1.01×, 1.14× end
  to end across a fourfold range of $t_G$). What separates them is the shape of the
  trend: Unknown-1 rises monotonically, while Unknown-2 and Unknown-3 both **spike by
  1.54–1.67× at $t_G$ = 45 specifically** and then fall back, which no run-time trend
  can produce. That localises the fault to one run's integration of those two peaks.
  SPEC §5 named them before any of this — *"the lab dataset's peaks 2–3 exceed it"*,
  of its ~30% area-share threshold. Where the integrator is not measuring the same
  thing, those compounds' widths in that run are not trustworthy either.

**Result** — $N$ implied by Unknown-1's width in each three-decimal run:

| convention for $p$ | $t_G$=15 | $t_G$=45 | $t_G$=60 | scatter (CV) | trend |
|---|---|---|---|---|---|
| $G=1$ (no compression) | 20866 | 17147 | 16548 | 12.86% | falls |
| $p = (b_e/\ln 10)\,k_0/(1+k_0)$ | 17810 | 16182 | 15836 | 6.35% | falls |
| **$p = b_e k_0/(1+k_0)$ — §5.2, shipped** | **15299** | **15126** | **15023** | **0.92%** | **flat** |
| $p = (\ln 10)\,b_e k_0/(1+k_0)$ | 12285 | 13304 | 13532 | 5.09% | rises |

The shipped convention holds one column's plate count constant to **0.92% across a
fourfold range of gradient steepness**. That is at the ±1.5% quantisation floor of
these widths — it cannot be beaten on this data, only matched. Every rival scatters by
5–13%, and the *sign of the trend* is the tell: too little compression makes $N$ fall
with $t_G$, too much makes it rise, and the correct factor removes the trend. The
shipped convention is bracketed by the two slips and lands flat between them.

**Robustness.** The verdict does not depend on either data-quality judgement above.
Averaged over all three compounds, with and without run 3, the shipped convention
still scatters $N$ least of the four candidates. Both variants are asserted.

**The one remaining caveat: extra-column dispersion.** The lab dataset carries no
measurement of it. A shared $\sigma_{ec}$ inflates narrow (steep-gradient) peaks
proportionally more, so it trades against $G$. Fitting one $\sigma_{ec}$ shared by the
two compounds and taking each convention's best achievable joint scatter:

| convention | best joint CV | at $\sigma_{ec}$ |
|---|---|---|
| **shipped** | **6.70%** | **0 µL** |
| $\times\ln 10$ mirror | 7.39% | 1.25 µL |
| $/\ln 10$ | 9.47% | 0 µL |
| $G = 1$ | 15.06% | 0 µL |

The shipped convention is the best explanation **with no nuisance parameter at all**,
and beats the mirror even after the mirror is given its best-fit $\sigma_{ec}$. The
mirror survives only by positing ~1.25 µL of extra-column $\sigma$ that nobody
measured, and is still worse. That is not a tie.

**Verdict.** $G=1$ and the base-10 steepness reading are excluded outright. The
natural-log convention of §5.2 is confirmed by measurement, on held-out data, and now
rests on the agreement of three independent things: two primary sources, the constancy
of a real column's plate count, and the vanishing of the steepness trend.

**Where this lives in the tests.** `tests/test_reality.py` pins the constancy result,
the scatter of all three rivals, the two robustness variants, the area-stability
grounds for resting on Unknown-1, and the quantisation floor the bar sits above.
§5.2's own computed table is pinned separately in `tests/test_width.py` as the numeric
statement of the convention. A ×2.303 slip in `band_compression_factor` now fails five
reality tests; before run 3 and 4's widths existed it failed none of them.

**Status of §10 item 5: resolved.**

---

## 6. Resolution

For an adjacent pair (peak 1 eluting first):

$$R_s = \frac{t_{R,2}-t_{R,1}}{2\,(\sigma_1+\sigma_2)}
= \frac{2\,(t_{R,2}-t_{R,1})}{W_1+W_2}
= 1.177\;\frac{t_{R,2}-t_{R,1}}{W_{1/2,1}+W_{1/2,2}}$$

Source: Molnár (2002) Fig. 1 gives the DryLab working form as
$R_s = \frac{t_2-t_1}{w_1+w_2}\times 1.178$ with half-height widths. The three
expressions above are algebraically identical, since $W = 4\sigma$ and
$W_{1/2} = \sqrt{8\ln 2}\,\sigma = 2.3548\,\sigma$, so the half-height coefficient is
$\sqrt{8\ln 2}/2 = 1.1774$. I verified the equivalence numerically (all three agree
to floating-point precision when the exact constant is used); the 1.177 vs. 1.178
spread in the literature is just rounding of $\sqrt{8\ln 2}$. **Use the exact
constant, not 1.178** — the rounded value costs ~0.04% on every $R_s$.

Use the **width-based definition**, not the $\frac{1}{4}(\alpha-1)\sqrt N \frac{k}{1+k}$
master form: the master form assumes equal widths and is an approximation, whereas
the engine already computes both widths exactly. (The gradient master-equation
variant with $k^*$ and $G$ is quoted in the literature but I could not verify its
exact form — §10.)

**Critical resolution** = $\min$ over adjacent pairs, after sorting peaks by
predicted $t_R$ at those conditions. Re-sort at every grid point: elution order
changes (§7.4).

**Note on validating $R_s$ (tickets #17 and #23).** SPEC §10 wanted an $R_s \pm 0.3$ bar once
§5.4's calibration landed. It is not met, and the reason is worth stating precisely
because it is *not* about $G$.

1. **With a defaulted $N$ the engine is 18–39% optimistic on $R_s$**, at both held-out
   conditions ($t_G$ = 25 and 60). $h = 2$ overstates the real efficiency of this
   column plus its extra-column volume, so predicted peaks are too narrow and every
   $R_s$ too good. Note this does not contradict §5.4: that section's statistic is
   deliberately $N$-free, and $R_s$ is not.
2. **Even a perfect width model would not exercise the bar here.** The sample's peaks
   sit at $R_s$ = 30–116, where ±0.3 is a 0.3–1% tolerance. An $R_s$ bar only bites
   near the critical region ($R_s \approx 1$–3), which this dataset never enters.

Obstacle 1 was closed by ticket #23, which makes $N$ a fitted quantity rather than a
geometry estimate (§5.1; `plate-count-from-widths.md`): with $N$ fitted per compound
from the scouting pair, held-out $R_s$ lands at 0.955 / 0.956× measured at $t_G$ = 25
and 0.935 / 0.900× at $t_G$ = 60 — 1.5–11.6 absolute $R_s$ units low, slightly
pessimistic where the default was 18–39% optimistic. At $t_G$ = 25 that residual is
inside the ±9–13% band run 3's two-decimal widths can resolve; at $t_G$ = 60 it is
real. Obstacle 2 stands and needs different data: a sample with a genuinely
difficult pair.

**What is asserted instead.** The absolute number is caveated, but the *ranking* is
not: under either $N$ the engine names the correct critical pair at both held-out
conditions. That — not the absolute $R_s$ — is what a chromatographer acts on, and it
is what `tests/test_reality.py` pins, alongside the fitted-$N$ bands, the defaulted-$N$
optimism band (kept for the width-less path; it tripped as designed when #23 landed)
and the unmet ±0.3 itself, pinned as a number.

---

## 7. Known pitfalls

### 7.1 Choice of $\beta$ — and why 3

Three sources converge on the same number:

- Molnár (2002) Table 1: two gradients *"in 40 and 120 min"* — $\beta = 3$.
- Molnár (2002) §8, reporting Snyder's work on how far conditions may be varied
  while still treating variables independently: *"This meant 15–20% change in %B,
  **a factor of three in gradient elution time**, 20–30 °C difference in temperature
  studies and 0.5–0.6 pH units of eluent A"*.
- Guillarme et al. (2022): *"usual ratio recommended for accurate retention
  modeling is 3 only"*.

But den Uijl et al. (2021) qualify it usefully: the gradient slope factor *"is often
assumed to be at least three"* yet proves *"less important than the proximity of the
slope of the predicted gradient to that of the scanning gradients"*. **Read: pick
the two scouting gradients to bracket the gradients you intend to predict, and $\beta=3$
is a good default, not a law.**

**The same Molnár sentence carries a composition number — read it for what it is.**
Its *"15–20% change in %B"* clause is the $\varphi$ half of the $\beta = 3$ recommendation,
and it is tempting to read it as a licence: "an LSS fit is good for 15–20 %B either
side of what it was fitted on". It is not. The claim is about *experimental design*
— how far two variables may be varied while still being treated as independent in
a factorial model, the $\varphi$ analogue of "how far apart to put the two runs" — not
about how far a fitted line may be extrapolated past its calibration. What a
$\beta = 3$ pair actually calibrates is the elution-composition window
$\Delta\varphi_e = \ln\beta / S_e$ (Guillarme et al. 2022 Eq. 16;
`composition-extrapolation.md` §1–2): 7.5–28 %B over §1.2's small-molecule $S$
range of 1.7–6.3, and ~9.4 %B on this project's own data ($S \approx 5$). Snyder's
span is therefore the same order as the calibrated window — roughly twice it for
this sample — a design width, not a margin beyond it. Molnár cites Dolan, Lommen &
Snyder (ref. 17) for the numbers; neither this document nor #43 has read them.

### 7.2 Fit degeneracy when the runs are too similar

As $\beta \to 1$, the closed form $b_{e,1} = t_0\ln\beta/(t'_{R,1}-t'_{R,2}/\beta)$
becomes $0/0$: both numerator and denominator vanish, and the fitted $S_e$ is the
ratio of two small, noisy numbers. Sensitivity analysis for the engine: an error
$\delta$ in either retention time propagates to $S_e$ roughly as
$\delta S_e/S_e \sim \delta/(\varphi_{e,1}-\varphi_{e,2})\cdot S_e$, so the
separation of elution compositions between the two runs is the conditioning number
of the whole fit. **[derived]** from §3.2 — Quarry, Grob & Snyder (1986) is the
paper that owns the rigorous error analysis, and I could not obtain it (§10).

Numerically, for $k_0=500$, $S_e=9$, $t_{G,1}=20$ min, $t_0=1.2$ min, $\tau=0.35$ min,
injecting 0.6 s of timing error into the second run (§11):

| $\beta$ | 3.0 | 2.0 | 1.5 | 1.2 | 1.05 |
|---|---|---|---|---|---|
| $\varphi_{e,1}-\varphi_{e,2}$ | 0.121 | 0.077 | 0.045 | 0.020 | 0.005 |
| resulting error in $S$ | 0.13% | 0.30% | 0.69% | 1.94% | 8.80% |

This is the quantitative case for $\beta = 3$: it is roughly the point past which
extra separation of the two runs stops buying much conditioning, while $\beta<2$
starts amplifying ordinary timing noise into visible parameter error.

Guards to implement:
- ~~Refuse $\beta < 2$ with an explicit error naming the reason.~~ **Amended during
  #15**: SPEC §4 is normative here and says "spacing-ratio warning < 2.5, strong < 1.2,
  **never a hard block**", which CLAUDE.md's warnings-over-blocks rule seconds. A
  $\beta$ of 1.9 is noisy, not impossible. The engine escalates through those two tiers
  (`FitResult.beta_spacing`) and fits anyway.
- Compute $\Delta\varphi_e = \varphi_{e,1}-\varphi_{e,2}$ per peak; if it is smaller
  than a few times the composition-equivalent of retention-time noise, mark the fit
  as low confidence rather than reporting a spuriously precise $S$.
- **Hard failure mode:** if $\varphi_{e,1} \le \varphi_{e,2}$ the root of §3.3 does
  not exist and the data are inconsistent with LSS. Causes: peak mis-tracking
  (most likely), timing noise on a near-degenerate pair, or genuine curvature.
  Report it as "cannot fit — check peak tracking"; do **not** fall back to a
  least-squares fudge that hides a tracking error.

### 7.3 Extrapolation limits

Guillarme et al. (2022): *"extrapolation should be avoided or at least critically
used, as it is a risky procedure."* Predict inside the bracket
$[b_{e,\min}, b_{e,\max}]$ set by the two scouting runs, and warn outside it. Same
applies to $\varphi$: the fit only constrains $\log k$ over $[\varphi_{e,2}, \varphi_{e,1}]$,
which for a $\beta=3$ pair is a **narrow** window — typically well under 20% B. Every
prediction outside it is a linear extrapolation of a relationship known to be curved
(§7.5). This is the single biggest honesty issue for the simulator's UI: it should
show the user how far outside the calibrated window a prediction sits.

### 7.4 Peak crossing / elution-order reversal

Peaks with different $S$ cross as $t_G$ changes — that is the entire point of
gradient-time optimisation, and also its main hazard. Molnár (2002) Fig. 2
demonstrates tracking peaks that swap position between $t_G$ = 40 and 120 min.
Dolan et al.'s DryLab G/plus demonstration (*J. Chromatogr.* **592** (1992) 183, via
[ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/0021967392850825))
reports the counter-intuitive result directly: with two gradients differing by a
factor of three, *"two peak pairs were less well separated in the gradient run with
the lower slope"*, contrary to expectation.

Engine consequences: (a) never assume the predicted order equals the observed order;
re-sort by $t_R$ at every condition; (b) resolution is a function of the *pair
that is currently adjacent*, which itself changes across the map — compute the
critical pair per grid point; (c) at a crossing point $R_s \to 0$ and the map has a
sharp trough — the map's grid must be fine enough not to step over it.

Peak tracking (§3.4 step 3) is where crossings do real damage: if two peaks swap
between the scouting runs and are matched by elution order, both fits are garbage.
Molnár's area-ratio method is the standard defence; UV spectra or MS are better.

### 7.5 When LSS breaks down

$\log k$ vs. $\varphi$ is genuinely curved (concave) over wide ranges. den Uijl et al.
(2021) are direct about it: *"nonlinear models describe the data best"*, there is
*"clear deviation from linearity, especially in the lower $\varphi$ range"*, and LSS
is *"only applicable to the narrow linear range"*. Their practical advice for
LSS users: *"if an LSS model is used it is better to omit data for $\ln k < 0$."*
Poole & Atapattu (2022) likewise treat the linear region as a bounded regime.

The alternatives, if v0.2 wants them (den Uijl et al. 2021a, the review, Eqs. 6–11;
the same five models are Eqs. 1–5 of den Uijl et al. 2021b, ref. 16, which #43
checked the rows against — the adsorption row keeps the review's $k_0$, $n$ where
2021b writes $k_1$, $R$):

| Model | Equation | Runs needed |
|---|---|---|
| Log-linear (LSS) | $\ln k = \ln k_0 - S_{\text{LSS}}\varphi$ | 2 |
| Quadratic | $\ln k = \ln k_0 + S_1\varphi + S_2\varphi^2$ | 3+ |
| Adsorption (log–log) | $\ln k = \ln k_0 - n\ln\varphi$ | 2 |
| Mixed-mode | $\ln k = \ln k_0 + S_1\varphi + S_2\ln\varphi$ | 3+ |
| Neue–Kuss | $\ln k = \ln k_0 + 2\ln(1+S_2\varphi) - \dfrac{S_1\varphi}{1+S_2\varphi}$ | 3+ |

(Two notes on the table. **Symbols:** in the LSS, quadratic and Neue–Kuss rows
$k_0$ is den Uijl's intercept at $\varphi = 0$ — *"often also denoted $\ln k_w$"* —
i.e. this document's $k_w$, not its $k_0$; see §0. The adsorption row's intercept
sits at $\varphi = 1$ (2021b writes $k_1$), and the mixed-mode $k_0$ is neither. The
zoo is natural-log throughout, so the rows lift into the engine's internal
convention without a 2.303. **Neue–Kuss:** this row was originally reconstructed
from a mangled extraction of the review's Eq. 11 and flagged unverified. #43
verified it against 2021b Eq. 5, which extracts cleanly: the grouping was right —
the parameter inside the logarithm is the one in the denominator — and, against
2021b's labels, the subscripts were swapped. The row now follows 2021b:
$S_{2,\text{NK}}$ inside the logarithm and the denominator, $S_{1,\text{NK}}$ in the
numerator. The review's Eq. 11 still renders unreliably (re-checked 2026-09-03),
so whether it labels the pair the other way is not settled [could not verify];
implement from 2021b. §10 item 10.)

den Uijl et al. note that *"when a limited number of input experiments was
desirable, good fits could be found for the two-parameter models (LSS and ADS)"*,
which is a fair defence of a two-run v0.1;
with more measurements the adsorption model fit best in their comparison.

**The honest framing for v0.1:** two runs buy exactly two parameters. LSS is the
right two-parameter choice for a gradient two-run workflow, and it will be locally
accurate near the scouting conditions and progressively wrong away from them.

### 7.6 Instrument reality

The dwell volume is not a nuisance parameter — it is the difference between a
transferable method and a broken one (Molnár §10). Beyaz et al. (2014) is devoted to
which instrument parameters actually control gradient retention precision. Boswell
et al. (2011) go further and *back-calculate the effective gradient and flow-rate
profiles* from standards rather than trusting the programmed profile at all.

For v0.1: require $t_D$ (or $V_D$) as an explicit input with no default, and make
$t_0$ explicit too. Silently defaulting either one produces plausible-looking,
wrong chromatograms.

### 7.7 Accuracy you can honestly claim

Reported in the literature, for well-executed LSS/DryLab-class prediction:

- Molnár (2002), summarising applications: *"Predicted and actual retentions
  typically differed by only 1%"*; *"the average difference between prediction and
  experiment for 10 compounds was less than 10 s"*; a four-step gradient predicted
  with *"a maximum deviation of 1.2% in retention times"*; *"Agreement between
  predicted and actual retention was 0.3%"*; and *"the average deviation between
  predicted and experimental retention times of 16 bands was less than 8 s"*.
- Molnár (2002) also reports a harder case: multi-segmented gradients simulated with
  *"average errors of prediction of retention times between 2 and 8%"*.
- Boswell et al., *J. Chromatogr. A* **1218** (2011) 6742–6749
  ([DOI](https://doi.org/10.1016/j.chroma.2011.07.070)) — not LSS, but the accuracy
  ceiling: retention projections of 20 solutes accurate to **0.23% of gradient time**
  ($R^2$ up to 0.99996), *"approaching reproducibility limits"*, and accuracy that
  *"does not deteriorate when the gradient, the flow rate, or the HPLC instrument is
  changed"* ([method description](http://www.retentionprediction.org/hplc/howitworks.php)).
- Guillarme et al. (2022) measure error in resolution units,
  $\lambda = (t_{r,\text{pred}}-t_{r,\text{exp}})/w$, and hold $\lambda \le 0.5$ as
  the target — a much better error metric for a *separation* simulator than percent
  retention error, because it scales with what the user actually cares about.

**Recommendation: report prediction error in $\lambda$ (fractions of a peak width),
not in percent.** A 1% error on a 30-min run is 18 s, which may be half a peak width
or a tenth of one depending on conditions.

---

## 8. Algorithm pseudocode

### 8.1 Two-run fit (per peak)

```
INPUT  t0, tau (= tD + t_init), phi0, phif, tG1, tG2, tR1, tR2
       # tG2 > tG1; identical column/flow/temperature/composition limits
OUTPUT (ln_k0, S_e) or a typed failure

dphi  = phif - phi0
beta  = tG2 / tG1

# --- guards on the experimental design -----------------------------
assert beta >= 2                              # else degenerate (7.2)

tp1 = tR1 - t0 - tau                          # gradient-corrected times
tp2 = tR2 - t0 - tau

if tp1 <= 0 or tp2 <= 0:
    return Failure.ELUTES_IN_HOLD             # 4.1 — no gradient info

phi_e1 = phi0 + dphi * tp1 / tG1              # Guillarme Eq 14
phi_e2 = phi0 + dphi * tp2 / tG2

if phi_e1 <= phi_e2:
    return Failure.NO_LSS_SOLUTION            # 7.2 — check peak tracking

# --- seed: closed form, large-k0 approximation (3.2) ---------------
b_seed = t0 * ln(beta) / (tp1 - tp2 / beta)

# --- exact solve: 1-D root find (3.3) ------------------------------
def g(b):  return exp(b*tp1/t0) - 1 - beta*(exp(b*tp2/(beta*t0)) - 1)

lo = 1e-9
hi = max(2*b_seed, 1e-3)
while g(hi) < 0 and hi < B_MAX:  hi *= 2      # bracket the nontrivial root
if g(hi) < 0:  return Failure.NO_LSS_SOLUTION

b1 = brentq(g, lo, hi)                        # exclude the trivial root at 0

# --- recover parameters (exact, given b1) --------------------------
A     = (exp(b1 * tp1 / t0) - 1) / b1
k0    = A + tau / t0
S_e   = b1 * tG1 / (t0 * dphi)
ln_k0 = ln(k0)

# --- confidence -----------------------------------------------------
delta_phi_e = phi_e1 - phi_e2                 # conditioning of the fit (7.2)
calibrated_range = (phi_e2, phi_e1)           # where the model is actually known
flag_low_confidence if delta_phi_e < 3 * (dphi/tG1) * timing_noise
flag_implausible    if not (4 <= S_e <= 40)   # ~ S in [1.7, 17]

return (ln_k0, S_e, delta_phi_e, calibrated_range)
```

Note: `S_e` is natural-log. Convert for display: `S_display = S_e / ln(10)`.

### 8.2 Forward prediction of a new gradient (per peak)

```
INPUT  ln_k0_ref, S_e   (fitted at reference phi0_ref)
       new run: phi0, phif, tG, F, Vm, tD, t_init, N
OUTPUT tR, width, regime, warnings

t0   = Vm / F
tau  = tD + t_init
dphi = phif - phi0
k0   = exp(ln_k0_ref - S_e * (phi0 - phi0_ref))   # re-anchor to new phi0
b_e  = S_e * dphi * t0 / tG

# --- regime 1: elutes before the gradient arrives (4.1) ------------
if k0 <= tau / t0:
    tR     = t0 * (1 + k0)
    k_e    = k0
    G      = 1.0                      # isocratic: no compression
    regime = ISOCRATIC_HOLD
else:
    # --- does the gradient finish first? (4.2) ---------------------
    kf   = k0 * exp(-S_e * dphi)
    x_G  = tau/(t0*k0) + (k0/kf - 1)/(k0 * b_e)

    if x_G >= 1:
        # --- regime 2: normal LSS elution (2.2) --------------------
        tR     = tau + t0 + (t0/b_e) * ln(b_e*(k0 - tau/t0) + 1)
        k_e    = k0 / (b_e*(k0 - tau/t0) + 1)
        p      = b_e * k0 / (1 + k0)
        G      = sqrt(1 + p + p*p/3) / (1 + p)
        regime = GRADIENT
    else:
        # --- regime 3: finishes isocratically at phif (4.2) --------
        tR     = tau + tG + t0 + (1 - x_G) * t0 * kf
        k_e    = kf
        G      = 1.0                  # no compression after ramp ends
        regime = POST_GRADIENT

# --- width (5.1) and warnings --------------------------------------
sigma = G * t0 * (1 + k_e) / sqrt(N)
W     = 4 * sigma
W_half= 2.355 * sigma

phi_e = phi0 + dphi * (tR - t0 - tau)/tG   if regime == GRADIENT else n/a
warn if phi_e outside calibrated_range     # 7.3 extrapolation
warn if b_e outside [b_e of the two scouting runs]
warn if k_e < 1 or k_e > 20                # 4.3
warn if regime != GRADIENT                 # 4.1 / 4.2 low confidence
```

### 8.3 Chromatogram / resolution map

```
for each condition in the grid:                    # e.g. tG, or (tG, T)
    peaks = [forward_predict(p, condition) for p in fitted_peaks]
    sort peaks by tR                               # order changes! (7.4)
    for each adjacent pair (i, i+1):
        Rs[i] = 2*(tR[i+1] - tR[i]) / (W[i] + W[i+1])
    critical_Rs[condition] = min(Rs)
    critical_pair[condition] = argmin(Rs)
optimum = argmax(critical_Rs)                      # prefer a broad plateau
```

Grid resolution matters: crossings produce narrow $R_s \to 0$ troughs (§7.4).
Refine adaptively around any pair whose $R_s$ changes sharply between grid points.

---

## 9. Recommended v0.1 scope

Based on the above, the defensible minimum:

1. Natural-log internals, base-10 at the UI boundary (§0).
2. Per-peak state $(\ln k_0, S_e)$ anchored at $\varphi_0$, not $\ln k_w$ (§1.1).
3. Two-run fit: closed-form seed + Brent root-find, with the typed failures of §8.1.
4. Forward prediction with all three regimes of §8.2 branched explicitly.
5. Width via $N$ + $G$ (§5), resolution via widths (§6).
6. Every prediction carries its regime, its distance outside the calibrated
   $\varphi$ window, and a $\lambda$-style error expectation — not a bare number.

Deliberately **out** of v0.1: curved retention models (§7.5), fitted per-peak $N$,
back-calculated gradient profiles (§7.6), temperature as a second dimension.

---

## 10. What I could NOT verify

Stated explicitly, per the ticket. These are the claims a reviewer should treat as
weaker than the rest of the document.

1. **Snyder & Dolan, *High-Performance Gradient Elution* (Wiley, 2007)** — the
   primary text named in the ticket. Paywalled; I could not read a single page.
   Everything attributed to it here reaches me through papers that cite it
   (Wilson et al. 2016 for $G$; Wang et al. 2006 for the width equation; Guillarme
   et al. 2022 and Molnár 2002 generally). Chapter/equation numbers are therefore
   absent from my citations of it.
2. **Quarry, Grob & Snyder, *Anal. Chem.* 58 (1986) 907–917**, "Prediction of
   precise isocratic retention data from two or more gradient elution runs.
   Analysis of some associated errors" — citation confirmed via OpenAlex
   ([DOI](https://doi.org/10.1021/ac00295a056)); ACS returned HTTP 403 and no
   abstract is exposed in the metadata. **This is the paper that owns the rigorous
   error analysis of the two-run fit**, and my §7.2 error-propagation argument is my
   own derivation, not theirs. If anyone gets library access, this is the first
   thing to read.
3. **Snyder, Dolan & Gant, *J. Chromatogr. A* 165 (1979) 3–30** — citation confirmed
   via OpenAlex; full text not retrieved (ScienceDirect 403). Cited as the origin of
   LSS, not for any specific equation form.
4. **Poppe, Paanakker & Bronckhorst, *J. Chromatogr.* 204 (1981) 77** — original not
   retrieved. The $G$ equation is verified from two independent papers that both
   attribute it there and that agree character-for-character on the algebra.
5. **The log-base convention inside $p$ for $G$.** Both sources write
   $p = b k_0/(1+k_0)$ with no 2.303, which forces the natural-log reading I adopted.
   I could not confirm this against Snyder & Dolan's own text. If a base-10 $b$ were
   intended, every $G$ is wrong by ~10–15% at typical steepness. **Flagged as the
   highest-risk number in this document.** Cheap resolution: check a computed $G$
   against a measured peak width once real data exists.

   **Update (ticket #17): RESOLVED — see §5.4.** The lab widths were used as
   proposed, and once runs 3 and 4 were measured they settled it: holding one
   column's plate count constant across a fourfold range of gradient steepness
   works to 0.92% under the natural-log reading and to 5–13% under every
   alternative, including the $p \times \ln 10$ mirror. Confirmed on held-out data.
   No longer the highest-risk number in this document.
6. **LCGC columns by Dolan, Snyder, Stoll** (chromatographyonline.com) — every URL
   returned HTTP 403. The Stoll quotation in §5.2 about the ~10% width effect comes
   from a search-result summary of that article, not the article itself.
7. **$k^* = t_G F/(1.15\,\Delta\varphi\,S\,V_m)$** and the origin of the 1.15 factor —
   widely quoted in Snyder/Dolan's LCGC columns; I could not reach a fetchable
   statement of it. **Not used anywhere in this document** — the engine uses the
   sourced $k_e$ of §2.3 instead, which is exact within LSS rather than an average.
8. **The gradient "master resolution equation"**
   $R_s = \frac{1}{4}(\alpha-1)\sqrt N \frac{k^*}{1+k^*}G$ — quoted in secondary
   summaries; exact form unverified. **Not used** — §6 uses the width-based
   definition, which the engine can evaluate exactly.
9. **$S \approx 0.25\,M^{0.5}$** — attributed to Snyder in a search summary of an
   ACS Omega paper whose page returned 403. Treat as folklore-grade; §1.2's Poole &
   Atapattu ranges are the verified numbers.
10. **The Neue–Kuss equation in §7.5** — the extraction of den Uijl Eq. 11 was
    mangled and my reconstruction of the grouping is a guess. Do not implement from
    this table; go to the source.

    **Update (ticket #43, applied under #48): RESOLVED — see §7.5.** #43 went to
    the source — den Uijl et al. 2021b (ref. 16) Eq. 5, which extracts cleanly. The
    grouping was right and the subscripts were swapped; §7.5 now carries the
    verified form and the table is implementable as a stated alternative model.
    The caveat that remains is den Uijl's own measurement, not a typography doubt:
    Neue–Kuss *"results in a poor description when the input data is limited to
    three gradient durations"* and is less robust to fit than the two-parameter
    models. Three parameters means three runs by count; expect it to want more
    [derived: poor at three input gradients, good at eight]
    (`composition-extrapolation.md` §4.1, §5.3).
11. **DryLab's internal solver** — whether it uses a closed form, Newton iteration,
    or something else is proprietary. Molnár (2002) documents the *workflow* and the
    *experimental design* (which is what §3.4 cites it for), not the numerics.
12. **Wang et al. (2006) Eq. 15 and Wilson et al. (2016) Eq. 4 exact typography** —
    the HTML extraction dropped radicals and superscripts. I reconstructed $\sqrt N$
    from dimensional consistency and from Guillarme Eq. 13, which rendered cleanly.
    The reconstruction is sound but is a reconstruction.

Against that, §11 records what I *was* able to verify numerically — which covers the
whole computational core, just not the provenance of the two constants above.

---

## 11. Numerical verification of this document

Before committing, I implemented every equation in §2–§6 and §8 in pure Python and
checked them against each other and against brute-force numerical integration of the
general equation (§2.1), using composite Simpson quadrature split at the gradient
kinks and bisection for root-finding. Test conditions: $t_0 = 1.2$ min,
$\tau = 0.35$ min, $\varphi_0 = 0.05$, $\Delta\varphi = 0.90$. Results:

| # | Check | Result |
|---|---|---|
| 1 | Branched closed form (§2.2, §4.1, §4.2) vs. numerical integration of §2.1, over 8 cases spanning $k_0 = 0.2$ to $2\times10^6$, $S_e = 5$–25, $t_G = 5$–60 min | agrees to **1e-14 min**; all three regimes (HOLD, GRADIENT, POST) exercised |
| 2 | Continuity of the GRADIENT/POST branches at $x_G = 1$ | joins to within the perturbation used to straddle it; both sides land on $\tau + t_G + t_0$ |
| 3 | Two-run fit (§8.1) round-trip: synthesise $t_{R,1},t_{R,2}$ from known $(k_0,S_e)$, refit | recovers both parameters to **~1e-14 relative**, over $k_0 = 8$–$10^4$ |
| 3b | Fit conditioning vs. $\beta$ | table in §7.2 |
| 4 | The three $R_s$ forms in §6 | identical to floating point with the exact $\sqrt{8\ln2}$ constant |
| 5 | $G(p)$ over $b_e = 0$–3 | table in §5.2 |
| 6 | $t_R = \tau + t_0 + (t_0/b_e)\ln(k_0/k_e)$, and the two $\varphi_e$ expressions of §2.3 | agree to **1e-16** |
| 7 | Base-10 and natural-log forms of the retention equation (§0) | agree to **6e-12** |

Checks 1, 6 and 7 are the ones that matter most: check 1 says the closed form I
derived and the branch logic for the edge cases are genuinely solutions of the
fundamental equation, and checks 6–7 say the identities and the two log conventions
are mutually consistent rather than accidentally similar.

What this does **not** validate: whether the *physics* is right (that is what §10's
unverified items are about), and in particular the log-base convention inside $p$ for
$G$ (§10 item 5) — self-consistency cannot catch a factor of 2.303 that is wrong in
the source I copied it from.

The verification script is not committed (this ticket's deliverable is a single
document); it is straightforward to regenerate from §8's pseudocode, and reproducing
checks 1, 3 and 6 as unit tests is the recommended first commit of the engine.

---

## References

Ordered roughly by how load-bearing they are here.

1. **Guillarme, D.; Bouvarel, T.; Rouvière, F.; Heinisch, S.** "A simple mathematical
   treatment for predicting linear solvent strength behavior in gradient elution:
   Application to biomolecules." *J. Sep. Sci.* **45** (2022) 3276–3285.
   [doi:10.1002/jssc.202200161](https://doi.org/10.1002/jssc.202200161) —
   **open access**. LSS Eqs. 1–7, elution composition Eqs. 3/14, the two-run
   closed form Eqs. 8–10/16, retention prediction Eq. 15, width Eq. 13, the
   $\log k_i > 2.1$ constraint, the $\beta = 3$ recommendation, the $\lambda$ error
   metric, and the warning against extrapolation. *The most directly useful single
   source for this ticket.*
2. **Beyaz, A.; Fan, W.; Carr, P. W.; Schellinger, A. P.** "Instrument Parameters
   Controlling Retention Precision in Gradient Elution Reversed-Phase Liquid
   Chromatography." *J. Chromatogr. A* **1371** (2014) 90–105.
   [doi:10.1016/j.chroma.2014.09.085](https://doi.org/10.1016/j.chroma.2014.09.085);
   [PMC4388777](https://pmc.ncbi.nlm.nih.gov/articles/PMC4388777/) — LSS Eq. 1,
   retention Eq. 2 (with $t_D$), steepness Eq. 3 in the $V_m\Delta\varphi S/(t_G F)$
   form. Also the reference for how instrument imperfection limits everything above.
3. **Molnár, I.** "Computerized design of separation strategies by reversed-phase
   liquid chromatography: development of DryLab software." *J. Chromatogr. A*
   **965** (2002) 175–194.
   [doi:10.1016/S0021-9673(02)00731-8](https://doi.org/10.1016/S0021-9673(02)00731-8);
   [publisher PDF](https://molnar-institute.com/fileadmin/user_upload/Literature/_2002_Molnar_Compu.pdf) —
   the DryLab-class workflow: two-run design at $\beta=3$ (Table 1), peak tracking by
   area (§8), dwell volume (§10), resolution map and $R_s$ formula (Fig. 1),
   $1<k<20$ practice (§16), and the accuracy figures quoted in §7.7.
4. **den Uijl, M. J.; Schoenmakers, P. J.; Pirok, B. W. J.; van Bommel, M. R.**
   "Recent applications of retention modelling in liquid chromatography."
   *J. Sep. Sci.* **44** (2021) 88–114.
   [doi:10.1002/jssc.202000905](https://doi.org/10.1002/jssc.202000905);
   [PMC7821232](https://pmc.ncbi.nlm.nih.gov/articles/PMC7821232/) — the general
   gradient equation (Eqs. 3–4), the model zoo (Eqs. 6–11), LSS validity limits and
   curvature, and the nuanced view of the gradient-time ratio.
5. **Wang, X.; Stoll, D. R.; Schellinger, A. P.; Carr, P. W.** "Peak Capacity
   Optimization of Peptide Separations in Reversed-Phase Gradient Elution
   Chromatography: Fixed Column Format." *Anal. Chem.* **78** (2006) 3406–3416.
   [PMC2638764](https://pmc.ncbi.nlm.nih.gov/articles/PMC2638764/) — steepness
   Eq. 14, width Eq. 15 (with $G$, attributed to Snyder), $k_f$ at elution Eq. 16
   (with the dwell correction).
6. **Wilson, R. E.; Groskreutz, S. R.; Weber, S. G.** "Improving the Sensitivity,
   Resolution, and Peak Capacity of Gradient Elution in Capillary Liquid
   Chromatography with Large-Volume Injections by Using Temperature-Assisted
   On-Column Solute Focusing." *Anal. Chem.* **88** (2016) 5112–5121.
   [doi:10.1021/acs.analchem.5b04793](https://doi.org/10.1021/acs.analchem.5b04793);
   [PMC4940048](https://pmc.ncbi.nlm.nih.gov/articles/PMC4940048/) — band
   compression $G(p)$ Eqs. 8–9 and $b$ Eq. 10, attributed to Snyder & Dolan (2007).
7. **Hao, W.; Liu, L.; Shen, Q.** "Effects of peak compression in gradient elution of
   liquid chromatography." *Se Pu (Chin. J. Chromatogr.)* **39** (2021) 10–14.
   [doi:10.3724/SP.J.1123.2020.07042](https://doi.org/10.3724/SP.J.1123.2020.07042);
   [PMC9274839](https://pmc.ncbi.nlm.nih.gov/articles/PMC9274839/) — independent
   statement of Poppe's $G$ (Eq. 3) with $p = k_{\varphi_0}BSt_0/(1+k_{\varphi_0})$,
   plus a dwell-aware generalisation (Eq. 10).
8. **Poole, C. F.; Atapattu, S. N.** "Analysis of the solvent strength parameter
   (linear solvent strength model) for isocratic separations in reversed-phase
   liquid chromatography." *J. Chromatogr. A* **1675** (2022) 463153.
   [doi:10.1016/j.chroma.2022.463153](https://doi.org/10.1016/j.chroma.2022.463153) —
   measured $S$ per solvent and the 1.69–6.33 range; the warning about $\log k_w$.
9. **Boswell, P. G.; Schellenberg, J. R.; Carr, P. W.; Cohen, J. D.; Hegeman, A. D.**
   "Easy and accurate high-performance liquid chromatography retention prediction
   with different gradients, flow rates, and instruments by back-calculation of
   gradient and flow rate profiles." *J. Chromatogr. A* **1218** (2011) 6742–6749.
   [doi:10.1016/j.chroma.2011.07.070](https://doi.org/10.1016/j.chroma.2011.07.070) —
   the accuracy ceiling (0.23% of gradient time) and the back-calculation idea.
   Companion paper: same authors, *J. Chromatogr. A* **1218** (2011) 6732–6741
   ("retention projection"). Method description:
   [retentionprediction.org/hplc/howitworks.php](http://www.retentionprediction.org/hplc/howitworks.php).
10. **Snyder, L. R.; Dolan, J. W.; Gant, J. R.** "Gradient elution in
    high-performance liquid chromatography. I. Theoretical basis for reversed-phase
    systems." *J. Chromatogr. A* **165** (1979) 3–30.
    [doi:10.1016/S0021-9673(00)85726-X](https://doi.org/10.1016/S0021-9673(00)85726-X) —
    origin of LSS. Part II (practical verification): *J. Chromatogr. A* **165**
    (1979) 31–58. **Not read** (§10).
11. **Snyder, L. R.; Dolan, J. W.** *High-Performance Gradient Elution: The Practical
    Application of the Linear-Solvent-Strength Model.* Wiley, 2007.
    ISBN 978-0-471-70646-5. **Not read** (§10) — cited only via refs. 1, 3, 5, 6.
12. **Quarry, M. A.; Grob, R. L.; Snyder, L. R.** "Prediction of precise isocratic
    retention data from two or more gradient elution runs. Analysis of some
    associated errors." *Anal. Chem.* **58** (1986) 907–917.
    [doi:10.1021/ac00295a056](https://doi.org/10.1021/ac00295a056).
    **Not read** (§10) — the missing primary source for two-run error analysis.
13. **Broeckhoven, K.; Desmet, G.** "Theory of separation performance and peak width
    in gradient elution liquid chromatography: A tutorial." *Anal. Chim. Acta*
    **1218** (2022) 339962.
    [doi:10.1016/j.aca.2022.339962](https://doi.org/10.1016/j.aca.2022.339962) —
    abstract only; identified as the best single tutorial if peak-width fidelity
    becomes a priority. **Not read in full.**
14. **Poppe, H.; Paanakker, J.; Bronckhorst, M.** "Peak width in solvent-programmed
    chromatography. I." *J. Chromatogr.* **204** (1981) 77. Origin of the band
    compression factor $G$. **Not read** (§10) — verified via refs. 6 and 7.
15. **Dolan, J. W.; et al.** "Application of the gradient elution technique:
    demonstration with a special test mixture and the DryLab G/plus method
    development software." *J. Chromatogr.* **592** (1992) 183.
    [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/0021967392850825) —
    abstract only; source of the counter-intuitive peak-crossing observation in §7.4.
16. **den Uijl, M. J.; Schoenmakers, P. J.; Schulte, G. K.; Stoll, D. R.;
    van Bommel, M. R.; Pirok, B. W. J.** "Measuring and using scanning-gradient
    data for use in method optimization for liquid chromatography."
    *J. Chromatogr. A* **1636** (2021) 461780.
    [doi:10.1016/j.chroma.2020.461780](https://doi.org/10.1016/j.chroma.2020.461780);
    [author PDF](https://pure.uva.nl/ws/files/54095340/2021_Den_Uijl_PROMISE.pdf) —
    Eqs. 1–5, the five retention models of §7.5 in natural-log form, against which
    that table (the Neue–Kuss row in particular) was verified by #43; the source of
    the $k_0$-means-$k_w$ note in §0. Cited as *2021b*; ref. 4, the review, is
    *2021a*. Added 2026-09-03 under #48.
17. **Dolan, J. W.; Lommen, D. C.; Snyder, L. R.** *J. Chromatogr.* **535** —
    cited by Molnár (2002) §8 as the source of the design spans quoted in §7.1
    (15–20 %B, a factor of three in gradient time, 20–30 °C, 0.5–0.6 pH units).
    **Not read**; volume as Molnár cites it, year/title/pages not verified. Added
    2026-09-03 under #48.

---

*Compiled 2026-08-24 for issue #2. Branch: `research/gradient-math`. Amended
2026-09-03 under #48 with #43's corrections: §0, §1, §7.1, §7.5, §10 item 10, refs. 16–17;
and under #54 with #52's dwell-sensitivity identity: §2.3.*
