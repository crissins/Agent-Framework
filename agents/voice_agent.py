# agents/voice_agent.py
"""
Text-to-Speech agent using DashScope Qwen3 TTS Voice Cloning (Singapore region).

Features:
- Text-to-speech via QwenTtsRealtime (Qwen3 TTS-VC) on Singapore endpoint
- Auto-enrollment: generates a reference voice using Edge TTS and enrolls it
- Multi-language support (Spanish, Portuguese, English, Chinese, etc.)
- Chapter-by-chapter audiobook narration
- WAV output (24kHz mono 16-bit PCM)

Models:
- qwen3-tts-vc-realtime-2025-11-27 : Realtime voice-cloning TTS (Singapore)

Note: CosyVoice v2 is NOT available on the Singapore region.
This agent uses QwenTtsRealtime with voice enrollment instead.

Workflow:
    1. Auto-enroll a voice from Edge TTS reference audio (once, cached)
    2. Synthesize via QwenTtsRealtime WebSocket API
    3. Output as WAV (PCM 24kHz mono 16-bit)

API docs: https://www.alibabacloud.com/help/en/model-studio/qwen-tts-vc
"""
import asyncio
import base64
import io
import json
import logging
import os
import struct
import threading
import time
import wave
from pathlib import Path
from typing import Optional, List

import dashscope
import requests

from dashscope.audio.qwen_tts_realtime import (
    QwenTtsRealtime,
    QwenTtsRealtimeCallback,
    AudioFormat as QwenAudioFormat,
)

from models.book_spec import AudioNarration
from utils.retry import sync_retry

logger = logging.getLogger(__name__)


# ── Qwen3 TTS-VC constants ───────────────────────────────────────────────
QWEN_TTS_VC_MODEL = "qwen3-tts-vc-realtime-2025-11-27"
ENROLLMENT_MODEL = "qwen-voice-enrollment"

# ── Paths for voice enrollment cache ─────────────────────────────────────
VOICE_REGISTRY_DIR = Path("books/voice_clones")
VOICE_SAMPLES_DIR = VOICE_REGISTRY_DIR / "samples"
VOICE_REGISTRY_FILE = VOICE_REGISTRY_DIR / "voice_registry.json"

# ── Singapore endpoint URLs ──────────────────────────────────────────────
SG_HTTP_URL = "https://dashscope-intl.aliyuncs.com/api/v1"
SG_WS_INFERENCE_URL = "wss://dashscope-intl.aliyuncs.com/api-ws/v1/inference"
SG_WS_REALTIME_URL = "wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime"
SG_ENROLLMENT_URL = f"{SG_HTTP_URL}/services/audio/tts/customization"

# PCM output from QwenTtsRealtime
PCM_SAMPLE_RATE = 24000
PCM_CHANNELS = 1
PCM_SAMPLE_WIDTH = 2  # 16-bit

# ── Language normalization ───────────────────────────────────────────────
_LANG_MAP = {
    "spanish": "es", "español": "es", "esp": "es",
    "portuguese": "pt", "português": "pt", "por": "pt", "brazilian": "pt",
    "english": "en", "eng": "en", "inglés": "en",
    "chinese": "zh", "mandarin": "zh", "中文": "zh",
}

def normalize_language(lang: str) -> str:
    """Convert language name/code to 2-letter code."""
    if not lang:
        return "es"
    lang_lower = lang.strip().lower()
    if len(lang_lower) <= 3 and lang_lower[:2].isalpha():
        return lang_lower[:2]
    return _LANG_MAP.get(lang_lower, lang_lower[:2])

# ── Pre-built voices (mapped to Edge TTS voices for auto-enrollment) ─────
# The original CosyVoice voice names are kept for UI compatibility.
# When a voice is selected, we auto-enroll an Edge TTS reference voice
# and cache the enrolled voice parameter for reuse.
COSYVOICE_VOICES = {
    # Female voices
    "longxiaochun": "Female · Warm · Narrator (Multilingual)",
    "longxiaoxia": "Female · Lively · Storyteller (Multilingual)",
    "longyue": "Female · Gentle · Soothing (Multilingual)",
    "longxiaofei": "Female · Clear · Professional (Multilingual)",
    # Male voices
    "longlaotie": "Male · Deep · Authoritative (Multilingual)",
    "longshuo": "Male · Energetic · Narrator (Multilingual)",
    "longjielidou": "Male · Humorous · Storyteller (Multilingual)",
    "longxiang": "Male · Calm · Educational (Multilingual)",
    # Neutral / Youth
    "longtong": "Child · Bright · Educational (Multilingual)",
    "longxiaobai": "Youth · Neutral · General (Multilingual)",
}

# ── Edge TTS voice mapping (for auto-enrollment reference audio) ────────
# Maps CosyVoice voice names → Edge TTS voices for reference generation
_EDGE_TTS_MAP = {
    # Female
    "longxiaochun": "es-MX-DaliaNeural",
    "longxiaoxia": "es-ES-ElviraNeural",
    "longyue": "es-AR-ElenaNeural",
    "longxiaofei": "es-CO-SalomeNeural",
    # Male
    "longlaotie": "es-MX-JorgeNeural",
    "longshuo": "es-ES-AlvaroNeural",
    "longjielidou": "es-AR-TomasNeural",
    "longxiang": "es-CO-GonzaloNeural",
    # Youth
    "longtong": "es-MX-DaliaNeural",
    "longxiaobai": "es-MX-JorgeNeural",
}

