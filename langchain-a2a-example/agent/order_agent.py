"""A (mocked) LangChain order & refund support agent.

This is a genuine LangChain tool-calling agent backed by Gemini on Vertex AI.
Its two tools return canned/deterministic data so the demo is reproducible — it
does not touch any real order system.

Exposed to the rest of the world over A2A (see ``agent_executor.py``), so a
coordinator agent built with any framework can hand off order/refund requests
to it.
"""

from __future__ import annotations

import os

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_google_vertexai import ChatVertexAI

MODEL = os.environ.get("MODEL", "gemini-flash-latest")
# Model-inference location, independent of the Agent Engine deployment region
# (GOOGLE_CLOUD_LOCATION). The `gemini-flash-latest` alias is served only on the
# `global` endpoint — regional endpoints 404 on it — so default the LLM call to
# `global` to match the coordinator.
MODEL_LOCATION = os.environ.get("MODEL_LOCATION", "global")

_STATUSES = [
    ("Em processamento", "ainda não expedido", "3-5 dias úteis"),
    ("Expedido", "em trânsito com a UPS (1Z-MOCK)", "2 dias úteis"),
    ("Em distribuição", "na carrinha de entrega", "hoje até às 20h"),
    ("Entregue", "deixado à porta", "já entregue"),
]


def _slot(order_id: str, n: int) -> int:
    return sum(ord(c) for c in order_id if c.isalnum()) % n


@tool
def get_order_status(order_id: str) -> str:
    """Consulta o estado atual de um pedido pelo seu id de pedido.

    Args:
        order_id: O identificador do pedido do cliente, ex. "123" ou "ORD-4471".
    """
    status, detail, eta = _STATUSES[_slot(order_id, len(_STATUSES))]
    return (
        f"Pedido {order_id}: estado={status}. {detail.capitalize()}. "
        f"Entrega estimada: {eta}."
    )


@tool
def initiate_refund(order_id: str, reason: str = "não especificado") -> str:
    """Inicia um reembolso para um pedido pelo seu id de pedido.

    Args:
        order_id: O identificador do pedido do cliente.
        reason: Motivo breve (opcional) para o reembolso.
    """
    ticket = f"RMA-{abs(hash(order_id)) % 100000:05d}"
    return (
        f"Reembolso iniciado para o pedido {order_id} (motivo: {reason}). "
        f"Autorização de devolução {ticket} criada; o reembolso do valor total do "
        f"pedido será creditado no método de pagamento original em 5-7 dias úteis."
    )


TOOLS = [get_order_status, initiate_refund]

SYSTEM_PROMPT = (
    "És o especialista em Apoio a Pedidos e Reembolsos de uma loja de comércio "
    "eletrónico. Ajuda os clientes com o estado de pedidos, rastreamento, "
    "estimativas de entrega, devoluções e reembolsos. Usa get_order_status para "
    "consultar um pedido e initiate_refund para iniciar um reembolso. Pede sempre "
    "o id do pedido se o cliente não o tiver fornecido. Sê conciso, cordial e "
    "específico. Responde apenas a temas de pedidos/reembolsos; se te perguntarem "
    "outra coisa, diz que está fora do teu âmbito. Responde sempre em português."
)

_agent = None


def _build_agent():
    llm = ChatVertexAI(
        model=MODEL,
        temperature=0,
        location=MODEL_LOCATION,
        project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    )
    # LangChain v1 tool-calling agent (LangGraph-based).
    return create_agent(model=llm, tools=TOOLS, system_prompt=SYSTEM_PROMPT)


async def run_order_agent(query: str) -> str:
    """Run the LangChain agent on a single user query and return its reply."""
    global _agent
    if _agent is None:
        _agent = _build_agent()
    result = await _agent.ainvoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content
