# agents/video_search_agent.py
"""
YouTube video search agent using DuckDuckGo.

Searches for real YouTube educational videos related to chapter content,
generates QR codes for easy access, and returns structured VideoPlaceholder
objects ready to embed in HTML/PDF exports.
"""
import asyncio
import re
import qrcode
import base64
import logging
from io import BytesIO
from typing import Optional, List
from ddgs import DDGS
from models.book_spec import VideoPlaceholder

logger = logging.getLogger(__name__)


# ── QR-code generator ─────────────────────────────────────────────────────
def generate_qr_code(url: str) -> str:
    """Return a base64 data-URI PNG of a QR code for *url*."""
    try:
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    except Exception as e:
        logger.warning(f"QR-code generation failed: {e}")
        return ""


# ── Single-video search ───────────────────────────────────────────────────
def _build_video_query(query: str, language: str = "Spanish", topic: str = "") -> str:
    """Build a topic-focused video search query with language-aware qualifiers."""
    lang = (language or "Spanish").strip().lower()
    if lang.startswith("port"):
        qualifiers = "educativo OR educação infantil OR explicação"
    elif lang.startswith("eng"):
        qualifiers = "educational OR for kids OR explained"
    else:
        qualifiers = "educativo OR para niños OR explicación"

    base = f'"{query}"'
    if topic and topic.lower() not in query.lower():
        base = f'{topic} {base}'
    return f"site:youtube.com {base} {qualifiers}"


def _score_video_result(result: dict, query: str, topic: str = "") -> float:
    """Score a video result by relevance. Higher = better match (0.0 – 1.0)."""
    title = (result.get("title") or "").lower()
    description = (result.get("description") or "").lower()
    url = (result.get("content") or result.get("embed_url") or "").lower()
    combined = f"{title} {description}"

    query_words = {w for w in query.lower().split() if len(w) > 2}
    score = 0.0

    # Keyword overlap in title + description
    if query_words:
        combined_words = set(combined.split())
        overlap = len(query_words & combined_words) / len(query_words)
        score += overlap * 0.45

    # Topic relevance
    if topic:
        topic_lower = topic.lower()
        if topic_lower in combined:
            score += 0.25
        elif any(w in combined for w in topic_lower.split() if len(w) > 3):
            score += 0.15

    # YouTube bonus
    if "youtube.com" in url or "youtu.be" in url:
        score += 0.15

    # Educational channel bonus
    publisher = (result.get("publisher") or "").lower()
    edu_hints = ["education", "learn", "school", "academy", "kids", "niños",
                 "educativo", "ciencia", "science", "infantil"]
    if any(h in publisher or h in title for h in edu_hints):
        score += 0.1

    # Penalize clearly off-topic (music videos, gaming, etc.)
    noise = ["gameplay", "fortnite", "minecraft", "roblox", "music video",
             "official video", "lyrics", "karaoke", "remix", "vevo",
             "trailer", "unboxing"]
    if any(n in combined for n in noise):
        score -= 0.4

    return max(0.0, min(1.0, score))


async def search_youtube_video(
    query: str,
    language: str = "Spanish",
    country: str = "Mexico",
    max_results: int = 12,
    timeout: int = 12,
    topic: str = "",
) -> Optional[VideoPlaceholder]:
    """
    Search DuckDuckGo Videos for a YouTube result matching *query*.

    Results are scored by relevance to the query and topic, preferring
    educational content on YouTube.

    Returns a ``VideoPlaceholder`` with the video URL, title, and an inline
    QR-code data-URI, or ``None`` if the search fails entirely.
    """

    def _sync() -> Optional[VideoPlaceholder]:
        region = {
            "Mexico": "mx-es", "Colombia": "co-es", "Argentina": "ar-es",
            "Chile": "cl-es", "Peru": "pe-es", "Brazil": "br-pt",
        }.get(country, "wt-wt")

        enhanced = _build_video_query(query, language, topic)
        # Fallback: simpler query if enhanced returns nothing
        queries_to_try = [enhanced, f"youtube {query}"]

        for q in queries_to_try:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.videos(
                        q,
                        region=region,
                        safesearch="moderate",
                        max_results=max_results,
                        duration="short",
                    ))

                if not results:
                    logger.debug(f"No video results for '{q}'")
                    continue

                # Score and rank all results
                scored = []
                for r in results:
                    url = r.get("content") or r.get("embed_url") or ""
                    if url:
                        s = _score_video_result(r, query, topic)
                        scored.append((s, r))

                if not scored:
                    continue

                scored.sort(key=lambda x: x[0], reverse=True)
                best_score, best = scored[0]
                url = best.get("content") or best.get("embed_url") or ""
                title = best.get("title", query)
                qr = generate_qr_code(url) if url else ""

                logger.info(
                    f"🎬 Found video (score={best_score:.2f}): "
                    f"{title[:80]}  →  {url}"
                )
                return VideoPlaceholder(query=query, title=title, url=url, qr_code=qr)

            except Exception as e:
                logger.warning(f"Video search failed for '{q}': {e}")
                continue

        logger.warning(f"No videos found for '{query}' after all attempts")
        return None

    return await asyncio.to_thread(_sync)


# ── Extract [VIDEO: ...] placeholders from markdown ──────────────────────
def extract_video_placeholders(markdown: str) -> List[str]:
    """Return all ``[VIDEO: description]`` placeholder texts from markdown."""
    return re.findall(r'\[VIDEO:\s*([^\]]+)\]', markdown)


# ── Batch: resolve all videos for one chapter ────────────────────────────
async def search_videos_for_chapter(
    chapter_title: str,
    video_queries: List[str],
    topic: str = "",
    language: str = "Spanish",
    country: str = "Mexico",
) -> List[VideoPlaceholder]:
    """
    Search YouTube for every ``[VIDEO: ...]`` placeholder in a chapter.

    Returns a list of ``VideoPlaceholder`` (one per query, in order).
    Failed searches are silently skipped.
    """
    results: List[VideoPlaceholder] = []
    for q in video_queries:
        # Pass the raw query + topic separately — search_youtube_video
        # now builds enhanced queries internally and scores by relevance
        vid = await search_youtube_video(
            query=q,
            language=language,
            country=country,
            topic=topic,
        )
        if vid:
            results.append(vid)
        else:
            logger.warning(f"  ⚠️ No video found for: {q}")
    return results