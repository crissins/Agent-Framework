#!/usr/bin/env python3
"""
Streamlit application for LATAM book generation.
Integrates Microsoft Agent Framework with best practices:
- Proper error handling and user feedback
- Structured logging
- Clean separation of concerns
- Qwen-Image-Max for AI-powered illustrations
"""
import asyncio
import json
import os
import re
import sys
import time
import hashlib
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding for emoji/unicode in print() statements
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
import streamlit as st
from dotenv import load_dotenv
from models.book_spec import BookRequest, Curriculum, ChapterContent, BookOutput, AudioNarration
from config import validate_api_keys, TTS_MODELS, TTS_VOICES, TTS_AUDIO_FORMATS, VC_MODELS
from models.template_registry import template_choices, list_template_ids, get_template, auto_pick_template

# Import agents
from agents.curriculum_agent import create_curriculum_agent, generate_curriculum
from agents.chapter_agent import create_chapter_agent, generate_chapter
from agents.qwen_image_agent import generate_chapter_image
from agents.html_css_agent import generate_html_css_book_from_json
from agents.markdown_agent import save_markdown_book
from agents.html_to_pdf_converter import generate_pdf_from_data
from agents.ddg_image_search_agent import search_and_download_image
from agents.youtube_search_agent import search_videos_for_chapter
from agents.voice_agent import narrate_chapter, COSYVOICE_VOICES
from agents.chat_agent import create_chat_agent, parse_book_request_from_response, build_book_request
from agents.voice_clone_agent import create_voice as create_cloned_voice
from agents.voice_clone_agent import narrate_chapter_vc
from agents.audio_book_script_agent import generate_audio_script, prepare_script_for_tts
from agents.voice_curriculum_agent import create_voice_curriculum_agent, generate_voice_curriculum
from agents.genre_agents import generate_genre_book_async as _generate_genre_book_async
from models.book_spec import BOOK_GENRES
from agents.batch_generator import (
    BatchJobSpec, run_batch_parallel,
    PROVIDER_MODELS, PROVIDER_LABELS,
)
from agents.voice_chapter_agent import create_voice_chapter_agent, generate_voice_chapter

# Load environment variables
load_dotenv()

# Configure OpenTelemetry tracing for AI Toolkit integration (opt-in)
# Suppress noisy OTLP exporter errors when no local collector is running
import logging as _logging
for _otlp_logger_name in (
    "opentelemetry.exporter.otlp.proto.grpc.exporter",
    "opentelemetry.exporter.otlp.proto.grpc",
    "opentelemetry.exporter.otlp",
):
    _logging.getLogger(_otlp_logger_name).setLevel(_logging.CRITICAL)

# ── Audio / TTS diagnostic logging ────────────────────────────────────────
# Ensure TTS-related loggers output to console so audio issues are visible
_audio_log_level = _logging.DEBUG if os.getenv("TTS_DEBUG", "0") == "1" else _logging.INFO
_console_handler = _logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
))
for _tts_logger_name in (
    "agents.voice_agent",
    "agents.voice_clone_agent",
    "agents.audio_book_script_agent",
    "audiobook_pipeline",
    "utils.retry",
):
    _tts_logger = _logging.getLogger(_tts_logger_name)
    _tts_logger.setLevel(_audio_log_level)
    if not _tts_logger.handlers:
        _tts_logger.addHandler(_console_handler)
print(f"🔊 TTS diagnostic logging enabled (level={'DEBUG' if _audio_log_level == _logging.DEBUG else 'INFO'})")

