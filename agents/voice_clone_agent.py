# agents/voice_clone_agent.py
"""
Voice Cloning Agent using Qwen3 TTS Voice Conversion (VC).

Enrolls a custom voice from a reference audio file and synthesizes speech
using the cloned voice through DashScope's Qwen3 TTS VC models.

Key differences from voice_agent.py (CosyVoice):
    - Uses Qwen3-TTS-VC models (higher-fidelity cloning)
    - Enrolls voices via REST API → qwen-voice-enrollment
    - Synthesizes via dashscope.MultiModalConversation.call()
    - Supports both batch and realtime VC models

Models:
    qwen3-tts-vc-2026-01-22          : Batch voice cloning + synthesis
    qwen3-tts-vc-realtime-2026-01-15 : Realtime voice cloning + synthesis

Workflow:
    1.  create_voice(audio_path)  →  voice parameter string
    2.  synthesize(text, voice)   →  audio bytes / saved file
    3.  (Optional) list / delete enrolled voices

API docs: https://www.alibabacloud.com/help/en/model-studio/qwen-tts-vc
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import threading
import time as _time
import wave
from pathlib import Path
from typing import List, Optional

import dashscope
import requests
from dashscope.audio.qwen_tts_realtime import (
    QwenTtsRealtime,
    QwenTtsRealtimeCallback,
    AudioFormat as QwenAudioFormat,
)

from utils.retry import sync_retry

logger = logging.getLogger(__name__)


# ── Model constants ───────────────────────────────────────────────────────
VC_MODEL_BATCH = "qwen3-tts-vc-2026-01-22"
VC_MODEL_REALTIME = "qwen3-tts-vc-realtime-2025-11-27"  # Confirmed working on Singapore
ENROLLMENT_MODEL = "qwen-voice-enrollment"  # Fixed – do NOT change

# PCM output constants
PCM_SAMPLE_RATE = 24000
PCM_CHANNELS = 1
PCM_SAMPLE_WIDTH = 2  # 16-bit

# ── Audio format presets (output is always WAV from QwenTtsRealtime) ─────
VC_AUDIO_FORMATS = {
    "wav_24k": "WAV 24kHz mono 16-bit (native QwenTtsRealtime)",
    "mp3_16k": "WAV 24kHz (MP3 not available without ffmpeg)",
    "mp3_22k": "WAV 24kHz (MP3 not available without ffmpeg)",
    "mp3_44k": "WAV 24kHz (MP3 not available without ffmpeg)",
    "wav_16k": "WAV 24kHz mono 16-bit",
    "wav_22k": "WAV 24kHz mono 16-bit",
    "wav_44k": "WAV 24kHz mono 16-bit",
}

# ── Region endpoints ──────────────────────────────────────────────────────
REGION_ENDPOINTS = {
    "singapore": {
        "customization": "https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization",
        "base_api": "https://dashscope-intl.aliyuncs.com/api/v1",
        "base_ws": "wss://dashscope-intl.aliyuncs.com/api-ws/v1/inference",
        "base_ws_realtime": "wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime",
    },
    "beijing": {
        "customization": "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization",
        "base_api": "https://dashscope.aliyuncs.com/api/v1",
        "base_ws": "wss://dashscope.aliyuncs.com/api-ws/v1/inference",
        "base_ws_realtime": "wss://dashscope.aliyuncs.com/api-ws/v1/realtime",
    },
}

# ── MIME types by extension ───────────────────────────────────────────────
_MIME_MAP = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".opus": "audio/opus",
}

DEFAULT_REGION = "singapore"
DEFAULT_VC_MODEL = VC_MODEL_BATCH
DEFAULT_PREFERRED_NAME = "custom_voice"


# ═══════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _get_api_key() -> str:
    """Return DASHSCOPE_API_KEY or raise."""
    key = os.getenv("DASHSCOPE_API_KEY")
    if not key:
        raise EnvironmentError(
            "DASHSCOPE_API_KEY is not set. "
            "Get one at https://www.alibabacloud.com/help/en/model-studio/get-api-key"
        )
    return key


def _audio_to_data_uri(file_path: str | Path) -> str:
    """Read a local audio file and return a base64 data URI."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    mime = _MIME_MAP.get(path.suffix.lower(), "audio/mpeg")
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def _region_urls(region: str = DEFAULT_REGION) -> dict:
    """Return endpoint URLs for the given region."""
    return REGION_ENDPOINTS.get(region, REGION_ENDPOINTS["singapore"])


