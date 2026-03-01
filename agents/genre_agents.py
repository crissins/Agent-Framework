"""
Genre-specific book agents for non-educational content.

Supported genres (beyond "educational"):
  • poetry              — single or multi-poem chapters, no activities
  • fairy_tale          — narrative story chapters, no curriculum structure
  • personal_development — adult non-fiction prose, no educational fluff

Each genre gets:
  - A dedicated *outline* agent  (replaces CurriculumAgent)
  - A dedicated *chapter* agent  (replaces ChapterAgent)

The Curriculum / ChapterContent models are still used so the rest of
the pipeline (HTML, PDF, Markdown export) works unchanged.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

from config import get_model_config
from models.book_spec import BookRequest, ChapterContent, ChapterOutline, Curriculum
from utils.retry import async_retry

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────

def _build_client(use_qwen: bool, model_id: str | None, provider: str | None = None) -> OpenAIChatClient:
    """Build an OpenAIChatClient using explicit provider > env var > use_qwen flag."""
    config = get_model_config(use_qwen=use_qwen, provider=provider)
    resolved = model_id or config.get("model_id")
    base_url = config.get("base_url") or ""
    if not base_url:
        raise ValueError(f"No base_url for provider config: {config}")
    return OpenAIChatClient(
        api_key=os.getenv(config["api_key_env"], ""),
        base_url=base_url,
        model_id=resolved,
    )


@async_retry(max_retries=3, base_delay=2.0, max_delay=60.0)
async def _run(agent: ChatAgent, prompt: str, options: dict):
    return await agent.run(prompt, **options)


# ──────────────────────────────────────────────────────────────────────────────
# POETRY
# ──────────────────────────────────────────────────────────────────────────────

async def create_poetry_outline_agent(use_qwen: bool = False, model_id: str | None = None, provider: str | None = None) -> ChatAgent:
    """Creates the table-of-contents / section outline for a poetry collection."""
    return ChatAgent(
        chat_client=_build_client(use_qwen, model_id, provider),
        name="PoetryOutlineAgent",
        instructions=(
            "You are a celebrated poetry editor and literary curator. "
            "Your task is to design the structure of a poetry collection book.\n\n"
            "### OUTPUT FORMAT ###\n"
            "Return a JSON object matching this schema exactly:\n"
            '{"title": "...", "description": "...", "chapters": [{"title": "...", "summary": "..."}]}\n\n'
            "Guidelines:\n"
            "- 'title': a beautiful, evocative title for the entire collection\n"
            "- 'description': 2-3 sentences describing the emotional landscape and themes\n"
            "- Each 'chapter' represents a *section* or *thematic grouping* of poems\n"
            "  - 'title': the section name (e.g. 'Dawn', 'Longing', 'The Sea')\n"
            "  - 'summary': brief note about the emotional/thematic tone of this section\n"
            "- Do NOT include activities, exercises, learning objectives, or QR codes\n"
            "- Respond entirely in the language specified by the user\n"
        ),
    )


async def create_poetry_chapter_agent(use_qwen: bool = False, model_id: str | None = None, provider: str | None = None) -> ChatAgent:
    """Writes a section of poems for a poetry collection."""
    return ChatAgent(
        chat_client=_build_client(use_qwen, model_id, provider),
        name="PoetryChapterAgent",
        instructions=(
            "You are a gifted poet and creative writer. "
            "Write a section of a poetry collection as beautifully crafted Markdown.\n\n"
            "### STRUCTURE ###\n"
            "Each section should contain 3-5 individual poems. For each poem:\n"
            "  1. Give it a title using ## heading\n"
            "  2. Write the poem body — use line breaks, stanzas, and white space deliberately\n"
            "  3. (Optional) add a short 1-sentence italicised note *after* the poem for context\n\n"
            "### STYLE ###\n"
            "- Vary forms: free verse, haiku, sonnet, prose poem, etc.\n"
            "- Use vivid imagery, metaphor, and rhythm\n"
            "- Never include educational activities, QR codes, questions, or bullet lists of facts\n"
            "- Respond entirely in the language specified by the user\n"
        ),
    )


async def generate_poetry_section(
    agent: ChatAgent,
    outline: ChapterOutline,
    request: BookRequest,
    max_tokens: int = 3000,
) -> Optional[ChapterContent]:
    prompt = (
        f"Write a poetry section for the collection '{outline.title}'.\n\n"
        f"Section theme: {outline.summary}\n"
        f"Overall collection topic: {request.topic}\n"
        f"Language: {request.language}\n"
        f"Target reader age: {request.target_audience_age}\n"
        f"Country / cultural context: {request.country}\n\n"
        "Return only the poem section content in Markdown — no extra commentary."
    )
    try:
        response_text = await _run(agent, prompt, {"max_tokens": max_tokens})
        content = response_text if isinstance(response_text, str) else str(response_text)
        return ChapterContent(chapter_title=outline.title, markdown_content=content)
    except Exception as exc:
        logger.error(f"Poetry section generation failed: {exc}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# FAIRY TALE / STORY
# ──────────────────────────────────────────────────────────────────────────────

async def create_fairy_tale_outline_agent(use_qwen: bool = False, model_id: str | None = None, provider: str | None = None) -> ChatAgent:
    """Creates the chapter outline (storyline arc) for a fairy tale or story book."""
    return ChatAgent(
        chat_client=_build_client(use_qwen, model_id, provider),
        name="FairyTaleOutlineAgent",
        instructions=(
            "You are a master storyteller and children's book author. "
            "Design the narrative arc for a fairy tale or story book.\n\n"
            "### OUTPUT FORMAT ###\n"
            "Return a JSON object:\n"
            '{"title": "...", "description": "...", "chapters": [{"title": "...", "summary": "..."}]}\n\n'
            "Guidelines:\n"
            "- 'title': a captivating story title\n"
            "- 'description': hook description — setting, main character, central conflict\n"
            "- Each 'chapter' is a story chapter with a narrative purpose\n"
            "  - 'title': chapter title (can be evocative or numbered)\n"
            "  - 'summary': 2-3 sentence plot summary — what happens, what changes\n"
            "- Follow proper story arc: setup → rising action → climax → falling action → resolution\n"
            "- Do NOT include learning objectives, curriculum goals, or activities\n"
            "- Respond entirely in the language specified by the user\n"
        ),
    )


async def create_fairy_tale_chapter_agent(use_qwen: bool = False, model_id: str | None = None, provider: str | None = None) -> ChatAgent:
    """Writes a narrative chapter for a fairy tale or story book."""
    return ChatAgent(
        chat_client=_build_client(use_qwen, model_id, provider),
        name="FairyTaleChapterAgent",
        instructions=(
            "You are a master storyteller. Write engaging, immersive story chapters in Markdown.\n\n"
            "### STRUCTURE ###\n"
            "Write flowing narrative prose. You may use:\n"
            "  - Vivid scene-setting descriptions\n"
            "  - Character dialogue (use straight quotes or em-dashes consistently)\n"
            "  - Sensory details (sight, sound, smell, touch)\n"
            "  - Emotional interiority -- what characters feel and think\n"
            "  - [IMAGE: brief visual description] placeholders where an illustration would help\n\n"
            "### RULES ###\n"
            "- Write ONLY the story narrative — no activities, no learning objectives\n"
            "- No QR codes, no bullet fact lists, no educational sections\n"
            "- End each chapter on a moment that propels the reader forward\n"
            "- Match tone and vocabulary to the specified reader age group\n"
            "- Respond entirely in the language specified by the user\n"
        ),
    )


async def generate_story_chapter(
    agent: ChatAgent,
    outline: ChapterOutline,
    request: BookRequest,
    book_title: str,
    max_tokens: int = 4000,
) -> Optional[ChapterContent]:
    prompt = (
        f"Write chapter '{outline.title}' for the story '{book_title}'.\n\n"
        f"Chapter plot: {outline.summary}\n"
        f"Overall story / topic: {request.topic}\n"
        f"Language: {request.language}\n"
        f"Target reader age: {request.target_audience_age}\n"
        f"Setting / cultural context: {request.country}\n\n"
        "Write immersive narrative prose in Markdown. "
        "Do not include any educational activities or structured sections."
    )
    try:
        response_text = await _run(agent, prompt, {"max_tokens": max_tokens})
        content = response_text if isinstance(response_text, str) else str(response_text)
        return ChapterContent(chapter_title=outline.title, markdown_content=content)
    except Exception as exc:
        logger.error(f"Story chapter generation failed: {exc}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# PERSONAL DEVELOPMENT (non-fiction)
# ──────────────────────────────────────────────────────────────────────────────

async def create_pd_outline_agent(use_qwen: bool = False, model_id: str | None = None, provider: str | None = None) -> ChatAgent:
    """Creates the chapter outline for a personal development / self-help book."""
    return ChatAgent(
        chat_client=_build_client(use_qwen, model_id, provider),
        name="PersonalDevelopmentOutlineAgent",
        instructions=(
            "You are a bestselling author of personal development and self-improvement books. "
            "Design the structure for a compelling non-fiction personal development book.\n\n"
            "### OUTPUT FORMAT ###\n"
            "Return a JSON object:\n"
            '{"title": "...", "description": "...", "chapters": [{"title": "...", "summary": "..."}]}\n\n'
            "Guidelines:\n"
            "- 'title': powerful, transformative title (think: 'Atomic Habits', 'The Power of Now')\n"
            "- 'description': who this book is for, the core transformation it promises\n"
            "- Each chapter builds on the previous — a journey of growth and insight\n"
            "  - 'title': punchy chapter title (a statement, question, or principle)\n"
            "  - 'summary': the core insight, the reader's problem it solves, what they'll gain\n"
            "- Do NOT use educational/pedagogical language — this is for adult readers\n"
            "- Respond entirely in the language specified by the user\n"
        ),
    )


async def create_pd_chapter_agent(use_qwen: bool = False, model_id: str | None = None, provider: str | None = None) -> ChatAgent:
    """Writes a chapter for a personal development book."""
    return ChatAgent(
        chat_client=_build_client(use_qwen, model_id, provider),
        name="PersonalDevelopmentChapterAgent",
        instructions=(
            "You are a bestselling author of personal development books. "
            "Write deeply insightful, practical, and inspiring chapters in Markdown.\n\n"
            "### CHAPTER STRUCTURE ###\n"
            "Each chapter should flow like a great non-fiction book:\n"
            "  1. **Opening Hook** — a compelling story, surprising fact, or bold statement\n"
            "  2. **Core Insight** — the central idea of this chapter, explained clearly\n"
            "  3. **Why It Matters** — the cost of ignoring this insight in real life\n"
            "  4. **Practical Framework** — concrete steps, mental models, or strategies\n"
            "  5. **Real-World Examples** — relatable stories or case studies\n"
            "  6. **Reflection Prompt** — 1-3 deep journalling / introspection questions\n"
            "  7. **Chapter Takeaway** — one crisp sentence the reader will remember\n\n"
            "### RULES ###\n"
            "- Write like a trusted mentor — warm, direct, no fluff\n"
            "- NO educational rubrics, age-group activities, QR codes, or LATAM-style sections\n"
            "- Use real psychological research, philosophy, or science to back up claims\n"
            "- Respond entirely in the language specified by the user\n"
        ),
    )


async def generate_pd_chapter(
    agent: ChatAgent,
    outline: ChapterOutline,
    request: BookRequest,
    book_title: str,
    max_tokens: int = 4000,
) -> Optional[ChapterContent]:
    prompt = (
        f"Write chapter '{outline.title}' for the personal development book '{book_title}'.\n\n"
        f"Chapter focus: {outline.summary}\n"
        f"Book topic: {request.topic}\n"
        f"Language: {request.language}\n"
        f"Primary audience age: {request.target_audience_age}\n"
        f"Cultural context: {request.country}\n\n"
        "Write a full personal development chapter in Markdown. "
        "Follow the hook → insight → framework → examples → reflection → takeaway structure. "
        "No educational activities or children's content."
    )
    try:
        response_text = await _run(agent, prompt, {"max_tokens": max_tokens})
        content = response_text if isinstance(response_text, str) else str(response_text)
        return ChapterContent(chapter_title=outline.title, markdown_content=content)
    except Exception as exc:
        logger.error(f"Personal development chapter generation failed: {exc}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Shared: generate outline (curriculum equivalent) for any non-educational genre
# ──────────────────────────────────────────────────────────────────────────────

async def generate_genre_outline(
    outline_agent: ChatAgent,
    request: BookRequest,
    max_tokens: int = 2000,
) -> Optional[Curriculum]:
    """
    Generate the structural outline (acts like Curriculum) for non-educational genres.
    Returns the same Curriculum model so the rest of the pipeline is unchanged.
    """
    import json as _json

    prompt = (
        f"Design the structure for a {request.genre.replace('_', ' ')} book.\n\n"
        f"Topic / Theme: {request.topic}\n"
        f"Language: {request.language}\n"
        f"Target reader age: {request.target_audience_age}\n"
        f"Country / cultural context: {request.country}\n"
        f"Number of chapters/sections: {request.num_chapters}\n\n"
        "Return ONLY valid JSON matching the required schema — no markdown fences, no extra text."
    )

    try:
        response_text = await _run(outline_agent, prompt, {"max_tokens": max_tokens})
        raw = response_text if isinstance(response_text, str) else str(response_text)

        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            raw = raw.rsplit("```", 1)[0]

        data = _json.loads(raw)
        # Pad chapters if LLM returned fewer
        while len(data.get("chapters", [])) < request.num_chapters:
            data["chapters"].append({
                "title": f"Chapter {len(data['chapters']) + 1}",
                "summary": "Content to be generated."
            })
        return Curriculum(**data)
    except Exception as exc:
        logger.error(f"Genre outline generation failed: {exc}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Top-level dispatcher: generate a full non-educational book
# ──────────────────────────────────────────────────────────────────────────────

async def generate_genre_book_async(
    request: BookRequest,
    use_qwen: bool = False,
    model_id: str | None = None,
    provider: str | None = None,   # explicit provider: 'github'|'qwen'|'claude'|'azure'
    max_tokens_outline: int = 2000,
    max_tokens_chapter: int = 4000,
    progress_callback=None,   # callable(str) for UI feedback
) -> tuple[Optional[Curriculum], list[ChapterContent]]:
    """
    Full non-educational book generation pipeline.

    Dispatches to the correct agent set based on request.genre.
    Returns (curriculum, chapters) — same shape as generate_book_async.
    """

    def _progress(msg: str):
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)

    genre = request.genre

    # ── Build outline agent ────────────────────────────────────────────────
    if genre == "poetry":
        outline_agent = await create_poetry_outline_agent(use_qwen, model_id, provider)
        chapter_agent = await create_poetry_chapter_agent(use_qwen, model_id, provider)
    elif genre == "fairy_tale":
        outline_agent = await create_fairy_tale_outline_agent(use_qwen, model_id, provider)
        chapter_agent = await create_fairy_tale_chapter_agent(use_qwen, model_id, provider)
    elif genre == "personal_development":
        outline_agent = await create_pd_outline_agent(use_qwen, model_id, provider)
        chapter_agent = await create_pd_chapter_agent(use_qwen, model_id, provider)
    else:
        raise ValueError(f"Unsupported genre for genre_agents: {genre!r}")

    # ── Generate outline ───────────────────────────────────────────────────
    _progress("🗂️ Generating outline…")
    curriculum = await generate_genre_outline(outline_agent, request, max_tokens_outline)
    if not curriculum:
        return None, []

    _progress(f"✅ Outline ready — {len(curriculum.chapters)} sections")

    # ── Generate chapters ──────────────────────────────────────────────────
    full_chapters: list[ChapterContent] = []
    for i, outline in enumerate(curriculum.chapters):
        _progress(f"✍️ Writing {i+1}/{len(curriculum.chapters)}: {outline.title}")

        if genre == "poetry":
            chapter = await generate_poetry_section(
                chapter_agent, outline, request, max_tokens_chapter
            )
        elif genre == "fairy_tale":
            chapter = await generate_story_chapter(
                chapter_agent, outline, request, curriculum.title, max_tokens_chapter
            )
        elif genre == "personal_development":
            chapter = await generate_pd_chapter(
                chapter_agent, outline, request, curriculum.title, max_tokens_chapter
            )
        else:
            chapter = None

        if chapter:
            full_chapters.append(chapter)

    return curriculum, full_chapters
