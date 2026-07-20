#!/usr/bin/env bash
# Deploy the order-support LangChain agent to Agent Engine (A2A).
#
# Ensures the staging bucket exists, runs deploy_agent.py (which packages the
# agent/ dir), and records the resulting reasoning engine id in .deploy_state.
#
# Env:
#   GOOGLE_CLOUD_PROJECT   target project (required)
#   GOOGLE_CLOUD_LOCATION  region (default us-central1)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$AGENT_DIR"

# Load project/region from .env — the .env is the single source of truth, so its
# values override anything already exported in the shell.
if [ -f "$AGENT_DIR/.env" ]; then
    while IFS='=' read -r key val; do
        case "$key" in ''|'#'*) continue ;; esac
        export "$key=$val"
    done < "$AGENT_DIR/.env"
fi

PROJECT="${GOOGLE_CLOUD_PROJECT:?GOOGLE_CLOUD_PROJECT must be set}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
STAGING_BUCKET="gs://${PROJECT}-ae-staging"

echo "==> [order-agent] project=$PROJECT region=$REGION staging=$STAGING_BUCKET"

if ! gcloud storage ls "$STAGING_BUCKET" >/dev/null 2>&1; then
    echo "==> Creating staging bucket $STAGING_BUCKET ..."
    gcloud storage buckets create "$STAGING_BUCKET" --project "$PROJECT" --location "$REGION"
fi

echo "==> Deploying to Agent Engine (this can take ~10-15 min)..."
OUT="$(GOOGLE_CLOUD_PROJECT="$PROJECT" GOOGLE_CLOUD_LOCATION="$REGION" \
    STAGING_BUCKET="$STAGING_BUCKET" \
    uv run --with "google-cloud-aiplatform[agent_engines]" \
    python deployment/deploy_agent.py 2>&1 | tee /dev/stderr)"

RESOURCE="$(printf '%s\n' "$OUT" | sed -n 's/^RESOURCE_NAME: //p' | tail -1)"
if [ -z "$RESOURCE" ]; then
    echo "ERROR: could not parse RESOURCE_NAME from deploy output." >&2
    exit 1
fi
ENGINE_ID="${RESOURCE##*/}"
echo "$ENGINE_ID" > "$AGENT_DIR/.deploy_state"
echo "==> [order-agent] done. engine_id=$ENGINE_ID (saved to .deploy_state)"

# Build and print the A2A card URL. Set ORDER_SUPPORT_A2A_CARD in the
# coordinator's .env (agents/triage-agent/.env) to this value manually. Uses the
# project *number* and the Agent Engine card path (/a2a/v1/card, not
# /.well-known/agent-card.json).
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)' 2>/dev/null || true)"
if [ -z "$PROJECT_NUMBER" ]; then
    echo "WARN: could not resolve project number for $PROJECT; cannot build card URL." >&2
else
    CARD="https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_NUMBER}/locations/${REGION}/reasoningEngines/${ENGINE_ID}/a2a/v1/card"
    echo ""
    echo "==> A2A card URL (set ORDER_SUPPORT_A2A_CARD in agents/triage-agent/.env to this):"
    echo "    $CARD"
fi
