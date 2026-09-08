# Column and instrument temperature/pressure limits — CORTECS UPLC Shield RP18 / Acquity H-Class

## Question

What are the temperature and pressure limits of the Waters CORTECS UPLC Shield RP18 column
(2.1 x 100 mm, 1.6 µm, solid-core / superficially-porous packing) as the vendor (Waters) states
them, including any dependence on pH or mobile-phase composition? What is the column-heater
temperature range of a Waters Acquity UPLC H-Class instrument?

This research supports a planned bench temperature series at 25–80 °C in 5 °C steps on this exact
column/instrument. The column's stated limit is the hard bound for that series; the H-Class heater
range is a separate, instrument-side bound.

## Result summary (read this first)

**No numeric temperature limit, pressure limit, or pH range for this column, and no numeric
column-heater/Column-Manager temperature range for the Acquity UPLC H-Class, could be retrieved
from any source in this pass.** Every Waters primary-source URL identified (the CORTECS product
page, the CORTECS Care and Use Manual, the Acquity UPLC H-Class product/spec page, and the
support.waters.com document search) was either unreachable (timeout) or access-walled (SSO login
redirect) from this research environment. Secondary distributor pages (VWR, Fisher Scientific,
Sigma-Aldrich) also timed out or returned empty content. Web search was exhausted before any
Waters-specific query could be run, and DuckDuckGo returned a CAPTCHA wall. Bing search (fetched
via its RSS output) returned only generic/irrelevant results for the specific numeric queries
attempted (see Sources and Open points below) and never surfaced usable numeric spec text.

The only Waters content actually retrieved successfully was one Knowledge Base article comparing
BEH C18 and CORTECS C18 packings, which describes particle/pore chemistry only — it contains no
temperature, pressure, or pH figures.

**Every number in the "What this bounds" section below is therefore marked not verified.** This
report should be treated as a documented blocked-research pass, not as a source of usable limits.

## Sources

| Source | URL | Access date | Verbatim wording |
|---|---|---|---|
| Waters CORTECS product page (primary, title only — content not retrievable) | https://www.waters.com/nextgen/us/en/products/columns/cortecs-columns.html | 2026-09-08 | Page title returned by search index: "CORTECS Solid Core C18 Columns \| Waters". No body content was retrievable (see Blocked fetch attempts) — no temperature/pressure/pH wording obtained. |
| Waters Knowledge Base — BEH C18 vs CORTECS C18 packings (primary, fetched successfully) | https://support.waters.com/KB_Chem/Columns/WKB51838_What_is_the_difference_between_BEH_C18_and_CORTECS_C18_packings | 2026-09-08 | "Silica-based, superficially porous, solid core particle" (CORTECS C18); "Fully porous, bridged ethylene hybrid (BEH) particle" (BEH C18); CORTECS pore diameter given as 90 Å vs BEH's 130 Å. This article does **not** state any temperature, pressure, or pH limit for either packing. |
| Waters Knowledge Base home / KB_Chem category (primary, fetched successfully, navigation only) | https://support.waters.com and https://support.waters.com/KB_Chem/Columns | 2026-09-08 | Category listing only; no CORTECS Care and Use Manual article was found linked from these category pages (only two unrelated column-care articles were listed: one on detergents and one on BEH vs. CORTECS packings). |

### Blocked / unreachable fetch attempts

