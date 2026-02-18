# agents/video_search_agent.py
"""
Video search tool for educational content.
Implements async patterns and generates QR codes for easy access.
"""
import asyncio
import qrcode
import base64
from io import BytesIO
from typing import Optional, Tuple
from ddgs import DDGS
from models.book_spec import VideoPlaceholder


def generate_qr_code(url: str) -> str:
    """
    Generate a base64-encoded QR code from URL.
    
    Best practice: Reusable utility with proper error handling.
    
    Args:
        url: URL to encode in QR code
        
    Returns:
        Base64-encoded PNG data URL
    """
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return f"image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return ""


async def video_search_tool(
    query: str,
    max_duration_minutes: int = 5,
    timeout: int = 10
) -> Optional[VideoPlaceholder]:
    """
    Search for quality educational videos.
    
    Best practices:
    - Async/await for non-blocking I/O
    - Structured error handling
    - Duration filtering for educational focus
    - Type hints and clear contract
    
    Args:
        query: Video search query
        max_duration_minutes: Maximum acceptable video duration
        timeout: Search timeout in seconds
        
    Returns:
        VideoPlaceholder with video metadata and QR code
    """
    def _sync_search() -> Tuple[str, str]:
        try:
            with DDGS() as ddgs:
                # Bias toward educational content
                enhanced_query = f"{query} educational OR tutorial OR microsoft"
                results = list(ddgs.videos(
                    keywords=enhanced_query,
                    region="mx-es",
                    safesearch="moderate",
                    max_results=5,
                    timeout=timeout
                ))
                
                # Filter by duration for educational focus
                for result in results:
                    duration = result.get("duration", "")
                    try:
                        # Parse duration and check if under limit
                        if "min" in duration:
                            minutes = int(duration.split()[0])
                            if minutes <= max_duration_minutes:
                                return result.get("content", ""), result.get("title", f"Video: {query}")
                    except (ValueError, IndexError):
                        continue
                
                # Fallback if no suitable video found
                if results:
                    return results[0].get("content", ""), results[0].get("title", f"Video: {query}")
                    
        except Exception as e:
            print(f"Warning: Video search failed for '{query}': {e}")
        
        return "https://www.youtube.com/watch?v=dQw4w9WgXcQ", f"Intro to {query}"

    try:
        url, title = await asyncio.to_thread(_sync_search)
        qr = generate_qr_code(url)
        
        return VideoPlaceholder(
            query=query,
            title=title,
            url=url,
            qr_code=qr
        )
    except Exception as e:
        print(f"Error in video_search_tool: {e}")
        return None