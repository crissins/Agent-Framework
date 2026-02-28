<p align="center">
  <img src="https://img.shields.io/badge/Agents%20League-Creative%20Apps-blueviolet?style=for-the-badge&logo=microsoft" alt="Agents League Creative Apps" />
  <img src="https://img.shields.io/badge/Microsoft-Agent%20Framework-0078D4?style=for-the-badge&logo=microsoft" alt="Microsoft Agent Framework" />
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License" />
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
  <a href="docs/INDEX.md">Full Docs</a>
</p>

---

## 🎯 Why This Matters

**350 million children** in Latin America deserve educational content that reflects their culture, language, and reality. Yet most AI-generated educational material is US/Euro-centric and English-only.

**LATAM Book Generator** solves this by orchestrating **12+ specialized AI agents** into a production pipeline that produces **complete, publication-ready educational books** — tailored to specific countries, age groups, and pedagogical methods — in Spanish, Portuguese, or English — with AI illustrations, audiobook narration, and even **voice cloning** so a parent or teacher can narrate in their own voice.

### What Makes This Special

| Dimension | What We Built |
|-----------|--------------|
| **Multi-Agent Orchestration** | 12+ specialized agents collaborating sequentially — curriculum design, chapter writing, image generation, TTS, fact-checking — each with a focused role |
| **Cultural Intelligence** | Country-specific content for Mexico, Colombia, Argentina, Chile, Peru, Brazil with local references and i18n support for 11 languages |
| **Multimodal Output** | Text → HTML → PDF → Markdown → Audiobook → Images → QR-embedded videos — all from a single natural-language prompt |
| **Voice Cloning** | Record your voice, clone it, and generate full audiobooks narrated in your own voice using Qwen3 TTS-VC |
| **Conversational UX** | Chat naturally with the AI assistant to design your book — no forms required |
| **Production-Ready** | HTTP server mode, AI Toolkit tracing, retry logic with exponential backoff, typed Pydantic schemas, session persistence |

---

## ✨ Features

### 📖 Full Book Generation Pipeline
From a single topic description, the system orchestrates multiple AI agents to produce:

- **Structured Curriculum** — Age-appropriate chapter outlines following Scandinavian, Montessori, or Project-Based pedagogy
- **Rich Chapter Content** — Educational text with activities, reflection questions, experiments, and cultural references
- **AI Illustrations** — Generated via Qwen-Image-Plus/Max with intelligent prompt engineering (auto-selects art style, camera angle, lighting, resolution)
- **Web Image Search** — DuckDuckGo SafeSearch fallback for royalty-free educational images
- **YouTube Video Embeds** — Relevant educational videos with auto-generated QR codes for print books
- **LaTeX Math Support** — Rich mathematical notation rendered via KaTeX for STEM content
- **Fact-Checking** — Web search-powered verification of educational claims with confidence scoring

### 🎙️ Audiobook Generation
- **10 Voice Options** — Male, female, and child voices via Qwen3 TTS-VC
- **Voice Cloning** — Record a sample, enroll a persistent voice profile, narrate entire books in your voice
- **Audio Script Optimization** — AI transforms chapter markdown into narration-ready scripts with pause markers
- **Audio-Only Mode** — Skip visual output entirely and produce pure audiobooks with voice-first curriculum design
- **Adjustable Speech Rate** — 0.5x to 2.0x speed control optimized for educational content

### 🎨 10 Visual Templates
Curated CSS/JS book templates with automatic selection:

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
| **Audio ZIP** | All chapter narrations bundled as downloadable archive |

