# agents/audio_book_script_agent.py
"""
Audio Book Script Agent — converts structured book content into a
narration-ready audio script with transitions, cues, and natural speech.

The agent generates an "audio-friendly" version of each chapter that:
  • Opens with a warm introduction / chapter title announcement
  • Converts visual content blocks (concepts, examples, activities, etc.)
    into flowing spoken narration
  • Adds transitions between sections ("Now let's move on to...")
  • Replaces [IMAGE:] / [VIDEO:] placeholders with descriptive audio cues
  • Appends a chapter summary / closing
  • Marks pauses with [PAUSE 1s], [PAUSE 2s] tags for the TTS engine

Usage:
    from agents.audio_book_script_agent import generate_audio_script, generate_full_audiobook_script

    # Single chapter
    script = await generate_audio_script(chapter, book_title, chapter_index, language)

    # Full book
    scripts = await generate_full_audiobook_script(curriculum, chapters, book_request)
"""
import logging
import os
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from models.book_spec import (
    BookRequest, Curriculum, ChapterContent, AudioNarration,
)
from config import get_model_config
from utils.retry import async_retry

logger = logging.getLogger(__name__)

# ── Audio script generation prompt ────────────────────────────────────────
_SCRIPT_SYSTEM_PROMPT = """\
You are an expert audio book narrator and script writer for educational children's books in Latin America.

Your job is to convert a structured book chapter (in markdown) into a **narration-ready audio script**.

RULES:
1. Write ONLY in the specified language — match the original chapter language exactly.
2. Open with a warm greeting and the chapter title.
3. When this chapter is part of a larger book, briefly reference what was covered before
   (e.g. "En el capítulo anterior aprendimos sobre...") and preview what's coming next.
4. Convert each section into flowing, natural spoken paragraphs:
   - "Concepto Clave" → Explain clearly as if speaking to the child face-to-face
   - "Ejemplo" → Tell it like a short story: "Imagina que..."
   - "Actividad" → Invite the listener: "Ahora te propongo algo divertido..."
   - "Desafío Creativo" → Challenge them: "¿Estás listo para el desafío?"
   - "Sabías que" → Use an excited tone: "¡Esto te va a sorprender!"
   - "Pregunta" → Pause and ask directly: "Piensa un momento..."
5. Add [PAUSE 1s] between sections and [PAUSE 2s] between major transitions.
6. Replace [IMAGE: description] with a brief audio description:
   "Aquí verías una imagen de [description]."
7. Replace [VIDEO: description] with:
   "En el libro puedes escanear el código QR para ver un video sobre [description]."
8. End with a brief recap and a friendly closing that transitions to the next chapter
   (or a final goodbye if it's the last chapter).
9. Do NOT include markdown formatting (no **, ##, etc.) — output plain spoken text only.
10. Keep the tone warm, engaging, and age-appropriate.
11. Keep sentences SHORT (max 25 words) — this will be read aloud by a TTS engine.
12. Spell out numbers under 100 as words.
13. Avoid abbreviations, acronyms, or symbols that TTS cannot pronounce.
14. Use natural breathing pauses: prefer short sentences over long compound ones.

OUTPUT FORMAT:
Return ONLY the narration script text. No headings, no metadata — just the spoken words
with [PAUSE Xs] markers where natural pauses should occur.
"""


