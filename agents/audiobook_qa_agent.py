# agents/audiobook_qa_agent.py
"""
Audiobook QA Agent — reviews and adapts audio narration scripts for
accessibility, specifically for blind and visually-impaired listeners.

When "Blind Friendly" mode is enabled, this agent:
  • Replaces activities that require sight (drawing, coloring, reading labels)
    with equivalent oral/tactile/listening activities
  • Converts "Look at the image…" or "Find the picture…" directions into
    descriptive text or imagination-based exercises
  • Removes or converts homework that requires written/visual output into
    spoken-word, memory, or tactile alternatives
  • Adds audio descriptions for any image cues that remain
  • Maintains the SAME educational objectives and chapter structure

Usage:
    from agents.audiobook_qa_agent import review_script_for_blind_friendly

    improved_script = await review_script_for_blind_friendly(
        script, chapter_title, language, target_age, use_qwen=True
    )
"""
import logging
import os
from typing import Optional

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from config import get_model_config
from utils.retry import async_retry

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────

_BLIND_FRIENDLY_SYSTEM_PROMPT = """\
You are an expert in creating fully accessible educational content for blind and
visually-impaired children (ages 6-16) in Latin America.

Your task is to review and adapt an audio narration script so that it is
100% accessible to a blind listener. The script will be read aloud by a
Text-to-Speech engine — there is NO accompanying visual content.

## RULES

1. **PRESERVE STRUCTURE**: Keep the same chapter sections, learning objectives,
   and educational content. Only change activities/exercises that require vision.

2. **ADAPT VISUAL ACTIVITIES**: When you find an activity that says things like
   "draw a", "color the", "look at the picture", "write on the board", "find
   the image", "read the labels", "match images to words":
   → Replace with an equivalent oral, memory, tactile, or imagination activity.
   Examples:
     - "Draw the water cycle" → "Describe the water cycle step by step out loud"
     - "Color the map of Mexico" → "Clap once for each state you can name in Mexico"
     - "Look at the diagram and label the parts" → "Try to name 3 parts from memory"
     - "Write the answer on paper" → "Say your answer out loud or share it with someone nearby"

3. **REMOVE or ADAPT homework that requires visual tools**:
   - "Write in your notebook" → "Tell a family member what you learned"
   - "Draw a poster" → "Prepare a short 1-minute speech about the topic"
   - "Print and complete the worksheet" → "Answer each question by saying it aloud"

4. **IMAGE REFERENCES**: If the script says "here you would see an image of X",
   replace with a 1-2 sentence vivid description of that image:
   "Imagine X: [brief, clear, vivid description using colors, shapes, size, action]."

5. **CHALLENGES & QUESTIONS**: Keep them but ensure they can be answered verbally.
   "Think about it and answer out loud: …" is always acceptable.

6. **LANGUAGE**: Keep the SAME language as the original (Spanish, Portuguese, English).
   Keep the same warm, age-appropriate tone.

7. **DO NOT ADD** visual content (images, diagrams, worksheets).

8. **OUTPUT FORMAT**: Return ONLY the adapted script text. No headings, no metadata,
   no "Adapted version:" prefix — just the spoken narration text ready for TTS,
   with [PAUSE Xs] markers where appropriate.

9. **KEEP IT NATURAL**: The adapted script should feel natural and flowing when
   spoken aloud. Avoid mechanical replacements that sound awkward.
"""


async def _create_qa_agent(use_qwen: bool = False, model_id: str | None = None) -> ChatAgent:
    """Create the accessibility QA agent."""
    config = get_model_config(use_qwen)
    resolved_model = model_id if model_id else config.get("model_id")

    client = OpenAIChatClient(
        api_key=os.getenv(config["api_key_env"], ""),
        base_url=config["base_url"],
        model_id=resolved_model,
    )
    return ChatAgent(
        chat_client=client,
        name="AudiobookQAAgent",
        instructions=_BLIND_FRIENDLY_SYSTEM_PROMPT,
    )