### 💬 Conversational Interface
A chat-based AI assistant that:
- Collects all book parameters through natural conversation
- Maintains memory across 20+ exchanges
- Emits structured `book_request_json` when complete
- Supports switching between GitHub Models and Qwen mid-conversation
- Responds in the user's language automatically

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Streamlit UI (app.py)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Chat Mode│  │Form Mode │  │Voice Mode│  │ Settings Panel │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────────────┘  │
│       └──────────────┴─────────────┘                            │
│                      │                                          │
├──────────────────────▼──────────────────────────────────────────┤
│              Agent Orchestration Layer (12+ Agents)              │
│                                                                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐ │
│  │ Chat Agent │ │ Curriculum │ │  Chapter   │ │ Voice Agents │ │
│  │            │ │   Agent    │ │   Agent    │ │ (5 modules)  │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────────┘ │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐ │
│  │ Qwen Image │ │ DDG Search │ │YouTube + QR│ │ Fact Check   │ │
│  │ Generator  │ │            │ │   Agent    │ │   Agent      │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────────┘ │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                    Export & Rendering Layer                       │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────────────┐ │
│  │ HTML │  │ PDF  │  │  MD  │  │ JSON │  │ Audio ZIP        │ │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────────────────┘ │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│              Flexible Model Providers (config.py)                │
│  ┌──────────────────┐  ┌──────────────────────────────────────┐ │
│  │ GitHub Models     │  │ Qwen via DashScope                  │ │
│  │ (gpt-4o-mini)     │  │ Text · Image · TTS · Voice Clone   │ │
│  │ Free dev tier     │  │ Singapore · Beijing · US-Virginia   │ │
│  └──────────────────┘  └──────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
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
| **Voice Agent** | `agents/voice_agent.py` | Standard TTS via Qwen3 TTS-VC (10 voices) |
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

All agents communicate through **typed Pydantic schemas** (`models/book_spec.py`):

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
- At least one API key (see below)

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
# At least one is required
GITHUB_TOKEN=ghp_your_github_token_here
DASHSCOPE_API_KEY=sk-your_dashscope_key_here

# Optional: Enable AI Toolkit tracing
AITK_TRACING_ENABLED=0
```

| Key | Source | Used For |
|-----|--------|----------|
| `GITHUB_TOKEN` | [github.com/settings/tokens](https://github.com/settings/tokens) | Text generation (free tier) |
| `DASHSCOPE_API_KEY` | [dashscope.aliyun.com](https://dashscope.aliyun.com/) | Text, images, TTS, voice cloning |

### 3. Run

```bash
# Streamlit UI (recommended)
python -m streamlit run app.py

# CLI mode
python main.py

# HTTP server (AI Toolkit Agent Inspector)
python server.py
```

### 4. Generate Your First Book

1. Open the Streamlit app at `http://localhost:8501`
2. Chat: *"Quiero un libro sobre los animales del océano para niños de 9 años en México"*
3. The assistant designs the curriculum, writes chapters, generates images and audio
4. Download as HTML, PDF, Markdown, or listen to the audiobook directly in the browser

---

## 🎬 Demo

### Chat-Driven Generation
```
You:   "I want a book about space exploration for 10-year-olds in Colombia"
Agent: Asks clarifying questions about learning method, chapters, voice preferences
Agent: Confirms all parameters and emits book_request_json
→ System generates complete book with curriculum, chapters, images, and audio
```

### Voice Cloning Workflow
```
1. Record a 10-second voice sample in the sidebar
2. Click "Clone & Save" to enroll the voice profile
3. Generate audiobook — narrated in YOUR voice
4. Download as ZIP with all chapter audio files
```

### Output Example
A generated book includes:
- 📄 **HTML** — Interactive styled book viewable in any browser
- 📕 **PDF** — Print-ready with proper pagination and Unicode
- 📝 **Markdown** — Portable format with embedded images
- 🎧 **Audio** — Chapter-by-chapter narration files
- 📊 **JSON** — Structured data for programmatic access

---

## 📁 Project Structure