# Language → Edge TTS voice fallback (when voice name not in map)
_EDGE_TTS_LANG_MAP = {
    "es": "es-MX-DaliaNeural",
    "en": "en-US-JennyNeural",
    "pt": "pt-BR-FranciscaNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "it": "it-IT-ElsaNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
}

# ── Standard (non-VC) preset voices for cosyvoice-v2 fallback ──────────────────
STANDARD_FALLBACK_VOICE_MODEL = "cosyvoice-v2"
STANDARD_FALLBACK_VOICES: dict[str, str] = {
    "es": "longxiaochun",
    "en": "longxiaochun",
    "pt": "longxiaochun",
    "fr": "longxiaochun",
    "de": "longxiaochun",
    "it": "longxiaochun",
    "zh": "longxiaochun",
    "ja": "longxiaochun",
}


# ── Supported TTS models (updated for Singapore) ─────────────────────────
TTS_MODELS = {
    "qwen3-tts-vc-realtime": "Qwen3 TTS-VC Realtime – Voice cloning (Singapore)",
}

# ── Audio format presets (output = WAV 24kHz from QwenTtsRealtime) ───────
AUDIO_FORMATS = {
    "wav_24k": "WAV 24kHz mono 16-bit (native QwenTtsRealtime output)",
    "wav_16k": "WAV 16kHz mono 16-bit (downsampled)",
    "mp3_22k": "WAV 24kHz mono 16-bit (MP3 not available without ffmpeg)",
    "mp3_16k": "WAV 24kHz mono 16-bit (MP3 not available without ffmpeg)",
    "mp3_44k": "WAV 24kHz mono 16-bit (MP3 not available without ffmpeg)",
    "wav_22k": "WAV 24kHz mono 16-bit",
    "wav_44k": "WAV 24kHz mono 16-bit",
}


def _get_api_key() -> Optional[str]:
    """Get DashScope API key from environment."""
    key = os.getenv("DASHSCOPE_API_KEY")
    if not key:
        logger.warning("⚠️ DASHSCOPE_API_KEY not set — TTS functions unavailable")
    else:
        masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
        logger.debug(f"[TTS] DASHSCOPE_API_KEY found: {masked} (len={len(key)})")
    return key


def _configure_dashscope():
    """Set DashScope base URLs and API key for Singapore region."""
    dashscope.base_http_api_url = SG_HTTP_URL
    dashscope.base_websocket_api_url = SG_WS_INFERENCE_URL
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if api_key:
        dashscope.api_key = api_key
        logger.info(
            f"[TTS] DashScope configured (Singapore) — "
            f"http={dashscope.base_http_api_url}, "
            f"ws={dashscope.base_websocket_api_url}, "
            f"api_key={'set' if api_key else 'MISSING'}"
        )
    else:
        logger.error("[TTS] _configure_dashscope: DASHSCOPE_API_KEY is empty/None!")


# ═══════════════════════════════════════════════════════════════════════════
# VOICE ENROLLMENT (auto-enroll via Edge TTS reference)
# ═══════════════════════════════════════════════════════════════════════════

def _synthesize_with_standard_voice(text: str, language: str = "es") -> Optional[bytes]:
    """
    Fallback synthesis using DashScope cosyvoice-v2 preset voices.
    No enrollment required — uses built-in voice names directly.
    Returns WAV bytes, or None on failure.
    """
    try:
        from dashscope.audio.tts_v2 import SpeechSynthesizer, AudioFormat as TtsAudioFormat
    except ImportError:
        logger.warning("[TTS-Fallback] dashscope.audio.tts_v2 not available")
        return None

    api_key = _get_api_key()
    if not api_key:
        return None

    lang_key = normalize_language(language)
    preset_voice = STANDARD_FALLBACK_VOICES.get(lang_key, "longxiaochun")

    logger.warning(
        f"⚠️ [TTS-Fallback] Using standard preset voice '{preset_voice}' "
        f"(model={STANDARD_FALLBACK_VOICE_MODEL}) — enrollment unavailable"
    )

    try:
        synth = SpeechSynthesizer(
            model=STANDARD_FALLBACK_VOICE_MODEL,
            voice=preset_voice,
            api_key=api_key,
        )
        audio_bytes = synth.call(text)
        if audio_bytes:
            # tts_v2 returns MP3 by default — wrap in WAV-compatible bytes
            logger.info(
                f"✅ [TTS-Fallback] Standard voice OK: "
                f"{len(audio_bytes):,} bytes, voice={preset_voice}"
            )
            return audio_bytes
        else:
            logger.error("[TTS-Fallback] Standard voice returned empty audio")
            return None
    except Exception as e:
        logger.error(f"❌ [TTS-Fallback] Standard voice failed: {e}")
        return None


