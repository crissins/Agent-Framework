#!/usr/bin/env python3
"""
HTTP Server entry point for AI Toolkit Agent Inspector integration.

Wraps the book-planning agent as an HTTP server using azure.ai.agentserver.agentframework.
Supports both HTTP server mode (default, for Agent Inspector) and CLI mode.

Usage:
    # HTTP server mode (default) — works with Agent Inspector
    python server.py

    # CLI mode — interactive terminal chat
    python server.py --cli

    # With agentdev instrumentation (recommended for debugging)
    agentdev run server.py --verbose --port 8087
"""
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv(override=True)

# Configure OpenTelemetry tracing for AI Toolkit integration
# Suppress noisy OTLP exporter errors when no local collector is running
import logging as _logging

for _otlp_logger_name in (
    "opentelemetry.exporter.otlp.proto.grpc.exporter",
    "opentelemetry.exporter.otlp.proto.grpc",
    "opentelemetry.exporter.otlp",
):
    _logging.getLogger(_otlp_logger_name).setLevel(_logging.CRITICAL)

try:
    from agent_framework.observability import configure_otel_providers

    # enable_sensitive_data captures prompts/completions – ON in dev, OFF in prod
    _enable_sensitive = os.getenv("ENABLE_SENSITIVE_DATA", "false").lower() in ("1", "true", "yes")
    configure_otel_providers(
        vs_code_extension_port=4317,  # AI Toolkit gRPC port
        enable_sensitive_data=_enable_sensitive,
    )
except Exception:
    print(
        "Warning: agent_framework observability setup failed. Tracing disabled.",
        file=sys.stderr,
    )

from agent_framework.openai import OpenAIChatClient
from config import get_model_config


async def create_book_agent(use_qwen: bool = False, model_id: str | None = None):
    """
    Create a book-planning agent for the HTTP server.

    This agent helps users plan LATAM educational books through conversation.
    It can design curriculum structures, suggest chapter topics, and outline
    content for age-appropriate educational materials.
    """
    config = get_model_config(use_qwen)
    resolved_model_id = model_id if model_id else config.get("model_id")

    client = OpenAIChatClient(
        api_key=os.getenv(config["api_key_env"], ""),
        base_url=config["base_url"],
        model_id=resolved_model_id,
    )

    agent = client.create_agent(
        name="BookPlannerAgent",
        instructions=(
            "You are an expert LATAM educational book planner and curriculum designer.\n\n"
            "Your role is to help users create engaging, age-appropriate educational books "
            "for children across Latin America. You can:\n\n"
            "1. **Plan a book**: Ask about the topic, target age, country, and learning method, "
            "then design a complete curriculum with chapter outlines.\n"
            "2. **Write chapters**: Given a chapter outline, produce rich educational content "
            "with activities, reflection questions, and cultural references.\n"
            "3. **Suggest improvements**: Review and enhance existing book plans.\n\n"
            "IMPORTANT GUIDELINES:\n"
            "- Respond in the language the user specifies (default: Spanish for LATAM)\n"
            "- Ensure cultural relevance for the target country\n"
            "- Follow age-appropriate pedagogy\n"
            "- Support learning methods: Scandinavian, Montessori, Project-Based, etc.\n"
            "- Include interactive elements: activities, questions, experiments\n"
            "- Be warm, encouraging, and professional\n"
        ),
    )
    return agent


async def run_server(agent):
    """Run the agent as an HTTP server for Agent Inspector."""
    from azure.ai.agentserver.agentframework import from_agent_framework

    print("🚀 Starting Book Planner Agent HTTP Server...")
    print("   Use AI Toolkit Agent Inspector to interact with the agent.")
    await from_agent_framework(agent).run_async()


async def run_cli(agent):
    """Run the agent in interactive CLI mode."""
    print("=" * 60)
    print("📚 LATAM Book Planner Agent — CLI Mode")
    print("=" * 60)
    print("Type your message and press Enter. Type 'quit' to exit.\n")

    thread = agent.get_new_thread()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 Goodbye!")
            break

        print("Agent: ", end="", flush=True)
        async for chunk in agent.run_stream(user_input, thread=thread):
            if chunk.text:
                print(chunk.text, end="", flush=True)
        print("\n")


async def main():
    # Determine Qwen mode from env or flag
    use_qwen = os.getenv("USE_QWEN", "").lower() in ("1", "true", "yes")
    model_id = os.getenv("MODEL_ID", None)

    agent = await create_book_agent(use_qwen=use_qwen, model_id=model_id)

    if "--cli" in sys.argv:
        await run_cli(agent)
    else:
        # Default: HTTP server mode (for Agent Inspector / agentdev)
        await run_server(agent)


if __name__ == "__main__":
    asyncio.run(main())
