# Setup & Configuration Guide

## Prerequisites

- **Python 3.12+** (required)
- **Git** (for cloning)
- At least one API key (see below — GitHub Models is free and works out of the box)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/crissins/Agent-Framework.git
cd Agent-Framework
```

### 2. Create Virtual Environment

```bash
# Create
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Windows CMD)
.venv\Scripts\activate.bat

# Activate (macOS/Linux)
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API Keys

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

Then edit `.env` — at minimum set `GITHUB_TOKEN` to get started immediately for free.

---

## API Key Configuration

The app supports **4 model providers**. You can switch between them in the sidebar — no restart needed.

### Provider Comparison

| Provider | Key Variable | Free Tier | Best For |
|----------|-------------|-----------|----------|
| **GitHub Models** | `GITHUB_TOKEN` | ✅ Free | Development, testing |
| **Qwen (DashScope)** | `DASHSCOPE_API_KEY` | ✅ Free tier | Production, images, TTS |
| **Claude (Anthropic)** | `ANTHROPIC_API_KEY` | ❌ Paid | High-quality reasoning |
| **Azure AI Foundry** | `AZURE_OPENAI_API_KEY` + endpoint | ❌ Paid | Enterprise, compliance |

### Getting API Keys

#### GitHub Token (Free — start here)
1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click **Generate new token (classic)**
3. Select `read:packages` scope
4. Copy token → paste into `GITHUB_TOKEN`

#### DashScope — Qwen + Images + TTS (Free tier)
1. Visit [dashscope.aliyun.com](https://dashscope.aliyun.com/)
2. Sign up for a free account
3. Create API key (format: `sk-xxxxx...`)
4. Copy → paste into `DASHSCOPE_API_KEY`
5. Choose your region (`singapore` recommended outside China)

#### Anthropic Claude (Paid)
1. Visit [console.anthropic.com](https://console.anthropic.com/)
2. Create an API key
3. Copy → paste into `ANTHROPIC_API_KEY`

#### Azure AI Foundry (Paid / Enterprise)
1. Create a resource in [ai.azure.com](https://ai.azure.com/)
2. Deploy a model (e.g., `gpt-4o`)
3. Copy the endpoint URL → `AZURE_OPENAI_ENDPOINT`
4. Copy the API key → `AZURE_OPENAI_API_KEY`
5. Set deployment name → `AZURE_OPENAI_DEPLOYMENT_NAME`

### Feature-to-Key Mapping

| Feature | Required Key(s) |
|---------|----------------|
| Text generation | `GITHUB_TOKEN` OR `DASHSCOPE_API_KEY` OR `ANTHROPIC_API_KEY` OR Azure keys |
| AI image generation | `DASHSCOPE_API_KEY` (Qwen) or Azure DALL-E deployment |
| TTS narration | `DASHSCOPE_API_KEY` |
| Voice cloning | `DASHSCOPE_API_KEY` |
| Web image search | None (DuckDuckGo, free) |
| YouTube search | None (DuckDuckGo, free) |
| QR code generation | None (local `qrcode` library) |

---

## Running the Application

### Streamlit UI (Recommended)

```bash
# Windows — one-click launcher
run_app.bat

# Any OS
python -m streamlit run app.py
```

Opens at `http://localhost:8501`

You can enter API keys directly in the sidebar **🧠 Model** expander if you haven't set up `.env` yet. Keys entered in the UI can be saved to `.env` with the **💾 Save to .env** button.

### CLI Mode

```bash
python main.py
```

Interactive terminal-based book generation using GitHub Models.

### HTTP Server (AI Toolkit Agent Inspector)

```bash
# Basic
python server.py

# With AI Toolkit debugger (recommended for development)
agentdev run server.py --verbose --port 8087
```

Then open VS Code and press **F5** (→ "Debug Agent HTTP Server") to connect the AI Toolkit Agent Inspector.

---

## Configuration Reference

### Model Settings (🧠 Model expander in sidebar)

| Setting | Options | Default |
|---------|---------|---------|
| Provider | GitHub / Qwen / Claude / Azure | GitHub |
| GitHub text model | gpt-4o-mini / gpt-4o / Llama / Mistral | gpt-4o-mini |
| Qwen region | Singapore / Beijing / US-Virginia | Singapore |
| Qwen text model | qwen-flash / qwen-plus / qwen-max / qwen3-max | qwen-flash |
| Qwen image model | qwen-image-plus / qwen-image-max variants | qwen-image-plus |
| Claude text model | claude-3-5-haiku / claude-3-5-sonnet / claude-3-7-sonnet | claude-3-5-haiku |
| Azure deployment | Your custom deployment name | gpt-4o |
| Azure image model | dall-e-3 / dall-e-2 / gpt-4o / qwen-image-plus | dall-e-3 |

### Voice Settings (🎙️ Voice expander in sidebar)

| Setting | Options | Default |
|---------|---------|---------|
| Enable TTS | On/Off | Off |
| Voice | 10 options (male/female/child) | longxiaochun |
| Audio format | WAV 24k / 16k / 22k | WAV 24k |
| Speech rate | 0.5x – 2.0x | 0.95x |
| Voice cloning | Record sample → save profile | Off |

### Image Settings (🖼️ Images & Video expander)

| Setting | Options | Default |
|---------|---------|---------|
| Image source | AI Generate / DDG Search / None | None |
| Images per chapter | 0–5 | 0 |
| Art style | 12 options + auto | auto |
| Video search | On/Off | Off |

---

## Tracing & Debugging

### Enable AI Toolkit Tracing

```env
AITK_TRACING_ENABLED=1
ENABLE_SENSITIVE_DATA=true   # capture prompts/completions (dev only)
```

Exports OpenTelemetry traces to port 4317 — visible in the VS Code AI Toolkit Agent Inspector.

### Enable Verbose TTS Logging

```env
TTS_DEBUG=1
```

### VS Code F5 Debugging

Pre-configured launch configurations in `.vscode/launch.json`:
- **Debug Agent HTTP Server** — starts `server.py` with debugpy + opens Agent Inspector
- **Debug Agent CLI Mode** — CLI mode with debugger attached

Press F5 and select a configuration. No additional setup needed.
