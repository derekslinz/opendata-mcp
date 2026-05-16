#!/usr/bin/env bash
# pr_check.sh — codify the merge gate from docs/PR_MERGE_CHECKLIST.md.
#
# Runs the seven checklist items in order against a PR number. Exits
# non-zero on the first failure with a precise reason. The intent is that
# this never replaces reading the comments — it makes it impossible to
# *forget* the steps.
#
# Usage:
#     scripts/pr_check.sh <PR_NUMBER>
#     make pr-check N=<PR_NUMBER>
#
# Requires: gh (authenticated), jq.

set -euo pipefail

PR="${1:-}"
if [[ -z "${PR}" ]]; then
    echo "usage: $0 <PR_NUMBER>" >&2
    exit 2
fi
if ! [[ "${PR}" =~ ^[0-9]+$ ]]; then
    printf 'PR_NUMBER must be a positive integer (got %q)\n' "${PR}" >&2
    exit 2
fi

for cmd in gh jq; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "missing required tool: $cmd" >&2
        exit 2
    fi
done

REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"

# Confirm the PR actually exists upfront. ``gh pr view`` is a leaky
# abstraction here: ``--json number`` echoes back whatever integer you
# pass without a server roundtrip, so a missing PR looks valid. Pick a
# field that forces the GraphQL fetch and surfaces the GraphQL error.
EXISTENCE_OUT="$(gh pr view "$PR" --json state 2>&1 || true)"
if [[ "$EXISTENCE_OUT" == *"Could not resolve to a PullRequest"* ]] \
    || [[ "$EXISTENCE_OUT" != *'"state"'* ]]; then
    echo "❌ PR #${PR} not found in ${REPO}" >&2
    exit 1
fi

echo "── PR merge gate for ${REPO} #${PR} ──"
echo

FAIL=0
fail() {
    echo "❌ $*" >&2
    FAIL=1
}
pass() {
    echo "✅ $*"
}

# Every command that talks to GitHub gets ``|| true`` on its capture so
# a transient gh failure inside a step doesn't abort the whole gate —
# we want each step to report individually.

# Step 1: CI is green.
echo "[1/7] CI checks"
CHECK_STATES="$(gh pr checks "$PR" --json bucket --jq '.[].bucket' 2>/dev/null | sort -u || true)"
if [[ -z "$CHECK_STATES" ]]; then
    fail "PR has no CI checks (or check-fetch failed)"
else
    # Buckets: pass, fail, pending, skipping, cancel.
    BAD="$(echo "$CHECK_STATES" | grep -vE '^(pass|skipping)$' || true)"
    if [[ -z "$BAD" ]]; then
        pass "all required checks pass/skipped"
    else
        fail "non-pass check buckets present: $(echo "$BAD" | tr '\n' ' ')"
        echo "    → gh pr checks $PR" >&2
    fi
fi
echo

# Step 2: Review state.
echo "[2/7] Review state"
DECISION="$(gh pr view "$PR" --json reviewDecision --jq .reviewDecision 2>/dev/null || true)"
case "$DECISION" in
"" | "null" | "APPROVED")
    pass "reviewDecision: ${DECISION:-<none>} (no required reviewers or approved)"
    ;;
"CHANGES_REQUESTED")
    fail "reviewDecision: CHANGES_REQUESTED — resolve and re-request review"
    ;;
"REVIEW_REQUIRED")
    fail "reviewDecision: REVIEW_REQUIRED — waiting on a reviewer"
    ;;
*)
    fail "reviewDecision: $DECISION — investigate"
    ;;
esac
echo

# Step 3: Every inline review comment is resolved. This is the gate the
# user explicitly called out: "always enumerate gh api .../comments
# before merge". Non-zero if any comments exist; the operator must
# eyeball them and decide. We don't try to detect "resolved" — GitHub
# stores that on the *thread*, not the comment, and the API for fetching
# thread state is GraphQL-only.
echo "[3/7] Inline review comments"
COMMENTS_JSON="$(gh api "repos/${REPO}/pulls/${PR}/comments" --paginate 2>/dev/null || echo "[]")"
COUNT="$(echo "$COMMENTS_JSON" | jq 'length')"
if [[ "$COUNT" -eq 0 ]]; then
    pass "no inline comments"
else
    fail "${COUNT} inline comment(s) — review and resolve before merging"
    echo "$COMMENTS_JSON" | jq -r '
        .[] | "    • \(.path):\(.line // .original_line // "?") @\(.user.login)\n      \(.body | gsub("\n"; "\n      ") | .[0:240])"
    ' >&2
fi
echo

# Step 4: Stack hygiene — base branch is main (we don't run stacks
# automatically here; if you're stacking, audit by hand).
echo "[4/7] Stack hygiene"
BASE="$(gh pr view "$PR" --json baseRefName --jq .baseRefName 2>/dev/null || true)"
if [[ "$BASE" == "main" ]]; then
    pass "base: main"
else
    # Not necessarily wrong — could be a stack — but worth flagging.
    echo "⚠️  base: $BASE (non-main; confirm this is intentional)"
fi
echo

# Step 5–6: Merge state + merged confirmation are post-merge; here we
# only require the PR to be mergeable.
echo "[5/7] Mergeability"
STATE="$(gh pr view "$PR" --json mergeable --jq .mergeable 2>/dev/null || true)"
case "$STATE" in
"MERGEABLE")
    pass "mergeable: clean"
    ;;
"CONFLICTING")
    fail "mergeable: CONFLICTING — rebase on main and resolve"
    ;;
"UNKNOWN")
    echo "⚠️  mergeable: UNKNOWN (GitHub still computing; rerun in a moment)"
    ;;
*)
    fail "mergeable: $STATE"
    ;;
esac
echo

# Step 6: Skip the post-merge "did it land" check — that's a *post*-merge
# verification that pr_check.sh runs *before* merging. Leave it as a
# numbered no-op so the gate's step numbering matches the checklist.
echo "[6/7] (post-merge confirmation runs after \`gh pr merge\` — see PR_MERGE_CHECKLIST.md step 6)"
echo

# Step 7: Same — post-merge CI on the merge commit. Numbered for parity.
echo "[7/7] (post-merge CI on the merge commit — verify with \`gh run list --branch main --limit 1\` after merge)"
echo

if [[ "$FAIL" -ne 0 ]]; then
    echo "── ❌ NOT READY TO MERGE — resolve the failures above first. ──" >&2
    exit 1
fi
echo "── ✅ Pre-merge gate passed. Run \`gh pr merge ${PR} --squash --delete-branch\` to merge. ──"
echo "── Remember: re-run steps 6 + 7 after merging. ──"
