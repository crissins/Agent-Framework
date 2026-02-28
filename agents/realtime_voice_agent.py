"""
Realtime Voice Agent using Qwen3-Omni-Flash via DashScope WebSocket.

Provides a bidirectional voice conversation where the user speaks and the
model responds with both text and audio in real time.  Designed for
collecting book generation preferences through natural spoken dialogue.

Model : qwen3-omni-flash-realtime  (free 1M-token quota, 90 days)
Protocol: DashScope Realtime WebSocket API
Voices : Sonrisa (LATAM woman), Bodega (Spanish man), Elias (educational),
         Cherry, Ethan, Serena, and 40+ others.

Audio formats:
  - Input  : pcm  (16-bit, 16 kHz mono)
  - Output : pcm  (24-bit, 24 kHz mono)  →  converted to 16-bit for playback

Requirements:
  - dashscope >= 1.22  (includes qwen_omni realtime support)
  - pyaudio             (microphone capture & speaker playback)

Usage:
    from agents.realtime_voice_agent import RealtimeVoiceSession

    session = RealtimeVoiceSession(
        voice="Sonrisa",
        system_prompt="You are a friendly book assistant...",
    )
    session.start()   # Opens mic + speaker, begins conversation
    session.stop()    # Gracefully shuts down
"""

import json
import logging
import os
import struct
import threading
import time
import wave
from io import BytesIO
from pathlib import Path
from typing import Callable, Optional, List

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────

REALTIME_MODEL = "qwen3-omni-flash-realtime"

# WebSocket endpoint (international / Singapore)
REALTIME_WS_URL = (
    "wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime"
    f"?model={REALTIME_MODEL}"
)

# Audio parameters
INPUT_SAMPLE_RATE = 16000   # 16 kHz mono PCM-16
OUTPUT_SAMPLE_RATE = 24000  # 24 kHz mono PCM-24  (from model)
PLAYBACK_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024           # frames per PyAudio buffer

# ── Available Voices (subset relevant for LATAM educational content) ──────

REALTIME_VOICES = {
    # Latin American / Spanish
    "Sonrisa":  "Female · Latin American · Warm & friendly",
    "Bodega":   "Male · Spanish · Deep & narrative",
    # English — Educational / Storytelling
    "Elias":    "Male · English · Educational storyteller",
    "Cherry":   "Female · English · Sweet & engaging",
    "Ethan":    "Male · English · Calm & professional",
    "Serena":   "Female · English · Gentle & soothing",
    # Portuguese
    "Amara":    "Female · Portuguese BR · Warm & clear",
    # Neutral / General
    "Chelsie":  "Female · English · Narrator",
    "River":    "Male · English · Natural conversational",
}

# ── Default system prompt for book creation assistant ─────────────────────

DEFAULT_SYSTEM_PROMPT = """\
### CONTEXT ###
You are **LibroBot Voice**, a warm and enthusiastic educational book design
assistant.  You help users plan interactive books for children in Latin
America through natural spoken conversation.

### OBJECTIVE ###
Collect the following information conversationally:
1. Book topic
2. Target audience age (6-16)
3. Country & language
4. Learning method (Scandinavian / Montessori / Project-Based)
5. Number of chapters and pages per chapter
6. Image style preferences (watercolor, cartoon, realistic, etc.)

### STYLE ###
- Speak naturally, as if brainstorming with a friend.
- Keep responses SHORT (1-3 sentences) since this is voice.
- Ask one question at a time.
- Use encouraging phrases: "Great choice!", "Love that idea!"
- Match the user's language (Spanish, Portuguese, or English).

### TONE ###
Friendly, enthusiastic, and creative.

### RULES ###
- After collecting all info, verbally summarize and ask for confirmation.
- Once confirmed, say the magic phrase: "BOOK_REQUEST_READY" followed by
  a JSON summary (the text transcript will be parsed by the app).
"""