async def _create_script_agent(use_qwen: bool = False, model_id: str | None = None) -> ChatAgent:
    """Create an LLM agent for audio script generation."""
    config = get_model_config(use_qwen)
    resolved_model = model_id if model_id else config.get("model_id")

    client = OpenAIChatClient(
        api_key=os.getenv(config["api_key_env"], ""),
        base_url=config["base_url"],
        model_id=resolved_model,
    )

    return ChatAgent(
        chat_client=client,
        name="AudioScriptAgent",
        instructions=_SCRIPT_SYSTEM_PROMPT,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  SINGLE CHAPTER SCRIPT
# ═══════════════════════════════════════════════════════════════════════════

@async_retry(max_retries=2, base_delay=2.0, max_delay=30.0)
async def _run_script_agent(agent: ChatAgent, prompt: str) -> str:
    """Run the script agent with retry."""
    response = await agent.run(prompt, max_tokens=4000)
    if hasattr(response, "text") and response.text:
        return response.text
    if hasattr(response, "content") and response.content:
        return response.content
    return str(response)


async def generate_audio_script(
    chapter: ChapterContent,
    book_title: str,
    chapter_index: int,
    language: str = "Spanish",
    target_age: int = 10,
    use_qwen: bool = False,
    model_id: str | None = None,
    *,
    curriculum: Curriculum | None = None,
    total_chapters: int | None = None,
) -> Optional[str]:
    """
    Generate a narration-ready audio script for a single chapter.

    Args:
        chapter: The chapter content with markdown
        book_title: Full book title
        chapter_index: 0-based chapter index
        language: Target language
        target_age: Target audience age
        use_qwen: Use Qwen model
        model_id: Specific model ID
        curriculum: Full book curriculum for narrative context
        total_chapters: Total number of chapters in the book

    Returns:
        The narration script as plain text, or None on failure
    """
    ch_num = chapter_index + 1
    logger.info(
        f"📝 [AudioScript] Generating script for chapter {ch_num}: "
        f"'{chapter.chapter_title}' ({len(chapter.markdown_content)} chars)"
    )

    try:
        agent = await _create_script_agent(use_qwen=use_qwen, model_id=model_id)

        # Build book-level context block
        book_context = ""
        if curriculum:
            toc_lines = "\n".join(
                f"  {i+1}. {ch.title}" for i, ch in enumerate(curriculum.chapters)
            )
            _total = total_chapters or len(curriculum.chapters)
            is_first = chapter_index == 0
            is_last = chapter_index == _total - 1
            position_hint = (
                "This is the FIRST chapter — give a warm welcome to the book."
                if is_first
                else (
                    "This is the LAST chapter — close with a heartfelt farewell."
                    if is_last
                    else f"This is chapter {ch_num} of {_total} — reference earlier content and preview what comes next."
                )
            )
            book_context = (
                f"=== FULL BOOK CONTEXT ===\n"
                f"Book title: {book_title}\n"
                f"Book description: {curriculum.description}\n"
                f"Total chapters: {_total}\n"
                f"Table of contents:\n{toc_lines}\n"
                f"Position: {position_hint}\n\n"
            )

        prompt = (
            f"{book_context}"
            f"Chapter {ch_num}: {chapter.chapter_title}\n"
            f"Language: {language}\n"
            f"Target age: {target_age} years\n\n"
            f"--- CHAPTER CONTENT ---\n"
            f"{chapter.markdown_content}\n"
            f"--- END ---\n\n"
            f"Convert this chapter into a narration-ready audio script "
            f"following all the rules. Remember: output ONLY the spoken text "
            f"with [PAUSE Xs] markers. Keep sentences SHORT for TTS."
        )

        script = await _run_script_agent(agent, prompt)

        if script and len(script.strip()) > 50:
            logger.info(
                f"✅ [AudioScript] Chapter {ch_num} script generated "
                f"({len(script)} chars, ~{len(script)//15}s estimated)"
            )
            return script.strip()
        else:
            logger.warning(
                f"⚠️ [AudioScript] Chapter {ch_num} script too short or empty"
            )
            return None

    except Exception as e:
        logger.error(
            f"❌ [AudioScript] Failed to generate script for chapter {ch_num}: {e}"
        )
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  FULL BOOK SCRIPT
# ═══════════════════════════════════════════════════════════════════════════

async def generate_full_audiobook_script(
    curriculum: Curriculum,
    chapters: List[ChapterContent],
    book_request: BookRequest,
    use_qwen: bool = False,
    model_id: str | None = None,
    progress_callback=None,
) -> List[str]:
    """
    Generate narration scripts for all chapters of a book.

    Args:
        curriculum: Book curriculum with title/description
        chapters: List of chapter contents
        book_request: Original book request
        use_qwen: Use Qwen model
        model_id: Specific model ID
        progress_callback: Optional callback(idx, total, message)

    Returns:
        List of script strings (one per chapter)
    """
    logger.info(
        f"📚 [AudioScript] Starting full audiobook script generation for "
        f"'{curriculum.title}' ({len(chapters)} chapters)"
    )

    scripts: List[str] = []

    language = (book_request.language or "Spanish").strip().lower()
    if language.startswith("port"):
        intro_open = "Bem-vindos ao livro"
        intro_start = "Vamos começar"
        closing_text = "E assim chegamos ao final do nosso livro"
        closing_tail = "Esperamos que você tenha gostado e aprendido muito. Até a próxima aventura!"
    elif language.startswith("eng"):
        intro_open = "Welcome to the book"
        intro_start = "Let's begin"
        closing_text = "And this brings us to the end of our book"
        closing_tail = "We hope you enjoyed it and learned a lot. See you in the next adventure!"
    else:
        intro_open = "Bienvenidos al libro"
        intro_start = "Comencemos"
        closing_text = "Y así llegamos al final de nuestro libro"
        closing_tail = "Esperamos que hayas disfrutado y aprendido mucho. ¡Hasta la próxima aventura!"

    # Generate intro script
    intro = (
        f"[PAUSE 1s]\n"
        f"{intro_open}: {curriculum.title}.\n\n"
        f"{curriculum.description}\n\n"
        f"[PAUSE 2s]\n"
        f"{intro_start}.\n"
        f"[PAUSE 2s]"
    )
    scripts.append(intro)
    logger.info(f"✅ [AudioScript] Book intro generated ({len(intro)} chars)")

    for i, chapter in enumerate(chapters):
        if progress_callback:
            progress_callback(
                i, len(chapters),
                f"📝 Generating audio script for chapter {i+1}: {chapter.chapter_title}"
            )

        script = await generate_audio_script(
            chapter=chapter,
            book_title=curriculum.title,
            chapter_index=i,
            language=book_request.language,
            target_age=book_request.target_audience_age,
            use_qwen=use_qwen,
            model_id=model_id,
            curriculum=curriculum,
            total_chapters=len(chapters),
        )

        if script:
            scripts.append(script)
        else:
            # Fallback: strip markdown and use raw text
            logger.warning(
                f"⚠️ [AudioScript] Using fallback plain-text for chapter {i+1}"
            )
            fallback = _fallback_script(chapter, i + 1, book_request.language)
            scripts.append(fallback)

    # Closing script
    closing = (
        f"[PAUSE 2s]\n"
        f"{closing_text}: {curriculum.title}.\n\n"
        f"{closing_tail}\n"
        f"[PAUSE 3s]"
    )
    scripts.append(closing)
    logger.info(
        f"✅ [AudioScript] Full audiobook script complete: "
        f"{len(scripts)} sections, "
        f"{sum(len(s) for s in scripts)} total chars"
    )

    if progress_callback:
        progress_callback(len(chapters), len(chapters), "✅ Audio scripts generated!")

    return scripts


def _fallback_script(chapter: ChapterContent, ch_num: int, language: str = "Spanish") -> str:
    """Create a basic narration script by stripping markdown."""
    text = chapter.markdown_content or ""
    # Remove markdown formatting
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'!\[[^\]]*\]\([^\)]+\)', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\[(IMAGE|VIDEO):\s*[^\]]+\]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    lang = (language or "Spanish").strip().lower()
    if lang.startswith("port"):
        chapter_prefix = "Capítulo"
        chapter_end = "Fim do capítulo"
    elif lang.startswith("eng"):
        chapter_prefix = "Chapter"
        chapter_end = "End of chapter"
    else:
        chapter_prefix = "Capítulo"
        chapter_end = "Fin del capítulo"

    return (
        f"[PAUSE 1s]\n"
        f"{chapter_prefix} {ch_num}: {chapter.chapter_title}.\n"
        f"[PAUSE 1s]\n\n"
        f"{text.strip()}\n\n"
        f"[PAUSE 2s]\n"
        f"{chapter_end} {ch_num}.\n"
        f"[PAUSE 2s]"
    )


