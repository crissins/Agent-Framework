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


async def _run_chat_turn(user_message: str) -> str:
    """Run one chat turn against the conversational agent."""
    if st.session_state.chat_agent is None:
        st.session_state.chat_agent = await create_chat_agent(use_qwen=True)

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

_DOTENV_PATH = Path(__file__).parent / ".env"


def _save_dotenv(github_token: str, dashscope_key: str, dashscope_region: str,
                 anthropic_key: str = "", azure_key: str = "",
                 azure_endpoint: str = "", azure_deployment: str = "") -> str:
    """Write/update provider keys in .env. Existing unrelated lines are preserved."""
    managed_keys = {
        "GITHUB_TOKEN", "DASHSCOPE_API_KEY", "DASHSCOPE_REGION",
        "ANTHROPIC_API_KEY",
        "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT_NAME",
    }
    new_values = {
        "GITHUB_TOKEN": github_token.strip(),
        "DASHSCOPE_API_KEY": dashscope_key.strip(),
        "DASHSCOPE_REGION": dashscope_region.strip(),
        "ANTHROPIC_API_KEY": anthropic_key.strip(),
        "AZURE_OPENAI_API_KEY": azure_key.strip(),
        "AZURE_OPENAI_ENDPOINT": azure_endpoint.strip(),
        "AZURE_OPENAI_DEPLOYMENT_NAME": azure_deployment.strip(),
    }

    existing_lines: list[str] = []
    if _DOTENV_PATH.exists():
        existing_lines = _DOTENV_PATH.read_text(encoding="utf-8").splitlines()

    # Rewrite managed keys in-place; remember which ones were updated
    updated_keys: set[str] = set()
    out_lines: list[str] = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            out_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in managed_keys:
            val = new_values[key]
            if val:
                out_lines.append(f'{key}="{val}"')
            # if empty, drop the line (don't save blank keys)
            updated_keys.add(key)
        else:
            out_lines.append(line)

    # Append keys that weren't already present
    for key in managed_keys:
        if key not in updated_keys and new_values[key]:
            out_lines.append(f'{key}="{new_values[key]}"')

    _DOTENV_PATH.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    saved = [k for k in managed_keys if new_values[k]]
    return f"✅ Saved to .env: {', '.join(sorted(saved))}" if saved else "⚠️ Nothing to save — all fields are empty."


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

    return resolved