_tracing_enabled = os.getenv("AITK_TRACING_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
if _tracing_enabled:
    try:
        from agent_framework.observability import configure_otel_providers
        configure_otel_providers(
            vs_code_extension_port=4317,  # AI Toolkit gRPC port
            enable_sensitive_data=True,    # Capture prompts and completions for debugging
        )
        print("✅ AI Toolkit tracing enabled (AITK_TRACING_ENABLED=1)")
    except Exception as e:
        print(f"⚠️ Tracing disabled due to setup/runtime error: {e}", file=sys.stderr)

st.set_page_config(page_title="📚 LATAM Book Generator", layout="wide")
st.title("📚 LATAM Book Generator")

# === Initialize session state ===
st.session_state.setdefault("book_generated", False)
st.session_state.setdefault("json_path", None)
st.session_state.setdefault("html_path", None)
st.session_state.setdefault("md_path", None)
st.session_state.setdefault("pdf_path", None)
st.session_state.setdefault("output_data", None)
st.session_state.setdefault("curriculum", None)
st.session_state.setdefault("full_chapters", None)
st.session_state.setdefault("audio_narrations", [])
st.session_state.setdefault("audio_output_dir", None)
st.session_state.setdefault("gen_time", None)
st.session_state.setdefault("gen_tokens_est", None)
st.session_state.setdefault("gen_model", None)

# Batch generation session state
st.session_state.setdefault("batch_results", None)    # list[BatchJobResult] | None
st.session_state.setdefault("batch_running", False)
st.session_state.setdefault("batch_status", {})       # live status dict from run_batch_parallel
st.session_state.setdefault("color_friendly_path", None)
st.session_state.setdefault("enable_tts", True)

# Chat session state
st.session_state.setdefault("chat_messages", [])  # list of {"role": ..., "content": ...}
st.session_state.setdefault("chat_agent", None)
st.session_state.setdefault("chat_thread", None)
st.session_state.setdefault("chat_book_data", None)  # parsed book request dict from chat
st.session_state.setdefault("chat_history", [])       # agent_framework message history
st.session_state.setdefault("chat_last_parsed_signature", None)

# Voice session state
st.session_state.setdefault("voice_transcript", [])
st.session_state.setdefault("voice_recordings", [])
st.session_state.setdefault("last_voice_clip_sig", None)
st.session_state.setdefault("voice_session", None)
st.session_state.setdefault("voice_running", False)
st.session_state.setdefault("voice_book_data", None)
st.session_state.setdefault("voice_clone_profile", None)
st.session_state.setdefault("pending_generation_mode", None)
st.session_state.setdefault("pending_generation_source", None)


# ── Batch background-thread singleton ─────────────────────────────────────────
# st.cache_resource creates the dict ONCE per server process; it survives
# Streamlit script reruns so background threads can safely write into it
# while the UI polls on each st.rerun().
@st.cache_resource
def _get_batch_globals() -> dict:
    """Singleton dict that persists across Streamlit reruns."""
    return {
        "running": False,
        "done":    False,
        "status":  {},   # job_id -> {state, log, current_step}
        "results": None,
        "specs":   [],
    }


def _render_batch_dashboard(bg: dict) -> None:
    """Render live progress cards (green / blue / red rectangles) for each batch job."""
    specs  = bg.get("specs",  [])
    status = bg.get("status", {})
    if not specs:
        return

    import re as _re2
    def _scrub(s: str) -> str:
        return _re2.sub(r'[A-Za-z]:[^\s]*Agent-Framework[^\s]*\\', '<workspace>\\', s)

    _CARD_STYLE = {
        "pending": ("#1c1c1c", "#555555"),
        "running": ("#0d1e35", "#4da6ff"),
        "done":    ("#0a2218", "#00c851"),
        "error":   ("#2a0a0a", "#ff4444"),
    }

    n_cols = min(len(specs), 3)
    cols   = st.columns(n_cols)

    for i, spec in enumerate(specs):
        col  = cols[i % n_cols]
        js   = status.get(spec.job_id, {})
        state  = js.get("state", "pending")
        step   = js.get("current_step", "\u23f3 Waiting\u2026")
        log    = js.get("log", [])

        bg_col, border = _CARD_STYLE.get(state, _CARD_STYLE["pending"])

        last_lines = "<br>".join(
            _scrub(ln).replace("<", "&lt;").replace(">", "&gt;") for ln in log[-4:]
        ) if log else "<em style='color:#666'>No output yet&hellip;</em>"

        step_esc = _scrub(step).replace("<", "&lt;").replace(">", "&gt;")
        prov_lbl = PROVIDER_LABELS.get(spec.provider, spec.provider)

        card = (
            f'<div style="background:{bg_col};border:2px solid {border};'
            f'border-radius:10px;padding:14px 16px;margin-bottom:10px;'
            f'font-family:monospace;min-height:160px;">'
            f'<div style="font-weight:bold;color:#fff;font-size:13px;margin-bottom:4px;">{spec.label}</div>'
            f'<div style="color:{border};font-size:11px;margin-bottom:8px;">'
            f'{prov_lbl} &middot; <code style="color:{border}">{spec.model}</code></div>'
            f'<div style="background:{border}22;border-left:3px solid {border};'
            f'padding:6px 8px;border-radius:4px;color:{border};font-size:12px;'
            f'font-weight:bold;margin-bottom:8px;word-break:break-word;">{step_esc}</div>'
            f'<div style="color:#888;font-size:10px;line-height:1.5;'
            f'border-top:1px solid #333;padding-top:6px;">{last_lines}</div>'
            f'</div>'
        )
        col.markdown(card, unsafe_allow_html=True)


def _render_gen_card(
    placeholder,
    step_text: str,
    step_idx: int,
    total_steps: int,
    topic: str = "",
    *,
    done: bool = False,
    error: bool = False,
) -> None:
    """Render a single-book generation progress card (matches batch dashboard style)."""
    if error:
        bg_col, border = "#2a0a0a", "#ff4444"
        icon = "❌"
    elif done:
        bg_col, border = "#0a2218", "#00c851"
        icon = "✅"
    else:
        bg_col, border = "#0d1e35", "#4da6ff"
        icon = "⚙️"

    pct = 100 if done else int((step_idx / max(total_steps, 1)) * 100)
    topic_esc = (topic[:55] + "…" if len(topic) > 55 else topic).replace("<", "&lt;").replace(">", "&gt;")
    step_esc = step_text.replace("<", "&lt;").replace(">", "&gt;")
    bar_fill = f'min-width:{"0" if pct == 0 else "6px"};background:{border};width:{pct}%;height:10px;border-radius:6px;'

    card = (
        f'<div style="background:{bg_col};border:2px solid {border};'
        f'border-radius:10px;padding:14px 18px;margin:8px 0;font-family:monospace;">'
        f'<div style="font-weight:bold;color:#fff;font-size:13px;margin-bottom:6px;">'
        f'{icon} {topic_esc}</div>'
        f'<div style="background:#1a1a1a;border-radius:6px;height:10px;margin:6px 0 10px 0;">'
        f'<div style="{bar_fill}"></div></div>'
        f'<div style="background:{border}22;border-left:3px solid {border};'
        f'padding:6px 10px;border-radius:4px;color:{border};font-size:12px;'
        f'font-weight:bold;word-break:break-word;">{step_esc}</div>'
        f'</div>'
    )
    placeholder.markdown(card, unsafe_allow_html=True)


def _strip_visual_for_blind(text: str) -> str:
    """Strip visual-only markdown elements from chapter text for blind-friendly output."""
    import re as _re
    # Remove markdown images: ![alt](url)
    text = _re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    # Remove HTML img tags
    text = _re.sub(r'<img[^>]*>', '', text, flags=_re.IGNORECASE)
    # Remove [VIDEO: ...] / [IMG: ...] / [IMAGE: ...] inline tags
    text = _re.sub(r'\[(VIDEO|IMG|IMAGE):[^\]]*\]', '', text, flags=_re.IGNORECASE)
    # Remove QR code lines (contain 'qr_code' or 'QR Code')
    text = _re.sub(r'.*(qr.?code|\bQR\b).*\n?', '', text, flags=_re.IGNORECASE)
    # Collapse 3+ blank lines to 2
    text = _re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


async def _run_chat_turn(user_message: str) -> str:
    """Run one chat turn against the conversational agent."""
    if st.session_state.chat_agent is None:
        st.session_state.chat_agent = await create_chat_agent(provider="qwen")

    # Use full conversation history (up to 20 exchanges) for better memory
    recent_history = st.session_state.chat_messages[-40:]
    history_lines = []
    for msg in recent_history:
        role = "User" if msg.get("role") == "user" else "Assistant"
        history_lines.append(f"{role}: {msg.get('content', '')}")

    prompt = (
        "FULL conversation history (remember ALL details the user provided):\n"
        + "\n".join(history_lines)
        + "\n\n"
        + f"New user message:\n{user_message}\n\n"
        + "IMPORTANT: Respond in the SAME language the user is writing in. "
        + "Remember every detail from the conversation above — do NOT ask for info already given."
    )

    response = await st.session_state.chat_agent.run(
        prompt, max_tokens=st.session_state.get("max_tokens_chat", 1600)
    )
    return (response.text or "").strip()


VOICE_CLONE_DIR = Path("books") / "voice_clones"
VOICE_SAMPLE_DIR = VOICE_CLONE_DIR / "samples"
VOICE_REGISTRY_PATH = VOICE_CLONE_DIR / "voice_registry.json"

def _slugify_name(value: str) -> str:
    cleaned = "".join(c.lower() if c.isalnum() else "_" for c in value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:60] or "my_voice"


def _load_voice_registry() -> dict:
    if VOICE_REGISTRY_PATH.exists():
        try:
            return json.loads(VOICE_REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_voice_registry(registry: dict):
    VOICE_CLONE_DIR.mkdir(parents=True, exist_ok=True)
    VOICE_REGISTRY_PATH.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _save_recording_sample(clip_bytes: bytes, preferred_name: str) -> Path:
    VOICE_SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    digest = hashlib.sha1(clip_bytes).hexdigest()[:10]
    filename = f"{_slugify_name(preferred_name)}_{stamp}_{digest}.wav"
    file_path = VOICE_SAMPLE_DIR / filename
    file_path.write_bytes(clip_bytes)
    return file_path


def _audio_mime(format_hint: str) -> str:
    fmt = (format_hint or "").strip().lower()
    return "audio/mpeg" if fmt == "mp3" else "audio/wav" if fmt == "wav" else "audio/mpeg"


def _collect_audio_narrations(chapters=None, fallback_dir: str | Path | None = None) -> list[AudioNarration]:
    """Collect valid audio narrations from chapter metadata and/or output directory scan."""
    collected: list[AudioNarration] = []
    seen_paths: set[str] = set()

    if chapters:
        for chapter in chapters:
            nar = getattr(chapter, "audio_narration", None)
            if not nar or not nar.file_path:
                continue
            path = Path(nar.file_path)
            if not path.exists():
                continue

            normalized = str(path.resolve())
            if normalized in seen_paths:
                continue
            seen_paths.add(normalized)

            if not nar.size_bytes:
                try:
                    nar.size_bytes = path.stat().st_size
                except Exception:
                    pass
            if not nar.format:
                nar.format = path.suffix.lstrip(".") or "mp3"

            collected.append(nar)

    if fallback_dir:
        base = Path(fallback_dir)
        if base.exists():
            for path in sorted(base.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in {".mp3", ".wav", ".m4a"}:
                    continue
                normalized = str(path.resolve())
                if normalized in seen_paths:
                    continue
                seen_paths.add(normalized)

                collected.append(
                    AudioNarration(
                        chapter_title=path.stem.replace("_", " "),
                        file_path=str(path),
                        duration_seconds=0.0,
                        voice_id="",
                        model="",
                        format=path.suffix.lstrip(".") or "mp3",
                        size_bytes=path.stat().st_size,
                    )
                )

    return collected


# Directories to skip when scanning for audio (test fixtures, etc.)
_AUDIO_SKIP_DIRS = {"test_e2e", "test", "tests", "fixtures", "samples"}


def _find_latest_audio_narrations(base_dir: str | Path = "books/audio") -> tuple[str | None, list[AudioNarration]]:
    """Find latest timestamp audio folder that actually contains playable files.

    Skips test/fixture directories and only returns audio from real generation
    sessions (timestamp-named folders like 20260227_054437).
    """
    base = Path(base_dir)
    if not base.exists():
        return None, []

    candidates = [
        p for p in base.iterdir()
        if p.is_dir() and p.name not in _AUDIO_SKIP_DIRS
    ]

    for folder in sorted(candidates, key=lambda p: p.name, reverse=True):
        narrations = _collect_audio_narrations(chapters=None, fallback_dir=folder)
        if narrations:
            return str(folder), narrations

    return None, []


def _request_from_chat_or_form(source: str, form_request: BookRequest) -> BookRequest:
    """Build request from chat JSON when available, otherwise fallback to form request."""
    if source == "chat" and st.session_state.chat_book_data:
        try:
            return build_book_request(st.session_state.chat_book_data)
        except Exception as e:
            st.warning(f"⚠️ Invalid parsed chat JSON, falling back to form values: {e}")
    return form_request


def _to_bool(value, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_runtime_options(parsed_chat_data: dict | None, defaults: dict) -> dict:
    """Resolve generation runtime options from chat payload with safe fallbacks."""
    resolved = dict(defaults)
    if not parsed_chat_data:
        return resolved

    provider = str(parsed_chat_data.get("model_provider", "github")).strip().lower()
    resolved["use_qwen_models"] = provider == "qwen"
    os.environ["MODEL_PROVIDER"] = provider

    parsed_text_model = parsed_chat_data.get("text_model")
    if parsed_text_model:
        resolved["qwen_text_model"] = str(parsed_text_model)

    resolved["enable_tts"] = _to_bool(
        parsed_chat_data.get("enable_voice_generation", None),
        resolved.get("enable_tts", False),
    )

    parsed_tts_voice = parsed_chat_data.get("tts_voice")
    if parsed_tts_voice in TTS_VOICES:
        resolved["tts_voice"] = parsed_tts_voice

    parsed_tts_model = parsed_chat_data.get("tts_model")
    if parsed_tts_model in TTS_MODELS:
        resolved["tts_model"] = parsed_tts_model

    parsed_tts_audio_format = parsed_chat_data.get("tts_audio_format")
    if parsed_tts_audio_format in TTS_AUDIO_FORMATS:
        resolved["tts_audio_format"] = parsed_tts_audio_format

    image_source = str(parsed_chat_data.get("image_source", "")).lower()
    if image_source == "ai_generate":
        resolved["generate_images"] = True
        resolved["use_ddg_images"] = False
    elif image_source == "web_search":
        resolved["generate_images"] = False
        resolved["use_ddg_images"] = True
    elif image_source == "none":
        resolved["generate_images"] = False
        resolved["use_ddg_images"] = False

    try:
        resolved["images_per_chapter"] = int(
            parsed_chat_data.get("images_per_chapter", resolved.get("images_per_chapter", 1))
        )
    except Exception:
        pass

    # Template ID from chat (supports "auto" for AI-driven selection)
    parsed_template = parsed_chat_data.get("template_id")
    if parsed_template and isinstance(parsed_template, str):
        resolved["template_id"] = parsed_template.strip().lower()

    # Palette ID from chat (optional — only meaningful for educational template)
    parsed_palette = parsed_chat_data.get("palette_id")
    if parsed_palette and isinstance(parsed_palette, str):
        resolved["palette_id"] = parsed_palette.strip().lower()

    return resolved


def _validate_generation_prereqs(
    use_qwen_models: bool,
    enable_tts: bool,
    voice_clone_profile: dict | None,
    generate_images: bool = False,
) -> bool:
    """Validate API-key prerequisites for selected generation path."""
    model_ok, model_msg = validate_api_keys(use_qwen_models)
    if not model_ok:
        st.error(model_msg)
        return False

    needs_dashscope = enable_tts or bool(voice_clone_profile and voice_clone_profile.get("voice"))
    if needs_dashscope and not os.getenv("DASHSCOPE_API_KEY"):
        st.error("\u274c Missing DASHSCOPE_API_KEY required for voice generation / voice cloning.")
        return False

    # AI image generation also requires DashScope
    if generate_images and not os.getenv("DASHSCOPE_API_KEY"):
        st.error(
            "\u274c Missing DASHSCOPE_API_KEY — required for AI image generation. "
            "Add it to your Streamlit secrets or .env file, "
            "or switch Image Source to \u2018DDG Safe Search\u2019 / \u2018None\u2019."
        )
        return False

    return True

# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR — All settings consolidated
# ══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Settings")

    # ── Model Settings ──────────────────────────────────────────────────
    with st.expander("🧠 Model", expanded=False):
        # Read keys from environment (.env loaded at startup)
        _env_github    = os.getenv("GITHUB_TOKEN", "")
        _env_dash      = os.getenv("DASHSCOPE_API_KEY", "")
        _env_anthropic = os.getenv("ANTHROPIC_API_KEY", "")
        _env_azure_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        _env_azure_ep  = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        _env_azure_dep = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")
        _env_region    = os.getenv("DASHSCOPE_REGION", "singapore")

        # ── Helper: render a key row (present banner OR input field) ──
        def _key_row(label: str, env_value: str, env_var: str, input_key: str, help_text: str):
            """Show ✅ banner if key already present, otherwise show password input."""
            if env_value:
                st.success(f"✅ {label} present")
                return env_value
            new_val = st.text_input(
                f"🔑 {label}",
                value="",
                type="password",
                help=help_text,
                key=input_key,
                placeholder=f"Paste your {env_var} here",
            )
            if new_val and new_val.strip():
                os.environ[env_var] = new_val.strip()
                return new_val.strip()
            return ""

        _github_key = _key_row(
            label="GitHub Models API Key",
            env_value=_env_github,
            env_var="GITHUB_TOKEN",
            input_key="ui_github_token_input",
            help_text="Personal Access Token for GitHub Models (GITHUB_TOKEN). Must have the 'models' scope — see github.com/settings/tokens.",
        )

        _dash_key = _key_row(
            label="DashScope API Key",
            env_value=_env_dash,
            env_var="DASHSCOPE_API_KEY",
            input_key="ui_dashscope_api_input",
            help_text="DashScope key for Qwen text/image/voice (DASHSCOPE_API_KEY).",
        )

        _anthropic_key = _key_row(
            label="Anthropic API Key",
            env_value=_env_anthropic,
            env_var="ANTHROPIC_API_KEY",
            input_key="ui_anthropic_key_input",
            help_text="Anthropic key for Claude models (ANTHROPIC_API_KEY).",
        )

        st.markdown("**Azure AI Foundry**")
        _azure_key = _key_row(
            label="Azure OpenAI API Key",
            env_value=_env_azure_key,
            env_var="AZURE_OPENAI_API_KEY",
            input_key="ui_azure_key_input",
            help_text="API key from Azure AI Foundry / Azure OpenAI (AZURE_OPENAI_API_KEY).",
        )
        if _env_azure_ep:
            st.success("\u2705 Azure Endpoint present")
            _azure_ep = _env_azure_ep
        else:
            _azure_ep = st.text_input(
                "\U0001f310 Azure Endpoint",
                value="",
                placeholder="https://your-instance.openai.azure.com/",
                help="Your Azure OpenAI endpoint URL (AZURE_OPENAI_ENDPOINT).",
                key="ui_azure_ep_input",
            )
            if _azure_ep.strip():
                os.environ["AZURE_OPENAI_ENDPOINT"] = _azure_ep.strip()

        if _env_azure_dep:
            st.success(f"\u2705 Azure Deployment: {_env_azure_dep}")
            _azure_dep = _env_azure_dep
        else:
            _azure_dep = st.text_input(
                "\U0001f4e6 Deployment Name",
                value="",
                placeholder="gpt-4o",
                help="Azure OpenAI deployment name (AZURE_OPENAI_DEPLOYMENT_NAME).",
                key="ui_azure_dep_input",
            )
            if _azure_dep.strip():
                os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = _azure_dep.strip()

        _region_options = ["singapore", "beijing", "us-virginia"]
        _region_default = _env_region if _env_region in _region_options else "singapore"
        qwen_region = st.selectbox(
            "🌍 DashScope Region",
            _region_options,
            index=_region_options.index(_region_default),
            help="Region used for Qwen models and voice cloning.",
            key="ui_dashscope_region",
        )
        os.environ["DASHSCOPE_REGION"] = qwen_region

        # ── Provider selector ────────────────────────────────────────
        _provider_options = [
            ("🐙 GitHub Models",   "github"),
            ("🟣 Qwen (DashScope)",  "qwen"),
            ("🔴 Claude (Anthropic)", "claude"),
            ("🔵 Azure AI Foundry",   "azure"),
        ]
        _provider_labels = [p[0] for p in _provider_options]
        _provider_values = [p[1] for p in _provider_options]

        _current_provider = os.getenv("MODEL_PROVIDER", "github")
        _provider_default_idx = _provider_values.index(_current_provider) if _current_provider in _provider_values else 0

        _selected_provider_label = st.radio(
            "🤖 Model Provider",
            _provider_labels,
            index=_provider_default_idx,
            horizontal=True,
        )
        selected_provider = _provider_values[_provider_labels.index(_selected_provider_label)]
        os.environ["MODEL_PROVIDER"] = selected_provider

        # Derived bool kept for backward-compat with all downstream code
        use_qwen_models = selected_provider == "qwen"

        # ── Model selector per provider ──────────────────────────────
        if selected_provider == "github":
            qwen_text_model = st.selectbox(
                "🧠 Text Model",
                ["gpt-4o-mini", "gpt-4o", "Meta-Llama-3.1-70B-Instruct", "Mistral-large"],
                index=0,
                help="gpt-4o-mini is fastest; gpt-4o is highest quality",
            )
            qwen_image_model = "qwen-image-plus"

        elif selected_provider == "qwen":
            qwen_text_model = st.selectbox(
                "🧠 Text Model",
                [
                    "qwen3.5-flash",
                    "qwen3.5-flash-2026-02-23",
                    "qwen3.5-35b-a3b",
                    "qwen3.5-27b",
                    "qwen3.5-122b-a10b",
                ],
                index=0,
                help="All models have 1 M-token free quota (expires 2026-05-24). "
                     "qwen3.5-flash is fastest; qwen3.5-122b-a10b is highest quality.",
            )
            qwen_image_model = st.selectbox(
                "🖼️ Image Model",
                ["qwen-image-plus", "qwen-image-max-2025-12-30", "qwen-image-max", "qwen-image"],
                index=0,
            )

        elif selected_provider == "claude":
            qwen_text_model = st.selectbox(
                "🧠 Text Model",
                [
                    "claude-haiku-4-5",
                    "claude-sonnet-4-6",
                    "claude-opus-4-6",
                ],
                index=0,
                help="Haiku is fastest; Opus 4 is highest quality",
            )
            qwen_image_model = "qwen-image-plus"

        else:  # azure
            _az_dep_default = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
            _az_choices = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-35-turbo"]
            if _az_dep_default not in _az_choices:
                _az_choices.insert(0, _az_dep_default)
            qwen_text_model = st.selectbox(
                "🧠 Deployment / Model",
                _az_choices,
                index=0,
                help="Deployment name in your Azure AI Foundry resource (AZURE_OPENAI_DEPLOYMENT_NAME).",
            )
            os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] = qwen_text_model
            qwen_image_model = st.selectbox(
                "🖼️ Image Deployment / Model",
                ["dall-e-3", "dall-e-2", "gpt-4o", "qwen-image-plus"],
                index=0,
                help="Azure image generation deployment, or select Qwen as fallback.",
                key="ui_azure_image_model",
            )

    # ── Max Tokens ──────────────────────────────────────────────────────
    with st.expander("📏 Max Tokens", expanded=False):
        st.caption(
            "Control the maximum response length for each agent. "
            "Higher values produce more detailed content but cost more."
        )
        max_tokens_curriculum = st.number_input(
            "Curriculum Agent",
            min_value=500, max_value=16000, value=2000, step=500,
            help="Max tokens for curriculum generation (book outline)",
        )
        max_tokens_chapter = st.number_input(
            "Chapter Agent",
            min_value=1000, max_value=16000, value=4000, step=500,
            help="Max tokens for each chapter's content generation",
        )
        max_tokens_chat = st.number_input(
            "Chat Agent",
            min_value=500, max_value=8000, value=1600, step=200,
            help="Max tokens for chat/conversational responses",
        )
        st.session_state["max_tokens_chat"] = max_tokens_chat

    # ── Images & Video ──────────────────────────────────────────────────
    with st.expander("🖼️ Images & Video", expanded=False):
        image_source = st.radio(
            "Image Source",
            ["AI Generate", "DDG Safe Search", "None"],
            index=0,
            help="AI Generate uses Qwen-Image; DDG uses DuckDuckGo safe search. Set to None for audio-only.",
        )
        generate_images = image_source == "AI Generate"
        use_ddg_images = image_source == "DDG Safe Search"
        images_per_chapter = st.slider("Images per chapter", 0, 5, 1)

        art_style = st.selectbox(
            "🎨 Art Style",
            [
                "auto",
                "watercolor",
                "cartoon",
                "realistic",
                "flat_vector",
                "pixel_art",
                "storybook",
                "3d_cartoon",
                "oil_painting",
                "educational",
                "ink_painting",
                "low_budget",
            ],
            index=0,
            format_func=lambda s: {
                "auto": "🧠 Auto (AI picks best)",
                "watercolor": "🎨 Watercolor",
                "cartoon": "🖍️ Cartoon",
                "realistic": "📷 Realistic Photography",
                "flat_vector": "📐 Flat / Vector",
                "pixel_art": "👾 Pixel Art",
                "storybook": "📖 Storybook Illustration",
                "3d_cartoon": "🧸 3D Cartoon / Pixar",
                "oil_painting": "🖼️ Oil Painting",
                "educational": "📚 Educational Illustration",
                "ink_painting": "🖌️ Ink / Sumi-e",
                "low_budget": "🖍️ Low Budget (B&W Coloring Pages)",
            }.get(s, s),
            help="Hint the AI about the visual style. 'Auto' lets the AI decide per image. 'Low Budget' generates B&W coloring pages.",
            disabled=not generate_images,
        )

        enable_video_search = st.checkbox(
            "🎬 YouTube Video Search",
            value=False,
            help="Find relevant YouTube videos and embed QR codes in each chapter",
        )
        st.caption(
            "🧠 The AI automatically picks the best camera angle, "
            "lighting, and resolution for each image."
        )

    # ── Voice & Narration ───────────────────────────────────────────────
    with st.expander("🔊 Voice & Audio", expanded=True):
        # Checkbox lives in the main form — read the stored value here
        enable_tts = st.session_state.get("enable_tts", True)

        # ── Cloned-voice option ─────────────────────────────────────────
        _voice_registry = _load_voice_registry()
        _has_cloned_voices = bool(_voice_registry)

        # Sync the checkbox default with whether a profile is already active
        if "use_cloned_voice_cb" not in st.session_state:
            st.session_state["use_cloned_voice_cb"] = bool(st.session_state.voice_clone_profile)
        use_cloned_voice = st.checkbox(
            "🎤 Use Cloned Voice",
            disabled=not enable_tts or not _has_cloned_voices,
            help=(
                "Use one of your saved cloned voice profiles instead of a preset voice. "
                "Record & clone a voice in the 🎤 Voice Cloning section below."
                if _has_cloned_voices
                else "No cloned voices found — record one in the 🎤 Voice Cloning section below."
            ),
            key="use_cloned_voice_cb",
        )

        if use_cloned_voice and _has_cloned_voices and enable_tts:
            _clone_keys = sorted(_voice_registry.keys())
            # Pre-select the currently active profile if any
            _active_name = (
                st.session_state.voice_clone_profile.get("name")
                if st.session_state.voice_clone_profile
                else None
            )
            _default_idx = (
                _clone_keys.index(_active_name)
                if _active_name and _active_name in _clone_keys
                else 0
            )
            selected_clone_key = st.selectbox(
                "🗣️ Cloned Voice Profile",
                options=_clone_keys,
                index=_default_idx,
                key="voice_audio_clone_select",
                help="Select which cloned voice to use for audio narration.",
            )
            # Activate the selected profile
            st.session_state.voice_clone_profile = _voice_registry.get(selected_clone_key)
            st.caption(
                f"✅ Cloned voice **{selected_clone_key}** will be used for narration."
            )
        # When unchecked we keep the stored profile so it can be re-enabled without re-cloning

        # ── Standard voice controls (disabled when using cloned voice) ──
        _using_clone = use_cloned_voice and _has_cloned_voices and enable_tts
        tts_model = st.selectbox(
            "TTS Model",
            list(TTS_MODELS.keys()),
            format_func=lambda k: TTS_MODELS[k],
            disabled=not enable_tts or _using_clone,
        )
        tts_voice = st.selectbox(
            "🗣️ Voice",
            list(TTS_VOICES.keys()),
            format_func=lambda k: f"{k} – {TTS_VOICES[k]}",
            disabled=not enable_tts or _using_clone,
            help="Preset voice (ignored when using a cloned voice)." if _using_clone else None,
        )
        tts_audio_format = st.selectbox(
            "Audio Format",
            list(TTS_AUDIO_FORMATS.keys()),
            index=0,
            format_func=lambda k: TTS_AUDIO_FORMATS[k],
            disabled=not enable_tts,
        )
        tts_speech_rate = st.slider(
            "⏩ Speech Rate",
            min_value=0.5, max_value=2.0, value=0.95, step=0.05,
            disabled=not enable_tts,
            help="Slightly slower (0.95) is ideal for educational content",
        )
        if enable_tts:
            st.info(
                "Requires DASHSCOPE_API_KEY. "
                + ("🎤 Using cloned voice." if _using_clone else "🗣️ Using preset voice.")
            )

    # ── Voice Cloning ───────────────────────────────────────────────────
    with st.expander("🎤 Voice Cloning", expanded=False):
        registry = _load_voice_registry()

        if registry:
            saved_keys = sorted(registry.keys())
            selected_saved_profile = st.selectbox(
                "Saved voice profiles",
                options=saved_keys,
                index=0,
                key="voice_saved_profile_select",
            )
            vc_col1, vc_col2 = st.columns(2)
            with vc_col1:
                if st.button("✅ Activate", key="voice_activate_saved_profile"):
                    st.session_state.voice_clone_profile = registry.get(selected_saved_profile)
                    # Delete the key so the init block recreates it as True on next run
                    st.session_state.pop("use_cloned_voice_cb", None)
                    st.success(f"✅ '{selected_saved_profile}' activated — cloned voice is now enabled!")
                    st.rerun()
            with vc_col2:
                if st.button("🗑️ Delete", key="voice_delete_saved_profile"):
                    profile = registry.get(selected_saved_profile) or {}
                    sample_path = profile.get("sample_path")
                    if sample_path and os.path.exists(sample_path):
                        try:
                            os.remove(sample_path)
                        except Exception:
                            pass
                    registry.pop(selected_saved_profile, None)
                    _save_voice_registry(registry)
                    if (
                        st.session_state.voice_clone_profile
                        and st.session_state.voice_clone_profile.get("name") == selected_saved_profile
                    ):
                        st.session_state.voice_clone_profile = None
                    st.success(f"Deleted: {selected_saved_profile}")
                    st.rerun()

        preferred_clone_name = st.text_input(
            "Voice profile name",
            value="my_voice",
            help="Key used to store/reuse your cloned voice.",
        )
        clone_model = st.selectbox(
            "Clone model",
            options=list(VC_MODELS.keys()),
            format_func=lambda k: VC_MODELS[k],
        )
        slug_name = _slugify_name(preferred_clone_name)
        existing_profile = registry.get(slug_name)
        if existing_profile:
            st.info(f"Profile '{slug_name}' exists — enable '🎤 Use Cloned Voice' in Voice & Audio to use it.")

        if hasattr(st, "audio_input"):
            clip = st.audio_input("🎙️ Record voice sample", key="sidebar_audio_input")
            if clip is not None:
                clip_bytes = clip.getvalue()
                clip_sig = f"{clip.name}:{len(clip_bytes)}"
                if clip_sig != st.session_state.last_voice_clip_sig:
                    st.session_state.last_voice_clip_sig = clip_sig
                    st.session_state.voice_recordings.append(
                        {
                            "name": clip.name or f"voice_clip_{len(st.session_state.voice_recordings) + 1}.wav",
                            "mime": clip.type or "audio/wav",
                            "bytes": clip_bytes,
                            "size": len(clip_bytes),
                        }
                    )
                    # Profile detected — user can enable it via the toggle in Voice & Audio
                    pass

            if st.session_state.voice_recordings:
                st.success(f"{len(st.session_state.voice_recordings)} recording(s)")
                latest_recording = st.session_state.voice_recordings[-1]
                clone_label = "♻️ Re-clone" if existing_profile else "🧬 Clone & save"
                if st.button(clone_label, key="clone_save_btn"):
                    try:
                        sample_path = _save_recording_sample(latest_recording["bytes"], preferred_clone_name)
                        # API requires lowercase alphanumeric only — strip underscores/hyphens
                        api_safe_name = re.sub(r'[^a-z0-9]', '', slug_name)[:60] or "myvoice"
                        voice_param = create_cloned_voice(
                            sample_path,
                            target_model=clone_model,
                            preferred_name=api_safe_name,
                            region=qwen_region,
                        )
                        profile = {
                            "name": slug_name,
                            "voice": voice_param,
                            "target_model": clone_model,
                            "sample_path": str(sample_path),
                            "updated_at": datetime.now().isoformat(timespec="seconds"),
                        }
                        registry[slug_name] = profile
                        _save_voice_registry(registry)
                        st.session_state.voice_clone_profile = profile
                        st.success(f"Voice cloned: '{slug_name}'")
                        st.rerun()
                    except Exception as e:
                        st.warning(f"⚠️ Voice enrollment failed — {e}")
                        st.caption("Your recording is saved. Check your DashScope key / region and try again.")

                if st.button("🧹 Clear recordings", key="voice_clear_btn"):
                    st.session_state.voice_recordings = []
                    st.session_state.last_voice_clip_sig = None
                    st.rerun()
        else:
            st.warning("Upgrade Streamlit for microphone support.")

        if st.session_state.voice_clone_profile:
            st.markdown("**✅ Active Clone**")
            st.json(st.session_state.voice_clone_profile)

    # ── Book Template (visible in main form below) ───────────────────────
    st.caption("🎨 Template & palette are configured in the Book Specification form below.")

    # ── API Key Status ──────────────────────────────────────────────────
    st.divider()
    is_valid, message = validate_api_keys(use_qwen_models)
    if is_valid:
        st.success(message)
    else:
        st.error(message)

# Profile actually used for this generation run (None when checkbox is off)
active_clone_profile = st.session_state.voice_clone_profile if use_cloned_voice else None

# ══════════════════════════════════════════════════════════════════════════
# ══ TABS: Form | Chat | Batch ═══════════════════════════════════════════
_tab_form, _tab_chat, _tab_batch = st.tabs(["📋 Form", "💬 Chat", "⚡ Batch"])

with _tab_batch:

    st.subheader("⚡ Batch Book Generation")
    st.caption(
        "Run up to 6 book jobs in parallel — each using a different LLM. "
        "Jobs execute concurrently in separate threads."
    )

    # ── Job builder ────────────────────────────────────────────────────────
    st.markdown("#### 📋 Configure Jobs")

    # ── Global batch options (use sidebar settings) ────────────────────
    _bopt_a, _bopt_b = st.columns(2)
    _batch_generate_images = _bopt_a.checkbox(
        "🖼️ Generate Images",
        value=False,
        key="batch_generate_images",
        help="Adds images to each chapter using the Image Source configured in the sidebar ‘🖼️ Images & Video’ section.",
    )
    _batch_enable_tts = _bopt_b.checkbox(
        "🔊 Generate Audio Narration",
        value=False,
        key="batch_enable_tts",
        help="Generates spoken narration for every chapter using the Voice & Audio settings from the sidebar.",
    )
    if _batch_generate_images:
        st.caption(f"🖼️ Images: {'AI Generate' if generate_images else ('DDG Search' if use_ddg_images else 'None')} · {images_per_chapter}/chapter · style={art_style}")
    if _batch_enable_tts:
        st.caption(f"🔊 Audio: {tts_voice} · {tts_model} · {tts_audio_format} · rate={tts_speech_rate}")
    st.divider()

    _batch_topic_default = "Emotional Intelligence for Teenagers"

    def _batch_job_row(idx: int):
        """Render one job configuration row. Returns a BatchJobSpec or None."""
        with st.expander(f"Job {idx + 1}", expanded=(idx < 3)):
            _col_en, _col_lbl = st.columns([1, 5])
            _enabled = _col_en.checkbox("Enable", value=True, key=f"bj_en_{idx}")
            if not _enabled:
                return None

            _lbl = _col_lbl.text_input(
                "Label", value=f"Job {idx + 1}",
                key=f"bj_lbl_{idx}",
            )

            _ca, _cb, _cc = st.columns(3)
            _provider = _ca.selectbox(
                "Provider",
                list(PROVIDER_LABELS.keys()),
                index=idx % len(PROVIDER_LABELS),
                format_func=lambda p: PROVIDER_LABELS[p],
                key=f"bj_prov_{idx}",
            )
            _models = PROVIDER_MODELS[_provider]
            _model = _cb.selectbox(
                "Model", _models, index=0,
                key=f"bj_model_{idx}",
            )
            _genre_opts = list(BOOK_GENRES.keys())
            _genre = _cc.selectbox(
                "Genre", _genre_opts,
                format_func=lambda g: BOOK_GENRES[g],
                index=0,
                key=f"bj_genre_{idx}",
            )

            _da, _db, _dc = st.columns([4, 1, 1])
            _topic = _da.text_input(
                "Topic", value=_batch_topic_default,
                key=f"bj_topic_{idx}",
            )
            _nch = _db.number_input(
                "Chapters", min_value=1, max_value=12, value=3,
                key=f"bj_nch_{idx}",
            )
            _lang = _dc.selectbox(
                "Language", ["English", "Spanish", "Portuguese"],
                key=f"bj_lang_{idx}",
            )

            return BatchJobSpec(
                job_id=f"job_{idx + 1}",
                label=_lbl,
                provider=_provider,
                model=_model,
                topic=_topic,
                num_chapters=int(_nch),
                language=_lang,
                genre=_genre,
                target_audience_age=14,
                country="World wide",
                learning_method="Project-Based Learning",
                # ── image settings from sidebar ─────────────────────────
                generate_images=generate_images if _batch_generate_images else False,
                use_ddg_images=use_ddg_images if _batch_generate_images else False,
                images_per_chapter=images_per_chapter if _batch_generate_images else 0,
                image_model=qwen_image_model,
                art_style=art_style,
                # ── TTS settings from sidebar ───────────────────────────
                enable_tts=_batch_enable_tts,
                tts_voice=tts_voice,
                tts_model=tts_model,
                tts_audio_format=tts_audio_format,
                tts_speech_rate=tts_speech_rate,
            )

    _num_jobs = st.slider("Number of parallel jobs", 1, 6, 3, key="batch_num_jobs")
    _specs = [_batch_job_row(i) for i in range(_num_jobs)]
    _specs = [s for s in _specs if s is not None]

    st.divider()

    # ── Run button ──────────────────────────────────────────────────────────
    _run_batch_clicked = st.button(
        f"🚀 Run {len(_specs)} Job(s) in Parallel",
        type="primary",
        disabled=len(_specs) == 0 or st.session_state.batch_running,
        key="run_batch_btn",
    )

    if _run_batch_clicked and _specs:
        import threading as _threading
        _bg = _get_batch_globals()
        _init_status = {
            s.job_id: {"state": "pending", "log": [], "current_step": "⏳ Waiting…"}
            for s in _specs
        }
        _bg["running"] = True
        _bg["done"]    = False
        _bg["results"] = None
        _bg["specs"]   = list(_specs)
        _bg["status"]  = _init_status
        st.session_state.batch_running = True
        st.session_state.batch_results = None

        def _bg_run_batch(_s=list(_specs), _st=_init_status, _bg_ref=_bg):
            try:
                _res, _ = run_batch_parallel(_s, status_dict=_st)
                _bg_ref["results"] = _res
            except Exception as _exc:
                _bg_ref["results"] = []
            finally:
                _bg_ref["done"]    = True
                _bg_ref["running"] = False

        _threading.Thread(target=_bg_run_batch, daemon=True).start()
        st.rerun()

    # ── Resolve cache-resource batch globals ─────────────────────────────────
    _bg = _get_batch_globals()

    # ── If batch just completed, move results into session_state ─────────────
    if st.session_state.batch_running and _bg["done"]:
        st.session_state.batch_results = _bg["results"]
        st.session_state.batch_running = False
        _bg["done"] = False
        st.rerun()

    # ── Live progress dashboard (auto-polls every 1.5 s) ─────────────────────
    if st.session_state.batch_running and not _bg["done"]:
        _live_specs = _bg.get("specs", _specs)
        st.markdown(f"#### ⚡ Running {len(_live_specs)} job(s) in parallel…")
        _render_batch_dashboard(_bg)
        time.sleep(1.5)
        st.rerun()

    # ── Completed results ─────────────────────────────────────────────────────
    if st.session_state.batch_results:
        st.markdown("#### 📊 Results")
        _results: list = st.session_state.batch_results

        # Sanitize a log line: strip absolute workspace paths
        import re as _re
        def _sanitize_log(line: str) -> str:
            # Remove any Windows absolute path up to and including the workspace folder name
            return _re.sub(r'[A-Za-z]:[^\s]*Agent-Framework[^\s]*\\', '<workspace>\\', line)

        # Summary table — 7 columns
        _col_hdrs = st.columns([2, 2, 1, 1, 1, 1, 1])
        for _h, _t in zip(
            _col_hdrs,
            ["Label", "Provider / Model", "Status", "Time", "Chapters", "Words", "Tokens"],
        ):
            _h.markdown(f"**{_t}**")
        st.divider()

        for _r in sorted(_results, key=lambda r: r.job_id):
            _rc = st.columns([2, 2, 1, 1, 1, 1, 1])
            _rc[0].write(_r.label)
            _rc[1].write(f"{PROVIDER_LABELS.get(_r.provider, _r.provider)} `{_r.model}`")
            if _r.success:
                _rc[2].success("✅ Done")
            else:
                _rc[2].error("❌ Failed")
            _rc[3].write(f"{_r.elapsed_sec:.0f}s" if _r.elapsed_sec else "—")
            _rc[4].write(str(_r.num_chapters) if _r.success else "—")
            _rc[5].write(f"{_r.word_count:,}" if _r.success else "—")
            _rc[6].write(f"{_r.tokens_est:,}" if _r.success else "—")

            # Inline error summary — shown immediately, with paths scrubbed
            if not _r.success:
                _err_time = f"{_r.elapsed_sec:.0f}s" if _r.elapsed_sec else "?"
                _err_toks = f"~{_r.tokens_est:,} tokens" if _r.tokens_est else "no tokens recorded"
                _safe_err = _sanitize_log(_r.error)
                st.error(
                    f"❌ **{_r.label}** failed after {_err_time} ({_err_toks}): {_safe_err}"
                )

            # Download buttons for successful jobs
            if _r.success and _r.html_path:
                import pathlib as _pl
                _html_file = _pl.Path(_r.html_path)
                try:
                    with open(_html_file, "rb") as _hf:
                        _file_bytes = _hf.read()
                    _dl_name = f"book_{_r.provider}_{_r.model.replace('.','_').replace('-','_')}.html"
                    st.download_button(
                        f"📥 {_r.label} — HTML",
                        data=_file_bytes,
                        file_name=_dl_name,
                        mime="text/html",
                        key=f"dl_html_{_r.job_id}",
                    )
                except Exception as _fe:
                    st.warning(f"⚠️ Could not load HTML for {_r.label}: {_fe}")

            # Log expander — paths scrubbed
            with st.expander(f"📋 Log — {_r.label}", expanded=not _r.success):
                if _r.error:
                    st.error(_sanitize_log(_r.error))
                for _line in _r.log:
                    st.text(_sanitize_log(_line))

    elif not st.session_state.batch_running:
        st.info("Configure jobs above and click **Run** to start parallel generation.")


# ══════════════════════════════════════════════════════════════════════════
# FORM TAB
# ══════════════════════════════════════════════════════════════════════════
with _tab_form:
    st.subheader("📋 Book Specification")
    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
    with c1:
        topic = st.text_input("📚 Topic", value="La IA en México 2025")
    with c2:
        country = st.selectbox("🌎 Country", ["Mexico", "Colombia", "Argentina", "Chile", "Peru", "Brazil", "World wide"])
    with c3:
        language = st.selectbox("🗣️ Language", ["Spanish", "Portuguese", "English"])
    with c4:
        target_audience_age = st.slider("👧 Age", 8, 16, 8)

    c5, c6, c7, c8 = st.columns([2, 2, 1, 2])
    with c5:
        learning_method = st.selectbox("🧠 Method", ["Scandinavian", "Montessori", "Project-Based"])
    with c6:
        _genre_options = list(BOOK_GENRES.keys())
        book_genre = st.selectbox(
            "📖 Genre",
            options=_genre_options,
            index=0,
            format_func=lambda g: BOOK_GENRES.get(g, g),
            help=(
                "**Educational** — curriculum + activities + QR codes (default)\n"
                "**Poetry** — poem sections, no activities\n"
                "**Fairy Tale** — narrative story chapters\n"
                "**Personal Development** — adult non-fiction prose chapters"
            ),
            key="book_genre",
        )
    with c7:
        num_chapters = st.slider("📑 Ch.", 2, 12, 2)
    with c8:
        pages_per_chapter = st.slider("📄 Pages/Ch", 1, 20, 1)

    if book_genre != "educational":
        _genre_desc = {
            "poetry":               "Each chapter = a thematic poem section. No activities, QR codes, or curriculum blocks.",
            "fairy_tale":           "Each chapter = immersive narrative prose. No educational structure.",
            "personal_development": "Each chapter = self-help non-fiction prose (hook → insight → framework → reflection).",
        }.get(book_genre, "")
        st.info(f"{BOOK_GENRES[book_genre]} — {_genre_desc}", icon="ℹ️")

    # ── Images ───────────────────────────────────────────────────
    _img_a, _img_b, _img_c, _img_d, _img_e = st.columns([1, 2, 1, 2, 2])
    with _img_a:
        _form_enable_images = st.checkbox(
            "🖼️ Images",
            value=False,
            key="form_enable_images",
            help="Generate or search for images for each chapter.",
        )
    with _img_b:
        _form_image_source = st.radio(
            "Source",
            ["AI Generate", "DDG Safe Search"],
            index=0,
            horizontal=True,
            key="form_image_source",
            disabled=not _form_enable_images,
        )
    with _img_c:
        _form_images_per_chapter = st.number_input(
            "Per chapter",
            min_value=1, max_value=5, value=1, step=1,
            key="form_images_per_chapter",
            disabled=not _form_enable_images,
        )
    _form_ai_images = _form_enable_images and _form_image_source == "AI Generate"
    _form_ddg_images = _form_enable_images and _form_image_source == "DDG Safe Search"
    with _img_d:
        _form_qwen_image_model = st.selectbox(
            "🤖 Model",
            ["qwen-image-plus", "qwen-image-max"],
            index=0,
            key="form_image_model",
            disabled=not _form_ai_images,
        )
    with _img_e:
        _form_art_style = st.selectbox(
            "🎨 Style",
            ["auto", "watercolor", "cartoon", "realistic", "flat_vector",
             "pixel_art", "storybook", "3d_cartoon", "oil_painting",
             "educational", "ink_painting", "low_budget"],
            index=0,
            key="form_art_style",
            format_func=lambda s: {
                "auto": "🧠 Auto", "watercolor": "🎨 Watercolor",
                "cartoon": "🖍️ Cartoon", "realistic": "📷 Realistic",
                "flat_vector": "📐 Flat/Vector", "pixel_art": "👾 Pixel Art",
                "storybook": "📖 Storybook", "3d_cartoon": "🧸 3D Cartoon",
                "oil_painting": "🖼️ Oil Painting", "educational": "📚 Educational",
                "ink_painting": "🖌️ Ink/Sumi-e", "low_budget": "🖍️ B&W Coloring",
            }.get(s, s),
            disabled=not _form_ai_images,
        )

    # ── Accessibility ──────────────────────────────────────────────────
    _accb = st.columns(1)[0]
    auto_color_friendly = False
    auto_blind_friendly = False
    with _accb:
        enable_tts = st.checkbox(
            "🎙️ Enable Audio Narration",
            help="Generate spoken narration for each chapter using Qwen3 TTS-VC",
            key="enable_tts",
        )

    # ── Visual Template & Palette ──────────────────────────────────────
    _tc8, _tc9 = st.columns(2)
    with _tc8:
        _tmpl_choices = template_choices()
        _tmpl_option_ids = [t_id for _, t_id in _tmpl_choices]
        template_id = st.selectbox(
            "🎨 Visual Template",
            options=_tmpl_option_ids,
            index=0,
            format_func=lambda tid: next(
                (label for label, t_id in _tmpl_choices if t_id == tid), tid
            ),
            help="Controls page layout, borders, ornaments, fonts, and colour scheme. "
                 "Each template is a completely different visual style — not just a colour change. "
                 "'Auto' picks the best template for your topic.",
            key="main_template_id",
        )
        if template_id != "auto":
            _tmpl_info = get_template(template_id)
            st.caption(f"{_tmpl_info.emoji} **{_tmpl_info.name}** — {_tmpl_info.description}")
        else:
            st.caption("🤖 AI will choose the best template for your topic.")
    with _tc9:
        _PALETTE_OPTIONS = {
            "auto": "🤖 Auto (based on topic)",
            "pal-naranja": "🟠 Naranja / Orange",
            "pal-azul": "🔵 Azul / Blue",
            "pal-rojo": "🔴 Rojo / Red",
            "pal-rosa": "🌸 Rosa / Pink",
            "pal-negro": "🖤 Negro / Dark",
            "pal-olivo": "🌿 Olivo / Olive Green",
            "pal-arcoiris": "🌈 Arcoíris / Rainbow",
            "pal-halloween": "🎃 Halloween",
            "pal-navidad": "🎄 Navidad / Christmas",
            "pal-san-valentin": "💕 San Valentín",
        }
        palette_id = st.selectbox(
            "🎨 Color Palette",
            options=list(_PALETTE_OPTIONS.keys()),
            index=0,
            format_func=lambda p: _PALETTE_OPTIONS.get(p, p),
            help="Override the automatic color palette. "
                 "Only applies to the Educational template — "
                 "specialty templates (Horror, Fantasy, etc.) use their own fixed palette.",
            key="main_palette_id",
        )
        if template_id not in ("auto", "educational"):
            st.caption("⚠️ Palette is fixed by this template's visual style.")
        elif palette_id == "auto":
            st.caption("🤖 Color palette chosen automatically from your topic.")
        else:
            st.caption(f"✅ Using **{_PALETTE_OPTIONS.get(palette_id, palette_id)}** palette.")

    st.divider()
    _gen_f1, _gen_f2 = st.columns(2)
    with _gen_f1:
        generate_full_clicked = st.button("🚀 Generate Full Book", key="gen_full_form")
    with _gen_f2:
        generate_audio_only_clicked = st.button("🎧 Generate Audiobook Only", key="gen_audio_form")

# ══════════════════════════════════════════════════════════════════════════
# CHAT TAB
# ══════════════════════════════════════════════════════════════════════════
with _tab_chat:
    st.caption(
        "Describe your book idea. The assistant will decide all parameters "
        "(topic, age, country, chapters, language, method) and trigger generation automatically."
    )
    if not st.session_state.chat_messages:
        st.info("💡 Example: 'Write a 6-chapter maths book for 10-year-olds in Mexico in Spanish'")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_prompt = st.chat_input("Type your message...", key="chat_input_tab")
    if user_prompt:
        st.session_state.chat_messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    assistant_text = asyncio.run(_run_chat_turn(user_prompt))
                except Exception as e:
                    assistant_text = f"❌ Chat error: {e}"
                st.markdown(assistant_text)
        st.session_state.chat_messages.append({"role": "assistant", "content": assistant_text})
        parsed = parse_book_request_from_response(assistant_text)
        if parsed:
            st.session_state.chat_book_data = parsed
            parsed_signature = json.dumps(parsed, ensure_ascii=False, sort_keys=True)
            if parsed_signature != st.session_state.chat_last_parsed_signature:
                st.session_state.chat_last_parsed_signature = parsed_signature
                requested_mode = str(parsed.get("generation_mode", "full")).strip().lower()
                if requested_mode not in {"full", "audio_only"}:
                    requested_mode = "full"
                st.session_state.pending_generation_mode = requested_mode
                st.session_state.pending_generation_source = "chat"
        st.rerun()

    if st.session_state.chat_book_data:
        st.success("✅ Book parameters captured — ready to generate.")
        _gen_c1, _gen_c2 = st.columns(2)
        with _gen_c1:
            generate_full_from_chat = st.button("🚀 Generate Full Book", key="gen_full_chat")
        with _gen_c2:
            generate_audio_from_chat = st.button("🎧 Audiobook Only", key="gen_audio_chat")
    else:
        generate_full_from_chat = False
        generate_audio_from_chat = False

def _make_export_relative_path(img_path: str) -> str:
    """Convert an image path to be relative to the export directory.

    Images are saved at:  books/images/{timestamp}/{chapter}/{file}
    Exports live at:      books/{type}/{timestamp}/
    Relative from export: ../../images/{timestamp}/{chapter}/{file}
    """
    normalized = img_path.replace("\\", "/")
    idx = normalized.find("books/")
    if idx >= 0:
        after_books = normalized[idx + len("books/"):]
        return "../../" + after_books
    return normalized


# Localised label for the "Recommended Video" text appended to each chapter.
# Add more languages as needed — falls back to English.
_VIDEO_RECOMMENDED_LABELS: dict[str, str] = {
    "Spanish":    "Video recomendado",
    "English":    "Recommended video",
    "Portuguese": "Vídeo recomendado",
    "French":     "Vidéo recommandée",
    "German":     "Empfohlenes Video",
    "Italian":    "Video consigliato",
    "Chinese":    "推荐视频",
    "Japanese":   "おすすめ動画",
    "Arabic":     "فيديو موصى به",
}


def _embed_images_in_markdown(markdown_content: str, generated_images: list) -> str:
    """Replace [IMAGE: ...] placeholders with generated images and style leftovers.

    Each generated image replaces the next available [IMAGE: ...] placeholder.
    If there are more images than placeholders the extra images are prepended.
    Remaining [IMAGE: ...] and [VIDEO: ...] are converted to styled callouts.
    """
    placeholder_pattern = r'\[IMAGE:\s*[^\]]+\]'
    placeholders = re.findall(placeholder_pattern, markdown_content)

    for idx, img in enumerate(generated_images):
        rel_path = _make_export_relative_path(img.url)
        img_md = f"![{img.description}]({rel_path})"
        if idx < len(placeholders):
            markdown_content = markdown_content.replace(placeholders[idx], img_md, 1)
        else:
            # More images than placeholders — prepend as header images
            markdown_content = f"{img_md}\n\n{markdown_content}"

    # Remove remaining [IMAGE: ...] and [VIDEO: ...] that had no image generated.
    # Do NOT convert them to styled callouts — they should disappear completely
    # so the HTML never shows a description without an actual image.
    markdown_content = re.sub(
        r'\[IMAGE:\s*[^\]]+\]',
        '',
        markdown_content,
    )
    markdown_content = re.sub(
        r'\[VIDEO:\s*[^\]]+\]',
        '',
        markdown_content,
    )
    return markdown_content


# Approximate output-token pricing per 1M tokens (USD)
# Sources: official model pricing pages (Feb 2026 snapshot).
# We ALWAYS show the commercial list price, even when a free-tier quota is
# available, so users see the real market value of each generation run.
_COST_PER_1M_OUTPUT: dict[str, float] = {
    # GitHub Models  (free quota, but underlying commercial rates shown)
    "gpt-4o-mini":                   0.60,
    "gpt-4o":                       10.00,
    "Meta-Llama-3.1-70B-Instruct":   0.90,   # Groq/Together commercial rate
    "Mistral-large":                 3.00,   # Mistral official API rate
    # Qwen / Alibaba Cloud — commercial list rates (free promo until 2026-05-24)
    "qwen3.5-flash":                 0.15,
    "qwen3.5-flash-2026-02-23":      0.15,
    "qwen3.5-35b-a3b":               0.35,
    "qwen3.5-27b":                   0.30,
    "qwen3.5-122b-a10b":             0.90,
    # Legacy Qwen aliases
    "qwen-flash":                    0.15,
    "qwen-plus":                     0.40,
    "qwen-max":                      2.00,
    "qwen3-max":                     2.60,
    # Anthropic Claude
    "claude-haiku-4-5":              4.00,
    "claude-sonnet-4-6":            15.00,
    "claude-opus-4-6":              75.00,
    # Azure OpenAI
    "gpt-35-turbo":                  2.00,
    "gpt-4-turbo":                  30.00,
}


def _estimate_cost(tokens: int, model: str | None) -> float | None:
    """Return estimated USD cost or None if pricing unknown."""
    if not model:
        return None
    price = _COST_PER_1M_OUTPUT.get(model)
    if price is None:
        # Try prefix match (e.g. 'gpt-4o' prefix for custom deployments)
        for k, v in _COST_PER_1M_OUTPUT.items():
            if model.startswith(k):
                price = v
                break
    if price is None:
        return None
    if price == 0.0:
        return 0.0
    return round(tokens * price / 1_000_000, 4)


def _estimate_tokens(curriculum, chapters) -> int:
    """Rough token estimate: whitespace-split words × 1.33 (avg subword factor)."""
    text = ""
    if curriculum:
        import json as _json
        try:
            text += _json.dumps(curriculum.model_dump())
        except Exception:
            pass
    for ch in (chapters or []):
        text += (ch.markdown_content or "")
    words = len(text.split())
    return max(1, int(words * 1.33))


def _apply_color_friendly_css(html_path: str) -> str | None:
    """Injects a WCAG 2.1 AA, colorblind-safe CSS block into the HTML and saves
    a new file with the suffix _accessible.html.  Returns the new file path."""
    COLOR_FRIENDLY_CSS = """
<style id="color-friendly-override">
/* ===== WCAG 2.1 AA — Colorblind-Safe Palette Override ===== */
:root {
  --cb-bg: #FFFFFF;
  --cb-text: #1A1A1A;
  --cb-primary: #0072B2;   /* blue  — safe for all CVD types */
  --cb-accent:  #E69F00;   /* amber — safe */
  --cb-success: #009E73;   /* teal  — safe */
  --cb-warn:    #CC79A7;   /* rose  — avoids red/green encoding */
  --cb-info:    #56B4E9;   /* sky blue */
}
body { background: var(--cb-bg) !important; color: var(--cb-text) !important;
       font-family: 'Atkinson Hyperlegible', Arial, sans-serif !important; }
h1, h2, h3, h4 { color: var(--cb-primary) !important; }
a, a:visited   { color: var(--cb-primary) !important; }
.chapter, section, article { border-left: 5px solid var(--cb-primary) !important; }
table { border-collapse: collapse; }
th { background: var(--cb-primary) !important; color: #fff !important; }
tr:nth-child(even) { background: #E8F4FD !important; }
.highlight, mark { background: var(--cb-accent) !important; color: #000 !important; }
.success, .correct { color: var(--cb-success) !important; font-weight: bold; }
.warning, .incorrect { color: var(--cb-warn) !important; font-weight: bold; }
img { filter: none !important; }
</style>
"""
    try:
        with open(html_path, "r", encoding="utf-8", errors="replace") as f:
            html = f.read()
        if "color-friendly-override" in html:
            # already applied — just return new path
            pass
        else:
            html = html.replace("</head>", f"{COLOR_FRIENDLY_CSS}</head>", 1)
        out_path = str(html_path).replace(".html", "_accessible.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        return out_path
    except Exception as e:
        print(f"⚠️ _apply_color_friendly_css failed: {e}")
        return None


async def generate_book_async(
    request: BookRequest,
    generate_images: bool,
    use_qwen_models: bool = False,
    qwen_region: str = "singapore",
    images_dir: str = "./books/images",
    text_model: str | None = None,
    image_model: str | None = None,
    images_per_chapter: int = 1,
    use_ddg_images: bool = False,
    enable_video_search: bool = False,
    enable_tts: bool = False,
    tts_voice: str = "longxiaochun",
    tts_model: str = "qwen3-tts-vc-realtime",
    tts_audio_format: str = "wav_24k",
    tts_speech_rate: float = 0.95,
    audio_dir: str = "./books/audio",
    art_style: str = "auto",
    voice_clone_profile: dict | None = None,
    max_tokens_curriculum: int = 2000,
    max_tokens_chapter: int = 4000,
) -> tuple:
    """
    Async book generation orchestration with optional image generation.

    Image prompts, style, AND resolutions are generated by the text LLM
    following the advanced formula.  The LLM picks shot size, perspective,
    lens type, style, lighting, and resolution automatically based on content.
    
    Best practices:
    - Clean error handling
    - Typed return values
    - Proper resource cleanup
    - Flexible model provider selection
    """
    use_qwen = use_qwen_models
    # Ensure image_model always has a valid default
    if not image_model:
        image_model = "qwen-image-plus"

    # ── Thread-pool helper: run any blocking/sync call without stalling the event loop ──
    import functools
    _loop = asyncio.get_event_loop()

    async def _run_sync(fn, *args, **kwargs):
        return await _loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))

    # ── Per-chapter TTS coroutine (runs concurrently with next chapter's text gen) ──
    async def _synthesize_tts(chapter, ch_idx: int) -> "AudioNarration | None":
        chapter_narration = None
        _using_clone = bool(voice_clone_profile and voice_clone_profile.get("voice"))

        if _using_clone:
            vc_voice = voice_clone_profile.get("voice")
            vc_model = voice_clone_profile.get("target_model", "qwen3-tts-vc-realtime-2025-11-27")
            vc_name  = voice_clone_profile.get("name", "custom_voice")
            try:
                vc_path = await _run_sync(
                    narrate_chapter_vc,
                    chapter_title=chapter.chapter_title,
                    markdown_content=chapter.markdown_content,
                    output_dir=audio_dir,
                    voice=vc_voice,
                    model=vc_model,
                    region=qwen_region,
                )
                if vc_path and os.path.exists(vc_path):
                    chapter_narration = AudioNarration(
                        chapter_title=chapter.chapter_title,
                        file_path=str(vc_path),
                        duration_seconds=0.0,
                        voice_id=vc_voice,
                        model=vc_model,
                        format=Path(vc_path).suffix.lstrip(".") or "wav",
                        size_bytes=os.path.getsize(vc_path),
                    )
                else:
                    print(f"❌ [TTS] VC failed for ch {ch_idx+1} '{vc_name}' — attempting re-enrollment")
            except Exception as vc_err:
                print(f"❌ [TTS] VC exception ch {ch_idx+1}: {vc_err}")

            # Auto-re-enroll when VC synthesis failed
            if chapter_narration is None:
                sample_path = voice_clone_profile.get("sample_path")
                if sample_path and Path(sample_path).exists():
                    try:
                        api_safe = re.sub(r'[^a-z0-9]', '', vc_name.lower())[:20] or "myvoice"
                        print(f"🔄 [TTS] Re-enrolling '{vc_name}' from {sample_path}")
                        new_voice = await _run_sync(
                            create_cloned_voice,
                            sample_path,
                            target_model=vc_model,
                            preferred_name=api_safe,
                            region=qwen_region,
                        )
                        if new_voice:
                            voice_clone_profile["voice"] = new_voice
                            voice_clone_profile["updated_at"] = datetime.now().isoformat(timespec="seconds")
                            st.session_state.voice_clone_profile = voice_clone_profile
                            _fresh_reg = _load_voice_registry()
                            _fresh_reg[vc_name] = voice_clone_profile
                            _save_voice_registry(_fresh_reg)
                            print(f"✅ [TTS] Re-enrolled {new_voice[:40]}... — retrying synthesis")
                            vc_path2 = await _run_sync(
                                narrate_chapter_vc,
                                chapter_title=chapter.chapter_title,
                                markdown_content=chapter.markdown_content,
                                output_dir=audio_dir,
                                voice=new_voice,
                                model=vc_model,
                                region=qwen_region,
                            )
                            if vc_path2 and os.path.exists(vc_path2):
                                chapter_narration = AudioNarration(
                                    chapter_title=chapter.chapter_title,
                                    file_path=str(vc_path2),
                                    duration_seconds=0.0,
                                    voice_id=new_voice,
                                    model=vc_model,
                                    format=Path(vc_path2).suffix.lstrip(".") or "wav",
                                    size_bytes=os.path.getsize(vc_path2),
                                )
                            else:
                                print(f"❌ [TTS] Re-enrolled VC also failed for ch {ch_idx+1}. No audio.")
                        else:
                            print(f"❌ [TTS] Re-enrollment returned no voice for ch {ch_idx+1}. No audio.")
                    except Exception as _re_err:
                        print(f"❌ [TTS] Re-enrollment exception ch {ch_idx+1}: {_re_err}")
                else:
                    print(
                        f"❌ [TTS] No sample for re-enrollment ch {ch_idx+1} "
                        f"(sample_path={sample_path!r}). Please re-clone the voice."
                    )

        # Fallback to preset TTS when clone is absent OR clone synthesis exhausted
        if chapter_narration is None:
            if _using_clone:
                print(
                    f"⚠️ [TTS] Ch {ch_idx+1}: cloned-voice synthesis exhausted — "
                    f"falling back to preset voice '{tts_voice}'. "
                    f"Re-clone the voice in the 🎤 section if this persists."
                )
            print(
                f"🔊 [TTS] Chapter {ch_idx+1}: '{chapter.chapter_title}' — "
                f"voice={tts_voice}, model={tts_model}, format={tts_audio_format}"
            )
            narration = await _run_sync(
                narrate_chapter,
                chapter_title=chapter.chapter_title,
                markdown_content=chapter.markdown_content,
                output_dir=audio_dir,
                voice=tts_voice,
                model=tts_model,
                audio_format=tts_audio_format,
                speech_rate=tts_speech_rate,
                language=request.language,
            )
            chapter_narration = narration

        if chapter_narration:
            print(
                f"🔊 ✅ Narration done ch {ch_idx+1}: {chapter_narration.file_path} "
                f"({chapter_narration.size_bytes} bytes)"
            )
        else:
            print(f"⚠️ ❌ TTS FAILED for chapter {ch_idx+1}: {chapter.chapter_title}")
        return chapter_narration

    try:
        # Step 1: Show progress card immediately then build curriculum
        progress_placeholder = st.empty()
        _render_gen_card(progress_placeholder, "📋 Building curriculum…", 0, 3, request.topic)

        # Step 2: Generate curriculum
        curriculum_agent = await create_curriculum_agent(use_qwen=use_qwen_models, model_id=text_model)
        curriculum = await generate_curriculum(curriculum_agent, request, max_tokens=max_tokens_curriculum)

        if not curriculum:
            raise ValueError("Failed to generate curriculum")

        _total_steps = len(curriculum.chapters) + 2  # curriculum + N chapters + TTS collect
        _render_gen_card(progress_placeholder, "✅ Curriculum ready — generating chapters…", 1, _total_steps, request.topic)

        # Step 3: Generate chapters + media in parallel per chapter
        chapter_agent = await create_chapter_agent(use_qwen=use_qwen_models, model_id=text_model)
        context = {
            "age": request.target_audience_age,
            "country": request.country,
            "learning_method": request.learning_method,
            "language": request.language,
            "pages_per_chapter": request.pages_per_chapter,
        }

        full_chapters: list = []
        previous_summaries: list[str] = []
        # TTS tasks fire in background — collected after all chapters are written
        pending_tts: list[tuple[int, object, "asyncio.Task"]] = []

        for i, outline in enumerate(curriculum.chapters):
            total = len(curriculum.chapters)

            # ── Chapter text (sequential — narrative continuity via previous_summaries) ──
            _render_gen_card(
                progress_placeholder,
                f"📝 Chapter {i+1}/{total}: {outline.title[:50]}",
                i + 1, _total_steps, request.topic,
            )
            chapter = await generate_chapter(
                chapter_agent, outline, context,
                max_tokens=max_tokens_chapter,
                images_per_chapter=images_per_chapter if (generate_images or use_ddg_images) else 0,
            )

            if not chapter:
                st.warning(f"⚠️ Failed to generate chapter: {outline.title}")
                continue

            # ── Build parallel media tasks for this chapter ─────────────────────────
            chapter_folder = "".join(
                c if c.isalnum() or c in (' ', '_', '-') else '_' for c in chapter.chapter_title
            ).replace(' ', '_')[:50]
            chapter.generated_images = []

            parallel_tasks: list = []
            task_labels: list[tuple[str, int]] = []

            # AI image generation (all N images simultaneously in thread pool)
            if generate_images and images_per_chapter:
                placeholder_descs = getattr(chapter, 'image_placeholders', []) or []
                for idx in range(images_per_chapter):
                    img_title = placeholder_descs[idx] if idx < len(placeholder_descs) else chapter.chapter_title
                    img_summary = placeholder_descs[idx] if idx < len(placeholder_descs) else outline.summary
                    parallel_tasks.append(_run_sync(
                        generate_chapter_image,
                        title=img_title, summary=img_summary,
                        output_dir=images_dir, chapter_name=chapter_folder,
                        language=request.language, country=request.country,
                        audience_age=request.target_audience_age,
                        use_qwen_text=use_qwen_models, text_model=text_model,
                        image_model=image_model, art_style=art_style,
                    ))
                    task_labels.append(('image', idx))

            # DDG image search (all N searches simultaneously)
            if use_ddg_images and images_per_chapter:
                ddg_img_dir = str(Path(images_dir) / chapter_folder)
                for idx in range(images_per_chapter):
                    query = f"{outline.title} {outline.summary[:60]} educational children"
                    parallel_tasks.append(search_and_download_image(
                        query=query, output_dir=ddg_img_dir,
                        language=request.language.lower()[:2],
                        country=request.country, safesearch="moderate",
                    ))
                    task_labels.append(('ddg_image', idx))

            # Video search (concurrent with images)
            if enable_video_search:
                video_queries = re.findall(r'\[VIDEO:\s*([^\]]+)\]', chapter.markdown_content)
                if not video_queries:
                    video_queries = [f"{outline.title} {request.language} educational"]
                parallel_tasks.append(search_videos_for_chapter(
                    chapter_title=chapter.chapter_title,
                    video_queries=video_queries,
                    topic=request.topic,
                    language=request.language,
                    country=request.country,
                ))
                task_labels.append(('videos', 0))

            # ── Run images + videos in parallel ─────────────────────────────────────
            if parallel_tasks:
                n_imgs = sum(1 for t, _ in task_labels if t in ('image', 'ddg_image'))
                n_vids = sum(1 for t, _ in task_labels if t == 'videos')
                parts = []
                if n_imgs:
                    parts.append(f"{'🎨' if generate_images else '🔍'} {n_imgs} image(s)")
                if n_vids:
                    parts.append("🎬 video search")
                _render_gen_card(
                    progress_placeholder,
                    f"⚡ Ch {i+1}/{total} — parallel: {', '.join(parts)}…",
                    i + 1, _total_steps, request.topic,
                )
                media_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)

                for (rtype, ridx), result in zip(task_labels, media_results):
                    if isinstance(result, Exception):
                        print(f"⚠️ {rtype}[{ridx}] ch {i+1} failed: {result}")
                        if rtype in ('image', 'ddg_image'):
                            st.warning(f"⚠️ Image {ridx+1} for '{chapter.chapter_title}' failed: {result}")
                        continue
                    if rtype in ('image', 'ddg_image'):
                        if result:
                            chapter.generated_images.append(result)
                            print(f"✅ {rtype.upper()} {ridx+1} ch {i+1}: {chapter.chapter_title}")
                        else:
                            st.warning(f"⚠️ {'Image' if rtype == 'image' else 'DDG image'} {ridx+1} for '{chapter.chapter_title}' not found.")
                    elif rtype == 'videos' and result:
                        chapter.videos = result
                        _vid_label = _VIDEO_RECOMMENDED_LABELS.get(
                            request.language, "Recommended video"
                        )
                        for v in result:
                            chapter.markdown_content += (
                                f"\n\n---\n🎬 **{_vid_label}:** [{v.title}]({v.url})\n\n"
                                f"![QR Code]({v.qr_code})\n"
                            )
                        print(f"✅ {len(result)} video(s) ch {i+1}: {chapter.chapter_title}")

            # ── Embed images into markdown (needs media results, so after gather) ───
            chapter.markdown_content = _embed_images_in_markdown(
                chapter.markdown_content,
                getattr(chapter, 'generated_images', []),
            )

            # ── Fire TTS as a background asyncio.Task ──────────────────────────────
            # It runs concurrently while the next chapter's text is being generated.
            if enable_tts:
                tts_task = asyncio.create_task(_synthesize_tts(chapter, i))
                pending_tts.append((i, chapter, tts_task))
                _render_gen_card(
                    progress_placeholder,
                    f"📝 Ch {i+1}/{total} done — 🔊 TTS running in background…",
                    i + 1, _total_steps, request.topic,
                )

            full_chapters.append(chapter)
            previous_summaries.append(f"{chapter.chapter_title}: {outline.summary[:120]}")

        # ── Collect all background TTS tasks ──────────────────────────────────────
        if pending_tts:
            remaining = [task for _, _, task in pending_tts if not task.done()]
            if remaining:
                _render_gen_card(
                    progress_placeholder,
                    f"⏳ Waiting for {len(remaining)} audio narration(s) to finish…",
                    len(curriculum.chapters) + 1, _total_steps, request.topic,
                )
                await asyncio.gather(*remaining, return_exceptions=True)
            for ch_idx, chapter, tts_task in pending_tts:
                try:
                    narration = tts_task.result()
                    if narration:
                        chapter.audio_narration = narration
                except Exception as tts_err:
                    print(f"⚠️ TTS result error ch {ch_idx+1}: {tts_err}")

        progress_placeholder.empty()

        if not full_chapters:
            raise ValueError("No chapters were successfully generated")

        return curriculum, full_chapters

    except Exception as e:
        import traceback
        error_msg = f"❌ Error during generation: {str(e)}"
        print(f"\n{'='*60}")
        print(f"ERROR: {error_msg}")
        print(f"Traceback:\n{traceback.format_exc()}")
        print(f"{'='*60}\n")
        st.error(error_msg)
        return None, None


async def generate_audio_book_only_async(
    request: BookRequest,
    use_qwen_models: bool = False,
    qwen_region: str = "singapore",
    text_model: str | None = None,
    tts_voice: str = "longxiaochun",
    tts_model: str = "qwen3-tts-vc-realtime",
    tts_audio_format: str = "wav_24k",
    tts_speech_rate: float = 0.95,
    audio_dir: str = "./books/audio",
    voice_clone_profile: dict | None = None,
) -> tuple:
    """Generate audiobook assets only (curriculum + chapters + narration), no HTML/PDF/images."""
    import logging as _logging
    _audio_logger = _logging.getLogger("audiobook_pipeline")
    _vc_summary = (
        f"name={voice_clone_profile.get('name','?')}  "
        f"voice={str(voice_clone_profile.get('voice',''))[:40]}..."
        if voice_clone_profile else "None"
    )
    _audio_logger.info(
        f"\n{'='*60}\n"
        f"🎧 AUDIOBOOK-ONLY PIPELINE STARTING\n"
        f"  topic       = {request.topic}\n"
        f"  language    = {request.language}\n"
        f"  tts_voice   = {tts_voice}  (preset fallback — only used if clone is absent)\n"
        f"  tts_model   = {tts_model}\n"
        f"  tts_format  = {tts_audio_format}\n"
        f"  speech_rate = {tts_speech_rate}\n"
        f"  audio_dir   = {audio_dir}\n"
        f"  use_qwen    = {use_qwen_models}\n"
        f"  text_model  = {text_model}\n"
        f"  voice_clone = {_vc_summary}\n"
        f"  DASHSCOPE_API_KEY set = {bool(os.getenv('DASHSCOPE_API_KEY'))}\n"
        f"{'='*60}"
    )
    try:
        progress_placeholder = st.empty()
        _render_gen_card(progress_placeholder, "📋 Building voice curriculum…", 0, 3, request.topic)

        curriculum_agent = await create_voice_curriculum_agent(
            use_qwen=use_qwen_models,
            model_id=text_model,
        )
        curriculum = await generate_voice_curriculum(curriculum_agent, request)
        if not curriculum:
            raise ValueError("Failed to generate voice curriculum")

        _vo_total_steps = len(curriculum.chapters) + 2  # curriculum + N chapters + TTS collect
        _render_gen_card(progress_placeholder, "✅ Curriculum ready — generating voice chapters…", 1, _vo_total_steps, request.topic)

        chapter_agent = await create_voice_chapter_agent(
            use_qwen=use_qwen_models,
            model_id=text_model,
        )
        context = {
            "age": request.target_audience_age,
            "country": request.country,
            "learning_method": request.learning_method,
            "language": request.language,
            "pages_per_chapter": request.pages_per_chapter,
        }

        full_chapters = []
        previous_summaries: list[str] = []
        pending_audio_tts: list[tuple[int, object, object]] = []  # (ch_idx, chapter, task)

        # ── Inner coroutine: script generation + TTS for one chapter ──────────
        async def _audio_script_and_tts(ch_obj, ch_idx: int):
            """Generate audio script then synthesize TTS — runs as a background task."""
            scr = await generate_audio_script(
                chapter=ch_obj,
                book_title=curriculum.title,
                chapter_index=ch_idx,
                language=request.language,
                target_age=request.target_audience_age,
                use_qwen=use_qwen_models,
                model_id=text_model,
                curriculum=curriculum,
                total_chapters=len(curriculum.chapters),
            )
            _audio_logger.info(
                f"  [Ch {ch_idx+1}] Audio script: "
                f"{'OK (' + str(len(scr)) + ' chars)' if scr else 'NONE/FAILED'}"
            )
            tts_in = prepare_script_for_tts(scr if scr else ch_obj.markdown_content)
            _audio_logger.info(f"  [Ch {ch_idx+1}] TTS input: {len(tts_in)} chars")

            narration_result: AudioNarration | None = None
            _using_clone = bool(voice_clone_profile and voice_clone_profile.get("voice"))

            if _using_clone:
                vc_voice = voice_clone_profile.get("voice")
                vc_model = voice_clone_profile.get("target_model", "qwen3-tts-vc-realtime-2025-11-27")
                vc_name  = voice_clone_profile.get("name", "custom_voice")

                vc_p = await asyncio.to_thread(
                    narrate_chapter_vc,
                    chapter_title=ch_obj.chapter_title,
                    markdown_content=tts_in,
                    output_dir=audio_dir,
                    voice=vc_voice,
                    model=vc_model,
                    region=qwen_region,
                )
                if vc_p and os.path.exists(vc_p):
                    narration_result = AudioNarration(
                        chapter_title=ch_obj.chapter_title,
                        file_path=str(vc_p),
                        duration_seconds=0.0,
                        voice_id=vc_voice,
                        model=vc_model,
                        format=Path(vc_p).suffix.lstrip(".") or "wav",
                        size_bytes=os.path.getsize(vc_p),
                    )
                else:
                    # ── VC synthesis failed — try re-enrollment from saved sample ──
                    _audio_logger.error(
                        f"  [Ch {ch_idx+1}] ❌ Cloned-voice synthesis failed for '{vc_name}' "
                        f"(voice={vc_voice[:40]}...). "
                        f"Attempting auto-re-enrollment from saved sample."
                    )
                    sample_path = voice_clone_profile.get("sample_path")
                    _reenrolled = False
                    if sample_path and Path(sample_path).exists():
                        try:
                            api_safe = re.sub(r'[^a-z0-9]', '', vc_name.lower())[:20] or "myvoice"
                            _audio_logger.info(
                                f"  [Ch {ch_idx+1}] 🔄 Re-enrolling '{vc_name}' "
                                f"from {sample_path} (model={vc_model})"
                            )
                            new_voice = await asyncio.to_thread(
                                create_cloned_voice,
                                sample_path,
                                target_model=vc_model,
                                preferred_name=api_safe,
                                region=qwen_region,
                            )
                            if new_voice:
                                # Persist the fresh enrollment in the registry
                                voice_clone_profile["voice"] = new_voice
                                voice_clone_profile["updated_at"] = datetime.now().isoformat(timespec="seconds")
                                st.session_state.voice_clone_profile = voice_clone_profile
                                _fresh_reg = _load_voice_registry()
                                _fresh_reg[vc_name] = voice_clone_profile
                                _save_voice_registry(_fresh_reg)
                                _audio_logger.info(
                                    f"  [Ch {ch_idx+1}] ✅ Re-enrolled: {new_voice[:40]}... — retrying TTS"
                                )
                                # Retry synthesis with renewed voice
                                vc_p2 = await asyncio.to_thread(
                                    narrate_chapter_vc,
                                    chapter_title=ch_obj.chapter_title,
                                    markdown_content=tts_in,
                                    output_dir=audio_dir,
                                    voice=new_voice,
                                    model=vc_model,
                                    region=qwen_region,
                                )
                                if vc_p2 and os.path.exists(vc_p2):
                                    narration_result = AudioNarration(
                                        chapter_title=ch_obj.chapter_title,
                                        file_path=str(vc_p2),
                                        duration_seconds=0.0,
                                        voice_id=new_voice,
                                        model=vc_model,
                                        format=Path(vc_p2).suffix.lstrip(".") or "wav",
                                        size_bytes=os.path.getsize(vc_p2),
                                    )
                                    _reenrolled = True
                                else:
                                    _audio_logger.error(
                                        f"  [Ch {ch_idx+1}] ❌ Re-enrolled TTS also failed. "
                                        f"Chapter will not have audio."
                                    )
                            else:
                                _audio_logger.error(
                                    f"  [Ch {ch_idx+1}] ❌ Re-enrollment returned no voice. "
                                    f"Check DASHSCOPE_API_KEY and try re-cloning in Voice Cloning section."
                                )
                        except Exception as _reenroll_err:
                            _audio_logger.error(
                                f"  [Ch {ch_idx+1}] ❌ Re-enrollment exception: {_reenroll_err}"
                            )
                    else:
                        _audio_logger.error(
                            f"  [Ch {ch_idx+1}] ❌ No sample file found for re-enrollment "
                            f"(sample_path={sample_path!r}). "
                            f"Please re-clone the voice in the 🎤 Voice Cloning section."
                        )

            # Fallback to preset TTS voice when:
            #  a) no clone profile was ever active for this run, OR
            #  b) clone synthesis failed completely (after re-enrollment attempt)
            if narration_result is None:
                if _using_clone:
                    _audio_logger.warning(
                        f"  [Ch {ch_idx+1}] ⚠️ Cloned-voice synthesis exhausted — "
                        f"falling back to preset voice '{tts_voice}'. "
                        f"Re-clone the voice in the 🎤 Voice Cloning section if this persists."
                    )
                _audio_logger.info(
                    f"  [Ch {ch_idx+1}] Calling narrate_chapter: voice={tts_voice}, "
                    f"model={tts_model}, format={tts_audio_format}, rate={tts_speech_rate}"
                )
                narr = await asyncio.to_thread(
                    narrate_chapter,
                    chapter_title=ch_obj.chapter_title,
                    markdown_content=tts_in,
                    output_dir=audio_dir,
                    voice=tts_voice,
                    model=tts_model,
                    audio_format=tts_audio_format,
                    speech_rate=tts_speech_rate,
                    language=request.language,
                )
                if narr:
                    narration_result = narr
                    _audio_logger.info(
                        f"  [Ch {ch_idx+1}] ✅ Narration OK: {narr.file_path} "
                        f"({narr.size_bytes} bytes, ~{narr.duration_seconds:.0f}s)"
                    )
                else:
                    _audio_logger.error(f"  [Ch {ch_idx+1}] ❌ TTS synthesis failed")
            return narration_result

        # ── Sequential chapter text generation + background TTS ────────────────
        for i, outline in enumerate(curriculum.chapters):
            _render_gen_card(
                progress_placeholder,
                f"🎤 Voice chapter {i+1}/{len(curriculum.chapters)}: {outline.title[:50]}",
                i + 1, _vo_total_steps, request.topic,
            )
            chapter = await generate_voice_chapter(
                chapter_agent, outline, context,
                curriculum=curriculum,
                chapter_index=i,
                previous_summaries=previous_summaries,
            )
            if not chapter:
                continue

            previous_summaries.append(
                f"{chapter.chapter_title}: {outline.summary[:120]}"
            )
            full_chapters.append(chapter)

            # ── Fire TTS as background task while next chapter text generates ──
            tts_task = asyncio.create_task(_audio_script_and_tts(chapter, i))
            pending_audio_tts.append((i, chapter, tts_task))
            _render_gen_card(
                progress_placeholder,
                f"📝 Voice ch {i+1}/{len(curriculum.chapters)} done — 🔊 script+TTS running…",
                i + 1, _vo_total_steps, request.topic,
            )

        # ── Collect all background TTS tasks ──────────────────────────────────
        if pending_audio_tts:
            remaining = [t for _, _, t in pending_audio_tts if not t.done()]
            if remaining:
                _render_gen_card(
                    progress_placeholder,
                    f"⏳ Waiting for {len(remaining)} audio narration(s) to finish…",
                    len(curriculum.chapters) + 1, _vo_total_steps, request.topic,
                )
                await asyncio.gather(*remaining, return_exceptions=True)
            for ch_idx, chapter, tts_task in pending_audio_tts:
                try:
                    narration_result = tts_task.result()
                    if narration_result:
                        chapter.audio_narration = narration_result
                except Exception as _tts_err:
                    _audio_logger.error(f"  [Ch {ch_idx+1}] TTS task error: {_tts_err}")

        progress_placeholder.empty()
        if not full_chapters:
            raise ValueError("No voice chapters were generated")
        return curriculum, full_chapters

    except Exception as e:
        import traceback
        error_msg = f"❌ Error during audiobook-only generation: {str(e)}"
        print(f"\n{'='*60}")
        print(f"ERROR: {error_msg}")
        print(f"Traceback:\n{traceback.format_exc()}")
        print(f"{'='*60}\n")
        st.error(error_msg)
        return None, None


pending_mode = st.session_state.pending_generation_mode
pending_source = st.session_state.pending_generation_source

run_full_generation = generate_full_clicked or generate_full_from_chat or pending_mode == "full"
run_audio_only_generation = generate_audio_only_clicked or generate_audio_from_chat or pending_mode == "audio_only"

generation_source = pending_source if pending_mode else "form"
if pending_mode:
    st.session_state.pending_generation_mode = None
    st.session_state.pending_generation_source = None

if run_full_generation:
    # Create book request
    form_request = BookRequest(
        topic=topic,
        target_audience_age=target_audience_age,
        language=language,
        country=country,
        learning_method=learning_method,
        num_chapters=num_chapters,
        pages_per_chapter=pages_per_chapter,
        genre=book_genre,
    )
    request = _request_from_chat_or_form(generation_source, form_request)

    parsed_chat_data = st.session_state.chat_book_data if generation_source == "chat" else None
    runtime = _resolve_runtime_options(
        parsed_chat_data,
        {
            "generate_images": _form_ai_images,
            "use_ddg_images": _form_ddg_images,
            "images_per_chapter": int(_form_images_per_chapter) if _form_enable_images else 0,
            "use_qwen_models": use_qwen_models,
            "qwen_text_model": qwen_text_model,
            "enable_tts": enable_tts,
            "tts_voice": tts_voice,
            "tts_model": tts_model,
            "tts_audio_format": tts_audio_format,
            "tts_speech_rate": tts_speech_rate,
            "template_id": template_id,
            "palette_id": palette_id,
        },
    )

    # Apply form-tab image model / style selections
    qwen_image_model = _form_qwen_image_model
    art_style = _form_art_style

    if not _validate_generation_prereqs(
        use_qwen_models=runtime["use_qwen_models"],
        enable_tts=runtime["enable_tts"],
        voice_clone_profile=active_clone_profile,
        generate_images=runtime["generate_images"],
    ):
        st.stop()

    # Generate book asynchronously
    try:
        print(f"\n{'='*60}")
        print(f"📚 Starting book generation...")
        print(f"  Topic: {request.topic}")
        print(f"  Chapters: {request.num_chapters}")
        print(f"  Country: {request.country}")
        print(f"  Language: {request.language}")
        print(f"{'='*60}\n")
        
        # Create images directory inside books/images/{timestamp}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_books_dir = Path("books")
        images_dir_path = base_books_dir / "images" / timestamp
        images_dir_path.mkdir(parents=True, exist_ok=True)

        # Create audio directory if TTS enabled
        audio_dir_path = base_books_dir / "audio" / timestamp
        if runtime["enable_tts"]:
            audio_dir_path.mkdir(parents=True, exist_ok=True)

        _gen_t0 = time.perf_counter()

        # ── Route based on genre ────────────────────────────────────────
        _genre = getattr(request, "genre", "educational")
        if _genre != "educational":
            _progress_ph = st.empty()
            _genre_step = [0]  # mutable counter for closure
            def _genre_progress(msg: str, _ph=_progress_ph, _topic=request.topic, _ctr=_genre_step):
                _ctr[0] += 1
                _render_gen_card(_ph, msg, _ctr[0], max(_ctr[0] + 1, 4), _topic)
            curriculum, full_chapters = asyncio.run(
                _generate_genre_book_async(
                    request,
                    use_qwen=runtime["use_qwen_models"],
                    model_id=runtime["qwen_text_model"],
                    provider=os.getenv("MODEL_PROVIDER", "github"),
                    max_tokens_outline=max_tokens_curriculum,
                    max_tokens_chapter=max_tokens_chapter,
                    progress_callback=_genre_progress,
                )
            )
            _progress_ph.empty()

            # ── Image generation for genre books — all chapters in parallel ──
            if full_chapters and (runtime["generate_images"] or runtime["use_ddg_images"]):
                _imgs_per_ch = runtime["images_per_chapter"]
                _img_ph = st.empty()
                _render_gen_card(
                    _img_ph,
                    f"⚡ Generating images for all {len(full_chapters)} genre chapters in parallel…",
                    1, 2, request.topic,
                )

                async def _genre_images_async():
                    import re as _re2
                    # Pre-compute per-chapter metadata
                    ch_meta = []
                    for _i, _ch in enumerate(full_chapters):
                        _ch_folder = "".join(
                            c if c.isalnum() or c in (' ', '_', '-') else '_'
                            for c in _ch.chapter_title
                        ).replace(' ', '_')[:50]
                        _ch.generated_images = []
                        _descs = _ch.image_placeholders if hasattr(_ch, 'image_placeholders') else []
                        if not _descs:
                            _descs = _re2.findall(r'\[IMAGE:\s*([^\]]+)\]', _ch.markdown_content or '')
                            _ch.image_placeholders = _descs
                        ch_meta.append((_i, _ch, _ch_folder, _descs))

                    if runtime["generate_images"]:
                        _tasks, _task_meta = [], []
                        for _i, _ch, _ch_folder, _descs in ch_meta:
                            for _idx in range(_imgs_per_ch or 0):
                                _title = _descs[_idx] if _idx < len(_descs) else _ch.chapter_title
                                _tasks.append(asyncio.to_thread(
                                    generate_chapter_image,
                                    title=_title,
                                    summary=_title,
                                    output_dir=str(images_dir_path),
                                    chapter_name=_ch_folder,
                                    language=request.language,
                                    country=request.country,
                                    audience_age=request.target_audience_age,
                                    use_qwen_text=runtime["use_qwen_models"],
                                    text_model=runtime["qwen_text_model"],
                                    image_model=qwen_image_model,
                                    art_style=art_style,
                                ))
                                _task_meta.append((_i, _idx))
                        _results = await asyncio.gather(*_tasks, return_exceptions=True)
                        for (_ri, _ridx), _res in zip(_task_meta, _results):
                            _ch = full_chapters[_ri]
                            if isinstance(_res, Exception):
                                print(f"⚠️ Image {_ridx+1} ch {_ri+1} failed: {_res}")
                            elif _res:
                                _ch.generated_images.append(_res)
                                print(f"✅ Image {_ridx+1} ch {_ri+1}: {_ch.chapter_title}")
                            else:
                                print(f"⚠️ No image {_ridx+1} for genre ch {_ri+1}")

                    elif runtime["use_ddg_images"]:
                        _tasks, _task_meta = [], []
                        for _i, _ch, _ch_folder, _descs in ch_meta:
                            _ddg_dir = str(images_dir_path / _ch_folder)
                            for _idx in range(_imgs_per_ch or 0):
                                _query = _descs[_idx] if _idx < len(_descs) else f"{_ch.chapter_title} illustration"
                                _tasks.append(search_and_download_image(
                                    query=_query,
                                    output_dir=_ddg_dir,
                                    language=request.language.lower()[:2],
                                    country=request.country,
                                    safesearch="moderate",
                                ))
                                _task_meta.append((_i, _idx))
                        _results = await asyncio.gather(*_tasks, return_exceptions=True)
                        for (_ri, _ridx), _res in zip(_task_meta, _results):
                            _ch = full_chapters[_ri]
                            if isinstance(_res, Exception):
                                print(f"⚠️ DDG image {_ridx+1} ch {_ri+1} failed: {_res}")
                            elif _res:
                                _ch.generated_images.append(_res)

                    # Embed collected images into markdown for each chapter
                    for _, _ch, _, _ in ch_meta:
                        _ch.markdown_content = _embed_images_in_markdown(
                            _ch.markdown_content, _ch.generated_images
                        )

                asyncio.run(_genre_images_async())
                _img_ph.empty()
        else:
            curriculum, full_chapters = asyncio.run(
                generate_book_async(
                    request,
                    runtime["generate_images"],
                    runtime["use_qwen_models"],
                    qwen_region,
                    str(images_dir_path),
                    text_model=runtime["qwen_text_model"],
                    image_model=qwen_image_model,
                    images_per_chapter=runtime["images_per_chapter"],
                    use_ddg_images=runtime["use_ddg_images"],
                    enable_video_search=enable_video_search,
                    enable_tts=runtime["enable_tts"],
                    tts_voice=runtime["tts_voice"],
                    tts_model=runtime["tts_model"],
                    tts_audio_format=runtime["tts_audio_format"],
                    tts_speech_rate=runtime["tts_speech_rate"],
                    audio_dir=str(audio_dir_path),
                    art_style=art_style,
                    voice_clone_profile=active_clone_profile,
                    max_tokens_curriculum=max_tokens_curriculum,
                    max_tokens_chapter=max_tokens_chapter,
                )
            )
        
        if not curriculum or not full_chapters:
            print("\n❌ Book generation failed - curriculum or chapters is None\n")
            st.error("Book generation failed. Please try again.")
        else:
            # Step 4: Create output folder structure: books/{json,html,md,pdf}/{timestamp}
            output_data = {
                "book_request": request.model_dump(),
                "curriculum": curriculum.model_dump(),
                "chapters": [c.model_dump() for c in full_chapters]
            }
            
            # Create directory structure
            base_books_dir = Path("books")
            json_dir = base_books_dir / "json" / timestamp
            html_dir = base_books_dir / "html" / timestamp
            md_dir = base_books_dir / "md" / timestamp
            pdf_dir = base_books_dir / "pdf" / timestamp
            
            # Create all directories
            json_dir.mkdir(parents=True, exist_ok=True)
            html_dir.mkdir(parents=True, exist_ok=True)
            md_dir.mkdir(parents=True, exist_ok=True)
            pdf_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"\n📁 Folder structure created:")
            print(f"   {json_dir}/")
            print(f"   {html_dir}/")
            print(f"   {md_dir}/")
            print(f"   {pdf_dir}/")

            # Save JSON (fast — do first so it's always available)
            json_path = json_dir / f"book_output.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"✅ JSON saved: {json_path}")

            # Resolve template / palette
            effective_template_id = runtime.get("template_id", template_id)
            if effective_template_id == "auto":
                effective_template_id = auto_pick_template(request.topic)
                print(f"🤖 Auto-picked template: {effective_template_id} (topic: {request.topic})")
            effective_palette_id = runtime.get("palette_id", palette_id)

            html_path = html_dir / "libro_interactivo.html"
            md_path   = md_dir   / "libro_interactivo.md"
            pdf_path  = pdf_dir  / "libro_interactivo.pdf"

            book_output_obj = BookOutput(
                book_request=request,
                curriculum=curriculum,
                chapters=full_chapters,
            )

            # ── Write HTML + Markdown + PDF in parallel (all independent) ──────────
            import concurrent.futures as _cf

            def _write_html():
                generate_html_css_book_from_json(
                    request, curriculum, full_chapters, str(html_path),
                    template_id=effective_template_id,
                    palette_id=effective_palette_id,
                )
                print(f"✅ HTML saved: {html_path} (template: {effective_template_id}, palette: {effective_palette_id})")
                return True

            def _write_md():
                save_markdown_book(book_output_obj, str(md_path))
                print(f"✅ Markdown saved: {md_path}")
                return True

            def _write_pdf():
                try:
                    ok = generate_pdf_from_data(
                        request, curriculum, full_chapters,
                        str(pdf_path),
                        images_base=images_dir_path,
                    )
                    if ok:
                        print(f"✅ PDF saved: {pdf_path}")
                    else:
                        print(f"⚠️ PDF generation failed")
                    return ok
                except Exception as _pdf_err:
                    print(f"⚠️ PDF error: {_pdf_err}")
                    return False

            with _cf.ThreadPoolExecutor(max_workers=3) as _pool:
                _f_html = _pool.submit(_write_html)
                _f_md   = _pool.submit(_write_md)
                _f_pdf  = _pool.submit(_write_pdf)
                html_ok, md_ok, pdf_success = (
                    _f_html.result(), _f_md.result(), _f_pdf.result()
                )

            if pdf_success:
                st.success(f"📄 PDF generated successfully!")
            else:
                st.info(f"📱 PDF generation failed — HTML is ready to open or print to PDF from browser")

            # Save generation metrics
            st.session_state.gen_time = time.perf_counter() - _gen_t0
            st.session_state.gen_tokens_est = _estimate_tokens(curriculum, full_chapters)
            st.session_state.gen_model = runtime.get("qwen_text_model")

            # Save to session state
            st.session_state.book_generated = True
            st.session_state.json_path = str(json_path)
            st.session_state.html_path = str(html_path)
            st.session_state.md_path = str(md_path)
            st.session_state.pdf_path = str(pdf_path)
            st.session_state.output_data = output_data
            st.session_state.curriculum = curriculum
            st.session_state.full_chapters = full_chapters
            st.session_state.audio_narrations = [
                ch.audio_narration for ch in full_chapters
                if ch.audio_narration is not None
            ]
            st.session_state.audio_output_dir = str(audio_dir_path) if runtime["enable_tts"] else None

            # ─ Auto-apply accessibility options if pre-selected ────────────────────
            if auto_color_friendly and st.session_state.html_path and os.path.exists(st.session_state.html_path):
                with st.spinner("🎨 Applying color-friendly palette..."):
                    _cf_path = _apply_color_friendly_css(st.session_state.html_path)
                    if _cf_path:
                        st.session_state.color_friendly_path = _cf_path
                        st.success("✅ Color-friendly HTML ready!")

            if auto_blind_friendly and st.session_state.full_chapters:
                for _bfch in st.session_state.full_chapters:
                    _bfch.markdown_content = _strip_visual_for_blind(_bfch.markdown_content or "")

            print(f"\n✅ Book generated successfully in organized folders!\n")
            st.success("✅ Book generated successfully!")
            
    except Exception as e:
        import traceback
        error_msg = f"❌ Unexpected error: {str(e)}"
        print(f"\n{'='*60}")
        print(f"ERROR: {error_msg}")
        print(f"Traceback:\n{traceback.format_exc()}")
        print(f"{'='*60}\n")
        st.error(error_msg)


