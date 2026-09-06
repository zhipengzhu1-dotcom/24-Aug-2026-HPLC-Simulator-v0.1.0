# Empower's peak-table export: what it contains, in what layouts, and what the app can rely on

Research notes for map [#118](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/118)
ticket [#119](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/119).
**Question:** for Waters Empower 3 (the lab's ACQUITY H-Class CDS), which export routes yield a
per-injection peak table as text; which columns exist and under what header names and units;
whether the instrument method's gradient table comes out alongside; how the file is encoded and
structured; and what SPEC §4 needs that no export carries. The finding the map needs: **a field
list the import contract can name, and the layout variants a reader must tolerate.**
**Date:** 2026-09-06 (every source read that day). **Audience:** the import-contract ticket
[#124](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/124) and
the sample-export task [#120](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/120).

Every claim is tagged **[verified]** (read in the source named), **[derived]** (my inference,
shown) or **[could not verify]** (no public source reached; §6 turns each into a line for #120).
Posture, per the ticket: ordinary fetches only. `support.waters.com` answered every request;
`help.waters.com`, `waters.com/webassets`, Benchling's help centre, ResearchGate and LinkedIn
refused or timed out (§7) and nothing was worked around. No Waters documentation is reproduced:
layouts are described, and header names and short phrases quoted with their source. Open-source
readers of Empower exports were read as *primary* evidence of a real layout (their code encodes
what a file looked like) and are cited by repository, file and commit.

**Headline** (§0): Empower has **one route** that yields a peak table as delimited text a program
can read — an **Export Method** run on results, whose *Fields* tab exports a Report-Publisher-style
peak table plus chosen injection fields, with user-chosen column, row and text-quote delimiters,
one file per result or one summary file for the selection. Every column is user-chosen at export
time, so the file's header row is **whatever the export method's table carries**, not a fixed
schema; the field *names* are stable and known (§2). Peak widths are available at half height
("Width @ 50%") and at several other heights, at tangent, and at baseline, and Empower's time unit
for widths and areas is **seconds** while retention time is **minutes** — the reader must divide
W½ by 60. The **gradient table is not a per-injection field**: it can be *printed* into a report
through the "Instrument Method group", and such a report can be exported as ASCII, but that layout
is unverified; the Fields-tab export carries only the method *names*. Nothing in any export carries
dwell, t0, its marker, packing architecture or which scouting run is which — those stay typed.

---

## 0. The owed lists

### 0.1 Field list for the import contract

Names in the *display* column are how Empower labels the field in its tables and, by default, in
an exported header row ([derived] from the readers in §2.4 — the four that parse a real export
all match on display names; #120 confirms). The *API/database* column is the identifier the
Empower Web API returns, read from the Benchling adapter's fixture (§2.4, ref. 21); it is what a
custom-renamed heading is a rename *of*. Units per §2.3.

| Role in SPEC §4 | Display name | API / database name | Unit | Tag |
|---|---|---|---|---|
| peak tR | "Retention Time" (table heading commonly "RT") | `RetentionTime` | min | [verified] name and unit (fixture, refs. 21, 28); heading form [could not verify] |
| peak area (raw) | "Area" | `Area` | µV·s | [verified] refs. 21, 28 |
| peak area (%) | "% Area" | `PctArea` | % of total area in the result | [verified] name ref. 21; heading form [could not verify] |
| peak height | "Height" | `Height` | µV | [verified] refs. 21, 28 |
| W½ | "Width @ 50%" | — (system-suitability field) | s [derived] | [verified] name refs. 16, 11; unit [derived] §2.3 |
| other widths | "Width @ Tangent", "Width @ 5%", "Width @ 10%", "Width @ 4.4%", "Width @ 13.4%", "Width @ 32.4%", "Width @ 60.7%", "Width @ Baseline", "f @ 5%" | — | s [derived] | [verified] names ref. 16 |
| baseline width | "Width" | `Width` | s | [verified] value = (EndTime − StartTime)·60 in ref. 21 |
| peak name | "Name" (blank when unassigned) | `Name` | text | [verified] ref. 21; blank-when-unassigned [derived] |
| peak status | "Peak Type" ("Found", "Missing", "Group"), "Int Type" ("BB", "BV", "VB", "VV", "EE", "TT"; lowercase = manual), "Peak Codes" | `PeakType`, `IntType`, `PeakCodes` | text | [verified] refs. 16, 21, 12 |
| sample name | "SampleName" (one word) | `SampleName` | text | [verified] refs. 21, 24, 26, 27, 29 |
| vial / injection no. | "Vial", "Injection" | `Vial`, `Injection` | text / int | [verified] refs. 21, 27, 29 |
| injection identity | "Injection Id", "Result Id" | `InjectionId`, `ResultId` | int | [verified] ref. 21; Result ID also the 4-char suffix of the export file name (§4.4) |
| acquisition date | "Date Acquired" | `DateAcquired` | e.g. `1/7/2022 3:22:48 PM GMT` in a text export; ISO in the API | [verified] refs. 24, 21 |
| methods | "Acq Method Set", "Instrument Method Name", "Processing Method" | `AcqMethodSet`, `InstrumentMethodName`, `ProcessingMethod` | text | [verified] ref. 21; display spelling [derived] |
| channel | "Channel", "Channel Description" (e.g. `254nm`), "Processed Channel Descr." | `Channel`, `ChannelDescription`, `ProcessedChanDesc` | text | [verified] ref. 21 |
| run constants present | "Injection Volume", "Run Time", "Column Name", "Column Serial Number", "Sample Type", "System Name", "Sample Set Name", "Sample Set Start Date" | `InjectionVolume`, `RunTime`, `ColumnName`, `ColumnSerialNumber`, `SampleType`, `SystemName`, `SampleSetName`, `SampleSetStartDate` | µL, min, text | [verified] refs. 21, 24 |
| software version | — | `AcqSWVersion` | text | [verified] ref. 21 (null in both fixtures) |

Absent from every export route: flow rate, %B start/end, initial hold, tG, column temperature,
dwell, t0, t0 marker, packing architecture, particle size, column length and i.d. (§5).

### 0.2 Layout variants a reader must tolerate

| # | Variant | Evidence | Tag |
|---|---|---|---|
| L1 | **Table export, one file per result** ("Individual"): optional table-title line (e.g. `Component Results`), a header row, one row per peak; optional leading `#` row-number column; text fields quoted with the chosen quote character; numeric fields bare | refs. 3, 6, 27 | [verified] |
| L2 | **Table export, one file for the selection** ("Summary By All" / "By Vial" / "By Injection"): the same table with an injection-identifying column (SampleName, Vial, Injection, Date Acquired) so many injections share one file; or a cross-tab (samples as rows, peak names as columns, one value per cell) | refs. 3, 5, 27 | [verified] shapes; column order [could not verify] |
| L3 | **Field-data legend before the table**, in either orientation: *Row* = one `label<delim>value` pair per line; *Column* = one line of labels then one line of values, then the table | refs. 6, 24, 25, 26, 29 (raw-data legends, same option) | [verified] for raw-data exports; [derived] for table exports |
| L4 | **Delimiters are export-method choices**: column delimiter (comma, tab and semicolon all seen or expected by readers), row delimiter, and text quotes none / single / double | refs. 3, 4, 6, 27, 29 | [verified] |
| L5 | **Header names are the table's column headings**, which default to the field name but can be renamed in the report/export table editor ("Edit Table") | refs. 3, 6 | [derived] |
| L6 | **Blank cells** where a suitability width could not be calculated (skimmed peaks, some valley-bounded peaks) and for unnamed peaks' Name | ref. 16 | [verified] |
| L7 | **Rows that are not peaks**: "Missing" component rows (a named component with no found peak) and "Group" rows are peak-table rows in the API and, by extension, in a table that lists all components | ref. 21 (the adapter skips `PeakType` in `Missing`, `Group`) | [derived] |
| L8 | **Summary rows** (Mean, %RSD …) under a summary table, and print-layout artefacts (wrapped rows) when a report — not a table — is exported as ASCII or pasted from print preview | refs. 4, 30 | [could not verify] for ASCII; [verified] for print-preview paste |
| L9 | **Clipboard paste** of the Injections/Results table ("Copy Table", ≤ 10,000 rows) or of the Review results view: tab-separated cells, presumably with headings | ref. 9 | [verified] route; delimiter and headings [could not verify] |
| L10 | **Raw-data `.arw`** (not a peak table): quoted label/value legend lines, then `time<TAB>signal` rows; a PDA export adds a `Wavelength` line and one column per wavelength | refs. 24, 25, 26, 29 | [verified] |
| L11 | **Decimal separator, encoding, line endings**: every example seen uses `.`; one reader opens `.arw` as latin-1; a forum user recalls `[cr][lf]` as the row delimiter | refs. 25, 30 | [could not verify] |

---

## 1. Export routes

Empower's export is a **method** (an "Export Method"), created under the project's Methods tab
and applied to selected data by right-click → "Export" → "Use Specified Export Method" in the
"Background Processing and Reporting" dialog **[verified]** (refs. 1, 2, 6). The editor has three
tabs, each a distinct route:

1. **Fields tab — database fields and tables, no report method** **[verified]** (refs. 1, 2, 3, 6).
   Options quoted from the KB: "Export ASCII File" (file to a local or network path), "Export
   E-Mail"; "Export Table Data" with "Export Row Numbers"; "Load Table" to pick one of the
   preconfigured Report Publisher tables, "Edit Table" to change its columns; "Export Field Data"
   with a "Label Orientation" of "Row" or "Column" and a sample-identifier list (Waters' example:
   "Sample Name and Injection"); a report type of "Individual", "Summary By All", "Summary By
   Vial" or "Summary By Injection"; and "optional column, row, and text delimiters". WKB32504
   states results export "to an ASCII file using comma-separated values" (ref. 4). WKB85134's
   worked example uses the "Area Component Summary" table with "Summary By All" to produce
   samples-as-rows × peak-names-as-columns of areas (ref. 5). **This is the peak-table route.**
2. **Report tab — a Report Method rendered to a file** **[verified]** (refs. 7, 8). Formats "EMF,
   ASCII, OpenLynx, or PDF"; for ASCII, "optional column and row delimiters" and "text quotes".
   What the ASCII of a *report* looks like (tables only? headers and footers? page breaks?) is
   **[could not verify]**; a 2008 forum answer describes stripping the header and footer from a
   report method holding only an "all peaks table" and exporting it, yielding an `.ARS` file that
   Excel opens (ref. 30) — an older Empower/Millennium extension, worth a look in #120.
3. **Raw Data tab** **[verified]** (refs. 10, 11, 12, 13, 14). Formats "ASCII, AIA, or OpenLynx";
   "Export Time Column" (x axis), "Export Fields" (a legend of sample identifiers), label
   orientation. Output is chromatogram points, `.arw` for ASCII (root name + Channel ID), `.cdf`
   for AIA; no peak table. Listed because its **legend** is the same field-data mechanism as
   route 1's and is the only Empower text layout with public sample files (§4.2).

Other ways a peak table leaves Empower, none of them a file a reader should target:

- **Clipboard.** "Copy Table" from the Injections or Results tab (Empower icon in the table
  corner → File → Copy Table; up to 10,000 rows) **[verified]** (ref. 9); copying a table from
  Preview/Publisher print preview, which a forum user reports mis-wraps rows **[verified]**
  (ref. 30). The repo's `validation/paste-run1-run2.tsv` is this shape.
- **PDF / print** of a report or of an instrument method (§3) — not text **[verified]** (ref. 17).
- **Empower Web API (JSON)** — Benchling's adapter, Novo Nordisk's OptiHPLCHandler and the
  Acceleration Consortium's COM wrapper all use it (refs. 21, 22, 23). A licensed toolkit, not an
  export; used here only as the authority on field names.
- **Project export (`.exp`)** is an Oracle schema dump used by backup **[verified]** (ref. 18);
  ACD's "Empower .raw" import (`acd-method-selection-suite.md` §2.6) reads Empower's binary
  side, not text.

## 2. Columns, header names, units, width definitions

### 2.1 Peak fields

Empower's integration fields on any Peaks table: `Name`, `RetentionTime`, `Area`, `PctArea`,
`Height`, `PctHeight`, `Width`, `StartTime`, `EndTime`, `IntType`, `PeakType`, `PeakCodes`,
`PeakLabel`, `Amount`, `PctAmount`, `Response`, `Units`, `RelativeRT`, `RRT~`, `InflectionWidth`,
`PointsAcrossPeak`, `Slope`, `StartHeight`, `EndHeight`, `BaselineStart`, `BaselineEnd`, plus ~50
quantitation/impurity fields **[verified]** as the key set of a peak in the Empower Web API
fixture (ref. 21, `tests/parsers/benchling_empower/testdata/input/example_01.json`). Note the API
carries **no** `Width50`, `USPTailing`, `USPPlateCount`, `Resolution` or `KPrime` keys in that
fixture — the suitability fields are absent, not null, when the processing method's Suitability
tab is off **[derived]**; a lab that wants W½ in the export must have suitability enabled.

### 2.2 Width definitions Empower offers

From the *Empower System Suitability Quick Reference Guide* (Waters 71500031605 Rev. A, © 2002,
read from a distributor's copy, ref. 16), Table 3-1, which lists the result fields by the
pharmacopeia option chosen on the processing method's Suitability tab (EP / JP / USP / All)
**[verified]**:

| Field | EP | JP | USP | All | Definition (ref. 16 §3.2–3.3) |
|---|---|---|---|---|---|
| "Width @ 50%" | ✓ | ✓ | ✓ | ✓ | x₂ − x₁ at 50 % of peak height above the baseline |
| "Width @ 5%", "f @ 5%" | ✓ | ✓ | ✓ | ✓ | width at 5 % height; front half from the 5 % start point to RT |
| "Width @ Tangent" | — | — | ✓ | ✓ | distance between the baseline intercepts of tangents through the inflection region (needs the widths at tangent-% ± 5 to exist) |
| "Width @ 4.4%", "Width @ 10%", "Width @ 13.4%", "Width @ 32.4%", "Width @ 60.7%", "Width @ Baseline" | — | — | — | ✓ | width at that % height; baseline width |
| "USP Resolution" / "USP Resolution (HH)" | — | — | ✓ | ✓ | tangent width / half-height width forms **[verified]** ref. 15 |
| "USP Plate Count", "EP Plate Count", "JP Plate Count", "USP Tailing", "Symmetry Factor", "K Prime", "Resolution", "Relative Resolution" | per column | | | | plate count N = 5.54 (RT/W)² (EP) and 5.55 (JP) with W = width at 50 % **[verified]** ref. 19 |

The KB articles use the same spellings today: "Width @ 50%", "Width @ Tangent (USP Resolution)"
(ref. 11), "Width @5%", "f@5%" (ref. 12, with the space dropped), "Width at Tangent" in prose
(ref. 13). Widths at % height are **blank** for skimmed peaks and for valley-bounded peaks whose
start or end lies above the % line; tangent width is blank unless both flanking widths exist
**[verified]** (ref. 16 §3.2–3.3; ref. 20 lists the same conditions for a blank resolution).

### 2.3 Units

- **Retention time in minutes.** Fixture values (RT 1.2487, StartTime 1.1583, EndTime 1.4167 on a
  6-min run) and the adapter's explicit min→s conversion **[verified]** (ref. 21).
- **Peak widths and areas in seconds.** WKB2764: "Time units are minutes for MassLynx and seconds
  for Empower", Empower reports "peak area as µV*second" and 1 AU ≡ 1,000,000 height counts
  **[verified]** (ref. 28). In the fixture `Width` = 15.5 while EndTime − StartTime = 0.2583 min =
  15.5 s, for all four peaks **[verified]** (ref. 21). That "Width @ 50%" follows the same
  seconds convention is **[derived]** — no public page states its unit; #120 settles it by
  comparing an exported W½ with the repo's minute values (`validation/*.csv` W½ ≈ 0.023–0.09 min
  → expect ≈ 1.4–5.6 s).
- **% Area** is per result (one channel of one injection), summing to 100 over the peaks the
  processing method found **[derived]** from the fixture values (27.94 + 27.72 + 22.00 + 22.33).

### 2.4 Header names in a real text export

No Waters page shows an exported header row. Four independent readers of real Empower text
exports do, and they agree on display names:

- `drkvogel/retrasst` `LADS/HPLCComms/FormEnterResults.cpp` @ `ee952fe` (ref. 27): a
  **comma-delimited, single-quoted** Export-Method table. The reader skips a `Component Results`
  title line and a header line beginning `'#','SampleName'`, then reads per row `#`, SampleName,
  Name, Concentration, Area/Height, Date Acquired, Vial — row numbers first (the "Export Row
  Numbers" option), text fields quoted, numerics bare **[verified]**. Its version history
  ("1.1.1, 13/9/05 Bug fix: skip 'Component Results' line") shows the title line appearing with a
  software or method change **[verified]**.
- `Kolmagorov/traceR` `R/helpers.R`, `R/parsers.R` @ `9d6a54e` (ref. 29): detects an Empower file
  by `SampleName` or `Date Acquired` on line 1, trying `,`, `;` and tab in turn; reads line 1 as
  labels and line 2 as values (the *Column* label orientation) and parses `Date Acquired` with
  day-first, month-first and year-first orders, with or without AM/PM and a zone token
  **[verified]**.
- `ArchercatNEO/HPLC` README @ `ac89e1d` (ref. 24): an `.arw` legend in *Row* orientation —
  `"SampleName"<TAB>"BF111"`, `"System Name"`, `"Sample Set Name"`, `"Date Acquired"<TAB>"1/7/2022
  3:22:48 PM GMT"`, `"Sample Set Start Date"` — then `time<TAB>signal` **[verified]**.
- `kittujoo/HM` `.../empower/pages/project/injections_tab.py` @ `5f70e7f` (ref. 31), a UI
  automation of Empower's Injections tab: column names `SampleName`, `Vial`, `Injection`,
  `Sample Type`, `Date Acquired`, `Sample Set Name`, `Injection Status` **[verified]** — the same
  spellings, including the one-word `SampleName`.

What no reader shows is the heading Empower puts over `RetentionTime` and `PctArea` in a peak
table ("RT" or "Retention Time"; "% Area") — **[could not verify]**; one AI-skill repository's
Empower signature lists `"Peak Name", "RT", "Area", "Height", "% Area"` (ref. 32) but is not
evidence of a file. #120 settles it.

## 3. Instrument method and gradient table

- The gradient table lives in the **Instrument Method** (solvent lines chosen on its Data tab)
  **[verified]** (ref. 33 search excerpt of WKB2231 / Tip 12). It is not a per-injection field:
  the injection and result field sets carry `InstrumentMethodName`, `InstrumentMethodId`,
  `AcqMethodSet`, `RunTime`, `InjectionVolume`, `ColumnName`, `ColumnSerialNumber` (the eCord)
  and no flow, composition or temperature **[verified]** (ref. 21 key lists; `ColumnName` was
  null in both fixtures).
- A report can **print** the method: Report Publisher has an "Instrument Method group" to drag
  onto a report **[verified]** (ref. 34); an instrument method alone can be previewed with an
  auto-generated report method and saved as **PDF** or printed **[verified]** (ref. 17). A report
  method holding that group can be exported through the Report tab as ASCII (§1 route 2) —
  whether the gradient table survives as a delimited table, and in what column order (Time /
  Flow / %A / %B / Curve), is **[could not verify]**. The repo's own `validation/*.csv` gradient
  block (`Time (min), Flow (mL/min), %A, %B`) was typed from the method screen, not exported.
- The Web API's `instrument_methods` list (ref. 21 reader) is not text and its content is unread.

**Consequence for #124 [derived]:** import fills the peak table and the run's provenance from
route 1; tG, %B start/end, hold, flow and temperature come either from a second, unverified
report-ASCII layout or stay typed. The mismatch-warning rule in #124 has a value to compare only
if that second layout exists.

## 4. Encoding and structure

### 4.1 Delimiters, quotes, row ends

Column delimiter, row delimiter and text quote are **per-export-method settings** with no fixed
default in the KB ("select or specify optional column and row delimiters", "single or double
quotes in the Text field") **[verified]** (refs. 3, 7). Seen in the wild: comma + single quotes
(ref. 27); tab + double quotes (refs. 24, 25, 26); a reader that also expects semicolon
(ref. 29). Waters' "CSV" answer (ref. 4) and its Excel-oriented tips (refs. 1, 6, 14) say
comma-separated. Row delimiter: a forum user recalls `[cr][lf]` being required (ref. 30) —
**[could not verify]**; Windows-hosted, so CRLF is the expectation **[derived]**. The repo's
own files are mostly CRLF already (§4.2).

### 4.2 Header block and table block

- **Field data first, then the table.** With "Export Field Data"/"Export Fields" on, the file
  opens with the chosen identifiers, in *Row* orientation (`label<delim>value` per line, quoted
  — ref. 24) or *Column* orientation (one label line, one value line — ref. 29) **[verified]**
  for raw-data exports; the Fields tab exposes the same option for table exports **[verified]**
  (ref. 3) and the layout is **[derived]** to match.
- **The table**: an optional title line naming the table (`Component Results`, ref. 27), a header
  row of column headings, rows; a leading `#` column when "Export Row Numbers" is on
  **[verified]** (refs. 3, 27).
- **Encoding**: no Waters statement found. chromConverter opens `.arw` as latin-1 and detects the
  legend by a `"` on line 1 (ref. 25) **[verified]** as that reader's assumption; whether Empower
  writes ANSI, UTF-8 or a BOM is **[could not verify]**. The repo's own hand-made run files
  already span the variants a reader must tolerate (checked 2026-09-06 over `validation/`):
  UTF-8 with CRLF throughout; **eight of the Validation_2 and run-sheet CSVs carry a UTF-8 BOM**
  (`4peaks_run3.csv` onward, `E1.csv`, `E4_Run3.csv`) while the earlier ones do not; a few
  files (`runs-combined.csv`, three run sheets) are LF-only; `method.csv` holds non-ASCII text
  (em dashes) in its notes column. Any reader that reproduces these cell for cell must strip an
  optional BOM and accept either line ending before it ever meets an Empower file.
- **Decimal separator**: every value seen uses `.`; there is no Waters page on regional settings
  and export; a comma-decimal Empower export is **[could not verify]** either way. The lab runs
  in a `.`-decimal locale (its typed files), so #120's sample settles the local case only.
- **Dates**: `1/7/2022 3:22:48 PM GMT` — month-first, 12-hour, zone name — in a text export
  (ref. 24); ISO `1997-09-17T17:03:14` in the API (ref. 21); readers tolerate d/m/y and y/m/d
  orders and `+03`-style zones (ref. 29) **[verified]**. The reader should treat the date as
  provenance text, not parse it into a number.

### 4.3 One injection or many per file

"Individual" writes "a separate report for each of the exported data" items; "Summary By All /
Vial / Injection" write one summary per selection, vial or injection **[verified]** (ref. 3). So
**both** shapes are ordinary: one file per result (L1) and one file holding every selected
injection's peaks with a `SampleName` / `Vial` / `Injection` column (L2), or a cross-tab (ref. 5).
A reader must accept a file with 1..N injections and split on the identifying columns.

### 4.4 File names and trailing rows

- File name = root name (≤ 32 characters) + a 4-character database ID appended at export ("the
  four-digit number in the file name is the 'Result ID'") **[verified]** (refs. 3, 6, 7); for
  raw data the suffix is the Channel ID and the extension `.arw` **[verified]** (ref. 10). The
  sample name is not in the file name unless the root is typed per export — a forum complaint
  (ref. 35). The extension of a Fields-tab ASCII table "varies depending on which format you
  select" (ref. 1) — the actual extension is **[could not verify]** (`.txt`? `.csv`? the 2008
  `.ARS`?).
- Trailing rows: summary tables in Report Publisher can carry statistics; whether an ASCII table
  export appends Mean / %RSD rows is **[could not verify]**. Print-preview pastes wrap long
  rows onto a second line (ref. 30) — a reason not to accept that route.

## 5. What SPEC §4 needs that no export carries

| §4 field | In any Empower text export? | What the import contract does [derived] |
|---|---|---|
| Dwell (t_D or V_D) | No — an instrument property Empower does not store per injection; the lab's 0.375 mL is a measured instrument figure (`vendor-column-and-instrument-data.md` §10) | stays typed; never inferred from the file |
| t0 and its marker | No field. If a marker was injected it is a *peak* row distinguishable only by Name | stays typed; the reader may offer a named peak as a t0 candidate, never assign it |
| Packing architecture, particle, length, i.d. | No. `ColumnName` / `ColumnSerialNumber` (eCord) may carry a part description whose *format* is unverified; SPEC forbids inferring architecture from a name | stays typed; the reader stamps the column name as provenance |
| Flow, temperature, %B start/end, hold, tG | Not in route 1; possibly in a report-ASCII of the Instrument Method group (§3, unverified) | typed until #120 shows the report layout; then a warning on mismatch, never an overwrite |
| Which run is run 1 / run 2 | No — the export is per injection; tG is a method property | the pairing is a user act at load |
| W½ in minutes | "Width @ 50%" exists but only with suitability on, and in seconds | ÷ 60 at the import boundary, the one place the unit changes |
| Area share | "Area" (µV·s) and "% Area" both exist | either; normalised to shares internally as §4 already says |
| Peak name | "Name", blank unless the processing method's component table named it | blank → auto P1…Pn, as §4 already says |

## 6. What #120's sample export must settle

One line per unverified item; the driver ticks each against the real files.

- [ ] Heading text over retention time and % area in a Peaks table export ("RT" vs "Retention Time"; "% Area").
- [ ] Whether "Width @ 50%" exports at all with the lab's processing method (Suitability tab on? which pharmacopeia?) and its **unit** (compare to the repo's minute values; expect ≈ 1.4–5.6 s).
- [ ] The default column delimiter, text-quote character and row terminator the lab's export method writes (open in a hex viewer: `0D 0A`?), and the file **encoding** (BOM? UTF-8? ANSI).
- [ ] The **extension** of a Fields-tab ASCII table file, and the exact file-name suffix (4-char Result ID).
- [ ] Whether the field-data legend precedes the table, in which orientation, and whether a table-title line (`Component Results`-style) is present.
- [ ] "Individual" vs "Summary By All": one file per injection *and* one multi-injection file, as the task already asks; which identifying columns the summary carries and their order.
- [ ] Whether summary/statistics rows or blank lines trail the table.
- [ ] How an unnamed peak's Name cell and a "Missing" component's row look (blank cell? absent row?).
- [ ] Whether a report method with the "Instrument Method group", exported as ASCII, yields the gradient table as delimited rows, and its column order (Time / Flow / %A / %B / Curve) — this decides §3 for #124.
- [ ] What `ColumnName` / `Column Serial Number` contain on the H-Class with the CORTECS eCord (part number? description?).
- [ ] The `Date Acquired` string as written on this system (order, 12/24 h, zone token).
- [ ] The Empower version string (Help → About) for the README, since `AcqSWVersion` was null in both public fixtures.

## 7. Refusals and what could not be verified

Ordinary WebFetch only. Refused or unreachable, for the driver to open by hand:

| Host | URL | Result |
|---|---|---|
| help.waters.com | `https://help.waters.com/help/en/product-support/empower-chromatography-data-system-support/empower-tips/tip-218.html` (Tip 218, Export Methods) | HTTP 403 |
| help.waters.com | `https://help.waters.com/content/dam/waters/en/support/technicalnotesservice/2018/TECN134899112/tecn134899112_r02.pdf` (*Resolution Values in Empower 3*, TECN134899112 Rev. 02 — the width definitions with units) | HTTP 403 |
| help.waters.com | `https://help.waters.com/content/dam/waters/en/support/usermanuals/2017/715005481/715005481ra.pdf` (*Empower 3 Data Acquisition and Processing Theory Guide* 715005481 Rev. A) | timeout |
| help.waters.com | `https://help.waters.com/content/dam/waters/en/support/usermanuals/2022/715007659/715007659v01.pdf` (*Empower System Suitability*, 2022 edition of ref. 16) | timeout |
| waters.com/webassets | `https://www.waters.com/webassets/cms/promotion/docs/FR14%20Appli%20Empower%20ABA.pdf` ("Things you forgot or didn't know about Empower", 2016); `https://www.waters.com/webassets/cms/support/docs/empower_service_packs-cumulative_changes.pdf` (release-notes appendix) | timeout ×2 |
| help.benchling.com | `https://help.benchling.com/hc/en-us/articles/34107168569997--Beta-Waters-Empower-Configuration-Guide` (search snippet: "Peak Table File .csv … additional user-defined custom fields … Injection and Peak data") | HTTP 403 |
| researchgate.net | *What's New in Empower 3* (2010) and *Data Acquisition and Processing Theory Guide* 71500031209 Rev. A, user-uploaded copies | HTTP 403 |
| linkedin.com | `https://www.linkedin.com/pulse/como-exporta-dados-do-software-empower-para-o-formato-flavio-de-jorge` (Portuguese walkthrough of ASCII export) | HTTP 403 |
| forums.waters.com | `https://forums.waters.com/discussion/4510/…` | DNS: host not found |
| chromforum.org | `viewtopic.php?t=43721` (Export of Empower reports), `t=25500` (Export Empower database data), `t=8339&start=15`, `t=52064`, `t=24143` | HTTP 403 to WebFetch; four other threads on the same host (t=8339, 17726, 24048, 79204) were read earlier the same day with a plain fetch |
| yumpu.com | "Exporting raw data in Empower" (forumsci.co.il, Empower 1) | preview text only |

One fetch was declined by the session's own permission layer: a `curl` retry of the refused
URLs with a browser user-agent string, correctly judged a workaround of a refusal. It was not
repeated by any route.

Not verified from any public source (each is a line in §6): the heading form of RT / % Area; the
unit of "Width @ 50%"; the default delimiter, quote, row terminator, encoding and extension of a
Fields-tab table export; whether the legend precedes the table; summary rows; the report-ASCII
layout of the Instrument Method group; the eCord column-name format; the local Date Acquired
string.

## 8. Sources

All read 2026-09-06. Waters KB pages are on `support.waters.com/KB_Inf/…`.

1. WKB193142, *Exporting Data, Results, and Reports with Export Methods in Empower* (Tip 218).
2. MarketScreener mirror of Tip 218, `marketscreener.com/…/Get-Empowered-Tip-218-Export-Methods-32775215/`.
3. WKB3071, *How to create an export method that exports database fields and tables in Empower*.
4. WKB32504, *Can results be exported as a CSV file in Empower 3?*
5. WKB85134, *How to create a method to export Area values with sample name on vertical axis and peak name on horizontal axis with Empower 3*.
6. Search excerpts of refs. 1–3 (Export Fields / Label Orientation / row-number wording).
7. WKB3067, *How to create an Export Method that uses a specified Report Method in Empower*.
8. WKB199288, *Exporting Reports with Export Methods in Empower* (Tip 224).
9. WKB20412, *How to copy and paste a table from the Injection tab in Empower into Excel*.
10. WKB196407, *Exporting Raw Data with Export Methods in Empower* (Tip 223).
11. WKB51220, *Resolution is not being calculated in Empower*.
12. WKB220500, *How to Calculate Peak Fronting* (Tip 247).
13. WKB93215, *Incorrect Width at Tangent values notably affect USP Resolution values…*
14. WKB9865, *How do you export raw data from Empower to a Microsoft Excel spreadsheet?*; WKB77571, *How to export 3D raw data from Empower…*; WKB118708; WKB3069; WKB65425 (AIA).
15. WKB101487, *Empower 3: What is the difference between "USP Resolution" and "USP Resolution (HH)"?*; WKB1287 (points to TECN134899112, refused).
16. Waters, *Empower System Suitability Quick Reference Guide*, 71500031605 Rev. A, © 2002, distributor copy at `d3bql97l1ytoxn.cloudfront.net/app_resources/159150/documentation/507042_en.pdf` (text extracted locally with pdftotext; a second copy at `…/159166/…/506974_en.pdf`).
17. WKB98077, *Empower 3: How to print the instrument method and save as PDF when there is no report method for instrument method*.
18. WKB209087, *What do the name extensions mean on the files used in Empower 3 backup?* (search excerpt: `.exp` = Oracle schema export).
19. WKB113445, *How to calculate plate counts in Empower 3 using peak width at 50% peak height*.
20. WKB51220 (as ref. 11) — blank-resolution conditions.
21. Benchling-Open-Source/allotropy @ `c7dc84c`: `src/allotropy/parsers/benchling_empower/benchling_empower_structure.py`, `benchling_empower_reader.py`, `tests/parsers/benchling_empower/testdata/input/example_01.json`, `example_with_blanks_and_stds.json` (Empower Web API JSON; Apache-2.0).
22. novonordisk-research/OptiHPLCHandler (Empower Web API client; field names only, not read in depth).
23. AccelerationConsortium/waters-acquity-uplc `empower/README.md` (COM wrapper; confirms no text export in that route).
24. ArchercatNEO/HPLC @ `ac89e1d`, `README.md` — verbatim `.arw` legend and data rows.
25. ethanbass/chromConverter @ `9137b85`, `R/read_waters_arw.R` — latin-1 read, `"` on line 1 as legend marker, tab-separated, `Wavelength`/`Time` rows for PDA.
26. Bayer-Group/MOCCA @ `bd00247`, `src/mocca2/parsers/empower.py` (and its copy in ombayley/ChromTroller @ `1247d08`) — tab-separated `.arw`, `Wavelength` and `Time` header lines.
27. drkvogel/retrasst @ `ee952fe`, `LADS/HPLCComms/FormEnterResults.cpp`, `FormFront.cpp` — comma-delimited, single-quoted Export-Method table with `#` row numbers and a `Component Results` title line.
28. WKB2764, *Empower peak area is much larger than the peak area for MassLynx* — "Time units are minutes for MassLynx and seconds for Empower"; µV·s; 1 AU = 10⁶ counts.
29. Kolmagorov/traceR @ `9d6a54e`, `R/helpers.R` (`file_scan`, `time_scan`), `R/parsers.R` (`parse_empower`).
30. Chromatography Forum threads `viewtopic.php?t=8339` (*Empower – Export result tables to Excel*, 2008), `t=17726` (*Exporting peak areas using waters empower*), `t=24048` (*Empower 3 (Waters) Export Format File*), `t=79204` — user reports, read as such.
31. kittujoo/HM @ `5f70e7f`, `JNJ/HM_Doc/New folder/atom/web_framework/empower/pages/project/injections_tab.py` — Injections-tab column names.
32. HERRY423/BioNexus `skills/instrument-data-to-allotrope/scripts/convert_to_asm.py` — a heuristic signature, cited as weak evidence only.
33. Search excerpts of WKB2231 (*What is the "Gradient Start" setting…*) and Tip 12 (WKB50271) — gradient table on the Instrument Method's Data tab.
34. WKB71152, *How do I add the instrument method parameters to my Empower report?*
35. Chromatography Forum `t=24048` — export file names carry a database suffix, not the sample name.
36. Repo: `SPEC.md` §4, §5, §8; `validation/run1.csv`, `validation/Validation_2/4peaks_run1.csv`, `validation/method.csv`, `validation/paste-run1-run2.tsv`, `validation/PROTOCOL.md`; `docs/research/vendor-column-and-instrument-data.md` §9–10; `docs/research/acd-method-selection-suite.md` §2.6.