def _validate_generation_prereqs(
    use_qwen_models: bool,
    enable_tts: bool,
    voice_clone_profile: dict | None,
) -> bool:
    """Validate API-key prerequisites for selected generation path."""
    model_ok, model_msg = validate_api_keys(use_qwen_models)
    if not model_ok:
        st.error(model_msg)
        return False

    needs_dashscope = enable_tts or bool(voice_clone_profile and voice_clone_profile.get("voice"))
    if needs_dashscope and not os.getenv("DASHSCOPE_API_KEY"):
        st.error("❌ Missing DASHSCOPE_API_KEY required for voice generation / voice cloning.")
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
            help_text="Personal Access Token for GitHub Models (GITHUB_TOKEN).",
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

        if st.button("💾 Save to .env", help="Persist keys & region to .env so they load automatically on next start."):
            msg = _save_dotenv(
                github_token=_github_key,
                dashscope_key=_dash_key,
                dashscope_region=qwen_region,
                anthropic_key=_anthropic_key,
                azure_key=_azure_key,
                azure_endpoint=_azure_ep,
                azure_deployment=_azure_dep,
            )
            if msg.startswith("✅"):
                st.success(msg)
            else:
                st.warning(msg)

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
                ["qwen-flash", "qwen-plus", "qwen-max", "qwen3-max"],
                index=0,
                help="qwen-flash is fastest; qwen-max is highest quality",
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
                    "claude-3-5-haiku-20241022",
                    "claude-3-5-sonnet-20241022",
                    "claude-3-7-sonnet-20250219",
                ],
                index=0,
                help="Haiku is fastest; Sonnet 3.7 is highest quality",
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
        enable_tts = st.checkbox(
            "🎙️ Enable Audio Narration",
            value=True,
            help="Generate spoken narration for each chapter using Qwen3 TTS-VC",
        )

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
                    # Auto-enable the Use Cloned Voice checkbox
                    st.session_state["use_cloned_voice_cb"] = True
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
                        voice_param = create_cloned_voice(
                            sample_path,
                            target_model=clone_model,
                            preferred_name=slug_name,
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
                    except Exception as e:
                        st.error(f"❌ Clone failed: {e}")

                if st.button("🧹 Clear recordings", key="voice_clear_btn"):
                    st.session_state.voice_recordings = []
                    st.session_state.last_voice_clip_sig = None
                    st.rerun()
        else:
            st.warning("Upgrade Streamlit for microphone support.")

        if st.session_state.voice_clone_profile:
            st.markdown("**✅ Active Clone**")
            st.json(st.session_state.voice_clone_profile)

    # ── Book Template ────────────────────────────────────────────────────
    with st.expander("📐 Book Template", expanded=False):
        _tmpl_choices = template_choices()
        _tmpl_option_ids = [t_id for _, t_id in _tmpl_choices]
        template_id = st.selectbox(
            "Visual Template",
            options=_tmpl_option_ids,
            index=0,
            format_func=lambda tid: next(
                (label for label, t_id in _tmpl_choices if t_id == tid),
                tid,
            ),
            help="Controls page borders, ornaments, fonts, and colour scheme. "
                 "'Auto' picks the best template based on topic.",
        )
        if template_id != "auto":
            _selected_tmpl = get_template(template_id)
            st.caption(f"{_selected_tmpl.emoji} {_selected_tmpl.description}")
        else:
            st.caption("🤖 The system will choose the best template based on your topic.")

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
# MAIN PAGE — Book Specification
# ══════════════════════════════════════════════════════════════════════════
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

c5, c6, c7 = st.columns(3)
with c5:
    learning_method = st.selectbox("🧠 Method", ["Scandinavian", "Montessori", "Project-Based"])
with c6:
    num_chapters = st.slider("📖 Chapters", 2, 12, 2)
with c7:
    pages_per_chapter = st.slider("📄 Pages/Ch", 1, 20, 1)

st.divider()

# ══════════════════════════════════════════════════════════════════════════
# MAIN PAGE — Chat Window
# ══════════════════════════════════════════════════════════════════════════
st.subheader("💬 Chat with the Book Assistant")
st.caption("Describe your book idea and the assistant will guide the full specification. Or skip and use the form above.")

if not st.session_state.chat_messages:
    st.info("💡 Example: 'I want a book about ocean animals for 9-year-olds in Mexico'")

for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_prompt = st.chat_input("Type your message...")
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
    st.success("✅ Request captured from chat. Generation will use chat options.")

st.divider()

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
    
    try:
        # Step 2: Generate curriculum (use selected text model when provided)
        curriculum_agent = await create_curriculum_agent(use_qwen=use_qwen_models, model_id=text_model)
        curriculum = await generate_curriculum(curriculum_agent, request, max_tokens=max_tokens_curriculum)
        
        if not curriculum:
            raise ValueError("Failed to generate curriculum")

        # Step 3: Generate all chapters (use selected text model when provided)
        chapter_agent = await create_chapter_agent(use_qwen=use_qwen_models, model_id=text_model)
        context = {
            "age": request.target_audience_age,
            "country": request.country,
            "learning_method": request.learning_method,
            "language": request.language,
            "pages_per_chapter": request.pages_per_chapter
        }

        full_chapters = []
        progress_placeholder = st.empty()
        
        for i, outline in enumerate(curriculum.chapters):
            progress_placeholder.info(f"📝 Generating Chapter {i+1}/{len(curriculum.chapters)}...")
            chapter = await generate_chapter(
                chapter_agent, outline, context,
                max_tokens=max_tokens_chapter,
                images_per_chapter=images_per_chapter if (generate_images or use_ddg_images) else 0,
            )
            
            if chapter:
                # Generate N images per chapter as introduction
                if generate_images and images_per_chapter and images_per_chapter > 0:
                    progress_placeholder.info(
                        f"📝 Chapter {i+1}/{len(curriculum.chapters)} - 🎨 Generating {images_per_chapter} image(s)..."
                    )
                    # Create clean chapter folder name
                    chapter_folder = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in chapter.chapter_title)
                    chapter_folder = chapter_folder.replace(' ', '_')[:50]
                    chapter.generated_images = []
                    # Use each [IMAGE: desc] placeholder as the unique prompt
                    placeholder_descs = chapter.image_placeholders if hasattr(chapter, 'image_placeholders') else []
                    for idx in range(images_per_chapter):
                        if idx < len(placeholder_descs):
                            img_title = placeholder_descs[idx]
                            img_summary = placeholder_descs[idx]
                        else:
                            img_title = f"{chapter.chapter_title} - illustration {idx+1}"
                            img_summary = outline.summary
                        img = generate_chapter_image(
                            title=img_title,
                            summary=img_summary,
                            output_dir=images_dir,
                            chapter_name=chapter_folder,
                            language=request.language,
                            country=request.country,
                            audience_age=request.target_audience_age,
                            use_qwen_text=use_qwen_models,
                            text_model=text_model,
                            image_model=image_model,
                            art_style=art_style,
                        )
                        if img:
                            chapter.generated_images.append(img)
                            print(f"✅ Image {idx+1} generated for chapter: {chapter.chapter_title}")
                        else:
                            print(f"⚠️ Failed to generate image {idx+1} for chapter: {chapter.chapter_title}")

                # DDG safe-search images (alternative to AI generation)
                if use_ddg_images and images_per_chapter and images_per_chapter > 0:
                    progress_placeholder.info(
                        f"📝 Chapter {i+1}/{len(curriculum.chapters)} - 🔍 Searching images (DuckDuckGo)..."
                    )
                    chapter_folder = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in chapter.chapter_title)
                    chapter_folder = chapter_folder.replace(' ', '_')[:50]
                    ddg_img_dir = str(Path(images_dir) / chapter_folder)
                    chapter.generated_images = []
                    for idx in range(images_per_chapter):
                        query = f"{outline.title} {outline.summary[:60]} educational children"
                        ddg_img = await search_and_download_image(
                            query=query,
                            output_dir=ddg_img_dir,
                            language=request.language.lower()[:2],
                            country=request.country,
                            safesearch="moderate",
                        )
                        if ddg_img:
                            chapter.generated_images.append(ddg_img)
                            print(f"✅ DDG Image {idx+1} found for chapter: {chapter.chapter_title}")
                        else:
                            print(f"⚠️ No DDG image found {idx+1} for chapter: {chapter.chapter_title}")

                # YouTube video search
                if enable_video_search:
                    progress_placeholder.info(
                        f"📝 Chapter {i+1}/{len(curriculum.chapters)} - 🎬 Searching YouTube videos..."
                    )
                    # Extract [VIDEO: ...] queries from chapter markdown
                    video_queries = re.findall(r'\[VIDEO:\s*([^\]]+)\]', chapter.markdown_content)
                    if not video_queries:
                        # Fallback: use chapter title as a single query
                        video_queries = [f"{outline.title} {request.language} educational"]
                    videos = await search_videos_for_chapter(
                        chapter_title=chapter.chapter_title,
                        video_queries=video_queries,
                        topic=request.topic,
                        language=request.language,
                        country=request.country,
                    )
                    if videos:
                        chapter.videos = videos
                        for v in videos:
                            # Embed video QR codes in markdown
                            chapter.markdown_content += (
                                f"\n\n---\n🎬 **Video recomendado:** [{v.title}]({v.url})\n\n"
                                f"![QR Code]({v.qr_code})\n"
                            )
                        print(f"✅ {len(videos)} video(s) found for chapter: {chapter.chapter_title}")

                # Embed generated images into [IMAGE:] placeholders with correct paths
                # and style remaining [IMAGE:]/[VIDEO:] as callouts
                chapter.markdown_content = _embed_images_in_markdown(
                    chapter.markdown_content,
                    chapter.generated_images if hasattr(chapter, 'generated_images') else []
                )

                # TTS narration (with voice clone fallback)
                if enable_tts:
                    progress_placeholder.info(
                        f"📝 Chapter {i+1}/{len(curriculum.chapters)} - 🔊 Generating audio narration..."
                    )
                    chapter_narration: AudioNarration | None = None

                    # Try cloned voice first (if available)
                    if voice_clone_profile and voice_clone_profile.get("voice"):
                        progress_placeholder.info(
                            f"📝 Chapter {i+1}/{len(curriculum.chapters)} - 🎤 Synthesizing cloned-voice audio..."
                        )
                        try:
                            vc_path = narrate_chapter_vc(
                                chapter_title=chapter.chapter_title,
                                markdown_content=chapter.markdown_content,
                                output_dir=audio_dir,
                                voice=voice_clone_profile.get("voice"),
                                model=voice_clone_profile.get("target_model", "qwen3-tts-vc-2026-01-22"),
                                region=qwen_region,
                            )
                            if vc_path and os.path.exists(vc_path):
                                chapter_narration = AudioNarration(
                                    chapter_title=chapter.chapter_title,
                                    file_path=str(vc_path),
                                    duration_seconds=0.0,
                                    voice_id=voice_clone_profile.get("voice", ""),
                                    model=voice_clone_profile.get("target_model", "qwen3-tts-vc-2026-01-22"),
                                    format=Path(vc_path).suffix.lstrip(".") or "wav",
                                    size_bytes=os.path.getsize(vc_path),
                                )
                        except Exception as vc_err:
                            print(f"⚠️ Voice clone synthesis failed: {vc_err}")

                        if chapter_narration is None:
                            print(
                                f"⚠️ Cloned-voice synthesis failed for chapter {i+1}; "
                                f"falling back to standard TTS..."
                            )

                    # Standard TTS fallback
                    if chapter_narration is None:
                        print(
                            f"🔊 [FullBook TTS] Chapter {i+1}: '{chapter.chapter_title}' — "
                            f"voice={tts_voice}, model={tts_model}, format={tts_audio_format}, "
                            f"rate={tts_speech_rate}, md_len={len(chapter.markdown_content)}, "
                            f"output_dir={audio_dir}"
                        )
                        narration = narrate_chapter(
                            chapter_title=chapter.chapter_title,
                            markdown_content=chapter.markdown_content,
                            output_dir=audio_dir,
                            voice=tts_voice,
                            model=tts_model,
                            audio_format=tts_audio_format,
                            speech_rate=tts_speech_rate,
                            language=request.language,
                        )
                        if narration:
                            chapter_narration = narration

                    if chapter_narration:
                        chapter.audio_narration = chapter_narration
                        print(
                            f"🔊 ✅ Narration OK: {chapter_narration.file_path} "
                            f"({chapter_narration.size_bytes} bytes, ~{chapter_narration.duration_seconds:.0f}s)"
                        )
                    else:
                        print(
                            f"⚠️ ❌ TTS FAILED for chapter: {chapter.chapter_title}. "
                            f"narrate_chapter returned None — check DashScope logs above."
                        )

                full_chapters.append(chapter)
            else:
                st.warning(f"⚠️ Failed to generate chapter: {outline.title}")

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
    _audio_logger.info(
        f"\n{'='*60}\n"
        f"🎧 AUDIOBOOK-ONLY PIPELINE STARTING\n"
        f"  topic       = {request.topic}\n"
        f"  language    = {request.language}\n"
        f"  tts_voice   = {tts_voice}\n"
        f"  tts_model   = {tts_model}\n"
        f"  tts_format  = {tts_audio_format}\n"
        f"  speech_rate = {tts_speech_rate}\n"
        f"  audio_dir   = {audio_dir}\n"
        f"  use_qwen    = {use_qwen_models}\n"
        f"  text_model  = {text_model}\n"
        f"  voice_clone = {voice_clone_profile is not None}\n"
        f"  DASHSCOPE_API_KEY set = {bool(os.getenv('DASHSCOPE_API_KEY'))}\n"
        f"{'='*60}"
    )
    try:
        curriculum_agent = await create_voice_curriculum_agent(
            use_qwen=use_qwen_models,
            model_id=text_model,
        )
        curriculum = await generate_voice_curriculum(curriculum_agent, request)
        if not curriculum:
            raise ValueError("Failed to generate voice curriculum")

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
        progress_placeholder = st.empty()

        for i, outline in enumerate(curriculum.chapters):
            progress_placeholder.info(f"🎙️ Generating voice chapter {i+1}/{len(curriculum.chapters)}...")
            chapter = await generate_voice_chapter(
                chapter_agent, outline, context,
                curriculum=curriculum,
                chapter_index=i,
                previous_summaries=previous_summaries,
            )
            if not chapter:
                continue

            # Track chapter summaries for narrative continuity
            previous_summaries.append(
                f"{chapter.chapter_title}: {outline.summary[:120]}"
            )

            script = await generate_audio_script(
                chapter=chapter,
                book_title=curriculum.title,
                chapter_index=i,
                language=request.language,
                target_age=request.target_audience_age,
                use_qwen=use_qwen_models,
                model_id=text_model,
                curriculum=curriculum,
                total_chapters=len(curriculum.chapters),
            )
            _audio_logger.info(
                f"  [Ch {i+1}] Audio script result: "
                f"{'OK (' + str(len(script)) + ' chars)' if script else 'NONE/FAILED'}"
            )
            tts_input = prepare_script_for_tts(script if script else chapter.markdown_content)
            _audio_logger.info(
                f"  [Ch {i+1}] TTS input prepared: {len(tts_input)} chars, "
                f"preview: {tts_input[:120]}..."
            )
            chapter_narration: AudioNarration | None = None

            if voice_clone_profile and voice_clone_profile.get("voice"):
                progress_placeholder.info(f"🎤 Synthesizing cloned-voice audio {i+1}/{len(curriculum.chapters)}...")
                vc_path = narrate_chapter_vc(
                    chapter_title=chapter.chapter_title,
                    markdown_content=tts_input,
                    output_dir=audio_dir,
                    voice=voice_clone_profile.get("voice"),
                    model=voice_clone_profile.get("target_model", "qwen3-tts-vc-2026-01-22"),
                    region=qwen_region,
                )
                if vc_path and os.path.exists(vc_path):
                    chapter_narration = AudioNarration(
                        chapter_title=chapter.chapter_title,
                        file_path=str(vc_path),
                        duration_seconds=0.0,
                        voice_id=voice_clone_profile.get("voice", ""),
                        model=voice_clone_profile.get("target_model", "qwen3-tts-vc-2026-01-22"),
                        format=Path(vc_path).suffix.lstrip(".") or "mp3",
                        size_bytes=os.path.getsize(vc_path),
                    )
                else:
                    progress_placeholder.warning(
                        f"⚠️ Cloned-voice synthesis failed for chapter {i+1}; falling back to standard TTS..."
                    )

            if chapter_narration is None:
                progress_placeholder.info(f"🔊 Synthesizing chapter audio {i+1}/{len(curriculum.chapters)}...")
                _audio_logger.info(
                    f"  [Ch {i+1}] Calling narrate_chapter: voice={tts_voice}, "
                    f"model={tts_model}, format={tts_audio_format}, "
                    f"rate={tts_speech_rate}, dir={audio_dir}"
                )
                narration = narrate_chapter(
                    chapter_title=chapter.chapter_title,
                    markdown_content=tts_input,
                    output_dir=audio_dir,
                    voice=tts_voice,
                    model=tts_model,
                    audio_format=tts_audio_format,
                    speech_rate=tts_speech_rate,
                    language=request.language,
                )
                if narration:
                    chapter_narration = narration
                    _audio_logger.info(
                        f"  [Ch {i+1}] ✅ Narration OK: {narration.file_path} "
                        f"({narration.size_bytes} bytes, ~{narration.duration_seconds:.0f}s)"
                    )
                else:
                    _audio_logger.error(
                        f"  [Ch {i+1}] ❌ narrate_chapter returned None! "
                        f"TTS synthesis failed for '{chapter.chapter_title}'"
                    )

            chapter.audio_narration = chapter_narration

            full_chapters.append(chapter)

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