# ═══════════════════════════════════════════════════════════════════════════
#  VOICE ENROLLMENT  (create / list / query / update / delete)
# ═══════════════════════════════════════════════════════════════════════════

@sync_retry(max_retries=2, base_delay=3.0, max_delay=30.0)
def create_voice(
    audio_path: str | Path,
    *,
    target_model: str = DEFAULT_VC_MODEL,
    preferred_name: str = DEFAULT_PREFERRED_NAME,
    region: str = DEFAULT_REGION,
) -> str:
    """
    Enroll a custom voice from a local audio file.

    The reference audio should be a clear recording of **10 – 60 seconds**
    with minimal background noise.

    Args:
        audio_path:      Path to MP3 / WAV / FLAC / OGG / M4A file.
        target_model:    VC model for synthesis (batch or realtime).
        preferred_name:  Human-readable name (lowercase alphanumeric).
        region:          'singapore' or 'beijing'.

    Returns:
        The ``voice`` parameter string to pass to synthesis calls.
    """
    api_key = _get_api_key()
    data_uri = _audio_to_data_uri(audio_path)
    url = _region_urls(region)["customization"]

    payload = {
        "model": ENROLLMENT_MODEL,
        "input": {
            "action": "create",
            "target_model": target_model,
            "preferred_name": preferred_name,
            "audio": {"data": data_uri},
        },
    }

    resp = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=120,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Voice enrollment failed ({resp.status_code}): {resp.text}"
        )

    try:
        voice = resp.json()["output"]["voice"]
    except (KeyError, ValueError) as exc:
        raise RuntimeError(f"Unexpected enrollment response: {resp.text}") from exc

    logger.info(f"✅ Voice enrolled: {voice}  (model={target_model}, name={preferred_name})")
    return voice


def list_voices(
    *,
    target_model: str = DEFAULT_VC_MODEL,
    preferred_name: str | None = None,
    page_index: int = 0,
    page_size: int = 20,
    region: str = DEFAULT_REGION,
) -> list[dict]:
    """
    List enrolled voices.

    Returns:
        List of voice info dicts  [{"voice": "...", ...}, ...]
    """
    api_key = _get_api_key()
    url = _region_urls(region)["customization"]

    payload: dict = {
        "model": ENROLLMENT_MODEL,
        "input": {
            "action": "list",
            "target_model": target_model,
            "page_index": page_index,
            "page_size": page_size,
        },
    }
    if preferred_name:
        payload["input"]["preferred_name"] = preferred_name

    resp = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )

    if resp.status_code != 200:
        logger.error(f"list_voices failed ({resp.status_code}): {resp.text}")
        return []

    try:
        return resp.json().get("output", {}).get("voices", [])
    except (ValueError, KeyError):
        return []


def query_voice(
    voice: str,
    *,
    region: str = DEFAULT_REGION,
) -> dict | None:
    """
    Query details of a single enrolled voice.

    Args:
        voice: The voice parameter string returned by create_voice().

    Returns:
        Voice details dict or None.
    """
    api_key = _get_api_key()
    url = _region_urls(region)["customization"]

    payload = {
        "model": ENROLLMENT_MODEL,
        "input": {
            "action": "query",
            "voice": voice,
        },
    }

    resp = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )

    if resp.status_code != 200:
        logger.error(f"query_voice failed ({resp.status_code}): {resp.text}")
        return None

    try:
        return resp.json().get("output", {})
    except (ValueError, KeyError):
        return None