| URL attempted | What happened |
|---|---|
| https://www.waters.com/nextgen/us/en/products/columns/cortecs-columns.html | Timed out (60 s) on every direct fetch attempt (3 attempts). No page body content retrievable. |
| https://www.waters.com (bare domain) | Timed out (60 s). |
| https://www.waters.com/nextgen/us/en/products/instruments/hplc-systems/acquity-uplc-h-class-system.html | Timed out (60 s). |
| https://www.waters.com/nextgen/us/en/products/instruments/acquity-uplc-h-class.html | Timed out (60 s). |
| https://www.waters.com/nextgen/us/en/shop/columns/186007095-cortecs-uplc-shield-rp18-column-130-1-6-m-2-1-mm-x-100-mm-1-pk.html (guessed part-number URL; part number not independently confirmed) | Timed out (60 s). |
| https://www.waters.com/nextgen/us/en/search-results.html?q=CORTECS+Shield+RP18... | Timed out (60 s). |
| https://www.waters.com/waters/en_US/CORTECS-Columns/nav.htm?cid=134761570 (legacy site path) | Timed out (60 s). |
| CORTECS Columns Care and Use Manual PDF — no URL located | Never located: no search performed in this pass (Bing/DuckDuckGo/direct fetch) surfaced a PDF link for this document, despite it being referenced by name in the task. This document needs a dedicated follow-up pass. |
| https://support.waters.com/@app/auth/3/login?returnto=...%2FSearch%3Fq%3DCORTECS... (support.waters.com's own search) | Redirected to a Microsoft Entra/SAML SSO login page (login.microsoftonline.com) — the support-portal search requires authentication in this environment; not followed further per instructions (no credential/auth workaround attempted). |
| https://duckduckgo.com/html/... (search) | Returned a "select all squares with a duck" CAPTCHA challenge page — no results obtainable without solving it; not attempted. |
| https://www.vwr.com/store/product/13439478/cortecs-uplc-shield-rp18-columns-waters (secondary, guessed URL) | Returned an empty page body (no extractable text) — likely a JS-rendered storefront the fetcher could not execute. |
| https://www.fishersci.com/shop/products/cortecs-uplc-shield-rp18-column-130-1-6-mm-waters/p-7692130 (secondary, guessed URL) | Timed out (connection timeout). |
| https://www.sigmaaldrich.com/US/en/product/waters/186007095 (secondary, guessed part number) | Timed out (60 s). |
| http://web.archive.org/web/.../cortecs-columns.html and CDX API queries on web.archive.org | Tool-level block: "Claude Code is unable to fetch from web.archive.org" (this domain is disallowed for WebFetch in this environment, independent of any Waters access issue). Only the sibling `archive.org/wayback/available` lookup endpoint worked, and it returned a snapshot URL for the CORTECS product page that could not itself be fetched. |
| WebSearch tool (general) | This session's web-search quota was already exhausted (200/200) before any query for this task could run; no WebSearch results were obtained for this research at all. |
| Bing (via WebFetch on bing.com/search, RSS output format) | Reachable, but for the specific technical queries used (CORTECS temperature/pressure/pH, "Column Manager" temperature range, "H-Class" spec sheet), it returned either a small fixed set of generic CORTECS-brand/unrelated-company results or, for the "H-Class"/"Acquity" queries, results for the unrelated word "Acuity"/letter "H" — no page containing a numeric spec was surfaced by search in this pass. |

## Findings

- **Temperature limit (column):** Not verified. No Waters source reachable in this pass stated a numeric maximum operating temperature for the CORTECS UPLC Shield RP18 (2.1 × 100 mm, 1.6 µm) column. (See Sources table — the only successfully fetched Waters page, row 2, contains no temperature figure; the product page and Care and Use manual that would normally carry this figure were unreachable — see Blocked fetch attempts.)
- **Pressure limit (column):** Not verified. No numeric maximum pressure (column-specific or system-level) was obtained from any source. Whether it depends on temperature, and whether it differs from an instrument/system pressure limit, is likewise not verified.
- **pH dependence / mobile-phase dependence:** Not verified. No source reachable in this pass stated a pH operating range or any statement of temperature/pressure limits varying with pH or solvent for this column.
- **Acquity H-Class column-heater (Column Manager) temperature range:** Not verified. No Waters product page, spec sheet, or system guide was reachable; no numeric heater range (upper or lower bound) was obtained from any source.

## What this bounds for the 25–80 °C series

No numbers were verified for either bound, so **none of 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75,
or 80 °C can currently be classified as inside or outside the column's stated temperature limit or
the H-Class Column Manager's heater range.** Stating any of these 12 points as safe or unsafe would
require citing a number this pass could not obtain from a Waters source (or any other source) — per
the task's own rule against invented/estimated numbers, no such classification is given here. This
question must be answered by a follow-up pass (see Open points) before the temperature series is
run.

## Second pass (same session, orchestrator)

After the background sub-agent's WebSearch quota was exhausted, the orchestrating session tried a
second, independent round of fetches (2026-09-08) to see whether the block was agent-specific:

- `https://www.waters.com/nextgen/us/en/products/columns/cortecs-columns.html` — timed out (60 s) on
  two further attempts, same as the sub-agent's result. `www.waters.com` remains unreachable from
  this environment.
