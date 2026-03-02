import os
import logging
from typing import Optional, Dict, Any

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

from config import get_model_config
from models.book_spec import ChapterOutline, ChapterContent, Curriculum
from utils.retry import async_retry

logger = logging.getLogger(__name__)


async def create_voice_chapter_agent(
    use_qwen: bool = False,
    model_id: str | None = None,
) -> ChatAgent:
    """Create a chapter agent optimized for audiobook pipelines."""
    config = get_model_config(use_qwen)
    resolved_model_id = model_id if model_id else config.get("model_id")

    client = OpenAIChatClient(
        api_key=os.getenv(config["api_key_env"], ""),
        base_url=config["base_url"],
        model_id=resolved_model_id,
    )

    return ChatAgent(
        chat_client=client,
        name="VoiceChapterAgent",
        instructions=(
            "You write educational chapter content that will be converted into AUDIO narration.\n"
            "Return a JSON object matching the ChapterContent schema.\n"
            "Prioritize clear spoken flow, short paragraphs, and natural transitions.\n"
            "Still include educational structure sections (concept, example, activity, reflection).\n"
            "Avoid dense tables, code blocks, or overly visual dependencies.\n"
            "Write entirely in the requested language and keep it age-appropriate.\n\n"
            "IMPORTANT AUDIO-FIRST RULES:\n"
            "- Write as if you're speaking directly to the listener (a child).\n"
            "- Use conversational tone: 'Imagina que...', '¿Sabías que...?', 'Ahora vamos a...'\n"
            "- Keep sentences short (max 25 words) so TTS flows naturally.\n"
            "- Avoid abbreviations, special characters, or symbols that TTS can't pronounce.\n"
            "- Spell out numbers under 100 as words (e.g. 'veinticinco' instead of '25').\n"
            "- Replace bullet lists with flowing prose and natural transitions.\n"
            "- Each paragraph should be 2-4 sentences max for good TTS chunking.\n"
            "- Add natural pauses between sections using a blank line.\n"
            "- End the chapter with a brief recap and a warm transition to the next topic.\n"
            "- When the chapter is part of a larger book, reference earlier concepts naturally\n"
            "  (e.g. 'Como vimos en el capítulo anterior...').\n"
            "Always respond with valid JSON."
        ),
    )


@async_retry(max_retries=3, base_delay=2.0, max_delay=60.0)
async def _run_agent_with_retry(agent: ChatAgent, prompt: str, options: dict):
    return await agent.run(prompt, **options)


async def generate_voice_chapter(
    agent: ChatAgent,
    outline: ChapterOutline,
    context: Dict[str, Any],
    *,
    curriculum: Curriculum | None = None,
    chapter_index: int = 0,
    previous_summaries: list[str] | None = None,
) -> Optional[ChapterContent]:
    """Generate a chapter suitable for audiobook script conversion.

    Args:
        agent: The voice chapter ChatAgent.
        outline: Chapter outline with title and summary.
        context: Book context (age, country, language, etc.).
        curriculum: Full book curriculum for narrative coherence.
        chapter_index: 0-based index of this chapter in the book.
        previous_summaries: Short summaries of previously generated chapters
            so the agent can reference earlier content naturally.
    """
    # Build full-book context header
    book_context_block = ""
    if curriculum:
        total_chapters = len(curriculum.chapters)
        toc_lines = "\n".join(
            f"  {i+1}. {ch.title}" for i, ch in enumerate(curriculum.chapters)
        )
        book_context_block = (
            f"=== BOOK OVERVIEW ===\n"
            f"Book title: {curriculum.title}\n"
            f"Book description: {curriculum.description}\n"
            f"Total chapters: {total_chapters}\n"
            f"Table of contents:\n{toc_lines}\n"
            f"You are writing chapter {chapter_index + 1} of {total_chapters}.\n\n"
        )

    # Previous chapters context
    prev_block = ""
    if previous_summaries:
        prev_lines = "\n".join(
            f"  Ch {i+1}: {s}" for i, s in enumerate(previous_summaries)
        )
        prev_block = (
            f"=== PREVIOUS CHAPTERS (for continuity) ===\n"
            f"{prev_lines}\n"
            f"Reference earlier ideas naturally when relevant.\n\n"
        )

    prompt = (
        f"{book_context_block}"
        f"{prev_block}"
        f"=== AUDIOBOOK CHAPTER REQUEST ===\n\n"
        f"Chapter number: {chapter_index + 1}\n"
        f"Chapter title: {outline.title}\n"
        f"Chapter summary: {outline.summary}\n"
        f"Age: {context['age']}\n"
        f"Country: {context['country']}\n"
        f"Language: {context['language']}\n"
        f"Method: {context['learning_method']}\n"
        f"Pages target: {context['pages_per_chapter']}\n\n"
        f"Write a full educational chapter in markdown suitable for later TTS conversion.\n"
        f"Use listener-friendly transitions and avoid heavy formatting.\n"
        f"Remember: this will be READ ALOUD to a child, so write naturally and conversationally."
    )

    try:
        response = await _run_agent_with_retry(agent, prompt, options={"max_tokens": 4000})
        text = response.text if hasattr(response, "text") else str(response)
        return ChapterContent(
            chapter_title=outline.title,
            markdown_content=text,
            image_placeholders=[],
        )
    except Exception as e:
        logger.error(f"❌ Error generating voice chapter '{outline.title}': {e}")
        return None