gen_col1, gen_col2 = st.columns(2)
with gen_col1:
    generate_full_clicked = st.button("🚀 Generate Full Book")
with gen_col2:
    generate_audio_only_clicked = st.button("🎧 Generate Audiobook Only")

pending_mode = st.session_state.pending_generation_mode
pending_source = st.session_state.pending_generation_source

run_full_generation = generate_full_clicked or pending_mode == "full"
run_audio_only_generation = generate_audio_only_clicked or pending_mode == "audio_only"

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
        pages_per_chapter=pages_per_chapter
    )
    request = _request_from_chat_or_form(generation_source, form_request)

    parsed_chat_data = st.session_state.chat_book_data if generation_source == "chat" else None
    runtime = _resolve_runtime_options(
        parsed_chat_data,
        {
            "generate_images": generate_images,
            "use_ddg_images": use_ddg_images,
            "images_per_chapter": images_per_chapter,
            "use_qwen_models": use_qwen_models,
            "qwen_text_model": qwen_text_model,
            "enable_tts": enable_tts,
            "tts_voice": tts_voice,
            "tts_model": tts_model,
            "tts_audio_format": tts_audio_format,
            "tts_speech_rate": tts_speech_rate,
            "template_id": template_id,
        },
    )

    if not _validate_generation_prereqs(
        use_qwen_models=runtime["use_qwen_models"],
        enable_tts=runtime["enable_tts"],
        voice_clone_profile=active_clone_profile,
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
            
            # Save JSON
            json_path = json_dir / f"book_output.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"✅ JSON saved: {json_path}")

            # Resolve template_id — chat may override, "auto" triggers auto-pick
            effective_template_id = runtime.get("template_id", template_id)
            if effective_template_id == "auto":
                effective_template_id = auto_pick_template(request.topic)
                print(f"🤖 Auto-picked template: {effective_template_id} (topic: {request.topic})")

            # Generate HTML
            html_path = html_dir / f"libro_interactivo.html"
            generate_html_css_book_from_json(request, curriculum, full_chapters, str(html_path), template_id=effective_template_id)
            print(f"✅ HTML saved: {html_path} (template: {effective_template_id})")

            # Generate Markdown
            md_path = md_dir / f"libro_interactivo.md"
            book_output = BookOutput(
                book_request=request,
                curriculum=curriculum,
                chapters=full_chapters
            )
            save_markdown_book(book_output, str(md_path))
            print(f"✅ Markdown saved: {md_path}")

            # Generate PDF directly from structured data (fpdf2, no native deps)
            pdf_path = pdf_dir / f"libro_interactivo.pdf"
            try:
                pdf_success = generate_pdf_from_data(
                    request, curriculum, full_chapters,
                    str(pdf_path),
                    images_base=images_dir_path,
                )
                if pdf_success:
                    print(f"✅ PDF saved: {pdf_path}")
                    st.success(f"📄 PDF generated successfully!")
                else:
                    print(f"⚠️ PDF generation failed")
                    st.info(f"📱 PDF generation failed, but HTML is ready to open or print to PDF from browser")
            except Exception as e:
                print(f"⚠️  Error generating PDF: {e}")
                pdf_success = False

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
        voice_clone_profile=active_clone_profile,
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
                audio_dir=str(audio_dir_path),
                voice_clone_profile=active_clone_profile,
            )
        )

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

    # === Inline PDF preview ===
    if st.session_state.pdf_path and os.path.exists(st.session_state.pdf_path):
        st.subheader("📄 PDF Preview")
        import base64
        with open(st.session_state.pdf_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()
            b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
            pdf_display = (
                f'<iframe src="data:application/pdf;base64,{b64_pdf}" '
                f'width="100%" height="700" type="application/pdf"></iframe>'
            )
            st.markdown(pdf_display, unsafe_allow_html=True)

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
            st.markdown(ch.markdown_content)

            # Generated images
            if hasattr(ch, 'generated_images') and ch.generated_images:
                for j, img in enumerate(ch.generated_images, 1):
                    st.caption(img.description)
                    st.image(img.url, use_container_width=True)

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