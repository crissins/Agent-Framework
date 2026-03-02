<p align="center">
  <img src="https://img.shields.io/badge/Agents%20League-Creative%20Apps-blueviolet?style=for-the-badge&logo=microsoft" alt="Agents League Creative Apps" />
  <img src="https://img.shields.io/badge/Microsoft-Agent%20Framework-0078D4?style=for-the-badge&logo=microsoft" alt="Microsoft Agent Framework" />
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+" />
  <img src="https://img.shields.io/badge/Streamlit-1.54+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License" />
  <a href="https://www.youtube.com/watch?v=Tr-6JnxO-9k"><img src="https://img.shields.io/badge/YouTube-Demo%20Video-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="YouTube Demo" /></a>
</p>

<h1 align="center">📚 LATAM Book Generator</h1>

<p align="center">
  <strong>AI-powered platform that creates complete, culturally relevant educational books for children across Latin America — with voice narration, AI illustrations, voice cloning, and multi-format export.</strong>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-features">Features</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-demo">Demo</a> •
  <a href="#-why-this-matters">Why This Matters</a> •
  <a href="COPILOT_STORY.md">Copilot Story</a> •
  <a href="https://www.youtube.com/watch?v=Tr-6JnxO-9k">📺 YouTube Demo</a> •
  <a href="docs/INDEX.md">Full Docs</a>
</p>

---

## 🎯 Why This Matters

**Millions of children** in Latin America deserve educational content that reflects their culture, language, and reality. Yet most AI-generated educational material is US/Euro-centric and English-only.

**LATAM Book Generator** solves this by orchestrating **16 specialized AI agents** into a production pipeline that produces **complete, publication-ready educational books** — tailored to specific countries, age groups, and pedagogical methods — in Spanish, Portuguese, or English — with AI illustrations, audiobook narration, and even **voice cloning** so a parent or teacher can narrate in their own voice.

### What Makes This Special

| Dimension | What We Built |
|-----------|--------------|
| **Multi-Agent Orchestration** | 16 specialized agents collaborating sequentially — curriculum design, chapter writing, image generation, TTS, fact-checking — each with a focused role |
| **Cultural Intelligence** | Country-specific content for Mexico, Colombia, Argentina, Chile, Peru, and Brazil with local references and i18n support for 11 languages |
| **Multimodal Output** | Text → HTML → PDF → Markdown → Audiobook → Images → QR-embedded videos — all from a single natural-language prompt |
| **Voice Cloning** | Record your voice, clone it, and generate full audiobooks narrated in your own voice using Qwen3 TTS-VC |
| **Conversational UX** | Chat naturally with the AI assistant to design your book — no forms required |
| **4 Model Providers** | GitHub Models, Qwen/DashScope (3 regions), Anthropic Claude, and Azure OpenAI — switchable at runtime |
| **Production-Ready** | HTTP server mode, AI Toolkit tracing, retry logic with exponential backoff, typed Pydantic schemas, and session persistence |

---

## ✨ Features

### 📖 Full Book Generation Pipeline

From a single topic description, the system orchestrates multiple AI agents to produce:

- **Structured Curriculum** — Age-appropriate chapter outlines following Scandinavian, Montessori, or Project-Based pedagogy
- **Rich Chapter Content** — Educational text with activities, reflection questions, experiments, and cultural references
- **AI Illustrations** — Generated via Qwen-Image-Plus/Max with intelligent prompt engineering (auto-selects art style, camera angle, lighting, and resolution)
- **Web Image Search** — DuckDuckGo SafeSearch fallback for royalty-free educational images
- **YouTube Video Embeds** — Relevant educational videos with auto-generated QR codes for print books
- **LaTeX Math Support** — Rich mathematical notation rendered via KaTeX for STEM content
- **Fact-Checking** — Web search-powered verification of educational claims with confidence scoring

### 🎙️ Audiobook Generation

