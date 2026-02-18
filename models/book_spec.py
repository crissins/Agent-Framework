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

class ChapterContent(BaseModel):
    chapter_title: str
    markdown_content: str
    # image/video placeholders kept for future use
    images: List[str] = []
    videos: List[str] = []
    image_placeholders: List[str] = []
    generated_images: List[ImagePlaceholder] = []

class BookOutput(BaseModel):
    book_request: BookRequest
    curriculum: Curriculum
    chapters: List[ChapterContent]