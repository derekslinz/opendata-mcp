# PR merge checklist

Every PR — author's own or another's — passes through this checklist
before `gh pr merge`. CI green is necessary, not sufficient.

## The checklist

1. **CI is green.**
   `gh pr checks <N>` — every check is `pass` or `skipped`. Investigate
   any `pending` / `fail` / `cancelled`.

2. **Review state is decided.**
   `gh pr view <N> --json reviews,reviewDecision`
   - `reviewDecision: APPROVED` or no required reviewers → continue.
   - `reviewDecision: CHANGES_REQUESTED` → block; resolve first.
   - `reviewDecision: REVIEW_REQUIRED` → wait or get an explicit waiver.

3. **Every inline review comment is resolved.** This is the gate that
   gets skipped most often, and the one that catches real bugs CI
   doesn't.

   ```
   gh api repos/<owner>/<repo>/pulls/<N>/comments
   ```

   For each comment in the output:
   - **Resolved by a follow-up commit** → confirm the commit is on the
     PR branch and the comment thread is marked resolved on GitHub.
     If GitHub's "Resolve conversation" button hasn't been clicked
     and you're the PR author, click it; otherwise ping the reviewer.
   - **Deferred** → reply on the comment with a one-line rationale and
     a tracking link (issue, follow-up PR, plan file section).
     "Deferred to v2.1 — see Plans/foo.md §3" is acceptable; silence
     is not.
   - **Disagreement** → reply on the comment with the counter-argument
     and tag the reviewer. Do not merge until they ack.

4. **Stack hygiene.**
   - If the PR is part of a stack, the base branch is the next-down
     PR's branch, not `main`. Otherwise the diff includes unrelated
     work.
   - If a downstream PR depends on this one, leave a one-line comment
     on this PR's body linking to it so the merge order is obvious.

5. **Merge.** `gh pr merge <N> --squash --auto` for the default flow.
   Use `--merge` instead of `--squash` only when preserving commit
   history materially helps (rare).

6. **Confirm the merge landed and the branch was deleted.**
   `gh pr view <N> --json state,mergedAt` and
   `git fetch --prune origin`.

## When to skip a step

Never skip step 3. It's the one that catches the bugs CI can't see.
If a comment seems trivial, the cost of resolving it is sub-minute;
the cost of merging past a real one and shipping the bug to `main`
is much higher.

## Why this exists

PR #58 on 2026-05-15 merged with an unresolved inline comment that
flagged a real bug in `Registry.remove()` (`_static_count` not
decremented). The bug landed on `main`. The follow-up cleanup is
tracked in `Plans/linear-swimming-pond.md` Phase 0a. This document
exists so the same lapse doesn't happen twice.
