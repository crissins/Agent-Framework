# models/book_spec.py
from typing import List
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

class ImagePlaceholder(BaseModel):
    description: str
    url: str

class VideoPlaceholder(BaseModel):
    query: str
    title: str
    url: str
    qr_code: str  # URL to QR image (not base64 for simplicity)

class ChapterContent(BaseModel):
    chapter_title: str
    markdown_content: str
    images: List[ImagePlaceholder] = []
    videos: List[VideoPlaceholder] = []