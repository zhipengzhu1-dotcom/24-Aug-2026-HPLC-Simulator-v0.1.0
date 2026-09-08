# Viscosity of Water–Methanol Mixtures Against Composition and Temperature

Research for issue #149. Purpose: the same pressure-scaling rule as the
water–acetonitrile document (`P ∝ Q·η`, pressure across a packed bed
proportional to flow rate × mobile-phase viscosity) but for methanol as
organic modifier — giving it the composition- and temperature-dependence of
viscosity, η(φ,T), needed to scale a recorded scouting-run pressure to a
candidate run at a different flow rate, starting composition, or column
temperature. φ is the methanol (MeOH) volume fraction, 0–1, per this repo's
unit convention (`CLAUDE.md`: "φ is a fraction 0–1 internally; %B 0–100
exists only at entry/display boundaries").

This pass located one primary paper whose full numeric dataset is openly
deposited in NIST's ThermoML Archive (the same US-government-hosted,
`.gov`, open data-deposit program that supplied the backbone of the sibling
water–acetonitrile document) and retrieved it directly. Every other
candidate paper named in the ticket, plus several more found in this pass,
was checked against ThermoML, Unpaywall, and (where those failed) a
stealth-browser fetch of the publisher's abstract page — and confirmed
either closed-access, absent from ThermoML, or (for two of them) readable
only as a freely-available abstract with no extractable numeric table. All
numbers below trace to the one open dataset, to NIST's own water viscosity
reference correlation, or to computations performed in this task from those
two; everything else is explicitly flagged as not found or not accessible.

**Bottom line.** Full composition range (13 points spanning x(MeOH) = 0 → 1)
is measured at **three temperatures, 20–30 °C in 5 °C steps** — this is a
**narrower** temperature band than both the ticket's 25–60 °C minimum ask
and the sibling ACN document's 25–45 °C. No primary source located in this
pass gives a single numeric water+methanol mixture viscosity point above
30 °C. A degree-4 polynomial in φ fits each isotherm with a residual
(≤1.03% of the measured value) comparable to the data's own stated
measurement uncertainty (~1.2–1.6%, 95% confidence). The composition effect
is large and now quantified directly: viscosity peaks at **φ(MeOH) ≈ 0.49
(x(MeOH) ≈ 0.30, on this composition grid)**, roughly **68–79% above pure
water** at the same temperature — several times the size of the analogous
ACN effect (~10%). Two high-pressure viscometry papers (Isdale, Easteal &
Woolf 1985; Tanaka, Matsuda, Fujiwara, Kubota & Makita 1987) were reached as
free abstracts via a stealth-browser pass and independently corroborate both
the location of the maximum (mole fraction 0.3–0.4) and its qualitative
shift with temperature, but their full data tables remain paywalled and no
number from either is used in the quantitative sections below. Modifier
(formic acid/TFA) viscosity data was not found, exactly as in the sibling
pass.

---

## 1. Question

What are the viscosities of water–methanol mixtures across composition
(0–100% MeOH by volume) and temperature (25–60 °C at minimum, 80 °C if
sources allow), from primary sources, in a form a pressure-scaling rule can
use? Pressure across a packed bed is proportional to flow × viscosity, so
scaling a recorded scouting pressure to a candidate at another flow, start
composition, or temperature needs η(φ,T). Also: does adding 0.1% formic
acid or a similar low-level acidic modifier (e.g. 0.1% TFA) change viscosity
by an amount that matters for pressure prediction, or is it negligible?

---

## 2. Sources

