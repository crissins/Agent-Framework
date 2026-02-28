# Agents Reference

Complete reference for all 17 agents in the LATAM Book Generator pipeline.

---

## Content Generation Agents

### Chat Agent
**File:** `agents/chat_agent.py`

Conversational agent that collects book generation parameters through natural dialogue. Maintains context across 20+ exchanges and emits a structured `book_request_json` when all required fields are captured.

**Functions:**
- `create_chat_agent(use_qwen=True)` → Creates the conversational agent
- `parse_book_request_from_response(text)` → Extracts JSON from agent response
- `build_book_request(data)` → Builds typed `BookRequest` from parsed dict

**Features:**
- Responds in the user's language
- Captures provider preferences (GitHub/Qwen)
- Captures output mode (full/audio_only)
- Captures voice/image preferences

---

### Curriculum Agent
**File:** `agents/curriculum_agent.py`

Designs structured educational book outlines following specified pedagogical methods.

**Functions:**
- `create_curriculum_agent(use_qwen, model_id)` → Creates the curriculum designer
- `generate_curriculum(agent, request)` → Returns `Curriculum` with chapter outlines

**Output:** `Curriculum` containing `title`, `description`, and list of `ChapterOutline` objects.

---

### Chapter Agent
**File:** `agents/chapter_agent.py`

Writes rich educational chapter content in markdown format with activities, questions, and cultural references.

**Functions:**
- `create_chapter_agent(use_qwen, model_id)` → Creates the chapter writer
- `generate_chapter(agent, outline, context)` → Returns `ChapterContent`

**Output:** `ChapterContent` with `chapter_title`, `markdown_content`, `image_placeholders[]`.

---

### Voice Curriculum Agent
**File:** `agents/voice_curriculum_agent.py`

Audio-optimized variant of the curriculum agent. Generates outlines suited for spoken delivery.

---

### Voice Chapter Agent
**File:** `agents/voice_chapter_agent.py`

Audio-optimized variant of the chapter agent. Produces flowing narrative text designed for narration rather than visual reading.

---

### Audio Book Script Agent
**File:** `agents/audio_book_script_agent.py`

Transforms structured chapter content into narration-ready audio scripts with pause markers and natural speech flow.

**Functions:**
- `generate_audio_script(chapter, book_title, ...)` → Returns optimized script text
- `prepare_script_for_tts(script)` → Strips formatting, adds pauses for TTS input
- `generate_full_audiobook_script(chapters, ...)` → Batch processing

---

### Audiobook QA Agent
**File:** `agents/audiobook_qa_agent.py`

Reviews and adapts audio narration scripts for accessibility — specifically for blind and visually-impaired listeners. When "Blind Friendly" mode is enabled, this agent replaces sight-dependent activities (drawing, colouring, reading labels) with equivalent oral, tactile, or imagination-based exercises.

**Functions:**
- `review_script_for_blind_friendly(script, chapter_title, language, target_age, use_qwen)` → Returns fully adapted accessible script
- `batch_review_for_blind_friendly(chapters, book_title, language, target_age, use_qwen)` → Batch processing for full book

**Features:**
- Preserves 100% of educational objectives and chapter structure
- Converts homework requiring visual tools to spoken/memory alternatives
- Adds audio descriptions for any remaining image cues
- Supports all 4 model providers via `get_model_config()`
- Async with retry via `@async_retry`

**Functions:**
- `generate_audio_script(chapter, book_title, ...)` → Returns optimized script text
- `prepare_script_for_tts(script)` → Strips formatting, adds pauses for TTS input
- `generate_full_audiobook_script(chapters, ...)` → Batch processing

---

### LaTeX Math Agent
**File:** `agents/latex_math_agent.py`

Generates chapters with rich mathematical notation using LaTeX, rendered via KaTeX in HTML output.

**Functions:**
- `create_latex_math_agent()` → Creates the math content agent
- `generate_math_chapter()` → Returns chapter with LaTeX blocks
- `extract_latex_blocks(text)` → Parses LaTeX from markdown
- `validate_latex_content(text)` → Validates LaTeX syntax

---

### Fact Check Agent
**File:** `agents/fact_check_agent.py`

Verifies educational content accuracy using web search. Provides confidence levels and source citations.