def update_voice(
    voice: str,
    audio_path: str | Path,
    *,
    target_model: str = DEFAULT_VC_MODEL,
    region: str = DEFAULT_REGION,
) -> str:
    """
    Update an enrolled voice with a new audio sample.

    Returns:
        Updated voice parameter string.
    """
    api_key = _get_api_key()
    data_uri = _audio_to_data_uri(audio_path)
    url = _region_urls(region)["customization"]

    payload = {
        "model": ENROLLMENT_MODEL,
        "input": {
            "action": "update",
            "voice": voice,
            "target_model": target_model,
            "audio": {"data": data_uri},
        },
    }

    resp = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=120,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"update_voice failed ({resp.status_code}): {resp.text}")

    try:
        return resp.json()["output"]["voice"]
    except (KeyError, ValueError) as exc:
        raise RuntimeError(f"Unexpected update response: {resp.text}") from exc


def delete_voice(
    voice: str,
    *,
    region: str = DEFAULT_REGION,
) -> bool:
    """
    Delete an enrolled voice.

    Returns:
        True on success.
    """
    api_key = _get_api_key()
    url = _region_urls(region)["customization"]

    payload = {
        "model": ENROLLMENT_MODEL,
        "input": {
            "action": "delete",
            "voice": voice,
        },
    }

    resp = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=60,
    )

    if resp.status_code == 200:
        logger.info(f"🗑️ Voice deleted: {voice}")
        return True

    logger.error(f"delete_voice failed ({resp.status_code}): {resp.text}")
    return False


# ═══════════════════════════════════════════════════════════════════════════
#  PCM → WAV CONVERSION
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
#  SYNTHESIS  (text → audio using a cloned voice via QwenTtsRealtime)
# ═══════════════════════════════════════════════════════════════════════════