```
Agent-Framework/
├── app.py                  # Streamlit UI — main application (1600+ lines)
├── main.py                 # CLI workflow runner
├── server.py               # HTTP server for AI Toolkit Agent Inspector
├── config.py               # Model provider configuration & API key management
├── requirements.txt        # Pinned dependencies
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
├── models/                 # Data schemas & templates
│   ├── book_spec.py               # Pydantic models (BookRequest, Curriculum, etc.)
│   ├── template_registry.py       # 10 visual book templates
│   └── i18n.py                    # 11-language internationalization
│
├── templates/              # HTML/CSS book templates
│   ├── master_book.html
│   ├── storybook-template.html
│   ├── math.html
│   └── ...
│
├── utils/                  # Shared utilities
│   └── retry.py                   # Async/sync retry with exponential backoff
│
├── tests/                  # Test suite
│   ├── test_chat_agent_contracts.py
│   └── test_retry.py
│
├── books/                  # Generated output (gitignored)
│   ├── json/               # Structured book data
│   ├── html/               # Interactive HTML books
│   ├── md/                 # Markdown exports
│   ├── pdf/                # Print-ready PDFs
│   ├── audio/              # Chapter narration files
│   ├── images/             # AI-generated illustrations
│   └── voice_clones/       # Persistent voice profiles
│
└── docs/                   # Documentation
    ├── INDEX.md
    ├── ARCHITECTURE.md
    ├── AGENTS_REFERENCE.md
    └── ...
```

---

## 🛡️ Reliability & Safety

| Practice | Implementation |
|----------|---------------|
| **Retry Logic** | Exponential backoff with jitter for all API calls (`utils/retry.py`) |
| **Type Safety** | Pydantic models for all data flow between agents |
| **API Key Validation** | Preflight checks before any long-running generation |
| **Session Persistence** | Streamlit session state survives page reruns |
| **Error Isolation** | Each agent fails gracefully without crashing the pipeline |
| **Safe Search** | DuckDuckGo SafeSearch for child-appropriate image results |
| **Content Verification** | Optional fact-checking agent validates educational claims |
| **No Hardcoded Secrets** | All keys via `.env` and environment variables |
| **Diagnostic Logging** | Structured logging for TTS, image gen, and API calls |
| **Tracing** | OpenTelemetry integration with AI Toolkit for debugging |

---

## 🔧 Technical Highlights

- **Agent-as-Server Pattern**: `server.py` wraps the book planner agent as an HTTP server compatible with Microsoft AI Toolkit Agent Inspector for visual debugging
- **Smart Template Selection**: AI auto-picks the best visual template based on book topic analysis
- **Intelligent Image Prompting**: The text LLM generates image prompts with camera angle, lighting, style, and resolution parameters — not just descriptions
- **WAV Audio Concatenation**: Properly extracts PCM frames from chunked TTS outputs and re-wraps with correct WAV headers (not naive byte concatenation)
- **Voice Profile Registry**: Persistent JSON-based registry for cloned voices with sample storage and reuse
- **Chat Memory**: 20-exchange rolling conversation history for coherent multi-turn book design
- **i18n Engine**: String tables for 11 languages with RTL support detection

---

## 🧪 Testing

```bash
# Run test suite
python -m pytest tests/ -v

# Test specific agent contracts
python -m pytest tests/test_chat_agent_contracts.py -v

# Test retry logic
python -m pytest tests/test_retry.py -v
```

---

## 🔍 Troubleshooting

| Issue | Solution |
|-------|----------|
| `st.audio_input` not found | Upgrade Streamlit: `pip install streamlit>=1.54.0` |
| Chat works but form values used | Ensure generation source shows "chat" — the chat JSON overrides form |
| Voice cloning fails | Confirm `DASHSCOPE_API_KEY` is set and valid |
| Images not generating | Set `DASHSCOPE_API_KEY` and select Qwen image model in sidebar |
| PDF missing characters | Expected for non-Latin scripts — use HTML export for full Unicode |
| Tracing errors in console | Normal if no OTLP collector running — suppressed by default |

---

## 🏆 Agents League Submission

**Track**: Creative Apps

**Key Technologies**:
- Microsoft Agent Framework (multi-agent orchestration)
- GitHub Models (gpt-4o-mini — free tier development)
- Qwen/DashScope (text, image generation, TTS, voice cloning)
- Streamlit (interactive UI)
- OpenTelemetry + AI Toolkit (observability & debugging)
- Pydantic (typed data contracts)
- fpdf2 (PDF generation)

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ for LATAM education
</p>
