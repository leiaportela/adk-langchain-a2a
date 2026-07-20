# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Sub-agents for the triage coordinator.

- ``order_support_agent``: the remote order-support specialist reached over A2A.

The catalog of specialists lives directly in the coordinator's instruction
(agent.agent), so no retrieval tool is needed.
"""

from __future__ import annotations

import os

import httpx
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# Agent-card URL of the order-support A2A provider (set via .env).
ORDER_SUPPORT_A2A_CARD = os.getenv(
    "ORDER_SUPPORT_A2A_CARD",
    "http://localhost:8001/.well-known/agent-card.json",
)


def _build_a2a_httpx_client() -> httpx.AsyncClient:
    """httpx client for the A2A call.

    Agent Engine (Vertex AI) A2A endpoints require an OAuth access token; a plain
    local server does not. We attach the token only for aiplatform endpoints.
    """
    if "aiplatform.googleapis.com" in ORDER_SUPPORT_A2A_CARD:
        import asyncio

        import google.auth
        import google.auth.transport.requests

        async def _add_access_token(request: httpx.Request) -> None:
            loop = asyncio.get_running_loop()
            creds, _ = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            await loop.run_in_executor(None, creds.refresh, auth_req)
            request.headers["Authorization"] = f"Bearer {creds.token}"

        return httpx.AsyncClient(
            event_hooks={"request": [_add_access_token]},
            timeout=httpx.Timeout(120.0),
        )
    return httpx.AsyncClient(timeout=httpx.Timeout(120.0))


async def _refresh_a2a_client(callback_context) -> None:
    """Rebuild the authed httpx client on the current event loop before each call.

    A reused client is bound to the loop that first used it; on a cold start that
    loop can already be closed ("Event loop is closed"). Recreating it here keeps
    it on the live request loop.
    """
    order_support_agent._httpx_client = _build_a2a_httpx_client()
    order_support_agent._httpx_client_needs_cleanup = True
    return None


order_support_agent = RemoteA2aAgent(
    name="order_support_agent",
    description=(
        "Especialista em apoio a pedidos e reembolsos (agente LangChain, acedido "
        "via A2A). Trata do estado de pedidos, rastreamento, estimativas de "
        "entrega, devoluções e reembolsos. Corresponde ao id de catálogo "
        "'order-support-agent'."
    ),
    agent_card=ORDER_SUPPORT_A2A_CARD,
    before_agent_callback=_refresh_a2a_client,
)