# ═══════════════════════════════════════════════════════════════════════════
#  SCRIPT → TTS (combines script agent + voice agent)
# ═══════════════════════════════════════════════════════════════════════════

def prepare_script_for_tts(script: str) -> str:
    """
    Clean a narration script for TTS synthesis.

    - Strips [IMAGE:] and [VIDEO:] placeholders (not relevant for audio)
    - Converts [PAUSE Xs] markers to appropriate silence text
    - Removes any remaining markdown artifacts
    - Normalises whitespace
    """
    # Remove [IMAGE: ...] and [VIDEO: ...] placeholders — not relevant for audio-only
    script = re.sub(r'\[(IMAGE|VIDEO):\s*[^\]]+\]', '', script)
    # Remove markdown image embeds  ![alt](url)
    script = re.sub(r'!\[[^\]]*\]\([^\)]+\)', '', script)
    # Convert pause markers to ellipsis (natural TTS pause)
    script = re.sub(r'\[PAUSE\s+(\d+)s?\]', lambda m: '...' * int(m.group(1)), script)
    # Remove leftover markdown
    script = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', script)
    script = re.sub(r'#{1,6}\s+', '', script)
    # Remove QR code references and video recommendation blocks
    script = re.sub(r'🎬\s*\*?\*?Video recomendado:\*?\*?.*', '', script)
    # Normalise spacing
    script = re.sub(r'\n{3,}', '\n\n', script)
    return script.strip()