@async_retry(max_retries=2, base_delay=2.0, max_delay=30.0)
async def _run_qa_agent(agent: ChatAgent, prompt: str) -> str:
    """Run the QA agent with retry."""
    response = await agent.run(prompt, max_tokens=4000)
    if hasattr(response, "text") and response.text:
        return response.text
    if hasattr(response, "content") and response.content:
        return response.content
    return str(response)


async def review_script_for_blind_friendly(
    script: str,
    chapter_title: str,
    language: str = "Spanish",
    target_age: int = 10,
    use_qwen: bool = False,
    model_id: str | None = None,
) -> Optional[str]:
    """
    Review and adapt an audio narration script for blind-friendly accessibility.

    Args:
        script: The TTS-ready narration script to review
        chapter_title: Chapter title (for context)
        language: Target language (Spanish, Portuguese, English)
        target_age: Target audience age
        use_qwen: Use Qwen model (DashScope) instead of GitHub Models
        model_id: Specific model ID override

    Returns:
        The adapted script as plain text, or None on failure.
        Falls back to the original script if adaptation fails.
    """
    if not script or len(script.strip()) < 50:
        logger.warning(f"[AudiobookQA] Script too short to review for '{chapter_title}'")
        return script

    logger.info(
        f"♿ [AudiobookQA] Reviewing '{chapter_title}' for blind-friendly accessibility "
        f"({len(script)} chars, lang={language}, age={target_age})"
    )

    try:
        agent = await _create_qa_agent(use_qwen=use_qwen, model_id=model_id)

        prompt = (
            f"Chapter: {chapter_title}\n"
            f"Language: {language}\n"
            f"Target age: {target_age} years\n\n"
            f"--- ORIGINAL SCRIPT ---\n"
            f"{script}\n"
            f"--- END ---\n\n"
            f"Please review this audio script and adapt it for blind-friendly accessibility. "
            f"Apply all the rules from your instructions. "
            f"Return ONLY the adapted narration text — no headers, no metadata."
        )

        adapted = await _run_qa_agent(agent, prompt)
        adapted = adapted.strip()

        if adapted and len(adapted) > 50:
            logger.info(
                f"✅ [AudiobookQA] '{chapter_title}' adapted: "
                f"{len(script)} → {len(adapted)} chars"
            )
            return adapted
        else:
            logger.warning(
                f"⚠️ [AudiobookQA] Adaptation result too short for '{chapter_title}', "
                f"keeping original"
            )
            return script

    except Exception as e:
        logger.error(
            f"❌ [AudiobookQA] Failed to adapt '{chapter_title}': {e}. Keeping original."
        )
        return script  # Graceful fallback to original


async def review_full_audiobook_for_blind_friendly(
    scripts: list[str],
    chapter_titles: list[str],
    language: str = "Spanish",
    target_age: int = 10,
    use_qwen: bool = False,
    model_id: str | None = None,
    progress_callback=None,
) -> list[str]:
    """
    Review and adapt all scripts in an audiobook for blind-friendly accessibility.

    Args:
        scripts: List of TTS-ready scripts (one per chapter/section)
        chapter_titles: Corresponding chapter titles
        language: Target language
        target_age: Target audience age
        use_qwen: Use Qwen model
        model_id: Specific model ID override
        progress_callback: Optional callback(idx, total, message)

    Returns:
        List of adapted scripts (same length as input)
    """
    adapted_scripts: list[str] = []
    total = len(scripts)

    for idx, (script, title) in enumerate(zip(scripts, chapter_titles)):
        if progress_callback:
            progress_callback(
                idx, total,
                f"♿ Adapting for blind-friendly: chapter {idx + 1}/{total}"
            )

        adapted = await review_script_for_blind_friendly(
            script=script,
            chapter_title=title,
            language=language,
            target_age=target_age,
            use_qwen=use_qwen,
            model_id=model_id,
        )
        adapted_scripts.append(adapted or script)

    if progress_callback:
        progress_callback(total, total, "✅ Blind-friendly adaptation complete!")

    logger.info(
        f"✅ [AudiobookQA] Full audiobook adaptation complete: "
        f"{len(adapted_scripts)} sections"
    )
    return adapted_scripts
