# How badly does an LSS fit extrapolate in composition (φ)?

Research notes for the v0.2 gradient-freedom map. Resolves issue #43
(parent: map issue #41). Audience: whoever designs the composition-window
honesty diagnostic (#44) and the acceptance bar for changed φ ranges (#46).

Every claim is tagged **[verified]** (I opened the paper, its full text or its
authors' own abstract and the statement is what it says), **[derived]** (my own
algebra, my own arithmetic on this repository's data, or my own recommendation),
or **[could not verify]**. Section 9 lists everything I could not verify.
Nothing below is described from a search-result snippet: where a search engine
offered a number I could not open at source, it is listed in §9 as unverified
and is not used to support a recommendation. I did not run any third-party code;
the arithmetic in §2 and §7 is my own, on this repository's own
`validation/` data, and every step of it is shown so it can be re-checked.

Survey date: 2026-09-02.

**Log convention.** This document follows CLAUDE.md: retention math is in the
natural-log convention (S_e, b_e), and base-10 (S) appears only where a source
uses it, always flagged. The two are related by S_e = ln(10)·S ≈ 2.303·S. φ is a
fraction 0–1; where a source quotes %B or "%ΔC" I convert and say so.
**A specific trap appears in §1**: the central formula of this document has the
*same algebraic form* in both conventions, so it cannot be caught by inspection —
only by checking that the S you divide by matches the log you take.

---

## 0. Method and coverage

**What the ticket asked for, and what exists [derived].** The ticket asked for
the composition analogue of den Uijl et al. 2021's gradient-time extrapolation
study. **That study does not exist.** I found no paper that varies the
calibration φ window and reports prediction error as a function of distance from
it — the direct experiment. What does exist, and is enough to settle the design
questions, is: (a) an exact analytic expression for the width of the calibrated
composition window, published by Guillarme et al. 2022 and *measured* by them
across three compound classes; (b) a large body of work establishing that ln k
vs φ is curved and that the log-linear model is a locally-valid approximation;
(c) one explicit statement, from Rutan/Cash/Stoll 2023, making composition-window
agreement a *precondition* of an accuracy claim; and (d) Snyder's own
"15–20% change in %B" rule, which is the φ half of the same sentence this
repository already quotes for β = 3.

**Sources opened in full [verified].** den Uijl et al. 2021 (J. Chromatogr. A
1636, 461780) — the PDF from the UvA repository, text-extracted and read end to
end, including the equations and the concluding remarks; den Uijl et al. 2021
(J. Sep. Sci. 44, 88–114) via PMC7821232; Guillarme et al. 2022 (J. Sep. Sci.
45, 3276–3285) via PMC9543774, read end to end — **this is the load-bearing
source of this document and the repository was under-reading it**; Molnár 2002
(J. Chromatogr. A 965, 175–194) via the publisher PDF.

**Sources read as the authors' own published abstract only [verified as
abstracts].** Rutan, Cash & Stoll 2023 (J. Chromatogr. A 1711, 464443);
Neue & Kuss 2010 (J. Chromatogr. A 1217, 3794–3803); Nikitas & Pappa-Louisi 2009
(J. Chromatogr. A 1216, 1737–1755); Baeza-Baeza et al. 2013 (J. Chromatogr. A
1284, 28–35). All four via the NCBI E-utilities abstract service. These are the
authors' words, not a summariser's, but they are abstracts: no figure, table or
per-compound number from these papers is claimed here.

**Blocked [could not verify], detail in §9.** ScienceDirect returned HTTP 403 to
every route I tried, which cost me two open-access *Journal of Chromatography
Open* tutorials that are directly on topic (Peiró-Vila et al. 2024; David &
Moldoveanu 2024), and the RODERIC green-OA copy of Baeza-Baeza 2013 sits behind
an anti-bot challenge. ChemRxiv and DOAJ's article pages also 403'd. Chrome
automation was available but required an interactive browser choice I could not
make from a background task.

**Licences [verified].** No code was ported or read for this ticket. For the
record, since v0.2 may want the tooling: MOREPEAKS (used by den Uijl to fit the
five models) is CC BY 4.0 on Zenodo but ships as a Windows MATLAB-runtime binary,
so there is nothing to re-derive from; Guillarme et al. distribute their two-run
Excel tool "freely available on our website" with no licence stated
[verified from the paper's text]; the MATLAB functions accompanying the
Peiró-Vila 2024 tutorial are described in its abstract but I could not open the
article to check their licence [could not verify]. This project re-derives
rather than ports, so none of this is blocking.

---

## 1. The window law: Δφ_e = ln β / S_e

This is the analytic core of the ticket, and it turns out to be **already
published, exactly, in the repository's own most-cited source**.

Guillarme et al. 2022 build up to it as follows [all verified from the PMC full
text]. Their retention model is **base-10**:

> log k_e = log k_0 − S × C_e  (their Eq. 2)

where — and this is a symbol collision worth pinning, see §8.3 — *their* `k_0` is
"the (extrapolated) value of k in pure water (C = 0)", i.e. what this repository
calls **k_w**, while their `k_i` is "the retention factor under initial gradient
conditions", i.e. what this repository calls **k_0**.

They define a **normalised gradient slope**

> s* = t_0 × ΔC / t_g  (their Eq. 6)

note that ΔC — the composition span — is *inside* it; then, assuming 1/k_i
negligible (the large-k_i approximation), k_e = 1/(2.3 × S × s*) (their Eq. 7),
and combining with their Eq. 3 they obtain

> C_e = (1/S) log s* + (1/S) log(2.3 × S) + (1/S) log k_0  (their Eq. 8)

from which, for one compound between two runs, comes the expression this ticket
was looking for:

> **ΔC_e = (1/S) log (s*_2 / s*_1)**  (their Eq. 16)

**Translation into this repository's convention [derived].** Their C is a volume
fraction quoted as a percentage; their S and log are base-10. Writing φ for C and
converting with S_e = ln(10)·S:

$$\Delta\varphi_e \;=\; \frac{1}{S}\log_{10}\frac{s^*_1}{s^*_2} \;=\; \frac{1}{S_e}\ln\frac{s^*_1}{s^*_2}$$

and when the two scouting runs differ **only** in t_G — which SPEC §4 mandates
("only tG differs") — the t_0 and Δφ in s* cancel, s*_1/s*_2 = t_{G,2}/t_{G,1} = β,
and the result collapses to

$$\boxed{\;\Delta\varphi_e \;=\; \frac{\ln \beta}{S_e} \;=\; \frac{\log_{10}\beta}{S}\;}$$

**The log-convention trap here [derived].** The boxed formula has *identical
algebraic form* in both conventions — `ln` with `S_e`, `log10` with `S`. A
mismatched pair (log10 with S_e, or ln with S) is off by a factor of ln 10 ≈ 2.303
and looks perfectly reasonable on screen: it turns a 9 %B window into a 22 %B
window or a 4 %B one. There is no stray 2.303 to spot, which is precisely how
CLAUDE.md's #1 hazard bites. This is a good candidate for an explicit unit test.

**Numerical verification against this repository's own §7.2 table [verified].**
`gradient-elution-math.md` §7.2 tabulates φ_{e,1} − φ_{e,2} against β for
S_e = 9, obtained numerically. The law reproduces it:

| β | 3.0 | 2.0 | 1.5 | 1.2 | 1.05 |
|---|---|---|---|---|---|
| research doc §7.2 table | 0.121 | 0.077 | 0.045 | 0.020 | 0.005 |
| ln β / S_e (this section) | 0.1221 | 0.0770 | 0.0451 | 0.0203 | 0.0054 |

Agreement to the table's stated precision at every point. §7.2's table was
computed by simulation; it turns out to have a two-symbol closed form.

### 1.1 Four consequences that fall straight out [derived]

1. **The calibrated composition window depends on β and S_e and on nothing
   else.** Not on t_G, not on t_0, not on the scouting gradient's own φ range.
2. **Widening the scouting gradient's %B range does not widen the calibrated
   window.** Δφ cancels. Running 5→95 %B instead of 30→70 %B buys elution
   coverage, not conditioning. This is counter-intuitive and is the single
   most likely wrong assumption a user (or a designer) will bring to v0.2.
3. **The window narrows as S_e grows** — so the peaks with the strongest
   composition dependence, the ones whose retention moves most when you change
   the φ range, are exactly the ones whose LSS line is pinned over the shortest
   stretch. The error is worst where it matters most.
4. **The window widens only logarithmically in β.** Doubling it requires β², i.e.
   β = 9 instead of 3; tripling it requires β = 27. There is no practical
   experiment design that makes a two-run composition window wide.

---

## 2. How narrow is it, really?

### 2.1 Measured, across compound classes [verified]

Guillarme et al. 2022 Figure 3 plots ΔC_e against S for six proteins, 36
peptides and nine small molecules (each with both MeOH and ACN), at a
**normalised-slope ratio of 10** (their t_G1 vs t_G5). Their numbers, verbatim
from the text:

> "For the proteins (red triangles), ΔC_e was on average equal to 1.7%, while
> this value increases to 5.2% for peptides (green square) and 15.3% for small
> molecules (blue circle). Interestingly, for the two largest proteins, namely
> intact mAb, and human albumin, ΔC_e was equal to 0.57 and 0.45%,
> respectively."

and, for the worst case among small molecules:

> "…for which a ΔC_e of more than 20% was observed (see the case of parabens)
> when using MeOH as an organic modifier."

**Cross-check [derived].** Inverting the boxed law at a slope ratio of 10 gives
the base-10 S implied by each average: 1/0.153 = 6.5 (small molecules),
1/0.052 = 19.2 (peptides), 1/0.017 = 58.8 (proteins), 1/0.0045 = 222 (albumin).
Those are exactly the S values the literature reports for those classes — small
molecules 1.69–6.33 per Poole & Atapattu as quoted in `gradient-elution-math.md`
§1.2, peptides in the tens, proteins in the tens-to-hundreds. The law, the
figure and the independent S literature are mutually consistent, which is good
evidence that I have read their units correctly.

**Note the ratio.** Those figures are for a slope ratio of **10**. At the β = 3
this project recommends, every number above shrinks by
log10(3)/log10(10) = 0.477 — **the window is less than half as wide as
Guillarme's Figure 3 suggests at a glance**. For small molecules at β = 3, the
average window is 15.3% × 0.477 ≈ **7.3 %B**.

Reference table [derived from the boxed law]:

| S (base-10) | S_e | Δφ_e at β = 3 | Δφ_e at β = 10 |
|---|---|---|---|
| 2 | 4.6 | 0.239 (23.9 %B) | 0.500 (50.0 %B) |
| 3 | 6.9 | 0.159 (15.9 %B) | 0.333 (33.3 %B) |
| 4 | 9.2 | 0.119 (11.9 %B) | 0.250 (25.0 %B) |
| 5 | 11.5 | 0.095 (9.5 %B) | 0.200 (20.0 %B) |
| 6 | 13.8 | 0.080 (8.0 %B) | 0.167 (16.7 %B) |

### 2.2 On this project's own lab dataset [derived]

Computed from `validation/` — `method.csv` (t_0 = 0.6 min, the fixture value when this was
computed; re-baselined to 0.525 on 2026-09-03, #24 — the numbers below are left as computed,
t_D = 0.9375, t_init = 0.5, so τ = 1.4375; φ_0 = 0.05, φ_f = 0.95) and the
retention times in `run1.csv` / `run2.csv`, using the exact elution-composition
identity φ_e = φ_0 + Δφ·(t_R − t_0 − τ)/t_G (`gradient-elution-math.md` §2.3):

| peak | φ_e run 1 (t_G 15) | φ_e run 2 (t_G 45) | Δφ_e | in %B | implied S_e | implied S |
|---|---|---|---|---|---|---|
| 1 | 0.5191 | 0.4259 | 0.0932 | 9.3 | 11.79 | 5.12 |
| 2 | 0.6233 | 0.5279 | 0.0954 | 9.5 | 11.52 | 5.00 |
| 3 | 0.8973 | 0.8052 | 0.0921 | 9.2 | 11.93 | 5.18 |

**Both scouting runs sweep 5→95 %B — a 90 %B ramp — and each peak's LSS line is
pinned over about 9.4 %B of it, roughly one tenth.** The implied base-10 S of
5.0–5.2 sits inside Poole & Atapattu's 1.69–6.33 range, so this is an ordinary
small-molecule result, not a pathology of this sample.

**And the three windows do not overlap.** Peak 1 is calibrated over
[0.426, 0.519], peak 3 over [0.805, 0.897]. There is no such thing as "the
method's calibrated composition range": the union, 0.426–0.897, is 47 %B wide
and is calibrated for **no peak at all**. Any method-level φ window shown to a
user would be a fiction. This decides the per-peak / per-method question in §10.

---

## 3. Does anyone measure prediction error against distance in φ?

### 3.1 den Uijl 2021 cannot answer it — and it is worth saying why [verified]

The paper this ticket takes as its model varies gradient *slope* only. From its
experimental section: Set X ran "a linear gradient to 100% B in either 1.5, 3,
3.75, 4.5, 6, 7.5, 9 or 12 min" with mobile phase A = buffer/ACN 95/5 and
B = ACN/buffer 95/5 — i.e. **5→95 %B**, the same span as this repository's lab
dataset; Set Y "started at 5% B at 0 min, followed by a linear gradient to 85% B"
in ten different times. Their concluding remarks confirm the design: the
benchmark scanning set is "from 5 to 95% or 5% to 85% of strong solvent for Set X
and Set Y, respectively". **Every gradient in the study spans the full range;
the φ range is a constant, not a variable.** Their extrapolation results —
including the ones already quoted in `github-hplc-simulators.md` §3 — are
strictly about slope.

What den Uijl *does* contribute to this ticket is their **Eq. 10** [verified]:

> β₂₁ = (t_G,2 / t_G,1) × (Δφ₁ / Δφ₂) × (t_0,1 / t_0,2)

with the surrounding text: "the effective slope of a gradient is also related to
the span of the gradient (Δφ = φ_final − φ_initial) and to the dead time (t_0),
so that changes in the gradient slope may also occur when changing the flow
rate." This is the same statement as Guillarme's s* = t_0ΔC/t_g, from an
independent group. **Two primary sources agree that changing the composition
span changes the effective gradient slope.** That is the bridge between the
tG axis and the φ axis, and §7 builds the design recommendation on it.

Their quantitative slope-extrapolation results, for calibration
[verified]: interpolation errors "mostly less than 0.5%" (Set X) and "almost all
… below 0.2%" (Set Y); extrapolating a 12-min gradient from a fast (1.5, 3, 4.5)
scanning set gives "large errors of up to 4% … In a hypothetical 20-min gradient,
this amount[s] to a difference of 48 s"; and "In almost all cases the retention
in slow gradients is overestimated by the model."

### 3.2 Guillarme 2022: extrapolation measured in peak widths [verified]

Guillarme et al. measure error as λ = (t_R,pred − t_R,exp)/w — error in units of
peak width — and hold λ ≤ 0.5 as the target. `gradient-elution-math.md` §7.7
already recommends adopting this metric. Their interpolation-vs-extrapolation
experiment (predict t_G2, t_G3 inside the t_G1–t_G4 bracket; t_G0, t_G5 outside):

> "As expected, the λ error values were very good by interpolation (Figure 4A),
> despite a ratio of 5 between the two gradient times… In terms of retention time
> prediction for t_G3, more than 90% of the λ values were below 0.5"

> "The prediction results were less good by extrapolation (Figure 4B), confirming
> that **retention models can be considered linear only within a limited retention
> window**. This is particularly true for the two peptides (#1 and #20) offering
> λ values higher than 2, such value corresponding to the bad case where predicted
> and experimental peaks would be fully baseline resolved. The vast majority of
> peptides exhibit λ values above 0.5, either for t_G0 or for t_G5. Even in the
> case of proteins, the errors can reach λ value up to 1 by extrapolation."

> "…extrapolation should not be considered, whatever the type of compound, as the
> risk to obtain inaccurate predictions of retention times becomes too high."

**This is the most useful quantitative extrapolation result available** [derived]:
crossing from inside to outside the bracket moves the *majority* of peptides from
below the λ = 0.5 acceptance threshold to above it, and the worst cases reach
λ > 2 — a full baseline separation between where the peak was predicted and
where it came out. Their caveat, in their own words, is that λ for proteins "can
be overestimated… since the calculation is based on the average peak width value
(w), which considers the maximum plate number". Note also this is still a
*slope* extrapolation, not a composition one — but by §1 the two are the same
axis.

### 3.3 Rutan, Cash & Stoll 2023: the composition-window proviso [verified, abstract]

The closest thing in the literature to an explicit φ-window condition, and it is
stated as a precondition on an accuracy claim rather than as a rule:

> "The average magnitude of error of the isocratic retention factors predicted
> from parameters obtained from fits of gradient data was 1.6 %, **provided that
> the range of organic solvent compositions that the solute sampled in the mobile
> phase gradient experiments was consistent with the isocratic experiments.**"

Two further numbers from the same abstract bear directly on §6's conditioning
argument. Comparing their re-parameterised Neue–Kuss model against the original
parameterisation, fitted to gradient data at their highest noise level:
parameter errors of "7.2 % for S1,ref, 18 % for S2,ref and 6.2 % for kref"
against "23 % for S1, 25 % for S2 and **160 % for kw**"; and isocratic retention
factors predicted with "an average magnitude of error of 0.51 % for the
re-parameterized model, as opposed to **6800 %** for the model with the original
parameterization."

**Why that matters here [derived].** k_w is k at φ = 0 — the far end of an
extrapolation from a calibration window that never goes near pure water. It is
the parameter that blows up (160%), and a model parameterised *on* it propagates
that blow-up into a 6800% prediction error while the *same model*, re-anchored on
a reference composition inside the measured range (k_ref), predicts to 0.51%.
The model was not wrong; the anchor point was outside the data. This is the
conditioning argument of §6 in its most vivid published form, and it is a direct
argument for reporting and reasoning in terms of k at a composition inside the
window rather than k_w.

### 3.4 Baeza-Baeza et al. 2013: the nearest thing to the missing experiment [verified, abstract]

> "As in isocratic elution, the linear relationship between the logarithm of the
> retention factor and the solvent contents is only acceptable in relatively small
> concentration ranges of modifier. However, more complex models may not allow an
> analytical integration of the general equation for gradient elution.
> Alternative approaches for modelling the retention in linear gradient elution
> are here proposed. Those based on the quadratic logarithmic model and a model
> proposed for normal liquid chromatography yielded accurate predictions of the
> retention time **for a wide range of initial concentrations of organic modifier
> and gradient slopes, with errors usually below 1-2%**."

This is the one paper I found whose stated variable is the **initial organic
modifier concentration** — φ_0, precisely v0.2's new freedom — alongside gradient
slope. Its claim is that the *quadratic* model holds to 1–2% across a wide range
of φ_0, with the log-linear model explicitly restricted to "relatively small
concentration ranges". I could not obtain the full text (§9), so the per-compound
numbers, the actual φ_0 range tested, and the corresponding LSS errors are
unknown to me. **This is the first paper to read if anyone gets library access**,
and it is the natural citation for #44 if its numbers hold up.

---

## 4. Is curvature the dominant error term, and over what span?

### 4.1 That ln k vs φ is curved is settled [verified]

From den Uijl et al. 2021 (J. Chromatogr. A), read in full: for their
high-precision Set Y "data from Set Y was best described by the log-log
adsorption model rather than the log-linear LSS model. This suggests that the
noise in Set X may obscure the non-linear trend and that scanning experiments are
best carried out under highly repeatable conditions." Their model comparison used
AIC across five models; with only three input gradients "the Neue-Kuss (NK) model
performed poorly" and the two-parameter models won — "The robustness of fit was
found to be better for both two-parameter models (LSS and ADS) than for the
three-parameter models (QM, MM and NK)".

From den Uijl et al. 2021 (J. Sep. Sci. review), quoted verbatim and confirmed
against the PMC text: LSS "cannot account for the non-linearity, making it only
applicable to the narrow linear range"; "nonlinear models describe the data
best"; and the practical instruction for LSS users, "if an LSS model is used it
is better to omit data for ln k < 0". The review also sets the accuracy bar this
project is judged against: retention models for method development "require
predictions (well) within 1%" because "small variations in retention times may
result in large variations in resolution".

From Guillarme et al. 2022 [verified]: "retention models can be considered linear
only within a limited retention window"; and, for the extreme case, "protein
species… are known to be suitably retained only within a very narrow composition
range", with the striking datum that "the transition range between a fully
adsorbed and desorbed state of proteins at the surface of the column corresponds
to a %ΔC of only 3.5% for an intact mAb of 150 kDa".

From Baeza-Baeza et al. 2013 [verified, abstract]: linearity "only acceptable in
relatively small concentration ranges of modifier".

### 4.2 Over what span does it become material? — not established here [could not verify]

**I could not verify a number.** A search engine surfaced the claim that the
log-linear relationship is accurate to within 1–2% only over Δφ ≈ 0.20–0.25,
attributed to Peiró-Vila et al. 2024; ScienceDirect returned 403 to every route
and I could not open the article to confirm it, so **that figure is not used
anywhere in this document's recommendations** and is recorded in §9 as
unverified. Anyone with access should check it: it is the right shape of number
and, if confirmed, it is the single most useful constant for #44.

**What can be said without it [derived].** Two bounds bracket the answer from
opposite directions:

- **Upper bound on what is safe**: the calibrated window itself, ~9 %B for a
  typical small molecule at β = 3 (§2). Inside it there is no curvature question,
  because the line was fitted through both ends.
- **Lower bound on what is dangerous**: this repository's own held-out evidence
  (§7.2 below) shows 2.3 %B of composition extrapolation producing no detectable
  penalty at all — 0.26% |Δt_R|, better than the in-window run.

So the material span lies somewhere above ~2 %B and the honest position is that
the literature bounds it qualitatively ("narrow", "limited", "relatively small")
while this project can bound it empirically on its own column.

### 4.3 Correction to `gradient-elution-math.md` §7.5 and §10 item 10 [verified]

The research doc flagged its Neue–Kuss row as a reconstruction of a mangled
extraction — "**Do not implement from this table; go to the source**" (§10 item
10). I went to the source. den Uijl et al. 2021 **Eq. 5**, extracted cleanly:

> ln k = ln k₀ + 2 ln(1 + S₂,NK·φ) − (φ·S₁,NK) / (1 + S₂,NK·φ)

The research doc's guess was:

> ln k = ln k₀ + 2 ln(1 + S₁φ) − S₂φ / (1 + S₁φ)

**The grouping was right; the subscripts are swapped.** The parameter inside the
logarithm is the same one that appears in the denominator — the doc got that
structural point correct — but den Uijl call it S₂,NK, not S₁. §10 item 10 can be
downgraded from "do not implement" to "structure verified, relabel the
parameters". The other four models in that table check out verbatim against
den Uijl Eqs. 1–4: LSS `ln k = ln k₀ − S_LSS·φ`, adsorption
`ln k = ln k₁ − R ln φ`, quadratic `ln k = ln k₀ + S₁,Q·φ + S₂,Q·φ²`, mixed-mode
`ln k = ln k₀ + S₁,M·φ + S₂,M·ln φ`.

**Convention note [verified]:** den Uijl's Eq. 1 is written with **ln**, and
their `ln k₀` is "the isocratic retention factor of a solute in pure water" —
so their `S_LSS` is this repository's **S_e** and their `k₀` is this repository's
**k_w**. Their model zoo is natural-log throughout, which is convenient: the
table can be lifted into hplcsim's internal convention without conversion.

---

## 5. Does anyone recommend a φ-window guard?

Three partial answers; no one states the clean rule the ticket hoped for.

### 5.1 Snyder's 15–20% in %B — the φ half of the β = 3 sentence [verified]

`gradient-elution-math.md` §7.1 quotes Molnár 2002 for the β = 3 recommendation.
I read the surrounding paragraph in the publisher PDF. The full sentence is:

> "A critical question, was raised by chemometricians: how far could
> chromatographic parameters in HPLC influence each other? Snyder and colleagues
> could show however that multiple variables may be treated independently, if the
> range of variation is kept sufficiently narrow. This meant **15–20% change in
> %B**, a factor of three in gradient elution time, 20–30 °C difference in
> temperature studies and 0.5–0.6 pH units of eluent A, between runs in the
> investigation of pH effects."

The same sentence gives a composition number: 15–20 %B, i.e. Δφ ≈ 0.15–0.20.
(A sentence here claiming the project "stopped there" at the factor-of-three clause
was struck 2026-09-03 under #54, on #48's finding: `gradient-elution-math.md` §7.1
has quoted the sentence in full since its first commit; what §7.1 lacked, and #48
added there, is the caveat that follows here.)

**But it does not mean what one wants it to mean [derived], and this is the
honesty point of the section.** The claim is about *experimental design* — the
span over which two variables may be varied while still being treated as
independent in a factorial model — not about how far a fitted line may be
extrapolated beyond its calibration. It is the φ analogue of "how far apart to
put your two runs", not of "how far outside the bracket you may predict". Read
correctly it is still useful: it says the Snyder school considered ~15–20 %B the
outer limit of a composition interval over which one-parameter-per-variable
linearity is trustworthy — which is the same order as the 9 %B window a β = 3
pair actually produces, and roughly twice it. Molnár cites Dolan, Lommen & Snyder,
J. Chromatogr. **535** for it; I did not read those papers [could not verify].

### 5.2 Guillarme's log k_i > 2.1 — a real, per-peak, sourced φ_0 ceiling [verified]

Guillarme et al. impose a constraint this repository already knows about but has
not connected to composition: two-run LSS parameter extraction is only reliable
when the retention factor at the *initial* composition is large enough, with a
cut-off of log k_i > 2.1 "allowing to obtain a reasonable error (λ < 0.5)".
Their §4 shows λ rising sharply as log k_i falls, "λ values can be as high as 6.5"
for biomolecules, and concludes "it is clear that the initial solvent strength for
preliminary gradients must be low enough".

**Why this is a φ_0 guard [derived].** log₁₀ k_0 = log₁₀ k_w − S·φ_0. Raising the
starting composition by Δφ_0 lowers log₁₀ k_0 by S·Δφ_0 — at S ≈ 5, every +10 %B
of starting composition costs 0.5 in log₁₀ k_0. So the cut-off converts directly
into a **per-peak ceiling on φ_0**, and on this repository's lab dataset
[derived, from the S and k_w of §2.2]:

| peak | S (base-10) | log₁₀ k_w | log₁₀ k_0 at 5 %B | φ_0 where log₁₀ k_0 = 2.1 |
|---|---|---|---|---|
| 1 | 5.12 | 3.03 | 2.78 | 0.182 (18.2 %B) |
| 2 | 5.00 | 3.50 | 3.25 | 0.280 (28.0 %B) |
| 3 | 5.18 | 5.02 | 4.76 | 0.563 (56.3 %B) |

**Peak 1 falls below Guillarme's floor once the candidate starts above ~18 %B.**
That is a hard, sourced, computable, per-peak limit on v0.2's φ_0 freedom, and it
is available today from parameters the engine already fits.

### 5.3 Neue & Kuss: change the model instead of guarding the window [verified, abstract]

Neue & Kuss 2010's own abstract claims their empirical nonlinear equation makes
"precise interpolation between experimental data points and **reasonable
extrapolation outside the directly measured data range**" possible, and — the
detail that matters most here — that it allows "the simultaneous exploration of
temperature, **gradient starting composition** and gradient slopes." **The model
whose stated purpose includes varying the gradient starting composition is
Neue–Kuss, not LSS.** Against that, den Uijl's measurement is that NK needs many
input gradients to behave: it fits well on eight gradients but "results in a poor
description when the input data is limited to three gradient durations", and its
robustness of fit is worse than the two-parameter models'. Rutan/Cash/Stoll's
2023 re-parameterisation exists precisely because NK is hard to fit; with it they
report 1.6% isocratic prediction from gradient data, under the composition-window
proviso of §3.3.

**Read together [derived]: a two-run workflow cannot have NK, and a workflow that
wants real φ freedom eventually needs more than two runs.** That is a roadmap
fact, not a v0.2 blocker — SPEC §11 already puts ≥2-run regression at v0.4.

---

## 6. How badly does S itself degrade from a narrow window?

`gradient-elution-math.md` §7.2 derives δS_e/S_e ~ δ/(φ_{e,1} − φ_{e,2})·S_e and
calls Δφ_e "the conditioning number of the whole fit", noting that Quarry, Grob &
Snyder 1986 owns the rigorous analysis and could not be obtained. **That is still
true — ACS returned 403 again** [could not verify]. What §1 adds is that the
conditioning number now has a closed form: substituting Δφ_e = ln β/S_e,

$$\frac{\delta S_e}{S_e} \;\sim\; \frac{\delta\,S_e^{\,2}}{\ln\beta}$$

[derived] — the fractional error in S_e grows with the **square** of S_e at fixed
β and timing noise δ. High-S compounds are doubly penalised: their window is
narrower (∝ 1/S_e) *and* the same φ error is a larger fraction of a steeper
line. This is consistent with, and explains, Guillarme's observation that their
two-run method is "more readily applicable to proteins and riskier with small
molecules" — for proteins the on/off mechanism means k_i is enormous and the
large-k_i approximation is excellent, which is a different effect that happens to
run the other way.

The strongest *published* statement of the conditioning hazard remains
Rutan/Cash/Stoll's 160% error on k_w versus 6.2% on k_ref (§3.3): the same data,
the same model, differing only in whether the reported parameter sits inside or
outside the sampled composition range [verified, abstract].

---

## 7. Is the two-run gradient window narrower than practitioners assume?

**Yes, and this is the ticket's sharpest finding [derived].**

### 7.1 The gap between the sweep and the calibration

Both scouting runs sweep the entire 5→95 %B range. A chromatographer looking at
those two chromatograms has every reason to believe the model has been shown the
whole composition range — the gradient visibly went there, twice. What was
actually pinned, per peak, is a ~9 %B interval (§2.2), because **each peak elutes
at exactly one composition per run, so two runs give two points on its line.**
Two points, ln β/S_e apart. The 90 %B ramp is the vehicle, not the calibration.

The three windows on this project's own sample do not even overlap, so there is
no method-level composition range to report — only three narrow, disjoint,
per-peak ones.

### 7.2 What the elution composition actually depends on

From Guillarme Eq. 8 in this repository's convention [derived]:

$$\varphi_e \;=\; \frac{\ln k_w + \ln S_e + \ln s^*}{S_e}, \qquad s^* = \frac{t_0\,\Delta\varphi}{t_G}$$

**The candidate gradient enters only through s\*.** Not through φ_0 and φ_f
separately — only through their difference, and only in the combination
t_0Δφ/t_G. Two consequences that reshape the #44 design:

1. **A candidate's prediction is inside the calibrated φ window if and only if
   its s\* is inside the scouting s\* bracket [s\*₂, s\*₁].** The composition
   question and the steepness question are *the same question*, asked in
   different units.
2. **Raising φ_0 with s\* held fixed does not extrapolate the fit in composition
   at all** — the band still elutes at the same φ_e. What raising φ_0 does is
   collapse k_i (§5.2) and push peaks toward the dwell/hold and post-gradient
   branches. That is a *regime* hazard, not an extrapolation hazard, and it needs
   a different diagnostic.

**Held-out verification on this repository's data [derived].** Fitting S_e and
k_w from runs 1–2 only (the boxed law plus Eq. 8), then predicting φ_e for the
held-out runs 3 and 4 and comparing against the measured φ_e computed from their
own retention times:

| run | peak | φ_e predicted | φ_e measured | difference |
|---|---|---|---|---|
| 3 (t_G 25) | 1 / 2 / 3 | 0.4757 / 0.5789 / 0.8545 | 0.4730 / 0.5763 / 0.8535 | +0.003 / +0.003 / +0.001 |
| 4 (t_G 60) | 1 / 2 / 3 | 0.4015 / 0.5029 / 0.7810 | 0.4032 / 0.5042 / 0.7818 | −0.002 / −0.001 / −0.001 |

The large-k_i approximation reproduces held-out elution compositions to ≤0.003 φ
units on this column. Good enough to build a diagnostic on.

### 7.3 The distance-outside formula, and a number that is peak-independent

For a candidate whose s* falls outside the bracket, the φ distance beyond the
edge of a given peak's window is [derived]:

$$\varphi_{\text{out}} \;=\; \frac{1}{S_e}\,\ln\!\frac{s^*_{\text{edge}}}{s^*_{\text{cand}}}$$

and dividing by that peak's window width ln β/S_e, **S_e cancels**:

$$\frac{\varphi_{\text{out}}}{\Delta\varphi_e} \;=\; \log_\beta\!\frac{s^*_{\text{edge}}}{s^*_{\text{cand}}}$$

So "how far outside, in window-widths" is a **single method-level number,
identical for every peak**, while "how far outside, in φ units" is **per-peak**
(it carries the 1/S_e). Both are computable from quantities the engine already
has, with no extra fitting. This is the cleanest possible answer to #44's
"per-peak or per-method" question: *both, and they are different facts.*

Verified against the lab data [derived]: run 4 has s* = 0.0090 against a bracket
edge of 0.0120, giving log₃(0.0120/0.0090) = 0.26 window-widths — and the direct
per-peak calculation gives 0.0244 / 0.0250 / 0.0241 φ units against window widths
of 0.0932 / 0.0954 / 0.0921, i.e. 0.262 / 0.262 / 0.262. Identical, as the
algebra requires.

**And the calibration point this repository already owns [derived]:** run 4 sits
0.26 window-widths (≈2.4 %B) outside every peak's calibrated composition window,
and SPEC §10 records that it was predicted to **0.26% average |Δt_R|** — *better*
than run 3 (0.35%), which is inside every window. At this distance the
composition-extrapolation penalty is not merely small, it is below the run-to-run
noise of the measurement. That is the empirical anchor for setting a gentle tier,
and it is consistent with SPEC §6 diagnostic 1's existing instinct that the
near-bracket flag should stay gentle.

---

## 8. Corrections and additions to existing repository documents

All [verified] against the sources named.

1. **`gradient-elution-math.md` §7.2** — the table of Δφ_e against β has the
   closed form ln β/S_e (§1), published as Guillarme Eq. 16. Worth stating, since
   it converts a simulated table into a law and makes the β-dependence obvious.
2. **`gradient-elution-math.md` §7.3** — the section says a β = 3 pair gives a
   window "typically well under 20% B". The law makes that precise: ln 3/S_e,
   which is 9–16 %B across the plausible small-molecule S range and ~9.4 %B on
   this project's own data. The estimate was right and can now be exact.
3. **`gradient-elution-math.md` §7.5 / §10 item 10** — Neue–Kuss Eq. 5 verified;
   grouping correct, subscripts swapped (§4.3). Downgrade from "do not implement".
4. **`gradient-elution-math.md` §7.1** — the Molnár/Snyder sentence quoted for
   β = 3 also contains "15–20% change in %B" (§5.1). Worth quoting in full, with
   the caveat that it is a design rule, not an extrapolation licence.
5. **Symbol collision worth a line in §1's symbol table [verified].** Guillarme
   et al. — this project's most-cited source — write `k_0` for k at φ = 0 (this
   repo's **k_w**) and `k_i` for k at the initial gradient composition (this
   repo's **k_0**). Their `k_0` is this repo's `k_w`. Anyone implementing from
   Guillarme Eqs. 8–10 while reading this repo's symbol table will silently swap
   two parameters. This belongs next to the log-base trap in §0.
6. **`github-hplc-simulators.md` §3** — den Uijl's extrapolation findings are
   about slope only, at a fixed 5→95 / 5→85 %B span (§3.1). The section does not
   claim otherwise, but a reader could easily assume the study covered
   composition; one clause would close that.

---

## 9. What I could NOT verify

1. **The Δφ ≈ 0.20–0.25 linear-range figure.** A search engine attributed to
   Peiró-Vila, Torres-Lapasió & García-Alvarez-Coque 2024 ("Global retention
   models in reversed-phase liquid chromatography. A tutorial", *J. Chromatogr.
   Open* 8, 100192, gold OA CC BY-NC) the claim that the log-linear relationship
   is accurate to 1–2% only over Δφ = 0.20–0.25. ScienceDirect returned 403 to
   the article page, the `/pdfft` endpoint, WebFetch and curl; DOAJ's article page
   also 403'd and its API carries only the abstract, which does not contain the
   claim. **Not used in any recommendation.** This is the highest-value item on
   this list: it is exactly the constant §4.2 lacks.
2. **David & Moldoveanu 2024**, "Retention factor variation on wide range of
   mobile phase compositions in RP-HPLC; a short tutorial" (*J. Chromatogr. Open*
   8, 100176, gold OA CC BY-NC). Title is squarely on topic; same 403 wall. Only
   the DOAJ abstract was readable, and it is generic.
3. **Baeza-Baeza et al. 2013 full text.** The abstract (§3.4) is the single best
   match to this ticket's question in the literature I found. Its green-OA copy
   in RODERIC (University of Valencia) is behind an Anubis anti-bot challenge that
   returns an HTML interstitial to both curl and WebFetch. **The φ_0 range they
   tested and the LSS-vs-quadratic error split are therefore unknown to me.**
   First thing to read with library access.
4. **Quarry, Grob & Snyder 1986** (*Anal. Chem.* 58, 907–917) — still not
   obtained; ACS 403, as in ticket #2. The rigorous two-run error analysis remains
   unread, so §6's conditioning algebra is still this project's own derivation.
5. **Dolan, Lommen & Snyder, J. Chromatogr. 535** — Molnár's refs [44,45] for the
   15–20 %B rule. Not retrieved, so §5.1's caveat about what the rule *means* is
   my reading of Molnár's paraphrase, not of Snyder's own statement.
6. **Neue & Kuss 2010 full text** — abstract only. Their "reasonable
   extrapolation outside the directly measured data range" is an authors' claim I
   could not see evidence for; no magnitude is attached to "reasonable".
7. **Rutan/Cash/Stoll 2023 full text** — abstract only. In particular I could not
   see *how* they quantified "consistent with", which is the number #44 would
   most like to have.
8. **Nikitas & Pappa-Louisi 2009** — abstract only; ScienceDirect 403. It is a
   review of one- and multi-variable retention models with "special attention…
   devoted to the fitting performance of the various models and its impact on the
   final predicted error", which is likely to contain per-model error figures over
   composition ranges. Not readable here.
9. **Poole & Atapattu 2022** — the repository's source for S ranges. Closed
   access per Unpaywall and not indexed in PubMed under any query I tried, so I
   could not check whether it states a linear-range span. §2.1's cross-check
   relies on the S ranges as already quoted in `gradient-elution-math.md` §1.2.
10. **The direct experiment does not exist, as far as I can find.** No paper
    varies the calibration φ window and reports error against distance from it.
    §7's conclusions are algebra plus this project's own held-out data, not a
    literature measurement. If that algebra is wrong, the recommendations below
    are wrong — which is why §10 leads with a bench run that tests it.
11. **My §2.2 / §5.2 / §7 arithmetic uses the large-k_i approximation** and
    S_e values derived from it, not the engine's exact Brent solve. §7.2 shows it
    reproduces held-out φ_e to ≤0.003 φ units on this dataset, but the S and
    log₁₀ k_w in §2.2 and §5.2 are approximate — expect small differences against
    what `fit.py` reports. The 18.2 %B ceiling for peak 1 in particular should be
    recomputed from the engine's own fit before it is put in front of a user.
12. **Nothing was executed from any third-party project.** The only code run was
    my own arithmetic on `validation/` data, shown in full above.

---

## 10. Consequence for hplcsim [derived]

### 10.1 For issue #44 — what a prediction may claim outside the fitted window

**a. Generalise SPEC §6 diagnostic 1 from t_G to s\*; do not add a second,
parallel φ diagnostic.** §7.2 shows the composition question and the steepness
question are one question. The bracket variable should become the normalised
slope s* = t_0·Δφ/t_G (equivalently b_e, which the engine already computes),
compared against [s*₂, s*₁] from the scouting pair. **In v0.1, where Δφ is fixed
and only t_G varies, this reduces exactly to today's t_G bracket** — so the
change is backward-compatible and can land before any φ freedom ships. Without it,
v0.2 has a live trap: a candidate at 15→55 %B with t_G = 25 min sits comfortably
*inside* [15, 45] on the t_G axis while being 0.20 window-widths *outside* the
calibration in s* (§10.3, run B). A t_G-only diagnostic calls that safe.

> **Amendment to (a), 2026-09-03 under #54** (from #52's research, §1.4 and §8
> item 2). The first half of (a) stands: the bracket variable is s\*. The second
> half — "do **not** add a second, parallel φ diagnostic" — is withdrawn. This
> repository's own bench data are the counter-example: `run3.csv` and `run5.csv`
> are s\*-matched to 0.1 % (0.02160 vs 0.02162), the engine puts every peak at the
> same φ_e on both to 0.1 %B, and the mean residual still doubles (+0.355 % →
> +0.729 %). Every s\*-mediated mechanism predicts those two residuals agree; they
> differ by 0.046 min. **s\* is necessary, not sufficient.** φ₀ needs a term of
> its own beside the s\* bracket — #44's diagnostic 7, φ₀ departure — and (d)'s
> per-peak k_i floor is a different hazard, not a substitute for it.

**b. Report both numbers, because they answer different questions.**
- *Per-method, one number*: overshoot in window-widths, `log_β(s*_edge/s*_cand)`
  — identical for every peak (§7.3). This drives the escalation tier and belongs
  on the candidate controls next to the existing t_G flag.
- *Per-peak, in φ units*: the peak's calibrated window [φ_e,run2, φ_e,run1], its
  width ln β/S_e, and where the candidate's φ_e falls relative to it. This is
  what tells a chromatographer *which peak to distrust*, and it must be per-peak
  because §2.2 shows the windows are narrow, disjoint, and have no meaningful
  union. Natural home: the fit-parameters tab, which SPEC §7 already promotes to
  its own tab, one row per peak alongside log₁₀ k₀ and S.

**c. Gentle vs strong, and what sets "far".** Express the tiers in
window-widths, which makes them β-aware — the current t_G rule is not. Evidence
for the thresholds:
- At **0.26 window-widths** outside, this project measured **0.26% |Δt_R|** on
  held-out run 4 — better than the in-window run 3 (0.35%). No penalty is
  detectable. Gentle.
- At **1.0 window-widths** outside, the prediction composition is a full Δφ_e
  beyond the last pinned point — as far outside as the two scouting runs are
  apart. That is a principled place for the strong tier, and it is easy to
  explain to a user in exactly those words.
- Guillarme's extrapolation result (§3.2) is the warning behind the strong tier:
  crossing outside the bracket moved most peptides from λ < 0.5 to λ > 0.5, with
  worst cases at λ > 2.

Recommendation: **gentle flag from 0 to ~0.6 window-widths, strong beyond.**
The 0.6 preserves the current SPEC §6 wording's severity — "beyond ~2× outside"
maps to log₃(2) = 0.63 window-widths at β = 3 — while re-expressing it in a
variable that survives φ freedom. Keeping continuity with the shipped threshold
is worth more than the marginally cleaner 1.0.

**d. Add a separate φ_0 regime check, because §7.2 shows raising φ_0 is a
different hazard.** Raising the starting composition does *not* move the
prediction out of the calibrated window; it collapses k_i. Use Guillarme's
sourced floor: flag any peak whose log₁₀ k₀ at the *candidate's* φ_0 falls below
**2.1** (§5.2). On this project's own sample that fires for peak 1 once the
candidate starts above ~18 %B — a real limit a user will hit immediately. This
is per-peak, it is cheap, and it reuses a constant already in the research doc.
It also composes naturally with SPEC §6 diagnostic 2 (the early-eluter badge),
which is the same physics arriving from the other side.

**e. What a prediction may claim.** Inside the window: the existing confidence.
Outside it, up to the gentle tier: unchanged numbers, an annotation naming the
distance in %B for the affected peaks. Beyond the strong tier: keep predicting —
CLAUDE.md's warnings-over-blocks rule holds, and den Uijl's own conclusion is
that extrapolation degrades gracefully rather than catastrophically — but say
plainly that the peak's LSS line was never pinned there, and stop treating the
resolution numbers as decision-grade. **Do not claim curvature-corrected
accuracy anywhere**: this project fits two parameters and cannot see curvature
at all (§5.3).

### 10.2 The honest caveat on all of the above

§7's equivalence is derived from LSS with the large-k_i approximation. It says
where the *model* is being evaluated relative to its calibration. It cannot see
**model-form error**: real ln k vs φ is curved (§4.1), and a candidate whose
whole migration path lies in a composition region far from the calibrated window
carries an error that s* does not measure. The φ-unit per-peak readout of (b) is
what surfaces that, which is the reason to show it even though the tier comes
from the method-level number.

### 10.3 For issue #46 — the acceptance bar and what new bench runs to make

**The problem, stated precisely.** `run3.csv` and `run4.csv` both use 5→95 %B —
the same span as the scouting pair — so they vary s* only through t_G, and
neither tests a changed composition range. But §7.2 sharpens the problem: simply
running *some* different %B range would not test composition extrapolation
either, because φ_e depends on Δφ and t_G only through s*. **The bench runs have
to be chosen against the algebra, or they will confirm nothing.** Three runs,
each targeting a distinct claim, all on the existing sample and column:

| run | gradient | t_G | s\* | what it tests | prediction to beat |
|---|---|---|---|---|---|
| **A** | 15→95 %B | 22.2 min | 0.0216 — matched to run 3, inside bracket | **the s\*-invariance claim of §7.2**: a changed φ range at matched s* should predict as well as run 3 did | avg \|Δt_R\| ≤ 2%, worst ≤ 5% (SPEC §10's bar); ideally ≈ run 3's 0.35% |
| **B** | 15→55 %B | 25 min | 0.0096 — **outside** the bracket while t_G is **inside** [15, 45] | **the trap case for #44(a)**: today's t_G-only diagnostic calls this safe; the s\* bracket calls it 0.20 window-widths out | error should resemble run 4's (0.26%), *not* run 3's — and the new diagnostic must flag it |
| **C** | 25→95 %B | 25 min | 0.0168 — inside bracket | **the φ_0 regime hazard of §10.1(d)**: peak 1's log₁₀ k₀ falls to ≈1.75, below Guillarme's 2.1 floor | peak 1 degrades while peaks 2–3 hold; the k_i flag fires on peak 1 only |

Run A is the flagship: it is the cheapest run that can *falsify* the central
claim of this document. If A predicts poorly while its s* says it should not,
§7.2 is wrong and #44's design must change. **Run A before B and C.**

> **As run** (recorded 2026-09-03 under #54; the numbers are #52's, §1.3–1.4).
> All three were made on 2026-09-02 as campaign #27's φ-range arm.
> **Run A is `run5.csv`** (15→95 %B, t_G 22.2, s\* 0.02162 against run 3's
> 0.02160) and the s\*-invariance claim **failed**: mean residual +0.729 %
> against run 3's +0.355 % — inside SPEC §10's 2 % bar, but twice the in-window
> residual that a matched s\* said it should reproduce, with the same predicted
> φ_e per peak to 0.1 %B. §10.1(a) is amended above as a consequence.
> **Run B is `run6.csv`** (15→55 %B, t_G 25, then held 19.5 min at 55 %B):
> Unknown-3 eluted in the 95 %B wash at 46.8 min against a pre-registered 47.0
> (#46) — the post-gradient regime the first caution below anticipated, and the
> evidence behind the wash-eluted badge that #58 decided for the v0.2 SPEC
> amendment (#47, not yet in `SPEC.md`). **Run C is `run7.csv`**
> (25→95 %B, t_G 25): mean +1.519 %, peak 1 worst at +2.496 % with log₁₀ k₀ = 1.74,
> below the 2.1 floor as predicted — but peaks 2–3 did *not* hold (+1.606 /
> +0.456 % against run 3's +0.425 / +0.105 %), so the k_i floor accounts for only
> part of run C; the rest is the φ₀ term. That the residual roughly doubles per
> 10 %B of φ₀ across runs 3 / A / C is #52's observation on this instrument, not
> a law.

Three cautions on the design [derived]:

- **Check φ_e < φ_f before committing a run.** Peak 3 elutes near φ_e ≈ 0.85, so
  any candidate with φ_f below ~0.90 pushes it into the post-gradient branch and
  confounds the composition test with a regime change. This is why run A ends at
  95 %B and not 75 %B, and why run B deliberately does not (it is *expected* to
  put peak 3 post-gradient — worth recording, but read runs A and C for the
  composition result).
- **φ_0 = 15 %B is about the ceiling for this sample**, not a free choice: peak 1
  crosses the log k_i = 2.1 floor at 18.2 %B (§5.2). Run C exceeds it on purpose.
- **The sample is still the binding constraint.** SPEC §10 already records that
  this mixture's pairs sit at Rs 30–116, so no φ-range run can test the Rs ± 0.3
  bar. Runs A–C can test retention and the diagnostics; they cannot close the
  resolution question, and #46 should not claim they do.

**What the acceptance bar should assert [derived].** Add to the three-layer bar,
as a fourth reality check: (i) run A within SPEC §10's existing held-out
tolerances, which validates φ freedom inside the s* bracket; (ii) the s* bracket
diagnostic fires on run B and not on run A — a test of the *diagnostic*, which is
the thing #44 ships; (iii) the k_i floor flags peak 1 and only peak 1 on run C;
and (iv) a pure-algebra unit test, needing no bench data at all, that
Δφ_e = ln β/S_e to 1e-12 against the engine's fitted φ_e values, and that the
same quantity computed as log₁₀β/S agrees — **which is exactly the assertion that
catches the log-convention slip §1 warns about.** (iv) costs nothing and should
land regardless of whether the bench runs happen.

---

## References

All accessed 2026-09-02.

1. **Guillarme, D.; Bouvarel, T.; Rouvière, F.; Heinisch, S.** "A simple
   mathematical treatment for predicting linear solvent strength behavior in
   gradient elution: Application to biomolecules." *J. Sep. Sci.* **45** (2022)
   3276–3285. [doi:10.1002/jssc.202200161](https://doi.org/10.1002/jssc.202200161);
   full text [PMC9543774](https://pmc.ncbi.nlm.nih.gov/articles/PMC9543774/) —
   **the load-bearing source of this document**: Eqs. 2–3 (base-10 LSS), 6 (s*),
   7–8 (large-k_i elution composition), 16 (ΔC_e), Figure 3 (measured ΔC_e by
   compound class), the log k_i > 2.1 cut-off, the λ metric, and the
   interpolation-vs-extrapolation results of Figures 4–5. Read in full.
2. **den Uijl, M. J.; Schoenmakers, P. J.; Schulte, G. K.; Stoll, D. R.;
   van Bommel, M. R.; Pirok, B. W. J.** "Measuring and using scanning-gradient
   data for use in method optimization for liquid chromatography."
   *J. Chromatogr. A* **1636** (2021) 461780.
   [doi:10.1016/j.chroma.2020.461780](https://doi.org/10.1016/j.chroma.2020.461780);
   PDF <https://pure.uva.nl/ws/files/54095340/2021_Den_Uijl_PROMISE.pdf> —
   Eqs. 1–5 (the five retention models, natural-log), Eq. 10 (slope factor
   including Δφ), §2.3 (both sets span the full %B range), §3.3 (extrapolation),
   concluding remarks. Read in full.
3. **den Uijl, M. J.; Schoenmakers, P. J.; Pirok, B. W. J.; van Bommel, M. R.**
   "Recent applications of retention modelling in liquid chromatography."
   *J. Sep. Sci.* **44** (2021) 88–114.
   [doi:10.1002/jssc.202000905](https://doi.org/10.1002/jssc.202000905);
   [PMC7821232](https://pmc.ncbi.nlm.nih.gov/articles/PMC7821232/) — LSS "only
   applicable to the narrow linear range"; "nonlinear models describe the data
   best"; "omit data for ln k < 0"; the "(well) within 1%" accuracy bar;
   parameter counts per model.
4. **Molnár, I.** "Computerized design of separation strategies by reversed-phase
   liquid chromatography: development of DryLab software." *J. Chromatogr. A*
   **965** (2002) 175–194.
   [doi:10.1016/S0021-9673(02)00731-8](https://doi.org/10.1016/S0021-9673(02)00731-8);
   [publisher PDF](https://molnar-institute.com/fileadmin/user_upload/Literature/_2002_Molnar_Compu.pdf) —
   §8's Snyder sentence in full ("15–20% change in %B, a factor of three in
   gradient elution time…"), citing Dolan, Lommen & Snyder, *J. Chromatogr.* 535;
   §18 on gradient→isocratic %B prediction "with an accuracy of about 1%"; and
   the observation that optimising the initial %B is a *follow-up* step after
   t_G/T optimisation, worth 0–20% further Rs.
5. **Rutan, S. C.; Cash, K.; Stoll, D. R.** "Experimental design and
   re-parameterization of the Neue-Kuss model for accurate and precise prediction
   of isocratic retention factors from gradient measurements in reversed phase
   liquid chromatography." *J. Chromatogr. A* **1711** (2023) 464443.
   [doi:10.1016/j.chroma.2023.464443](https://doi.org/10.1016/j.chroma.2023.464443);
   abstract via PubMed [PMID 37890376](https://pubmed.ncbi.nlm.nih.gov/37890376/) —
   the composition-window proviso; k_w 160% vs k_ref 6.2%; 6800% vs 0.51%.
   **Abstract only.**
6. **Neue, U. D.; Kuss, H.-J.** "Improved reversed-phase gradient retention
   modeling." *J. Chromatogr. A* **1217** (2010) 3794–3803.
   [doi:10.1016/j.chroma.2010.04.023](https://doi.org/10.1016/j.chroma.2010.04.023);
   abstract via PubMed [PMID 20444458](https://pubmed.ncbi.nlm.nih.gov/20444458/) —
   "reasonable extrapolation outside the directly measured data range"; explicit
   support for varying "gradient starting composition". **Abstract only.**
7. **Baeza-Baeza, J. J.; Ortiz-Bolsico, C.; Torres-Lapasió, J. R.;
   García-Álvarez-Coque, M. C.** "Approaches to model the retention and peak
   profile in linear gradient reversed-phase liquid chromatography."
   *J. Chromatogr. A* **1284** (2013) 28–35.
   [doi:10.1016/j.chroma.2013.01.076](https://doi.org/10.1016/j.chroma.2013.01.076);
   abstract via PubMed [PMID 23453677](https://pubmed.ncbi.nlm.nih.gov/23453677/);
   green OA copy at RODERIC (unreachable, §9) — linearity "only acceptable in
   relatively small concentration ranges of modifier"; quadratic model accurate
   to 1–2% "for a wide range of initial concentrations of organic modifier".
   **Abstract only — the closest match to this ticket in the literature.**
8. **Nikitas, P.; Pappa-Louisi, A.** "Retention models for isocratic and gradient
   elution in reversed-phase liquid chromatography." *J. Chromatogr. A* **1216**
   (2009) 1737–1755.
   [doi:10.1016/j.chroma.2008.09.051](https://doi.org/10.1016/j.chroma.2008.09.051);
   abstract via PubMed [PMID 18838140](https://pubmed.ncbi.nlm.nih.gov/18838140/).
   **Abstract only.**
9. **Peiró-Vila, P.; Torres-Lapasió, J. R.; García-Alvarez-Coque, M. C.**
   "Global retention models in reversed-phase liquid chromatography. A tutorial."
   *J. Chromatogr. Open* **6** (2024) 100192.
   [doi:10.1016/j.jcoa.2024.100192](https://doi.org/10.1016/j.jcoa.2024.100192).
   Gold OA (CC BY-NC) but **unreachable** (§9 item 1); abstract via the DOAJ API.
10. **David, V.; Moldoveanu, S. C.** "Retention factor variation on wide range of
    mobile phase compositions in reversed-phase high-performance liquid
    chromatography; a short tutorial." *J. Chromatogr. Open* **6** (2024) 100176.
    [doi:10.1016/j.jcoa.2024.100176](https://doi.org/10.1016/j.jcoa.2024.100176).
    Gold OA (CC BY-NC) but **unreachable** (§9 item 2).
11. **Quarry, M. A.; Grob, R. L.; Snyder, L. R.** "Prediction of precise isocratic
    retention data from two or more gradient elution runs. Analysis of some
    associated errors." *Anal. Chem.* **58** (1986) 907–917.
    [doi:10.1021/ac00295a056](https://doi.org/10.1021/ac00295a056).
    **Still not obtained** (§9 item 4).
12. This repository's own prior work: `docs/research/gradient-elution-math.md`
    (§0 log-base trap, §1 symbol table, §2.3 elution-composition identity, §7.1–7.3,
    §7.5, §7.7, §10), `docs/research/github-hplc-simulators.md` §3,
    `SPEC.md` §3/§4/§6/§10/§11, `src/hplcsim/fit.py` (`FitResult.delta_phi_e`),
    and `validation/method.csv`, `run1.csv`–`run4.csv`.

---

*Compiled 2026-09-02 for issue #43. Branch: `research/composition-extrapolation`.
Amended 2026-09-03 under #54: §10.1(a) and §10.3 with #52's corrections, §5.1 on
#48's finding.*
