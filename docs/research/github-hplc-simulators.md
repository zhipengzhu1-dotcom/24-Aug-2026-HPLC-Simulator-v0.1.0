# Open-source HPLC / gradient-elution simulators on GitHub and adjacent hosts

Research notes for the v0.2 resolution map and optimizer. Resolves issue #40
(parent: map issue #28). Audience: whoever designs the map's sweep, flip display,
extrapolation shading and validation fixtures.

Every claim is tagged **[verified]** (I opened the repository, file, page or
paper and the statement is what it says), **[derived]** (my own reading of the
code or my own recommendation), or **[could not verify]**. Section 8 lists
everything I could not verify. Nothing below is described from a search-result
snippet; every repository row comes from a downloaded tarball, `gh api`, the
GitLab API, PyPI's JSON API, or the page itself. I did not run any of the code.

Survey date: 2026-09-02. "Last activity" is the `pushed_at` date from the GitHub
API (or the equivalent host field) on that day.

---

## 0. Method and coverage

**Searches run [verified].** GitHub via `gh search repos` for: "hplc simulator",
"gradient elution", "linear solvent strength", "chromatography simulation",
"retention modeling chromatography", "chromatography optimization gradient",
"drylab hplc", "hplc method development", "chromatogram simulation retention",
"lss chromatography", plus the names HappyTools, ChromPy, ChromaPy, pyChrom,
"Chromatography Toolbox". GitLab via `/api/v4/projects?search=` for
"chromatography" and "hplc". PyPI via `/pypi/<name>/json` (the HTML search page
does not render without JavaScript). CRAN package pages for chromatographR and
RpeakChrom. SourceForge project page for hplcsimulator. Zenodo record 5710443
for MOREPEAKS. Web search for the Boswell/Stoll simulators, den Uijl / Pirok /
Schoenmakers tooling, and the Nikitas R package.

**What exists, in one paragraph [derived].** There are exactly two open-source
projects that fit two scouting gradients to LSS parameters and then draw
something map-like: **PyLSS** (Python, AGPL-3.0, actively maintained) and
**apex-res** (Python + React, MIT, abandoned 2023). One more, **AutoLC-BO**
(CC BY-NC-SA), has the best-written multi-segment LSS forward model I found
(explicit before / during / after-gradient cases, cumulative band-compression
integral) but optimises with Bayesian optimisation rather than a map. The
teaching simulators (Boswell/Carr/Stoll Java applet, its JS ports, the multidlc
4.2.0 web app) forward-predict from a built-in compound database and do not fit
or map. Everything else returned by the searches is chromatogram
*data-processing* (peak picking, integration) and is out of scope. **No project
anywhere in this survey draws a critical-resolution-versus-t_G map with
order-flip markers or an extrapolation bracket.** The open-source state of the
art is behind what `docs/research/gradient-elution-math.md` §7.4 / §8.3 already
specifies.

---

## 1. Project table

Only projects I opened. "Map" means a plot of some resolution-like quantity over
a swept condition. Column "flip" = how elution-order reversal is handled at each
swept condition.

| # | Project | URL | Lang | Licence | Last activity | Retention model / gradient / dwell / width | Resolution map | Optimizer |
|---|---|---|---|---|---|---|---|---|
| 1 | **PyLSS** (Randazzo) | https://github.com/gmrandazzo/PyLSS | Python 3.10–3.12, PyQt6 GUI | AGPL-3.0 | pushed 2026-05-01; created 2016-02-11; 12 stars | LSS base-10, `log10 k = log10 kw − Sφ`; closed-form `tR = (t0/b)·log10(2.3·k0·b + 1) + t0 + tD` with `b = t0·Δφ·S/tG`; **no dwell correction to k0** (tD added as a pure delay); logarithmic-gradient variant; Neue–Kuss written in a docstring but not implemented; width = `4·N^-1/2·G·t0·(1+ke)` with Poppe G, `N = L/(3.4·dp)`; two-run fit = Nelder–Mead on RMSD of predicted tR | Yes. 3-D grid: initial %B (20 pts, 0–30 %), final %B (20 pts, 50–100 %), tG (2–60 min, **step 2 min**) → lowest adjacent Rs per point (peaks re-sorted by tR), then `scipy.interpolate` onto a 500×500 contour in three projections (init %B vs steepness, vs final %B, vs tG). Critical-only; pairs below `crit_res=1.8` are returned with their original ids | Yes: grid + simplex maximising the **lowest selectivity α** (not Rs); isocratic optimum by simplex on 1/Rs; "automatic elution-window stretching" (even spacing) |
| 2 | **apex-res** (Smith) | https://github.com/joekitsmith/apex-res | Python FastAPI + React/TS | MIT (pyproject) — no LICENSE file | pushed 2023-10-31; created 2021-04-20; 0 stars; 1 open issue | LSS base-10 with the constant **2.3**; two-run fit: closed-form b seed from β = tG2/tG1, then `scipy.optimize.root` on residual tR; dwell handled via `(1 − tD/(t0·k0))` and a "small k0" branch (`t0·k0 ≤ tD` → isocratic `tR = t0(1+k0)`); predicted `tR < t0` clamped to t0; width via k* and a user N | Partial. Grid is **φ0 × φf** (101×101, φf−φ0 ≥ 0.15) at a *fixed* tG — not a tG sweep; "critical" is a `nanmax` over pairs involving one "peak of interest" (see §2); an unused `tricontourf` plotter exists | Argmax of that "critical" quantity over the φ0/φf grid |
| 3 | **HPLC Simulator** (Boswell / Carr / Stoll) Java applet | SourceForge https://sourceforge.net/projects/hplcsimulator/ ; forks https://github.com/joshuapouliot27/HPLC-Simulator , https://github.com/andychase/HPLC-Simulator | Java 1.6 | **Conflicting**: SourceForge page says GPLv3; hplcsimulator.org/development says CC BY-NC-SA 3.0 US; pouliot fork GPL-3.0; andychase fork no licence | SF last update 2013-08-05; pouliot fork 2017-03-26; andychase 2023-01-03 | `log10 k'w` and S each linear in T (°C); gradient retention by **time-stepping** (1000-step gradient array, per-compound loop advancing fractional migration `dt/(k'·t0)` until x ≥ 1, linear interpolation at the exit); dwell modelled as a **mixer** (mixing volume + non-mixing volume) rather than a delay; width from the k' at exit, isocratic σ (no G) | No | No |
| 4 | **mlibby/hplc_simulator** (JS port of #3) | https://github.com/mlibby/hplc_simulator (mirror gitlab.com/m_libby/hplc_simulator) | JavaScript/Angular | CC BY-NC-SA 3.0 US (README) | pushed 2018-05-16 | **Gradient mode not implemented**: `f.kPrime` returns `NaN` when `elutionMode === gradient`; isocratic only | No | No |
| 5 | **HPLC Simulator 4.2.0** (Lauer / Stoll / Carr, multidlc.org) | https://www.multidlc.org/hplcsim/4_2_0/ (source served as `simulator.js`) | JavaScript | **Not open source**: "Copyright © 2012-2026 Multi-Dimensional Separations - All Rights Reserved"; no licence file | v4.2.0 2022-08-18 (what's-new page) | **Natural-log** LSS: `ln kw` and `S` linear in T (K); closed form `tR = t0 + tD + (t0/b)·ln(b·(k0 − tD/t0) + 1)`, `b = S·Δφ·V0/(F·tG)`; φe from the gradient line, **clamped to φ_i** when `(tR−tD−t0) < 0 or > tG`; σ from ke, no G; compound DB of 22 compounds × {SB-C18, SB-C8} × {ACN, MeOH} | No map; single-condition "Critical Resolution" (v4.2.0): sort by tR, adjacent pairs, `Rs = (k2/(k2+1))·(|α−1|/α)·(√N2/4)`, minimum | No |
| 6 | **AutoLC-BO** (Boelrijk / Bos / Pirok) | https://github.com/Jimbo994/AutoLC-BO | Python (Jupyter) | CC BY-NC-SA 4.0 | pushed 2026-02-24; created 2022-12-09 | Natural-log LSS `k = k0·exp(−Sφ)`; **multi-segment** gradient, closed form per segment; explicit cases: elutes before gradient (`(tD+t_init)/(t0·k_init) ≥ 1`), during segment n, or in the final isocratic hold; width via cumulative G integral (and a separate Poppe G); `sort_peaks` before adjacent Rs | No | Bayesian optimisation of gradient profiles; CRFs: sigmoid-product, capped sum of adjacent Rs, Tyteca eq. 11, all after sorting |
| 7 | **MOREPEAKS** (formerly PIOTR; CAST, Amsterdam) | https://zenodo.org/records/5710443 | MATLAB runtime, Windows .exe | CC BY 4.0 on the Zenodo record | v1.0.1, 2021-11-10 | 1-D and 2-D LC optimisation; used in den Uijl 2021 to fit LSS/NK/quadratic/ADS/MM models and evaluate goodness of fit | Unknown — binary only | Yes (binary only) |
| 8 | **BAGO** | https://github.com/huaxuyu/bago ; PyPI `bago` 1.0.0 (2024-12-10) | Python | CC BY-NC 4.0 | pushed 2025-05-18 | No retention model: Bayesian optimisation directly on measured LC-MS runs | No | Yes (on measurements) |
| 9 | **HPLCMethodOptimisationGUI** (Bourne group) | https://github.com/Bourne-Group/HPLCMethodOptimisationGUI | MATLAB + ChemStation macros | MIT | pushed 2024-06-14 | No retention model: closed-loop BO on measured chromatograms; objective includes critical Rs of consecutive measured peaks | No | Yes (on measurements) |
| 10 | **nefuzcj/HPLC** | https://github.com/nefuzcj/HPLC | Python (single 1000+-line script, Excel I/O) | none | pushed 2023-09-21 | Natural-log (`k0 = exp(…)`) LSS plus a quadratic ("QSSM") and a Gaussian retention model; multi-segment gradient with dwell and injection delay; genetic-algorithm gradient optimiser | No | Yes (GA) |
| 11 | **Zisi / Pappa-Louisi / Nikitas R package** | paper only: J. Chromatogr. A 1617 (2020) 460823, https://doi.org/10.1016/j.chroma.2019.460823 | R | unknown | 2020 | Abstract: retention modelling, retention/chromatogram prediction, optimisation under isocratic and single/double gradients of φ and/or pH; "automatic" mode maximises resolution within a preset time; "manual" mode via scatter/contour plots | Yes per abstract (contour plots) | Yes per abstract |
| 12 | **chrom-rs** | https://gitlab.com/open-works/chromatography (mirror of github.com/biface/chromatography) | Rust | Apache-2.0 | 2026-08-28 | Langmuir-isotherm transport PDE (Euler/RK4); not an LSS / gradient tool | No | No |
| 13 | **GasChromatographyToolbox** | https://github.com/GasChromatographyToolbox/GasChromatographyToolbox | Julia | MIT | pushed 2024-06-29 | GC only: ODE migration model, retention-parameter estimator from temperature programmes | No | No |
| 14 | Data-processing only (out of scope) | hplc-py https://github.com/cremerlab/hplc-py (GPL-3.0, pushed 2026-06-26); MOCCA https://github.com/HaasCP/mocca (MIT, "Deprecated", 2024-09-05); chromatographR https://github.com/ethanbass/chromatographR (GPL-2.0, pushed 2026-09-01; removed from CRAN 2022-11-07); PeakUtils mirror https://github.com/lucashn/peakutils (MIT, 2022-08-05); Chromapy https://github.com/JBrinco/Chromapy (GPL-3.0, 2026-05-12); RpeakChrom (removed from CRAN 2026-04-30) | — | — | — | Peak detection / integration / alignment of measured chromatograms | No | No |
| 15 | **Practical HPLC Simulator** (Guillarme lab, Geneva) | https://farma-unites.unige.ch/en/guillarme-lab/tools/practical-hplc-simulator | Excel (macro and macro-free) | none stated | — | Empirical simulator "based on more than 3500 practical experiments" (37 molecules, 4 columns, 2 modifiers); outputs tR, k', w½, N, Rs; dwell volume is an input | No | No |

All rows [verified] from the sources named, except row 11 (abstract only) and
row 7 (Zenodo record + den Uijl 2021 §2.4), which are [verified] as far as they
go and [could not verify] for the binary's internals.

Repositories found by name but not opened in depth because their descriptions
show they are unrelated or trivial [verified from `gh search` metadata only]:
`62392/HPLC-Simulator` (instrument-operation training UI), `C10H/HPLC_Simulator`
(isotherm models, README in Chinese), `benehas/Chromatography_Simulation_Python`
(finite-difference solver), `turboseb/chromatography` (GDScript, "early
development"), and a dozen empty or AI-generated "method development" repos
created in 2025–2026. The GitHub topic `drylab` has no public repositories.
PyPI's `pylss` is an unrelated `ls` clone, not PyLSS.

---

## 2. Order flips / co-elution across a t_G sweep

The map's §7.4 requirement — re-sort at every grid point, track pair identity,
show where pairs cross — has **no open-source precedent**. What each project
actually does:

**PyLSS** [verified, `src/pylss/gradientutils.py` `get_lss_gradient_critical_rs`]:
at every grid point it builds `[tR, W, id]` per peak, sorts by tR, computes
adjacent-pair Rs, records the minimum as `lowestrs`, and appends
`[id_{i-1}, id_i, rs]` for every pair below `crit_res` (1.8 for the map). So
the *identity* of the critical couple survives — but `getResMapPlot` only keeps
`lowestrs` per condition and the GUI interpolates that scalar onto a 500×500
grid (`gui/plotmaps.py`). No pair trajectories, no crossing markers. Because tG
is stepped in 2-min increments and then smoothed by interpolation, a crossing
trough narrower than ~2 min is invisible on the plotted map [derived].

**apex-res** [verified, `optimisers/two_gradient/resolution.py`]: does **not**
sort. It enumerates all `itertools.combinations` of peaks, computes
`sqrt((2(tR2−tR1)/(w1+w2))²)` — i.e. |Rs| — so a flip is invisible, and its
"critical resolution" is `np.nanmax` over the pairs that involve one
user-chosen "peak of interest" (with a `# TODO: not sure what this did`
comment next to it). This is neither a critical pair nor a minimum; treat the
project as an example of what *not* to do.

**multidlc 4.2.0** [verified, `simulator.js` lines 1818–1830]: sorts the results
table by tR, computes adjacent Rs with a Purnell-type formula in k and N, and
takes the minimum. Single condition only; no sweep.

**AutoLC-BO** [verified, `rm_code/crf.py`]: `sort_peaks` is called before every
CRF, with the comment "We need to do sorting so in the list are neighbours."
Resolution uses `abs(tR2−tR1)`. Flip information is deliberately discarded
because the Bayesian optimiser only needs a scalar score.

**Java applet / mlibby port**: no resolution computed at all [verified by grep].

**den Uijl 2021** does not discuss order reversal; its metric is per-compound
retention-prediction error [verified from the PDF text].

**Consequence for hplcsim [derived].** Keep the §8.3 design (sort per grid
point, min over adjacent pairs). To *display* flips, carry a **signed** pair
quantity: for each pair (i, j) fixed by identity in the first scouting run,
store `Δ = tR_j − tR_i` on the grid; a sign change between adjacent grid points
brackets a crossing, and the map can mark it and refine locally
(`gradient-elution-math.md` §8.3's "refine adaptively" step). Nobody in the
survey does this, so there is no code to borrow; it is a few lines on top of
what v0.1 already computes.

---

## 3. Extrapolation beyond the scouting bracket

No project shades, warns about, or even represents the bracket set by the two
scouting gradients.

- **PyLSS** [verified]: the map sweeps tG 2–60 min and %B ranges fixed in
  `plotmaps.py` (`g_start 0–0.30, g_stop 0.50–1.0`) regardless of what gradients
  the parameters came from. Conditions where any peak predicts `tR < t0` or
  `tR > tG + 2·t0` are silently dropped (the function returns `None, None`),
  which leaves holes in the map rather than a warning.
- **apex-res** [verified]: sweeps φ0, φf ∈ [0, 1]; `tg_final` defaults to the
  first scouting tG and is a single value, so there is no tG sweep and no
  bracket concept.
- **AutoLC-BO** [verified]: the optimiser's bounds are user-set box constraints
  on the gradient profile; nothing in `rm_code/` references the scanning
  gradients' slope range.

The only primary source that quantifies the risk is **den Uijl et al. 2021**
(J. Chromatogr. A 1636, 461780, open access; PDF at
https://pure.uva.nl/ws/files/54095340/2021_Den_Uijl_PROMISE.pdf) [verified from
the extracted text]:

> "Generally, it is not advisable to extrapolate the retention model to predict
> retention times for gradients that are shorter or longer than those used for
> scanning."

> "The prediction errors resulting from extrapolation toward either slower or
> faster (Fig. 10) gradients are higher than for gradients with a slope within
> the range used to establish the model parameters (Fig. 6), but extrapolation
> towards shallower gradients yields smaller errors than towards steeper
> gradients."

> "…the proximity of the slope of a gradient, for which retention will be
> predicted, to one of the scanning gradients, used to build the model, is far
> more determinant of retention prediction error. With decreasing proximity, it
> is more important that the slope of the target gradient lies between the
> slopes of the scanning gradients (i.e., interpolation is better than
> extrapolation, as one would expect)."

> "Whereas it is frequently recommended that the slopes of scanning gradients
> used to obtain retention data should vary by a factor of three or so, we do
> not see any evidence in our results that support this guideline."

**Consequence for hplcsim [derived].** Shade the map outside
`[min(tG1, tG2), max(tG1, tG2)]` (equivalently outside the `b_e` bracket of
`gradient-elution-math.md` §7.3), and make the shading asymmetric in tone if
desired: den Uijl's data say extrapolation toward *longer* tG is less harmful
than toward *shorter*. The same paper undercuts the β = 3 rule that v0.1
inherited from Molnár; that is a v0.2 UI-wording question, not an engine change.

---

## 4. Test datasets and worked examples

Nothing in the survey publishes a **resolution-map answer** (a critical-Rs
curve with a known optimum). What is available:

| Source | What it gives | Usable as | Caveats |
|---|---|---|---|
| **apex-res** `optimisers/two_gradient/example.py` and `tests/test_two_grad_optimise.py` [verified] | 8 peaks (4 in the test) with tR, width, area in two runs: tG 15 and 30 min, φ 0.4→1.0 (test) / 0.6→1.0 (example), `t0 = 2.56`, `tD = 3.05`, N = 19 000 (Agilent 1260, Phenomenex Gemini C18 250×4 mm, 5 µm); expected `S = [8.133, 5.490, 3.650, 3.312]`, `log kw = [4.092, 3.226, 2.604, 2.521]`, predicted tR at tG 15 = `[8.92, 10.73, 12.99, 13.84]`, widths `[0.190, 0.138, 0.174, 0.215]` | Cross-implementation check of two-run arithmetic under apex-res's conventions (base-10, constant 2.3, dwell as `1 − tD/(t0 k0)`) | Expected values were generated by the code itself; the fit averages two b estimates; the tests import modules by bare name and the API router **swaps** `t0`/`tD` (see §5). Not ground truth. |
| **PyLSS** `examples/test_caculation_lss_parameter.txt`, `tests/test_ssengine.py` [verified] | Steroids on a 150×2.1 mm 1.7 µm column: `t0 = 0.969`, `V_D = 0.375 mL`, `F = 0.30`, gradients 14 min 5→95 %B and 60 min 5→95 %B (the test uses 5→96 for the second); compound 1 tR = (8.53, 22.11) → `log kw = 2.7902513433`, `S = 5.9790144752` | Round-trip check of a closed form **without** dwell correction to k0 | The test comment admits the numbers "differ slightly from examples/output_test_lss_parameter.txt possibly due to formula updates". |
| **multidlc 4.2.0 compound DB** (`simulator.js` `calcGradientACN_Agilent_SBC18` etc.) and **Java applet** `Globals.LSSTDataArray` [verified] | 22 compounds × {ACN, MeOH} with `ln kw` (multidlc) or `log10 k'w` (Java) and S each linear in temperature; Java: Zorbax SB-C8, T in °C; multidlc: SB-C18 and SB-C8, T in K | Realistic (kw, S) pairs for synthesising fixtures with wide S spread (crossings guaranteed) | multidlc is "All Rights Reserved"; the Java DB's licence is contradictory (GPLv3 vs CC BY-NC-SA). Re-deriving a few numbers for a test is defensible; bulk copying is not [derived]. Boswell 2013 (J. Chem. Educ., PMC3610537) documents the measurement: HP 1090, four compositions (e.g. 20/30/40/50 %), several temperatures. |
| **den Uijl 2021 Sets X and Y** (CC BY supplement) | 8 and 10 gradient times × 23 / 19 compounds × 10 replicates, measured tR | Already transcribed in `docs/research/validation-datasets.md` (examples 1–2) — the only measured multi-tG dataset for a tG-axis map | Retention only; no peak widths in the parts I read, so no measured Rs. |
| **Guillarme 2022 supplementary Excel** | Exact reference implementation of the two-run closed form | Already `validation-datasets.md` example 3 | Not a map. |

**Consequence for hplcsim [derived].** The map's validation fixture has to be
synthetic and analytic: pick 3–4 peaks with (kw, S) taken from the Java/multidlc
ranges such that two of them have equal `tR` at a `tG*` solvable from the LSS
closed form, then assert that the map (a) finds critical Rs → 0 at `tG*`, (b)
reports the correct critical pair on either side of `tG*`, and (c) locates the
argmax of critical Rs in the right sub-interval. Cross-check the forward
arithmetic against the apex-res and PyLSS numbers *after* translating their
conventions (2.3 → ln 10; PyLSS's missing dwell correction) — if hplcsim
reproduces them only after those translations, that is itself evidence the
conventions are handled correctly.

---

## 5. Pitfalls documented in issues, comments and code

### 5.1 Log-base convention

- **nefuzcj/HPLC issue #2** [verified, open]: a user asks, of line 760
  `tr = 1 + t0 + td_dim + 1/bn/s * Log(1 + bn*s*kk*(1 − x0))`, whether `Log` is
  natural or base-10 "and whether it should be `math.log`". `Log` is never
  defined in the file (the only occurrence is that line), so the LSS branch
  raises `NameError`; the other models use `math.exp` (natural). A live example
  of the §0 trap in `gradient-elution-math.md`.
- **multidlc `simulator.js` line 1415** [verified]: a function
  `isocraticRetentionFactor` computes `kw = 10^(a+bT)` and then
  `k = 10^(ln(kw) − Sφ)` — base-10 and natural log mixed in one expression. The
  live gradient path (`gradientElutionMode`, lines 1947–1967) is consistently
  natural-log. I did not trace whether the mixed function is still called. A
  neighbouring `retentionTime` returns `t0/(1+k)` (should be `t0(1+k)`).
- **PyLSS `ssengine.py`** [verified]: the docstring states
  `tr = t0/b * log10(2.3*k0*b)+td+t0` (no `+1`) while `rtpred` implements
  `log10(2.3*k0*b + 1)`; `getgradientconditions` in `optseparation.py` uses the
  `+1`-less form; and a commented-out block labelled "personal resolution.
  Better and powerfull!!" uses `exp`/`log`. Both conventions in one module.
- **apex-res** [verified]: uses the literal `2.3` (not `ln 10 = 2.302585`) in
  every equation including `k*`; a ~0.1 % bias that compounds through the fit.

### 5.2 Dwell handling

- **apex-res `routers/two_gradient.py`** [verified]:
  `optimiser.t0 = instrument_params.dwell_time` and
  `optimiser.td = instrument_params.dead_time` — the two are swapped at the API
  boundary; the engine's own tests pass because they set attributes directly.
- **apex-res** [verified] applies Snyder–Dolan's `(1 − tD/(t0 k0))` and branches
  to isocratic `tR = t0(1+k0)` when `t0·k0 ≤ tD` (elution during dwell) — the
  same edge case as `gradient-elution-math.md` §4.1, handled correctly in form.
- **PyLSS** [verified]: tD is added as a pure delay with **no** correction of k0
  for migration during the dwell. `getAutomaticElutionWindowStretching` computes
  `t0 = self.v_m * self.flow` and `td = self.v_d * self.flow` (volume × flow
  instead of ÷), while `gradientutils.py` carries the comment
  `t0 = v_m/flow # Fixed: was v_m*flow` — the same units bug fixed in one module
  and still live in another.
- **Java applet** [verified, `calculateGradient`]: dwell is a mixer model —
  "mixing volume" (exponential blending) plus "non-mixing volume" (pure delay),
  integrated on a 1000-point time grid. The end time is padded by
  `(3·V_mix + V_nonmix)/F`. This is richer than a scalar tD and is the only
  open-source treatment of gradient distortion I found.
- **den Uijl 2021 Eq. 7** [verified]: defines `τ = tD + t0 + t_init` as the
  delay before the gradient reaches the analyte, with `k_init` migration during
  it — the form hplcsim already uses.

### 5.3 Post-gradient elution

- **AutoLC-BO `retention_model.py`** [verified]: three explicit cases — elutes
  before the gradient, during segment *n* (with the per-segment closed form
  `tR = t0 + tD + t_init + t_n + (1/(S·B_n))·ln(1 + t0·S·B_n·k(φ_n)·(1 − f_before − Σ a_i))`),
  or in the final isocratic hold (`tR = tD + t_init + t0 + t_n + t0·k(φ_final)·(1 − …)`).
  Structurally the cleanest implementation in the survey.
- **den Uijl 2021 Eq. 8** [verified] gives the same post-gradient form:
  the residual fraction after `tG` elutes isocratically at `k_final`.
- **multidlc** [verified, lines 1960–1964]: when `(tR − tD − t0) > tG` it sets
  `φe = φ_i` (the *initial* composition) rather than `φ_f`, so ke and therefore
  σ are overestimated for late eluters. Also the closed form itself is applied
  without checking the elution window, so tR for a post-gradient peak is wrong
  before φe is even considered.
- **PyLSS** [verified]: any peak with `tR > tG + 2·t0` invalidates the whole
  grid point; **apex-res** [verified]: `calculate_total_resolution` only sums
  pairs with `tR < tG`.

### 5.4 Peak width and resolution formula

- **PyLSS** [verified]: `get_lss_peak_width` returns `4·N^-1/2·G·t0·(1+ke)`
  (a 4σ width) and the Rs routine then multiplies it by 1.7 "to obtain the peak
  width at base" — a factor that belongs to half-height width, not 4σ; every
  Rs on the PyLSS map is therefore low by ~1.7× [derived].
- **apex-res** [verified]: `k* = k0 / (2.3·b·k0/2 − t0/tD + 1)` — the term is
  `t0/tD`, which is dimensionally a ratio but is not the `tD/(t0 k0)` correction
  used elsewhere in the same file; I could not match it to any published form
  [could not verify]. N is fixed to a user estimate (the width-based `estimate_N`
  is commented out).
- **multidlc** [verified]: critical Rs uses `Rs = (k2/(k2+1))·(|α−1|/α)·(√N2/4)`
  with the *gradient* ke values plugged into an isocratic Purnell-type formula.

### 5.5 Grid and interpolation

- PyLSS: tG step 2 min, then bilinear/`scipy.interpolate` to 500×500
  [verified]. Interpolating a scalar minimum smooths exactly the troughs the map
  exists to find [derived].
- apex-res: 101×101 in φ0/φf, no tG axis [verified].

---

## 6. What this means for hplcsim v0.2

1. **There is nothing to adopt wholesale.** The two projects that draw maps
   (PyLSS, apex-res) are behind SPEC and `gradient-elution-math.md` §8.3 on every
   axis the ticket asked about: neither shows flips, neither shows the bracket,
   neither has a fixture with a known map answer, and both carry live
   convention bugs (§5). [derived]
2. **Reuse by reading, not by copying.** AutoLC-BO's `retention_model.py` is the
   right *structure* for a multi-segment forward model (v0.2 frontier, not
   v0.1); it is CC BY-NC-SA, so re-derive from den Uijl Eq. 7–8 rather than
   port. PyLSS is AGPL-3.0 and mlibby/Java are NC or GPL; only apex-res (MIT) is
   licence-compatible with copying, and it is the one not worth copying.
   [verified licences; derived advice]
3. **Flip display**: implement the signed-pair `Δ = tR_j − tR_i` grid and local
   refinement described in §2. No precedent; cheap on top of v0.1. [derived]
4. **Extrapolation**: shade outside `[tG1, tG2]`; cite den Uijl 2021 for the
   asymmetry (longer-tG extrapolation is safer) and for dropping any claim that
   β = 3 is special. [verified source; derived UI]
5. **Validation fixture**: synthesise an analytic crossing case (§4) and use the
   apex-res / PyLSS numbers only as convention-translated cross-checks. Consider
   the multidlc/Java (kw, S) ranges as the source of realistic spreads.
   [derived]
6. **Pitfall checklist for code review** (all seen in the wild, §5): mixed log
   bases in one module; swapped `t0`/`tD` at an I/O boundary; `V·F` vs `V/F`
   for a time; no dwell correction to k0; φe clamped to φ_i after the gradient;
   4σ width multiplied by a half-height factor; |Rs| hiding a flip; coarse tG
   grid smoothed by interpolation. hplcsim's log-convention rule and inputs-only
   persistence already guard the first two structurally.
7. **Not for v0.1.0** — everything here is v0.2 scope (map, optimizer,
   multi-segment gradients).

---

## 7. Notes on the adjacent hosts

- **GitLab** [verified via API]: only `m_libby/hplc_simulator` (a mirror of #4)
  and `open-works/chromatography` (chrom-rs, #12) are simulators; the rest are
  data-processing or hardware documentation. `heingroup/data-driven-hplc-
  method-development` exists (last activity 2025-08-14) but its README could not
  be read via the API [could not verify].
- **SourceForge** [verified]: `hplcsimulator` (pgboswell), registered
  2010-03-31, last update 2013-08-05, GPLv3 per the project page, Java, "Beta";
  SVN at `svn.code.sf.net/p/hplcsimulator/code`.
- **PyPI** [verified via JSON API]: `bago` 1.0.0 (CC BY-NC 4.0). `pylss` is an
  unrelated package. No LSS / gradient-simulation package is published on PyPI.
- **CRAN** [verified]: `chromatographR` removed 2022-11-07 ("recurring issues
  were not corrected in time"; lives on GitHub); `RpeakChrom` removed
  2026-04-30 (maintainer e-mail undeliverable). Neither models retention.
- **Zenodo** [verified]: MOREPEAKS v1.0.1 (2021-11-10), CC BY 4.0, 2.3 GB
  MATLAB-runtime installer; cites Pirok 2016 (PIOTR), the 2018 peak-tracking
  paper and a 2021 paper; no source code, no GitHub link.

---

## 8. What I could NOT verify

1. **Boswell et al. 2013 supplementary material** — the paper says the
   calculations are in the SI; ACS returned 403. The gradient algorithm is
   therefore described from the Java source (`HPLCSimulatorApplet.java`), not
   from the authors' write-up.
2. **LCGC articles** on the open-source simulator (chromatographyonline.com) —
   HTTP 403, as in earlier tickets.
3. **Zisi / Pappa-Louisi / Nikitas 2020 R code** — ScienceDirect 403; PubMed
   abstract says only that "an illustrative video" is in the supplement. Whether
   the R functions were ever released, and under what licence, is unknown. Not on
   CRAN under any name I searched.
4. **MOREPEAKS / PIOTR internals** — binary only; the CAST page and Zenodo record
   do not state the retention models, map axes or optimiser. Its behaviour is
   inferred solely from den Uijl 2021 §2.4 (it fits the models and reports
   goodness of fit).
5. **multidlc.org licence** — the page footer says "All Rights Reserved"; the
   older hplcsimulator.org site says CC BY-NC-SA 3.0 for the Java version. I
   could not find a licence statement covering `simulator.js`.
6. **Java applet licence** — GPLv3 (SourceForge) vs CC BY-NC-SA 3.0
   (hplcsimulator.org/development) is a genuine contradiction between the
   author's own pages.
7. **apex-res `k*` formula** (§5.4) — could not be matched to a published form.
8. **apex-res `docs/TwoGradient.md`** — empty at HEAD, so the author's intended
   algorithm description is unavailable; the README points to it.
9. **HappyTools** — `gh search repos "HappyTools chromatography"` returned
   nothing and the guessed path `Bram-Hulsebos/HappyTools` is 404. Not located.
10. **`heingroup/data-driven-hplc-method-development`** README (GitLab) —
    the raw-file API returned nothing; the project may lack a README or be
    restricted.
11. **Search coverage** — `gh search repos` returns at most the top matches per
    query and GitHub's index is keyword-based; a repository that never says
    "HPLC", "gradient" or "chromatography" in its name or description would be
    missed. Ten queries plus name lookups is thorough for the obvious terms, not
    exhaustive.
12. **Nothing was executed.** Every statement about behaviour is from reading
    source, tests, docstrings and issues.

---

## References

Repositories and pages opened (all accessed 2026-09-02):

1. gmrandazzo/PyLSS — https://github.com/gmrandazzo/PyLSS (README, `doc/Documentation.md`, `TODO`, `LICENSE`, `src/pylss/{ssengine,optimizer,optseparation,gradientutils,lssoptseparation,RsOrgSolvPlot}.py`, `src/pylss/gui/plotmaps.py`, `tests/`, `examples/`, `.github/workflows/python-ci.yml`).
2. joekitsmith/apex-res — https://github.com/joekitsmith/apex-res (README, `pyproject.toml`, `apex_res/optimisers/two_gradient/**`, `apex_res/routers/two_gradient.py`, `apex_res/schemas/two_gradient.py`, `frontend/src/features/twoGradient/**`, issues #1–#27).
3. Boswell / Carr / Stoll HPLC Simulator — https://sourceforge.net/projects/hplcsimulator/ ; https://hplcsimulator.org/about/index.php ; https://hplcsimulator.org/development/index.php ; fork https://github.com/joshuapouliot27/HPLC-Simulator (`HPLCSimulatorApplet.java`, `Globals.java`); fork https://github.com/andychase/HPLC-Simulator (metadata only).
4. Boswell, P. G.; Stoll, D. R.; Carr, P. W.; et al. "An Advanced, Interactive, High-Performance Liquid Chromatography Simulator and Instructor Resources." *J. Chem. Educ.* 90 (2013) 198–202. https://pmc.ncbi.nlm.nih.gov/articles/PMC3610537/
5. mlibby/hplc_simulator — https://github.com/mlibby/hplc_simulator (README, `src/js/model/{hplc_formulae,hplc_simulator,hplc_compound}.js`, issues #1–#10).
6. HPLC Simulator 4.2.0 (multidlc.org) — https://www.multidlc.org/hplcsim/4_2_0/ , `…/4_2_0/simulator.js`, https://www.multidlc.org/hplcsim/whats_new/ , https://www.multidlc.org/hplcsim/about/
7. Jimbo994/AutoLC-BO — https://github.com/Jimbo994/AutoLC-BO (README, `license.md`, `rm_code/{retention_model,crf,chromatographic_response_functions,peak_width}.py`, `example_interface_code/assymetric_resolution.py`). Paper: Boelrijk et al., *Anal. Chim. Acta* 1242 (2023) 340789, https://doi.org/10.1016/j.aca.2023.340789
8. MOREPEAKS — https://zenodo.org/records/5710443 ; https://cast-amsterdam.org/tag/morepeaks/
9. den Uijl, M. J.; Schoenmakers, P. J.; Schulte, G. K.; Stoll, D. R.; van Bommel, M. R.; Pirok, B. W. J. "Measuring and using scanning-gradient data for use in method optimization for liquid chromatography." *J. Chromatogr. A* 1636 (2021) 461780. https://doi.org/10.1016/j.chroma.2020.461780 ; PDF https://pure.uva.nl/ws/files/54095340/2021_Den_Uijl_PROMISE.pdf
10. huaxuyu/bago — https://github.com/huaxuyu/bago ; https://pypi.org/pypi/bago/json
11. Bourne-Group/HPLCMethodOptimisationGUI — https://github.com/Bourne-Group/HPLCMethodOptimisationGUI (README, file list).
12. nefuzcj/HPLC — https://github.com/nefuzcj/HPLC (`prediction program.py`, issues #1–#3).
13. Zisi, C.; Pappa-Louisi, A.; Nikitas, P. "Separation optimization in HPLC analysis implemented in R programming language." *J. Chromatogr. A* 1617 (2020) 460823. https://doi.org/10.1016/j.chroma.2019.460823 (abstract via PubMed E-utilities, PMID 31932085).
14. open-works/chromatography (chrom-rs) — https://gitlab.com/open-works/chromatography (README via GitLab API).
15. GasChromatographyToolbox — https://github.com/GasChromatographyToolbox/GasChromatographyToolbox (README).
16. Data-processing tools (metadata and README only): https://github.com/cremerlab/hplc-py ; https://github.com/HaasCP/mocca ; https://github.com/ethanbass/chromatographR ; https://github.com/lucashn/peakutils ; https://github.com/JBrinco/Chromapy ; https://cran.r-project.org/web/packages/chromatographR/index.html ; https://cran.r-project.org/web/packages/RpeakChrom/index.html
17. Practical HPLC Simulator (Guillarme lab) — https://farma-unites.unige.ch/en/guillarme-lab/tools/practical-hplc-simulator
18. This repository's own prior research: `docs/research/gradient-elution-math.md` (§0, §3.4, §7.3–7.4, §8.3) and `docs/research/validation-datasets.md` (examples 1–3).
