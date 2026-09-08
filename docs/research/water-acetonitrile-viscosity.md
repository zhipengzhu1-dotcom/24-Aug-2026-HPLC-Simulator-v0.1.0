# Viscosity of Water–Acetonitrile Mixtures Against Composition and Temperature

Research for issue #137. Purpose: give a pressure-scaling rule (`P ∝ Q·η`,
pressure across a packed bed proportional to flow rate × mobile-phase
viscosity) the composition- and temperature-dependence of viscosity, η(φ,T),
it needs to scale a recorded scouting-run pressure to a candidate run at a
different flow rate, starting composition, or column temperature. φ is the
acetonitrile (ACN) volume fraction, 0–1, per this repo's unit convention
(`CLAUDE.md`: "φ is a fraction 0–1 internally; %B 0–100 exists only at
entry/display boundaries").

This document went through two research passes. The first pass located five
genuine primary papers measuring this exact system but could not read a
single number out of any of them — all five are confirmed closed-access. The
second pass found a sixth primary paper whose full numeric dataset is legally
and openly deposited in a US government archive (NIST's ThermoML Archive,
required of authors publishing transport-property data in cooperating
journals) and retrieved it directly. That dataset is the numeric backbone of
everything below. Every other number in this document is either read from
that same archive, from NIST's own reference correlation, or is explicitly
labeled as computed/derived in this task from those two, or is explicitly
flagged as not found.

**Bottom line.** Full composition range (16 points spanning x(ACN) = 0 → 1)
is measured at **five temperatures, 25–45 °C in 5 °C steps**. Temperatures
above 45 °C (up to the ticket's 80 °C ceiling) are **not covered by any
source located in either pass** — this is the one major open gap. A
degree-4 polynomial in φ fits each isotherm with a residual (≤1.7% of the
measured value) comparable to the data's own stated measurement uncertainty
(~1.2–1.6%, 95% confidence). Modifier (formic acid/TFA) viscosity data was
not found in either pass.

---

## 1. Question

What are the viscosities of water–acetonitrile mixtures across composition
(0–100% ACN by volume) and temperature (25–80 °C), from primary sources, in
a form a pressure-scaling rule can use? Pressure across a packed bed is
proportional to flow × viscosity, so scaling a recorded scouting pressure to
a candidate at another flow, start composition, or temperature needs
η(φ,T). Also: does adding 0.1% formic acid or a similar low-level acidic
modifier (e.g. 0.1% TFA) change viscosity by an amount that matters for
pressure prediction, or is it negligible?

---

## 2. Sources

| Source | Type | What it provides | Access notes |
|---|---|---|---|
| M. d. C. Grande, J. A. Julià, C. R. Barrero, C. M. Marschoff, H. L. Bianchi, "The (water + acetonitrile) mixture revisited: A new approach for calculating partial molar volumes," *J. Chem. Thermodyn.* **38** (2006) 760–768. DOI: [10.1016/j.jct.2005.08.009](https://doi.org/10.1016/j.jct.2005.08.009) | **Primary** | Measured density and viscosity of water+ACN over the **whole composition range** (16 mole fractions, x(ACN) = 0 to 1) at **five temperatures**: 298.15, 303.15, 308.15, 313.15, 318.15 K (25, 30, 35, 40, 45 °C). This is the numeric source for essentially all of §3 below. | **The journal article itself (Elsevier ScienceDirect) is presumed paywalled — not separately re-checked in this task** (it was not one of the four papers originally named and Unpaywall-checked). **Its full numeric dataset was independently retrieved**, however, from the NIST ThermoML Archive (`trc.nist.gov/ThermoML/10.1016/j.jct.2005.08.009.xml`, HTTP 200, no login) — a standing, `.gov`-hosted, open data-deposit program that *J. Chem. Thermodyn.* participates in as a "cooperating journal." The XML was fetched and re-parsed independently in this pass (not taken on trust from the sub-agent's summary) — see §3 for the values and §9 for how it was verified. |
| A. M. Katti, N. E. Tarfulea, C. J. Hopper, K. R. Kmiotek, "Prediction of Viscosity−Temperature−Composition Surfaces in a Single Expression for Methanol−Water and Acetonitrile−Water Mixtures," *J. Chem. Eng. Data* **53** (2008) 2865–2872. DOI: [10.1021/je800607j](https://doi.org/10.1021/je800607j) | **Primary** | By title, exactly the reusable published η(T,composition) correlation this ticket asked to look for, for exactly this binary system. | **Confirmed closed on every route tried.** Article: HTTP 403 from `pubs.acs.org`; Unpaywall and Semantic Scholar both report closed access (independent registries, same conclusion). ACS Supporting Information (`pubs.acs.org/doi/suppl/10.1021/je800607j`): also HTTP 403. **NIST ThermoML Archive**: queried directly by DOI, by author surname ("Katti", "Kmiotek"), and by title fragment — **zero hits**, despite *J. Chem. Eng. Data* being a ThermoML cooperating journal with coverage through 2019. This paper's correlation and coefficients could not be retrieved by any route tried in either pass. **This is the single most consequential remaining gap.** |
| C. Moreau, G. Douhéret, "Thermodynamic behaviour of water-acetonitrile mixtures excess volumes and viscosities," *Thermochimica Acta* **13** (1975) 385–392. DOI: [10.1016/0040-6031(75)85079-9](https://doi.org/10.1016/0040-6031(75)85079-9) | **Primary** | Direct measurement of water+ACN viscosity vs. composition; a classic reference on this system. | **Confirmed paywalled.** Unpaywall: `is_oa: false`, no open location. Not deposited in ThermoML (predates the archive's typical coverage; not queried again in pass 2 beyond the general water+ACN sweep, which did not surface it). No number used from this paper. |
| H. Wode, W. Seidel, "Precise viscosity measurements of binary liquid mixtures of acetonitrile-water and 1,3-dimethyl-2-imidazolidinone-water," *Ber. Bunsenges. Phys. Chem.* **98** (1994) 927–934. DOI: [10.1002/bbpc.19940980706](https://doi.org/10.1002/bbpc.19940980706) | **Primary** | Ubbelohde-capillary viscosity measurements, confirmed range **20–40 °C** from bibliographic metadata (abstract itself unreadable). | **Confirmed paywalled** (Unpaywall `is_oa: false`). Its confirmed 20–40 °C range does not extend past what Grande et al. 2006 already supplies (25–45 °C), so it was not pursued further as a range-extension candidate. |
| M. A. Saleh, S. Akhtar, M. S. Ahmed, "Density, viscosity and thermodynamic activation of viscous flow of water + acetonitrile," *Phys. Chem. Liq.* **44** (2006) 551–562. DOI: [10.1080/00319100600861151](https://doi.org/10.1080/00319100600861151) | **Primary** | Direct measurement, framed around Eyring activation-energy theory (a temperature-dependence model) — could be relevant to extending the T-range if accessible. | **Confirmed paywalled** (Unpaywall `is_oa: false`; Taylor & Francis returned HTTP 403, no abstract text obtained). Temperature range not confirmed. |
| J. W. Thompson, T. J. Kaiser, J. W. Jorgenson, "Viscosity measurements of methanol–water and acetonitrile–water mixtures at pressures up to 3500 bar," *J. Chromatogr. A* **1134** (2006) 201–209. DOI: [10.1016/j.chroma.2006.09.006](https://doi.org/10.1016/j.chroma.2006.09.006) | **Primary** | PubMed abstract (freely readable) states the **full 0–100% v/v composition range in 10% increments at 25 °C**, atmospheric pressure up to 3500 bar, cross-validated against Bridgman falling-body viscometers — directly on-topic for HPLC pressure work and, unusually, reports composition in **%v/v directly** (not mole fraction) if the full text bears that out. | **Abstract only.** No numeric table retrieved (article and NIST ThermoML both not checked successfully / not deposited). Not used for any number below; flagged as the best next lead for someone with journal access, since it would let this repo's φ (volume-fraction) values be checked directly against a source that reports φ the same way the app does, without a mole-to-volume-fraction conversion. |
| NIST Chemistry WebBook, water (CAS 7732-18-5), fluid-properties calculator, IAPWS-2008 viscosity formulation and IAPWS-95 density formulation, 1 bar | **Primary/authoritative reference correlation** (not itself a new lab measurement — a formulation fit to a large body of primary data by international agreement) | Pure-water η(T) and ρ(T), the φ=0 endpoint, fetched directly at `webbook.nist.gov` for 25–80 °C (viscosity) and near 25–45 °C (density, for the mole→volume-fraction conversion in §3.4). | Fully open, fetched directly, no login. Uncertainty of the underlying IAPWS-2008 formulation itself was **not** retrieved from the standard (Huber, M. L. et al., *J. Phys. Chem. Ref. Data* **38** (2009) 101–125) — the WebBook page does not surface a number, and that paper was not separately fetched — so no uncertainty is asserted for this row (§8). |
| Pure acetonitrile density/viscosity, own-paper measurement in Grande et al. 2006 (same DOI as above), retrieved via the same ThermoML XML | **Primary**, single-composition endpoint of the same dataset | η(T) and ρ(T) for pure ACN, 25–45 °C, five points, **with stated combined expanded uncertainty at each point** — see §3.2. This **supersedes** an earlier single-point tertiary estimate (PubChem/Kirk-Othmer, 0.35 cP at 20 °C) used in the first pass, which is retained below only as an independent cross-check. | Fully retrieved, same XML file as the mixture data. |
| PubChem CID 6342 (acetonitrile), `Viscosity` property, citing DeVito, "Nitriles," *Kirk-Othmer Encyclopedia of Chemical Technology* (2007), and ILO-WHO ICSC #0088 | **Tertiary compilation** | Pure-ACN viscosity, single point: 0.35 cP at 20 °C. | Retained only as a cross-check against Grande et al.'s own pure-ACN measurement (§3.2) — the two agree with the expected trend (see §3.2 note). Not used as a primary number. |
| Ch. Wohlfarth, "Viscosity of the mixture (1) water; (2) acetonitrile," in *Landolt-Börnstein — Group IV Physical Chemistry, Supplement to IV/18* (Springer, 2008), 716–718. DOI: [10.1007/978-3-540-75486-2_443](https://doi.org/10.1007/978-3-540-75486-2_443) | **Secondary** (critically evaluated compilation; standard L-B practice is to fit a recommended smoothing equation to pooled primary data and report each source's deviation from it) | Would very likely fold in Grande et al. 2006, Wode & Seidel 1994, and Moreau & Douhéret 1975, plus a recommended correlation with a stated fit quality. | **Not opened in either pass** (Springer chapter, expected paywalled, not separately re-verified). Still the single most promising next fetch for someone with institutional access — see §7. |
| International Critical Tables, Vol. 5 (1929), viscosity volume | Public-domain compilation, checked as a candidate primary/tertiary source | — | **Confirmed absent.** Full OCR text fetched from archive.org and searched for "acetonitrile," "aceto-nitrile," "cyanomethane," and "methyl cyanide" — **zero matches**. Acetonitrile as a laboratory/industrial solvent postdates this 1929 compilation; this is a clean negative result, not a failed fetch. |
| Riddick, Bunger & Sakano, *Organic Solvents: Physical Properties and Methods of Purification* (Techniques of Chemistry series, Wiley) | Handbook, checked as a candidate secondary source | Tabulates pure acetonitrile properties and, in some editions, binary-mixture data. | **Located on archive.org but access-restricted** (`Access-restricted-item: true`, Internet Archive Controlled Digital Lending). Not borrowed or circumvented, per the constraint against bypassing access controls — left as an unopened lead, not asserted to contain or lack the relevant table. |
| CORE.ac.uk (green-OA aggregator) | Aggregator, checked for author-archived copies of the four closed papers | — | Public search page and v3 API both returned HTTP 403 without an API key; not pursued further (obtaining a key was judged out of scope for a research task). |
| "Chen–Horváth" viscosity correlation (a form named in the ticket as a candidate published correlation) | — | The ticket named this as an example of a ready-to-use published correlation. | **Could not be verified to exist under that name.** The only Chen–Horváth paper found via CrossRef is Chen, H.; Horváth, Cs., *J. Chromatogr. A* **705** (1995) 3–20, "High-speed high-performance liquid chromatography of peptides and proteins" — about instrument/column speed, not a solvent-viscosity-vs-composition correlation. Treated as **not established to exist**, not cited for any number here. |

---

## 3. Data

All numbers in this section trace to two fetches: NIST's ThermoML XML for
`10.1016/j.jct.2005.08.009` (Grande et al. 2006), and NIST's Chemistry
WebBook fluid-properties calculator for water. Both were re-parsed directly
in this final pass from the raw retrieved files, not taken from a
sub-agent's prose summary at face value — see §9 for how.

### 3.1 Pure water, η(T), 25–80 °C — the φ=0 endpoint

Source: NIST Chemistry WebBook, water (CAS 7732-18-5), IAPWS-2008 viscosity
formulation, 1 bar.

| T (°C) | η (mPa·s) |
|---|---|
| 25.0 | 0.89002 |
| 30.0 | 0.79722 |
| 35.0 | 0.71913 |
| 40.0 | 0.65273 |
| 45.0 | 0.59577 |
| 50.0 | 0.54652 |
| 55.0 | 0.50362 |
| 60.0 | 0.46603 |
| 65.0 | 0.43290 |
| 70.0 | 0.40355 |
| 75.0 | 0.37742 |
| 80.0 | 0.35405 |

Method: not a single lab measurement — this is NIST's implementation of the
IAPWS-2008 international reference formulation, itself fit to a large body of
primary measurements the WebBook page does not enumerate. Uncertainty: not
retrieved (see §2, §8).

**Cross-check.** Grande et al. 2006's own independently measured pure-water
point (x(ACN)=0, i.e. the mixture-series endpoint, not a separate
"pure-component" experiment) reads 0.8901, 0.7973, 0.7193, 0.6530, 0.5961
mPa·s at 25/30/35/40/45 °C — agreeing with the NIST/IAPWS table above to
within 0.1% at every overlapping temperature. This is two independent
sources agreeing, not one source repeated.

### 3.2 Pure acetonitrile, η(T), 25–45 °C — the φ=1 endpoint

Source: Grande et al. 2006 (DOI 10.1016/j.jct.2005.08.009), pure-component
viscosity and density series (ThermoML `PureOrMixtureData` block 1/2, 1
component = acetonitrile).

| T (°C) | η (mPa·s) | Combined expanded uncertainty, 95% CI (mPa·s) | ρ (kg/m³) | ρ uncertainty, 95% CI (kg/m³) |
|---|---|---|---|---|
| 25.0 | 0.3417 | ±0.0053 | 776.69 | ±1.89 |
| 30.0 | 0.3280 | ±0.0051 | 771.89 | ±1.92 |
| 35.0 | 0.3129 | ±0.0049 | 765.46 | ±1.96 |
| 40.0 | 0.3009 | ±0.0048 | 760.86 | ±1.99 |
| 45.0 | 0.2899 | ±0.0047 | 754.76 | ±2.03 |

Method: capillary (Ubbelohde-type U-tube) viscometer — ThermoML method code
`CAPTUB:UFactor:2`. Relative uncertainty is ≈1.55–1.62% (95% CI) across this
range.

**No source found gives pure-ACN viscosity above 45 °C.** NIST WebBook has
no free viscosity correlation for acetonitrile (confirmed in the first pass:
the WebBook's fluid calculator returns HTTP 400 for acetonitrile and its
compound page states "No viscosity data is present on this page," pointing
to the subscription-only TRC Web Thermo Tables).

**Cross-check against the tertiary PubChem value** (0.35 cP at 20 °C,
Kirk-Othmer via PubChem, first-pass finding): extrapolating Grande et al.'s
25→30 °C trend backward toward 20 °C by eye is consistent with a value
modestly above 0.3417 mPa·s, and 0.35 cP is in that direction — the two are
consistent, though this is a qualitative check, not a fitted extrapolation
(no extrapolation is asserted as a citation-backed number).

### 3.3 Water+ACN mixtures across the full composition range, 25–45 °C

Source: Grande et al. 2006, `PureOrMixtureData` block 3 (2 components, 2
variables: temperature and mole fraction of ACN), 80 data points (16
compositions × 5 temperatures). Method: same Ubbelohde-type capillary
viscometer as §3.2 (`CAPTUB:UFactor:2`). Uncertainty: combined expanded
uncertainty at 95% confidence, stated **per data point** in the source XML
(propagation of evaluated standard uncertainties, per the source's own
`CombinedUncertainty` metadata) — not a single blanket figure.

Composition is converted here from the source's mole fraction x(ACN) to
volume fraction φ(ACN) — this repo's internal convention — using the
"as-prepared" definition: φ = V(ACN)/(V(ACN)+V(water)), where each pure
component's volume is computed from its own mass and **pure-component**
density at that temperature (not the mixture's actual, contracted volume).
This matches how a mobile phase is actually made up on an HPLC instrument
(metering pure-solvent volumes before they mix), and is therefore the
operationally correct match to this app's %B/φ convention — **but it is a
conversion performed in this research task, not a value read from Grande et
al. 2006 directly**, and it uses input densities from two different sources
(ACN density: Grande et al. 2006 itself, §3.2; water density: NIST WebBook,
IAPWS-95 formulation, read at the nearest whole-Kelvin grid point — 298,
303, 308, 313, 318 K rather than exact ...15 K, an offset of ≤0.15 K, judged
negligible given water's density-vs-T slope but flagged here rather than
silently absorbed) and standard atomic weights (M(H₂O)=18.0153 g/mol,
M(CH₃CN)=41.0519 g/mol, IUPAC/CIAAW standard values). Because this binary
system has a known negative excess volume on mixing (corroborated, though
not quantified here, by Handa & Benson 1981 and Davis 1983, §2), the
"as-prepared" φ computed this way is **not** the same as the true fractional
volume of the mixed solution — that distinction is a real one for anyone
consuming this table, not a rounding nuance (§7).

| x(ACN), mole fr. | φ(ACN), volume fr. (this-task conversion) | η at 25 °C | η at 30 °C | η at 35 °C | η at 40 °C | η at 45 °C |
|---|---|---|---|---|---|---|
| 0.0000 | 0.0000 | 0.8901 ± 0.0112 | 0.7973 ± 0.0102 | 0.7193 ± 0.0093 | 0.6530 ± 0.0086 | 0.5961 ± 0.0080 |
| 0.0510 | 0.1359 | 0.9849 ± 0.0122 | 0.8799 ± 0.0111 | 0.7964 ± 0.0102 | 0.7208 ± 0.0093 | 0.6522 ± 0.0086 |
| 0.1169 | 0.2791 | 0.9567 ± 0.0119 | 0.8628 ± 0.0109 | 0.7842 ± 0.0100 | 0.7155 ± 0.0093 | 0.6524 ± 0.0086 |
| 0.1971 | 0.4180 | 0.8743 ± 0.0110 | 0.7931 ± 0.0101 | 0.7218 ± 0.0094 | 0.6628 ± 0.0087 | 0.6069 ± 0.0081 |
| 0.2728 | 0.5232 | 0.7891 ± 0.0101 | 0.7152 ± 0.0093 | 0.6502 ± 0.0086 | 0.5951 ± 0.0080 | 0.5462 ± 0.0075 |
| 0.3601 | 0.6221 | 0.6953 ± 0.0091 | 0.6298 ± 0.0084 | 0.5737 ± 0.0078 | 0.5266 ± 0.0073 | 0.4853 ± 0.0068 |
| 0.4417 | 0.6983 | 0.6061 ± 0.0081 | 0.5574 ± 0.0076 | 0.5121 ± 0.0071 | 0.4744 ± 0.0067 | 0.4435 ± 0.0064 |
| 0.5204 | 0.7604 | 0.5387 ± 0.0074 | 0.4972 ± 0.0069 | 0.4606 ± 0.0065 | 0.4317 ± 0.0062 | 0.4089 ± 0.0060 |
| 0.6012 | 0.8152 | 0.4802 ± 0.0068 | 0.4473 ± 0.0064 | 0.4189 ± 0.0061 | 0.3959 ± 0.0058 | 0.3783 ± 0.0056 |
| 0.6671 | 0.8543 | 0.4415 ± 0.0063 | 0.4138 ± 0.0060 | 0.3902 ± 0.0058 | 0.3698 ± 0.0056 | 0.3556 ± 0.0054 |
| 0.7398 | 0.8927 | 0.4064 ± 0.0060 | 0.3831 ± 0.0057 | 0.3633 ± 0.0055 | 0.3471 ± 0.0053 | 0.3353 ± 0.0052 |
| 0.8253 | 0.9325 | 0.3722 ± 0.0056 | 0.3545 ± 0.0054 | 0.3386 ± 0.0052 | 0.3256 ± 0.0051 | 0.3159 ± 0.0050 |
| 0.8860 | 0.9579 | 0.3561 ± 0.0054 | 0.3405 ± 0.0052 | 0.3259 ± 0.0051 | 0.3142 ± 0.0050 | 0.3039 ± 0.0048 |
| 0.9389 | 0.9782 | 0.3478 ± 0.0053 | 0.3330 ± 0.0052 | 0.3173 ± 0.0050 | 0.3061 ± 0.0049 | 0.2963 ± 0.0048 |
| 0.9990 | 0.9997 | 0.3418 ± 0.0053 | 0.3281 ± 0.0051 | 0.3130 ± 0.0049 | 0.3010 ± 0.0048 | 0.2900 ± 0.0047 |
| 1.0000 | 1.0000 | 0.3417 ± 0.0053 | 0.3280 ± 0.0051 | 0.3129 ± 0.0049 | 0.3009 ± 0.0048 | 0.2899 ± 0.0047 |

(η in mPa·s = cP; uncertainty is combined expanded uncertainty, 95% CI, per
source point.)

### 3.4 Coverage achieved, stated plainly

| Composition | 25–45 °C (5 °C steps) | 50–80 °C |
|---|---|---|
| Full range, φ = 0→1 (16 points) | ✅ Grande et al. 2006, via NIST ThermoML | ❌ not found in either pass |
| φ = 0 (pure water) only | ✅ (also NIST/IAPWS to 80 °C, §3.1) | ✅ NIST/IAPWS reference formulation only |
| φ = 1 (pure ACN) only | ✅ Grande et al. 2006 | ❌ not found |

The temperature range is the one part of the ticket's ask (25–80 °C) not
met. See §7.

---

## 4. Interpolating form

### 4.1 Why not a published correlation

Katti et al. 2008's paper is, by title, exactly the single-expression
η(T,composition) correlation this ticket describes — and it remains
completely inaccessible (§2): article, ACS Supporting Information, and NIST
ThermoML archive all returned nothing. No "Chen–Horváth" viscosity
correlation could be shown to exist under that name (§2). So the form below
is a fit performed in this research task against the §3.3 data, **not** a
citation to a published correlation — flagged as such throughout, per the
ticket's own fallback ("failing that, fit a polynomial to the tabulated
primary points myself").

### 4.2 Polynomial in φ, fit per isotherm

For each of the five measured temperatures, a degree-4 polynomial in φ was
fit by ordinary least squares to the 16 points in §3.3 (computed in this
task; arithmetic reproducible from §3.3's table):

η(φ) ≈ a₄φ⁴ + a₃φ³ + a₂φ² + a₁φ + a₀ (η in mPa·s, φ = ACN volume fraction 0–1)

| T (°C) | a₄ | a₃ | a₂ | a₁ | a₀ |
|---|---|---|---|---|---|
| 25 | 0.2518 | 1.0545 | −2.8075 | 0.9439 | 0.8941 |
| 30 | 0.2567 | 0.8803 | −2.4683 | 0.8559 | 0.7997 |
| 35 | 0.0004 | 1.2689 | −2.5247 | 0.8447 | 0.7207 |
| 40 | −0.0787 | 1.2932 | −2.3561 | 0.7877 | 0.6532 |
| 45 | −0.2184 | 1.3799 | −2.1754 | 0.7078 | 0.5952 |

**Residual against the fitted-to data** (computed in this task, degree 4):

| T (°C) | RMS residual (mPa·s) | Max \|residual\| (mPa·s) | Max \|residual\| (% of value) |
|---|---|---|---|
| 25 | 0.0055 | 0.0117 | 1.67% |
| 30 | 0.0035 | 0.0070 | 1.30% |
| 35 | 0.0022 | 0.0041 | 0.94% |
| 40 | 0.0015 | 0.0020 | 0.59% |
| 45 | 0.0021 | 0.0047 | 0.97% |

The worst-case relative residual (1.67% at 25 °C) is on the same order as
the source data's own stated measurement uncertainty at those points
(1.2–1.6%, 95% CI, §3.3) — i.e. the degree-4 fit is about as good as the
underlying data supports; a higher-degree fit (degree 5, tried for
comparison) roughly halves the residual (worst case 0.79% at 45 °C) but
starts to fit noise given only 16 points, and a lower degree (3) is
measurably worse (worst case 1.93% at 25 °C). **Degree 4 is the recommended
form.** An implementation should carry the residual figures above as this
form's evidenced error, not a smaller number.

### 4.3 Temperature axis

Within 25–45 °C, the recommended approach is to **interpolate between the
five measured isotherms** (e.g. linearly or with a monotonic spline in T, at
fixed φ) rather than fit a global bivariate surface — five points 5 °C apart
is too few to responsibly fit a smooth T-dependence and extrapolate it, and
no published correlation coefficients (Katti et al. 2008's) could be
obtained to do this properly. **Extrapolating any of this beyond 45 °C, up
toward the ticket's 80 °C ceiling, is not supported by data found in this
research** — see §7. If a candidate run's temperature exceeds 45 °C, a
pressure-scaling rule consuming this document should flag that the
viscosity term is extrapolated/unverified, not silently extend the
polynomial.

---

## 5. Modifier note: formic acid / TFA

**Not found**, in either research pass. Searches combining "formic acid" /
"trifluoroacetic acid" with "viscosity," "mobile phase," "backpressure,"
"acetonitrile water," and "UHPLC eluent" (CrossRef, Semantic Scholar,
general web search) found no paper measuring viscosity of a
water/ACN/formic-acid or water/ACN/TFA ternary mixture at any concentration,
and no paper measuring aqueous formic acid's own viscosity vs. temperature.
The closest chromatography-adjacent hit (Gilar, Xie & Jaworski, *Anal.
Chem.* **82** (2010) 265–275) addresses how TFA concentration affects
retention *selectivity*, not viscosity or backpressure.

**What is not being claimed:** this document does not assert that 0.1%
formic acid or TFA has a "measured negligible" effect on viscosity — no
measurement was found either way. It is physically plausible by simple
dilution reasoning that adding ~0.1% v/v of a small-molecule acid to a
binary solvent perturbs bulk viscosity by much less than the water/ACN
composition swings this document quantifies in §3.3 (0.1% is roughly two
orders of magnitude smaller than those swings), but **this is inference, not
a citation**, and the honest status is **not tested**, not "tested and
found negligible."

---

## 6. Implications for pressure scaling

- **η(φ) is strongly non-monotonic and now quantified, not merely
  described.** At every one of the five measured temperatures, viscosity
  *rises* from the pure-water value before falling toward the pure-ACN
  value. At 25–40 °C the measured maximum on this composition grid is at
  φ≈0.136–0.138 (x(ACN)≈0.051), 10.4–10.7% above pure water at the same
  temperature (0.9849 vs 0.8901 mPa·s at 25 °C, for example); at 45 °C the
  grid maximum shifts to φ≈0.284 (x(ACN)≈0.117), 9.4% above pure water at
  45 °C (§3.3 table — all figures computed directly from that table in this
  task). Because these are grid maxima on a 16-point mesh, the true
  continuous maximum may sit anywhere between the two smallest measured
  compositions — its location is bounded, not pinned exactly, by this data.
  **A linear interpolation between pure-water and pure-ACN viscosity would
  underestimate pressure near the scouting-typical low-%B starting region by
  roughly 10%,** not merely be "approximate" — this is a direction-and-magnitude
  statement now backed by the §3.3 table, not an inference from the
  existence of a literature (which is all the first pass could offer).
- **The composition effect and the temperature effect are comparable in
  size over the range covered.** Pure water's viscosity falls from 0.890 to
  0.596 mPa·s (33%) from 25 to 45 °C (§3.1); over the same temperature span,
  the peak-viscosity composition (φ≈0.14) falls from 0.985 to (at φ≈0.14,
  45 °C — interpolating within the fitted isotherms) roughly 0.66–0.68
  mPa·s, a comparable fractional drop. A pressure-scaling rule that
  ignores column-temperature change even within this well-covered 25–45 °C
  band will be wrong by a similar order of magnitude to ignoring a
  20–40-percentage-point composition change.
- **φ must be defined the same way this document defines it before a number
  is plugged in.** The mixture table in §3.3 reports φ in this repo's
  volume-fraction convention only because of a conversion performed in this
  task (§3.3) from the source's mole fraction — using **pure-component**
  densities at each temperature (the "as-prepared," operational definition
  of %B, matching how a pump actually meters solvent), not the mixture's
  true contracted volume (this system has a documented negative excess
  volume, per Handa & Benson 1981 and Davis 1983, §2, though its magnitude
  was not itself retrieved or used here). Whoever consumes this table should
  preserve that distinction rather than treat φ as self-evidently "the %B
  the operator dialed in."
- **Temperature coverage stops at 45 °C — 45 to 80 °C is unverified
  territory for the mixture.** Only the pure-water endpoint (§3.1,
  NIST/IAPWS) and the pure-ACN endpoint (§3.2, capped at 45 °C, no source
  found above that) have any data in that range, and even those don't cover
  the full 45–80 °C span for ACN. A pressure-scaling rule must either
  refuse to predict pressure for a candidate above 45 °C without an
  explicit "extrapolated, unverified" flag, or be re-derived once a source
  covering that range is found (§7).
- **Dwell volume is unaffected by any of this.** This project's dwell
  volume is a fixed instrument constant (0.375 mL, per project memory:
  "Dwell volume is fixed at 0.375 mL"), never data-tuned — viscosity feeds
  the column pressure term, not the dwell term.
- **A modifier-viscosity term is not currently justified by data (§5).**
  Until a source is found, a pressure-scaling rule should either ignore
  modifier concentration entirely (documented as an assumption) or expose it
  as an explicit, separately-flagged unknown.

---

## 7. Open points

Ranked by how much each blocks a usable pressure-scaling implementation:

1. **Temperature range 45–80 °C is unresolved for the mixture.** No primary
   source located in either pass covers this span for water+ACN mixtures
   (Wode & Seidel's confirmed range, 20–40 °C, doesn't extend it either).
   Katti et al. 2008 (§2) is the best-named candidate to close this, if
   institutional/ILL access can be obtained; the Landolt-Börnstein Wohlfarth
   (2008) compilation is the second-best target.
2. **Katti et al. 2008's correlation remains fully inaccessible** — article,
   ACS Supporting Information, and NIST ThermoML archive all checked and all
   negative (§2). This is the most consequential single gap: it is, by
   title, a ready-made answer to §4's exercise.
3. **Composition convention (mole vs. volume fraction) for the three
   originally-named papers (Moreau & Douhéret 1975; Wode & Seidel 1994;
   Saleh et al. 2006) was never confirmed**, since none were readable. Not
   load-bearing for this document (§3.3 uses Grande et al. 2006, whose
   convention — mole fraction — was directly read from the ThermoML
   metadata), but relevant if those three papers are ever obtained and
   merged into this table.
4. **The mole→volume-fraction conversion (§3.3) is a same-task computation,
   not a sourced table.** It rests on two different sources' pure-component
   densities (Grande 2006 for ACN, NIST/IAPWS-95 for water, the latter read
   at a ≤0.15 K offset from the exact isotherm temperatures) and on standard
   atomic weights. Anyone re-deriving this should re-check that chain rather
   than take φ in §3.3 as itself a primary-sourced number.
5. **The true (mixed, contracted) volume fraction is not what §3.3
   tabulates** — only the "as-prepared" one (§3.3, §6). The magnitude of the
   difference (this system's excess volume) was not retrieved from Handa &
   Benson 1981 or Davis 1983, only its existence and sign (contraction) was
   noted from their titles/abstracts framing. If a pressure-scaling rule
   needs the true mixed volume fraction rather than the as-prepared one,
   this is an additional unresolved gap.
6. **Modifier (formic acid/TFA) viscosity effect: no data found at all**
   (§5), not even a qualitative measurement outside the specific 0.1% level
   asked about.
7. **Landolt-Börnstein (Wohlfarth 2008) was identified but never opened**
   in either pass (§2) — flagged again here as the most promising single
   next fetch, since compilations of this kind typically publish a
   recommended smoothing equation together with each primary source's
   deviation from it.
8. **Riddick & Bunger's "Organic Solvents" is confirmed to exist on
   archive.org but access-restricted** (Controlled Digital Lending) — not
   borrowed, per the constraint against circumventing access controls; left
   genuinely unopened rather than assumed empty or assumed to contain the
   answer.
9. **CORE.ac.uk's aggregator search was blocked (HTTP 403) without an API
   key** and not pursued further — a legitimate additional green-OA search
   route that a future pass with a free API key could still try.
10. **IAPWS-2008's own stated uncertainty for pure water was never
    retrieved** from Huber et al. 2009 directly (§2, §3.1) — the WebBook
    page consumed here doesn't surface it.
11. **Thompson, Kaiser & Jorgenson 2006** (§2) is a promising, unopened
    lead specifically because its abstract states composition in %v/v
    directly, at the full 0–100% range, which would let this table's φ
    values be checked against a source that never needed the mole→volume
    conversion in §3.3 — worth fetching if access becomes available.

**What can be relied on as-is:** the full §3.3 mixture table (16 compositions
× 5 temperatures, both raw mole-fraction values and the same-task
volume-fraction conversion, each point's stated measurement uncertainty),
the §3.1 pure-water table (cross-validated by two independent sources), the
§3.2 pure-ACN table, and the §4.2 polynomial fit and its residuals — all
independently re-parsed from the raw retrieved ThermoML XML and NIST WebBook
fetches in this pass (§9), not taken on trust from a prior summary.

---

## 8. What was not independently re-verified

For completeness, two things in this document rest on the research
sub-agents' reports rather than a fetch repeated in this final pass: (a) the
closed-access status of Moreau & Douhéret 1975, Wode & Seidel 1994, and
Saleh et al. 2006 (Unpaywall checks) and of Katti et al. 2008 (Unpaywall +
Semantic Scholar + direct 403s, both passes); (b) the archive.org searches
for International Critical Tables and Riddick & Bunger. Both rest on the
pattern of two independent registries agreeing on the same conclusion (e.g.
Katti 2008 closed per both an Unpaywall-style check and a Semantic Scholar
check), which is treated here as reasonable corroboration for a closed-access
finding, though it was not re-run a third time in this final pass.

---

## 9. How this final pass verified the numbers

Every number in §3 and §4 above was re-derived in this final pass directly
from two raw files fetched fresh (not taken from a research sub-agent's
prose summary on trust):

- `https://trc.nist.gov/ThermoML/10.1016/j.jct.2005.08.009.xml` — parsed
  with Python's `xml.etree.ElementTree` against the ThermoML XML namespace,
  reading `PureOrMixtureData` blocks 1–4 (pure-ACN viscosity, pure-ACN
  density, mixture viscosity, mixture density) directly, including each
  point's `nCombExpandUncertValue` for the stated 95%-CI uncertainty.
- NIST Chemistry WebBook's fluid-properties calculator for water (CAS
  7732-18-5), fetched directly for both the viscosity table (§3.1) and the
  density values used in the §3.3 volume-fraction conversion.
- The mole→volume-fraction conversion and the degree-3/4/5 polynomial fits
  and their residuals (§3.3, §4.2) were computed directly from those two
  fetches in this pass, with the arithmetic shown in §3.3–4.2 reproducible
  from the tabulated inputs.