@sync_retry(max_retries=2, base_delay=5.0, max_delay=45.0)
def synthesize(
    text: str,
    voice: str,
    *,
    model: str = DEFAULT_VC_MODEL,
    region: str = DEFAULT_REGION,
    audio_format: str = "wav_24k",
) -> bytes | None:
    """
    Synthesize speech with a cloned voice via QwenTtsRealtime.

    Args:
        text:         Text to synthesize (any language supported by the model).
        voice:        Voice parameter from create_voice().
        model:        VC model to use (realtime model will be used).
        region:       'singapore' or 'beijing'.
        audio_format: Audio format key (output is always WAV 24kHz).

    Returns:
        WAV audio bytes on success, None on failure.
    """
    api_key = _get_api_key()

    # Configure DashScope for the target region
    urls = _region_urls(region)
    dashscope.base_http_api_url = urls["base_api"]
    dashscope.base_websocket_api_url = urls["base_ws"]
    dashscope.api_key = api_key

    # Use confirmed working realtime model
    rt_model = VC_MODEL_REALTIME

    logger.info(
        f"🔊 [VC] Synthesizing via QwenTtsRealtime — voice={voice[:30]}..., "
        f"model={rt_model}, region={region}, text_len={len(text)} chars"
    )

    _t0 = _time.perf_counter()

    audio_chunks: list[bytes] = []
    complete_event = threading.Event()
    session_ready = threading.Event()
    errors: list[str] = []

    class _CB(QwenTtsRealtimeCallback):
        def on_open(self):
            logger.debug("[VC] WebSocket opened")

        def on_close(self, code, msg):
            logger.debug(f"[VC] WebSocket closed: code={code}")
            complete_event.set()

        def on_event(self, response: dict):
            t = response.get("type", "")
            if t == "session.created":
                logger.debug("[VC] Session created")
                session_ready.set()
            elif t == "response.audio.delta":
                audio_chunks.append(base64.b64decode(response["delta"]))
            elif t == "response.done":
                logger.debug("[VC] Response done")
            elif t == "session.finished":
                complete_event.set()
            elif t == "error":
                msg = response.get("error", {}).get("message", str(response))
                errors.append(msg)
                logger.error(f"❌ [VC] Server error: {msg}")
                complete_event.set()

    try:
        ws_url = urls.get("base_ws_realtime", urls["base_ws"].replace("/inference", "/realtime"))
        cb = _CB()
        tts = QwenTtsRealtime(
            model=rt_model,
            callback=cb,
            url=ws_url,
        )
        tts.connect()
        tts.update_session(
            voice=voice,
            response_format=QwenAudioFormat.PCM_24000HZ_MONO_16BIT,
            mode="server_commit",
        )

        # Wait for session.created before sending text — critical for gRPC init
        if not session_ready.wait(timeout=8.0):
            if errors:
                raise RuntimeError(f"VC session setup error: {'; '.join(errors)}")
            logger.warning("⚠️ [VC] session.created not received in 8s, proceeding anyway")

        # Extra stabilization delay for the gRPC backend
        _time.sleep(1.0)

        if errors:
            raise RuntimeError(f"VC session setup error: {'; '.join(errors)}")

        tts.append_text(text)
        _time.sleep(0.2)
        tts.finish()

        timeout = max(20, len(text) * 0.025 + 15)
        if not complete_event.wait(timeout=timeout):
            logger.warning(f"⚠️ [VC] Timeout after {timeout:.0f}s")

    except Exception as e:
        _elapsed = _time.perf_counter() - _t0
        logger.error(
            f"❌ [VC] QwenTtsRealtime EXCEPTION after {_elapsed:.1f}s: "
            f"{type(e).__name__}: {e}",
            exc_info=True,
        )
        raise

    _elapsed = _time.perf_counter() - _t0

    if errors:
        error_msg = '; '.join(errors)
        logger.error(f"❌ [VC] Synthesis errors: {error_msg}")
        raise RuntimeError(f"VC server error: {error_msg}")

    if audio_chunks:
        pcm_data = b"".join(audio_chunks)
        wav_data = _pcm_to_wav(pcm_data)
        duration = len(pcm_data) / (PCM_SAMPLE_RATE * PCM_SAMPLE_WIDTH)
        logger.info(
            f"✅ [VC] Synthesized {len(wav_data):,} bytes WAV "
            f"({duration:.1f}s audio) in {_elapsed:.1f}s"
        )
        return wav_data
    else:
        logger.error(
            f"❌ [VC] Empty audio after {_elapsed:.1f}s — voice={voice[:30]}, "
            f"model={rt_model}, text_len={len(text)}"
        )
        raise RuntimeError("VC returned empty audio data")


def synthesize_to_file(
    text: str,
    voice: str,
    output_path: str | Path,
    *,
    model: str = DEFAULT_VC_MODEL,
    region: str = DEFAULT_REGION,
) -> Path | None:
    """
    Synthesize speech and save the audio to a file.

    Extracts audio bytes from the DashScope response and writes them to
    ``output_path``.  The caller should use an ``.mp3`` or ``.wav`` extension.

    Returns:
        The resolved output Path on success, None on failure.
    """
    try:
        audio_bytes = synthesize(text, voice, model=model, region=region)
    except Exception as exc:
        logger.error(f"❌ Synthesis failed: {exc}")
        return None

    if not audio_bytes:
        logger.error("❌ No audio data from synthesis")
        return None

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio_bytes)
    logger.info(f"💾 Cloned-voice audio saved: {out}  ({len(audio_bytes)} bytes)")
    return out


