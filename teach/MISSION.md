# Mission: Understanding the HPLC Gradient Method Simulator

## Why
The user is a working chromatographer (Waters Acquity H-Class, CORTECS UPLC Shield RP18
2.1×100 mm 1.6 µm, Empower, 0.1% FA water/ACN methods) who directed the design of a
gradient-method simulator (v0.1 spec approved, build pending — see [wayfinder map #1](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/1))
but experiences the *modeling and software side* as the unfamiliar part. They want to fully
own the tool they commissioned — able to explain to a colleague, or to themselves six months
from now, why it predicted their real confirmation runs to within 0.35% and 0.26% average
error, what math is actually running underneath, and how the three artifacts on disk
(UI mock, engine preview, planned product) relate to each other and to the still-open
build work (ticket #11, spec approval).

## Success looks like
- Can distinguish, without notes, the three things that have each been called "the prototype"
  (`prototype/main-screen` UI mock, the in-conversation engine preview, the drafted `SPEC.md`)
  and say what each one proves or doesn't prove.
- Can explain *why* two scouting runs (tG and ~3·tG) are enough to fit each peak's
  retention parameters — in their own words, from lab intuition (dwell, t0, gradient) up
  to the LSS equation, not by reciting the derivation.
- Can walk through the headline validation result (tG=25 interpolation, tG=60 extrapolation)
  and explain what the sign-flip in the residual bias means chromatographically (mild LSS
  curvature) versus what it would mean if it were dwell-time error.
- Can name the open hazards in the current spec (band-compression `G` log-base convention,
  the log-base trap generally, β=3 spacing) and why each matters before the app is built.
- Understands the architecture decision (thin Streamlit UI over a pure `hplcsim` engine
  library) well enough to explain why it was made, not just that it was made.

## Constraints
- Sessions proceed via the `teach` skill's lesson format: short, one-tangible-win-at-a-time,
  building on real lab intuition rather than abstract math-first exposition.
- The user already understands dwell volume, t0, and gradients experientially — teaching
  should build *on* that, not re-explain chromatography basics.
- All quantitative claims must trace to the primary sources already gathered in the repo
  (`docs/research/gradient-elution-math.md` on `research/gradient-math`,
  `docs/research/validation-datasets.md` on `research/validation-datasets`) — don't
  re-derive from parametric memory when a sourced equation exists.
- The user chose every v0.1 design decision themselves via a "grilling" process; framing
  material as "your decision on X" is effective and should be used deliberately.

## Out of scope
- Resuming build or planning work on the simulator itself (ticket #11 spec approval,
  writing `src/hplcsim/`) — that's `/wayfinder` territory, not `/teach`. Flag it if it comes
  up, but don't drift into it.
- Deferred-roadmap science (multi-segment gradients, temperature/pH modeling, structure-based
  prediction, column-selectivity DB) — v0.1 scope only, per `SPEC.md` §2 and §11.
- General HPLC/UHPLC fundamentals the user already has from bench experience (what a gradient
  is, what t0/dwell mean physically).
