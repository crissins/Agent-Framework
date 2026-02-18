"""
Image generation using Qwen-Image-Plus model via DashScope API (simplified).

Uses synchronous API calls for simpler error handling.
Downloads and saves generated images locally.

Documentation: https://www.alibabacloud.com/help/en/model-studio/qwen-image
"""
import os
import requests
from typing import Optional
from http import HTTPStatus
from pathlib import Path

try:
    from dashscope import ImageSynthesis
except ImportError:
    ImageSynthesis = None

from models.book_spec import ImagePlaceholder


def generate_chapter_image(
    title: str,
    summary: str,
    style: str = "educational",
    size: str = "1664*928",
    output_dir: str = "./chapter_images",
    language: str = "English"
) -> Optional[ImagePlaceholder]:
    """
    Generate a single chapter introduction image using Qwen-Image-Plus (synchronous call).
    
    Downloads and saves the image locally.
    
    Args:
        title: Chapter title for image generation
        summary: Chapter summary to inform image content
        style: "educational", "story", or "artistic"
        size: Output resolution (1664*928 default for 16:9)
        output_dir: Directory to save images
        language: Language for prompt generation
        
    Returns:
        ImagePlaceholder with local file path and description, or None if generation fails
    """
    if ImageSynthesis is None:
        print("⚠️  Warning: dashscope SDK not installed. Install with: pip install dashscope")
        return None
    
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("⚠️  Warning: DASHSCOPE_API_KEY environment variable not set")
        return None
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Create descriptive prompt for chapter image
    prompt = _create_chapter_prompt(title, summary, style, language)
    
    try:
        print(f"\n{'='*80}")
        print(f"🎨 Generating chapter image: {title}")
        print(f"{'='*80}")
        print(f"Prompt: {prompt[:100]}...")
        
        # Synchronous call using call() instead of async_call()
        response = ImageSynthesis.call(
            api_key=api_key,
            model="qwen-image-plus",
            prompt=prompt,
            negative_prompt="low quality, blurry, deformed",
            n=1,
            size=size,
            prompt_extend=True,
            watermark=False
        )
        
        if response.status_code != HTTPStatus.OK:
            print(f"❌ Image generation failed: {response.code} - {response.message}")
            return None
        
        # Extract image URL
        if response.output.results and len(response.output.results) > 0:
            image_url = response.output.results[0].url
            print(f"✅ Image generated successfully")
            
            # Download and save image
            local_path = _download_and_save_image(image_url, title, output_dir)
            
            if local_path:
                print(f"💾 Image saved: {local_path}\n")
                return ImagePlaceholder(
                    description=title,
                    url=local_path  # Return local path instead of URL
                )
            else:
                print(f"⚠️ Failed to save image locally, using URL instead")
                return ImagePlaceholder(
                    description=title,
                    url=image_url
                )
        else:
            print("❌ No image results returned")
            return None
            
    except Exception as e:
        print(f"❌ Error generating image: {e}\n")
        return None


def _download_and_save_image(url: str, title: str, output_dir: str) -> Optional[str]:
    """
    Download image from URL and save it locally.
    
    Args:
        url: Image URL from DashScope
        title: Chapter title (used for filename)
        output_dir: Directory to save image
        
    Returns:
        Local file path if successful, None otherwise
    """
    try:
        # Sanitize filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip()
        safe_title = safe_title.replace(' ', '_')[:50]  # Max 50 chars
        filename = f"{safe_title}.png"
        filepath = os.path.join(output_dir, filename)
        
        # Download image
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Save to file
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        return filepath
        
    except Exception as e:
        print(f"⚠️ Error downloading image: {e}")
        return None


def _create_chapter_prompt(title: str, summary: str, style: str, language: str = "English") -> str:
    """
    Create a detailed prompt for chapter image generation.
    
    Args:
        title: Chapter title
        summary: Chapter summary
        style: Visual style
        language: Language for the prompt
        
    Returns:
        Formatted prompt for image generation
    """
    style_guides = {
        "educational": "Educational illustration style, bright colors, clear and engaging, suitable for children's learning materials, friendly characters, simple clean design.",
        "story": "Storybook illustration style, warm and inviting, narrative-driven, rich colors, expressive characters, whimsical atmosphere.",
        "artistic": "High-quality artistic illustration, detailed, textured, professional artwork with beautiful composition and fine details."
    }
    
    style_desc = style_guides.get(style, style_guides["educational"])
    
    prompt = (
        f"{style_desc}\n"
        f"Chapter title: {title}\n"
        f"Chapter topic: {summary[:200]}\n"
        f"Create a visually engaging chapter introduction image that represents the main topic. "
        f"Include relevant educational elements and make it age-appropriate for children.\n"
        f"[Generate this image in a way that would be appropriate for a {language}-speaking audience]"
    )
    
    return prompt

