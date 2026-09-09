---
status: accepted
date: 2026-09-09
ticket: "architecture review 2026-09-09 — app/"
---

# The frame put-backs stay at their call sites

`streamlit_app.py` reconciles an edited table frame against its canonical rendering in
three places: once in `_scouting_table`, twice in `_candidate_table`. Each is the same
shape — read the frame back, re-render it canonically, and if the two disagree, replace
the stored frame and rerun.

The 2026-09-09 architecture review of `app/` proposed moving that reconciliation into
`app/tables.py`, beside `frames_agree`, on the grounds that the comparison primitive
already lives there. The grilling session approved it. Writing it showed it was a
pass-through, and it was dropped from the ticket that shipped
(`build/takeover-rule`, "Give the takeover rule one home and one spelling"). This record
exists so the next review does not re-suggest it.

## Why it was rejected

- **The decision is already one call.** The whole of the put-back decision is
  `not tables.frames_agree(canonical, edited)`. A `needs_putback(canonical, edited)`
  wrapping it would be a module whose interface is the whole of its implementation —
  shallow by construction, the same objection ADR-0001 raised against a re-export surface.
- **The deletion test says *move*, not *concentrate*.** Delete the proposed module and the
  complexity does not reappear across the three call sites: each re-inlines one boolean it
  was already spelling. Nothing concentrates, so nothing is earned.
- **The put-back is not the rule the two controls shared.** The review's real finding was
  the *takeover* rule — `CANDIDATE_TOUCHED` and `AXIS_TOUCHED` as two instances of one
  unnamed concept, written two different ways and compared by nothing. That one had two
  adapters and a genuine asymmetry to resolve, and it shipped as
  `screen_state.follow` (see `CONTEXT.md`, **Taken over**). The put-backs were swept in
  beside it by association, not by sharing its rule.
- **The primitive is already in the right home.** `frames_agree` is in `app/tables.py`
  because comparing two frames is what that module does. Moving the *caller's* branch in
  beside it would put a decision about rerun behaviour into a module that knows nothing
  about reruns.

## Consequences

- The three put-backs stay in `streamlit_app.py`, each as an `if not
  tables.frames_agree(...)` followed by `_replace_frame` and `st.rerun()`. They are inside
  the file mypy does not check, which is a real cost and is accepted: what they contain is
  one call and one rerun, not a rule.
- `app/tables.py` keeps its subject — frames in, domain rows out, and back — and gains no
  knowledge of the entry point's control flow.
- Revisit if a *fourth* put-back appears whose semantics differ from the other three, or if
  the put-back ever needs to decide something beyond "do these two frames read the same".
  Either would make it a rule rather than a call, which is the line this record draws.