if run_audio_only_generation:
    form_request = BookRequest(
        topic=topic,
        target_audience_age=target_audience_age,
        language=language,
        country=country,
        learning_method=learning_method,
        num_chapters=num_chapters,
        pages_per_chapter=pages_per_chapter,
    )
    request = _request_from_chat_or_form(generation_source, form_request)
    parsed_chat_data = st.session_state.chat_book_data if generation_source == "chat" else None

    runtime = _resolve_runtime_options(
        parsed_chat_data,
        {
            "use_qwen_models": use_qwen_models,
            "qwen_text_model": qwen_text_model,
            "enable_tts": True,
            "tts_voice": tts_voice,
            "tts_model": tts_model,
            "tts_audio_format": tts_audio_format,
            "tts_speech_rate": tts_speech_rate,
            "generate_images": False,
            "use_ddg_images": False,
            "images_per_chapter": 0,
        },
    )

    if not runtime["enable_tts"]:
        st.error("❌ Audio-only mode requires voice generation enabled.")
        st.stop()

    if not _validate_generation_prereqs(
        use_qwen_models=runtime["use_qwen_models"],
        enable_tts=runtime["enable_tts"],
        voice_clone_profile=st.session_state.voice_clone_profile or active_clone_profile,
        generate_images=runtime.get("generate_images", False),
    ):
        st.stop()

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_books_dir = Path("books")
        audio_dir_path = base_books_dir / "audio" / timestamp
        json_dir = base_books_dir / "json" / timestamp
        md_dir = base_books_dir / "md" / timestamp
        audio_dir_path.mkdir(parents=True, exist_ok=True)
        json_dir.mkdir(parents=True, exist_ok=True)
        md_dir.mkdir(parents=True, exist_ok=True)

        _gen_t0 = time.perf_counter()
        # For audio-only mode, honour the saved clone profile regardless of whether
        # the form-tab "Enable Audio Narration" / "Use Cloned Voice" checkboxes are
        # ticked — those guard the full-book flow, not the dedicated audio-only path.
        _ao_clone = st.session_state.voice_clone_profile or active_clone_profile
        curriculum, full_chapters = asyncio.run(
            generate_audio_book_only_async(
                request=request,
                use_qwen_models=runtime["use_qwen_models"],
                qwen_region=qwen_region,
                text_model=runtime["qwen_text_model"],
                tts_voice=runtime["tts_voice"],
                tts_model=runtime["tts_model"],
                tts_audio_format=runtime["tts_audio_format"],
                tts_speech_rate=runtime["tts_speech_rate"],
                audio_dir=str(audio_dir_path.resolve()),
                voice_clone_profile=_ao_clone,
            )
        )
        st.session_state.gen_time = time.perf_counter() - _gen_t0
        st.session_state.gen_tokens_est = _estimate_tokens(curriculum, full_chapters)
        st.session_state.gen_model = runtime.get("qwen_text_model")

        if not curriculum or not full_chapters:
            st.error("Audiobook-only generation failed. Please try again.")
        else:
            output_data = {
                "book_request": request.model_dump(),
                "curriculum": curriculum.model_dump(),
                "chapters": [c.model_dump() for c in full_chapters],
                "mode": "audio_only",
            }
            json_path = json_dir / "book_output_audio_only.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            md_path = md_dir / "libro_audio_only.md"
            book_output = BookOutput(
                book_request=request,
                curriculum=curriculum,
                chapters=full_chapters,
            )
            save_markdown_book(book_output, str(md_path))

            collected_audio = _collect_audio_narrations(full_chapters, audio_dir_path)
            if not collected_audio:
                raise ValueError(
                    f"Audiobook-only generation completed but no playable audio files were created in: {audio_dir_path}"
                )

            st.session_state.book_generated = True
            st.session_state.json_path = str(json_path)
            st.session_state.html_path = None
            st.session_state.md_path = str(md_path)
            st.session_state.pdf_path = None
            st.session_state.output_data = output_data
            st.session_state.curriculum = curriculum
            st.session_state.full_chapters = full_chapters
            st.session_state.audio_narrations = collected_audio
            st.session_state.audio_output_dir = str(audio_dir_path)

            st.success("✅ Audiobook-only generation completed!")
            st.info(f"📂 Audio saved in: {audio_dir_path.resolve()}")

    except Exception as e:
        import traceback
        error_msg = f"❌ Unexpected audio-only generation error: {str(e)}"
        print(f"\n{'='*60}")
        print(f"ERROR: {error_msg}")
        print(f"Traceback:\n{traceback.format_exc()}")
        print(f"{'='*60}\n")
        st.error(error_msg)