- `https://www.sigmaaldrich.com/US/en/search/cortecs%20shield%20rp18` — timed out (60 s).
- Bing search (`bing.com/search`, fetched via WebFetch) was queried several more times (`"CORTECS
  Columns Care and Use Manual" filetype:pdf`, `CORTECS "maximum pressure"`, `"18,000 psi" OR
  "15,000 psi"`, `site:waters.com "care and use" CORTECS pdf`, `site:support.waters.com CORTECS
  pressure temperature`, `site:waters.com H-Class "column manager" specifications`, `"Acquity"
  "H-Class" "Column Manager" specification sheet temperature`). None surfaced a page with a numeric
  temperature, pressure, or pH figure. One snippet (Bing result for the CORTECS product page) read,
  verbatim as far as it was rendered: *"The CORTECS Columns family redefines efficiency in liquid
  chromatography with its solid-core technology, designed to meet the …"* — truncated by Bing's own
  snippet rendering before any numeric claim; the source page itself could not be fetched to see the
  rest. `site:` search operators were not honored reliably by Bing through this fetch path (results
  for other, unrelated domains were returned instead), so site-restricted search could not be relied
  on either.
- This session's own WebSearch tool call quota was also already exhausted (200/200) at the time of
  this second pass, so no native web search (as opposed to fetching Bing's HTML output) was
  available in this pass either.

This second pass reached the same negative result as the sub-agent's: no primary Waters document
with the target numbers was retrievable in this research environment, and no stealth/bot-evasion
technique was attempted, per instructions. The blockers are environmental (network timeouts on
`www.waters.com`, an SSO wall on `support.waters.com`'s search, a CAPTCHA wall on DuckDuckGo, and
exhausted WebSearch quota) rather than anything resolvable by more querying within this session.

## Open points

- **The single most important gap:** the Waters "CORTECS Columns Care and Use Manual" (the document
  the task specifically named as the expected primary source for the temperature/pressure/pH
  limits) was never located or fetched. No URL for it was found via Bing search, and general Waters
  KB browsing did not surface it. This needs a dedicated follow-up pass — ideally starting from a
  literature/document search directly on waters.com once that domain is reachable, or from Waters
  customer support, rather than open web search.
- **www.waters.com (the "nextgen" site) was unreachable for every attempted page in this pass** —
  the CORTECS product page, the Acquity H-Class product page, and a guessed part-number shop page
  all timed out (60 s) on every attempt (2–3 attempts each). This looks like a JS-rendering/loading
  issue for this fetch environment rather than an explicit 403/CAPTCHA, but the practical effect is
  the same: this domain needs an authorized follow-up pass (e.g., a real browser session) to read.
- **support.waters.com's own document search requires SSO login** (redirects to
  login.microsoftonline.com) in this environment — its Knowledge Base *category* pages are
  browsable without login, but they did not list a CORTECS Care and Use Manual article, and the one
  CORTECS-specific article found (BEH vs. CORTECS packing chemistry) has no operating-limit numbers.
- **web.archive.org is blocked at the tool level** in this environment (distinct from any
  Waters-side issue), so the Wayback Machine could not be used as a fallback route to an archived
  copy of the CORTECS product page, even though a snapshot was confirmed to exist via the
  `archive.org/wayback/available` lookup.
- **VWR, Fisher Scientific, and Sigma-Aldrich distributor pages** (secondary sources that might
  reproduce Waters' own spec figures) were guessed at plausible URLs (part numbers were not
  independently confirmed) and all failed (timeout or empty JS-rendered body) — these need
  re-attempting with confirmed part numbers and/or a different fetch method.
- **This session's WebSearch quota was already exhausted (200/200) before this task began**, so no
  general web search was available at all; all search in this pass was done indirectly by fetching
  Bing's search-result page, which for these specific technical queries returned mostly
  generic/irrelevant hits rather than the target documents. A fresh session with search quota
  available, or a manual driver-side search, would likely do much better.
- **The exact part number** for "CORTECS UPLC Shield RP18 Column, 130Å, 1.6 µm, 2.1 mm × 100 mm"
  was never confirmed from a Waters source in this pass; the number used in one guessed URL
  (186007095) is unverified and should not be relied on.
- No information was found, verified or otherwise, on whether the column's temperature/pressure
  limits differ by particle size or packing variant within the CORTECS Shield RP18 line — this
  remains an open question for the follow-up pass.