**Functions:**
- `create_fact_check_agent(use_qwen=True)` → Creates the fact checker with web search
- `fact_check_content(agent, content)` → Returns verification report
- `batch_fact_check(agent, chapters)` → Verifies multiple chapters
- `verify_chapter_accuracy(agent, title, content, age_group)` → Age-appropriate verification

---

## Media Agents

### Qwen Image Agent
**File:** `agents/qwen_image_agent.py`

AI image generation using Qwen-Image models via DashScope. The text LLM generates intelligent prompts with camera angle, lighting, style, and resolution parameters.

**Functions:**
- `generate_image_with_qwen(prompt, style, size)` → Returns `ImagePlaceholder`
- `generate_chapter_image(title, summary, ...)` → LLM-prompted image for a chapter

**Models supported:** `qwen-image-plus`, `qwen-image-max`, `qwen-image-max-2025-12-30`

**Resolutions:** 12 options from `512*512` to `1664*928` (landscape/portrait/square).

---

### DDG Image Search Agent
**File:** `agents/ddg_image_search_agent.py`

Web image search using DuckDuckGo with SafeSearch for child-appropriate results. Multi-region support with fallback logic.

**Functions:**
- `search_image(query, ...)` → Returns image URL
- `search_and_download_image(query, output_dir, ...)` → Downloads and returns `ImagePlaceholder`
- `search_images_for_chapter(chapter, ...)` → Batch search for a chapter

---

### YouTube Search Agent
**File:** `agents/youtube_search_agent.py`

Discovers relevant educational YouTube videos and generates QR codes for embedding in print books.

**Functions:**
- `search_youtube_video(query, ...)` → Returns video metadata
- `search_videos_for_chapter(title, queries, ...)` → Returns `VideoPlaceholder[]`
- `search_videos_for_book(chapters, ...)` → Batch search for entire book

---

### QR Code Agent
**File:** `agents/qr_agent.py`

Generates QR codes with optional logo overlay, returns base64 data URIs for HTML embedding.

**Functions:**
- `generate_qr_code(url, ...)` → Returns base64 QR image
- `save_qr_code(url, path, ...)` → Saves QR to file
- `generate_qr_batch(urls, ...)` → Batch generation

---

## Voice Agents

### Voice Agent
**File:** `agents/voice_agent.py`

Standard TTS synthesis via Qwen3 TTS-VC with 10 voice options, adjustable speech rate, and multiple audio formats.

**Functions:**
- `synthesize_speech(text, voice, ...)` → Returns audio bytes
- `synthesize_to_file(text, path, ...)` → Saves audio file
- `narrate_chapter(title, markdown, output_dir, ...)` → Returns `AudioNarration`
- `narrate_book(chapters, ...)` → Batch narration

**Voices:** `longxiaochun` (warm female), `longlaotie` (deep male), `longtong` (child), and 7 more.

---

### Voice Clone Agent
**File:** `agents/voice_clone_agent.py`

Voice enrollment and cloned-voice synthesis using Qwen3 TTS-VC. Manages persistent voice profiles.

**Functions:**
- `create_voice(sample_path, ...)` → Enrolls a voice from audio sample
- `list_voices()` / `query_voice()` / `delete_voice()` → Voice profile management
- `synthesize(text, voice, ...)` → Synthesis with cloned voice
- `narrate_chapter_vc(title, markdown, ...)` → Full chapter narration with clone

---

## Export Agents

### HTML CSS Agent
**File:** `agents/html_css_agent.py`

Template-based HTML book renderer. Parses LLM markdown into typed blocks and injects into the master template with CSS/JS configurations.

**Functions:**
- `generate_html_css_book_from_json(request, curriculum, chapters, output, template_id)` → Generates complete HTML book

---

### PDF Generator
**File:** `agents/html_to_pdf_converter.py`

Unicode-aware PDF generation using fpdf2 with embedded images, structured data rendering, and proper pagination.

**Functions:**
- `generate_pdf_from_data(request, curriculum, chapters, output, images_base)` → Generates PDF
- `convert_html_to_pdf(html_path, pdf_path)` → HTML-to-PDF conversion

---

### Markdown Agent
**File:** `agents/markdown_agent.py`

Exports book content as self-contained Markdown with base64-embedded images for maximum portability.

**Functions:**
- `save_markdown_book(book_output, path)` → Generates Markdown file
