# ACD/Labs Method Selection Suite as a feature benchmark for SPEC §11

Research notes resolving ticket [#114](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/114),
filed from the driver's question "does the ACD Method Selection Suite help our development
status?". **Question:** what does ACD/Labs' Method Selection Suite — LC Simulator, Column
Selector, peak tracking and processing, property prediction, the method database — actually do
per its primary sources, and where does each capability land against SPEC §11's roadmap. **The
finding owed:** one table, ACD capability → §11 slot → hplcsim status → open equivalent already
researched, plus any place the benchmark argues §11's ordering or the profiles map's
"chemistry identity" fog should change, written as recommendations for the driver to grill,
never as an amendment. **Date:** 2026-09-06 (every source accessed that day unless stated).
**Audience:** the driver ranking §11; the profiles map [#103](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/103)
for its "chemistry identity" bullet; and the sibling repo `zhipengzhu1-dotcom/14-August-2026`,
whose map names its quality target as "close to ACD/Labs Method Development Suite".

Every claim is tagged **[verified]** (read in the source named), **[derived]** (my inference,
shown) or **[could not verify]**. Posture, per the ticket: ordinary public fetches (WebFetch,
WebSearch, `curl`, the Europe PMC and Crossref REST APIs); a page that refused is a finding in
§9, not something worked around. **One exception, recorded plainly (§9.2):** mid-session the
driver wrote "use shadow browsers if you can", and on that instruction four third-party pages
that had refused ordinary fetches (an RSC abstract page, a trade listing, a forum thread and
the LCGC article that is LC Simulator's methods paper) were read once with a real Chromium
through Playwright — the same second-pass shape as `vendor-column-and-instrument-data.md`
§10. No acdlabs.com page needed it. Nothing licensed under ACD's terms is reproduced: no
images, no assets, no equations from the software; short feature names are quoted with their
source. The earlier read of the *Optimizations* window ([#56](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/56),
resolved into #45) covered information architecture only; this document is the feature
benchmark that read never did. The driver's screenshot stays local and untracked
(`Front-End Design/Screenshot 2026-08-14 at 9.46.30 PM.png`) and is referred to by path.

**Headline** (§0, §7, §8): ACD's suite is a *multi-run, multi-factor* retention modeller with a
peak-matching front end and a column-similarity side tool; every capability it has that
hplcsim lacks already sits in a named §11 cycle, and nothing in the benchmark argues for
adding a cycle. Three things it does argue: (1) the most-cited ACD map is **tG × temperature**,
built from four runs, so the v0.7 map does not need pH to be worth drawing and could move
ahead of v0.6; (2) ACD's own methods paper calls pH modelling "possible but less common" with
"relatively large" errors, which supports §11 keeping temperature before pH; (3) on the
profiles map, ACD keys every selectivity source (its Tanaka database, and the open HSM and
WSU databases alike) by **commercial column name**, so the profile's "chemistry identity"
should be a free-text phase name plus optional part number, held as a future join key, and
nothing more. Where hplcsim is *ahead*: t0 and dwell provenance (ACD types Dead Time beside
the geometry with no stamp), and refusing a hidden composite objective (#29) where ACD's map
colours a product of normalised criteria.

---

## 0. The owed table

Column 2 is the §11 cycle that owns the capability (or §2/§4 where v0.1 already has it).
Column 3 is hplcsim on `main` at `4e57963`. Column 4 names the research already done in this
repo (`docs/research/`) or in the 14-Aug repo (`research/`, cited by file and issue, nothing
copied). Sources for each ACD claim are in §1–§6.

| # | ACD capability (source §) | SPEC §11 slot | hplcsim status | Open equivalent already researched |
|---|---|---|---|---|
| 1 | Gradient editor: a No. / Time / %B table, multi-segment, chromatogram redrawn live (§2.4) | v0.2 gradient freedom | **Built**: two No. / Time / %B tables in the rail, programme overlay, composition-window whisker (#73, #74) | `github-hplc-simulators.md` §5.3/§6 (multi-segment licence ruling) |
| 2 | Vendor data import: Agilent, Waters, Thermo, Shimadzu, Bruker, SCIEX, ASCII, netCDF, JCAMP (§2.6) | v0.3 CSV import | Absent; peak table typed by hand | None. `github-hplc-simulators.md` found no open project reading vendor formats; CSV only |
| 3 | Automated peak matching from UV spectra ("UV-Mutual Automated Peak Matching Algorithm") and MS (§2.5) | v0.3 auto peak-matching | Absent; the user pairs rows (SPEC §5) | 14-Aug #16 (assign-within-scenario tracker; DAD/MS as evidence channels; co-elution as a rendered frequency) |
| 4 | Model choice per factor — "linear, polynomial, inverse, or logarithmic" — fitted to n runs with a goodness-of-fit overlay (§2.2) | v0.3 ≥2-run regression (+ isocratic) | Two-run closed-form seed then a solve; linear ln k–φ only (SPEC §3) | `gradient-elution-math.md`; `composition-extrapolation.md` (two parameters cannot see curvature); 14-Aug #24 (interpolation beats LSS reparameterisation) |
| 5 | Temperature as a second axis: 2 × 2 = 4 runs for small molecules (§2.3, §6.1) | v0.4 temperature (2×2) | Metadata only (SPEC §4) | 14-Aug #11 (four roles of temperature), `retention-datasets.md` (30→50 °C flips order in ~1 % of pairs) |
| 6 | Searchable, shareable method database; structure and substructure search (§5.3) | v0.5 hosting + sharing | Session file, inputs only, one user (SPEC §8) | None |
| 7 | pH as an axis (with gradient or temperature; 2D and 3D) (§2.3) | v0.6 pH (three-run design) | Absent | 14-Aug `ionisation-providers.md` (Uni-pKa; Rosés/Bosch scale correction), #34 (`D` term fitted, never zero) |
| 8 | Resolution map 1D / 2D / 3D; "Suitability-limits map"; Table of Methods with a suitability score; "Generate Methods"; MODR display (§3) | v0.7 resolution map / optimizer | Empty frame with real axes (SPEC §7); goal-seek and ceiling decided (#29), sweep vocabulary in `CONTEXT.md`; nothing filled | 14-Aug #10 (threshold-anchored colour, pair territory), #19 (probabilistic design space; `P(all)` collapses with peak count; recommend the most interior point); `prototype/resolution-map.html?variant=A` |
| 9 | Column Selector: six Tanaka parameters, z-scored Euclidean "column difference factor", 254 → 340+ columns, weights adjustable, radar and dendrogram (§4) | v0.8 column selectivity DB | Absent; #103's profiles carry geometry and architecture only, chemistry identity is fog | 14-Aug `hsm-lser-bridge.md` (819-row HSM CSV, `Fs`, CC BY-NC-SA), `lser-system-constants.md` (WSU 27 MeOH / 25 MeCN columns), #36 (`Fs`-nearest is not LSER-nearest) |
| 10 | Method transfer: free LC Method Translator — geometry, flow, gradient-time and injection scaling, dwell compensation, re-equilibration estimate (§2.7) | v0.8 method transfer | Absent; SPEC §6 diagnostic 6 already forbids carrying fitted S, k0, N to another flow or column | `dead-time-from-geometry.md` §6; 14-Aug `instrument-layer.md` §5 (dwell "breaks method transfer" because it is selectivity-affecting) |
| 11 | Property prediction: pKa (Classic and GALAS), logP, logD, "% ionization vs. pH" plot to pick a pH (§5.1) | v0.9+ structure-based | Absent | 14-Aug `ionisation-providers.md` (Uni-pKa benchmarked level with ACD Classic/GALAS over 31,250 molecules) |
| 12 | Structure → retention (ChromGenius lineage, now "Retention-Time Prediction ... from behavior of structurally similar molecules") (§5.2, §6.3) | v0.9+ structure-based | Absent | 14-Aug `qspr-approaches.md`, `abraham-ground-truth.md` (#5: Abraham "ground truth" is partly ACD Absolv output), `marchetto-baseline.md` |
| 13 | Instrument characterisation: dwell and dead time entered as method values, no provenance shown (§2.8) | v0.1 §4 (shipped) | **Ahead**: dwell required with no default; t0 measured-first with marker text; V_ec readout; estimated-t0 stamp | `dead-time-from-geometry.md`, `porosity-for-t0-geometry.md`, `vendor-column-and-instrument-data.md` |
| 14 | Peak width and asymmetry: empirical width and asymmetry models, opaque to the user (§2.2) | v0.1 §3 (shipped, Gaussian) | Present for width (N fitted from W½, G convention); asymmetry not modelled | `plate-count-from-widths.md`; 14-Aug `instrument-layer.md` (G ≈ 0.77–0.85) |
| 15 | Flow rate and ternary solvent ratio as optimised axes (§2.3) | Not in §11 | Absent | 14-Aug #12 (ternary ruled out; both binaries modifier-conditioned) |
| 16 | Composite objective: suitability "as Product of normalized" (or minimum) over Resolution, Run Time, k′, tG, %B, Temperature (§3.1) | v0.7 optimizer | **Deliberately not**: #29 chose two named answers, goal-seek and ceiling, "no hidden optimization policy" | 14-Aug #19 (Pareto on run time against interior margin, never a scalar) |
| 17 | Robustness: AutoChrom varies flow, T, gradient, pH, buffer, solvent ratio; MODR shown on 2D maps (v2025) (§3.3) | Unscheduled (SPEC §7's Rs 2.0 colour is display only) | Absent | 14-Aug #19 (margin = distance to the design-space boundary); `CONTEXT.md` there: predicted vs established design space |
| 18 | GC simulator; HILIC / IEX / mixed-mode / protein modes; NMR, MS, IR processing; instrument control (AutoChrom) | Out of scope (SPEC §2) | — | — |

**[derived]** Rows 2–4 are one cycle in §11 and one workflow in ACD: import → match peaks
across runs → fit a chosen model to all of them. Every ACD paper in §6 leans on exactly that
triad; the two-run closed form hplcsim ships is the special case n = 2, linear.

---

## 1. What the suite is

### 1.1 Modules, as ACD names them today

**[verified]** The product page (ref. 1) does not present five named modules. It names
**LC Simulator**, **GC Simulator** and **Column Selector**, and otherwise groups capabilities
under functional headings: physicochemical property prediction; column selection; data
import and processing; modelling and optimisation; retention-time prediction; databasing and
reporting; multi-technique processing (NMR, MS, IR alongside chromatography). "Peak Tracker",
"Property Predictor" and "Method Database" in the ticket title are the driver's names for
three of those headings, not ACD's. The suite runs on the **Spectrus** platform; its data
import is the platform's (ref. 8). The trade listing (ref. 27, browser pass) summarises the
same five things: "3D optimization for QbD method development", physchem prediction for
starting conditions, Tanaka column comparison, "Databasing tools to build knowledge base of
previous methods and results", vendor-format compatibility.

**[verified]** The sister product **AutoChrom** (ref. 4) is the same modelling engine with a
project workflow and direct instrument control (Agilent ChemStation and OpenLab CDS 2.5–2.8,
Waters Empower 2 and 3; no Chromeleon named); "AutoChrom Offline works with any instrument
using manual parameter transfer". Instrument control is out of hplcsim's scope (SPEC §2), so
AutoChrom is cited below only where it documents a feature the two products share.

### 1.2 Naming history, dated

| Date | Source | Names in use |
|---|---|---|
| 2002 | Pittcon abstracts, PMC2562965 (ref. 30) | "ACD/AutoChrom uses both UV-Vis and MS detection to track peaks" — the AutoChrom name and UV+MS peak tracking already exist |
| 2004-01-31 | R&D World (ref. 31) | "ACD/LC Simulator 8.0 ... part of ACD/Method Development Suite"; pKa prediction from ACD/pKa DB added; a "Suggest Gradient" tool |
| 2006-07-05 | Technology Networks (ref. 32) | Column Selector update, 153 → 187 columns, data from Euerby and Petersson (then AstraZeneca) |
| 2010-06-13 | SelectScience (ref. 33) | "ACD/LC Simulator", "ACD/ChromGenius", "ACD/AutoChrom Method Development Suite (MDS)" |
| 2011–2013 | ACD press release (ref. 34) | Spectrus platform: Processor 2011, Workbooks 2012, Spectrus DB March 2013 |
| 2012-06-15 | Technology Networks (ref. 35) | Version 2012: "ACD/AutoChrom MDS", "ACD/ChromGenius", "ACD/LC Simulator", new "ACD/Chrom Workbook", on the Spectrus platform |
| v2018.1 | Lab Manager (ref. 36) | Chromatography line consolidated into "the improved ACD/AutoChrom, and the new ACD/Method Selection Suite" |
| 2018-03 | LCGC Europe (ref. 20) | Cites `acdlabs.com/products/com_iden/meth_dev/lc_sim/` (accessed 2017) — that URL is 404 today; `.../meth_dev/chromgen` 301s to the AutoChrom page; `.../meth_dev/` 301s to the LC/GC solutions page (all checked with `curl`) |
| 2025-11-10 | ACD press release (ref. 37) | Revvity announces an agreement to acquire ACD/Labs; products listed include Method Selection Suite and AutoChrom |

**[verified]** So "Method Development Suite" was the AutoChrom bundle's name (2004–2012);
"Method Selection Suite" is the 2018 rename of the non-instrument-control bundle. The 14-Aug
map's quality target "close to ACD/Labs Method Development Suite" therefore names the older,
AutoChrom-era label; the product it describes is today's Method Selection Suite plus
AutoChrom. **[verified]** ChromGenius survives as the unnamed "Retention-Time Prediction"
capability on both product pages (refs. 1, 4). **[could not verify]** Whether ChromGenius is
still a separately licensed module.

### 1.3 Version state

**[verified]** Current version page (ref. 2) is "Version 2025": template reporting for LC
Simulator data; "Users can now display and report the Method Operable Design Region (MODR)
and values across all 2D optimizations, except solvent ratio mode"; new TetraScience and
Waters import formats. Version 2024 (ref. 1, "What's New"): "Optimize solvent mixtures by
defining primary organic phases" and "Improved Resolution and Suitability Map visualization".
The LC Simulator build used in the LCGC methods paper was 2016.2.2; the Hemida 2024 paper
names "ver. L35R41" (ref. 26).

---

## 2. LC Simulator's retention modelling

### 2.1 What the vendor states

**[verified]** Ref. 1: "1D, 2D, or 3D models"; equations "linear, polynomial, inverse, or
logarithmic"; optimise "pH, temperature, gradient, solvent ratio, and flow rate"; modes
"reversed-phase, HILIC, mixed mode, and protein separations"; "GC temperature gradient
optimization from two experimental chromatograms"; "Goodness-of-fit evaluation with overlay
comparison"; "Interactive gradient editing with real-time chromatogram updates".
**[verified]** ACD states **no minimum run count** for LC anywhere I could read (refs. 1, 2,
4); the "two experimental chromatograms" phrase is the GC simulator's.

### 2.2 What the methods paper states (LC Simulator 2016.2.2)

The primary source for how the models work is Petersson, Boateng, Field and Euerby, *LCGC
Europe* 31(3), March 2018 (ref. 20; read on the browser pass, §9.2). Its Experimental
section: "Modelling was performed using ACD Lab's LC Simulator (version 2016.2.2)". All of
the following is **[verified]** from that text:

- **Models offered.** Five equations: first-order ln k versus φ (the LSS line); second-order
  in φ "for very high levels of organic modifier" and for peptides and proteins; temperature
  as a 1/T term, optionally 1/T²; and a log–log relationship for buffer concentration.
  "Commercial software for retention modelling is based on numerical calculations", which is
  what lets any two factor models be combined. This is the "linear, polynomial, inverse, or
  logarithmic" list of ref. 1 with its physics attached.
- **Peak width.** "The software employed in the current study uses empirical peak width or
  asymmetry models"; "How the peak width and peak asymmetry models are defined is usually not
  visible in the software to the user." The paper recommends entering W½ and converting to
  4σ, and notes areas "are only used to facilitate visual comparisons" — the same posture as
  SPEC §4 and §7.
- **Runs per dimension.** Gradient: two runs at tG differing "by a factor of three", aimed at
  k* ≈ 3 and 9 (a third at k* ≈ 6 for a second-order model). Temperature: "two temperatures,
  for example, 30 °C and 60 °C" for small molecules, three for proteins — "2 × 2 = 4 or
  3 × 3 = 9 experiments". Isocratic: k ≈ 3 and 9 (and 6 for three parameters). These are
  literature rules (Snyder and Dolan 2007) the authors apply, not limits the software imposes.
- **Model selection rule.** "the simplest model should be selected that still gives an
  acceptable error for the validation data set. A first order model ... is more robust and
  allows for more extensive extrapolation than a second order model."
- **pH.** "It is possible — but less common — to optimize pH by retention modelling ... the
  range covered by pH models is often quite narrow ... In addition, the prediction errors can
  be relatively large." Ionised acids at intermediate pH give non-linear ln k versus φ.
- **Dwell.** Defined as mixing point to column head; measured with a linear-gradient
  procedure; a ±20 % dwell error costs "<<1 %" in absolute retention; once measured it need
  not be re-measured unless flow, slope or hardware changes. Iterating dwell to minimise fit
  residuals is named as an alternative — the data-tuned dwell hplcsim refuses (driver
  2026-09-02, dwell is the instrument's 0.375 mL always).
- **Dead volume.** Water at 214 nm recommended over uracil (uracil is pH-sensitive); a ±20 %
  error costs <1 %; "for gradient modelling ... the dead volume for initial gradient
  conditions gives a better fit than the average dead volume".
- **Peak tracking.** "Effective and rapid assignment of peaks in the input chromatograms
  remains the 'Achilles heel' of retention modelling"; automated UV/MS trackers "do not handle
  multiple samples because they assume that all components of interest are present in the
  same sample"; "retention modelling software requires that there should not be any missing
  data for any of the analytes that are modelled" (compare SPEC §5's untracked row).
- **Accuracy metric.** 90th percentile of |predicted − actual| × 100 / actual, chosen over a
  standard deviation. Numbers in §6.1.

**[derived]** ACD's "1D / 2D / 3D" is therefore a count of *factors*, each with its own small
model, combined numerically; the run count is the product of the per-factor levels. hplcsim's
v0.3 "≥2-run regression" and v0.4 "temperature (2×2)" are the same design written as two
cycles.

### 2.3 Axes

**[verified]** Ref. 1: pH, temperature, gradient, solvent ratio (ternary: a mixture of two
predefined organics, per ref. 4), flow rate. The two ACD screenshots show the mode names:
the driver's shows status-bar mode "RP Gradient/Temperature" with a Column Temperature × %B
map; the image that the LC Simulator URL serves (ref. 3, §9.1) shows a pH field, a
three-axis map over Temperature, pH and Time, and tabs for Gradient/Temperature,
Gradient/pH, Temperature/pH, 3D View and All in One. **[verified]** Peer-reviewed 3D builds:
gradient × temperature × ternary ratio, 27 runs (ref. 26); gradient × temperature × column
and mobile-phase combinations, 2 × 2 or 3 × 3 (ref. 23). **[verified]** No peer-reviewed
paper found reports an LC Simulator pH-axis accuracy number; pH appears only in vendor text
and in an IEX pH-gradient study (ref. 25).

### 2.4 Gradient editor

**[verified, screenshot]** A No. / Time / %B table (six rows visible, more by scrolling), a
Temperature field, and tabs Gradient Editor and Grad.Editor Res.Map; the second screenshot
adds a Stop Time field. **[verified]** Ref. 1: "Interactive gradient editing with real-time
chromatogram updates". This is the information architecture #56 handed to #45; hplcsim's
rail now has the same table shape (SPEC §7).

### 2.5 Peak matching and processing

**[verified]** Ref. 1: "Assign chemical structures to peaks"; "Peak picking and
integration"; "Baseline correction and peak deconvolution"; a "UV-Mutual Automated Peak
Matching Algorithm" for LC/UV peak tracking with spectral overlay; "Macro automation".
Ref. 4: "Algorithmically track peaks between runs" using UV or MS spectra. **[verified]**
The 2002 abstract (ref. 30) already describes UV plus MS tracking in AutoChrom.
**[could not verify]** The algorithm itself — no technical description is public.

### 2.6 Import formats

**[verified]** Ref. 8 (platform-wide, not per product): Agilent ChemStation (.d, .ch, .ms,
.uv), OpenLab CDS, EZChrom; Waters Empower 2/3 (.raw), MassLynx, UNIFI; Thermo Xcalibur,
Chromeleon 6/7, Atlas, GAML; Shimadzu LabSolutions, LCsolution (.lcd); Bruker Compass;
SCIEX Analyst (.wiff); ASCII (.txt, .csv, .asc), netCDF (.cdf), JCAMP-DX. v2025 adds
"TetraScience and Waters formats" (ref. 2).

### 2.7 Method transfer and scaling

**[verified]** ACD's free web **LC Method Translator** (ref. 6): scales flow with column
geometry ("Scaling of flow to hit optima in van Deemter"), scales gradient times
geometrically, scales injection volume, "Accounts for instrument dwell and dead volumes;
users can input experimental values or use estimates", gives a pressure warning and a
re-equilibration estimate; cites Petersson, Euerby and James, *LCGC* 2014, and Ph. Eur.
2.2.46 for dwell measurement. **[verified]** A Pfizer application note (ref. 17) describes a
"vary method parameters" tool in the suite that enumerates parameter-variation combinations
and names dwell volume and pump type as the "impactful instrument parameters" for transfer.
**[derived]** ACD's method transfer is *programme translation* (geometry, flow, dwell
offset), not transfer of fitted retention parameters — the distinction SPEC §6 diagnostic 6
already draws.

### 2.8 How the method panel holds column and instrument

**[verified, screenshot]** Column Name (free text), Length, Diameter, Particle Size, Dead
Time in one block; Flow Rate with Solvent Used, Pressure and Average Plate N in the results
block; Temperature beside the gradient table; the second screenshot adds Dwell Time and
Mobile Phase A / B as method fields. No vendor, part number, packing architecture,
measured-versus-estimated stamp or marker. This was already posted to #104 and #105 on
2026-09-06; §8.4 draws the profiles-map consequence.

---

## 3. The suitability map and design-space claims

### 3.1 How suitability is defined

**[verified, screenshot]** A panel headed "Suitability" with a value, then "as Product of
normalized", then six rows each with its own 0–1 value: Resolution, Run Time, k′,
tG(0-100%), Solvent B, Temperature. In the driver's capture Resolution reads 0.08437,
Solvent B 0, the other four 1, and the headline Suitability 0. The second image (ref. 3)
shows the same panel headed "as Minimum of normalized". **[verified]** Ref. 1 calls the
display a "Suitability-limits map" that "visualizes criteria across design space"; ACD's
2012 wording (ref. 35): LC Simulator can "propose methods that meet user criteria in terms of
run time, resolution, retention factor (k′)".

**[derived]** Each criterion is normalised to 0–1 against user-set limits (the "suitability
limits"), and the aggregate is either the product or the minimum of the six terms; the map
colours that aggregate, and a candidate with any criterion at 0 scores 0 regardless of the
others. **[could not verify]** The normalisation function (linear ramp, step, or otherwise)
and the exact limit semantics — no ACD document I could read gives the algebra, and it must
not be reconstructed from the software.

**[derived]** This is precisely the "hidden optimization policy" that #29 ruled out for
hplcsim: goal-seek (shortest run time at Rs ≥ target) and ceiling (highest critical Rs) are
two named answers with one scientific meaning each, where ACD's scalar folds six criteria
into one colour. The 14-Aug repo reached the same place from the other side (#19: recommend
the most interior point; Pareto on run time against margin, never a scalar).

### 3.2 Resolution map and Table of Methods

**[verified, screenshot]** Tabs Table of Peaks, Resolution Map, Gradient Editor, Grad.Editor
Res.Map, Experimental Points; the map is Column Temperature (°C) × Solvent B (%) with a
colour bar 0.00–3.81 (a linear ramp in Rs, with crosshair lines at the current condition —
the un-anchored colour scale that 14-Aug #10 names as a defect class). A **Table of Methods**
with columns Suit., Gradient, Temp. (°C), ten rows, values 0 and 1 in the driver's capture
and fractional values (0.24, 0.15 …) in the second image; a toolbar button "Generate
Methods". **[derived]** The Table of Methods is a held list of candidate programmes scored
by suitability — the candidate history that #56 deferred "until more than one candidate can
be held", and that §11 currently gives no owner.

### 3.3 Design space and MODR

**[verified]** Ref. 2 and ref. 4 (v2025): MODR displayed and reported "across all 2D
optimizations, except solvent ratio mode", described as "the region where minimal method
adjustments will not impact the method performance"; AutoChrom's robustness studies
"automatically vary flow rate, temperature, gradient, pH, buffer concentration, and solvent
ratio". **[derived]** ACD's MODR is a deterministic region on a point-estimate map; the
14-Aug repo's `CONTEXT.md` distinguishes a *predicted* design space (a hypothesis for
verification, with calibration state attached) from the *established* ICH Q14 object, and
measured that the probabilistic version collapses with peak count. Neither the benchmark nor
hplcsim's spec claims robustness today; SPEC §7's Rs 2.0 colour is a display convention.

---

## 4. Column Selector

**[verified]** The free web tool (ref. 5) selects "alternatives to a desired chromatographic
column, closely matched for retention and selectivity, based on the Tanaka chromatographic
parameters", compares two columns or one against the database, and states: "Columns that
possess low chromatographic discrimination factors to the original column (i.e., CDF <1)
will possess similar chromatographic properties." Weights per parameter are adjustable.
Ref. 1 (the suite's version): "Calculate similarity factor between columns with customizable
weights"; "Find most dissimilar columns for screening"; "Find most similar columns for
replacement"; radar graphs and dendrograms.

**[verified]** The 2010 user guide (ref. 15, a mirror on hplc.eu; PDF metadata 2010-07-26)
gives the six parameters with their test conditions — kPB (pentylbenzene retention),
αCH2 (hydrophobic selectivity), αT/O (steric), αC/P (hydrogen-bonding), αB/P at pH 7.6
(total silanols) and at pH 2.7 (acidic silanols) — states a database of 254 columns, and
says each parameter is z-scored across the database and "Euclidean distance is then used to
calculate the column difference factor (CDF)". **[verified]** A 2017 ACD poster (ref. 16):
"database of 340 columns" with parameters "provided by M.R. Euerby and P. Petersson";
distance is "weighed and scaled Euclidean"; hydrophobicity parameters weighted 2 "to mimic
PCA". **[verified]** Database growth: 153 → 187 (2006, ref. 32), 229 with ">3,400
experiments" (2008, ref. 38), 254 (2010), 340 (2017). **[could not verify]** Today's count;
the web tool's dropdown suggests a few hundred, not counted. **[could not verify]** Whether
the commercial suite lets a user add a column; the free tool does not.

**[verified]** Independent literature: Haghedooren et al. 2008 (ref. 28) state the Euerby
system "is now released as Column Selector by ACD/Labs" and found its ranking similar to the
KU Leuven F-value system on seven pharmaceutical separations; Jolliffe, Field, Euerby and
Petersson 2024 (ref. 29) add a positive-charge parameter and argue Euclidean distance over
the ten Tanaka parameters is the better similarity measure — i.e. the method is still being
extended by its authors outside ACD.

**[derived]** The open counterpart is the 14-Aug repo's finding: the 819-column HSM
database (`H, S*, A, B, C`, free CSV, **CC BY-NC-SA 3.0 US**) with the `Fs` distance
reproduces a shortlist offline; but `Fs` screens columns and never substitutes retention
constants, and `Fs`-nearest is not LSER-nearest (#36). Column Selector makes the same
limited claim ACD's page makes for it — similar or dissimilar *selectivity*, for screening
and replacement — and no claim about k. Both databases, and ACD's, are keyed by **commercial
column name**, which is the load-bearing fact for §8.4.

---

## 5. Property prediction, structure-based prediction, database

### 5.1 Property Predictor

**[verified]** Ref. 1: pKa, logP, logD at any pH, plus a long physicochemical list; "Graph
logD and percent ionization vs. pH to find the best pH for development", with colour-coded
regions. Ref. 9 (ACD/pKa): two algorithms, "ACD/pKa Classic" (training database ">26,000
compounds, representing >42,000 pKa values") and "GALAS" (">17,500 compounds representing
>20,000 ionization centers"); a reliability index "in ±log units"; no RMSE published on the
page. Ref. 10 (ACD/logD): logD from fragmental logP plus pKa-governed species distribution;
notes logD matters "for selection of the appropriate pH and separation columns".
**[verified]** The independent 2026 benchmark the 14-Aug repo cites (`ionisation-providers.md`,
JCIM 10.1021/acs.jcim.6c00107) compared ACD Classic and GALAS with open predictors and found
Uni-pKa "comparable (and, in two cases, significantly better)"; commercial tools keep the
coverage advantage (<1 % exceptions).

**[derived]** ACD positions this module as *starting-condition advice* — which pH, which
column class — not as retention prediction. That split matters for §8.6.

### 5.2 Structure → retention (ChromGenius lineage)

**[verified]** 2010 (ref. 33): ChromGenius "predicts retention times and chromatograms based
on the structures of the compounds to be separated"; "An add-on incorporating Absolv
parameters enhances prediction accuracy". Today (ref. 4): "Retention-Time Prediction ... from
behavior of structurally similar molecules" — a database-nearest-neighbour QSRR, retrained
on the user's own method database. Accuracy numbers in §6.3.

**[verified]** The 14-Aug repo's #5 finding bears directly here: 16.7 % of `E` and 22.1 % of
`B` Abraham descriptor "ground truth" values are ACD Absolv / ChemSketch / ClogP output, so a
structure-based stack graded against that corpus partly measures agreement with ACD's own
predictor. Its #28 ruling (internal, educational use) makes ACD an explicit *comparator*, as
long as "agrees with ACD to within X" is kept distinct from "accurate to within X".

### 5.3 Method database and the Table of Methods

**[verified]** Ref. 1: "Searchable, shareable method databases"; "Search by compound
structures, substructures, method details"; report templates. A separate product, the
Chromatography Applications Database (ref. 11), holds ">10,500 HPLC, GC, and CE separations"
with chromatogram, method (solvent, gradient, pH, column) and structure. **[derived]** Two
objects: a *library* of finished methods (v0.5's sharing problem, and a storage problem #103
already names), and the per-project *Table of Methods* of §3.2 (candidate history, unowned).

---

## 6. Published accuracy

### 6.1 LC Simulator, fitted models

| Source | Design | Reported error | Read as |
|---|---|---|---|
| Petersson et al. 2018, LCGC Europe (ref. 20) | Gradient → gradient, first-order, acids at pH 3 | \|Δtg\| < 0.2 % (second-order < 0.1 %); \|Δw\| and \|ΔRs\| < 3 %; 90th percentile | full text **[verified]** |
| same | Gradient → isocratic | 3–6 % (k < 3 worst); \|Δw\| < 13 %, \|ΔRs\| < 17 % | **[verified]** |
| same | Isocratic → isocratic, second-order, interpolation | \|ΔtR\| < 1 %; ~3× worse on extrapolation | **[verified]** |
| same, quoting the literature it builds on | Snyder and Dolan 2007 | \|Δtg\| < 1 %, \|Δw\| < 17 %, \|ΔRs\| < 10 % | **[verified]** |
| Petersson et al. 2014 app note, proteins (ref. 18) | 6 or 9 runs, gradient × temperature | interpolation < 1 %; extrapolation to shorter tG up to 2 % (RPC) and 10 % (IEC); multi-step gradients < 2 %; width < 22 % | full PDF **[verified]** |
| Haidar Ahmad et al. 2019, Analyst (ref. 21) | multi-column screening, "3D resolution maps" | ΔtR < 0.35 % | abstract **[verified]** |
| Haidar Ahmad et al. 2020, Anal. Chem. (ref. 22) | temperature, gradient, combined; RPLC and IEC | ΔtR < 1 % (abstract); < 0.35 % per ACD's summary | abstract **[verified]**; browser pass |
| Makey et al. 2021, Anal. Chem. (ref. 23) | 2D-LC; 2 × 2 or 3 × 3 (slope, temperature, column/eluent) | ΔtR < 3.5 % | abstract **[verified]** |
| Haidar Ahmad et al. 2021, Anal. Chem. (ref. 24) | ²D: tG, T, modifier blend, buffer conc. | < 0.5 % | abstract **[verified]** |
| Losacco et al. 2022 ×2 (refs. 25a, 25) | chiral screening; IEX salt/pH gradients | < 0.5 % | abstract **[verified]** |
| Hemida et al. 2024 (ref. 26) | **27-run 3 × 3 × 3**: T × tG × ACN:IPA ratio, 12 lipids | < 1 %, R² > 0.99 | full text **[verified]** |
| Manheim et al. 2024 (ref. 26b) | MS-compatible assay and purification | ΔtR < 7 % | abstract **[verified]** |
| Euerby et al. 2015, HILIC (ref. 19) | 2D isocratic and 1D gradient | "comparable to ... RPC retention modelling" | abstract; numbers paywalled **[could not verify]** |

**[derived]** Read together: inside the calibrated bracket, gradient-to-gradient prediction
lands at 0.1–1 % of tR whoever runs it; extrapolation and regime changes (gradient →
isocratic, shorter tG for proteins) cost 2–10 %. hplcsim's blind 0.42 % / 0.34 % (SPEC §1)
sits inside that band with two runs and one factor, and its §6 extrapolation and φ0 tiers
name the same regime boundaries the ACD literature reports errors across.

### 6.2 Where ACD has no number

**[verified]** No source gives a minimum run count, the suitability algebra, or a pH-axis
accuracy for LC Simulator. **[verified]** The methods paper's authors themselves cite a 2010
*Chromatography Today* paper (Euerby, Schad, Rieger, Molnár — the DryLab group) for
three-dimensional modelling, so in 2018 "3D" was not an ACD-specific claim; by 2024 a 27-run
3D LC Simulator build is in print (ref. 26).

### 6.3 Structure-based prediction (ChromGenius, QSRR with ACD tools)

| Source | Setting | Error | Read as |
|---|---|---|---|
| Tyrkkö et al. 2012 (ref. 12) | 486 drugs, urine screening; 118 isomers in 50 groups | correct order 68 % of groups; MAE 1.12 min, median 0.84 min; r² 0.85 | abstract **[verified]** |
| Gravell et al., ACD app note (ref. 13) | 1,453-compound training set, 103 pharmaceuticals test | mean error 6.6 % (6.2 % on the 50 most similar); 70 % within 1 min, 93 % within 2 min | full PDF **[verified]** |
| Szucs et al. 2021 (ref. 14), Pfizer | 24 compounds; QSRR built with ACD/Percepta, LC Simulator for T × tG | cross-validation RMSE 0.35–1.01 min, R² 0.976–0.987; 60 % of pairwise Rs within ±0.1 | full text **[verified]**; the accuracy is the authors' QSRR, not LC Simulator's |

**[derived]** An order of magnitude worse than fitted models (minutes, not tenths of a
percent), which is why ACD sells it as pre-injection method *selection* — the exact role the
14-Aug map assigns to a priori prediction ("choosing which experiments to run and supplying
peak-identity priors; fitting real injections delivers accuracy").

---

## 7. Placement against SPEC §11 and the 14-Aug repo

The table in §0 is the placement. What it shows, cycle by cycle **[derived]**:

- **v0.2** — done; the editor shape matches the benchmark's.
- **v0.3** — the benchmark's centre of gravity. Import, peak matching and n-run regression are
  one workflow in ACD and one cycle here. The open peak-matching research lives in the 14-Aug
  repo (#16) and is more ambitious than ACD's (a co-elution probability, not a bijection).
- **v0.4** — ACD's default second axis, four runs, sub-percent error in every paper. Cheap and
  accurate; weakly discriminating for elution order on public data (14-Aug #4/#11).
- **v0.5** — ACD's "shareable method databases" are the same object as colleague hosting; the
  Table of Methods is a smaller, per-project object with no owner in §11.
- **v0.6** — the axis ACD's own methods paper hedges on; the axis the 14-Aug repo found most
  discriminating (23–31 % order reversals) and worst supported by public data.
- **v0.7** — the driver's screenshot *is* a v0.7 map, over tG × T, with a composite colour
  hplcsim has already declined. The 14-Aug prototype is the stated target (SPEC §12).
- **v0.8** — two unrelated things bundled: a selectivity database (Column Selector ↔ HSM/WSU)
  and programme translation (LC Method Translator ↔ nothing yet). §8.5.
- **v0.9+** — two unrelated things bundled: pH advice from pKa/logD (cheap, open) and
  structure → retention (the whole 14-Aug stack, with its ground-truth caveat). §8.6.
- **Ahead of the benchmark** — provenance on t0 and dwell (rows 13); refusing a scalar
  objective (row 16); the extrapolation and φ0 tiers, which ACD's literature reports as error
  bands but the software does not surface as warnings **[could not verify** whether LC
  Simulator warns on extrapolation; no source describes it].

---

## 8. What the benchmark argues — recommendations to grill, not decisions

Each is a claim for the driver to attack. None amends SPEC.

**8.1 Keep v0.3 ahead of v0.4, and write its regression over *factors*, not over runs.** Every
ACD result in §6.1 is an n × m design fitted by one regression. If v0.3's "≥2-run regression"
is specified as a per-factor model (linear in φ now; 1/T later) combined numerically, v0.4
becomes two more levels of the same fitter rather than a second fitter. The methods paper's
model-selection rule — simplest model that passes a validation set; first-order extrapolates,
second-order does not — is a spec sentence hplcsim already half-has in §6 diagnostic 1.
*Grill:* does a generic factor regression pull v0.4 design decisions into v0.3 and break the
one-ticket-one-cycle rule?

**8.2 The v0.7 map need not wait for pH.** SPEC §12 says "the axes that make it worth drawing
are temperature (v0.4) and pH (v0.6), which is why §11 puts the map after both". The
benchmark's most-cited map — the driver's own screenshot, and refs. 21–26 — is **tG ×
temperature**, four runs. Once v0.4 lands, the 2D map has a live, cheap, accurate second axis;
pH would then be a *third* axis (ACD's "3D View"), not a precondition. *Grill:* is the reason
the map waits really pH, or is it #28's second gate — no dataset with a critical pair — which
no re-ordering fixes? If the latter, say so in §12 instead of naming pH.

**8.3 Keep temperature before pH, and say why in §11.** ACD's methods paper: pH models cover
narrow ranges and carry larger errors; no ACD paper publishes a pH-axis accuracy number. The
14-Aug repo: pH is the discriminating axis but public data cannot validate it and the `D`
term has never been fitted. Both say v0.6 is the hard cycle. *Grill:* should v0.6's "three-run
design" be re-examined against the methods paper's warning that peak shape and robustness
are worst near pKa — i.e. is the three-run design measuring the region a chromatographer
should avoid?

**8.4 Chemistry identity on a column profile (#103): a free-text phase name plus optional
part number, kept as a future join key, nothing else.** The benchmark's method panel names the
column as free text and holds chemistry in a separate module; that module, the open HSM
database and the WSU constants are all keyed by commercial column name. So the profile's
"chemistry identity" has one job in v0.8: to *join* to a selectivity record. A controlled
vocabulary ("C18", "phenyl") would be wrong-grained for that join and is what the USP
equivalency data already failed to be (#26). Do **not** put Tanaka, HSM or LSER parameters
on the profile: ACD's are proprietary, HSM is CC BY-NC-SA, and 14-Aug #36 shows `Fs`-nearest
is not retention-nearest. The seed records in `docs/research/seed/columns.csv` already carry
part number and vendor phrase — that is the identity. *Grill:* is a phase name without a
vocabulary "identity" at all, or just a label; and does anything in v0.3–v0.7 ever read it?

**8.5 Split v0.8: programme translation is not a selectivity database.** ACD ships method
translation as a free calculator (geometry, flow, gradient time, injection, dwell offset,
re-equilibration) with no chemistry in it, and the profiles map is about to give hplcsim
exactly the fields it needs (column geometry on the column profile, dwell on the instrument
profile). SPEC §6 diagnostic 6 already states the rule a translator would enforce (fitted S,
k0, N do not travel across flow or column). *Grill:* could "translate this programme to that
column and instrument profile" ride with the profiles build, years before a selectivity DB,
and would it be honest without the extra-column term (#101) it leaves out?

**8.6 Split v0.9+: pH advice is cheap and belongs beside v0.6; structure → retention is a
different effort.** ACD sells pKa/logD as *starting-condition* advice (a "% ionization vs.
pH" plot), and the open predictor (Uni-pKa) benchmarks level with ACD's. That is a small
feature that makes v0.6 usable — a chromatographer entering a pH axis needs to know where
the pKa is. Structure → retention is an order of magnitude less accurate (§6.3), graded
against a corpus partly made of ACD's own output (14-Aug #5), and is the 14-Aug repo's whole
programme. *Grill:* does "pKa advice" drag a molecule-structure input into an app whose
input contract (§4) is retention times only, and is that a scope change or a side panel?

**8.7 Name flow rate and ternary ratio in §11 as out, or park them.** ACD optimises both;
§11 says nothing. 14-Aug #12 ruled ternary out of its validated regime. One sentence in §2
or §11 closes the question. *Grill:* is flow rate really an axis, or a translator input
(8.5)?

**8.8 Give the candidate history an owner.** ACD's Table of Methods with "Generate Methods"
is the object #56 deferred and #29's two answers would populate (goal-seek, ceiling, plus
whatever the user pins). It is not a v0.5 sharing object; it is a v0.7 optimizer output.
*Grill:* is a held list of candidates a session-file concern (SPEC §8, inputs only — a
candidate is an input) or an output that is never serialised?

**8.9 No change: keep the two named answers over a composite, and keep provenance.** The
benchmark colours a product of six normalised criteria and types Dead Time without a stamp.
Both are places hplcsim's spec is deliberately different, and the 14-Aug repo independently
reached the same two positions (#19, #17). The benchmark does not argue against them.

---

## 9. Terms of use, and the pages that refused

### 9.1 Terms

**[verified]** ACD's terms live at `/terms-conditions/` (ref. 39; `/terms-of-use/` is 404),
titled "Terms & Conditions | ACD/Labs", legal entity Advanced Chemistry Development, Inc.,
governed by "the laws of Canada", no effective date shown. Operative clauses: "You agree not
to reproduce, duplicate, copy, sell, resell or exploit any portion of the Service, use of the
Service, or access to the Service ... without express written permission by us"; a
prohibited-uses section (13) that forbids using the site to "spider, crawl, or scrape"; a
trademark section (4) requiring ® / ™ marks when ACD software is referenced in
documentation. No personal-use or linking clause. **[verified]** `robots.txt` (ref. 40)
disallows crawlers from `/wp-content/uploads/download/autochrom/`, `/download/docs/whats-new/`,
`/download/freeware/`, `/download/macros/`, `/portal-resource/` and the yearly `uploads/2019–2022/`
folders, and allows `/wp-content/uploads/download/` and `/uploads/docs/` otherwise. Every
page read here is on an allowed path; the two application-note PDFs are under
`/uploads/download/app/chrom/` (allowed). The image the LC Simulator URL serves is under
`/uploads/2021/12/` (disallowed to crawlers) — it was reached by following the product URL,
not by crawling, and is not reproduced.

**[derived]** For hplcsim: ACD's terms forbid reproducing site content and forbid scraping;
they say nothing about reading. Describing features in one's own words with citation, as
this document does, is ordinary review; copying the Tanaka table, the suitability algebra,
screenshots or icons would not be. The 14-Aug repo's #28 licence ruling (internal and
educational use) does not change this — it governs data, not ACD's site.

### 9.2 URLs that refused an ordinary fetch, and what was done

| URL | First pass | Second pass |
|---|---|---|
| `acdlabs.com/products/spectrus-platform/method-selection-suite/lc-simulator/` | HTTP 200 **image/png** — resolves to `wp-content/uploads/2021/12/LC-Simulator.png`, a screenshot of the Optimizations window in 3D mode; there is no LC Simulator sub-page | none; described in §2.3 and §3.1, not reproduced |
| `.../method-selection-suite/{column-selector, gc-simulator, peak-tracker, property-predictor, method-database, chromgenius}/` | HTTP 404 (all six, `curl`) | none; Column Selector lives at `/resources/free-chemistry-software-apps/column-selector/` (200) |
| `acdlabs.com/terms-of-use/` | 404 | terms found via `page-sitemap.xml` at `/terms-conditions/` |
| `acdlabs.com/products/com_iden/meth_dev/lc_sim/` (the 2018 paper's citation) | 404 | none |
| `pubs.rsc.org/.../d4gc04300f` | 403 | **read with headed Chromium** (driver's instruction): abstract only, full text paywalled |
| `americanpharmaceuticalreview.com/...ACD-Method-Selection-Suite/` | 403 | **read with headed Chromium**: product listing (§1.1) |
| `chromforum.org/viewtopic.php?t=12721` | 403 | **read with headed Chromium**: a 2010 thread; nothing about LC Simulator's internals beyond one moderator's view that all commercial modellers "are basically interpolation programs"; not cited for facts |
| `chromatographyonline.com/view/practical-approach-modelling-...` | 403 | **read with headed Chromium**: the LC Simulator methods paper (ref. 20, §2.2, §6.1) |
| `pubs.acs.org/doi/10.1021/acs.analchem.0c02807` and `.0c03680` | not tried by ordinary fetch (publisher) | abstracts via Europe PMC REST; landing pages also read on the browser pass, abstracts only |
| `pubmed.ncbi.nlm.nih.gov/33301312/` | cookie wall | Europe PMC REST |
| `api.semanticscholar.org` | 429 after one call | Crossref and Europe PMC used instead |
| `sciencedirect.com` (two 2005/2008 articles), `chromatographytoday.com`, `support.revvitysignals.com`, `link.springer.com/10.1007/s12247-009-9058-2` | 403 / redirect loop (literature sweep) | none |
| ACD webinar resource pages (refs. 41–43) | 200, but abstracts only; recordings on YouTube | not watched |
| ACD "portal-resource" GSK training | gated | none |

The headless-shell Chromium build was challenged by Cloudflare on every publisher page
("Just a moment…"); only a headed full Chromium (`chromium-1223`, Playwright) passed. That
distinction is itself a finding for the next research ticket that meets a publisher wall.

---

## 10. What I could NOT verify

- The suitability normalisation and aggregation algebra (§3.1) — inferred from two
  screenshots; no document states it.
- Any minimum or recommended run count stated by ACD for LC (§2.1) — only the literature's
  rules (two gradients at 3×, 2 × 2 with temperature).
- Whether LC Simulator warns on extrapolation outside the calibrated runs, or on a candidate
  φ0 different from the runs' (§7) — no source describes the software's diagnostics.
- The peak-matching algorithm's basis (§2.5) beyond "UV-Mutual" and "UV or MS spectra".
- Today's Column Selector database size and whether the commercial module accepts user
  columns (§4).
- Whether ChromGenius is still separately licensed, and how "Retention-Time Prediction" is
  trained on a user's method database (§5.2).
- Any pH-axis accuracy number for LC Simulator (§2.3, §6.2).
- HILIC accuracy numbers (ref. 19, paywalled); the Green Chemistry paper's methods (ref. 27b,
  paywalled; ACD's blog summary of it was not treated as a source for numbers).
- The Revvity acquisition's close date (ref. 37 announces the agreement only).
- Version 2024/2025 release-note PDFs — the `whats-new` folder is disallowed to crawlers and
  was not fetched.

---

## 11. Sources

All accessed 2026-09-06. **Browser pass** marks the four pages read with headed Chromium on
the driver's instruction (§9.2). Items marked *(sweep)* were read by a delegated literature
sweep in this session using the same ordinary-fetch posture; abstract-level reads are marked.

**ACD/Labs pages and documents**

1. Method Selection Suite product page — https://www.acdlabs.com/products/spectrus-platform/method-selection-suite/ — read.
2. Method Selection Suite, current software version (2025) — https://www.acdlabs.com/technical-support/current-software-versions/method-selection-suite/ — read.
3. `.../method-selection-suite/lc-simulator/` — resolves to https://www.acdlabs.com/wp-content/uploads/2021/12/LC-Simulator.png — an image; viewed, not reproduced.
4. AutoChrom product page — https://www.acdlabs.com/products/spectrus-platform/autochrom/ — read; AutoChrom version 2025 — https://www.acdlabs.com/technical-support/current-software-versions/autochrom/ — read.
5. Column Selector, free web tool — https://www.acdlabs.com/resources/free-chemistry-software-apps/column-selector/ — read; resource page https://www.acdlabs.com/resource/column-selector-web-tool/ — read (Quick Start Guide PDF linked, not fetched).
6. LC Method Translator, free web tool — https://www.acdlabs.com/resources/free-chemistry-software-apps/lc-method-translator/ — read.
7. LC/GC method development solutions page — https://www.acdlabs.com/solutions/developing-and-optimizing-lc-and-gc-methods/ — read.
8. Supported data formats — https://www.acdlabs.com/technical-support/supported-data-formats/ — read.
9. ACD/pKa (Percepta) — https://www.acdlabs.com/products/percepta-platform/physchem-suite/pka/ — read.
10. ACD/logD (Percepta) — https://www.acdlabs.com/products/percepta-platform/physchem-suite/logd/ — read.
11. Chromatography databases — https://www.acdlabs.com/products/spectrus-platform/chromatography-databases/ — read.
12. Tyrkkö E., Pelander A., Ojanperä I., *Anal. Chim. Acta* 720 (2012) 142–148, doi:10.1016/j.aca.2012.01.024 — abstract via Europe PMC *(sweep)*.
13. Gravell A., Mills G. A., Binnington M. J., "UHPLC Retention Time Prediction Using ACD/ChromGenius…", ACD/Labs application note — https://www.acdlabs.com/wp-content/uploads/download/app/chrom/appnote_chrom_uhplc-retention-time-prediction-using-chromgenius.pdf — full PDF *(sweep)*.
14. Szucs R., Brown R., Brunelli C., Heaton J. C., Hradski J., *Int. J. Mol. Sci.* 22 (2021) 3848, doi:10.3390/ijms22083848 — full text via PMC8068189 *(sweep)*.
15. ACD/Column Selector user guide (PDF metadata 2010-07-26), mirror — https://www.hplc.eu/Downloads/ACD_Column_Selector.pdf — full PDF *(sweep)*.
16. Kassam K., Tsarev D., Euerby M., "Tanaka-parameter based approach for chromatographic column selection…", poster (c. 2017), mirror — https://cdn.technologynetworks.com/ep/pdfs/tanaka-parameter-based-approach-for-chromatographic-column-selection-how-to-locate-k-columns-with.pdf — full PDF *(sweep)*.
17. Brunelli C., Bains B., "Improving Method Transfer Outcomes: Pfizer's Approach…", ACD/Labs application note — https://www.acdlabs.com/wp-content/uploads/download/app/chrom/appnote-improving-method-transfer-outcomes-pfizers-approach-with-method-development-software.pdf — full PDF *(sweep)*.
18. Petersson P., Munch J., Euerby M. R., Vazhentsev A., McBrien M., Bhal S. K., Kassam K., "Adaption of Retention Models to Allow Optimization of Peptide and Protein Separations", ACD/Labs application note (also *Chromatography Today* 7 (2014) 15–18) — https://theanalyticalscientist.com/media/u5whow2y/acdlabs-app-note-6-supplied.pdf — full PDF *(sweep)*.
19. Euerby M. R., Hulse J., Petersson P., Vazhentsev A., Kassam K., *Anal. Bioanal. Chem.* 407 (2015) 9135–9152, doi:10.1007/s00216-015-9079-2 — abstract *(sweep)*.
20. Petersson P., Boateng B. O., Field J. K., Euerby M. R., "A Practical Approach to Modelling of Reversed-Phase Liquid Chromatographic Separations: Advantages, Principles, and Possible Pitfalls", *LCGC Europe* 31(3), 1 March 2018 — https://www.chromatographyonline.com/view/practical-approach-modelling-reversed-phase-liquid-chromatographic-separations-advantages-principles — **browser pass**, full text; ACD's landing page for it https://www.acdlabs.com/resource/a-practical-approach-to-modelling-of-reversed-phase-liquid-chromatographic-separations-advantages-principles-and-possible-pitfalls/ — read.

**Peer-reviewed users of LC Simulator (Merck, Amgen and others)**

21. Haidar Ahmad I. A. et al., *Analyst* 144 (2019) 2872–2880, doi:10.1039/c8an02499e — abstract *(sweep)*.
22. Haidar Ahmad I. A., Shchurik V., Nowak T., Mann B. F., Regalado E. L., *Anal. Chem.* 92 (2020) 13443–13451, doi:10.1021/acs.analchem.0c02807 — abstract via Europe PMC; landing page **browser pass**.
23. Makey D. M. et al., *Anal. Chem.* 93 (2021) 964–972, doi:10.1021/acs.analchem.0c03680 — abstract via Europe PMC.
24. Haidar Ahmad I. A. et al., *Anal. Chem.* 93 (2021) 11532–11539, doi:10.1021/acs.analchem.1c01970 — abstract *(sweep)*.
25. Losacco G. L. et al., *Anal. Bioanal. Chem.* 414 (2022) 3581–3591, doi:10.1007/s00216-022-03982-z — abstract *(sweep)*; 25a. Losacco G. L. et al., *Anal. Chem.* 94 (2022) 1804–1812, doi:10.1021/acs.analchem.1c04585 — abstract *(sweep)*.
26. Hemida M. et al., *ACS Pharmacol. Transl. Sci.* 7 (2024) 3108–3118, doi:10.1021/acsptsci.4c00306 — full text via PMC11480893 *(sweep)*; 26b. Manheim J. et al., *Anal. Bioanal. Chem.* 416 (2024) 1269–1279, doi:10.1007/s00216-023-05118-3 — abstract *(sweep)*.
27. American Pharmaceutical Review, "ACD/Method Selection Suite from ACD/Labs — Product Description" — https://www.americanpharmaceuticalreview.com/26758-Pharmaceutical-Software/16618112-ACD-Method-Selection-Suite/ — **browser pass**; 27b. Handlovic T. T., Roy D., Farooq M. Q., Mazzi Leme G., Crossley K., Haidar Ahmad I. A., *Green Chem.* 27 (2025) 109–119, doi:10.1039/d4gc04300f — Crossref metadata; abstract **browser pass** (https://pubs.rsc.org/en/content/articlelanding/2024/gc/d4gc04300f).
28. Haghedooren E. et al., *J. Chromatogr. A* 1189 (2008) 59–71, doi:10.1016/j.chroma.2008.02.012 — abstract *(sweep)*.
29. Jolliffe S., Field J. K., Euerby M. R., Petersson P., *J. Chromatogr. A* 1730 (2024) 465059, doi:10.1016/j.chroma.2024.465059 — accepted manuscript, Strathprints *(sweep)*.

**Naming history and corporate**

30. Pittcon 2002 abstracts, *J. Autom. Methods Manag. Chem.* 24(5), PMC2562965 — full text *(sweep)*.
31. R&D World, "ACD/LC Simulator 8.0", 31 January 2004 — https://www.rdworldonline.com/acd-lc-simulator-8-0/ *(sweep)*.
32. Technology Networks, Column Selector update, 5 July 2006 — https://www.technologynetworks.com/tn/product-news/acdlabs-announces-update-to-acdcolumn-selector-214664 *(sweep)*.
33. SelectScience, ACD/Labs at HPLC 2010, 13 June 2010 — https://www.selectscience.net/article/acd-labs-to-showcase-software-products-that-facilitates-quality-by-design-for-chromatographic-method-development-and-optimization-at-hplc-2010 — read.
34. ACD/Labs, Spectrus DB release completes the platform (18 March 2013) — https://www.acdlabs.com/resource/acd-spectrus-db-release-completes-acd-labs-next-generation-cheminformatics-platform/ *(sweep)*.
35. Technology Networks, "ACD/Labs' Version 2012 Chromatography Software…", 15 June 2012 — https://www.technologynetworks.com/analysis/product-news/acdlabs-version-2012-chromatography-software-continues-to-address-the-challenge-of-method-development-214677 — read.
36. Lab Manager, ACD/Labs v2018.1 — https://www.labmanager.com/acd-labs-announces-v-2018-1-software-updates-3266 *(sweep)*.
37. ACD/Labs, "Revvity to acquire ACD/Labs…", 10 November 2025 — https://www.acdlabs.com/resource/revvity-to-acquire-acd-labs-to-expand-its-signals-software-capabilities/ *(sweep)*.
38. Scientific Computing World, Column Selector update (c. 2008) — https://www.scientific-computing.com/press-releases/acdcolumn-selector-update *(sweep)*.

**Terms and site structure**

39. ACD/Labs, *Terms & Conditions* — https://www.acdlabs.com/terms-conditions/ — read.
40. https://www.acdlabs.com/robots.txt, https://www.acdlabs.com/sitemap.xml, https://www.acdlabs.com/page-sitemap.xml — read.

**Webinar landing pages (abstracts only)**

41. https://www.acdlabs.com/resource/practical-method-development-for-todays-analytical-scientist/ (2025 series; YouTube playlist linked, not watched).
42. https://www.acdlabs.com/resource/retention-modelling-principles-advantages-and-potential-pitfalls-to-avoid/ (J. Field, Shimadzu).
43. https://www.acdlabs.com/resource/in-silico-mapped-separation-spaces-for-green-method-development/ (T. Handlovic, Amgen).

**Repository context (read, not sources for ACD claims)**

- This repo: `SPEC.md` §1, §2, §4, §6, §7, §11, §12; `CONTEXT.md`; `docs/research/vendor-column-and-instrument-data.md`, `github-hplc-simulators.md`; issues #56, #103, #28, #29, and the 2026-09-06 comments on #104 and #105.
- 14-Aug repo (`/Users/maracchi/Desktop/Claude/14-Aug-2026 HPLC Simulator`, `zhipengzhu1-dotcom/14-August-2026`): map #1 and its Notes; `CONTEXT.md`; `research/ionisation-providers.md`, `lser-system-constants.md`, `abraham-ground-truth.md` (#5), `hsm-lser-bridge.md` (#8), `instrument-layer.md` (#9), `retention-datasets.md` (#4), `qspr-approaches.md` (#6), `marchetto-baseline.md` (#2); decisions #10, #11, #12, #16, #17, #19, #24, #28, #34, #36 as recorded on the map.
- The driver's screenshot: `Front-End Design/Screenshot 2026-08-14 at 9.46.30 PM.png` (local, untracked).
