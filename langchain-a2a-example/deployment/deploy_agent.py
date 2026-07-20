"""Deploy the order-support A2A agent to Agent Engine.

Run from the project root (langchain-a2a-example/) so the source tarball contains
the ``agent/`` package and ``requirements.txt`` at its root; the entrypoint is
``agent.agent_app:adk_app``:

    cd langchain-a2a-example
    GOOGLE_CLOUD_PROJECT=your-project-id \
      uv run --with "google-cloud-aiplatform[agent_engines]" \
      python deployment/deploy_agent.py

Prints the reasoning engine resource name on success.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import vertexai
from vertexai._genai.types import AgentEngineConfig

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "your-project-id")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
STAGING_BUCKET = os.environ.get("STAGING_BUCKET", "gs://your-project-id-ae-staging")
DISPLAY_NAME = "order-support-agent"

_class_methods = json.loads(
    (Path(__file__).parent / "a2a_class_methods.json").read_text()
)


def main() -> None:
    client = vertexai.Client(project=PROJECT, location=LOCATION)

    config = {
        "display_name": DISPLAY_NAME,
        "description": "Order & refund support (LangChain) exposed over A2A.",
        "staging_bucket": STAGING_BUCKET,
        # The agent/ package + requirements.txt (not ".") so the tarball excludes
        # .venv / caches. requirements.txt MUST be included or the build skips
        # dependency install.
        "source_packages": [
            "agent",
            "requirements.txt",
        ],
        "entrypoint_module": "agent.agent_app",
        "entrypoint_object": "adk_app",
        "class_methods": _class_methods,
        "requirements_file": "requirements.txt",
        "env_vars": {"MODEL": "gemini-flash-latest", "MODEL_LOCATION": "global"},
        "min_instances": 0,
        "max_instances": 1,
        "resource_limits": {"cpu": "1", "memory": "4Gi"},
        "container_concurrency": 9,
        "python_version": "3.12",
        "agent_framework": "a2a",
    }

    # SDK bug: agent_framework "a2a" fails the Pydantic Literal; set it after.
    actual_framework = config.pop("agent_framework", None)
    config_obj = AgentEngineConfig.model_validate(config)
    config_obj.agent_framework = actual_framework

    existing = [
        a
        for a in client.agent_engines.list()
        if a.api_resource.display_name == DISPLAY_NAME
    ]
    if existing:
        print(f"Updating existing engine: {existing[0].api_resource.name}")
        remote = client.agent_engines.update(
            name=existing[0].api_resource.name, config=config_obj
        )
    else:
        print("Creating new Agent Engine deployment...")
        remote = client.agent_engines.create(config=config_obj)

    print("RESOURCE_NAME:", remote.api_resource.name)


if __name__ == "__main__":
    main()
