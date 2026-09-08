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
