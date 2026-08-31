# Handoff — hplcsim, after #20 (diagnostics)

**Date:** 2026-08-30
**Repo:** `/Users/maracchi/Desktop/Claude/24-Aug-2026 HPLC Simulator v0.1.0`
**Branch:** `main` @ `b2513a2`, clean tree, pushed to origin
**Next focus:** **#21**, then **#22** — and a decision on #24 that the last section arms

---

## Where things stand

Ticket **#20** (diagnostics and tracking checks) is merged and closed. The account
lives in the places that own it — do not re-derive it here:

- Completion record, walking every acceptance criterion: the closing comment on
  [issue #20](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/20)
- What was built: merge commit `b2513a2`; module layout in `SPEC.md` §9 (amended `26610c1`)
- Review findings and their fixes: `1acb610`, whose message also records the two
  findings that were deliberately *not* acted on and why

Verified on `main` **after** the merge, not just on the branch: **282 tests pass**,
`ruff check`, `ruff format --check` and `mypy` all clean.

The v0.1 build sequence is 10 tickets. #14–#20 and #23 are done. Remaining: **#21, #22**.

## Start here: ticket #21

`gh issue view 21`. #20 left it two things on purpose:

- The **session schema** must learn to store half-paired rows. `app/pipeline.py`'s
  `PeakRow` is the type; `hplcsim/session.py` still round-trips `Peak`, which requires
  both retention times. #19's module docstring already names this as #21's.
- The **guided empty state** and the **sticky chromatogram** (SPEC §7's "carried forward
  from the prototype") are still unbuilt.

## What #20 established that #21 should follow

**Diagnostics are computed in `app/diagnostics.py` and only *placed* by
`streamlit_app.py`.** Every threshold is a named constant with a test pinning it. If #21
adds anything that decides something, it goes in the logic layer — the entry point holds
widgets and layout, and is still the only file excluded from mypy.

**`tests/test_screen.py` is new and is the answer to this project's worst recurring
hazard.** It drives the real entry point through Streamlit's own `AppTest` and asserts
that messages are actually painted. Use it. Its current limit: `st.data_editor` cannot be
driven from `AppTest`, so anything needing a filled peak table still cannot be screen-tested.

## Standing constraints that bite

`CLAUDE.md` is normative — read it. Beyond it:

- **Parallel ticket sessions get separate `git worktree`s.** Never share one checkout.
- **SPEC and research-doc amendments need the driver's approval of the *exact diff*.**
  Show the diff, wait, then apply behind a verbatim-match `assert` on the anchor text.
  `26610c1` is the worked example.
- **Post-v0.1 findings get their own ticket** opening with "Not for v0.1.0". Filed #37
  this way (the two deferred fit-confidence diagnostics).
- **Stage explicit paths, never the working tree.** `docs/research/porosity-for-t0-geometry.md`
  is an untracked skeleton from a killed `/research` run for #33 — it survived this
  session only because every `git add` named its files.

## Hazards this session hit

**The engine could hang, and pytest does not time out.** `_solve_steepness` spun forever
on transposed retention times; the suite presented it as pytest never returning, not as a
failure. `faulthandler.dump_traceback_later(...)` is what located it. Fixed and recorded
as [#38](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/38),
which also suggests `pytest-timeout` — deliberately not added.

**`uv run` contends with itself.** Two concurrent `uv run` invocations blocked on uv's
lock and looked exactly like a hung test. Kill stragglers before believing a hang.

**Stale bytecode still produces false failures.** `PYTHONDONTWRITEBYTECODE=1 uv run pytest
-p no:cacheprovider`, and clear `__pycache__`, before believing a result that contradicts
the source.

## The open decision, now with numbers: #24 and the dwell

The driver asked whether **#24** (geometry t0 estimator) is impactful enough to keep in
v0.1. Measured this session by refitting the lab compounds from runs 1–2 at a range of
t0 and predicting the held-out runs 3 and 4 — reproducing
`docs/research/dead-time-from-geometry.md` §6.2 independently, to the third decimal:

| t0 | Δt0 | run 3 avg / worst | run 4 avg / worst | fitted S (U1) |
|---|---|---|---|---|
| 0.360 | −40% | 0.558% / 0.784% | 0.508% / 0.735% | 4.592 |
| 0.4243 | −29.3% | 0.504% / 0.717% | 0.441% / 0.651% | 4.714 |
| **0.600** | **0** | **0.355% / 0.534%** | **0.257% / 0.419%** | **5.082** |
| 0.840 | +40% | 0.179% / 0.281% | 0.060% / 0.095% | 5.681 |

**Verdict on the estimator: not impactful for predictions.** SPEC §10's trust bar is 2%
average / 5% worst. A t0 wrong by 40% still lands ~3.6× inside the worst-case bar. What a
wrong t0 *does* corrupt is the science readout — S moves ±12% across that range — so the
case for #24 rests on the reported parameters and on the **reverse check** (its part 3),
not on the chromatogram.

**But the same experiment turned up something bigger.** Notice that predictions get
*better* as t0 rises. Holding the measured t0 = 0.6 and varying the **dwell** instead:

| t_D | V_D | run 3 signed | run 4 signed | avg abs |
|---|---|---|---|---|
| 0.9375 (**spec sheet, shipped**) | 0.375 mL | **+0.355%** | **−0.257%** | 0.306% |
| 1.15 | 0.460 mL | +0.173% | −0.033% | 0.132% |
| **1.25** | **0.500 mL** | **+0.088%** | **+0.074%** | **0.110%** |
| 1.35 | 0.540 mL | +0.002% | +0.181% | 0.141% |

**SPEC §10 attributes the flipping signed bias (+0.35% / −0.26%) to "mild LSS curvature,
chromatographically negligible". The data fit an underestimated dwell at least as well.**
One additive constant nulls the bias on *both* held-out runs simultaneously, and they
have opposite signs — curvature is not removed by a single additive shift. Moving V_D
from the spec-sheet 0.375 mL to ~0.50 mL improves held-out accuracy **2.8×**, and
`validation/method.csv` records the shipped figure as *"from instrument spec sheet, NOT
measured"*. A 33% understatement is unremarkable for an as-plumbed dwell volume.

**Caveats, stated so nobody over-reads this.** One parameter fitted to two held-out runs
and three compounds is not a measurement. t0 and dwell are partly degenerate — both enter
additively — and the only reason to attribute the offset to the dwell is that t0 was
measured with a marker and the dwell was not. The real answer costs one injection:
`validation/PROTOCOL.md` §1 already gives the procedure.

**Recommendation, for the driver to accept or reject:**

1. **File and prioritise the dwell ticket** above #24. It is one bench measurement, it is
   the largest uncorrected error in the validation dataset, and it is not absorbed by the
   two-run fit.
2. **Defer #24's estimator; keep its reverse check in view.** The reverse check would
   have caught the driver's own anomaly — ε_T = 0.6929 on a solid-core column, where a
   marker time inflated by extra-column volume is one of the tiers it warns on.
3. **Either way, SPEC §4 needs a decision**, because it promises a geometry estimator
   v0.1 does not have. Softening it is a one-line diff; building #24 is a ticket.
4. **SPEC §10's "mild LSS curvature" sentence should not stand unqualified** once the
   dwell is measured. It is a claim about cause, and the cause is now in doubt.

None of 1–4 was actioned. They are the driver's calls.

## Conventions worth copying

- Completed tickets get a handoff in `docs/handoffs/`; this is one of them.
- Ticket branches are `build/NN-slug`, merged with `git merge --no-ff`, then the issue is
  closed with a completion comment that walks the acceptance criteria.
- Commit messages explain *why* and name the evidence, and carry the `Co-Authored-By` /
  `Claude-Session` trailers.
- `/implement` for building from a ticket, `/tdd` at agreed seams, `/code-review` before
  every merge — it runs Standards and Spec as parallel sub-agents and does not rerank
  across them. **Verify its findings against the code before relaying them.** Both agents
  were accurate this session; that was checked, not assumed.