| Capability | Detail |
|------------|--------|
| **TTS Models** | `qwen3-tts-flash` (fast/cheap), `qwen3-tts-instruct-flash` (emotion/character control), `qwen3-tts-vd` (custom voice from text description) |
| **Voice Clone** | `qwen3-tts-vc` — replicates any enrolled voice with high fidelity |
| **10 Built-in Voices** | Male, female, and child voices in multiple styles (warm, lively, deep, humorous, educational) |
| **Audio Script Optimization** | AI transforms chapter markdown into narration-ready scripts with pause markers |
| **Audio-Only Mode** | Skip visual output and produce pure audiobooks with voice-first curriculum design |
| **Speech Rate Control** | 0.5× to 2.0× speed adjustment optimized for educational content |
| **Audio ZIP Download** | All chapter narrations bundled as a single downloadable archive |

### 🎨 10 Visual Templates

Curated CSS/JS book templates with automatic AI selection:

| Template | Style | Best For |
|----------|-------|----------|
| `storybook` | Warm borders, soft colors | Fiction, fairy tales |
| `stem` | Clean diagrams, scientific layout | Science, technology |
| `adventure` | Bold colors, explorer themed | Geography, history |
| `math` | KaTeX-ready, equation-focused | Mathematics, physics |
| `low_budget` | B&W coloring pages | Printable worksheets |
| `nature` | Earthy tones, leaf ornaments | Biology, ecology |
| `culture` | Vibrant folk-art borders | Social studies, culture |
| `space` | Dark theme, star backgrounds | Astronomy |
| `ocean` | Wave patterns, blue palette | Marine science |
| `auto` | AI picks best match | Any topic |

### 📦 Export Formats

| Format | Description |
|--------|-------------|
| **HTML** | Interactive, self-contained book with embedded images, videos, and styled templates |
| **PDF** | Print-ready with Unicode support, embedded images, and proper pagination |
| **Markdown** | Clean markdown with base64-embedded images for portability |
| **JSON** | Structured data for programmatic consumption or re-rendering |
| **Audio ZIP** | All chapter narrations bundled as a downloadable archive |

### 💬 Conversational Interface

A chat-based AI assistant that:
- Collects all book parameters through natural dialogue
- Maintains memory across 20+ conversation exchanges
- Emits a structured `book_request_json` when all parameters are confirmed
- Supports switching between model providers mid-conversation
- Automatically responds in the user's language

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Streamlit UI  (app.py)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │Chat Mode │  │Form Mode │  │Voice Mode│  │   Settings / Sidebar │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────────────────┘ │
│       └─────────────┴──────────────┘                                 │
│                           │                                          │
├───────────────────────────▼──────────────────────────────────────────┤
│               Agent Orchestration Layer  (16 Agents)                 │
│                                                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────────┐ │
│  │ Chat Agent  │ │  Curriculum │ │   Chapter   │ │ Voice Agents  │ │
│  │             │ │    Agent    │ │    Agent    │ │  (5 modules)  │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────────┐ │
│  │ Qwen Image  │ │ DDG Search  │ │YouTube + QR │ │  Fact Check   │ │
│  │  Generator  │ │             │ │    Agent    │ │    Agent      │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────────┘ │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                      Export & Rendering Layer                        │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌───────────────────────┐ │
│  │ HTML │  │ PDF  │  │  MD  │  │ JSON │  │      Audio ZIP        │ │
│  └──────┘  └──────┘  └──────┘  └──────┘  └───────────────────────┘ │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│               Flexible Model Providers  (config.py)                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐ │
│  │  GitHub Models   │  │ Qwen/DashScope   │  │ Claude / Azure OAI │ │
│  │  gpt-4o-mini     │  │ Text·Image·TTS   │  │  (configurable)    │ │
│  │  Free dev tier   │  │ 3 global regions │  │                    │ │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### Agent Breakdown

