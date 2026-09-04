# Handoff — 2026-09-03: ticket #55 complete (the extrapolation thresholds re-pinned)

For the next session on the v0.2 gradient-freedom map. Written at the end of the #55 session.
Everything below is a pointer; the detail lives on the tracker and in the commits.

## Where things stand

- [#55](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/55) is
  **closed**; its resolution comment carries the full residual table at t0 = 0.525 and the five
  driver decisions. [PR #68](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/pull/68)
  (`task/55-repin`, worktree `../hplcsim-55-repin`) **awaits merge**: commit 1 is the
  driver-approved diff, commit 2 the /code-review fix-up — merging approves the fix-up wording.
  Gate on the branch: 510 passed, ruff and mypy clean.
- The map [#41](https://github.com/zhipengzhu1-dotcom/24-Aug-2026-HPLC-Simulator-v0.1.0/issues/41)
  has no open decision tickets. Only the build tasks #61 / #62 remain; #61 has a comment
  pointing at the settled numbers and the diagnostic 7 message change (no evaluated multiplier).

## What the next session must know that is not on a ticket

1. **Nothing in SPEC §6 or §10 is provisional any more.** 0.6 window-widths (v0.1
   continuity, untested), +10 %B departure (untested below), 0.5 % ceiling on both samples,
   ordering on 7-strong in-bracket runs only.
2. **Δφ0 is a departure.** The driver reads a bare "%B" threshold as an absolute starting
   composition; always write "departure from the scouting start" with a worked example.
3. **SPEC §10 item 2 was corrected** (diagnostic 1 silent on four-peak run 5, diagnostic 9 on
   all four of its peaks) — the build's fire/silent acceptance list changed; #61 knows.
4. A fresh worktree needs `uv sync --python 3.12 --extra app` before the gate.

## Suggested next steps

- Merge PR #68 after reading its "fix-up" section.
- Cut the build from #61 / #62 (`/implement` or `/tdd` per ticket); the map is done.

## Addendum, same day: PR #68 merged, the v0.2 build cut

- Main is at `c252440` (merge of PR #68). The #55 worktree is removed.
- The build was cut from the merged SPEC into seven `ready-for-agent` sub-issues of #61
  (table in #61's last comment): #75 reality-layer assertions, #69 programme type,
  #70 walker, #71 session schema 2, #72 nine diagnostics, #73 rail tables, #74 overlay
  and surfaces. #62 (axis strip) is relabelled `ready-for-agent` and blocks #73.
- **Frontier**: #75, #69, #62 — parallel-safe in separate worktrees (`build/NN-slug`), and
  a fresh worktree needs `uv sync --python 3.12 --extra app` first.
- zsh arrays are 1-indexed: a `declare -a` loop over ticket titles created one blank title
  and shifted the rest; fixed by retitling. Use explicit variables for batch `gh` creation.
