import os
import logging
from typing import Optional

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

from config import get_model_config
from models.book_spec import BookRequest, Curriculum
from utils.retry import async_retry

logger = logging.getLogger(__name__)


async def create_voice_curriculum_agent(
    use_qwen: bool = False,
    model_id: str | None = None,
) -> ChatAgent:
    """Create a curriculum agent optimized for audiobook-first output."""
    config = get_model_config(use_qwen)
    resolved_model_id = model_id if model_id else config.get("model_id")

    client = OpenAIChatClient(
        api_key=os.getenv(config["api_key_env"], ""),
        base_url=config["base_url"],
        model_id=resolved_model_id,
    )

    return ChatAgent(
        chat_client=client,
        name="VoiceCurriculumAgent",
        instructions=(
            "You design curricula for AUDIO-FIRST educational books for children in LATAM.\n"
            "Create a coherent curriculum where chapters flow naturally when narrated.\n"
            "Return a JSON object matching the Curriculum schema with fields: title, description, chapters[].title, chapters[].summary.\n"
            "Use age-appropriate language and culturally relevant examples for the target country.\n"
            "Ensure chapter progression is logical and easy to follow by listening.\n"
            "Write all fields in the user's requested language.\n\n"
            "AUDIOBOOK-SPECIFIC GUIDELINES:\n"
            "- Each chapter title should be short and memorable (max 8 words) for spoken intros.\n"
            "- Chapter summaries should describe what the LISTENER will learn, not just content.\n"
            "- Build a narrative arc: early chapters introduce concepts, later ones deepen.\n"
            "- Include natural hooks between chapters (each summary should hint at what's next).\n"
            "- Aim for 3-6 chapters depending on topic scope — fewer chapters with richer content\n"
            "  is better for audio than many shallow ones.\n"
            "- The book description should read like a spoken introduction: warm, inviting, conversational.\n"
            "Always respond with valid JSON."
        ),
    )


@async_retry(max_retries=3, base_delay=2.0, max_delay=60.0)
async def _run_agent_with_retry(agent: ChatAgent, prompt: str, options: dict):
    return await agent.run(prompt, **options)


async def generate_voice_curriculum(
    agent: ChatAgent,
    request: BookRequest,
) -> Optional[Curriculum]:
    """Generate an audiobook-oriented curriculum."""
    prompt = (
        f"=== AUDIOBOOK CURRICULUM REQUEST ===\n\n"
        f"Topic: {request.topic}\n"
        f"Target age: {request.target_audience_age}\n"
        f"Country: {request.country}\n"
        f"Language: {request.language}\n"
        f"Method: {request.learning_method}\n"
        f"Chapters: {request.num_chapters}\n\n"
        f"Design a spoken-friendly curriculum.\n"
        f"Each chapter summary should indicate what the listener will understand by the end.\n"
        f"Use concise chapter titles suitable for narration intros."
    )

    try:
        response = await _run_agent_with_retry(
            agent,
            prompt,
            options={"response_format": Curriculum, "max_tokens": 2000},
        )
        return response.value
    except Exception as e:
        logger.error(f"❌ Error generating voice curriculum: {e}")
        return None