| Agent | File | Role |
|-------|------|------|
| **Chat Agent** | `agents/chat_agent.py` | Conversational requirement elicitation with memory |
| **Curriculum Agent** | `agents/curriculum_agent.py` | Designs structured educational outlines |
| **Chapter Agent** | `agents/chapter_agent.py` | Writes rich educational chapters in markdown |
| **Voice Curriculum** | `agents/voice_curriculum_agent.py` | Audio-optimized curriculum design |
| **Voice Chapter** | `agents/voice_chapter_agent.py` | Chapters optimized for spoken delivery |
| **Audio Script** | `agents/audio_book_script_agent.py` | Transforms chapters into narration-ready scripts |
| **Voice Agent** | `agents/voice_agent.py` | Standard TTS via Qwen3 (10 built-in voices) |
| **Voice Clone** | `agents/voice_clone_agent.py` | Voice enrollment + cloned-voice synthesis |
| **Image Generator** | `agents/qwen_image_agent.py` | AI illustrations via Qwen-Image models |
| **DDG Image Search** | `agents/ddg_image_search_agent.py` | Web image search with SafeSearch |
| **YouTube + QR** | `agents/youtube_search_agent.py` | Educational video discovery + QR code generation |
| **Fact Checker** | `agents/fact_check_agent.py` | Web search verification of educational claims |
| **LaTeX Math** | `agents/latex_math_agent.py` | Mathematical content with KaTeX rendering |
| **HTML Renderer** | `agents/html_css_agent.py` | Template-based HTML book rendering engine |
| **PDF Generator** | `agents/html_to_pdf_converter.py` | Unicode PDF with embedded images |
| **Markdown Export** | `agents/markdown_agent.py` | Self-contained markdown with base64 images |

### Data Flow

All agents communicate through **typed Pydantic schemas** defined in `models/book_spec.py`:

```
BookRequest → Curriculum → [ChapterContent] → BookOutput
                                ├── ImagePlaceholder[]
                                ├── VideoPlaceholder[]
                                └── AudioNarration
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- At least one API key (GitHub Token **or** DashScope API key)

### 1. Clone & Setup

```bash
git clone https://github.com/crissins/Agent-Framework.git
cd Agent-Framework

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate
# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# At minimum, provide one of these:
GITHUB_TOKEN=ghp_your_github_token_here
DASHSCOPE_API_KEY=sk-your_dashscope_key_here

# Optional providers
ANTHROPIC_API_KEY=sk-ant-your_key_here
AZURE_OPENAI_API_KEY=your_azure_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# Optional: Enable AI Toolkit tracing
AITK_TRACING_ENABLED=0
```

| Key | Source | Used For |
|-----|--------|----------|
| `GITHUB_TOKEN` | [github.com/settings/tokens](https://github.com/settings/tokens) | Text generation via GitHub Models (free tier) |
| `DASHSCOPE_API_KEY` | [dashscope.aliyun.com](https://dashscope.aliyun.com/) | Text, images, TTS, and voice cloning via Qwen |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/) | Text generation via Claude models |
| `AZURE_OPENAI_API_KEY` | [portal.azure.com](https://portal.azure.com/) | Text generation via Azure OpenAI |

### 3. Run

```bash
# Streamlit UI (recommended)
python -m streamlit run app.py

# CLI mode
python main.py

# HTTP server for AI Toolkit Agent Inspector
python server.py
```

### 4. Generate Your First Book

1. Open the Streamlit app at `http://localhost:8501`
2. In the chat, type: *"Quiero un libro sobre los animales del océano para niños de 9 años en México"*
3. The assistant collects remaining parameters, then generates curriculum, chapters, images, and audio
4. Download the result as HTML, PDF, Markdown, or listen to the audiobook directly in the browser

---

## 🎬 Demo

### 📺 Watch the Full Demo

