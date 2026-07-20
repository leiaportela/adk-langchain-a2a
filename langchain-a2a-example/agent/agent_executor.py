"""A2A wiring for the LangChain order-support agent.

Wraps ``run_order_agent`` in a standard a2a-sdk ``AgentExecutor`` and declares
the agent's public identity (name, description, skills). The Agent Engine
deployment (``agent_app.py``) reuses these definitions.
"""

from __future__ import annotations

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentSkill
from a2a.utils import new_agent_text_message

from .order_agent import run_order_agent

# Must match the `order-support-agent` entry in the catalog PDF so the
# coordinator's catalog-grounded routing resolves to this agent.
AGENT_NAME = "order-support-agent"
AGENT_DESCRIPTION = (
    "Apoio a pedidos e reembolsos: estado e rastreamento de pedidos, estimativas "
    "de entrega, devoluções, cancelamentos e processamento de reembolsos."
)

SKILLS = [
    AgentSkill(
        id="order_status",
        name="Estado e rastreamento de pedidos",
        description="Consulta o estado, a transportadora e a estimativa de entrega de um pedido.",
        tags=["pedidos", "rastreamento", "envio"],
        examples=["Onde está o meu pedido 123?", "O pedido ORD-4471 já foi expedido?"],
    ),
    AgentSkill(
        id="refunds",
        name="Reembolsos e devoluções",
        description="Inicia um reembolso ou uma devolução de um pedido.",
        tags=["reembolso", "devolução", "dinheiro-de-volta"],
        examples=["Quero um reembolso do pedido 123", "Como devolvo o pedido 88?"],
    ),
]


class OrderSupportAgentExecutor(AgentExecutor):
    """Runs the LangChain order-support agent for each incoming A2A message."""

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        query = context.get_user_input()
        try:
            reply = await run_order_agent(query)
        except Exception as exc:  # surface errors as an agent message, not a 500
            reply = f"Order-support agent error: {type(exc).__name__}: {exc}"
        await event_queue.enqueue_event(new_agent_text_message(reply))

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception("cancel not supported")
