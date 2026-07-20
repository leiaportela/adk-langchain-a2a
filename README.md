# ADK Triage Coordinator + LangChain A2A Specialist

A two-agent demo on Google Cloud (Agent Engine):

- **`triage-agent/`** — an ADK coordinator/router. It does a short triage and, for
  order/refund requests, hands off over **A2A** to the specialist below.
- **`langchain-a2a-example/`** — a **LangChain** order-support specialist exposed over
  the **A2A** protocol and deployed to Agent Engine. The coordinator consumes it via a
  `RemoteA2aAgent`.

---

## How this was built

### 1. Scaffold the triage agent

```bash
agents-cli scaffold create triage-agent \
    --agent adk \
    --prototype \
    --region us-central1 \
    --agent-directory agent \
    --output-dir agents
```

This creates a prototype ReAct agent. It was then turned into the **coordinator**:
`agent/tools.py` defines a `RemoteA2aAgent` pointing at the specialist's A2A card, and
`agent/agent.py` uses a routing instruction with `sub_agents=[order_support_agent]`.

### 2. Add the LangChain A2A specialist

`langchain-a2a-example/` was **hand-built** (not scaffolded — it is not an ADK agent). It's
a LangChain order/refund agent wrapped in an a2a-sdk `AgentExecutor`, deployed to Agent
Engine via `deployment/deploy_agent.py`.

---

## Prerequisites

### Install the tools

**`uv`** — runs `agents-cli` and manages each project's dependencies:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Restart your shell (or `source ~/.bashrc` / `~/.zshrc`), then verify with `uv --version`.

**`gcloud`** (Google Cloud CLI) — needed for auth and deployment. Follow the installer at
https://cloud.google.com/sdk/docs/install, then verify with `gcloud --version`.

**`agents-cli`** — installed as a `uv` tool:
```bash
uv tool install google-agents-cli
```
Verify with `agents-cli info`.

### Authenticate GCP (billing-enabled project)

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project <YOUR_PROJECT>
gcloud auth application-default set-quota-project <YOUR_PROJECT>
gcloud services enable aiplatform.googleapis.com storage.googleapis.com
```

---

## Deploy

Order matters: **deploy the specialist first**, then point the coordinator at its A2A card.
Each deploy takes ~10–15 min. Substitute your own values for the `<...>` placeholders below —
your project (`<YOUR_PROJECT>` / `<PROJECT_NUMBER>`) and the engine IDs each deploy prints.

### Step 1 — Deploy the LangChain A2A specialist

```bash
cd langchain-a2a-example
cp .env.example .env          # set GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION
./deployment/deploy_order_agent.sh
```

The script creates the staging bucket if needed, deploys to Agent Engine, saves the engine
id to `.deploy_state`, and **prints the A2A card URL**.

Smoke-test it (the `BASE` below is the printed card URL **without** the `/v1/card` suffix):

```bash
BASE="https://us-central1-aiplatform.googleapis.com/v1beta1/projects/<PROJECT_NUMBER>/locations/us-central1/reasoningEngines/<SPECIALIST_ENGINE_ID>/a2a"
curl -s -X POST "$BASE/v1/message:send" \
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    -H "Content-Type: application/json" \
    -d '{"request":{"message_id":"smoke-001","role":"ROLE_USER","content":[{"text":"Qual é o estado do meu pedido ORD-4471?"}]}}' \
    | python3 -m json.tool
```

Expected: a Portuguese order-status reply under `.message.content[0].text`.

### Step 2 — Point the coordinator at the specialist

Copy the printed **A2A card URL** into the coordinator's env file
`triage-agent/agent/.env` (create it from the template first if needed):

```bash
cd ../triage-agent
cp agent/.env.example agent/.env    # if not already present
# then set, in agent/.env:
#   ORDER_SUPPORT_A2A_CARD=https://us-central1-aiplatform.googleapis.com/v1beta1/projects/<PROJECT_NUMBER>/locations/us-central1/reasoningEngines/<SPECIALIST_ENGINE_ID>/a2a/v1/card
```

`agent/.env` lives inside `agent/` on purpose: `adk deploy` bundles it and `load_dotenv()`
reads `ORDER_SUPPORT_A2A_CARD` at runtime (locally in the playground too).

### Step 3 — Deploy the triage coordinator

```bash
# from triage-agent/
agents-cli install                      # sync the venv (so `uv run adk` works)

uv run adk deploy agent_engine \
    --project <YOUR_PROJECT> \
    --region us-central1 \
    --display_name triage-agent \
    agent
```

This prints the coordinator's engine resource name.

> **Redeploying?** The command above **creates a new engine** every run. To update the
> existing coordinator instead, add `--agent_engine_id <COORDINATOR_ENGINE_ID>` to the
> `adk deploy` command (use the id from your first deploy).

Test the full chain (use the engine id it printed):

```bash
ENGINE="projects/<PROJECT_NUMBER>/locations/us-central1/reasoningEngines/<COORDINATOR_ENGINE_ID>"
REGION=us-central1
TOKEN=$(gcloud auth print-access-token)

curl -s -X POST "https://${REGION}-aiplatform.googleapis.com/v1beta1/${ENGINE}:streamQuery" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"class_method":"stream_query","input":{"message":"Olá, preciso de um reembolso do pedido 123","user_id":"u1"}}'
```

Expected: the coordinator triages the request, transfers to `order_support_agent`, and the
specialist replies (in Portuguese) confirming the refund was initiated.