[![LATAM Book Generator — Full Demo](https://img.youtube.com/vi/Tr-6JnxO-9k/maxresdefault.jpg)](https://www.youtube.com/watch?v=Tr-6JnxO-9k)

> *Click the thumbnail to watch the complete walkthrough on YouTube — live book generation, voice narration, AI illustrations, and export in action.*

---

### Chat-Driven Generation

```
You:   "I want a book about space exploration for 10-year-olds in Colombia"
Agent: Clarifying questions about learning method, number of chapters, voice preferences
Agent: Confirms all parameters and emits book_request_json
→ Pipeline generates a complete book: curriculum + chapters + images + audio narration
```

### Voice Cloning Workflow

```
1. Record a 10-second voice sample using the sidebar microphone
2. Click "Clone & Save" to enroll a persistent voice profile
3. Generate audiobook — narrated entirely in YOUR voice
4. Download as ZIP with all chapter audio files
```

### Output Preview

A generated book includes:
- 📄 **HTML** — Interactive styled book viewable in any browser
- 📕 **PDF** — Print-ready with proper pagination and Unicode
- 📝 **Markdown** — Portable format with embedded images
- 🎧 **Audio** — Chapter-by-chapter WAV narration files
- 📊 **JSON** — Structured data for programmatic access

---

## 📁 Project Structure

```
Agent-Framework/
├── app.py                  # Streamlit UI — main application
├── main.py                 # CLI workflow runner
├── server.py               # HTTP server for AI Toolkit Agent Inspector
├── config.py               # Multi-provider model configuration
├── requirements.txt        # Python dependencies
├── .env                    # API keys (not committed)
│
├── agents/                 # 16 specialized AI agents
│   ├── chat_agent.py              # Conversational book design
│   ├── curriculum_agent.py        # Curriculum structure generation
│   ├── chapter_agent.py           # Chapter content writing
│   ├── voice_curriculum_agent.py  # Audio-first curriculum
│   ├── voice_chapter_agent.py     # Voice-optimized chapters
│   ├── audio_book_script_agent.py # Chapter → narration script
│   ├── voice_agent.py             # TTS synthesis (10 voices)
│   ├── voice_clone_agent.py       # Voice cloning enrollment & synthesis
│   ├── qwen_image_agent.py        # AI image generation
│   ├── ddg_image_search_agent.py  # Web image search
│   ├── youtube_search_agent.py    # YouTube video search + QR
│   ├── fact_check_agent.py        # Web-search fact verification
│   ├── latex_math_agent.py        # LaTeX/KaTeX math content
│   ├── html_css_agent.py          # HTML book renderer
│   ├── html_to_pdf_converter.py   # PDF generator (fpdf2)
│   └── markdown_agent.py          # Markdown exporter
│
├── models/                 # Data schemas & i18n
│   ├── book_spec.py               # Pydantic models (BookRequest, Curriculum, etc.)
│   ├── template_registry.py       # 10 visual book templates
│   └── i18n.py                    # 11-language string tables
│
├── templates/              # HTML/CSS book templates
│   ├── master_book.html
│   ├── storybook-template.html
│   ├── math.html
│   └── ...
│
├── utils/                  # Shared utilities
│   ├── retry.py                   # Async/sync retry with exponential backoff
│   └── math_latex.py              # LaTeX rendering helpers
│
├── tests/                  # Test suite
│   ├── test_chat_agent_contracts.py
│   ├── test_math_book.py
│   └── test_retry.py
│
├── books/                  # Generated output (gitignored)
│   ├── json/               # Structured book data
│   ├── html/               # Interactive HTML books
│   ├── md/                 # Markdown exports
│   ├── pdf/                # Print-ready PDFs
│   ├── audio/              # Chapter narration WAV files
│   ├── images/             # AI-generated illustrations
│   └── voice_clones/       # Persistent cloned-voice profiles
│
└── docs/                   # Extended documentation
    ├── INDEX.md
    ├── ARCHITECTURE.md
    ├── AGENTS_REFERENCE.md
    ├── SETUP.md
    └── USER_GUIDE.md
```

---

## 🛡️ Reliability & Safety

| Practice | Implementation |
|----------|---------------|
| **Retry Logic** | Exponential backoff with jitter for all API calls (`utils/retry.py`) |
| **Type Safety** | Pydantic v2 models for all data flowing between agents |
| **API Key Validation** | Preflight checks before any long-running generation |
| **Session Persistence** | Streamlit session state survives page reruns |
| **Error Isolation** | Each agent fails gracefully without crashing the pipeline |
| **Safe Search** | DuckDuckGo SafeSearch for child-appropriate image results |
| **Content Verification** | Optional fact-checking agent validates educational claims |
| **No Hardcoded Secrets** | All credentials via `.env` and environment variables |
| **Diagnostic Logging** | Structured logging for TTS, image generation, and API calls |
| **Tracing** | OpenTelemetry + AI Toolkit integration for distributed debugging |

---

## 🔧 Technical Highlights

- **Agent-as-Server Pattern** — `server.py` wraps the book planner agent as an HTTP server compatible with Microsoft AI Toolkit Agent Inspector for visual debugging and tracing
- **4 Provider Abstraction** — `config.py` resolves the correct endpoint, API key, and model ID at runtime for GitHub Models, Qwen/DashScope (Singapore · Beijing · US-Virginia), Anthropic Claude, and Azure OpenAI — eliminating per-agent provider logic
- **Smart Template Selection** — The LLM auto-selects the best visual template based on topic analysis rather than defaulting to a single style
- **Intelligent Image Prompting** — The text LLM generates structured image prompts (camera angle, lighting, art style, resolution) rather than plain descriptions, improving generation quality
- **WAV Audio Concatenation** — Properly extracts PCM frames from chunked TTS responses and re-wraps with correct WAV headers — not naive byte concatenation
- **Voice Profile Registry** — Persistent JSON registry stores cloned voice IDs and enrollment audio for reuse across sessions
- **Chat Memory** — 20-exchange rolling conversation history enables coherent multi-turn book design
- **i18n Engine** — String tables covering 11 languages with RTL support detection

---

## 🧪 Testing

```bash
# Run the full test suite
python -m pytest tests/ -v

# Test agent data contracts
python -m pytest tests/test_chat_agent_contracts.py -v

# Test retry / backoff logic
python -m pytest tests/test_retry.py -v

# Test math book generation end-to-end
python -m pytest tests/test_math_book.py -v
```

---

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| `st.audio_input` not found | Streamlit is too old: `pip install --upgrade streamlit>=1.54.0` |
| Chat completes but form values are used | Check that the generation source indicator says "chat" — the chat JSON overrides form fields |
| Voice cloning fails silently | Confirm `DASHSCOPE_API_KEY` is set and the DashScope account has TTS-VC quota |
| Images not generating | Set `DASHSCOPE_API_KEY` and select a Qwen image model in the sidebar |
| PDF missing characters | Expected for CJK / Arabic scripts — use HTML export for full Unicode fidelity |
| Tracing errors in the console | Normal when no OTLP collector is running — set `AITK_TRACING_ENABLED=0` to suppress |
| `agent-framework` package not found | Ensure you're using Python 3.12+ and the virtual environment is activated |
| DashScope 429 / rate limit | Switch Qwen region in sidebar (Singapore → Beijing → US-Virginia) or add backoff |

---

## 🚧 Known Issues & Work in Progress

These are active limitations that are known and being tracked:

| Area | Issue | Status |
|------|-------|--------|
| **DDG Image Search** | `ddg_image_search_agent.py` is functional but **does not meet production quality standards** — DuckDuckGo returns inconsistent results, has no relevance ranking, and the API is undocumented/unofficial. Used as a fallback only. | ⚠️ Needs replacement |
| **DDG Video Search** | Same constraints as image search — YouTube results via DuckDuckGo are unreliable and miss the most relevant educational content. | ⚠️ Needs replacement |
| **PDF Blocking** | PDF generation (`html_to_pdf_converter.py`) runs synchronously and blocks the Streamlit UI thread during export for large books. | 🔄 In progress |
| **`app.py` Size** | The Streamlit UI file is 2,600+ lines — it handles all tabs (chat, form, voice, batch, settings) in a single module, making it harder to maintain as features grow. | 🔄 Planned refactor |
| **Test Coverage** | Integration tests for the full book generation pipeline and golden-file tests for HTML templates are missing. Unit tests exist only for retry logic and chat agent contracts. | 🔄 Expanding |
| **Voice Clone Quota** | `qwen3-tts-vc` voice cloning requires a DashScope account with TTS-VC quota enabled — it silently degrades to standard TTS when quota is absent. | 📋 Known behavior |
| **CJK / RTL in PDF** | Unicode characters outside Latin script (Arabic, Chinese, Japanese) render as blank boxes in the PDF output. Use HTML export for full Unicode fidelity. | 📋 Known limitation |

---

## 🗺️ Roadmap & Future Improvements

Planned enhancements ordered by impact:

### 🔍 Search — Replace DDG with Azure AI Agents + Bing

The current DuckDuckGo implementation for both image and YouTube search is a temporary stand-in. The planned replacement is **Bing Search via Azure AI Agents**, which provides:

- Ranked, high-confidence image results with licensing metadata
- Proper YouTube video relevance scoring with educational topic matching
- Azure-grade reliability, SLA, and rate limits
- Seamless integration with the existing Azure AI provider already in `config.py`

```python
# Planned: agents/bing_image_search_agent.py
# Planned: agents/bing_video_search_agent.py
# Using: azure-ai-projects + BingGroundingTool
```

This is the **highest-priority search improvement** — DDG quality is the weakest link in the current pipeline.

---

### ⚛️ React Frontend

Streamlit is excellent for prototyping but has real limits at production scale: no fine-grained component control, limited real-time streaming, no code splitting, and a Python-locked rendering model. A React frontend would unlock:

| Capability | Streamlit Today | React Target |
|------------|----------------|--------------|
| Real-time chapter streaming | `st.write_stream()` (limited) | Server-Sent Events / WebSocket |
| Book preview | iFrame embed | Full interactive renderer |
| Audio playback UI | Basic `st.audio` | Custom waveform + chapter timeline |
| Mobile responsiveness | Limited | Full responsive layouts |
| Routing / multi-page | `st.navigation()` | React Router |
| Component reuse | Copy-paste | Composable component library |

The existing `server.py` HTTP backend is already structured to serve as a headless API — a React frontend would consume it directly.

---

### 🐳 Docker Compose Deployment

A `docker-compose.yml` with a Python service (app + server) and optional OTLP collector for tracing would make the project runnable without Python/venv setup.

### 🧪 Expanded Test Suite

- Golden-file tests for HTML template rendering
- End-to-end generation pipeline integration tests with mocked LLM responses
- Snapshot tests for Pydantic schema evolution

### 📦 `app.py` Modularization

Split the 2,600-line `app.py` into per-tab Streamlit page modules:

```
pages/
  01_chat.py        ← Chat-driven book design
  02_form.py        ← Manual form mode
  03_voice.py       ← Voice cloning & audiobook
  04_batch.py       ← Batch generator
  05_settings.py    ← Provider config & API keys
```

### 🌐 Additional Language Support

Extend i18n beyond the current 11 languages — particularly Quechua, Guaraní, and Haitian Creole for broader LATAM coverage.

---

## 🏆 Agents League Submission

**Track**: Creative Apps

**Key Technologies**:

| Technology | Role |
|------------|------|
| Microsoft Agent Framework | Multi-agent orchestration backbone |
| GitHub Models (gpt-4o-mini) | Text generation — free tier development |
| Qwen/DashScope | Text, image generation, TTS Flash/Instruct, voice cloning |
| Anthropic Claude | Optional high-quality text generation provider |
| Azure OpenAI | Optional enterprise text generation provider |
| Streamlit 1.54+ | Interactive UI with real-time audio recording |
| OpenTelemetry + AI Toolkit | Distributed tracing and visual debugging |
| Pydantic v2 | Typed data contracts across all agents |
| fpdf2 | Pure-Python PDF generation with Unicode support |
| KaTeX | Client-side LaTeX math rendering |

---

## 🤖 Built with GitHub Copilot

Curious how this project was built? Read the [Copilot Story](COPILOT_STORY.md) — an honest account of how GitHub Copilot acted as a co-author at every stage: architecture design, Pydantic schema generation, WAV audio handling, multi-provider abstraction, and more.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ for LATAM education
</p>
