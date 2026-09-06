# Seed records

Two tables of **seed records**: the vendor-stated column and instrument facts that research
#109 verified (`docs/research/vendor-column-and-instrument-data.md`), typed into one place so
the profiles map (#103) has a concrete table to point at and future agents read the
cross-vendor comparison without re-extracting it from prose. Decided on task #113.

A seed record is one vendor-stated fact set from one cited public page, with URL, read date
and provenance. It never carries t0, V0, porosity, or any measurement of the lab's own: no
vendor publishes a per-column V0 or porosity (research doc §3), and t0 belongs to a column on
an instrument, measured or estimated as SPEC §4 says. A *profile* (the app's selectable
object, this map's destination) may be seeded from a record; a record is never a profile.

**This is a research artifact.** No code reads it. It lives here until map #103's storage
ticket decides where profiles live and whether a shipped seed exists at all; it moves then.

## Posture

- Every row is typed from the cited page, never scraped or copied as a table. Nothing here
  reproduces a vendor document beyond the quoted architecture sentence.
- Small and non-commercial: one worked-example part per vendor, and only the fields a spec
  sheet states. Shimadzu's terms forbid compiling a database by systematic retrieval, Thermo
  forbids scraping, Agilent and Sigma-Aldrich forbid automated access; Sigma-Aldrich's Site
  Use Terms carry a research-use carve-out conditioned on attribution and non-commercial
  purpose (research doc §5, §10.3, §10.5). Keep it this size.
- Core scope only (map #103 notes): no pH range, pressure limit, temperature limit, carbon
  load or surface area, even where the vendor states them.

## `read_by`

- `agent` — read by an agent with an ordinary fetch the site served.
- `agent_evading` — read by an agent with a fingerprint-evading client or browser on the
  driver's explicit instruction (research doc §10, §10.5). These rows are the ones the driver
  still owes a **hand re-confirmation**; each says so in `notes`.
- `hand` — read or re-confirmed by a person in a browser. Change the value when that happens.

## `columns.csv`

| Column | Meaning |
|---|---|
| `vendor`, `product_line`, `part_no`, `phase` | As the vendor names them. |
| `length_mm`, `id_mm`, `particle_um`, `pore_a` | Normalised to mm, mm, µm, Å. Where the vendor used cm (Supelco, Tosoh) or nm (Shimadzu, Tosoh) the original string is in `notes`. |
| `architecture` | `core_shell`, `fully_porous`, or `unstated`. What the t0 estimator turns on (#24, #33). |
| `architecture_stated_as` | `field` (a spec-table field on the part's own page), `prose` (a family-page or brochure sentence), `unstated` (the vendor says nothing either way), `declared` (a person asserted it; name and date in `notes`). |
| `architecture_quote` | The vendor's words verbatim; empty when unstated. |
| `source_url`, `source_read_on`, `read_by` | Provenance of the row. |
| `notes` | Original unit strings, second citations, and what still needs hand re-confirmation. |

## `instruments.csv`

A row is one **published dwell figure**, not one instrument: the research found the same
word covers four different quantities across vendors (research doc §6.2), and a per-instrument
row would flatten exactly that. The H-Class therefore has two rows, and the lab's 0.375 mL sits
on the `system_measured_representative` one.

| Column | Meaning |
|---|---|
| `vendor`, `system`, `module` | `module` is empty when the figure is for the whole system. |
| `configuration` | Mixer, loop, mode the figure is stated for. |
| `dwell_ml` | The figure in mL. For a `system_bound` row it is the upper bound the vendor states; where the vendor states a range, the upper end, and the range is in `notes`. Empty for `none_published`. |
| `dwell_kind` | `system_bound` (vendor's upper bound for the whole system), `system_measured_representative` (vendor's own bench measurement on a representative system in a stated configuration), `module_only` (one module's contribution, sampler unstated), `system_sum_case_study` (vendor's per-component sum for a named configuration), `none_published`. |
| `span` | What the vendor says the number spans, in the vendor's words. |
| `source_url`, `source_read_on`, `read_by`, `notes` | As above. |

None of these is a measurement on the lab's instrument. SPEC §4's rule stands: dwell is
required, never silently defaulted; a profile may prefill a vendor figure and must show which
kind it is.