class RealtimeVoiceSession:
    """
    Manages a bidirectional voice session with Qwen3-Omni-Flash-Realtime.

    Uses the DashScope Python SDK ``OmniRealtimeConversation`` when available,
    falling back to raw WebSocket if needed.
    """

    def __init__(
        self,
        voice: str = "Sonrisa",
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        on_text: Optional[Callable[[str], None]] = None,
        on_audio: Optional[Callable[[bytes], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_session_end: Optional[Callable[[], None]] = None,
        language: str = "es",
    ):
        """
        Args:
            voice:          Voice ID (see REALTIME_VOICES).
            system_prompt:  System instructions for the model.
            on_text:        Callback for each text transcript chunk.
            on_audio:       Callback for each audio chunk (PCM bytes).
            on_error:       Callback for error messages.
            on_session_end: Callback when session ends.
            language:       ISO 639-1 code (es, pt, en).
        """
        self.voice = voice
        self.system_prompt = system_prompt
        self.language = language

        # Callbacks
        self._on_text = on_text or (lambda t: None)
        self._on_audio = on_audio or (lambda a: None)
        self._on_error = on_error or (lambda e: logger.error(e))
        self._on_session_end = on_session_end or (lambda: None)

        # State
        self._running = False
        self._conversation = None
        self._mic_thread: Optional[threading.Thread] = None
        self._transcript_chunks: List[str] = []
        self._audio_chunks: List[bytes] = []

    # ── Public API ────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def full_transcript(self) -> str:
        """Return the accumulated text transcript."""
        return "".join(self._transcript_chunks)

    def start(self) -> bool:
        """
        Start the realtime voice session.

        Returns True if started successfully, False otherwise.
        """
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            self._on_error("DASHSCOPE_API_KEY not set — cannot start voice session")
            return False

        try:
            return self._start_with_sdk(api_key)
        except ImportError:
            logger.info("DashScope OmniRealtime SDK not available, using raw WebSocket")
            return self._start_with_websocket(api_key)
        except Exception as exc:
            self._on_error(f"Failed to start voice session: {exc}")
            return False

    def stop(self):
        """Gracefully stop the voice session."""
        self._running = False
        if self._conversation:
            try:
                self._conversation.stop()
            except Exception:
                pass
            self._conversation = None
        if self._mic_thread and self._mic_thread.is_alive():
            self._mic_thread.join(timeout=3)
        self._on_session_end()
        logger.info("Voice session stopped")

    def send_text(self, text: str):
        """Send a text message to the model (useful for hybrid mode)."""
        if self._conversation and self._running:
            try:
                self._conversation.send_text(text)
            except Exception as exc:
                self._on_error(f"Failed to send text: {exc}")

    # ── SDK-based implementation ──────────────────────────────────────

    def _start_with_sdk(self, api_key: str) -> bool:
        """Start using DashScope OmniRealtimeConversation SDK."""
        from dashscope.audio.qwen_omni import (
            OmniRealtimeConversation,
            OmniRealtimeCallback,
        )

        session = self  # closure reference

        class _Callback(OmniRealtimeCallback):
            """Handles events from the realtime model."""

            def on_open(self):
                logger.info("🎤 Realtime session opened")
                session._running = True

            def on_event(self, event_type: str, data: dict):
                """Handle generic events."""
                logger.debug("Event: %s → %s", event_type, data)

            def on_text(self, text: str, is_final: bool):
                """Model produced text output."""
                session._transcript_chunks.append(text)
                session._on_text(text)

            def on_audio(self, audio_data: bytes):
                """Model produced audio output."""
                session._audio_chunks.append(audio_data)
                session._on_audio(audio_data)

            def on_error(self, error: str):
                logger.error("Realtime error: %s", error)
                session._on_error(error)

            def on_close(self):
                logger.info("🔇 Realtime session closed")
                session._running = False
                session._on_session_end()

        callback = _Callback()

        self._conversation = OmniRealtimeConversation(
            model=REALTIME_MODEL,
            callback=callback,
            api_key=api_key,
            base_ws_url="wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime",
        )

        # Configure session
        self._conversation.start(
            session_config={
                "model": REALTIME_MODEL,
                "modalities": ["audio", "text"],
                "voice": self.voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm24",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                },
                "instructions": self.system_prompt,
            }
        )

        # Start microphone capture in a background thread
        self._mic_thread = threading.Thread(
            target=self._capture_microphone,
            daemon=True,
        )
        self._mic_thread.start()

        return True

    # ── Raw WebSocket fallback ────────────────────────────────────────

    def _start_with_websocket(self, api_key: str) -> bool:
        """Start using raw websocket-client as fallback."""
        try:
            import websocket
        except ImportError:
            self._on_error(
                "Neither dashscope.audio.qwen_omni nor websocket-client is available. "
                "Install with: pip install dashscope websocket-client"
            )
            return False

        import base64

        session = self

        def on_message(ws, message):
            try:
                data = json.loads(message)
                event_type = data.get("type", "")

                if event_type == "response.audio.delta":
                    audio_b64 = data.get("delta", "")
                    if audio_b64:
                        audio_bytes = base64.b64decode(audio_b64)
                        session._audio_chunks.append(audio_bytes)
                        session._on_audio(audio_bytes)

                elif event_type == "response.text.delta":
                    text = data.get("delta", "")
                    if text:
                        session._transcript_chunks.append(text)
                        session._on_text(text)

                elif event_type == "error":
                    session._on_error(data.get("error", {}).get("message", str(data)))

            except Exception as exc:
                logger.exception("Error processing WS message: %s", exc)

        def on_error(ws, error):
            session._on_error(str(error))

        def on_close(ws, close_status, close_msg):
            session._running = False
            session._on_session_end()

        def on_open(ws):
            session._running = True
            # Send session.update with config
            config_msg = {
                "type": "session.update",
                "session": {
                    "model": REALTIME_MODEL,
                    "modalities": ["audio", "text"],
                    "voice": session.voice,
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm24",
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500,
                    },
                    "instructions": session.system_prompt,
                },
            }
            ws.send(json.dumps(config_msg))
            logger.info("🎤 WebSocket session configured")

            # Start microphone capture
            session._mic_thread = threading.Thread(
                target=session._capture_microphone_ws,
                args=(ws,),
                daemon=True,
            )
            session._mic_thread.start()

        ws_url = f"{REALTIME_WS_URL}"
        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        self._ws = websocket.WebSocketApp(
            ws_url,
            header=headers,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )

        # Run WebSocket in a background thread
        ws_thread = threading.Thread(
            target=self._ws.run_forever,
            daemon=True,
        )
        ws_thread.start()

        # Wait a moment for connection
        time.sleep(1.0)
        return self._running

    # ── Microphone capture ────────────────────────────────────────────

    def _capture_microphone(self):
        """Capture audio from microphone and send to SDK conversation."""
        try:
            import pyaudio
        except ImportError:
            self._on_error(
                "PyAudio not installed. Install with: pip install pyaudio"
            )
            return

        pa = pyaudio.PyAudio()
        stream = None
        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=INPUT_SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
            )
            logger.info("🎤 Microphone capture started (16kHz mono PCM-16)")

            while self._running:
                try:
                    data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    if self._conversation:
                        self._conversation.send_audio(data)
                except OSError:
                    break
        except Exception as exc:
            self._on_error(f"Microphone error: {exc}")
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            pa.terminate()
            logger.info("🎤 Microphone capture stopped")

    def _capture_microphone_ws(self, ws):
        """Capture audio from microphone and send via raw WebSocket."""
        try:
            import pyaudio
        except ImportError:
            self._on_error("PyAudio not installed.")
            return

        import base64

        pa = pyaudio.PyAudio()
        stream = None
        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=INPUT_SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
            )
            logger.info("🎤 Microphone capture started (WebSocket mode)")

            while self._running:
                try:
                    data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    audio_b64 = base64.b64encode(data).decode("ascii")
                    msg = {
                        "type": "input_audio_buffer.append",
                        "audio": audio_b64,
                    }
                    ws.send(json.dumps(msg))
                except (OSError, Exception):
                    break
        except Exception as exc:
            self._on_error(f"Microphone error: {exc}")
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            pa.terminate()

    # ── Audio playback helper ─────────────────────────────────────────

    @staticmethod
    def play_audio_chunk(audio_data: bytes, sample_rate: int = PLAYBACK_SAMPLE_RATE):
        """
        Play a PCM audio chunk through the default speaker.

        Args:
            audio_data: Raw PCM bytes (24-bit from model, needs conversion).
            sample_rate: Sample rate for playback.
        """
        try:
            import pyaudio
        except ImportError:
            return

        pa = pyaudio.PyAudio()
        try:
            # Model outputs PCM-24 (3 bytes/sample) — convert to PCM-16 (2 bytes/sample)
            pcm16 = _pcm24_to_pcm16(audio_data)
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                output=True,
            )
            stream.write(pcm16)
            stream.stop_stream()
            stream.close()
        finally:
            pa.terminate()

    # ── Transcript extraction ─────────────────────────────────────────

    def extract_book_request(self) -> Optional[dict]:
        """
        Try to extract a book request from the accumulated transcript.

        Looks for BOOK_REQUEST_READY followed by JSON.
        """
        transcript = self.full_transcript
        marker = "BOOK_REQUEST_READY"
        idx = transcript.find(marker)
        if idx < 0:
            return None

        after = transcript[idx + len(marker):]
        # Try to find JSON in the remaining text
        import re
        json_match = re.search(r'\{[^{}]+\}', after, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                return None
        return None

    def save_conversation_audio(self, output_path: str) -> Optional[str]:
        """
        Save accumulated model audio output as a WAV file.

        Args:
            output_path: Destination file path.

        Returns:
            Path to saved file, or None if no audio.
        """
        if not self._audio_chunks:
            return None

        all_audio = b"".join(self._audio_chunks)
        pcm16 = _pcm24_to_pcm16(all_audio)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(PLAYBACK_SAMPLE_RATE)
            wf.writeframes(pcm16)

        logger.info("💾 Conversation audio saved to %s", output_path)
        return output_path


# ── Utility functions ─────────────────────────────────────────────────────

def _pcm24_to_pcm16(data: bytes) -> bytes:
    """
    Convert PCM-24 (3 bytes/sample, little-endian) to PCM-16 (2 bytes/sample).

    The conversion drops the least significant byte of each 24-bit sample.
    """
    if len(data) % 3 != 0:
        # Already PCM-16 or unknown format — return as-is
        return data

    samples = []
    for i in range(0, len(data), 3):
        # 24-bit LE: byte0 (LSB), byte1, byte2 (MSB)
        # Take upper 16 bits: byte1 + byte2
        sample_16 = struct.unpack_from("<h", data, i + 1)[0]
        samples.append(sample_16)

    return struct.pack(f"<{len(samples)}h", *samples)


def get_available_voices() -> dict:
    """Return available voices for the realtime model."""
    return REALTIME_VOICES.copy()
