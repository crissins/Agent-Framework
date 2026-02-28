# Architecture

## System Overview

LATAM Book Generator is a **multi-agent AI pipeline** built on Microsoft Agent Framework. It orchestrates 12+ specialized agents through a Streamlit UI to produce complete educational books from a single natural-language prompt.

## Design Principles

1. **Single Responsibility** — Each agent handles one task (curriculum, chapters, images, audio, etc.)
2. **Sequential Orchestration** — Agents execute in a defined pipeline with typed data handoffs
3. **Fault Isolation** — Individual agent failures don't crash the pipeline; fallbacks are applied
4. **Provider Flexibility** — Swap between GitHub Models, Qwen, Claude, and Azure AI Foundry without code changes
5. **Type Safety** — Pydantic schemas enforce data contracts between agents

## Pipeline Flow

### Full Book Generation

```
User Input (chat or form)
    │
    ▼
┌─────────────────┐
│   Chat Agent    │ ← Conversational requirement gathering
│   (optional)    │    Emits book_request_json
└────────┬────────┘
         ▼
┌─────────────────┐
│ Curriculum Agent│ ← Designs chapter outlines
│                 │    Follows selected pedagogy (Montessori, etc.)
└────────┬────────┘
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Chapter Agent  │────▶│  Image Agent    │ ← Per-chapter AI illustrations
│  (per chapter)  │     │  (optional)      │
└────────┬────────┘     └─────────────────┘
         │              ┌─────────────────┐
         ├─────────────▶│  DDG Search     │ ← Web image fallback
         │              └─────────────────┘
         │              ┌─────────────────┐
         ├─────────────▶│  YouTube + QR   │ ← Video discovery
         │              └─────────────────┘
         │              ┌─────────────────┐
         ├─────────────▶│  TTS Agent      │ ← Audio narration
         │              │  or Voice Clone │
         │              └─────────────────┘
         │              ┌─────────────────┐
         └─────────────▶│  Fact Checker   │ ← Content verification
                        └─────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│         Export Layer                 │
│  HTML │ PDF │ Markdown │ JSON │ ZIP │
└─────────────────────────────────────┘
```

### Audio-Only Mode

Uses voice-optimized agents (`voice_curriculum_agent`, `voice_chapter_agent`) that produce spoken-flow content, then pipes through `audio_book_script_agent` for narration optimization before TTS synthesis.

## Model Provider Architecture

All providers share the same `OpenAIChatClient` interface. The active provider is resolved via the `MODEL_PROVIDER` environment variable or the sidebar selector — no code changes needed to switch.

```python
# config.py — Provider-agnostic configuration
config = get_model_config(provider="github")  # or qwen / claude / azure
# Returns: { api_key_env, base_url, model_id, description }
```

| Provider | Env Var | Base URL | Notes |
|----------|---------|----------|-------|
| **GitHub Models** | `GITHUB_TOKEN` | `https://models.inference.ai.azure.com` | Free tier, great for dev |
| **Qwen/DashScope** | `DASHSCOPE_API_KEY` | `dashscope-intl.aliyuncs.com` | Free tier, best TTS+image |
| **Claude (Anthropic)** | `ANTHROPIC_API_KEY` | `https://api.anthropic.com/v1` | Paid, stronger reasoning |
| **Azure AI Foundry** | `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_DEPLOYMENT_NAME` | Dynamic from env | Enterprise, compliance |

The `MODEL_PROVIDER` env var accepts `github` / `qwen` / `claude` / `azure`. The `use_qwen_models` flag is kept for backward compatibility but `MODEL_PROVIDER` takes priority.

## Session Management

Streamlit session state maintains:
- Chat conversation history (20+ turns)
- Generated book artifacts (paths to JSON/HTML/PDF/audio)
- Voice clone profiles and recordings
- Runtime configuration overrides from chat
- Pending generation triggers (chat-initiated auto-generation)

## Retry & Resilience

All API calls use the `utils/retry.py` decorators:
- `@async_retry(max_retries=3, base_delay=5.0)` — for async agent calls
- `@sync_retry(max_retries=3, base_delay=5.0)` — for sync API calls (DashScope)
- Exponential backoff with jitter to avoid thundering herd
- Configurable `max_delay` ceiling

## Observability

When `AITK_TRACING_ENABLED=1`:
- OpenTelemetry traces exported to AI Toolkit on port 4317
- Full prompt/completion capture for debugging
- Compatible with VS Code AI Toolkit Agent Inspector
- Noisy OTLP exporter logs suppressed by default
