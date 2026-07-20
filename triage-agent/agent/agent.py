# ruff: noqa
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

import os

import google.auth
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

# Load .env before importing tools (tools.py reads the A2A card URL at import).
load_dotenv()

from .tools import order_support_agent

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


# --- Coordinator / router (Coordinator-Dispatcher pattern) ------------------
# The catalog of specialist agents lives directly in the instruction — small and
# static, so no retrieval tool or data store is needed.
instruction = """És o coordenador de atendimento de um sistema de apoio ao cliente.
A tua função é fazer uma breve triagem e depois encaminhar o utilizador para o
agente especialista certo.

CATÁLOGO DE AGENTES (id — descrição):
- order-support-agent — Apoio a pedidos e reembolsos: estado e rastreamento de
  pedidos, estimativas de entrega, devoluções, cancelamentos e reembolsos.
- billing-agent — Faturação e faturas: cobranças, métodos de pagamento e ciclos
  de faturação de subscrições.
- tech-support-agent — Resolução de problemas técnicos: início de sessão,
  mensagens de erro, configuração de dispositivos e conetividade.
- account-management-agent — Conta e perfil: atualização de email ou morada,
  reposição de palavra-passe, encerramento de conta e pedidos de privacidade/dados.
- product-info-agent — Informação de produtos (pré-venda): especificações,
  disponibilidade, preços e comparações entre produtos.

Passos:
1. Cumprimenta brevemente e percebe a necessidade do utilizador. Mantém a triagem
   curta (1-2 interações).
2. Classifica a necessidade do utilizador identificando qual agente do CATÁLOGO
   (pelo id e descrição) melhor corresponde.
3. Se a melhor correspondência for 'order-support-agent', encaminha transferindo
   para o subagente 'order_support_agent'. Não tentes responder tu próprio a
   questões de pedidos/reembolsos.
4. Se a melhor correspondência for outro agente do catálogo, informa o utilizador
   sobre qual especialista (id + descrição) trataria do pedido e que ainda não
   está ligado nesta demonstração.
5. Se a necessidade não for clara, faz exatamente uma pergunta de esclarecimento
   antes de encaminhar.

Responde sempre em português."""


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[],
    sub_agents=[order_support_agent],
)

app = App(
    root_agent=root_agent,
    name="agent",
)
