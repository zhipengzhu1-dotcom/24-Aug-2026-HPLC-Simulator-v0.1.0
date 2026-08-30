# Teaching Notes

- User: working chromatographer (Waters Acquity H-Class, CORTECS UPLC Shield RP18
  2.1×100 mm 1.6 µm, Empower, 0.1% FA water/ACN methods). Deep bench expertise. The
  modeling/software side is the actual learning gap — don't re-teach chromatography
  fundamentals (dwell, t0, gradients) they already have experientially.
- Teach math and architecture *from* lab intuition, not from abstract theory inward.
  E.g. anchor τ = dwell + hold to their own H-Class numbers (t_D = 0.94 min, t0 = 0.6 min)
  rather than a generic symbol-table walk.
- They chose every v0.1 design decision themselves via a grilling process (see wayfinder
  map #1, 10/11 tickets closed). Framing content as "your decision on X" lands well —
  use it deliberately, it's not flattery, it's accurate and it's motivating.
- Session initiated via `HANDOFF.md` at repo root (written 2026-08-26), which pre-loaded
  the mission, knowledge inventory, and teaching order. First `/teach` session in this
  workspace — no prior learning-records exist yet.
- Do not resume build/planning work (ticket #11 spec approval, `/wayfinder`) during teach
  sessions unless the user explicitly asks — see MISSION.md "Out of scope".
- Workspace consolidated into `teach/` (this folder) on 2026-08-26, at the user's request,
  to keep it separate from the project root (`HANDOFF.md`, `SPEC.md`, `validation/`, etc.).
  All internal links are relative and were preserved by moving the whole tree as one unit —
  no link rewrites needed. Treat `teach/` as the workspace root going forward.
