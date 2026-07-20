"""Agent Engine entrypoint: expose the LangChain order-support agent over A2A.

Wraps the ``OrderSupportAgentExecutor`` in the Agent Engine ``A2aAgent``
template. On deploy, Agent Engine serves the A2A protocol endpoints
(``/a2a/v1/...``) and overrides the agent card URL to the reasoning engine's A2A
address automatically.
"""

from __future__ import annotations

from vertexai.preview.reasoning_engines.templates.a2a import (
    A2aAgent,
    create_agent_card,
)

from .agent_executor import (
    AGENT_DESCRIPTION,
    AGENT_NAME,
    SKILLS,
    OrderSupportAgentExecutor,
)

agent_card = create_agent_card(
    agent_name=AGENT_NAME,
    description=AGENT_DESCRIPTION,
    skills=SKILLS,
)

# agent_executor_builder is called with no args -> OrderSupportAgentExecutor().
adk_app = A2aAgent(
    agent_card=agent_card,
    agent_executor_builder=OrderSupportAgentExecutor,
)