# === Display output if generated ===
if st.session_state.book_generated and st.session_state.curriculum:
    st.divider()

    # === Generation Stats ===
    _chapters_list = st.session_state.full_chapters or []
    _num_chapters = len(_chapters_list)

    # Word count across all chapters
    _total_words = sum(
        len((ch.markdown_content or "").split())
        for ch in _chapters_list
    )

    # Image count
    _total_images = sum(
        len(getattr(ch, "generated_images", None) or [])
        for ch in _chapters_list
    )

    # Audio files count
    _audio_count = len([
        n for n in (st.session_state.audio_narrations or [])
        if n and getattr(n, "file_path", None)
    ])

    # Total audio size in MB
    _audio_mb = sum(
        (getattr(n, "size_bytes", 0) or 0)
        for n in (st.session_state.audio_narrations or [])
        if n
    ) / (1024 * 1024)

    st.subheader("📊 Generation Summary")

    # --- compute / recover metrics at display time ---
    _disp_tokens = st.session_state.gen_tokens_est
    if not _disp_tokens and st.session_state.full_chapters:
        _disp_tokens = _estimate_tokens(
            st.session_state.curriculum, st.session_state.full_chapters
        )
    _disp_model = st.session_state.gen_model
    _est_cost = _estimate_cost(_disp_tokens or 0, _disp_model) if _disp_tokens else None

    _m1, _m2, _m3 = st.columns(3)
    _m4, _m5, _m6, _m7 = st.columns(4)

    # Row 1: timing / tokens / cost
    if st.session_state.gen_time:
        _min, _sec = divmod(int(st.session_state.gen_time), 60)
        _time_str = f"{_min}m {_sec}s" if _min else f"{_sec}s"
        _m1.metric("⏱️ Generation Time", _time_str)
    else:
        _m1.metric("⏱️ Generation Time", "—")

    _m2.metric(
        "📝 Tokens (est.)",
        f"{_disp_tokens:,}" if _disp_tokens else "—",
        help="Rough estimate: output word count × 1.33 subword factor.",
    )

    if _est_cost is None:
        _m3.metric(
            "💰 Est. Cost",
            "—",
            help="Model not found in pricing table; update _COST_PER_1M_OUTPUT in app.py.",
        )
    else:
        _cost_str = f"${_est_cost:.4f}" if _est_cost < 0.01 else f"${_est_cost:.3f}"
        _rate = _COST_PER_1M_OUTPUT.get(_disp_model or "", 0)
        _m3.metric(
            "💰 Est. Cost",
            _cost_str,
            help=(
                f"Model: {_disp_model}\n"
                f"Rate: ${_rate:.4f} / 1M output tokens\n"
                "Input tokens not included (output-only estimate).\n"
                "Commercial list price shown regardless of free-tier quota."
            ),
        )

    # Row 2: chapters / words / images / audio
    _m4.metric(
        "📚 Chapters",
        _num_chapters,
    )
    _m5.metric(
        "📖 Word Count",
        f"{_total_words:,}" if _total_words else "—",
        help="Total words across all generated chapter content.",
    )
    _m6.metric(
        "🖼️ Images",
        _total_images if _total_images else "—",
        help="AI-generated or web-searched images embedded in the book.",
    )
    if _audio_count:
        _m7.metric(
            "🔊 Audio Files",
            _audio_count,
            delta=f"{_audio_mb:.1f} MB" if _audio_mb > 0 else None,
            delta_color="off",
            help="Number of narrated chapter audio files generated.",
        )
    else:
        _m7.metric("🔊 Audio Files", "—")

    # === Download Buttons ===
    st.subheader("📥 Download")
    colA, colB, colC, colD = st.columns(4)
    
    with colA:
        with open(st.session_state.json_path, "rb") as f:
            st.download_button(
                label="📊 JSON",
                data=f,
                file_name="book_output.json",
                mime="application/json"
            )
    
    with colB:
        if st.session_state.html_path and os.path.exists(st.session_state.html_path):
            with open(st.session_state.html_path, "rb") as f:
                st.download_button(
                    label="🌐 HTML",
                    data=f,
                    file_name="libro_interactivo.html",
                    mime="text/html"
                )
    
    with colC:
        if st.session_state.md_path and os.path.exists(st.session_state.md_path):
            with open(st.session_state.md_path, "rb") as f:
                st.download_button(
                    label="📝 Markdown",
                    data=f,
                    file_name="libro_interactivo.md",
                    mime="text/markdown"
                )
    
    with colD:
        if st.session_state.pdf_path and os.path.exists(st.session_state.pdf_path):
            with open(st.session_state.pdf_path, "rb") as f:
                st.download_button(
                    label="📄 PDF",
                    data=f,
                    file_name="libro_interactivo.pdf",
                    mime="application/pdf"
                )

    # === Audiobook Download ===
    audio_files = list(st.session_state.audio_narrations or [])
    if not audio_files:
        fallback_audio_dir = st.session_state.audio_output_dir
        if not fallback_audio_dir and st.session_state.json_path:
            json_parent = Path(st.session_state.json_path).parent
            fallback_audio_dir = Path("books") / "audio" / json_parent.name
        audio_files = _collect_audio_narrations(st.session_state.full_chapters, fallback_audio_dir)
        st.session_state.audio_narrations = audio_files

    if audio_files:
        st.subheader("🔊 Audiobook")
        total_dur = sum(a.duration_seconds for a in audio_files)
        total_kb = sum(a.size_bytes for a in audio_files) / 1024
        st.caption(
            f"{len(audio_files)} chapters · ~{total_dur:.0f}s total · "
            f"{total_kb:.0f} KB"
        )

        # Combine all audio into a single download (ZIP)
        import io, zipfile
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, nar in enumerate(audio_files):
                fname = Path(nar.file_path).name
                zf.write(nar.file_path, f"{idx+1:02d}_{fname}")
        zip_buf.seek(0)
        st.download_button(
            label="📥 Download All Audio (ZIP)",
            data=zip_buf,
            file_name="audiobook.zip",
            mime="application/zip",
            key="audiobook_zip_dl",
        )

        # Also offer individual chapter audio list
        with st.expander("🎧 Individual Chapter Audio", expanded=False):
            for idx, nar in enumerate(audio_files):
                acol1, acol2 = st.columns([3, 1])
                with acol1:
                    with open(nar.file_path, "rb") as af:
                        st.audio(af.read(), format=_audio_mime(nar.format))
                with acol2:
                    st.caption(f"{nar.chapter_title[:30]}")
                    st.caption(f"~{nar.duration_seconds:.0f}s · {nar.size_bytes/1024:.0f}KB")

    # === Curriculum & chapter previews (collapsed) ===
    with st.expander("📘 Curriculum JSON"):
        st.json(st.session_state.curriculum.model_dump())

    for i, ch in enumerate(st.session_state.full_chapters):
        with st.expander(f"Ch {i+1}: {ch.chapter_title}"):
            # Audio narration player
            if ch.audio_narration and ch.audio_narration.file_path and os.path.exists(ch.audio_narration.file_path):
                st.markdown("**🔊 Audio Narration**")
                with open(ch.audio_narration.file_path, "rb") as af:
                    audio_bytes = af.read()
                    st.audio(audio_bytes, format=_audio_mime(ch.audio_narration.format))
                    st.caption(
                        f"Voice: {ch.audio_narration.voice_id} · "
                        f"~{ch.audio_narration.duration_seconds:.0f}s · "
                        f"{ch.audio_narration.size_bytes / 1024:.0f} KB"
                    )
                    st.download_button(
                        label=f"📥 Download Audio ({ch.audio_narration.format.upper()})",
                        data=audio_bytes,
                        file_name=Path(ch.audio_narration.file_path).name,
                        mime=_audio_mime(ch.audio_narration.format),
                        key=f"audio_dl_{i}",
                    )

            st.divider()
            # Sanitize markdown for Streamlit display — strips markers that
            # look broken (image placeholders, video tags, raw Windows paths,
            # and unmatched $ signs that confuse Streamlit's LaTeX renderer).
            def _sanitize_md_for_display(text: str) -> str:
                if not text:
                    return ""
                import re as _re
                # Remove [IMAGE: ...] placeholders
                text = _re.sub(r'\[IMAGE:[^\]]*\]', '', text)
                # Remove [VIDEO: ...] placeholders
                text = _re.sub(r'\[VIDEO:[^\]]*\]', '', text)
                # Remove 🎬 video markers (various forms LLM generates)
                text = _re.sub(r'[\U0001F3AC]\s*\*{0,2}[Vv]ideo\*{0,2}:?[^\n]*', '', text)
                # Remove markdown images referencing local file paths — shown separately via st.image()
                text = _re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
                # Remove lines that only contain asterisks / dashes (decorative separators that render oddly)
                text = _re.sub(r'^\s*[\*\-]{3,}\s*$', '', text, flags=_re.MULTILINE)
                # Strip trailing whitespace per line and collapse 3+ blank lines
                text = _re.sub(r'\n{3,}', '\n\n', text)
                return text.strip()
            st.markdown(_sanitize_md_for_display(ch.markdown_content))

            # Generated images
            if hasattr(ch, 'generated_images') and ch.generated_images:
                for j, img in enumerate(ch.generated_images, 1):
                    st.caption(img.description)
                    st.image(img.url, width='stretch')

            # Videos with QR codes
            if hasattr(ch, 'videos') and ch.videos:
                st.markdown("**🎬 Recommended Videos**")
                for v in ch.videos:
                    st.markdown(f"[{v.title}]({v.url})")
                    if v.qr_code:
                        st.image(v.qr_code, width=150, caption="Scan QR to watch")


# === Fallback audio downloads (only from current session, never test fixtures) ===
_session_audio_dir = st.session_state.get("audio_output_dir")
if _session_audio_dir:
    _session_narrations = _collect_audio_narrations(chapters=None, fallback_dir=_session_audio_dir)
    if _session_narrations and not (st.session_state.get("book_generated") and st.session_state.get("audio_narrations")):
        st.divider()
        st.subheader("🔊 Audio Downloads")
        st.caption(f"Session audio folder: {_session_audio_dir}")

        import io, zipfile
        latest_zip = io.BytesIO()
        with zipfile.ZipFile(latest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, nar in enumerate(_session_narrations):
                src = Path(nar.file_path)
                if src.exists():
                    zf.write(src, f"{idx+1:02d}_{src.name}")
        latest_zip.seek(0)

        st.download_button(
            label="📥 Download Session Audio (ZIP)",
            data=latest_zip,
            file_name="session_audiobook.zip",
            mime="application/zip",
            key="session_audio_zip_dl",
        )
elif Path("books/audio").exists() and not st.session_state.get("book_generated"):
    st.divider()
    st.subheader("🔊 Audio Downloads")
    st.info("No audio for this session yet. Generate a book with voice enabled to create audio.")