async def synthesize_to_file_async(
    text: str,
    voice: str,
    output_path: str | Path,
    *,
    model: str = DEFAULT_VC_MODEL,
    region: str = DEFAULT_REGION,
) -> Path | None:
    """Async wrapper for synthesize_to_file."""
    return await asyncio.to_thread(
        synthesize_to_file,
        text,
        voice,
        output_path,
        model=model,
        region=region,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  CHAPTER / BOOK NARRATION  (voice-cloned version)
# ═══════════════════════════════════════════════════════════════════════════

def narrate_chapter_vc(
    chapter_title: str,
    markdown_content: str,
    output_dir: str | Path,
    voice: str,
    *,
    model: str = DEFAULT_VC_MODEL,
    region: str = DEFAULT_REGION,
) -> Path | None:
    """
    Narrate a single chapter using a cloned voice.

    Strips markdown formatting, splits long text into chunks within
    the model's limit, synthesizes each chunk, and concatenates the
    resulting audio into a single file.

    Args:
        chapter_title:    Chapter title (used as filename & spoken intro).
        markdown_content: Raw markdown of the chapter.
        output_dir:       Directory where the audio file will be saved.
        voice:            Voice parameter from create_voice().
        model:            VC model.
        region:           API region.

    Returns:
        Path to the output audio file, or None on failure.
    """
    clean = _strip_markdown(markdown_content)
    if not clean or len(clean) < 10:
        logger.warning(f"⚠️ Chapter '{chapter_title}' has no narrable content")
        return None

    narration_text = f"{chapter_title}.\n\n{clean}"

    MAX_CHARS = 2000  # Smaller chunks for better VC reliability
    chunks = _split_text(narration_text, MAX_CHARS) if len(narration_text) > MAX_CHARS else [narration_text]

    all_audio: list[bytes] = []
    for i, chunk in enumerate(chunks, 1):
        logger.info(f"🔊 [VC] Synthesizing chunk {i}/{len(chunks)} ({len(chunk)} chars)...")
        try:
            audio_bytes = synthesize(chunk, voice, model=model, region=region)
            if audio_bytes:
                all_audio.append(audio_bytes)
            else:
                logger.warning(f"⚠️ Chunk {i} returned no audio")
        except Exception as exc:
            logger.warning(f"⚠️ Chunk {i} synthesis failed: {exc}")
        # Small delay between chunks to avoid overwhelming the server
        if i < len(chunks):
            _time.sleep(1.5)

    if not all_audio:
        return None

    # Properly concatenate WAV files by extracting PCM data
    import wave
    import io
    if len(all_audio) == 1:
        combined = all_audio[0]
    else:
        pcm_frames = b""
        sample_params = None
        for wav_bytes in all_audio:
            try:
                with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                    if sample_params is None:
                        sample_params = wf.getparams()
                    pcm_frames += wf.readframes(wf.getnframes())
            except Exception:
                # Fallback: treat as raw bytes if not valid WAV
                pcm_frames += wav_bytes
        if sample_params:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as out_wf:
                out_wf.setparams(sample_params)
                out_wf.writeframes(pcm_frames)
            combined = buf.getvalue()
        else:
            combined = b"".join(all_audio)

    safe_title = "".join(c if c.isalnum() or c in (" ", "_", "-") else "_" for c in chapter_title)
    safe_title = safe_title.replace(" ", "_")[:50]
    filename = f"{safe_title}_vc.wav"
    filepath = Path(output_dir) / filename

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_bytes(combined)
    logger.info(f"💾 [VC] Narration saved: {filepath} ({len(combined)} bytes)")
    return filepath


async def narrate_chapter_vc_async(
    chapter_title: str,
    markdown_content: str,
    output_dir: str | Path,
    voice: str,
    **kwargs,
) -> Path | None:
    """Async wrapper for narrate_chapter_vc."""
    return await asyncio.to_thread(
        narrate_chapter_vc,
        chapter_title,
        markdown_content,
        output_dir,
        voice,
        **kwargs,
    )


async def narrate_book_vc(
    chapters: list,
    output_dir: str | Path,
    voice: str,
    *,
    model: str = DEFAULT_VC_MODEL,
    region: str = DEFAULT_REGION,
    progress_callback=None,
) -> list[Path]:
    """
    Narrate all chapters of a book using a cloned voice.

    Args:
        chapters:          List of objects with .chapter_title and .markdown_content
        output_dir:        Base directory for audio files.
        voice:             Voice parameter from create_voice().
        model:             VC model.
        region:            API region.
        progress_callback: Optional callback(idx, total, msg).

    Returns:
        List of Paths to saved audio files.
    """
    results: list[Path] = []

    for i, chapter in enumerate(chapters):
        if progress_callback:
            progress_callback(i, len(chapters), f"🔊 [VC] Narrating chapter {i+1}: {chapter.chapter_title}")

        path = await narrate_chapter_vc_async(
            chapter_title=chapter.chapter_title,
            markdown_content=chapter.markdown_content,
            output_dir=output_dir,
            voice=voice,
            model=model,
            region=region,
        )

        if path:
            results.append(path)
            logger.info(f"✅ [VC] Chapter {i+1} done: {path}")
        else:
            logger.warning(f"⚠️ [VC] Chapter {i+1} failed: {chapter.chapter_title}")

    if progress_callback:
        progress_callback(len(chapters), len(chapters), "✅ [VC] Narration complete!")

    return results


# ═══════════════════════════════════════════════════════════════════════════
#  INTERNAL UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def _extract_audio_bytes(response) -> bytes | None:
    """
    Best-effort extraction of audio bytes from a DashScope response.

    The response shape can vary across model versions.  This function
    checks several known locations.
    """
    if response is None:
        return None

    # If the response is a dict-like object
    data = response if isinstance(response, dict) else getattr(response, "__dict__", {})

    # Try response.output.audios[0] (base64)
    output = data.get("output") or {}
    if isinstance(output, dict):
        audios = output.get("audios")
        if audios and isinstance(audios, list) and audios[0]:
            try:
                return base64.b64decode(audios[0])
            except Exception:
                pass

        # Try output.audio.data (base64 data URI or raw)
        audio_obj = output.get("audio")
        if isinstance(audio_obj, dict):
            audio_data = audio_obj.get("data", "")
            if audio_data.startswith("data:"):
                # Strip data URI prefix
                b64_part = audio_data.split(",", 1)[-1]
                try:
                    return base64.b64decode(b64_part)
                except Exception:
                    pass
            elif audio_data:
                try:
                    return base64.b64decode(audio_data)
                except Exception:
                    pass

    # Try response.audio (bytes directly)
    raw = getattr(response, "audio", None)
    if isinstance(raw, bytes) and len(raw) > 0:
        return raw

    # Try iterating choices (multimodal conversation style)
    choices = data.get("output", {}).get("choices") if isinstance(data.get("output"), dict) else None
    if choices:
        for choice in choices:
            msg = choice.get("message", {})
            for content_item in msg.get("content", []):
                if isinstance(content_item, dict) and "audio" in content_item:
                    audio_val = content_item["audio"]
                    if isinstance(audio_val, bytes):
                        return audio_val
                    if isinstance(audio_val, str):
                        try:
                            return base64.b64decode(audio_val)
                        except Exception:
                            pass

    return None


def _safe_serialize(obj) -> dict:
    """Attempt to convert a response object to a dict for logging."""
    if isinstance(obj, dict):
        return obj
    try:
        return obj.__dict__
    except AttributeError:
        return {"repr": repr(obj)}


def _strip_markdown(text: str) -> str:
    """Strip markdown formatting for cleaner TTS input."""
    import re
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", text)
    # Strip images BEFORE links — ![alt](url) contains [alt](url)
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[(IMAGE|VIDEO):\s*[^\]]+\]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks at paragraph / sentence boundaries."""
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current.strip())
            if len(para) > max_chars:
                sentences = para.replace(". ", ".\n").split("\n")
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


# ═══════════════════════════════════════════════════════════════════════════
#  CLI  — quick smoke test
# ═══════════════════════════════════════════════════════════════════════════

def _cli():
    """Interactive CLI for testing voice clone operations."""
    import argparse
    from dotenv import load_dotenv
    load_dotenv(override=True)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    parser = argparse.ArgumentParser(description="Qwen3 TTS Voice Clone Agent")
    sub = parser.add_subparsers(dest="command")

    # ── create ────────────────────────────────────────────────────────────
    p_create = sub.add_parser("create", help="Enroll a voice from an audio file")
    p_create.add_argument("audio", help="Path to reference audio (MP3/WAV/FLAC)")
    p_create.add_argument("--name", default=DEFAULT_PREFERRED_NAME, help="Preferred voice name")
    p_create.add_argument("--model", default=DEFAULT_VC_MODEL, help="Target VC model")
    p_create.add_argument("--region", default=DEFAULT_REGION, choices=list(REGION_ENDPOINTS))

    # ── list ──────────────────────────────────────────────────────────────
    p_list = sub.add_parser("list", help="List enrolled voices")
    p_list.add_argument("--model", default=DEFAULT_VC_MODEL)
    p_list.add_argument("--region", default=DEFAULT_REGION)

    # ── query ─────────────────────────────────────────────────────────────
    p_query = sub.add_parser("query", help="Query a single voice")
    p_query.add_argument("voice", help="Voice parameter string")
    p_query.add_argument("--region", default=DEFAULT_REGION)

    # ── delete ────────────────────────────────────────────────────────────
    p_delete = sub.add_parser("delete", help="Delete an enrolled voice")
    p_delete.add_argument("voice", help="Voice parameter string")
    p_delete.add_argument("--region", default=DEFAULT_REGION)

    # ── speak ─────────────────────────────────────────────────────────────
    p_speak = sub.add_parser("speak", help="Synthesize text with a cloned voice")
    p_speak.add_argument("voice", help="Voice parameter (from 'create')")
    p_speak.add_argument("text", help="Text to synthesize")
    p_speak.add_argument("-o", "--output", default="output_vc.mp3", help="Output file")
    p_speak.add_argument("--model", default=DEFAULT_VC_MODEL)
    p_speak.add_argument("--region", default=DEFAULT_REGION)

    # ── quick ─────────────────────────────────────────────────────────────
    p_quick = sub.add_parser("quick", help="One-shot: enroll + synthesize in one go")
    p_quick.add_argument("audio", help="Path to reference audio")
    p_quick.add_argument("text", help="Text to speak")
    p_quick.add_argument("-o", "--output", default="output_vc.mp3", help="Output file")
    p_quick.add_argument("--name", default=DEFAULT_PREFERRED_NAME)
    p_quick.add_argument("--model", default=DEFAULT_VC_MODEL)
    p_quick.add_argument("--region", default=DEFAULT_REGION)

    args = parser.parse_args()

    if args.command == "create":
        voice = create_voice(args.audio, target_model=args.model, preferred_name=args.name, region=args.region)
        print(f"\n🎤 Voice parameter:\n{voice}\n")

    elif args.command == "list":
        voices = list_voices(target_model=args.model, region=args.region)
        if voices:
            print(f"\n📋 {len(voices)} enrolled voice(s):")
            for v in voices:
                print(f"   • {json.dumps(v, ensure_ascii=False)}")
        else:
            print("\n(no voices found)")

    elif args.command == "query":
        info = query_voice(args.voice, region=args.region)
        print(json.dumps(info or {}, indent=2, ensure_ascii=False))

    elif args.command == "delete":
        ok = delete_voice(args.voice, region=args.region)
        print("Deleted ✅" if ok else "Failed ❌")

    elif args.command == "speak":
        path = synthesize_to_file(args.text, args.voice, args.output, model=args.model, region=args.region)
        print(f"Saved: {path}" if path else "Synthesis failed ❌")

    elif args.command == "quick":
        print("1/2  Enrolling voice …")
        voice = create_voice(args.audio, target_model=args.model, preferred_name=args.name, region=args.region)
        print(f"     Voice: {voice}")
        print("2/2  Synthesizing …")
        path = synthesize_to_file(args.text, voice, args.output, model=args.model, region=args.region)
        print(f"     Saved: {path}" if path else "     Synthesis failed ❌")

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