- **Recommended follow-up:** an authorized pass (driver's own browser session, or an explicitly
  authorized stealth/anti-bot pass per this ticket's own contingency clause) against
  `www.waters.com`'s CORTECS product page and the Acquity H-Class product page, plus a direct
  request to Waters technical support for the CORTECS Columns Care and Use Manual PDF, since neither
  a plain fetch nor open web search reached it in two independent passes in this environment.

## Third pass (orchestrator, 2026-09-08): a Waters primary source held locally

The two web passes above found nothing because waters.com would not serve a page. A Waters
primary document was already on the driver's disk: the **Waters Columns, Analytical Standards
& Reagents Selection Guide** wallchart, document **720002241EN Rev. E**, "©2026 Waters
Corporation. March 26-15086" (local copy: `Exploration/waters-wallchart-WatersColumnsAnalyticalStandardsReagentsSelectionGuide-720002241.pdf`,
untracked, not in the repository). Text extracted with `pdftotext -layout`; the CORTECS
table is on page 1 under "CORTECS™ UPLC™, UHPLC, and HPLC Columns".

### What the wallchart says, verbatim, for the Shield RP18 row

| Column | Ligand density | Carbon load | Endcapped | USP class | pH range | Temperature limits | Surface area | Particles |
|---|---|---|---|---|---|---|---|---|
| CORTECS Shield RP18 | 3.2 µmol/m² | 6.4 % | Yes | L1 | **2–8** | **Low pH = 60 ˚C, High pH = 45 ˚C** | 100 m²/g | UPLC 1.6 µm, UHPLC/HPLC 2.7 µm |

Bonding text on the same row: "Monofunctional embedded polar C18, fully endcapped, bonded to
a silica solid-core substrate." The same two temperature figures (60 ˚C at low pH, 45 ˚C at
high pH) appear on every CORTECS reversed-phase row on the chart (C18, C18+, T3, C8, Phenyl);
only the HILIC row differs (45 ˚C at both).

### What this settles and what it does not

- **Temperature limit, verified.** 60 ˚C at low pH, 45 ˚C at high pH. The chart does not define
  where "low" ends and "high" begins; the pH range column says 2–8.
- **Pressure limit: still not verified.** The wallchart carries no pressure column.
- **H-Class heater range: still not verified.** Not an item the wallchart covers.
- **The lab's mobile-phase pH is not recorded in `validation/method.csv`.** `validation/PROTOCOL.md`'s
  worked example assumes A = 0.1 % formic acid in water, which is low pH; if that is the lab
  method, the 60 ˚C figure is the bound. The modifier should be recorded in `method.csv` before the
  temperature series is designed (raise on the bench-design ticket).

### What this bounds for the 25–80 ˚C series

Assuming a low-pH mobile phase: **25, 30, 35, 40, 45, 50, 55, 60 ˚C are inside the stated limit**;
65, 70, 75 and 80 ˚C are above it and would be run against the vendor's stated bound. At a
high-pH mobile phase the inside set shrinks to 25–45 ˚C. The wallchart gives no margin
guidance, so none is claimed here.

## Fourth pass (2026-09-08): stealth-browser pass on waters.com

The driver authorized a stealth-browser pass (`playwright` + `playwright-stealth`,
`p.chromium.launch(channel="chrome", headless=True)`) against `www.waters.com` and
`support.waters.com` to resolve the two remaining open points: the CORTECS Shield RP18
column's maximum operating pressure, and the Acquity UPLC H-Class column-heater/Column
Manager temperature range. This pass succeeded on both counts, using a Waters primary
source in each case.

### How the documents were found

A direct stealth-browser fetch of the CORTECS product page,
`https://www.waters.com/nextgen/us/en/products/columns/cortecs-columns.html` (2026-09-08),
returned HTTP 200 (previous passes had timed out on this domain; a real Chrome instance
with stealth patches was not blocked). The rendered page's "Support" section names Waters'
document-search API directly in its markup
(`data-base-url="https://prodservices.waters.com/api/waters/v1/search"`,
`data-search-v2-url="https://prodservices.waters.com/api/waters/v2/search"`). Calling that
same API in-page (`fetch(...)` executed via `page.evaluate`, so it ran with the site's own
session/cookies) with `keyword=CORTECS Care and Use Manual` returned Waters' own search
index, including the current CORTECS Care and Use Manual's PDF path. The same API, queried
with `keyword=Acquity UPLC H-Class specifications`, returned the current Acquity UPLC
H-Class System Specifications PDF path. Both PDFs were then fetched with
`context.request.get(url)` inside the same browser context (having first navigated to a
waters.com page to establish a session) — a plain, unauthenticated `curl`/`fetch` of the
same PDF URLs (tried in the third pass, for unrelated document numbers) had returned an
Akamai "Access Denied" page, so the browser context was necessary here too. Both PDFs
downloaded as valid, readable `application/pdf` bytes (1,936,240 bytes and 279,861 bytes
respectively) and needed no decryption workaround — `pdftotext -layout` extracted their
text directly.

