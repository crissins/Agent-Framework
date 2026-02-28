from typing import List, Optional
from pydantic import BaseModel

class BookRequest(BaseModel):
    topic: str
    target_audience_age: int
    language: str
    country: str
    learning_method: str
    num_chapters: int = 8
    pages_per_chapter: int = 12

class ChapterOutline(BaseModel):
    title: str
    summary: str

class Curriculum(BaseModel):
    title: str
    description: str
    chapters: List[ChapterOutline]

class VideoPlaceholder(BaseModel):
    """YouTube video found via DuckDuckGo search."""
    query: str = ""           # Original search query
    title: str = ""           # Video title from YouTube
    url: str = ""             # YouTube watch URL
    qr_code: str = ""         # Base64 data-URI of the QR code PNG

class ImagePlaceholder(BaseModel):
    description: str
    url: str
    # ── New image-generation metadata ────────────────────────────
    prompt: str = ""          # Full LLM-generated prompt sent to the image API
    resolution: str = ""      # e.g. "1328*1328" – chosen by the LLM
    image_model: str = ""     # e.g. "wanx2.1-t2i-plus"

class AudioNarration(BaseModel):
    """TTS audio narration for a chapter."""
    chapter_title: str = ""
    file_path: str = ""              # Local path to audio file
    duration_seconds: float = 0.0    # Estimated duration in seconds
    voice_id: str = ""               # CosyVoice voice ID used
    model: str = ""                  # TTS model used
    format: str = "mp3"              # Audio format (mp3, wav)
    size_bytes: int = 0              # File size in bytes

class ChapterContent(BaseModel):
    chapter_title: str
    markdown_content: str
    # image/video placeholders kept for future use
    images: List[str] = []
    videos: List[VideoPlaceholder] = []
    image_placeholders: List[str] = []
    video_placeholders: List[str] = []
    generated_images: List[ImagePlaceholder] = []
    audio_narration: Optional[AudioNarration] = None

class BookOutput(BaseModel):
    book_request: BookRequest
    curriculum: Curriculum
    chapters: List[ChapterContent]