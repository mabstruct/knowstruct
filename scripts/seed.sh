#!/usr/bin/env bash
# One-time seed of the first KNOWSTRUCT content. Refuses to run twice.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
DEV="uv run --project $HERE dev"
T="$HERE/docs/tickets"

if $KS list KS --label requirement | grep -q "The knowledge system"; then
  echo "already seeded"
  exit 0
fi

REQ=$($KS create KS --label requirement --title "The knowledge system" \
  --body-file "$T/ks-requirement-knowledge-system.md" --state Review --priority high)
echo "$REQ"

$KS create CLAWSTRUCT --label analysis --title "Analysis: CLAWSTRUCT" \
  --body-file "$T/analysis-clawstruct.md" --state Todo --relates "$REQ"
$KS create CONSTRUCT --label analysis --title "Analysis: CONSTRUCT" \
  --body-file "$T/analysis-construct.md" --state Todo --parent CONSTRUCT-1 --relates "$REQ"
$KS create ZENSTRUCT --label analysis --title "Analysis: ZENSTRUCT" \
  --body-file "$T/analysis-zenstruct.md" --state Todo --relates "$REQ"
$KS create KS --label analysis --title "Analysis: what got lost at each widening of the target" \
  --body-file "$T/analysis-what-got-lost.md" --state Todo --relates "$REQ"

PROP="${TMPDIR:-/tmp}/seed-proposal-zen-ask-v2.md"
sed "s/KS-<n>/$REQ/" "$T/proposal-zen-ask-v2.md" > "$PROP"
$KS create ZENSTRUCT --label proposal --title "zen-ask v2" \
  --body-file "$PROP" --state Backlog --relates "$REQ"
rm -f "$PROP"

$KS create KS --label task --title "Revoke the old personal token" \
  --body-file "$T/task-revoke-old-token.md" --state Backlog --priority high
$KS create KS --label task --title "Decide on SMTP for Plane invites and notifications" \
  --body-file "$T/task-smtp-decision.md" --state Backlog --priority low
$KS create KS --label task --title "Delete the merged book-ingest branch in zen" \
  --body-file "$T/task-delete-book-ingest-branch.md" --state Backlog --priority low
$KS create KS --label task --title "Delete the zen/.env copy of the agent token" \
  --body-file "$T/task-delete-zen-env-copy.md" --state Backlog --priority low