### URLs fetched and access date (2026-09-08)

| URL | What it is | Result |
|---|---|---|
| `https://www.waters.com/nextgen/us/en/products/columns/cortecs-columns.html` | CORTECS product page | HTTP 200 via stealth browser (previously timed out) |
| `https://prodservices.waters.com/api/waters/v2/search?keyword=CORTECS%20Care%20and%20Use%20Manual&isocode=en_US&page=1&rows=10` | Waters document-search API | HTTP 200, JSON, 1,709 matches; top hit is the current CORTECS manual |
| `https://prodservices.waters.com/api/waters/v1/search?keyword=Acquity%20UPLC%20H-Class%20specifications&isocode=en_US&page=1&rows=10` | Waters document-search API | HTTP 200, JSON, 5,470 matches; top hit is the current H-Class spec document |
| `https://www.waters.com/content/dam/waters/en/support/usermanuals/2025/720008932/720008932.pdf` | CORTECS and CORTECS Premier Care and Use Manual (PDF) | Downloaded, 1,936,240 bytes, `application/pdf`, text extracted with `pdftotext -layout` |
| `https://www.waters.com/content/dam/waters/en/support/usermanuals/2010/USRM10144203/acquity_h-class_h-class_bio_system_spec.pdf` | ACQUITY UPLC H-Class and H-Class Bio System Specifications (PDF) | Downloaded, 279,861 bytes, `application/pdf`, 10 pages, text extracted with `pdftotext -layout` |

### Fact 1 — CORTECS Shield RP18 maximum operating pressure: verified

**Source:** *CORTECS and CORTECS Premier Columns Care and Use Manual*, document
**720008932EN, Rev. A**, "©2025 Waters Corporation. June 25-14178" (Waters Corporation, 34
Maple Street, Milford, MA 01757). This is the exact "CORTECS Columns Care and Use Manual"
the original task named as the expected primary source, and which the first three passes
could not locate.

Verbatim, section "e. Pressure":

> "Table 2 summarizes the pressure limits of CORTECS and CORTECS Premier Columns based on
> particle size and column internal diameter.
> Note: Working at the extremes of pressure, pH and/or temperature will result in shorter
> column lifetimes."

Table 2 ("Maximum Tolerated Operating Pressures for CORTECS and CORTECS Premier Columns"),
verbatim, the row for the CORTECS Shield RP18's particle size and column i.d.:

> "Particle Size: 1.6 µm | Column i.d.: 2.1 mm and 3.0 mm | Maximum Tolerated Operating
> Pressure: 18,000 psi (1241 bar or 124 MPa)"

This is a particle-size/i.d.-keyed limit shared across the whole CORTECS and CORTECS
Premier line (it is not stated separately per bonded phase), so it applies to the CORTECS
UPLC Shield RP18, 1.6 µm, 2.1 x 100 mm column named in the task. The figure is consistent
with the generic marketing claim already seen on the CORTECS product page in this same
pass ("sub-2-µm particles at 1241 bar pressures with UPLC Columns").

### Fact 2 — Acquity UPLC H-Class column-heater / Column Manager temperature range: verified

**Source:** *ACQUITY UPLC H-Class and H-Class Bio System Specifications*, document id
**USRM10144203, Revision B**, "Copyright © Waters Corporation 2010".

