# agents/video_search_agent.py
import asyncio
import qrcode
import base64
from io import BytesIO
from ddgs import DDGS
from models.book_spec import VideoPlaceholder

def generate_qr_code(url: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return f"image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

async def video_search_tool(query: str) -> VideoPlaceholder:
    def _sync_search():
        with DDGS() as ddgs:
            # Bias toward Microsoft/educational content
            enhanced_query = f"{query} site:youtube.com microsoft OR educational OR tutorial"
            results = ddgs.videos(
                keywords=enhanced_query,
                region="mx-es",
                safesearch="moderate",
                max_results=3
            )
            for r in results:
                duration = r.get("duration", "")
                if "h" not in duration and ("min" not in duration or int(duration.split()[0]) <= 5):
                    return r.get("content", ""), r.get("title", "Video")
            return "https://www.youtube.com/watch?v=dQw4w9WgXcQ", f"Intro to {query}"

    url, title = await asyncio.to_thread(_sync_search)
    qr = generate_qr_code(url)
    return VideoPlaceholder(query=query, title=title, url=url, qr_code=qr)