async def generate_and_narrate_book(
    curriculum: Curriculum,
    chapters: List[ChapterContent],
    book_request: BookRequest,
    output_dir: str,
    voice: str = "longxiaochun",
    tts_model: str = "qwen3-tts-vc-realtime",
    audio_format: str = "wav_24k",
    speech_rate: float = 0.95,
    use_qwen: bool = False,
    model_id: str | None = None,
    progress_callback=None,
) -> List[AudioNarration]:
    """
    End-to-end: generate audio scripts then synthesise them via TTS.

    Returns a list of AudioNarration objects (one per section).
    """
    from agents.voice_agent import narrate_chapter

    logger.info(
        f"🎙️ [AudioBook] Starting full pipeline: "
        f"script generation → TTS for '{curriculum.title}'"
    )

    # Step 1: Generate scripts
    scripts = await generate_full_audiobook_script(
        curriculum=curriculum,
        chapters=chapters,
        book_request=book_request,
        use_qwen=use_qwen,
        model_id=model_id,
        progress_callback=progress_callback,
    )

    # Step 2: Synthesise each script
    narrations: List[AudioNarration] = []
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    section_names = ["00_intro"] + [
        f"{i+1:02d}_{ch.chapter_title[:40]}" for i, ch in enumerate(chapters)
    ] + [f"{len(chapters)+1:02d}_closing"]

    for idx, (script, name) in enumerate(zip(scripts, section_names)):
        if progress_callback:
            progress_callback(
                idx, len(scripts),
                f"🔊 Synthesising audio section {idx+1}/{len(scripts)}: {name}"
            )

        tts_text = prepare_script_for_tts(script)
        logger.info(
            f"🔊 [AudioBook] Synthesising section {idx+1}/{len(scripts)}: "
            f"{name} ({len(tts_text)} chars)"
        )

        narration = narrate_chapter(
            chapter_title=name,
            markdown_content=tts_text,  # already cleaned, voice_agent strips md again harmlessly
            output_dir=output_dir,
            voice=voice,
            model=tts_model,
            audio_format=audio_format,
            speech_rate=speech_rate,
        )

        if narration:
            narrations.append(narration)
            logger.info(
                f"✅ [AudioBook] Section {idx+1} synthesised: "
                f"{narration.file_path} ({narration.size_bytes} bytes, "
                f"~{narration.duration_seconds:.0f}s)"
            )
        else:
            logger.warning(f"⚠️ [AudioBook] Failed to synthesise section: {name}")

    total_duration = sum(n.duration_seconds for n in narrations)
    total_size = sum(n.size_bytes for n in narrations)
    logger.info(
        f"✅ [AudioBook] Complete! {len(narrations)} sections, "
        f"~{total_duration:.0f}s total, {total_size/1024:.0f} KB"
    )

    if progress_callback:
        progress_callback(len(scripts), len(scripts), "✅ Audiobook generation complete!")

    return narrations
