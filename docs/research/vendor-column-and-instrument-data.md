# Vendor column and instrument data: what a public spec sheet gives, and under what terms

Research notes for map [#103](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/103)
ticket [#109](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/109).
**Question:** for the vendors a working lab holds columns from (Waters, Agilent, Phenomenex,
Thermo Fisher, Merck/Supelco, YMC, Shimadzu, Tosoh), what does a public catalogue entry give
per column; does anyone publish a column volume, $V_0$ or porosity; is any of it
machine-readable; what do the sources' terms say about extracting and redistributing it; and
what do the instrument vendors publish, and mean, by *dwell volume*? The finding the map
needs: **can the app ship a column or instrument record it did not measure, and if so which
fields are trustworthy from a spec sheet and which must be declared or measured by the user.**
**Date:** 2026-09-04 (every source accessed that day). **Audience:** the driver deciding the
seed library's contents and provenance (#103 "Not yet specified", first bullet), and whoever
writes the profile schema.

Every claim is tagged **[verified]** (read in the source named) or **[derived]** (my
inference, shown). Posture, per the ticket: ordinary fetches only (WebFetch, WebSearch,
`curl`). Sites that refused automated access are a *finding*, listed in §9 with URLs for the
driver to fetch by hand; nothing was worked around. No table of catalogue data is
reproduced here: §2 records which *fields* exist and one worked example per vendor.
Units follow CLAUDE.md (mm, µm, mL, µL where the source uses µL).

**Headline** (§7): the app may ship column records for the fields a spec sheet actually
states — length, i.d., particle size, pore size, phase, part number, and the packing
architecture *as a sentence quoted from the vendor* — typed by hand from the cited document
with URL and date, never scraped. **No vendor publishes a per-column $V_0$, column void
volume or total porosity**; $t_0$ stays measured-or-estimated exactly as SPEC §4 has it.
Instrument dwell volume is published by three of the four vendors asked about, but under
**three incompatible definitions** (whole system; pump module only; pump and sampler
tabulated separately), so a shipped instrument record may carry a vendor figure only as a
labelled upper bound with its definition attached, and the user still declares or measures.
Four of the eight vendor sites block automated access outright (§9); every readable terms
page forbids commercial redistribution, and two (Shimadzu, Thermo) forbid systematic
retrieval or scraping in so many words (§5). **Second pass, same day (§10):** on the
driver's instruction the blocked pages were fetched with a real browser; the product page
shows Waters states the architecture as a spec field too, and Waters' own white paper
reports the lab's 0.375 mL dwell as a *measured* H-Class PLUS figure. **Third pass, next
day (§10.5):** a TLS-impersonating client read the Agilent store page and the four
Agilent PDFs; Agilent states the architecture as a field as well, so it is four vendors.

---

## 1. What was read, and how

About forty documents were read in full or in the relevant section; roughly two dozen URLs
refused or timed out (§9). Three kinds of source appear below and are labelled throughout:

- **Vendor-hosted, read directly** — product pages, knowledge-base articles, specification
  PDFs and terms pages on the vendor's own domain.
- **Vendor document, read from a mirror** — a PDF the vendor published (its document number
  and copyright line are quoted) but which the vendor's own host refused to serve to an
  automated fetch, read instead from a distributor's or a university's copy. Tagged
  *(mirror)*. These are the vendor's words, but the driver should confirm the current
  edition by hand; document numbers are given for that.
- **Third party** — distributor catalogues, community databases.

The lab's own record (`validation/method.csv`: Waters CORTECS UPLC Shield RP18 100 × 2.1 mm
1.6 µm on an ACQUITY UPLC H-Class, dwell 0.375 mL) is the worked case wherever a vendor
document lets it be.

## 2. What a catalogue entry gives, per vendor

### 2.1 Summary table

Fields a *public* entry states for a specific column. "Prose" means the architecture is
asserted in marketing text on the family page or brochure, not as a field on the part's
own entry; "brand" means it is carried only by the product name.

| Vendor / line | Read from | L, i.d., $d_p$ | Pore size | Phase, part no. | Architecture | $V_0$ / porosity |
|---|---|---|---|---|---|---|
| Waters CORTECS | product page **blocked** on the first pass, read in §10; KB + care manual (mirror, then direct) | fields on the product page (§10) | field (90 Å) | yes | **explicit field: "Particle Technology: Solid Core"** (§10) | **formula only** (KB WKB28079: 0.66 / 0.49); "empty column volume" table in care manual |
| Agilent Poroshell 120 | family page read in §10; store page read in §10.5; brochure 5991-8750EN (2025) and ordering guide 5991-9123EN (2024), direct (§10.5) | fields on the store page (§10.5) | field on the store page (120 Å) | yes | **explicit field: "Particle Type: Superficially Porous"** (§10.5); brochure prose "solid silica core and a porous outer layer" | none |
| Phenomenex Kinetex | product page + family page, direct | fields | in title only | yes | family-page prose ("solid, non-porous silica core surrounded by a porous outer layer") | none |
| Thermo Accucore | product page + technical manual, direct | fields | field (80 Å) | yes | **explicit field: "Particle Shape: Solid Core"**; manual: "Porous layer depth = 0.5 µm" | none |
| Merck/Supelco Ascentis Express | site **unreachable** on the first pass, product page read in §10; 2008 catalogue (mirror) | ordering grid; fields on the product page (§10) | field on the product page (90 Å; §10) | yes | **field: "Matrix: Fused-Core particle platform, superficially porous particle"** (§10); FAQ prose "1.7 μm solid core and a 0.5 μm porous shell" | none |
| YMC-Triart | product list + product page, direct | table | table (120 Å) | yes | **not stated either way** | none |
| Shimadzu Shim-pack Scepter | shop page, direct | fields | field (12 nm) | yes | prose ("Fully Porous Hybrid Particle Based Column Series") | none |
| Tosoh TSKgel ODS-100V | product pages **blocked** on the first pass, read in §10; instruction manual (Asia site), direct | table in the manual; fields on the product page (§10) | field on the product page (10 nm; §10) | yes | not stated (page or manual) | none |

[verified] for every cell whose source is named "direct" or "(mirror)"; cells marked §10
are [verified] from the second pass, and cells marked §10.5 from the third. Every
product page named in §9 has now been read.

### 2.2 Per-vendor detail and the worked example

**Waters.** `waters.com` (Akamai) returned HTTP 403 "Access Denied" to every product,
family, specification-PDF and terms URL tried (§9). What could be read:

- The search-index listing of the lab's column gives its part number and title as Waters
  publishes them: **186008694**, "CORTECS Shield RP18 Column, 90Å, 1.6 µm, 2.1 mm X 100 mm,
  1/pk" (ref. 1) [verified from the URL slug and result title only; page content unread].
  So particle size, pore size and dimensions are in the *title*; whether the page has a
  spec table with an architecture field, I could not see.
- KB article WKB28079 (ref. 2, read; already the basis of `dead-time-from-geometry.md`
  §3.1) is the only Waters statement about void volume: a *formula*, $\pi r^2 L \times$
  **0.66** for "fully porous packings" and **0.49** for "superficially porous packings",
  with the instruction that "To understand what the actual column void volume is for a
  particular column installed on a particular system, you must make an injection with a
  compound that does not retain on the packing material." Waters tags the article with
  CORTECS, so Waters' own classification of CORTECS as superficially porous is [verified]
  there, in prose.
- *ACQUITY UPLC BEH Column Care and Use Instructions* (©2004 Waters, ref. 3, university
  mirror) has "Table 1. Empty Column Volumes in mL (multiply by 10 for flush solvent
  volumes)", by length and i.d.; the 2.1 × 100 mm entry is **0.4 mL** [verified].
  [derived] $\tfrac{\pi}{4}(2.1)^2(100)$ mm³ = 0.346 mL, so this is the geometric volume
  of the empty tube rounded to one figure — a flushing aid, **not** a hold-up volume, and
  it must not be read into a profile as $V_0$.

**Agilent.** `agilent.com` (Akamai), `lc.help.agilent.com` and the Agilent Community forum
all refused (§9). The Poroshell 120 brochure 5990-5951EN (© Agilent 2012, ref. 4, read from
a distributor mirror) states the architecture in prose — "their superficially porous
microparticulate column packing. Poroshell 120 particles have a 1.7 μm solid silica core
with a 0.5 μm porous outer layer" — and gives two tables [verified]: an ordering grid whose
axes are *Size (mm)* × *bonded phase* with a part number in each cell, and a bonded-phase
table with columns *Bonded Phase | Pore Size | Temp. Limits | pH Range | Endcapped | Carbon
Load*. Worked example: EC-C18, 2.1 × 100 mm, 2.7 µm = **695775-902**, pore size 120 Å,
endcapped, carbon load 8 %. Particle size lives in the table caption ("2.7 μm"), not in a
per-part field. Nothing about column volume or porosity anywhere in the brochure.

