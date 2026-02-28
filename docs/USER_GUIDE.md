# User Guide

## Getting Started

LATAM Book Generator offers three ways to create books:

1. **Chat Mode** — Describe your book in natural language
2. **Form Mode** — Fill in structured fields
3. **Voice Mode** — Record your voice and generate audiobooks

## Chat Mode (Recommended)

### How It Works

1. Open the Streamlit app
2. In the chat window, describe your book idea:
   > *"Quiero un libro sobre los volcanes de México para niños de 10 años, con método Montessori y narración de audio"*
3. The assistant asks clarifying questions if needed
4. When all parameters are captured, it emits a structured JSON
5. Generation starts automatically using your chat specifications

### Tips for Better Results

- **Be specific about the audience**: age, country, language
- **Mention the learning method**: Scandinavian, Montessori, or Project-Based
- **Specify output preferences**: "with images", "audiobook only", "with video links"
- **You can switch languages**: The AI responds in whatever language you write

### Chat-Captured Options

The chat agent can capture:
- Topic, age, country, language
- Number of chapters and pages
- Learning method
- Model provider (GitHub/Qwen)
- Image source (AI/web search/none)
- Voice generation preferences
- Template selection

## Form Mode

Use the form fields at the top of the page:
- **Topic** — What the book is about
- **Country** — Target country for cultural references
- **Language** — Spanish, Portuguese, or English
- **Age** — Target audience age (8-16)
- **Method** — Pedagogical approach
- **Chapters** — Number of chapters (2-12)
- **Pages/Chapter** — Content density (1-20)

Click **"🚀 Generate Full Book"** or **"🎧 Generate Audiobook Only"**.

## Voice Cloning Workflow

### Recording a Voice Sample

1. Open **🎤 Voice Cloning** in the sidebar
2. Enter a profile name (e.g., "teacher_maria")
3. Click the microphone icon to record a 10+ second sample
4. Click **"🧬 Clone & Save"**
5. Your voice profile is now saved and reusable

### Using a Cloned Voice

1. In the sidebar, select your voice profile from the dropdown
2. Click **"✅ Activate"**
3. Generate a book — it will be narrated in your cloned voice
4. If cloning fails, the system falls back to standard TTS

### Managing Voice Profiles

- Profiles persist in `books/voice_clones/voice_registry.json`
- Audio samples stored in `books/voice_clones/samples/`
- Use **"🗑️ Delete"** to remove a profile
- Re-clone at any time with a new recording

## Generation Modes

### Full Book Generation

Produces all output formats:
- Curriculum design → Chapter writing → Images → Videos → Audio → Export
- Outputs: HTML, PDF, Markdown, JSON, Audio ZIP

### Audiobook-Only Generation

Streamlined audio-first pipeline:
- Voice-optimized curriculum → Voice chapters → Audio scripts → TTS
- Outputs: JSON, Markdown, Audio files
- Uses specialized voice agents for better narration flow

## Sidebar Settings

### Model Settings
- **Use Qwen Models** — Toggle between GitHub (free) and Qwen (production)
- **Region** — DashScope region (affects latency)
- **Text Model** — qwen-flash (fast/cheap) to qwen-max (highest quality)
- **Image Model** — qwen-image-plus (standard) to qwen-image-max (best)

### Images & Video
- **Image Source** — AI Generate, DDG SafeSearch, or None
- **Images per chapter** — 0 to 5
- **Art Style** — 12 options including auto (AI picks best style)
- **YouTube Video Search** — Embed relevant educational videos with QR codes

### Voice & Audio
- **Enable Narration** — On/Off
- **Voice** — 10 options with different tones and genders
- **Audio Format** — WAV at 24k (recommended), 16k, or 22k
- **Speech Rate** — 0.5x to 2.0x (0.95 recommended for education)

### Book Template
- **Visual Template** — 10 themed designs or "auto" for AI selection
- Templates control fonts, colors, borders, and ornaments

## Viewing & Downloading Output

### In-Browser Preview
- **PDF** — Inline iframe preview
- **Audio** — Built-in audio player for each chapter
- **Curriculum JSON** — Expandable structured view

### Downloads
- **📊 JSON** — Complete structured data
- **🌐 HTML** — Self-contained interactive book
- **📝 Markdown** — Portable text format
- **📄 PDF** — Print-ready document
- **📥 Audio ZIP** — All chapter narrations bundled

### Output Directory Structure

```
books/
├── json/20260227_054437/book_output.json
├── html/20260227_054437/libro_interactivo.html
├── md/20260227_054437/libro_interactivo.md
├── pdf/20260227_054437/libro_interactivo.pdf
├── audio/20260227_054437/
│   ├── Capitulo_1_vc.wav
│   ├── Capitulo_2_vc.wav
│   └── ...
├── images/20260227_054437/
│   └── {chapter_name}/
│       └── image_001.png
└── voice_clones/
    ├── voice_registry.json
    └── samples/
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| No audio generated | Check `DASHSCOPE_API_KEY` is set and valid |
| Images not appearing | Enable Qwen Image model and set `DASHSCOPE_API_KEY` |
| Chat ignores my preferences | Make sure you're in Chat Mode end-to-end; don't mix form and chat |
| PDF has missing characters | Expected for CJK/special scripts; use HTML for full Unicode |
| Voice clone sounds robotic | Use a longer, clearer voice sample (15+ seconds) |
| Generation stalls | Check console for API errors; try reducing chapter count |
| `st.audio_input` error | Upgrade: `pip install streamlit>=1.54.0` |