def _load_voice_registry() -> dict:
    """Load the voice registry from disk."""
    if VOICE_REGISTRY_FILE.exists():
        try:
            return json.loads(VOICE_REGISTRY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_voice_registry(registry: dict):
    """Save the voice registry to disk."""
    VOICE_REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    VOICE_REGISTRY_FILE.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _generate_reference_audio(
    voice_name: str,
    language: str = "es",
) -> Optional[Path]:
    """
    Generate a reference speech sample using Edge TTS (Microsoft free TTS).

    This creates a 15-20 second speech clip that serves as the enrollment
    reference for Qwen3 TTS-VC voice cloning. The Edge TTS voice determines
    the characteristics of the cloned voice.

    Args:
        voice_name: CosyVoice voice name (maps to an Edge TTS voice)
        language:   Language code for reference text

    Returns:
        Path to the generated audio file, or None on failure
    """
    try:
        import edge_tts
    except ImportError:
        logger.error(
            "❌ edge-tts package not installed. "
            "Run: pip install edge-tts"
        )
        return None

    # Pick Edge TTS voice
    edge_voice = _EDGE_TTS_MAP.get(voice_name)
    if not edge_voice:
        lang_key = language[:2].lower() if language else "es"
        edge_voice = _EDGE_TTS_LANG_MAP.get(lang_key, "es-MX-DaliaNeural")

    # Reference texts by language
    REF_TEXTS = {
        "es": (
            "Hola, mi nombre es una voz de ejemplo para el sistema de síntesis de voz. "
            "Este es un texto de referencia que se utilizará para crear un perfil de voz personalizado. "
            "La calidad del audio de referencia es muy importante para obtener buenos resultados. "
            "Estoy hablando de manera clara y a un ritmo natural para que el sistema pueda capturar "
            "las características de mi voz correctamente. "
            "Los libros educativos son una herramienta fundamental para el aprendizaje "
            "y la formación de niños y jóvenes en todo el mundo."
        ),
        "en": (
            "Hello, this is a reference voice sample for the text-to-speech system. "
            "This text will be used to create a custom voice profile for audiobook narration. "
            "I am speaking clearly and at a natural pace so the system can accurately capture "
            "the characteristics of my voice. Educational books are a fundamental tool "
            "for learning and development of children and young people around the world."
        ),
        "pt": (
            "Olá, este é um exemplo de voz para o sistema de síntese de fala. "
            "Este texto será utilizado para criar um perfil de voz personalizado. "
            "Estou falando de forma clara e em um ritmo natural para que o sistema "
            "possa capturar as características da minha voz corretamente. "
            "Os livros educativos são uma ferramenta fundamental para a aprendizagem."
        ),
    }
    lang_key = language[:2].lower() if language else "es"
    text = REF_TEXTS.get(lang_key, REF_TEXTS["es"])

    VOICE_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    output_path = VOICE_SAMPLES_DIR / f"ref_{voice_name}_{lang_key}.mp3"

    logger.info(
        f"[TTS] Generating Edge TTS reference: voice={edge_voice}, "
        f"lang={lang_key}, output={output_path}"
    )

    try:
        # edge_tts is async, run in event loop
        async def _gen():
            communicate = edge_tts.Communicate(text, edge_voice)
            await communicate.save(str(output_path))

        # Use existing event loop or create one
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, use a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(lambda: asyncio.run(_gen())).result(timeout=60)
        except RuntimeError:
            asyncio.run(_gen())

        if output_path.exists() and output_path.stat().st_size > 1000:
            logger.info(
                f"✅ [TTS] Reference audio generated: {output_path} "
                f"({output_path.stat().st_size} bytes)"
            )
            return output_path
        else:
            logger.error(f"❌ [TTS] Reference audio too small or missing: {output_path}")
            return None

    except Exception as e:
        logger.error(f"❌ [TTS] Edge TTS generation failed: {e}", exc_info=True)
        return None


def _enroll_voice(
    audio_path: Path,
    preferred_name: str,
    target_model: str = QWEN_TTS_VC_MODEL,
) -> Optional[str]:
    """
    Enroll a voice via DashScope REST API.

    Args:
        audio_path:     Path to reference audio (MP3/WAV)
        preferred_name: Name for the enrolled voice
        target_model:   TTS-VC model to enroll for

    Returns:
        The voice parameter string, or None on failure
    """
    api_key = _get_api_key()
    if not api_key:
        return None

    # Read audio and encode as data URI
    audio_bytes = audio_path.read_bytes()
    ext = audio_path.suffix.lower()
    mime = {"mp3": "audio/mpeg", ".mp3": "audio/mpeg", ".wav": "audio/wav"}.get(ext, "audio/mpeg")
    b64 = base64.b64encode(audio_bytes).decode()
    data_uri = f"data:{mime};base64,{b64}"

    payload = {
        "model": ENROLLMENT_MODEL,
        "input": {
            "action": "create",
            "target_model": target_model,
            "preferred_name": preferred_name,
            "audio": {"data": data_uri},
        },
    }

    logger.info(
        f"[TTS] Enrolling voice: name={preferred_name}, model={target_model}, "
        f"audio={audio_path} ({len(audio_bytes)} bytes)"
    )

    try:
        resp = requests.post(
            SG_ENROLLMENT_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120,
        )
    except Exception as e:
        logger.error(f"❌ [TTS] Enrollment request failed: {e}")
        return None

    if resp.status_code != 200:
        logger.error(
            f"❌ [TTS] Enrollment failed ({resp.status_code}): {resp.text[:300]}"
        )
        return None

    try:
        voice_param = resp.json()["output"]["voice"]
    except (KeyError, ValueError) as e:
        logger.error(f"❌ [TTS] Unexpected enrollment response: {resp.text[:300]}")
        return None

    logger.info(f"✅ [TTS] Voice enrolled: {voice_param}")
    return voice_param


def _ensure_enrolled_voice(
    voice_name: str = "longxiaochun",
    language: str = "es",
) -> Optional[str]:
    """
    Ensure an enrolled voice exists for the given voice name + language.

    If no enrolled voice is cached, auto-generates a reference audio
    using Edge TTS and enrolls it with DashScope.

    Args:
        voice_name: CosyVoice voice name (for mapping to Edge TTS voice)
        language:   Language code for reference text

    Returns:
        The voice parameter string, or None on failure
    """
    registry = _load_voice_registry()
    cache_key = f"{voice_name}_{language[:2].lower()}"

    # Check cache
    if cache_key in registry:
        voice_param = registry[cache_key].get("voice")
        if voice_param:
            logger.info(f"[TTS] Using cached enrolled voice: {cache_key} → {voice_param}")
            return voice_param

    logger.info(f"[TTS] No cached voice for '{cache_key}' — auto-enrolling...")

    lang_key = language[:2].lower() if language else "es"

    # Step 1: Use existing reference audio if already on disk (avoids regenerating)
    existing_ref = VOICE_SAMPLES_DIR / f"ref_{voice_name}_{lang_key}.mp3"
    if not existing_ref.exists():
        existing_ref = VOICE_SAMPLES_DIR / f"ref_{voice_name}_{lang_key}.wav"
    if existing_ref.exists() and existing_ref.stat().st_size > 1000:
        logger.info(f"[TTS] Reusing existing reference audio: {existing_ref}")
        ref_path = existing_ref
    else:
        # Step 1b: Generate reference audio with Edge TTS
        ref_path = _generate_reference_audio(voice_name, language)
        if not ref_path:
            # Try with default voice
            logger.warning("[TTS] Trying default Edge TTS voice for enrollment...")
            ref_path = _generate_reference_audio("longxiaochun", language)
            if not ref_path:
                logger.error("❌ [TTS] Cannot generate reference audio for enrollment")
                return None

    # Step 2: Enroll with DashScope
    # preferred_name: alphanumeric only, max 20 chars, no underscores
    clean_name = "".join(c for c in f"{voice_name}{language[:2]}" if c.isalnum())[:20]
    if not clean_name:
        clean_name = "autovoice"
    voice_param = _enroll_voice(ref_path, clean_name)
    if not voice_param:
        return None

    # Step 3: Cache the result
    registry[cache_key] = {
        "voice": voice_param,
        "voice_name": voice_name,
        "language": language,
        "ref_audio": str(ref_path),
        "model": QWEN_TTS_VC_MODEL,
        "enrolled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _save_voice_registry(registry)
    logger.info(f"✅ [TTS] Voice enrolled and cached: {cache_key} → {voice_param}")
    return voice_param


# ═══════════════════════════════════════════════════════════════════════════
# PCM → WAV CONVERSION
# ═══════════════════════════════════════════════════════════════════════════

def _pcm_to_wav(
    pcm_data: bytes,
    sample_rate: int = PCM_SAMPLE_RATE,
    channels: int = PCM_CHANNELS,
    sample_width: int = PCM_SAMPLE_WIDTH,
) -> bytes:
    """Convert raw PCM data to WAV format (adds WAV header)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════
# TEXT-TO-SPEECH (QwenTtsRealtime)
# ═══════════════════════════════════════════════════════════════════════════

@sync_retry(max_retries=2, base_delay=5.0, max_delay=45.0)
def synthesize_speech(
    text: str,
    voice: str = "longxiaochun",
    model: str = "qwen3-tts-vc-realtime",
    audio_format: str = "wav_24k",
    volume: int = 60,
    speech_rate: float = 1.0,
    pitch_rate: float = 1.0,
    language: str = "es",
) -> Optional[bytes]:
    """
    Synthesize speech from text using QwenTtsRealtime (Singapore).

    Auto-enrolls a voice via Edge TTS if needed, then synthesizes
    via WebSocket using the Qwen3 TTS-VC realtime model.

    Args:
        text: Text to synthesize (UTF-8, any language)
        voice: Voice name (maps to Edge TTS voice for enrollment)
        model: TTS model name (ignored, always uses Qwen3 TTS-VC)
        audio_format: Output format (always WAV 24kHz currently)
        volume: Volume 0-100 (not yet supported by QwenTtsRealtime)
        speech_rate: Speed (not yet supported by QwenTtsRealtime)
        pitch_rate: Pitch (not yet supported by QwenTtsRealtime)
        language: Language code for auto-enrollment reference text

    Returns:
        Audio bytes (WAV format) or None on failure
    """
    language = normalize_language(language)
    logger.info(
        f"🔊 [TTS] synthesize_speech called — "
        f"voice={voice}, model=qwen3-tts-vc-realtime, "
        f"text_len={len(text)} chars, language={language}"
    )
    logger.debug(f"[TTS] Text preview: {text[:120]}..." if len(text) > 120 else f"[TTS] Text: {text}")

    api_key = _get_api_key()
    if not api_key:
        logger.error("❌ [TTS] No DASHSCOPE_API_KEY — aborting synthesis")
        return None

    _configure_dashscope()

    # Ensure we have an enrolled voice
    voice_param = _ensure_enrolled_voice(voice, language)
    if not voice_param:
        logger.warning(
            f"⚠️ [TTS] Enrollment failed for '{voice}' ({language}) — "
            f"falling back to standard preset voice."
        )
        return _synthesize_with_standard_voice(text, language)

    _t0 = time.perf_counter()

    # Synthesize via QwenTtsRealtime callback
    audio_chunks: list[bytes] = []
    complete_event = threading.Event()
    session_ready = threading.Event()
    errors: list[str] = []

    class _SynthCallback(QwenTtsRealtimeCallback):
        def on_open(self):
            logger.debug("[TTS] WebSocket opened")

        def on_close(self, code, msg):
            logger.debug(f"[TTS] WebSocket closed: code={code}")
            complete_event.set()

        def on_event(self, response: dict):
            t = response.get("type", "")
            if t == "session.created":
                logger.debug("[TTS] Session created")
                session_ready.set()
            elif t == "response.audio.delta":
                chunk = base64.b64decode(response["delta"])
                audio_chunks.append(chunk)
            elif t == "response.done":
                logger.debug("[TTS] Response done")
            elif t == "session.finished":
                complete_event.set()
            elif t == "error":
                msg = response.get("error", {}).get("message", str(response))
                errors.append(msg)
                logger.error(f"❌ [TTS] Server error: {msg}")
                complete_event.set()
            else:
                logger.debug(f"[TTS] Event: {t}")

    logger.info(
        f"[TTS] Starting QwenTtsRealtime — model={QWEN_TTS_VC_MODEL}, "
        f"voice_param={voice_param[:30]}..."
    )

    try:
        cb = _SynthCallback()
        tts = QwenTtsRealtime(
            model=QWEN_TTS_VC_MODEL,
            callback=cb,
            url=SG_WS_REALTIME_URL,
        )
        tts.connect()
        tts.update_session(
            voice=voice_param,
            response_format=QwenAudioFormat.PCM_24000HZ_MONO_16BIT,
            mode="server_commit",
        )

        # Wait for session.created before sending text — critical for gRPC init
        if not session_ready.wait(timeout=8.0):
            if errors:
                raise RuntimeError(f"TTS session setup error: {'; '.join(errors)}")
            logger.warning("⚠️ [TTS] session.created not received in 8s, proceeding anyway")

        # Extra stabilization delay for the gRPC backend
        time.sleep(1.0)

        if errors:
            # Server already reported an error during session setup
            raise RuntimeError(f"TTS session setup error: {'; '.join(errors)}")
        tts.append_text(text)
        time.sleep(0.2)
        tts.finish()

        # Wait for completion (timeout based on text length: ~2.5s per 100 chars, min 20s)
        timeout = max(20, len(text) * 0.025 + 15)
        if not complete_event.wait(timeout=timeout):
            logger.warning(f"⚠️ [TTS] Timeout after {timeout:.0f}s waiting for synthesis")

    except Exception as e:
        _elapsed = time.perf_counter() - _t0
        logger.error(
            f"❌ [TTS] QwenTtsRealtime EXCEPTION after {_elapsed:.1f}s: "
            f"{type(e).__name__}: {e}",
            exc_info=True,
        )
        # Raise so @sync_retry can retry transient errors
        raise

    _elapsed = time.perf_counter() - _t0

    if errors:
        error_msg = '; '.join(errors)
        logger.error(
            f"❌ [TTS] Synthesis errors after {_elapsed:.1f}s: {error_msg}"
        )
        # Raise so @sync_retry can retry transient server errors
        raise RuntimeError(f"TTS server error: {error_msg}")

    if audio_chunks:
        pcm_data = b"".join(audio_chunks)
        wav_data = _pcm_to_wav(pcm_data)
        duration = len(pcm_data) / (PCM_SAMPLE_RATE * PCM_SAMPLE_WIDTH * PCM_CHANNELS)
        logger.info(
            f"✅ [TTS] Synthesized {len(wav_data):,} bytes WAV "
            f"({duration:.1f}s audio) in {_elapsed:.1f}s "
            f"({len(text)} chars → {len(wav_data)/1024:.0f} KB)"
        )
        return wav_data
    else:
        logger.error(
            f"❌ [TTS] Empty audio after {_elapsed:.1f}s — "
            f"voice_param={voice_param[:30]}, text_len={len(text)}"
        )
        raise RuntimeError("TTS returned empty audio data")


async def synthesize_speech_async(
    text: str,
    voice: str = "longxiaochun",
    model: str = "qwen3-tts-vc-realtime",
    audio_format: str = "wav_24k",
    volume: int = 60,
    speech_rate: float = 1.0,
    pitch_rate: float = 1.0,
    language: str = "es",
) -> Optional[bytes]:
    """Async wrapper for synthesize_speech."""
    return await asyncio.to_thread(
        synthesize_speech,
        text=text,
        voice=voice,
        model=model,
        audio_format=audio_format,
        volume=volume,
        speech_rate=speech_rate,
        pitch_rate=pitch_rate,
        language=language,
    )


def synthesize_to_file(
    text: str,
    output_path: str,
    voice: str = "longxiaochun",
    model: str = "qwen3-tts-vc-realtime",
    audio_format: str = "wav_24k",
    volume: int = 60,
    speech_rate: float = 1.0,
    pitch_rate: float = 1.0,
    language: str = "es",
) -> Optional[str]:
    """
    Synthesize speech and save to a file.

    Args:
        text: Text to synthesize
        output_path: Path to save audio file (.wav)
        voice: Voice name
        model: TTS model (always Qwen3 TTS-VC)
        audio_format: Audio format
        volume: Volume 0-100
        speech_rate: Speed 0.5-2.0
        pitch_rate: Pitch 0.5-2.0
        language: Language code for auto-enrollment

    Returns:
        Output file path on success, None on failure
    """
    try:
        audio_data = synthesize_speech(
            text=text,
            voice=voice,
            model=model,
            audio_format=audio_format,
            volume=volume,
            speech_rate=speech_rate,
            pitch_rate=pitch_rate,
            language=language,
        )
    except Exception as e:
        logger.error(f"❌ synthesize_speech failed after retries: {e}")
        return None

    if not audio_data:
        return None

    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_data)
        logger.info(f"💾 Audio saved: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"❌ Failed to save audio: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# VOICE CLONING (enrollment-based, same as voice_clone_agent)
# ═══════════════════════════════════════════════════════════════════════════

def clone_voice(
    audio_url: str,
    prefix: str = "custom",
    target_model: str = QWEN_TTS_VC_MODEL,
    language_hints: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Clone a voice from an audio file path or URL.

    Uses QwenTtsRealtime voice enrollment on Singapore.
    The audio should be a clear recording of 10-60 seconds.

    Args:
        audio_url: Path to the reference audio file
        prefix: Custom prefix for the voice name
        target_model: Target TTS model
        language_hints: Language codes (unused, kept for API compat)

    Returns:
        voice parameter string on success, None on failure
    """
    audio_path = Path(audio_url)
    if not audio_path.exists():
        logger.error(f"Audio file not found: {audio_url}")
        return None

    preferred_name = f"{prefix}_clone"[:20]
    return _enroll_voice(audio_path, preferred_name, target_model)


def clone_voice_from_file(
    audio_path: str,
    prefix: str = "custom",
    target_model: str = QWEN_TTS_VC_MODEL,
    language_hints: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Clone a voice from a local audio file.

    Args:
        audio_path: Local path to audio file (WAV/MP3)
        prefix: Custom prefix for voice name
        target_model: Target TTS model
        language_hints: Language codes (unused)

    Returns:
        voice parameter string on success, None on failure
    """
    return clone_voice(audio_path, prefix, target_model, language_hints)


def list_cloned_voices(
    prefix: Optional[str] = None,
    page_size: int = 20,
) -> List[dict]:
    """
    List all enrolled (cloned) voices on Singapore.

    Returns:
        List of voice info dicts
    """
    api_key = _get_api_key()
    if not api_key:
        return []

    payload = {
        "model": ENROLLMENT_MODEL,
        "input": {
            "action": "list",
            "target_model": QWEN_TTS_VC_MODEL,
            "page_index": 0,
            "page_size": page_size,
        },
    }

    try:
        resp = requests.post(
            SG_ENROLLMENT_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )
        if resp.status_code == 200:
            return resp.json().get("output", {}).get("voices", [])
        logger.error(f"list_cloned_voices failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        logger.error(f"❌ Failed to list voices: {e}")
    return []


def delete_cloned_voice(voice_id: str) -> bool:
    """
    Delete an enrolled voice.

    Args:
        voice_id: The voice parameter string to delete

    Returns:
        True on success, False on failure
    """
    api_key = _get_api_key()
    if not api_key:
        return False

    payload = {
        "model": ENROLLMENT_MODEL,
        "input": {
            "action": "delete",
            "voice": voice_id,
        },
    }

    try:
        resp = requests.post(
            SG_ENROLLMENT_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )
        if resp.status_code == 200:
            logger.info(f"✅ Voice deleted: {voice_id}")
            return True
        logger.error(f"delete_cloned_voice failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        logger.error(f"❌ Failed to delete voice: {e}")
    return False


# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER / BOOK NARRATION
# ═══════════════════════════════════════════════════════════════════════════

def _strip_markdown(text: str) -> str:
    """Strip markdown formatting for cleaner TTS input."""
    import re
    # Remove headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    # Remove images BEFORE links (otherwise ![alt](url) becomes !alt)
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', text)
    # Remove links but keep text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove inline code
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Remove blockquotes
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
    # Remove [IMAGE: ...] and [VIDEO: ...] placeholders
    text = re.sub(r'\[(IMAGE|VIDEO):\s*[^\]]+\]', '', text)
    # Remove QR code references and video recommendation blocks
    text = re.sub(r'🎬\s*\*?\*?Video recomendado:\*?\*?.*', '', text)
    text = re.sub(r'!\[QR Code\]\([^\)]+\)', '', text)
    # Collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def narrate_chapter(
    chapter_title: str,
    markdown_content: str,
    output_dir: str,
    voice: str = "longxiaochun",
    model: str = "qwen3-tts-vc-realtime",
    audio_format: str = "wav_24k",
    volume: int = 60,
    speech_rate: float = 0.95,
    pitch_rate: float = 1.0,
    language: str = "es",
) -> Optional[AudioNarration]:
    """
    Generate audio narration for a single chapter.

    Args:
        chapter_title: Chapter title
        markdown_content: Chapter markdown content
        output_dir: Directory to save audio files
        voice: Voice name (maps to Edge TTS for enrollment)
        model: TTS model (always Qwen3 TTS-VC)
        audio_format: Audio format
        volume: Volume 0-100
        speech_rate: Speech rate (not yet supported by QwenTtsRealtime)
        pitch_rate: Pitch rate (not yet supported by QwenTtsRealtime)
        language: Language code for auto-enrollment

    Returns:
        AudioNarration object with file path and metadata, or None
    """
    _t0 = time.perf_counter()
    logger.info(
        f"🎙️ [Narrate] Starting chapter: '{chapter_title}' "
        f"(md_len={len(markdown_content)}, voice={voice}, "
        f"model={model}, format={audio_format}, rate={speech_rate})"
    )

    # Clean markdown for TTS
    clean_text = _strip_markdown(markdown_content)
    logger.debug(
        f"[Narrate] Markdown stripped: {len(markdown_content)} → {len(clean_text)} chars "
        f"(removed {len(markdown_content) - len(clean_text)} formatting chars)"
    )

    if not clean_text or len(clean_text) < 10:
        logger.warning(
            f"⚠️ [Narrate] Chapter '{chapter_title}' has no narrable content "
            f"(clean_text_len={len(clean_text) if clean_text else 0})"
        )
        return None

    # Add a natural intro
    narration_text = f"{chapter_title}.\n\n{clean_text}"

    # QwenTtsRealtime handles longer text, but use smaller chunks for reliability
    MAX_CHARS = 2000
    if len(narration_text) > MAX_CHARS:
        chunks = _split_text(narration_text, MAX_CHARS)
        logger.info(
            f"📝 [Narrate] Text chunked: {len(narration_text)} chars → "
            f"{len(chunks)} chunks (max {MAX_CHARS}/chunk)"
        )
    else:
        chunks = [narration_text]
        logger.info(f"📝 [Narrate] Single chunk: {len(narration_text)} chars")
    logger.info(
        f"📝 [Narrate] First 200 chars of narration text: "
        f"{narration_text[:200]}..."
    )

    # Synthesize each chunk
    all_audio: List[bytes] = []
    for i, chunk in enumerate(chunks):
        logger.info(
            f"🔊 [Narrate] Synthesizing chunk {i+1}/{len(chunks)} "
            f"({len(chunk)} chars)..."
        )
        try:
            audio = synthesize_speech(
                text=chunk,
                voice=voice,
                model=model,
                audio_format=audio_format,
                volume=volume,
                speech_rate=speech_rate,
                pitch_rate=pitch_rate,
                language=language,
            )
        except Exception as e:
            logger.error(
                f"❌ [Narrate] TTS exception in chunk {i+1}/{len(chunks)}: "
                f"{type(e).__name__}: {e}"
            )
            audio = None
        if audio:
            all_audio.append(audio)
            logger.debug(f"[Narrate] Chunk {i+1} OK: {len(audio):,} bytes")
        else:
            logger.warning(f"⚠️ [Narrate] Chunk {i+1}/{len(chunks)} returned no audio")
        # Small delay between chunks to avoid overwhelming the server
        if i < len(chunks) - 1:
            time.sleep(1.5)

    if not all_audio:
        _elapsed = time.perf_counter() - _t0
        logger.error(
            f"\u274c [Narrate] ALL chunks failed for '{chapter_title}' "
            f"after {_elapsed:.1f}s \u2014 0/{len(chunks)} synthesized. "
            f"Check DASHSCOPE_API_KEY, network connectivity, and DashScope quota. "
            f"voice={voice}, model=qwen3-tts-vc-realtime"
        )
        return None

    logger.info(
        f"\ud83d\udcc0 [Narrate] Concatenating {len(all_audio)} audio chunks"
    )

    # For WAV, we need to combine the PCM data (strip WAV headers, concat, re-wrap)
    if len(all_audio) == 1:
        combined_audio = all_audio[0]
    else:
        # Extract raw PCM from each WAV chunk and concatenate
        pcm_parts = []
        for wav_bytes in all_audio:
            try:
                with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                    pcm_parts.append(wf.readframes(wf.getnframes()))
            except Exception:
                # If not valid WAV, treat as raw PCM
                pcm_parts.append(wav_bytes)
        combined_pcm = b"".join(pcm_parts)
        combined_audio = _pcm_to_wav(combined_pcm)

    total_size = len(combined_audio)

    # Save to file (always WAV)
    safe_title = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in chapter_title)
    safe_title = safe_title.replace(' ', '_')[:50]
    filename = f"{safe_title}.wav"
    filepath = Path(output_dir) / filename

    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(combined_audio)

        _elapsed = time.perf_counter() - _t0
        est_dur = _estimate_duration(combined_audio, "wav_24k")
        logger.info(
            f"💾 [Narrate] Saved: {filepath} — "
            f"{total_size:,} bytes ({total_size/1024:.0f} KB), "
            f"~{est_dur:.0f}s audio, "
            f"{len(chunks)} chunks, took {_elapsed:.1f}s wall-time"
        )

        return AudioNarration(
            chapter_title=chapter_title,
            file_path=str(filepath),
            duration_seconds=est_dur,
            voice_id=voice,
            model=QWEN_TTS_VC_MODEL,
            format="wav",
            size_bytes=total_size,
        )

    except Exception as e:
        logger.error(f"❌ Failed to save narration: {e}")
        return None


async def narrate_chapter_async(
    chapter_title: str,
    markdown_content: str,
    output_dir: str,
    voice: str = "longxiaochun",
    model: str = "qwen3-tts-vc-realtime",
    audio_format: str = "wav_24k",
    **kwargs,
) -> Optional[AudioNarration]:
    """Async wrapper for narrate_chapter."""
    return await asyncio.to_thread(
        narrate_chapter,
        chapter_title=chapter_title,
        markdown_content=markdown_content,
        output_dir=output_dir,
        voice=voice,
        model=model,
        audio_format=audio_format,
        **kwargs,
    )


async def narrate_book(
    chapters: list,
    output_dir: str,
    voice: str = "longxiaochun",
    model: str = "qwen3-tts-vc-realtime",
    audio_format: str = "wav_24k",
    volume: int = 60,
    speech_rate: float = 0.95,
    pitch_rate: float = 1.0,
    progress_callback=None,
) -> List[AudioNarration]:
    """
    Generate audio narration for all chapters in a book.

    Args:
        chapters: List of ChapterContent objects
        output_dir: Base directory for audio files
        voice: Voice name
        model: TTS model (always Qwen3 TTS-VC)
        audio_format: Audio format
        volume: Volume
        speech_rate: Speech rate
        pitch_rate: Pitch rate
        progress_callback: Optional callback(chapter_idx, total, status_msg)

    Returns:
        List of AudioNarration objects
    """
    _book_t0 = time.perf_counter()
    logger.info(
        f"📚 [NarrateBook] Starting full book narration — "
        f"{len(chapters)} chapters, voice={voice}, model=qwen3-tts-vc-realtime, "
        f"format={audio_format}, rate={speech_rate}"
    )

    narrations: List[AudioNarration] = []

    for i, chapter in enumerate(chapters):
        if progress_callback:
            progress_callback(i, len(chapters), f"🔊 Narrating chapter {i+1}: {chapter.chapter_title}")

        logger.info(
            f"📖 [NarrateBook] Chapter {i+1}/{len(chapters)}: "
            f"'{chapter.chapter_title}' ({len(chapter.markdown_content)} chars md)"
        )

        narration = await narrate_chapter_async(
            chapter_title=chapter.chapter_title,
            markdown_content=chapter.markdown_content,
            output_dir=output_dir,
            voice=voice,
            model=model,
            audio_format=audio_format,
            volume=volume,
            speech_rate=speech_rate,
            pitch_rate=pitch_rate,
        )

        if narration:
            narrations.append(narration)
            logger.info(
                f"✅ [NarrateBook] Chapter {i+1} done: "
                f"{narration.file_path} — {narration.size_bytes:,} bytes, "
                f"~{narration.duration_seconds:.0f}s"
            )
        else:
            logger.warning(
                f"⚠️ [NarrateBook] Chapter {i+1} FAILED: '{chapter.chapter_title}'"
            )

    _book_elapsed = time.perf_counter() - _book_t0
    total_bytes = sum(n.size_bytes for n in narrations)
    total_dur = sum(n.duration_seconds for n in narrations)
    logger.info(
        f"📚 [NarrateBook] Complete! {len(narrations)}/{len(chapters)} chapters, "
        f"{total_bytes:,} bytes ({total_bytes/1024:.0f} KB), "
        f"~{total_dur:.0f}s audio, took {_book_elapsed:.1f}s wall-time"
    )

    if progress_callback:
        progress_callback(len(chapters), len(chapters), "✅ Narration complete!")

    return narrations


def _split_text(text: str, max_chars: int) -> List[str]:
    """
    Split text into chunks at sentence boundaries.

    Tries to split at paragraph breaks first, then sentences,
    ensuring each chunk is under max_chars.
    """
    paragraphs = text.split('\n\n')
    chunks: List[str] = []
    current = ""
    logger.debug(
        f"[Split] Splitting {len(text)} chars into chunks of max {max_chars}: "
        f"{len(paragraphs)} paragraphs"
    )

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current.strip())
            # If a single paragraph is too long, split by sentences
            if len(para) > max_chars:
                sentences = para.replace('. ', '.\n').split('\n')
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= max_chars:
                        current = f"{current} {sent}" if current else sent
                    else:
                        if current:
                            chunks.append(current.strip())
                        current = sent
            else:
                current = para

    if current:
        chunks.append(current.strip())

    return chunks


def _estimate_duration(audio_bytes: bytes, audio_format: str) -> float:
    """Estimate audio duration in seconds based on byte size and format."""
    size = len(audio_bytes)
    if "wav" in audio_format:
        # WAV 24kHz 16-bit mono: try reading header first
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return frames / rate
        except Exception:
            pass
        # Fallback: 24kHz 16-bit mono
        sample_rate = PCM_SAMPLE_RATE
        bytes_per_sample = PCM_SAMPLE_WIDTH
        # Subtract WAV header (~44 bytes)
        pcm_size = max(0, size - 44)
        return pcm_size / (sample_rate * bytes_per_sample)
    elif "mp3" in audio_format:
        # ~128-256 kbps MP3
        bitrate = 192_000 / 8  # bytes per second (avg)
        return size / bitrate
    return 0.0