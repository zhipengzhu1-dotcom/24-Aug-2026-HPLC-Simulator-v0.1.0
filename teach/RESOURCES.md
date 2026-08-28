# HPLC Gradient Simulator — Resources

## Knowledge

- [`docs/research/gradient-elution-math.md`](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/blob/research/gradient-math/docs/research/gradient-elution-math.md) (branch `research/gradient-math`, 1058 lines)
  The workspace's primary source for everything mathematical. Symbol table (§1), the
  log-base trap (§0), the gradient retention closed form and its derivation (§2), the
  two-run fit — seed and exact root-find (§3), edge cases (§4), peak width and band
  compression (§5), resolution (§6), and the known pitfalls incl. β=3 and LSS curvature
  (§7). Every equation is tagged with the paper that owns it or marked **[derived]**.
  Use for: any lesson touching the science model.
- [`docs/research/validation-datasets.md`](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/blob/research/validation-datasets/docs/research/validation-datasets.md) (branch `research/validation-datasets`)
  The den Uijl Sets X/Y reference numbers the three-layer test bar (`SPEC.md` §10) checks
  against. Use for: lessons on validation methodology and trust bars.
- `validation/` on `main` (`PROTOCOL.md`, `method.csv`, `run1–4.csv`)
  The user's own real lab dataset — H-Class/CORTECS, tG=15 & 45 scouting runs, tG=25 & 60
  confirmation runs. Use for: concrete worked examples instead of synthetic numbers;
  this is what actually validated the engine.
- Guillarme, Bouvarel, Rouvière & Heinisch, *J. Sep. Sci.* **45** (2022) 3276–3285,
  [DOI](https://doi.org/10.1002/jssc.202200161) — base-10 LSS convention, the two-run
  composition-domain fit (their Eqs. 8–16), typical S ranges. The single most-cited
  source in the research doc.
- den Uijl, Schoenmakers, Pirok & van Bommel, *J. Sep. Sci.* **44** (2021) 88–114,
  [PMC7821232](https://pmc.ncbi.nlm.nih.gov/articles/PMC7821232/) — natural-log LSS
  convention, the general (numerically-integrated) retention equation, honest treatment
  of where LSS breaks down (§7.5 of the research doc), alternative retention models.
- Molnár, *J. Chromatogr. A* **965** (2002) 175–194,
  [PDF](https://molnar-institute.com/fileadmin/user_upload/Literature/_2002_Molnar_Compu.pdf) —
  the DryLab-class standard algorithm order (§3.4): measure the instrument, run two
  scouting gradients, track peaks, fit, predict, optimize. Source for β=3 and the
  dwell-volume-must-be-measured discipline.
- Poole & Atapattu, *J. Chromatogr. A* **1675** (2022) 463153,
  [PubMed 35609444](https://pubmed.ncbi.nlm.nih.gov/35609444/) — why the engine fits k0
  rather than kw, and the empirical small-molecule S range (1.69–6.33).

## Wisdom (Communities)

- Not yet explored. The user's expertise is already at the practitioner level for the lab
  science; the gap being taught here is modeling/software, which is closer to a knowledge
  problem than a wisdom problem for now. Revisit if the user wants to pressure-test the
  simulator's design against other chromatographers or LC-modeling practitioners (e.g. the
  Separation Science community, LCGC forums) once v0.1 is built.

## Gaps

- Wang, Stoll, Schellinger & Carr (2006) and Wilson, Groskreutz & Weber (2016) are cited
  heavily in the research doc (peak width, band compression) but not yet read directly in
  a teaching session — currently taught secondhand via the research doc's quotes.
- The band-compression factor G's log-base convention is explicitly flagged unverified in
  the research doc (§10) — an open hazard, not a resolved fact. Don't teach it as settled.
- Quarry, Grob & Snyder (1986), which owns the rigorous error-propagation analysis behind
  the β=3 recommendation, could not be obtained by the research session. The numeric
  sensitivity table in §7.2 of the research doc is the best available substitute.