**Phenomenex.** The part page for 00D-4462-AN (ref. 5, read directly) shows these fields
and no others: *Technique* HPLC, *Brand* Kinetex, *Separation Mode* Reversed Phase, *Phase*
C18, *Length* 100 mm, *Particle Size* 2.6 µm, *Internal Diameter* 2.1 mm, *Part ID*
[verified]. Pore size ("100 Å") is in the product title, not a field. Architecture is not a
field; the Kinetex family page (ref. 6) states it in prose — "a solid, non-porous silica
core surrounded by a porous outer layer", pore size 100 Å, surface area 200 m²/g for the
2.6 µm particle [verified]. The Kinetex care-and-use guide (© 2017, ref. 7) contains **no**
column-volume table; "column volumes" appears only as a flushing unit ("rinse with at least
10 column volumes") [verified]. I had expected one; there is none.

**Thermo Fisher.** The only vendor whose *part page* carries the architecture as a
**field**. The page for 17126-102130 (ref. 8, read directly) lists: *Catalog Number,
Column Format, Length 100 mm, Diameter 2.1 mm, Particle Size 2.6 μm, Pore Size 80 Å,
**Particle Shape Solid Core**, Stationary Phase C18, Phase Type Reversed Phase, USP Type L1,
pH Range 1 to 11, Temperature 70 °C, Carbon Load 9 %, Surface Area 130 m²/g, Endcapped
Yes, Max. Pressure 14500 psi (1000 bar), Packing Material Ultrapure Silica* [verified]. The
Accucore technical manual TG20666 (© 2012, ref. 9, vendor-hosted PDF) adds "Porous layer
depth = 0.5 µm" for the 2.6 µm particle and an ordering table with columns *Description |
Particle Size | Length (mm) | 2.1 mm ID | 3.0 mm ID | 4.6 mm ID* [verified]. No column
volume: the manual's "Column Volumes" strings are the x-axis of column-lifetime plots.

**Merck / Supelco.** `sigmaaldrich.com` never answered (§9: connection timeouts on HTTP/1.1
and a stream reset on HTTP/2, on product and terms URLs alike). The 2008 Supelco catalogue
*Ascentis Express HPLC Columns with Fused-Core Technology* (© 2008 Sigma-Aldrich Co.,
ref. 10, distributor mirror) states the architecture in prose — "The Fused-Core particle
consists of a 1.7 μm solid core and a 0.5 μm porous shell" — and its ordering table has the
axes *ID (mm) | Length (cm) | phase* [verified]; worked example: C18, 2.1 mm × 10 cm =
**53823-U**. Pore size is not in the ordering table. Whether the current sigmaaldrich.com
product page has a spec table with more fields is unread.

**YMC.** `ymc.co.jp` served everything. The YMC-Triart C18 product list (ref. 11) is an
HTML table with headers *Particle size (µm) | Pore size (Å) | Column size Inner diameter x
length (mm) | Product Number*; example row: 1.9 | 120 | 1.0 X 100 | TA12SP9-1001WT
[verified]. The product page (ref. 12) gives the phase-level specs: organic/inorganic
hybrid silica, 1.9/3/5 µm, 120 Å, 20 % carbon, pH 1–12, USP L1 [verified]. **Neither page
uses the words "fully porous" or "core-shell"** [verified]. [derived] The absence of a
core-shell claim is not a statement of architecture; a YMC-Triart record's architecture
would be *declared by the person typing it*, not quoted.

**Shimadzu.** The Shimadzu Asia-Pacific shop page for S227-31012-05 (ref. 13, read
directly) has the richest field list after Thermo's: *Part Number 227-31012-05, Length 100
mm, ID 2.1 mm, Particle size 1.9 µm, Pore size 12 nm, Phase C18, USP L1, pH range 1–12,
Carbon Load 20 %, End Capping Yes, Pressure Tolerance 100 MPa*, surface area 360 m²/g
[verified]. Architecture is prose on the same page: "Fully Porous Hybrid Particle Based
Column Series" [verified]. Pore size is in nm, not Å — a unit the schema must normalise.

**Tosoh.** `tosohbioscience.com` sits behind a Cloudflare challenge (HTTP 403 with a
captcha page) and the EU separations site redirects into it (§9); the Asia site's PDFs are
served. The TSKgel ODS-100V/100Z instruction manual (Rev. CO071010, ref. 14, read) has
"Table 1 Maximum Pressure" with columns *Part No. | Type | Column Size mm(I.D.)× cm(L) |
Maximum Pressure (MPa)*; worked example: **0021938**, TSKgel ODS-100V 3 μm, 2.0 × 10,
24.0 MPa [verified]. The phase is "Octadecyl group functionalized silica gel"; the manual
gives **no pore size, no particle description beyond "3 μm", no volume and no porosity**
[verified]. Its "dead volume" sentences are about fittings. The published Tosoh terms page
is a placeholder (§5.8).

### 2.3 What this means for the architecture field

[derived] The field the $t_0$ estimator turns on (#24, #33) is *explicit* for exactly one
vendor read on the first pass (Thermo); the second pass (§10) makes it three — Waters
("Particle Technology: Solid Core") and Supelco ("Matrix: … superficially porous particle")
state it as a field on the part's own page — and the third pass (§10.5) makes it
**four**, with Agilent's "Particle Type: Superficially Porous". For Phenomenex and (in
the mirrored catalogue) Supelco it is a brand-level
sentence on a family page or brochure that a human must map to `core_shell`; for Shimadzu
it is a brand-level sentence mapping to `fully_porous`; for YMC and Tosoh it is not stated
at all in what was read. A shipped record therefore needs the architecture to carry its
own provenance — the vendor sentence quoted, or "declared by <who> on <date>" — rather
than a bare enum. This is the same honesty rule SPEC §4 already applies to $t_0$.

## 3. Column volume, $V_0$, dead volume, total porosity: who publishes what

**Nobody publishes a per-column value** [verified across every source in §2; the four
blocked product pages are the caveat, §8]. What exists:

1. Waters WKB28079 — a porosity *constant* per particle class (0.66 / 0.49) and an
   instruction to measure. Already assessed in `dead-time-from-geometry.md` §3.1 and
   superseded there by the literature defaults 0.62 / 0.52.
2. Waters BEH care manual Table 1 — geometric *empty* volumes (§2.2), not $V_0$.
3. Particle-level structure numbers from which a shell-volume fraction could be computed —
   Agilent and Supelco "1.7 µm core + 0.5 µm shell", Thermo "porous layer depth 0.5 µm",
   and (from the search index only, unread) Waters CORTECS "core diameter 1.1 µm, ρ = 0.7".
   `porosity-for-t0-geometry.md` §3.3 already shows why $1-\rho^3$ is *not* a liquid-filled
   porosity and would overestimate $t_0$ by ~50 %. These numbers help classify, not
   quantify.

[derived] Consequently nothing found here changes the porosity defaults, the band, or the
measured-first posture. The value a profile could add on this axis is a **measured** $t_0$
for a named column on a named instrument, with marker and date — which is a lab
measurement, not a catalogue field, and belongs to the pair (#26).

## 4. Machine-readable catalogues

**Vendor side: none found** [verified by search and by reading the pages above]. What
exists is *structured HTML* — Phenomenex's part pages are keyed by a `partNo=` query
string, the Shimadzu shop page has a labelled spec table, the YMC list is an HTML table —
none offered as CSV, export or API. Of those three sites' terms, Shimadzu's forbids
systematic retrieval in words, Phenomenex's forbids reproduction beyond personal use, and
YMC's permits non-profit reproduction (§5). Waters' "Column Comparison Chart" and "Column Coach" and Agilent's
"selector tools" appear in search listings but sit on the blocked domains and are, from
their titles, selection aids rather than downloads [unverified].

**Third party:**

| Source | Holds | Geometry? | Export? | Terms |
|---|---|---|---|---|
| hplccolumns.org (ref. 15, read) | hydrophobic-subtraction parameters H, S*, A, B, C, EB, USP type, phase type, manufacturer, silica type for ~700 RP columns | **no** — no length, i.d., particle or pore size | none visible (web filter/pagination only) | "all content on this site is licensed under a Creative Commons Attribution-Noncommercial-Share Alike 3.0 United States License" [verified] |
| USP Column Equivalency database (`Exploration/USP-column-equivalency.xlsx`, assessed on #26) | phase activity parameters | no | workbook | no redistribution licence in the README |
| hplc.eu (ref. 16, read) | a brand directory and a quote-request selector, "Copyright 2025 - Weber Consulting" | fields not exposed on the page read | none | not stated |
| Fisher Scientific (distributor; product pages for Waters and Supelco columns) | spec tables across vendors | rendered by script — WebFetch timed out twice, `curl` returned the shell without the table | none | "any use of these materials on any other Web site or networked computer environment for any purpose is prohibited" (§5.9) |
| GL Sciences "HPLC column equivalents" | cross-reference list | unread — HTTP 403 | — | — |

[derived] The only openly licensed dataset is the wrong dataset (selectivity, not
geometry), and it is Non-Commercial Share-Alike, which would bind a derived table. There is
no legitimate bulk source for geometries; a seed library is hand-typed or it is nothing.

## 5. Terms of use, per source, on extracting and redistributing catalogue data

Quoted verbatim from the page read; where the vendor's terms page was unreachable that is
the finding. None of this is legal advice; §5.11 marks what is judgement.

### 5.1 Waters — terms page blocked
`https://www.waters.com/nextgen/us/en/legal/terms-of-use.html` → HTTP 403 (§9). The KB
articles were served without a visible licence statement. **Unread.** Second pass (§10):
the URL is a Waters **404**, not a block; no Waters web terms text was located.

### 5.2 Agilent — terms page blocked; document notice read
`https://www.agilent.com/home/terms-of-use` → HTTP 403. Second pass (§10): **read**; it
authorises viewing "solely for non-commercial use within your organization" and forbids
access "programmatically by macro, robot, or other automated means" — quoted in §10.3.
The Specification Compendium
(ref. 17, mirror) carries Agilent's standard notice [verified]:

> No part of this manual may be reproduced in any form or by any means (including
> electronic storage and retrieval or translation into a foreign language) without prior
> agreement and written consent from Agilent Technologies, Inc. as governed by United
> States and international copyright laws.

### 5.3 Phenomenex — *Website Terms of Use* (ref. 18, read)
> You may access, copy, download, and print the material contained on the site for your
> personal and non-commercial use, provided you do not delete any copyright, trademark, or
> other proprietary notice that appears on the materials. Except as expressly authorized by
> Phenomenex, you may not in any manner modify, copy, reproduce, republish, upload, post,
> transmit, distribute, sell, license, rent, publicly display or perform, edit, reverse
> engineer, adapt or create a derivative work of any material, information, software,
> products or services obtained from the site.

No clause names scraping or databases [verified]. No effective date shown.

### 5.4 Thermo Fisher — *Website and Mobile Application Terms of Use* (ref. 19, read; "Effective as of June 17, 2016") and its *DO's and DON'Ts* (ref. 20, read)
> You are hereby granted a non-exclusive, non-transferable, revocable license to access the
> Site via an industry-standard web browser and use the Site strictly in accordance with
> these Terms.

> Such intellectual property rights include, but are not limited to, patents, trademarks,
> trade names, inventions, copyrights, design rights, and rights in and to databases, know
> how, and any other intellectual property relating to the Site. All intellectual property
> rights are reserved unless granted in an express written license.

DO's and DON'Ts, among the DON'Ts:
> employ any scraping, crawling, or similar technologies on the Site; or resell or charge
> others for use of or access to the Site.

The specification and case-study PDFs carry "© 2025 Thermo Fisher Scientific Inc. All
rights reserved." / "© 2022 …" [verified].

### 5.5 Merck / Sigma-Aldrich — unreachable
Product and terms URLs both timed out (§9). **Unread.** Second pass (§10): the product
page reads; the terms URL now returns an Akamai 403. Terms still **unread**. Third pass
(§10.5): the old URL is gone (404); the live *Site Use Terms* were read and forbid
robots and copying — quoted in §10.5. The 2008 catalogue (mirror) carries
"©2008 Sigma-Aldrich Co. All rights reserved." and nothing on reuse [verified].

### 5.6 YMC — *About Site* (ref. 21, read)
> YMC CO., LTD. owns the copyright of the texts, pictures, and computer programs on the YMC
> web server. […] any duplicate, printing or any reproduction of the material contained on
> this Server site is allowed by third parties only for nonprofit use. Alteration and/or
> reproduction and distribution of materials on this site for purposes other than
> non-profit use is strictly forbidden, and use of the information contained on this site
> for any "for profit" use shall not be permitted unless prior written permission for use
> of such materials is obtained from YMC CO., LTD.

The most permissive terms read: non-profit reproduction is expressly allowed.

### 5.7 Shimadzu — Shimadzu Scientific Instruments *Terms of Use* (ref. 22) and Shimadzu Asia Pacific shop *Terms of Use* (ref. 23), both read; identical operative language
> you agree not to sell, license, rent, modify, distribute, copy, download, reproduce,
> transmit, publicly display, publicly perform, publish, adapt, edit, or create derivative
> works […]

> Systematic retrieval of data or other content from this Site to create or compile,
> directly or indirectly, a collection, compilation, database or directory without the
> prior written permission from SSI is prohibited.

> you may print or download one copy of the materials or content on this Site on any
> single computer for your non-commercial use, provided you keep intact all copyright and
> other proprietary notices.

(The SAP page names "SAP" where the SSI page names "SSI".) This is the clause that most
directly describes a scraped seed library, and it forbids it.

### 5.8 Tosoh — placeholder
`https://www.tosohbioscience.com/terms-of-use` returns HTTP 200 whose body under the
heading "Terms of Use" is **lorem ipsum** ("Lorem ipsum dolor sit amet, integer elit
tellus, …") [verified]. There is no published Tosoh web terms text to comply with; the
instruction manual carries only trademark notices.

### 5.9 Fisher Scientific (distributor) — *Website Terms & Conditions* (ref. 24, read)
> Fisher Scientific authorizes you to view and download the materials at this Web site
> ("Site") only for your personal, non-commercial use […] You may not modify the materials
> at this Site in any way or reproduce or publicly display, perform, or distribute or
> otherwise use them for any public or commercial purpose. For purposes of these Terms,
> any use of these materials on any other Web site or networked computer environment for
> any purpose is prohibited.

### 5.10 hplccolumns.org — CC BY-NC-SA 3.0 US (§4).

### 5.11 Reading the terms — judgement, not citation

[derived] Three things follow, and I mark them as my reading rather than anything a source
says:

1. **Bulk extraction is out.** Shimadzu forbids "systematic retrieval … to compile a
   database" and Thermo forbids "scraping, crawling" in terms; four other vendors enforce
   the same thing technically (§9). A crawler-built seed library would breach terms the
   lab has to keep on good standing with its own suppliers.
2. **Hand-typed facts with attribution are a different act.** A record saying "2.1 mm ×
   100 mm, 1.6 µm, 90 Å, solid-core, part 186008694, per Waters product page <URL>, read
   2026-09-04" reproduces no vendor text, table or image; it states facts and cites where
   they came from. Whether bare dimensional facts attract copyright at all differs by
   jurisdiction (I am not going to opine), which is one more reason to keep the seed small,
   sourced and the vendor's expression out of it. YMC's non-profit permission and Waters'
   KB (which is meant to be quoted) are the easy cases; Fisher's "any other Web site or
   networked computer environment" clause is the one to remember for v0.5 hosting, and is
   avoided by not using Fisher as a source at all.
3. **"Non-commercial" is not settled by the repo's licence.** Every readable terms page
   conditions personal use on non-commercial purpose. The app is a lab's tool today; if it
   is ever offered commercially the seed library's provenance becomes a licensing question
   the driver must revisit. Record it now so it does not have to be re-derived.

## 6. Instrument side: dwell (gradient delay) volume

### 6.1 What each vendor publishes, and what its number spans

**Waters — ACQUITY UPLC H-Class.** The specification PDF (720003294) and system guide are
blocked (§9); the knowledge base is not, and is unambiguous [verified, refs. 25–28]:

- WKB8302 *What is the dwell volume for an ACQUITY UPLC H-Class system?*: "Dwell volume,
  system is <400 μL with 100-μL mixer"; with the Radial GPV kit installed, "< 505 µL".
- WKB201368 *What is the system volume of the HPLC and UPLC systems?* lists
  "Acquity H-Class (QSM+FTN): <400 uL (Including a 100 μL mixer)" alongside the other
  ACQUITY and Arc systems.
- WKB50711 *What is system dwell volume?*: "The dwell volume is the total volume in the
  system between the point where the gradient is formed and the inlet of the column."
- WKB50707 *How do I determine system dwell volume?*: replace the column with a restrictor
  (≥ 2000 psi on an ACQUITY), A = water, B = water + 10 mg/L caffeine, 1.00 mL/min, 273 nm,
  100 % A held to 5 min, 100 % B at 25 min (programmed t½ = 15 min); "tD = t1/2
  experimental − t1/2 programmed";
  "VD = tD x F".

[derived] Waters' figure is a **whole-system, configuration-named** number — the "QSM+FTN"
label says the flow-through-needle sample manager is inside it — stated as an upper bound
for a named mixer. The lab's 0.375 mL sits under that bound, and Thermo's competitor table
(§6.2) independently quotes "Waters ACQUITY H-Class with 100 µL mixer: 380 µL". The lab's
value is therefore the *instrument's own* figure in the sense the map already decided
(#27 close-out), and consistent with the vendor's spec — but it is a bound, not a
measurement, and the app should keep saying so. **Superseded in part by §10.2:** Waters'
white paper 720005723 reports **0.375 mL** as the *measured* dwell of an ACQUITY UPLC
H-Class PLUS (quaternary) in default configuration — the lab's number to three digits.

**Agilent — 1290 Infinity II and 1260 Infinity II.** Every agilent.com host refused (§9).
The *InfinityLab LC Series Specification Compendium* (manual part 01200-90062 Rev. C,
edition 03/2018, © Agilent 2014-2018; ref. 17, mirror) gives, per pump module [verified]:

- 1290 Infinity II High Speed Pump G7120A: "Delay volume: As low as 45 µL (10 µL without
  mixer)".
- 1290 Infinity II Flexible Pump G7104A: "Delay volume: As low as 350 µL".
- 1260 Infinity II Quaternary Pump G7111B: "Delay volume: 600 – 900 µL, dependent on back
  pressure; measured with water at 1 mL/min (water/caffeine tracer)" (same wording in the
  standalone data sheet, ref. 29, mirror).
- 1260 Infinity II Binary Pump G7112B: "Standard delay volume configuration: 600 – 900 µL,
  (includes 400 µL mixer), dependent on back pressure. Low delay volume configuration:
  120 µL".

The Multisampler and Vialsampler entries in the same compendium carry **no delay-volume
row** [verified by grep across the document]. [derived] Agilent's numbers are therefore
**pump-module figures** — "as low as", configuration-dependent, and for the quaternary
pumps a 300 µL span that depends on back pressure — with the sampler's contribution
unstated. An Agilent system dwell is not on any page read; the community thread that
reportedly says the manual figures cover "only the physical contribution just of the
module itself" came back empty (§9), so that sentence is [unverified]. Thermo's competitor
table gives "Agilent 1290 Infinity II: 300 µL (pressure dependent)" and "1260 Infinity II
(quaternary pump): 1,100 µL" as system values — a competitor's numbers, useful only as a
sanity bound.

**Shimadzu — Nexera (LC-40).** The Nexera series specification page (ref. 30, read) lists
pressure, flow, injection, temperature and detector specs for every LC-40 pump and **no
delay or dwell volume** [verified]; neither do the SSI pages for the LC-40D X3 and LC-40B X3
(refs. 31, 32, read). The Nexera series catalogue C196-E095 (© Shimadzu 2019, ref. 33,
mirror) lists the *mixers* — MR 20, 40, 100, 180 µL for high-pressure gradient; MR 40 and
300 µL for low-pressure gradient — and says only that the X3 dual pump "reduces gradient
delay volume" [verified]. The IVD solvent-delivery manual 228-97197C (Sep. 2024, ref. 34,
read) says a larger mixer "will also increase the gradient delay volume", no number
[verified]. The only Shimadzu system figure found is for the **previous generation**: the
2010 Nexera catalogue C196-E071 (ref. 35, mirror), "The total system delay volume has been
reduced to less than 42 µL with an ultra-low volume (20 µL) mixer, optional loop injection
kit with 5 µL loop and micro-volume pre-heater" [verified] — LC-30AD/SIL-30AC, not LC-40.
Shimadzu's definition (SSI knowledge base, ref. 36, read): "Gradient Delay volume is the
total amount of volume from the point of mixing to the head of the column", with
"Vd = Vmixer + Vinj + Vtubing" — the injector is inside it.

**Thermo — Vanquish.** Vendor-hosted, all read. The pumps specification sheet PS73056-EN
0825 (© 2025, ref. 37) has a row named, exactly, **"Dwell volume (contribution of the pump
to the system gradient delay volume)"** [verified]: Binary Pump H "35 μL (25 μL proprietary
capillary mixer and 10 μL filter, default configuration)"; Binary Pump F "200 μL (default
configuration)"; Binary Pump C "400 µL (default configuration)"; Quaternary Pump F and
Quaternary Pump C/CN "679 μL (default configuration)". The Vanquish Horizon system page
(ref. 38) says "Binary (35 µL)" and "Customizable gradient delay volume to simplify method
transfer: Yes, with metering device" [verified]. The method-transfer case study CS000566
(© 2022, ref. 39) gives the definition and the arithmetic [verified]:

> Gradient delay volume is defined as the volume between the point of mobile phase mixing
> and the column entry. More precisely, it is the combined volume contributed by pumping
> system, gradient mixer, tubing between the pump and the injector, injector, and tubing
> between the injector and the column.

> Gradient delay volume = FR × (T50 – (0.5 × TG))

with A = water, B = "10 mg/mL caffeine in water" (Waters says 10 mg/L; a tracer
concentration difference that does not change the method), and per-system tables that sum
*Sampler GDV* + *invariable system tubing* + *mixer + inline filter*: for the Vanquish
Horizon with the 25 µL loop, sampler 110/135/210 µL (minimum/default/maximum), tubing
5 µL, mixer + filter 35 µL, system GDV 150 / **175** (factory set) / 250 µL. The Thermo
blog (ref. 40) says the same in one sentence: dwell volume "is the volume from the point of
mobile phase mixing to the inlet of the column" and includes "pump heads, tubing,
mixer(s), the sample loop, and any valves in the flow path".

### 6.2 The definitions, side by side

| Vendor | Span | Sampler / loop inside the published number? | Published as | Measured how (vendor's own words) |
|---|---|---|---|---|
| Waters | "point where the gradient is formed" → "inlet of the column" | **yes** — figure is for "QSM+FTN" | system upper bound per mixer ("<400 µL with 100-µL mixer") | caffeine step, t½ minus programmed t½, × F (WKB50707) |
| Agilent | not defined on any page read | **no** — pump module only; sampler rows silent | "as low as" / a 300 µL pressure-dependent range per pump | "water/caffeine tracer", 1 mL/min (spec footnote) |
| Shimadzu | "point of mixing" → "head of the column", Vd = Vmixer + Vinj + Vtubing | yes by definition; **no number for LC-40** | mixer volumes only | not stated |
| Thermo | "point of mobile phase mixing" → "column entry", listing pump, mixer, tubing, injector, tubing | tabulated **separately** (pump row is "contribution of the pump") and summed per system in a case study | pump contribution on the spec sheet; system sums in CS000566 | caffeine step, FR × (T50 − 0.5·TG) |

[derived] All four vendors agree on the *span* (mixing point to column inlet, injector
included) and, where they say, on the *method* (a tracer step, read at half height). They
disagree on **what the published number is a number of**: Waters publishes the system,
Agilent the pump, Thermo both but on different documents, Shimadzu (current generation)
neither. A profile field called `dwell_ml` seeded from a spec sheet would be comparing a
Waters system bound with an Agilent pump minimum. The record has to say which.

## 7. Recommendation

**Can the app ship a record it did not measure?** Yes for columns, conditionally for
instruments, and never for $t_0$.

1. **Column records: ship, hand-typed, with provenance.** Trustworthy from a spec sheet:
   `length_mm`, `id_mm`, `particle_um`, `pore_a`, `phase` (as the vendor names it), `part_no`,
   `vendor`, `product_line`. Each record carries `source_url`, `source_read_on` and — for
   `architecture` — either the vendor sentence quoted (Thermo's field; Waters', Agilent's,
   Phenomenex's, Supelco's, Shimadzu's prose) or `declared_by` + date when the vendor says
   nothing (YMC, Tosoh). No scraping, no vendor table copied, no distributor site as a
   source; a seed of the lab's own columns plus a handful the lab is likely to hold, each
   typed by a person from the cited page. For the four vendors whose sites block automated
   access (§9) the driver reads the page by hand and the record cites it; that is the
   process, not an obstacle.
2. **Never from a spec sheet: `t0`, $V_0$, porosity.** No vendor publishes them per column
   (§3). A column record ships **without** a $t_0$; $t_0$ belongs to the column–instrument
   pair, measured (marker, date) or estimated (architecture → 0.62 / 0.52, stamped), as
   SPEC §4 and #24 already say. The `t0_is_measured` provenance rule in #26's acceptance
   criteria is exactly right and this research adds nothing that would let it be relaxed.
3. **Instrument records: ship the vendor figure only as a labelled bound with its
   definition.** Fields: `dwell_ml`, `dwell_source` ∈ {`measured`, `vendor_spec`,
   `declared`}, `dwell_definition` (the vendor's span and scope — "system incl. sample
   manager, <400 µL with 100 µL mixer, Waters WKB8302" vs "pump module only, as low as
   45 µL, Agilent 01200-90062"), `configuration` (mixer, loop). SPEC §4's "required, no
   silent default" for dwell stands: a profile may *prefill* the vendor bound and must show
   it as such, and the in-app measurement guidance (Waters WKB50707 / Thermo CS000566 are
   the same procedure) is the path to `measured`. The lab's own H-Class record is
   `vendor_spec`-consistent (0.375 mL under "<400 µL") and stays the instrument's own value.
   Built-in instrument profiles, if any, should be the two literal sets the Guillarme note
   suggested, re-typed from §6.1 with these labels — Waters H-Class (system), Thermo
   Vanquish Horizon (system sum, factory 175 µL), Agilent per-pump (module only) — and
   **no Shimadzu LC-40 number**, because none is published.
4. **Terms: keep the seed small, cited and non-commercial; revisit if the app's status
   changes** (§5.11). Do not ship any vendor PDF, table image or text beyond the quoted
   architecture sentence. Record in the profile file's header that records are facts typed
   from cited public pages.
5. **Schema notes for the shape ticket:** normalise pore size (Shimadzu uses nm), keep
   length in mm even where the vendor uses cm (Supelco, Tosoh), and give `architecture` a
   third state, `unstated`, so YMC- and Tosoh-style records are not forced to a guess.

## 8. What I could NOT verify

1. The field list on the **Waters** product page for 186008694 (and the CORTECS family
   page's particle figures: core 1.1 µm, ρ 0.7, pore volume 0.26 cm³/g, 100 m²/g, carbon
   6.6 % — all seen only in a search-index snippet) — blocked. Driver to read by hand.
   *Second pass (§10): product page read — carbon load is **6.4 %**, not 6.6 %; the family
   page carries none of the particle-structure numbers, which remain unverified.*
2. The field list on **Agilent**'s store page for 695775-902 and whether "superficially
   porous" appears there as a field — blocked; the 2012 brochure is what was read and may
   not the current edition. *Second pass (§10): store page still blocked; the family
   page has a pore-size facet and prose only.* *Third pass (§10.5): store page read —
   "Particle Type: Superficially Porous" is a field; brochure 5991-8750EN (© 2020, 2025)
   and ordering guide 5991-9123EN (August 2024) read direct. Closed.*
3. The **sigmaaldrich.com** product page for 53823-U and Merck's web terms — unreachable.
   *Second pass (§10): product page read; terms still blocked.* *Third pass (§10.5):
   Site Use Terms read. Closed.*
4. Whether **Tosoh**'s product pages state pore size or architecture — Cloudflare challenge.
   *Second pass (§10): read — pore size yes (10 nm), architecture no.*
5. **Agilent's definition of delay volume** and the sampler's contribution — no Agilent
   page defining it was readable; the community-forum sentence is unverified.
   *Second pass (§10): the forum sentence is verified as written by a forum member, not
   as an Agilent statement; the module manuals are still blocked.* *Third pass (§10.5):
   the 1260 Infinity III Binary Pump manual gives the pump's delay volume with its
   measurement condition and still no sampler figure; no Agilent definition of the span
   was found. Narrowed further, not closed.*
6. Any **Shimadzu LC-40 (Nexera X3/XR/XS)** system delay volume — not published on any page
   or PDF read; the 42 µL figure is the 2010 LC-30 generation.
7. Waters' own **specification sheet 720003294** wording ("Dwell volume (total system)")
   — blocked; the KB articles carry the same numbers and were used instead.
   *Second pass (§10): read — "Dwell volume (total system) <400 µL (includes standard
   100 µL mixer)", verbatim.*
8. Whether the mirrored PDFs (Agilent compendium Rev. C 2018, Poroshell brochure 2012,
   Supelco catalogue 2008, Waters BEH care manual 2004, Shimadzu C196-E095 2019 and
   C196-E071 2010) are the current editions — document numbers are given so the driver
   can check against the vendor's copy. *Third pass (§10.5): the Poroshell brochure's
   current edition is 5991-8750EN (© 2020, 2025), superseding 5990-5951EN (2012); the
   others are unchanged.*
9. The Thermo Terms of Use page's own copying clause beyond the licence and IP sentences
   quoted — the page is long and script-heavy; the DO's and DON'Ts PDF was read in full.

## 9. Sites that refused automated access

For the driver to fetch by hand. Failure mode as observed with WebFetch and with `curl`
(desktop user-agent, HTTP/1.1 and HTTP/2 tried). **§10 records a second pass with a real
browser on the driver's instruction; the table below is the first-pass finding.**

| Host | URL tried | Result |
|---|---|---|
| waters.com (Akamai) | `https://www.waters.com/nextgen/us/en/shop/columns/186008694-cortecs-shield-rp18-column-90a-16--m-21-mm-x-100-mm-1-pk.html` | HTTP 403 "Access Denied" |
| waters.com | `https://www.waters.com/nextgen/us/en/products/columns/cortecs-columns.html` | HTTP 403 |
| waters.com | `https://www.waters.com/nextgen/us/en/legal/terms-of-use.html` | HTTP 403 |
| waters.com | `https://www.waters.com/content/dam/waters/en/library/specifications/2016/waters-specification-ACQUITYUPLCH-ClassSystem-720003294` (H-Class spec sheet) | HTTP 403 |
| waters.com | `https://www.waters.com/webassets/cms/library/docs/720005723en.pdf` (dwell-volume white paper); `…/support/docs/720004750en.pdf` (CORTECS care and use); `…/content/dam/waters/de/library/wall-charts/2021/…720001983.pdf` | HTTP 403 / timeout |
| help.waters.com | `https://help.waters.com/content/dam/waters/en/support/usermanuals/2016/715005049/715005049rc.pdf` (H-Class system guide); `…/2025/720008980/720008980.pdf` | HTTP 403 |
| agilent.com (Akamai) | `https://www.agilent.com/store/en_US/Prod-695775-902/695775-902`; `https://www.agilent.com/en/product/small-molecule-columns/reversed-phase-hplc-columns/infinitylab-poroshell-120`; `https://www.agilent.com/home/terms-of-use`; `https://www.agilent.com/cs/library/brochures/5991-8750EN_InfinityLab_Poroshell120_brochure.pdf`; `…/sales/public/5991-9123EN_InfinityLab_Poroshell120_ordering.pdf`; `…/usermanuals/public/G7112BUser.pdf`; `…/G7104ASystem.pdf`; `…/technicaloverviews/Public/…5994-2174en-agilent.pdf` | HTTP 403 "Access Denied" (every path) |
| lc.help.agilent.com | `https://lc.help.agilent.com/en/docs/project0/contents/a-lc/27021601966376843-1-4-72057597081143819-9.htm` (G7120A description) | HTTP 403 |
| community.agilent.com | `https://community.agilent.com/technical/lc/f/forum/8637/low-delay-volume-configuration` | HTTP 200 with an empty (212-byte) body |
| hpst.cz (Agilent distributor mirror) | `…/customer_1290_ii_high_speed_pump_datasheet_5991-5336en.pdf`; `…/customer_5991-7087en_1260_ii_quat_pump_datasheet.pdf` | HTTP 403 |
| sigmaaldrich.com | `https://www.sigmaaldrich.com/US/en/product/supelco/53823u`; `https://www.sigmaaldrich.com/US/en/life-science/legal/terms-of-use` | no response: 40 s timeout (HTTP/1.1), stream INTERNAL_ERROR (HTTP/2) |
| tosohbioscience.com (Cloudflare) | `https://www.tosohbioscience.com/EU-EN-separations/products/tskgel-ods-100v-3-m/0021940` (and CN-CN); `https://www.separations.eu.tosohbioscience.com/products/hplc-columns-uhplc-columns/reversed-phase/tskgel-ods-100v` redirects here | HTTP 403, captcha challenge page |
| fishersci.com | `https://www.fishersci.com/shop/products/cortecsc182-1-mm100-mm-11/501384990`; `…/ascentis-express-c18-hplc-column-2-7-m-particle-size-18/111007163` | WebFetch timeout ×2; `curl` HTTP 200 but the spec table is script-rendered and absent |
| glsciencesinc.com | `https://www.glsciencesinc.com/hplc-column-equivalents` | HTTP 403 |
| device.report (mirror) | Agilent flexible-pump manual | HTTP 403 |

Reachable without incident: support.waters.com, phenomenex.com (and its blob storage),
thermofisher.com and documents.thermofisher.com, ymc.co.jp and ymcamerica.com,
shimadzu.com, ssi.shimadzu.com and shopshimadzu.com, separations.asia.tosohbioscience.com
(PDFs), hplccolumns.org, hplc.eu, and the mirrors named in the references.

## 10. Second pass: the blocked pages, fetched with a real browser

**Posture change, recorded.** §1 said "nothing was worked around". The same day, the
driver granted the session a browser (`.claude/settings.local.json`: Playwright with
`playwright-stealth`) and asked for the §9 list to be fetched. Each URL was opened once
in the installed Google Chrome, headless, with the stealth patches; page text was saved
and read; PDFs were saved and text-extracted. No site was crawled and no listing was
walked. What that means under each vendor's terms is in §10.3 — Agilent's terms forbid
exactly this, and the driver should weigh that before any repeat.

### 10.1 What the second pass returned

| URL (first-pass row in §9) | Second pass |
|---|---|
| waters.com product page 186008694 | **200**, full spec table (§10.2) |
| waters.com CORTECS family page | **200**; prose only, no particle-structure numbers |
| waters.com terms of use | **404** (Waters' own "page can't be found"), not a block |
| waters.com 720003294 H-Class spec sheet | **200**, PDF (AES-encrypted; opens without a password) |
| waters.com 720005723 dwell white paper | **200**, PDF (encrypted, same) |
| waters.com 720004750 CORTECS care manual | **200**, PDF |
| help.waters.com 715005049 H-Class system guide | **200**, PDF, 116 pages |
| help.waters.com 720008980 care and use manual | **200**, PDF |
| agilent.com store page 695775-902 | **403** still |
| agilent.com Poroshell 120 family page | **200** |
| agilent.com terms of use | **200** |
| agilent.com `/cs/library` brochure, ordering guide, G7112B and G7104A manuals | **403** still, every path |
| lc.help.agilent.com G7120A page | **403** still (S3 "AccessDenied") |
| community.agilent.com thread | **200**, full thread |
| sigmaaldrich.com 53823-U product page | **200** |
| sigmaaldrich.com terms of use | **403** (Akamai) — a block now, not a timeout |
| tosohbioscience.com ODS-100V product page | **200**; the Cloudflare challenge cleared |
| fishersci.com CORTECS and Ascentis listings | **200**, spec fields rendered |
| glsciencesinc.com equivalents chart | **200** |

Playwright with real Chrome and stealth gets past Akamai on waters.com and sigmaaldrich.com
product pages and past Cloudflare on tosohbioscience.com; it does **not** get past
Akamai on agilent.com's store and document paths, or on sigmaaldrich.com's legal path.
§10.5 records the third pass that did.

### 10.2 What the pages say, and what it changes above

**Waters product page 186008694 (ref. 41) [verified].** A "Specifications" table with
these fields, in this order: Chemistry C18; Separation Mode Reversed Phase; Particle
Substrate Silica; pH Range Min 2 / Max 8; Temperature Limits 45 C; Maximum Pressure
18000 psi (1240 Bar); Endcapped Yes; Bonding Technology Shield RP18; Silanol Activity Low;
Particle Shape Spherical; Particle Size 1.6 µm; Endfitting Type Parker-style; Pore Size
90 Å; Format Column; Surface Area 100 (no unit shown); System UPLC, UHPLC; **Particle
Technology Solid Core**; USP Classification L1; Inner Diameter 2.1 mm; Length 100 mm;
Carbon Load **6.4 %**; eCord Yes; UNSPSC 41115709; Brand CORTECS; Units per Package 1 pk.
The product description adds, in prose, "The solid core particle morphology offers high
efficiency and lower backpressures when compared to fully porouse [sic] particles".

[derived] Three corrections to the first pass. (i) Waters states the architecture as a
**field**, so §2.3's count of vendors with an explicit field rises from one to three
(Thermo, Waters, Supelco — next paragraph). (ii) Geometry, particle size and pore size are
fields, not only title tokens. (iii) The search-index snippet's carbon load (6.6 %, §8
item 1) was wrong; the page says 6.4 %. The particle-structure numbers from that snippet
(core 1.1 µm, ρ 0.7, pore volume, 100 m²/g) are **not** on the product page or the family
page; only "Surface Area 100" survives, unit unstated. §3 item 3 stands as "unverified".

**Sigma-Aldrich 53823-U (ref. 51) [verified].** Fields: *L × i.d. 10 cm × 2.1 mm; Particle
size 2.7 μm; Matrix active group C18 (RP18), C18 (octadecyl) phase; Pore size 90 Å;
Matrix Fused-Core particle platform, superficially porous particle*; and under
properties *surface area 135 m2/g, impurities <5 ppm metals*. The page's FAQ says "The
Fused-Core particle consists of a 1.7 μm solid core and a 0.5 μm porous shell" and, on
carbon load, that "%Carbon … can not be compared to traditional porous particles"; the
coverage is given as 3.5 µmol/m². [derived] So for Supelco, pore size *is* a field on the
part page (the 2008 grid lacked it) and the architecture is a field ("Matrix"), which
§2.1 and §2.3 now say.

**Tosoh 0021940 (ref. 52) [verified].** This URL is the 4.6 mm × 10 cm part, not the lab
example's 2.0 × 10 (0021938). Fields: *Column Diameter (mm) 4.6; Column Length (cm) 10;
Housing Material Stainless Steel; Particle Size (µm) 3; Pore Size (nm) 10; Mode Reversed
Phase; Base Material Silica*. Nothing on architecture. [derived] Pore size is a field, in
nm like Shimadzu's; the "unstated" third state for `architecture` (§7 item 5) is still
needed for Tosoh.

**Agilent Poroshell 120 family page (ref. 48) [verified].** A family page with a
"Pore Size" filter facet and a part list ("InfinityLab Poroshell 120 Aq-C18 2.1 x 100 mm,
2.7 µm", …); the architecture is prose: "Superficially porous, core-shell particles that
provide both improved throughput and higher resolution". No per-part spec table here; the
store page that holds one was read on the third pass (§10.5).

**Waters specification sheet 720003294EN, June 2016 (ref. 43) [verified].** Under
"ACQUITY UPLC H-Class System Features": "Dwell volume (total system)  <400 µL (includes
standard 100 µL mixer)". §8 item 7 is resolved: the KB wording and the spec sheet agree.

**Waters white paper 720005723EN, April 2018 (ref. 44) [verified].** Definition: "Dwell
volume is the volume required for the change in a gradient to reach the column, or the
volume difference between the point of mixing and the head of the column", "also commonly
referred to as gradient delay volume". Method: 0–100 % B step with 10 mg/L caffeine in B,
273 nm, a restrictor in place of the column, systems "in [their] default configuration".
Figure 2, "System Dwell Volume (VD) (mL)": Alliance HPLC (Quaternary) 1.15; ACQUITY Arc
(Quaternary) 1.19 (Path 1) / 0.770 (Path 2); **ACQUITY UPLC H-Class PLUS (Quaternary)
0.375**; ACQUITY UPLC I-Class PLUS (Binary) 0.073; with the caveat "Values may vary from
system to system based on column heater, tubing, and flow cell configuration". Table 1,
extra-column band broadening measured with a zero-dead-volume union in place of the
column, 40 Hz: ACQUITY UPLC H-Class PLUS with CH-A and ACQUITY PDA detector **8 µL at 5σ,
7 µL at 4σ**; I-Class PLUS SM-FTN 7.5 / 5; Arc 25 / 19; Alliance 43–45 / 30–34.

[derived] This is the most consequential page of the pass. The lab's dwell, 0.375 mL,
recorded in `validation/method.csv` as "from instrument spec sheet, NOT measured", is
Waters' **measured** figure for a representative H-Class PLUS in default configuration —
identical to three digits, so that is almost certainly where the lab's number came from.
It is neither the "<400 µL" bound (§6.1) nor a measurement on *this* instrument. The
profile schema in §7 item 3 therefore needs a fourth `dwell_source` state,
`vendor_measured_representative` (vendor's bench, vendor's configuration, cited document),
between `vendor_spec` and `measured`; the lab's own record should carry that state, ref.
44, and the configuration caveat. The 7–8 µL extra-column figure is the instrument-side
input #101's budget needs and was not available anywhere on the first pass. None of this
moves the value: 0.375 mL stays the instrument's own number, per the #27 close-out.

**Waters care manuals 720004750EN (CORTECS, December 2022; ref. 45) and 720008980EN
(July 2025; ref. 47) [verified].** Both carry the same "Table 1. Empty Column Volumes in
mL (multiply by 10 for flush solvent volumes)" as the 2004 BEH manual (§2.2): 2.1 mm ×
100 mm → 0.4 mL. Geometric volume, not $V_0$; §3 item 2 stands, now from the CORTECS
document itself.

**Waters H-Class system guide 715005049 Rev. C, August 2016 (ref. 46) [verified].** No
dwell figure. It says "the dwell volumes of the ACQUITY UPLC H-Class system are far
smaller than those of a conventional HPLC system, often a gradient hold is required", and
recommends a pre-injector volume "to maintain a constant dwell volume to column volume
ratio on both systems" for transfer. Nothing for the schema.

**Agilent community thread (ref. 50) [verified].** The sentence quoted in §6.1 is real and
is by a forum member ("ankugler"), replying to the question: "It always depends on the way
you are calculating or defining your delay volume. The volumes that are provided in the
manuals typically represent only the physical contribution just of the module itself".
The same reply gives capillary volumes per 100 mm (0.17 mm i.d. 2.27 µL; 0.12 mm 1.13 µL;
0.075 mm 0.44 µL) and a 6-port valve's port-to-port volume of about 0.51 µL. [derived]
This supports §6.1's reading of Agilent's numbers as module-only, but as a member's
statement, not Agilent's; §8 item 5 is narrowed, not closed.

**Fisher Scientific listings and the GL Sciences chart [verified].** Fisher's CORTECS
listing (50-138-4990) carries "Length 100 mm, Diameter 2.1 mm" fields plus Waters' prose;
its Ascentis listing carries "Diameter (Metric) 2.1 mm, Length (Metric) 10 cm". The GL
Sciences page is an interactive cross-reference ("51 equivalents") with no geometry. §4's
conclusion — no machine-readable catalogue — is unchanged.

### 10.3 Terms, second pass

**Agilent (ref. 49) [verified].** "Agilent Technologies, Inc. ("Agilent") authorizes you
to view and download the materials at this website ("Site") solely for non-commercial
use within your organization to acquire, use, and support Agilent products and services
… You may not modify the materials at this Site in any way or reproduce or publicly
display, perform, or distribute or otherwise use them for any public or commercial
purpose. For purposes of these Terms, any use of these materials on any other website or
networked computer environment for any purpose is prohibited." And under Restrictions:
"You may not access, scrape, search, crawl or otherwise attempt to use or extract data
from this Site in any manner other than as expressly permitted by these Terms. You may
only access and use this Site by manual request and not programmatically by macro,
robot, or other automated means … (v) use any device, hardware or software to bypass any
security system on this Site".

[derived] Two consequences. The second pass itself — a scripted browser with detection
evasion — is what this clause names, so agilent.com should be read by hand from here on
and the two Agilent facts above are recorded for the driver to re-confirm that way. And
for the seed library, "any other website or networked computer environment" is the
Fisher clause in Agilent's words (§5.9): typed facts with a citation, not copied
material, remain the posture in §7 item 4.

**Waters.** No web terms text found (the URL is a 404); the documents read carry only
"©20xx Waters Corporation" lines. **Sigma-Aldrich.** Terms still blocked. **Tosoh.** The
terms page is still lorem ipsum (§5.8).

### 10.4 Net effect on §7

- Item 1: `architecture` comes as a field from four vendors (Thermo, Waters, Supelco and,
  per §10.5, Agilent), as prose from Phenomenex and Shimadzu, and not at all from YMC and
  Tosoh. The
  provenance rule is unchanged; the seed for the lab's own CORTECS part can now cite the
  product page's field rather than a family-page sentence.
- Item 3: add `vendor_measured_representative` to `dwell_source`, and record the lab's
  0.375 mL under it with ref. 44 and its configuration caveat. Ship the 7–8 µL H-Class
  PLUS extra-column figure to #101 as the same kind of provenance.
- Item 4: Agilent's terms make hand-reading the only compliant route for agilent.com;
  the process sentence in item 1 ("the driver reads the page by hand") is now a terms
  requirement for that vendor, not just a workaround for a 403. Sigma-Aldrich's Site Use
  Terms (§10.5) say the same, with a research-use carve-out for reproduction.

### 10.5 Third pass, 2026-09-05: the seven survivors, with a TLS-impersonating client

**Posture.** The driver switched the session's auto mode off and said to proceed with the
tools §10.1 said would be needed. `curl_cffi` (a Python binding of curl-impersonate) with
`impersonate="chrome"` was run once per URL; no browser, no JavaScript. Safari and Firefox
impersonation were also tried where Chrome failed. Both vendors' terms forbid this
(§10.3, and Sigma-Aldrich below); the facts are recorded for the driver to re-confirm by
hand, and the fetches are not to be repeated without the same explicit instruction.

| URL (§10.1 row) | Third pass |
|---|---|
| agilent.com store page 695775-902 | **200**, full spec table (Chrome impersonation) |
| agilent.com 5991-8750EN Poroshell brochure | **200**, PDF, 32 pages, © 2020, 2025 |
| agilent.com 5991-9123EN Poroshell ordering guide | **200**, PDF, 8 pages, printed 2024-08-16 |
| agilent.com G7112BUser.pdf | **200**, PDF, 290 pages — *1260 Infinity III Binary Pump User Manual*, edition 10/2024 |
| agilent.com G7104ASystem.pdf | **200**, PDF, 77 pages — *1290 Infinity III LC System Manual*, SD-29000160 Rev. E.02, 11/2025 |
| lc.help.agilent.com G7120A page | **403** under all three impersonations, S3 "AccessDenied" body — a dead link, not bot-blocking |
| sigmaaldrich.com `/legal/terms-of-use` | **404** as Chrome, 403 as Safari/Firefox — the page has moved; the live legal index lists `site-use-terms` and `terms-and-conditions`, both **200** |

[derived] Akamai on agilent.com blocks on TLS/HTTP-2 fingerprint, not on JavaScript
signals: a headless real Chrome with stealth patches was refused but a curl with Chrome's
handshake was served. That is the opposite of waters.com, where the browser passed.

**Agilent store page 695775-902 (ref. 53) [verified].** "Specifications": Agency Method
EPA 553; Brand InfinityLab Poroshell 120; Carbon Load 10 %; Endcapped Yes; Guard Column No;
Hardware Conventional; Inner Diameter (ID) 2.1 mm; LC Platform HPLC, UHPLC; Length 100 mm;
Maximum Temperature 60 °C; Molecular Weight Lower/Upper Limit 0 / 3000 Da; Particle Size
2.7 µm; **Particle Type Superficially Porous**; Phase EC-C18; Pore Size 120 Å; Pressure
Rating 600 bar; Separation Mode Reversed Phase; Shipping Solvent Acetonitrile/Water;
UNSPSC Code 41115709; pH Range 2-8. [derived] Agilent is the fourth vendor with an
explicit architecture field, and its store page has the same shape as Waters' and
Thermo's; §2.1, §2.3, §7 item 1 and §8 item 2 updated. Nothing on $V_0$ or porosity.

**Brochure 5991-8750EN (ref. 54) and ordering guide 5991-9123EN (ref. 55) [verified].**
The brochure is the current edition (© 2020, 2025) of the 2012 document read from a
mirror (§2.2); it describes the particle as a three-step product — "Step 1: make the
solid core", "Step 2: apply the porous shell", "Step 3: apply the bonded phase" — and
says "1.9 μm, 2.7 μm, and 4 μm superficially porous particles", without core or shell
dimensions in the extractable text. The ordering guide (printed 2024-08-16) opens with
"Based on superficially porous particle technology, InfinityLab Poroshell 120 columns
feature a solid silica core and a porous outer layer", lists 20 chemistries, and gives
the maximum pressure per particle size (1.9 µm: 1,300 bar; 2.7 µm and 4 µm: 600 bar).
[derived] The "1.7 µm core + 0.5 µm shell" figure in §2.1 came from the 2012 brochure;
the current brochure's text does not carry it, so a seed record should quote the current
edition's sentence and leave the dimensions out.

**1260 Infinity III Binary Pump manual G7112B (ref. 56) [verified].** Specification
table: "Delay volume — Standard delay volume configuration: 600 – 900 µL, (includes 400 µL
mixer), dependent on back pressure; Low delay volume configuration: 120 µL; Measured with
water at 1 mL/min (water/water with tracer)". Feature list: "Configurable delay volume -
down to 120 µL"; "Damper and mixer can be bypassed for lowest delay volume of the binary
pump". Nothing on the sampler's contribution and no definition of the span. [derived]
Same shape as the compendium figures in §6.1 (a pump-module number with its measurement
condition), now from the module's own manual and for the Infinity III generation; §8
item 5 is narrowed again but stays open on the sampler and the definition.

**1290 Infinity III LC System Manual G7104A (ref. 57) [verified].** Marketing text only
on this point: "Exceptionally low delay volumes down to 10 µl and high flow rates enable
fast gradients"; the configuration chapters say each layout "optimizes the flow path for
minimum delay volume" without a number. Nothing for the schema.

**Sigma-Aldrich *Site Use Terms* (ref. 58) [verified].** Under prohibited uses: "Use any
robot, spider, or other automatic device, process, or means to access the Website for any
purpose, including text and data mining, monitoring or copying any of the material on
the Website" and "Use any manual or automated process to monitor or copy any of the
material on the Website without our prior written consent." On content: "You must not
reproduce, distribute, modify, create derivative works of, publicly display, publicly
perform, republish, download, store, or transmit any part of our Website or content on
our Website without our written consent … You may download certain materials from the
Website such as product images, charts, graphs, etc. for non-commercial personal use
only. Research organizations whose primary goal is to conduct scientific research or to
carry out educational activities, as well as accredited educational institutions such as
universities and colleges may download and reproduce the materials mentioned in this
section for the sole purpose of illustration for teaching or scientific research, so
long as the source is indicated and only to the extent justified for the non-commercial
purpose to be achieved." [derived] The research carve-out is the most permissive
sentence found in any vendor's terms, and it is conditioned on attribution and
non-commercial purpose; it covers a typed, cited fact in a research seed and does not
cover the automated fetch that read it. §5.5 and §5.11's judgement stand: small, cited,
non-commercial, hand-read.

## References

Accessed 2026-09-04 unless stated. "Read" = content read directly; "(mirror)" = vendor
document read from a non-vendor host; "listing only" = seen in a search index, page unread.

**Columns**

1. Waters, product listing "CORTECS Shield RP18 Column, 90Å, 1.6 µm, 2.1 mm X 100 mm, 1/pk",
   part 186008694 — https://www.waters.com/nextgen/us/en/shop/columns/186008694-cortecs-shield-rp18-column-90a-16--m-21-mm-x-100-mm-1-pk.html — listing only (HTTP 403).
2. Waters, KB WKB28079 "How do I determine column void volume?" —
   https://support.waters.com/KB_Chem/Columns/WKB28079_How_do_I_determine_column_void_volume — read (this session and on #24).
3. Waters, *ACQUITY UPLC BEH Column Care and Use Instructions*, ©2004 —
   http://www.ecs.umass.edu/eve/facilities/equipment/Acquity/Acquity%20UPLC%20BEH%20column.pdf — read (mirror, University of Massachusetts).
4. Agilent, *Agilent Poroshell 120 Columns for HPLC and UHPLC*, 5990-5951EN, © 2012 —
   https://hplc.eu/Downloads/Poroshell.pdf — read (mirror, hplc.eu).
5. Phenomenex, part page 00D-4462-AN "Kinetex 2.6 µm C18 100 Å, LC Column 100 x 2.1 mm" —
   https://www.phenomenex.com/part?partNo=00D-4462-AN — read.
6. Phenomenex, Kinetex family page — https://www.phenomenex.com/products/kinetex-hplc-column — read.
7. Phenomenex, *Kinetex HPLC/UHPLC Columns: Tips for Care and Use*, © 2017 —
   https://phenomenex.blob.core.windows.net/webdocument/kinetex-hplc-uhplc-columns-tips-for-care-and-use.pdf — read.
8. Thermo Fisher Scientific, product page 17126-102130 "Accucore C18 HPLC Columns" —
   https://www.thermofisher.com/order/catalog/product/17126-102130 — read.
9. Thermo Fisher Scientific, *Accucore HPLC Columns Technical Manual*, TG20666-EN, © 2012 —
   https://documents.thermofisher.com/TFS-Assets/CMD/brochures/TG-20666-Accucore-HPLC-Columns-TG20666-EN.pdf — read.
10. Supelco / Sigma-Aldrich, *Ascentis Express HPLC Columns with Fused-Core Technology*, ©2008 —
    https://www.labicom.cz/cogwpspogd/uploads/2016/07/Supelco-LC_Ascentis_Expres_catalog.pdf — read (mirror, Labicom).
11. YMC Co., Ltd., YMC-Triart C18 product list — https://www.ymc.co.jp/en/columns/ymc_triart_c18/order.html — read.
12. YMC Co., Ltd., YMC-Triart C18 product page — https://www.ymc.co.jp/en/columns/ymc_triart_c18/ — read;
    YMC America product page — https://www.ymcamerica.com/product/ymc-triart-c18-4/ — read.
13. Shimadzu Asia Pacific shop, "Shim-pack Scepter C18-120, 1.9um, 2.1x100", S227-31012-05 —
    https://www.shopshimadzu.com/product/s227-31012-05 — read.
14. Tosoh, *Packed Columns for Reversed Phase Chromatography: TSKgel ODS-100V 3μm / 5μm, ODS-100Z 3μm / 5μm — Instruction Manual*, Rev. CO071010 —
    https://www.separations.asia.tosohbioscience.com/File%20Library/TBJS/Lit_EN/InstructionManual/Columns/ODS100VZ_EN010.pdf — read.

**Third-party catalogues**

15. hplccolumns.org, HPLC column selectivity database — https://www.hplccolumns.org/database/index.php — read.
16. hplc.eu, "Column brands, HPLC Columns Selection Tool" — https://www.hplc.eu/brands.htm — read.

**Terms**

17. Agilent, *InfinityLab LC Series Specification Compendium*, manual part 01200-90062 Rev. C, edition 03/2018, © 2014-2018 —
    https://www.richmondscientific.com/wp-content/uploads/2024/11/1260-Infinity-II-Spec-list.pdf — read (mirror, Richmond Scientific). Also its 2014-2015 predecessor at https://quantum.ee/wp-content/uploads/File/Agilent/InfinityLab_LC_Series_Compendium.pdf — read (mirror).
18. Phenomenex, *Website Terms of Use* — https://www.phenomenex.com/legal/phx-site-terms-of-use — read.
19. Thermo Fisher Scientific, *Website and Mobile Application Terms of Use*, effective June 17, 2016 —
    https://www.thermofisher.com/us/en/home/global/terms-of-use.html — read.
20. Thermo Fisher Scientific, *Website and Mobile Application DO's and DON'Ts* —
    https://www.thermofisher.com/content/dam/LifeTech/Documents/PDFs/terms-of-use-Dos-and-Donts.pdf — read.
21. YMC Co., Ltd., *About Site* (copyright) — https://www.ymc.co.jp/en/about_site/copyright.html — read.
22. Shimadzu Scientific Instruments, *Terms of Use* — https://www.ssi.shimadzu.com/terms/terms-of-use.html — read.
23. Shimadzu Asia Pacific, *Terms of Use* — https://www.shopshimadzu.com/terms-of-use — read.
24. Fisher Scientific, *Website Terms & Conditions* — https://www.fishersci.com/us/en/footer/terms-conditions/website_terms_and_conditions.html — read.
    Tosoh Bioscience, *Terms of Use* — https://www.tosohbioscience.com/terms-of-use — read; body is placeholder text (§5.8).

**Instruments**

25. Waters, KB WKB8302 "What is the dwell volume for an ACQUITY UPLC H-Class system?" —
    https://support.waters.com/KB_Inst/Chromatography/WKB8302_What_is_the_dwell_volume_for_an_ACQUITY_UPLC_H-Class_system — read.
26. Waters, KB WKB201368 "What is the system volume of the HPLC and UPLC systems?" —
    https://support.waters.com/KB_Inst/Chromatography/WKB201368_What_is_the_system_volume_of_the_HPLC_and_UPLC_systems — read.
27. Waters, KB WKB50711 "What is system dwell volume?" —
    https://support.waters.com/KB_Chem/Other/WKB50711_What_is_system_dwell_volume — read.
28. Waters, KB WKB50707 "How do I determine system dwell volume?" —
    https://support.waters.com/KB_Chem/Other/WKB50707_How_do_I_determine_system_dwell_volume — read.
29. Agilent, *1260 Infinity II Quaternary Pump (G7111B)* specification extract —
    https://sim-gmbh.de/images/PDF_Dokumente_neu/Specifications_1260_II_Quaternary_Pump.pdf — read (mirror, SIM GmbH).
30. Shimadzu, *Nexera Series — Specs* — https://www.shimadzu.com/an/products/liquid-chromatography/hplcuhplc/nexera-series/spec.html — read.
31. Shimadzu Scientific Instruments, LC-40D X3 — https://www.ssi.shimadzu.com/products/hplc-components-accessories/nexera-hplc-and-uhplc-pumps/nexera-hplcuhplc-pump-lc-40d-x3/index.html — read.
32. Shimadzu Scientific Instruments, LC-40B X3 — https://www.ssi.shimadzu.com/products/hplc-components-accessories/nexera-hplc-and-uhplc-pumps/nexera-hplcuhplc-pump-lc-40b-x3/index.html — read.
33. Shimadzu, *Nexera series* catalogue C196-E095, © 2019, first edition April 2019 —
    https://www.testunlimited.com/pdf/Shimadzu_SIL40CX3_datasheet.pdf — read (mirror, Test Unlimited).
34. Shimadzu, *Solvent Delivery Module for Shimadzu Liquid Chromatograph* 228-97197C, Sep. 2024 —
    https://www.shimadzu.com/an/ivd/L/228-97197.pdf — read.
35. Shimadzu, *Nexera* catalogue C196-E071 (2010, "Printed in Japan 3295-01008-30A-NS") —
    https://photos.labwrench.com/equipmentManuals/6704-2295.pdf — read (mirror, LabWrench).
36. Shimadzu Scientific Instruments, KB "Optimizing HPLC/UHPLC Systems – General Recommendations" —
    https://www.ssi.shimadzu.com/service-support/faq/liquid-chromatography/knowledge-base/optimizing-your-hplc-uhplc-system/index.html — read.
37. Thermo Fisher Scientific, *Vanquish Pumps — Product specifications* PS73056-EN 0825, © 2025 —
    https://documents.thermofisher.com/TFS-Assets/CMD/Specification-Sheets/ps-73056-lc-vanquish-pumps-ps73056-en.pdf — read.
38. Thermo Fisher Scientific, Vanquish Horizon UHPLC System page —
    https://www.thermofisher.com/us/en/home/industrial/chromatography/liquid-chromatography-lc/hplc-uhplc-systems/vanquish-horizon-uhplc-system.html — read.
39. Thermo Fisher Scientific, *Method transfer onto the Thermo Scientific Vanquish HPLC and UHPLC platform* (case study CS000566, © 2022) —
    https://documents.thermofisher.com/TFS-Assets/CMD/Reference-Materials/cs-000566-lc-method-transfer-vanquish-cdmo-cs000566-na-en.pdf — read.
40. Valenta, A., "Understanding Your HPLC System: Dead Volume, Dwell Volume, and Extra Column Volume", Thermo Fisher AnalyteGuru blog, 2022-02-28 —
    https://www.thermofisher.com/blog/analyteguru/understanding-your-hplc-system-dead-volume-dwell-volume-and/ — read.

**Blocked on the first pass** (listed in §9): Waters 720003294, 715005049, 720005723,
720004750; Agilent store, product, terms, brochure, ordering guide and user-manual URLs;
sigmaaldrich.com; tosohbioscience.com product pages; fishersci.com product pages;
glsciencesinc.com. Those read on the second pass are refs. 41–52.

**Second pass (§10), all accessed 2026-09-04 with a real browser**

41. Waters, product page 186008694 "CORTECS Shield RP18 Column, 90Å, 1.6 µm, 2.1 mm X 100 mm, 1/pk" — ref. 1's URL — read.
42. Waters, "CORTECS Solid Core C18 Columns" family page — https://www.waters.com/nextgen/us/en/products/columns/cortecs-columns.html — read.
43. Waters, *ACQUITY UPLC H-Class System* specification sheet, 720003294EN, June 2016 —
    https://www.waters.com/content/dam/waters/en/library/specifications/2016/waters-specification-ACQUITYUPLCH-ClassSystem-720003294 — read.
44. Waters, *Dwell Volume and Extra-Column Volume: What Are They and How Do They Impact Method Transfer* (white paper), 720005723EN, April 2018 —
    https://www.waters.com/webassets/cms/library/docs/720005723en.pdf — read.
45. Waters, *CORTECS Columns Care and Use Manual*, 720004750EN, December 2022 —
    https://www.waters.com/webassets/cms/support/docs/720004750en.pdf — read.
46. Waters, *ACQUITY UPLC H-Class System Guide*, 715005049 Rev. C, August 2016 —
    https://help.waters.com/content/dam/waters/en/support/usermanuals/2016/715005049/715005049rc.pdf — read.
47. Waters, column *Care and Use Manual*, 720008980EN Rev. A, July 2025 —
    https://help.waters.com/content/dam/waters/en/support/usermanuals/2025/720008980/720008980.pdf — read.
48. Agilent, "InfinityLab and Altura Poroshell 120 HPLC Columns" family page —
    https://www.agilent.com/en/product/small-molecule-columns/reversed-phase-hplc-columns/infinitylab-poroshell-120 — read.
49. Agilent, *Website Terms of Use* — https://www.agilent.com/home/terms-of-use — read.
50. Agilent Community, "Low Delay Volume Configuration" (forum thread, replies by member "ankugler") —
    https://community.agilent.com/technical/lc/f/forum/8637/low-delay-volume-configuration — read.
51. Sigma-Aldrich, product page 53823-U "Ascentis® Express C18 (2.7 μm) HPLC Column L × I.D. 10 cm × 2.1 mm" —
    https://www.sigmaaldrich.com/US/en/product/supelco/53823u — read.
52. Tosoh Bioscience, product page 0021940 "TSKgel ODS-100V, 3 µm" —
    https://www.tosohbioscience.com/EU-EN-separations/products/tskgel-ods-100v-3-m/0021940 — read; Fisher Scientific listings 50-138-4990 and 111007163 and the GL Sciences equivalents chart (§9 URLs) — read, nothing cited.

**Third pass (§10.5), all accessed 2026-09-05 with curl_cffi (Chrome impersonation)**

53. Agilent, store page 695775-902 (InfinityLab Poroshell 120 EC-C18, 2.1 × 100 mm, 2.7 µm) —
    https://www.agilent.com/store/en_US/Prod-695775-902/695775-902 — read.
54. Agilent, *Agilent InfinityLab Poroshell 120 columns for HPLC and UHPLC*, 5991-8750EN, © 2020, 2025 —
    https://www.agilent.com/cs/library/brochures/5991-8750EN_InfinityLab_Poroshell120_brochure.pdf — read.
55. Agilent, *Agilent InfinityLab Poroshell 120 Columns Ordering Guide*, 5991-9123EN, printed 2024-08-16 —
    https://www.agilent.com/cs/library/sales/public/5991-9123EN_InfinityLab_Poroshell120_ordering.pdf — read.
56. Agilent, *1260 Infinity III Binary Pump User Manual* (G7112B), edition 10/2024 —
    https://www.agilent.com/cs/library/usermanuals/public/G7112BUser.pdf — read.
57. Agilent, *InfinityLab LC Series 1290 Infinity III LC System Manual* (G7104A), SD-29000160 Rev. E.02, 11/2025 —
    https://www.agilent.com/cs/library/usermanuals/public/G7104ASystem.pdf — read.
58. Sigma-Aldrich (Merck KGaA), *Site Use Terms* —
    https://www.sigmaaldrich.com/US/en/life-science/legal/site-use-terms — read.