| Source | Type | What it provides | Access notes |
|---|---|---|---|
| B. González, N. Calvar, E. Gómez, Á. Domínguez, "Density, dynamic viscosity, and derived properties of binary mixtures of methanol or ethanol with water, ethyl acetate, and methyl acetate at T = (293.15, 298.15, and 303.15) K," *J. Chem. Thermodyn.* **39** (2007) 1578–1588. DOI: [10.1016/j.jct.2007.05.004](https://doi.org/10.1016/j.jct.2007.05.004) | **Primary** | Measured density and viscosity of water+methanol (and, separately, water+ethanol and two ester+alcohol pairs, not used here) over the **whole composition range** (13 mole fractions, x(water) = 0 to 1) at **three temperatures**: 293.15, 298.15, 303.15 K (20, 25, 30 °C). This is the numeric source for essentially all of §3 below. | **The journal article itself (Elsevier ScienceDirect) is presumed paywalled — not separately checked in this task** (not one of the papers named in the ticket, so no dedicated Unpaywall check was spent on it). **Its full numeric dataset was retrieved directly from the NIST ThermoML Archive** (`trc.nist.gov/ThermoML/10.1016/j.jct.2007.05.004.xml`, HTTP 200, no login) — the same standing, `.gov`-hosted, open data-deposit program used in the sibling ACN document, since *J. Chem. Thermodyn.* is a ThermoML "cooperating journal." Found in this pass by querying CrossRef for candidate methanol+water viscosity papers in ThermoML-cooperating journals (J. Chem. Eng. Data, J. Chem. Thermodyn., Fluid Phase Equilibria, Int. J. Thermophys.) and then probing each candidate DOI directly against the ThermoML URL pattern — not found via the ticket's named candidate list, none of which turned out to be the ThermoML hit. |
| A. M. Katti, N. E. Tarfulea, C. J. Hopper, K. R. Kmiotek, "Prediction of Viscosity−Temperature−Composition Surfaces in a Single Expression for Methanol−Water and Acetonitrile−Water Mixtures," *J. Chem. Eng. Data* **53** (2008) 2865–2872. DOI: [10.1021/je800607j](https://doi.org/10.1021/je800607j) | **Primary** | By title, exactly the reusable published η(T,composition) correlation this ticket asked to look for, for exactly this binary system (and, per its title, also ACN-water — matching the sibling document's finding). | **Confirmed closed on every route tried, independently re-checked for this ticket rather than assumed from the sibling document.** CrossRef metadata confirms the citation. Unpaywall: `is_oa: false`, `oa_status: closed`, no open location. **NIST ThermoML Archive**: `trc.nist.gov/ThermoML/10.1021/je800607j.xml` → HTTP 404 (checked fresh in this pass, same negative result as the sibling ACN pass). ACS article page (`pubs.acs.org/doi/10.1021/je800607j`): a stealth-browser fetch (Chrome, `playwright-stealth`) still returned HTTP 403 with a Cloudflare "Performing security verification" challenge page — confirms this is a bot-management block, not merely a scripted-fetch quirk, and that even a stealth pass does not get past it. ACS Supporting Information PDF (`pubs.acs.org/doi/suppl/10.1021/je800607j/suppl_file/je800607j_si_001.pdf`): plain fetch, HTTP 403. **This remains the single most consequential inaccessible source**, exactly as in the sibling document. |
| S. Z. Mikhail, W. R. Kimel, "Densities and Viscosities of Methanol-Water Mixtures," *J. Chem. Eng. Data* **6** (1961) 533–537. DOI: [10.1021/je60011a015](https://doi.org/10.1021/je60011a015) | **Primary** | Classic early reference, by title exactly on this system. DOI located via CrossRef bibliographic search (the ticket did not supply one). | **Confirmed closed.** Unpaywall: `is_oa: false`, `oa_status: closed`. Not deposited in NIST ThermoML (`.../10.1021/je60011a015.xml` → HTTP 404; 1961 predates ThermoML's typical coverage). No number used from this paper — referenced only because it is cited (as "J. Chem. Eng. Data 6:644 (1961)", an apparent page-number transcription error in that citing paper's own reference list, vs. the correct 533–537 confirmed by CrossRef) in the reference list of Isdale et al. 1985 below. |
| J. D. Isdale, A. J. Easteal, L. A. Woolf, "Shear viscosity of methanol and methanol + water mixtures under pressure," *Int. J. Thermophys.* **6** (1985) 439–450. DOI: [10.1007/BF00508889](https://doi.org/10.1007/BF00508889) | **Primary** | Found via CrossRef search for "Kubota methanol water viscosity" (the ticket's under-specified "Kubota, various" lead — see next row) and independently via a direct methanol+water CrossRef sweep. Free abstract (obtained via stealth-browser pass, see §9) states: pure methanol viscosity measured up to 400 MPa at **298, 313, and 323 K** (25, 40, 50 °C); methanol+water mixtures measured (a) at 0.1 MPa and **278 K** (5 °C — below this document's range) and (b) up to 300 MPa at **298 K only**. So even with full-text access, this paper's *mixture* composition-vs-temperature coverage would not extend past what González et al. 2007 already supplies (298 K / 25 °C is the only mixture isotherm, and it duplicates rather than extends). Its pure-methanol points at 40/50 °C are potentially useful for the φ=1 endpoint but are inside the paywalled full text. | **Confirmed closed** (Unpaywall: `is_oa: false`). Not in ThermoML (`.../10.1007/BF00508889.xml` → HTTP 404). A plain `WebFetch` of the Springer abstract page redirected to a Springer login page (`idp.springer.com/authorize...`); a **stealth-browser pass** (`playwright` + `playwright-stealth`, `chromium.launch(channel="chrome")`) reached the same URL directly with HTTP 200 and the abstract text rendered normally — this was a scripted-fetch/cookie-consent quirk, not a bot-block, unlike the ACS case above. Full text still shows only "This is a preview... log in via an institution to check access" — no numeric table obtained from this paper. |
| Y. Tanaka, Y. Matsuda, H. Fujiwara, H. Kubota, T. Makita, "Viscosity of (water + alcohol) mixtures under high pressure," *Int. J. Thermophys.* **8** (1987) 147–163. DOI: [10.1007/BF00515199](https://doi.org/10.1007/BF00515199) | **Primary** | This is very likely the paper the ticket's under-specified "Kubota, various... on methanol-water excess viscosity" lead was pointing at (H. Kubota is a co-author). Free abstract (stealth-browser pass) states: aqueous methanol, ethanol, 1-propanol, 2-propanol, and *t*-butyl alcohol, **283–348 K (10–75 °C)**, pressures up to 120 MPa, falling-cylinder viscometer, uncertainty <2%. Abstract text explicitly states **"a distinct maximum appears near 0.3–0.4 mole fraction of alcohol on all isobars at each temperature. The viscosity maximum shifts gradually to a higher alcohol concentration with increasing temperature and pressure."** This is an independent, if qualitative-only, corroboration of both the location and the temperature-shift of the maximum reported quantitatively in §3.3/§6 below. Its temperature range (up to 75 °C) would, if the full tables were obtainable, be the single best fix for this document's temperature-coverage gap. | **Confirmed closed** (Unpaywall: `is_oa: false`). Not in ThermoML (`.../10.1007/BF00515199.xml` → HTTP 404). Same login-redirect-vs-stealth-pass pattern as Isdale 1985: plain fetch redirected to Springer login, stealth pass reached the abstract (HTTP 200) but full text remains "preview... log in via an institution." **No numeric table obtained** — only the abstract's qualitative statements are used, and only where explicitly attributed as such (§6). |
| J. W. Thompson, T. J. Kaiser, J. W. Jorgenson, "Viscosity measurements of methanol–water and acetonitrile–water mixtures at pressures up to 3500 bar using a novel capillary time-of-flight viscometer," *J. Chromatogr. A* **1134** (2006) 201–209. DOI: [10.1016/j.chroma.2006.09.006](https://doi.org/10.1016/j.chroma.2006.09.006) | **Primary** | PubMed abstract (PMID 16996532, fetched via NCBI E-utilities `efetch`, freely readable) confirms: methanol–water and acetonitrile–water mixtures in **"decade volume % increments"** — i.e., the full 0–100% v/v range in 10% steps, reported directly in volume fraction rather than mole fraction — at **25 °C**, atmospheric pressure up to 3500 bar, cross-validated against Bridgman falling-body viscometers. Directly on-topic and unusually convenient (reports composition the same way this app's φ convention does), but only a single temperature. | **Confirmed closed.** Unpaywall: `is_oa: false`, `oa_status: closed`, no open location — re-checked independently in this pass (not assumed from the sibling document, which flagged the same DOI as an untried lead). NIST ThermoML: `.../10.1016/j.chroma.2006.09.006.xml` → HTTP 404 (*J. Chromatogr. A* is not typically a ThermoML-cooperating journal). No numeric table obtained — the abstract statement above is the only content used, and it is not itself a source of any tabulated number in §3. |
| M. Dizechi, E. Marschall, "Viscosity of some binary and ternary liquid mixtures," *J. Chem. Eng. Data* **27** (1982) 358–363. DOI: [10.1021/je00029a039](https://doi.org/10.1021/je00029a039) | **Primary** | Found via CrossRef search; a widely-cited classic reference for water+methanol (and other common HPLC-solvent) viscosity across a wide temperature range, often cited secondhand in chromatography textbooks. | **Confirmed closed** (Unpaywall: `is_oa: false`). Not in ThermoML (`.../10.1021/je00029a039.xml` → HTTP 404; predates typical ThermoML deposit coverage, like Mikhail & Kimel 1961). No number used. |
| K. Noda, M. Ohashi, K. Ishida, "Viscosities and densities at 298.15 K for mixtures of methanol, acetone, and water," *J. Chem. Eng. Data* **27** (1982) 328–331. DOI: [10.1021/je00029a028](https://doi.org/10.1021/je00029a028) | **Primary** | A *ternary* system (methanol + acetone + water); its binary methanol+water edge, if extractable, would be a single-temperature (25 °C) cross-check. | **Confirmed closed** (Unpaywall: `is_oa: false`). Not in ThermoML (`.../10.1021/je00029a028.xml` → HTTP 404). Not pursued further given it is single-temperature and ternary. |
| NIST Chemistry WebBook, water (CAS 7732-18-5), fluid-properties calculator, IAPWS-2008 viscosity formulation, 1 bar | **Primary/authoritative reference correlation** (a formulation fit to a large body of primary data by international agreement, not a new lab measurement) | Pure-water η(T), the φ=0 endpoint, fetched directly at `webbook.nist.gov` for 25–80 °C — **independently re-fetched in this pass** rather than only reused from the sibling document, per the ticket's instruction. | Fully open, fetched directly, no login. The re-fetched values agree with the sibling document's cited table to within ≤0.0003 mPa·s (≤0.03%) at every temperature — see §3.1 for both tables and a note on the small discrepancy's likely cause (a temperature-grid quantization artifact in this pass's query, not a data disagreement). Uncertainty of the underlying IAPWS-2008 formulation itself was not retrieved from the standard (Huber et al., *J. Phys. Chem. Ref. Data* **38** (2009) 101–125) in this pass either — same gap as the sibling document (§8). |
| NIST Chemistry WebBook, methanol (CAS 67-56-1), compound page and fluid-properties calculator | Checked as a candidate for a free reference-correlation, per the ticket's instruction to check whether one exists for methanol as it does for water | — | **Confirmed absent**, matching the sibling ACN document's finding for acetonitrile. The methanol compound page states viscosity data is not present on the free WebBook page and points to the subscription-only "NIST/TRC Web Thermo Tables, professional edition." Methanol is not part of IAPWS's scope (IAPWS covers only H₂O), so no free international reference correlation of that kind exists for it either. |
| PubChem CID 887 (methanol), `Viscosity` property, citing Haynes, W. M. (ed.), *CRC Handbook of Chemistry and Physics*, 95th ed. (2014–2015), p. 6-231, and ILO-WHO ICSC Card No. 0057 | **Tertiary compilation** | Pure-methanol viscosity, single point: 0.544 mPa·s at 25 °C. | Retained only as a cross-check against González et al. 2007's own measured pure-methanol point (0.545 mPa·s at 25 °C, §3.2) — the two agree to within 0.2%. Not used as a primary number. |
| Ch. Wohlfarth, "Viscosity of the mixture (1) water; (2) methanol," in *Landolt-Börnstein — Group IV Physical Chemistry, Supplement to IV/18* (Springer, 2008). DOI: [10.1007/978-3-540-75486-2_441](https://doi.org/10.1007/978-3-540-75486-2_441); reissued as Ch. Wohlfarth, "Viscosity of the binary liquid mixture of water and methanol," in *Viscosity of Pure Organic Liquids and Binary Liquid Mixtures* (Springer, 2017). DOI: [10.1007/978-3-662-49218-5_454](https://doi.org/10.1007/978-3-662-49218-5_454) | **Secondary** (critically evaluated compilation; standard Landolt-Börnstein practice is to fit a recommended smoothing equation to pooled primary data and report each source's deviation from it) | Would very likely fold in González et al. 2007, Mikhail & Kimel 1961, Dizechi & Marschall 1982, Isdale et al. 1985, and Tanaka et al. 1987, plus a recommended correlation with a stated fit quality across a wider temperature range than any single primary paper found here. | **Not opened in this pass** (Springer book chapters, expected paywalled, not separately fetched — the stealth pass used for the two *Int. J. Thermophys.* abstracts above was not spent here since it was judged more likely to hit the same subscription wall with no free abstract, and the ticket asks for one target site per script). Flagged as the single most promising next fetch for someone with institutional access — see §7. |
| Chen–Horváth or other named "ready-made" correlation candidates | — | The sibling document could not establish that a "Chen–Horváth" viscosity correlation exists under that name; no equivalent named-correlation candidate was supplied in this ticket, and none was found in this pass's searches beyond Katti et al. 2008 (above). | Not applicable — no further claim made. |

---

## 3. Data

All numbers in this section trace to two fetches: NIST's ThermoML XML for
`10.1016/j.jct.2007.05.004` (González, Calvar, Gómez & Domínguez 2007), and
NIST's Chemistry WebBook fluid-properties calculator for water. The
mole-fraction→volume-fraction conversion, the excess-volume computation, and
the polynomial fits and residuals (§3.3, §4) were all computed directly in
this task from the ThermoML numbers, with the arithmetic shown reproducible
from the tables below.

### 3.1 Pure water, η(T), 25–80 °C — the φ=0 endpoint

Source: NIST Chemistry WebBook, water (CAS 7732-18-5), IAPWS-2008 viscosity
formulation, 1 bar. Re-fetched independently in this pass.

| T (°C) | η (mPa·s), this pass | η (mPa·s), sibling document's table | Difference |
|---|---|---|---|
| 25.0 | 0.88982 | 0.89002 | 0.02% |
| 30.0 | 0.79705 | 0.79722 | 0.02% |
| 35.0 | 0.71898 | 0.71913 | 0.02% |
| 40.0 | 0.65261 | 0.65273 | 0.02% |
| 45.0 | 0.59566 | 0.59577 | 0.02% |
| 50.0 | 0.54642 | 0.54652 | 0.02% |
| 55.0 | 0.50354 | 0.50362 | 0.02% |
| 60.0 | 0.46596 | 0.46603 | 0.02% |
| 65.0 | 0.43284 | 0.43290 | 0.01% |
| 70.0 | 0.40349 | 0.40355 | 0.01% |
| 75.0 | 0.37737 | 0.37742 | 0.01% |
| 80.0 | 0.35401 | 0.35405 | 0.01% |

The two columns are two independent fetches of the same underlying NIST
IAPWS-2008 formulation, not two different data sources — the ≤0.02%
difference is attributed to the WebBook's isobar-table query snapping the
requested temperature to a slightly offset internal grid point (this pass's
query returned nominal temperatures reading e.g. "25.010 °C" rather than
exactly "25.000 °C") rather than to any disagreement in the underlying
correlation. It is far smaller than any other uncertainty in this document
and is not treated as a finding.

Method: not a single lab measurement — NIST's implementation of the
IAPWS-2008 international reference formulation, itself fit to a large body
of primary measurements the WebBook page does not enumerate. Uncertainty:
not retrieved (see §2, §8).

**Cross-check.** González et al. 2007's own measured pure-water point
(x(water)=1, the mixture-series endpoint) reads 1.003, 0.890, 0.797 mPa·s at
20/25/30 °C — agreeing with the NIST/IAPWS table above to within 0.1% at
both overlapping temperatures (25 and 30 °C). Two independent sources
agreeing, not one source repeated.

### 3.2 Pure methanol, η(T), 20–30 °C — the φ=1 endpoint

Source: González et al. 2007 (DOI 10.1016/j.jct.2007.05.004), pure-methanol
viscosity and density series (ThermoML `PureOrMixtureData` blocks 1–2, 1
component = methanol).

| T (°C) | η (mPa·s) | Combined expanded uncertainty, 95% CI (mPa·s) | ρ (kg/m³) | ρ uncertainty, 95% CI (kg/m³) |
|---|---|---|---|---|
| 20.0 | 0.585 | ±0.008 | 791.90 | ±0.46 |
| 25.0 | 0.545 | ±0.008 | 787.20 | ±0.46 |
| 30.0 | 0.508 | ±0.007 | 782.48 | ±0.47 |

Method: capillary (Ubbelohde-type U-tube) viscometer — ThermoML method code
`CAPTUB:UFactor:2`, same code family as the sibling ACN document's source.
Relative uncertainty is ≈1.4% (95% CI) across this range.

**No source found gives pure-methanol viscosity above 30 °C.** NIST WebBook
has no free viscosity correlation for methanol (confirmed in §2: the
compound page states no viscosity data is present, pointing to the
subscription-only TRC Web Thermo Tables). Isdale et al. 1985's abstract
(§2) states pure methanol was measured at 25, 40, and 50 °C — meaning a
40 °C and 50 °C point for pure methanol likely exists in the literature —
but the numeric value is inside that paper's paywalled full text and is
**not used** here.

**Cross-check against the tertiary PubChem/CRC value** (0.544 mPa·s at
25 °C, §2): agrees with González et al.'s own measured 0.545 mPa·s at 25 °C
to within 0.2% — two independent sources agreeing.

### 3.3 Water+methanol mixtures across the full composition range, 20–30 °C

Source: González et al. 2007, `PureOrMixtureData` blocks 9–10 (2 components,
viscosity and mass density), 39 data points (13 compositions × 3
temperatures). Method: same Ubbelohde-type capillary viscometer as §3.2
(`CAPTUB:UFactor:2`) for viscosity; vibrating-tube densimeter
(`VIBTUB:UFactor:4`) for density. Uncertainty: combined expanded uncertainty
at 95% confidence, stated per data point in the source XML.

Composition is converted here from the source's mole fraction x(MeOH) to
volume fraction φ(MeOH) — this repo's internal convention — using the
"as-prepared" definition: φ = V(MeOH)/(V(MeOH)+V(water)), where each pure
component's volume is computed from its own mass and **pure-component**
density **at that same temperature, from this same source's own
pure-component measurements** (§3.2 for methanol; the x(water)=1 endpoint of
this same mixture series for water). Unlike the sibling ACN document, no
second external source's density was needed for this conversion — González
et al. 2007 measured density and viscosity on the identical composition grid
with the identical instrument, so the conversion is fully self-consistent
within one paper. Standard atomic weights used: M(H₂O) = 18.015 g/mol,
M(CH₃OH) = 32.04 g/mol (IUPAC/CIAAW standard values).

| x(water), mole fr. | x(MeOH), mole fr. | φ(MeOH), volume fr. (this-task conversion) | η at 20 °C | η at 25 °C | η at 30 °C |
|---|---|---|---|---|---|
| 0.0000 | 1.0000 | 1.0000 | 0.585 ± 0.008 | 0.545 ± 0.008 | 0.508 ± 0.007 |
| 0.0490 | 0.9510 | 0.9776 | 0.655 ± 0.009 | 0.607 ± 0.008 | 0.563 ± 0.008 |
| 0.0993 | 0.9007 | 0.9533 | 0.735 ± 0.010 | 0.677 ± 0.009 | 0.627 ± 0.009 |
| 0.1973 | 0.8027 | 0.9016 | 0.900 ± 0.012 | 0.821 ± 0.011 | 0.751 ± 0.010 |
| 0.2983 | 0.7017 | 0.8412 | 1.086 ± 0.014 | 0.987 ± 0.013 | 0.889 ± 0.012 |
| 0.3985 | 0.6015 | 0.7727 | 1.287 ± 0.016 | 1.150 ± 0.015 | 1.032 ± 0.014 |
| 0.5003 | 0.4997 | 0.6923 | 1.481 ± 0.019 | 1.309 ± 0.017 | 1.164 ± 0.015 |
| 0.5994 | 0.4006 | 0.6009 | 1.673 ± 0.021 | 1.463 ± 0.019 | 1.289 ± 0.017 |
| 0.6997 | 0.3003 | 0.4916 | 1.793 ± 0.022 | 1.554 ± 0.020 | 1.342 ± 0.018 |
| 0.7986 | 0.2014 | 0.3623 | 1.789 ± 0.022 | 1.542 ± 0.020 | 1.342 ± 0.019 |
| 0.8999 | 0.1001 | 0.2004 | 1.522 ± 0.019 | 1.317 ± 0.017 | 1.147 ± 0.016 |
| 0.9512 | 0.0488 | 0.1036 | 1.274 ± 0.016 | 1.121 ± 0.015 | 0.996 ± 0.014 |
| 1.0000 | 0.0000 | 0.0000 | 1.003 ± 0.013 | 0.890 ± 0.012 | 0.797 ± 0.011 |

(η in mPa·s = cP; uncertainty is combined expanded uncertainty, 95% CI, per
source point. φ(MeOH) computed with the pure-component densities in §3.2 and
the x(water)=1 density row below.)

Densities used for the conversion (source: González et al. 2007, same
`PureOrMixtureData` blocks, kg/m³):

| x(water) | ρ at 20 °C | ρ at 25 °C | ρ at 30 °C |
|---|---|---|---|
| 0.0000 (pure MeOH) | 791.90 | 787.20 | 782.48 |
| 1.0000 (pure water) | 998.20 | 997.05 | 995.65 |

The pure-water density row above (read from this same source's own
measurement) agrees with the standard tabulated density of water at these
temperatures to within normal rounding, corroborating that this dataset's
density scale is sound before it is used for the φ conversion.

**Location of the viscosity maximum.** At every one of the three measured
temperatures, the grid maximum falls at x(MeOH)=0.3003 (φ(MeOH)≈0.49):

| T (°C) | η_max (mPa·s) | at φ(MeOH) | η_max / η(pure water) | η_max / η(pure MeOH) |
|---|---|---|---|---|
| 20 | 1.793 | 0.4904 | 1.788 (+78.8%) | 3.065 |
| 25 | 1.554 | 0.4916 | 1.746 (+74.6%) | 2.851 |
| 30 | 1.342 | 0.4927 | 1.684 (+68.4%) | 2.642 |

The next-adjacent grid point (x(MeOH)=0.2014, φ≈0.36) gives an almost
identical viscosity at all three temperatures (1.789, 1.542, and 1.342
mPa·s respectively — the last one tied with the x=0.3003 point to 4
significant figures at 30 °C). **This means the true continuous maximum is
only bounded, not pinned, by this 13-point grid** — it sits somewhere
between x(MeOH)≈0.20 and 0.30 (φ(MeOH)≈0.36–0.49) at every measured
temperature, and this grid is too coarse to resolve the direction of any
shift with temperature that Tanaka et al. 1987's abstract (§2) reports
qualitatively ("the viscosity maximum shifts gradually to a higher alcohol
concentration with increasing temperature"). No number is asserted here for
the shift itself — only the bracketing bounds, which are read directly from
the table above.

**Excess molar volume — quantified, not just cited.** This dataset's own
density measurements make it possible to compute the excess molar volume
directly, rather than only note its existence by title (as the sibling ACN
document did for Handa & Benson 1981 and Davis 1983, without opening
either). Using V_m(mixture) = M_mix/ρ_mix and V_ideal =
x(MeOH)·V_m(pure MeOH) + x(water)·V_m(pure water), computed in this task
from the table above:

| x(water) | V_E at 25 °C (cm³/mol) |
|---|---|
| 0.0000 | 0.0000 |
| 0.0490 | −0.178 |
| 0.0993 | −0.340 |
| 0.1973 | −0.612 |
| 0.2983 | −0.819 |
| 0.3985 | −0.946 |
| 0.5003 | **−0.997 (most negative)** |
| 0.5994 | −0.962 |
| 0.6997 | −0.842 |
| 0.7986 | −0.625 |
| 0.8999 | −0.311 |
| 0.9512 | −0.141 |
| 1.0000 | 0.0000 |

(20 °C and 30 °C give the same shape, most-negative value −0.990 and −0.991
cm³/mol respectively, both near x(water)=0.50.) This confirms, with an
actual computed magnitude from this task's own data rather than only a
literature citation, that water+methanol mixing is contractive (negative
excess volume), peaking near equimolar composition — consistent with the
well-known hydrogen-bonding picture for this system, though no external
literature value (e.g. Benson & Kiyohara-type compilations) was
cross-checked against this computed number in this pass (§7, §8).

**As-prepared φ vs. true (actual-volume) φ — quantified.** Because of the
negative excess volume above, the "as-prepared" φ used in the main table
(computed from pure-component volumes, matching how a pump doses solvent)
differs from a "true" φ computed against the mixture's actual, contracted
volume. At 25 °C, computed in this task:

| x(water) | φ(MeOH), as-prepared | φ(MeOH), true (actual volume) | Difference |
|---|---|---|---|
| 0.0490 | 0.9776 | 0.9821 | +0.0044 |
| 0.1973 | 0.9016 | 0.9171 | +0.0155 |
| 0.3985 | 0.7727 | 0.7965 | +0.0238 |
| 0.5003 | 0.6923 | 0.7166 | **+0.0243 (largest)** |
| 0.6997 | 0.4916 | 0.5088 | +0.0172 |
| 0.8999 | 0.2004 | 0.2035 | +0.0031 |

The largest gap (≈0.024, i.e. 2.4 percentage points of φ, roughly 2.4% of
%B) occurs near the middle of the composition range and is small compared
to the composition-driven viscosity swings this document quantifies, but it
is not zero, and — per the same convention decision as the sibling
document — the **as-prepared** definition (matching how %B is actually
metered on an HPLC pump) is what is carried forward into the table above and
into §4, not the true-volume figure.

### 3.4 Coverage achieved, stated plainly

| Composition | 20–30 °C (5 °C steps) | 35–80 °C |
|---|---|---|
| Full range, φ = 0→1 (13 points) | ✅ González et al. 2007, via NIST ThermoML | ❌ not found in this pass |
| φ = 0 (pure water) only | ✅ (also NIST/IAPWS to 80 °C, §3.1) | ✅ NIST/IAPWS reference formulation only |
| φ = 1 (pure MeOH) only | ✅ González et al. 2007 | ❌ not found (Isdale et al. 1985 abstract states 40/50 °C points exist but are paywalled, §2, §3.2) |

The temperature range found (20–30 °C) is **narrower** than both the
ticket's 25–60 °C minimum ask and the 25–45 °C found for the sibling ACN
system. This is the single biggest gap in this document — see §7.

---

## 4. Interpolating form

### 4.1 Why not a published correlation

Katti et al. 2008 is, by title, exactly the single-expression
η(T,composition) correlation this ticket describes, for exactly this
binary system — and it remains completely inaccessible (§2): article, ACS
Supporting Information, NIST ThermoML archive, and a stealth-browser pass
against the ACS article page (which returned a Cloudflare bot-check page,
not the article) all returned nothing. Landolt-Börnstein's Wohlfarth
chapter (§2) was not opened. So the form below is a fit performed in this
research task against the §3.3 data, **not** a citation to a published
correlation — flagged as such throughout, matching the sibling document's
fallback approach.

### 4.2 Polynomial in φ, fit per isotherm

For each of the three measured temperatures, a degree-4 polynomial in φ was
fit by ordinary least squares to the 13 points in §3.3 (computed in this
task; arithmetic reproducible from §3.3's table):

η(φ) ≈ a₄φ⁴ + a₃φ³ + a₂φ² + a₁φ + a₀ (η in mPa·s, φ = MeOH volume fraction 0–1)

| T (°C) | a₄ | a₃ | a₂ | a₁ | a₀ |
|---|---|---|---|---|---|
| 20 | 4.5641 | −8.3143 | 0.5123 | 2.8332 | 0.9969 |
| 25 | 3.3135 | −6.2709 | 0.2787 | 2.3406 | 0.8868 |
| 30 | 2.3017 | −4.5588 | 0.0236 | 1.9467 | 0.7964 |

**Residual against the fitted-to data** (computed in this task, degree 4):

| T (°C) | RMS residual (mPa·s) | Max \|residual\| (mPa·s) | Max \|residual\| (% of value) |
|---|---|---|---|
| 20 | 0.00816 | 0.01606 | 0.90% |
| 25 | 0.00585 | 0.01217 | 0.93% |
| 30 | 0.00575 | 0.01376 | 1.03% |

The worst-case relative residual (1.03% at 30 °C) is on the same order as
the source data's own stated measurement uncertainty at those points
(~1.2–1.6%, 95% CI, §3.3) — the degree-4 fit is about as good as the
underlying data supports. A degree-5 fit (tried for comparison, at 25 °C)
roughly halves the residual (RMS 0.0032 mPa·s, max 0.47% vs. degree-4's
0.93%) but starts to fit noise given only 13 points; a degree-3 fit is
markedly worse (RMS 0.0203 mPa·s, max 3.60% at 25 °C). **Degree 4 is the
recommended form**, matching the sibling document's choice for the same
reasons. An implementation should carry the residual figures above as this
form's evidenced error, not a smaller number.

### 4.3 Temperature axis

Within 20–30 °C, the recommended approach is to **interpolate between the
three measured isotherms** (e.g. linearly or with a monotonic spline in T,
at fixed φ) rather than fit a global bivariate surface — three points 5 °C
apart is fewer even than the sibling ACN document's five points, and is not
enough to responsibly fit a smooth T-dependence and extrapolate it, with no
published correlation coefficients (Katti et al. 2008's) obtainable to do
this properly. **Extrapolating any of this beyond 30 °C, toward the
ticket's 60 °C minimum or 80 °C stretch goal, is not supported by data
found in this research** — this is a materially bigger gap than the
sibling document's (which reached 45 °C). If a candidate run's temperature
exceeds 30 °C, a pressure-scaling rule consuming this document should flag
that the viscosity term is extrapolated/unverified for methanol mixtures,
not silently extend the polynomial — and should treat that flag as firing
far more often than the equivalent ACN flag would, given how much of this
repo's realistic operating temperature range (up to 60 °C, per the ticket)
falls outside 20–30 °C.

---

## 5. Modifier note: formic acid / TFA

**Not found**, matching the sibling document's finding for the ACN system.
CrossRef searches combining "formic acid" / "trifluoroacetic acid" with
"viscosity," "mobile phase," "backpressure," "methanol water," and "UHPLC
eluent" found papers about TFA's effect on chromatographic *retention
selectivity* (e.g. the same Gilar, Xie & Jaworski work the sibling document
found, which is solvent-system-agnostic and not specific to methanol) and
about TFA/formic-acid *vapor-liquid equilibrium* (e.g. Huang et al. 2016,
"Isobaric vapor-liquid equilibrium of trifluoroacetic acid+water," §2's
search results) — but no paper measuring viscosity of a
water/methanol/formic-acid or water/methanol/TFA ternary mixture at any
concentration, and no paper measuring aqueous formic acid's own viscosity
vs. temperature, was found.

**What is not being claimed:** this document does not assert that 0.1%
formic acid or TFA has a "measured negligible" effect on viscosity — no
measurement was found either way. It remains physically plausible by simple
dilution reasoning that adding ~0.1% v/v of a small-molecule acid to a
binary solvent perturbs bulk viscosity by much less than the water/methanol
composition swings this document quantifies in §3.3 (which are enormous for
this particular system — up to ~79% above pure water, §3.3, §6), but **this
is inference, not a citation**, and the honest status is **not tested**, not
"tested and found negligible." If anything, the unusually large composition
sensitivity of this particular system (compared to water-ACN) is a reason
for extra caution before assuming a modifier's effect is negligible, not
less caution.

---

## 6. Implications for pressure scaling

- **η(φ) has a large, sharply peaked, now-quantified maximum — much larger
  than the water-ACN case.** At every one of the three measured
  temperatures, viscosity rises from the pure-water value to a peak roughly
  **68–79% above pure water** (and 2.6–3.1× pure methanol) before falling
  toward the pure-methanol value (§3.3). This is roughly 7× the size of the
  ACN system's ~10% maximum-vs-water effect found in the sibling document.
  **A linear interpolation between pure-water and pure-methanol viscosity
  would dramatically underestimate pressure in the low-to-mid %B region** —
  not merely be "approximate," but wrong by tens of percent in the region
  many real gradient methods spend most of their time in.
- **The maximum sits close to φ(MeOH) ≈ 0.49 — near the midpoint of the
  composition range, not near the low-%B end the way ACN's was.** The
  sibling ACN document found its maximum at φ≈0.14 (a low-%B region); this
  document finds the methanol maximum at φ≈0.49 (bracketed between φ≈0.36
  and φ≈0.49 on this 13-point grid, §3.3) — i.e., **essentially at 49%B**,
  a composition many gradient methods pass directly through. This is
  qualitatively corroborated (mole fraction 0.3–0.4, matching this
  document's x(MeOH)=0.20–0.30 bracket) by Tanaka et al. 1987's freely-read
  abstract (§2), though that paper's own numbers were not obtained.
- **The composition effect swamps the temperature effect at every
  temperature found.** Pure water's viscosity falls from 1.003 to 0.797
  mPa·s (20.5%) from 20 to 30 °C (§3.3); over the same span, the peak
  viscosity falls from 1.793 to 1.342 mPa·s (25.2%) — a comparable
  fractional temperature sensitivity, but both are dwarfed by the
  ~3× swing across composition at fixed temperature. A pressure-scaling
  rule that gets the composition term right but crudely approximates the
  temperature term is far less wrong, for this solvent system, than one
  that gets composition wrong.
- **φ must be defined the same way this document defines it before a
  number is plugged in.** The mixture table in §3.3 reports φ in this
  repo's volume-fraction convention via a same-task conversion from the
  source's mole fraction, using **pure-component** densities at each
  temperature (the "as-prepared," operational definition of %B, matching
  how a pump actually meters solvent) — not the mixture's true, contracted
  volume. Unlike the sibling document, this gap is **quantified directly
  from the same dataset** in §3.3 (up to ≈0.024, i.e. ~2.4 percentage
  points of φ, near mid-composition) rather than only flagged by citing an
  unopened paper's title.
- **Temperature coverage stops at 30 °C — this is a materially bigger gap
  than the ACN case's 45 °C ceiling.** Only the pure-water endpoint (§3.1,
  NIST/IAPWS, to 80 °C) has any data above 30 °C; the mixture and the
  pure-methanol endpoint have none. Given the ticket's own 25–60 °C
  minimum ask, most of the temperature range this repo needs to support
  falls **entirely outside** what this pass could verify for methanol. A
  pressure-scaling rule must either refuse to predict pressure for a
  methanol-mode candidate above 30 °C without an explicit
  "extrapolated, unverified" flag, or be re-derived once a source covering
  that range is found (§7) — and this should be treated as a higher
  priority than the equivalent ACN gap, since 30 °C is reached by far more
  real HPLC methods than 45 °C is.
- **Dwell volume is unaffected by any of this.** This project's dwell
  volume is a fixed instrument constant (0.375 mL, per project memory),
  never data-tuned — viscosity feeds the column pressure term, not the
  dwell term.
- **A modifier-viscosity term is not currently justified by data (§5).**
  Until a source is found, a pressure-scaling rule should either ignore
  modifier concentration entirely (documented as an assumption) or expose
  it as an explicit, separately-flagged unknown — and, given how much
  larger the underlying composition effect is for methanol than for ACN,
  any future modifier study should be read with correspondingly more
  caution before being treated as "negligible here too."

---

## 7. Open points

Ranked by how much each blocks a usable pressure-scaling implementation:

1. **Temperature range above 30 °C is unresolved for the mixture, and this
   is worse than the sibling ACN gap.** No primary source located in this
   pass covers 35–80 °C for water+methanol mixtures. Katti et al. 2008
   (§2) is the best-named candidate to close this if institutional access
   can be obtained; Tanaka et al. 1987 (§2, abstract states 283–348 K,
   i.e. up to 75 °C) is arguably an even better target since its abstract
   confirms the needed range exists in principle; Isdale et al. 1985 could
   supply pure-methanol points at 40/50 °C; the Landolt-Börnstein
   Wohlfarth compilation is a further candidate.
2. **Katti et al. 2008's correlation remains fully inaccessible** —
   article, ACS Supporting Information, NIST ThermoML archive, and a
   stealth-browser pass against the ACS article page (blocked by
   Cloudflare, not merely paywalled) all checked and all negative (§2).
   Exactly as in the sibling document, this is the single most
   consequential gap: it is, by title, a ready-made answer to both §4's
   exercise and open point #1 above, for methanol specifically.
3. **Tanaka et al. 1987 and Isdale et al. 1985's full data tables are
   unopened.** Both papers' free abstracts (obtained via a stealth-browser
   pass, §9) describe exactly the temperature range and composition
   behavior this document needs, but the numeric tables sit behind
   "log in via an institution" gates that a stealth pass against a
   bot-detection system cannot address (this is a genuine authentication
   wall, not a scripted-fetch block) — no attempt was made to bypass this,
   per the constraint against circumventing real access controls.
4. **The mole→volume-fraction conversion (§3.3) is a same-task
   computation, not a sourced table**, though — unlike the sibling ACN
   document — it now rests on a **single, internally consistent** source
   (González et al. 2007 measured both density and viscosity on the same
   composition grid), removing the sibling document's cross-source/offset
   concern. Anyone re-deriving this should still re-check the standard
   atomic weights and arithmetic rather than take φ in §3.3 as itself a
   primary-sourced number.
5. **The true (mixed, contracted) volume fraction vs. the as-prepared one
   is now quantified (§3.3)**, unlike the sibling document, which only
   noted the effect existed by citing unopened papers' titles. The
   quantification here (up to ≈0.024 in φ) rests entirely on this task's
   own computation from González et al. 2007's density data, not on an
   external excess-volume reference — no independent literature check of
   this document's own excess-volume numbers (§3.3) was performed. That
   is a smaller gap than the sibling document's (which had no number at
   all), but still an unverified-against-a-second-source computation.
6. **Modifier (formic acid/TFA) viscosity effect: no data found at all**
   (§5), matching the sibling document exactly.
7. **Landolt-Börnstein (Wohlfarth 2008/2017) was identified but never
   opened** (§2) — flagged again here as a promising next fetch, since
   compilations of this kind typically publish a recommended smoothing
   equation together with each primary source's deviation from it, and
   this system has more primary sources (§2) than were opened here.
8. **The true continuous location of the viscosity maximum is bounded, not
   pinned, by this 13-point grid** (§3.3) — between x(MeOH)≈0.20 and 0.30
   (φ≈0.36–0.49) at every temperature found, with the direction of any
   temperature-shift (which Tanaka et al. 1987's abstract asserts
   qualitatively exists) not resolvable from this grid.
9. **Dizechi & Marschall 1982 and Mikhail & Kimel 1961** — both classic,
   widely-cited water+methanol viscosity references — remain fully
   inaccessible and not deposited in ThermoML (§2); neither was pursued
   via a stealth pass, since both are pre-2000 ACS/Wiley content behind
   standard subscription paywalls rather than a bot-detection layer a
   stealth browser would plausibly get past (unlike the Springer
   login-redirect cases, §9).
10. **Noda, Ohashi & Ishida 1982's ternary methanol+acetone+water paper**
    was identified as a possible single-temperature (25 °C) cross-check
    for the binary edge but never opened (§2) — low priority, since it
    would only duplicate a temperature already well covered by González
    et al. 2007.
11. **IAPWS-2008's own stated uncertainty for pure water was never
    retrieved** from Huber et al. 2009 directly (§2, §3.1) — same gap as
    the sibling document.

**What can be relied on as-is:** the full §3.3 mixture table (13
compositions × 3 temperatures, both raw mole-fraction values and the
same-task volume-fraction conversion, each point's stated measurement
uncertainty), the excess-volume and as-prepared-vs-true-φ computations in
§3.3 (both derived from this same self-consistent dataset), the §3.1
pure-water table (cross-validated by two independent sources and
independently re-fetched in this pass), the §3.2 pure-methanol table
(cross-validated against PubChem/CRC), and the §4.2 polynomial fit and its
residuals — all parsed directly from the raw retrieved ThermoML XML and
NIST WebBook fetches in this pass (§9), not taken on trust from a prior
summary.

---

## 8. What was not independently re-verified

For completeness: (a) the closed-access status determinations rest on a
single Unpaywall API check per DOI plus, for the two Springer *Int. J.
Thermophys.* papers and the one ACS paper, a stealth-browser fetch of the
article page itself — these were not cross-checked against a second
registry (e.g. Semantic Scholar) the way the sibling document's Katti 2008
finding was corroborated by two independent registries; (b) the excess
molar volume computed in §3.3 was not checked against any external
literature value for this system (e.g. a Landolt-Börnstein or
Kell-type compilation) — it is presented purely as this task's own
arithmetic from González et al. 2007's density data, consistent internally
(both endpoints correctly return V_E=0) but not externally corroborated;
(c) IAPWS-2008's own stated uncertainty (§2, §3.1, §7) was not retrieved
from the primary standard; (d) the CrossRef bibliographic searches used to
locate candidate papers (§2) are keyword searches against CrossRef's own
index, not an exhaustive literature search — other primary papers on this
extremely well-studied system almost certainly exist and were not found by
the search terms tried in this pass.

---

## 9. How this pass verified the numbers

Every number in §3 and §4 above was derived directly from two raw sources
fetched in this pass:

- `https://trc.nist.gov/ThermoML/10.1016/j.jct.2007.05.004.xml` — fetched
  and queried (via `WebFetch`, which converts the page and answers a
  targeted prompt against it — the file was queried multiple times with
  narrower, single-temperature/single-property prompts specifically to
  force literal, un-rounded numeric transcription rather than a summarized
  table, since a first broad query on this file truncated one long block)
  for the pure-methanol viscosity/density blocks (§3.2) and the
  methanol+water mixture viscosity and density blocks at each of the three
  temperatures separately (§3.3).
- NIST Chemistry WebBook's fluid-properties calculator for water (CAS
  7732-18-5), fetched directly for the viscosity table in §3.1, and for
  methanol (CAS 67-56-1), fetched directly to confirm the compound page
  states no free viscosity data is present (§2).
- CrossRef's public API (`api.crossref.org/works`) was used extensively in
  this pass — both by DOI (to confirm/obtain exact citations for candidate
  papers named or implied by the ticket) and by bibliographic keyword
  search (to locate the ThermoML-deposited paper that ended up anchoring
  this document, and to locate the Isdale 1985 and Tanaka 1987 papers) —
  since this session's interactive web-search tool had exhausted its
  budget for this conversation before this task began; all literature
  discovery in this pass therefore ran through CrossRef's own search
  index plus targeted single-URL fetches, not a general web search engine.
- Unpaywall's public API (`api.unpaywall.org/v2/<DOI>`) was queried for
  every candidate DOI to determine open-access status, using a generic
  contact address for the API's required `email` parameter
  (`team@ourresearch.org`, Unpaywall's own publicly listed contact) rather
  than any personal address, since this is a third-party API call
  unrelated to user identity.
- NCBI's E-utilities (`eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi`
  and `efetch.fcgi`) were used to locate and read the freely-available
  PubMed abstract for Thompson, Kaiser & Jorgenson 2006 (PMID 16996532),
  since a direct `pubmed.ncbi.nlm.nih.gov` fetch returned only a
  cookie-consent wall.
- A **stealth-browser pass** (as authorized in the ticket for 403/captcha/
  blocked-JS cases) was run for two targets, one script per site, from
  this task's scratchpad directory, using `playwright` with
  `p.chromium.launch(channel="chrome", headless=True)` and
  `playwright_stealth.stealth_sync(page)` applied to each page:
  - `https://pubs.acs.org/doi/10.1021/je800607j` (Katti et al. 2008): the
    stealth pass still received an HTTP 403 Cloudflare "Performing
    security verification" challenge page — confirms the block is a
    bot-detection layer, unaffected by stealth techniques, not merely an
    artifact of the plain-fetch tool.
  - `https://link.springer.com/article/10.1007/BF00508889` (Isdale et al.
    1985) and `https://link.springer.com/article/10.1007/BF00515199`
    (Tanaka et al. 1987): a plain `WebFetch` of these URLs had redirected
    (HTTP 303) to a Springer login page; the stealth pass reached each
    URL directly with HTTP 200 and the full abstract text rendered
    normally, confirming these are freely-readable abstracts blocked only
    by a scripted-fetch/redirect quirk, with the full article text itself
    still gated behind "log in via an institution" (a genuine
    subscription wall, not attempted to be bypassed).
- The mole→volume-fraction conversion, the excess-molar-volume
  computation, the as-prepared-vs-true-φ comparison, and the degree-3/4/5
  polynomial fits and their residuals (§3.3, §4.2) were computed directly
  in this pass with a short Python script (`numpy.polyfit`) against the
  ThermoML-derived tables above; every intermediate number quoted in §3.3
  and §4.2 is reproducible from the raw tables given in this document.