Verbatim, section "Column heater" (covering "the ACQUITY UPLC H-Class CH-A, H-Class 30-cm
column heater with active pre-heater (CH-30A), H-Class bioCH-A, and H-Class bioCH-30A"),
from the "Column heater performance specifications" table:

> "Column compartment temperature range: CH-A/CH-30A: 20 to 90 °C, in increments of 0.1 °C
> (control requires a setpoint of greater than ambient temperature +5 °C)"

Verbatim, section "Column manager" (covering "the ACQUITY UPLC H-Class CM-A, H-Class
auxiliary column manager (CM-Aux), H-Class bioCM-A, and H-Class bioCM-Aux"), from the
"Column manager performance specifications" table:

> "Column compartment temperature range (settable): 4 to 90 °C, in increments of 0.1 °C.
> Troughs are independently settable. Derating: The minimum achievable column compartment
> temperature set point must not be greater than 25 °C below ambient temperature."

So the H-Class family offers two distinct column-thermostatting modules with two different
settable ranges: the column heater (CH-A/CH-30A), 20–90 °C, and the column manager
(CM-A/CM-Aux), 4–90 °C — both subject to a derating clause tying the achievable low end to
ambient temperature (heater: setpoint must exceed ambient +5 °C; manager: setpoint must not
be more than 25 °C below ambient). Which module a given H-Class instrument is fitted with
is a configuration choice not stated in this document; this needs to be checked against the
lab's actual instrument configuration before it is used to bound the bench series. This same
document separately states the overall instrument's environmental operating temperature
(distinct from the column-heater/-manager range, and not to be confused with it): "Operating
temperature: 4 to 40 °C (39.2 to 104 °F)."

### Pressure-related wording near the temperature limits

The task asked that any pressure-related wording near the temperature limits be recorded
(e.g. reduced limits at elevated temperature). The CORTECS Care and Use Manual's temperature
section, verbatim ("f. Temperature"):

> "The maximum recommended temperature for CORTECS Columns is 60 º C. Higher temperatures
> can be used but may result in shorter column lifetimes. When operating with mobile phases
> that are close to the pH limits, lower temperatures are recommended to avoid short column
> lifetimes."

No numeric reduced pressure limit at elevated temperature is stated anywhere in this manual
— the only linkage given between pressure and temperature is the qualitative note quoted
under Fact 1 above ("Working at the extremes of pressure, pH and/or temperature will result
in shorter column lifetimes") and the qualitative statement just above (elevated temperature
near the pH limits shortens lifetime). Neither ties a numeric pressure derating to a
numeric temperature. The pressure table (Table 2) and the temperature statement are two
separate, independently-stated limits in this document, not a joint pressure-temperature
curve.

### A discrepancy with the third pass's wallchart figure, noted for the record

The third pass (above) read a **60 °C at low pH / 45 °C at high pH** split for the CORTECS
Shield RP18 row from the *Waters Columns, Analytical Standards & Reagents Selection Guide*
wallchart (720002241EN Rev. E). This fourth pass's primary source — the CORTECS Care and Use
Manual itself, 720008932EN Rev. A, dated 2025 — states a single, undifferentiated figure
instead: **"The maximum recommended temperature for CORTECS Columns is 60 º C,"** with no
pH-dependent split anywhere in its temperature section or its pH-limits table (Table 3,
which gives a flat pH range of 2–8 for the Shield RP18 with no accompanying temperature
column). This report does not attempt to resolve the discrepancy between the two Waters
documents; it records both, verbatim, with their document identifiers, so a human reader can
weigh the Care and Use Manual (the document type the original task named, and the more
recent of the two) against the wallchart's more specific-looking low-pH/high-pH split.

### What remains unverified (updated)

- **Column maximum operating pressure: now verified** — 18,000 psi (1241 bar / 124 MPa) for
  1.6 µm particles at 2.1 mm i.d., per the CORTECS Care and Use Manual, 720008932EN Rev. A.
- **H-Class column-heater/Column Manager temperature range: now verified**, but as two
  ranges rather than one — the CH-A/CH-30A column heater (20–90 °C) and the CM-A/CM-Aux
  column manager (4–90 °C), per the ACQUITY UPLC H-Class and H-Class Bio System
  Specifications, USRM10144203 Rev. B. **Which module is installed on the lab's actual
  H-Class instrument is not recorded anywhere in this repository and is not stated in this
  document** — this must be confirmed (e.g. from the instrument's own configuration label or
  purchase record) before either range is used as the instrument-side bound for the bench
  temperature series.
- **Column temperature limit: two Waters documents disagree** (60 °C flat, per the 2025 Care
  and Use Manual, vs. 60 °C low-pH / 45 °C high-pH, per the wallchart) — not resolved in this
  pass; see the discrepancy note above. The mobile-phase pH still is not recorded in
  `validation/method.csv` (carried over from the third pass), so which of the two readings
  (if either differs by application) would even apply is still unresolved on the lab-data
  side regardless of which document is preferred.
- **pH-dependence of the pressure limit specifically:** not addressed by either document —
  the pressure table (Table 2) is keyed only to particle size and column i.d., with no pH
  column, and no statement was found anywhere in the Care and Use Manual tying the pressure
  limit itself to pH or to temperature.
- No further Waters URLs were left unfetched for these two specific facts in this pass;
  the stealth-browser route resolved both.
