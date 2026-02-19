"""
Image generation using Qwen-Image-Plus model via DashScope API (simplified).

Uses synchronous API calls for simpler error handling.
Downloads and saves generated images locally.

Documentation: https://www.alibabacloud.com/help/en/model-studio/qwen-image
"""
import os
import asyncio
import requests
from typing import Optional
from http import HTTPStatus
from pathlib import Path
from dashscope import ImageSynthesis
from models.book_spec import ImagePlaceholder

# Shared negative prompt — prevents any text/typography from appearing in images
_NO_TEXT_NEGATIVE_PROMPT = (
    "low quality, blurry, deformed, distorted, "
    "text, words, letters, numbers, captions, labels, titles, subtitles, "
    "watermark, typography, fonts, writing, inscriptions, signs with text, "
    "speech bubbles, dialogue, annotations, printed text, handwriting"
)


async def generate_image_with_qwen(
    prompt: str,
    style: str = "educational",
    size: str = "1664*928",
    output_dir: str = "./books/images",
    chapter_name: str = "images",
    image_model: str = "qwen-image-plus"
) -> Optional[ImagePlaceholder]:
    """
    Generate an image from a prompt description using Qwen-Image-Plus (async wrapper).

    This is the main async function to use for image generation.

    Args:
        prompt: Image description/prompt to generate from
        style: "educational", "story", or "artistic"
        size: Output resolution (1664*928 default for 16:9)
        output_dir: Directory to save images (will create chapter subfolder)
        chapter_name: Chapter name for organizing in subfolders

    Returns:
        ImagePlaceholder with local file path and URL, or None if generation fails
    """
    # Run sync function in thread pool to avoid blocking
    return await asyncio.get_event_loop().run_in_executor(
        None,
        _generate_image_sync,
        prompt,
        style,
        size,
        output_dir,
        chapter_name
    )


def _generate_image_sync(
    prompt: str,
    style: str = "educational",
    size: str = "1664*928",
    output_dir: str = "./books/images",
    chapter_name: str = "images",
    image_model: str = "qwen-image-plus"
) -> Optional[ImagePlaceholder]:
    """
    Synchronous image generation function (called from async wrapper).

    Args:
        prompt: Image description/prompt to generate from
        style: Visual style guide
        size: Output resolution
        output_dir: Parent directory to save images
        chapter_name: Chapter name for creating subfolders

    Returns:
        ImagePlaceholder with local file path and URL
    """
    if ImageSynthesis is None:
        print("⚠️  Warning: dashscope SDK not installed. Install with: pip install dashscope")
        return None

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("⚠️  Warning: DASHSCOPE_API_KEY environment variable not set")
        return None

    # Configure DashScope API endpoint (required for proper regional routing)
    import dashscope
    dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'

    # Create chapter-specific output directory (nested structure)
    chapter_dir = Path(output_dir) / chapter_name
    chapter_dir.mkdir(parents=True, exist_ok=True)

    # Add style guidance to prompt
    enhanced_prompt = _enhance_prompt_with_style(prompt, style)

    try:
        print(f"\n{'='*80}")
        print(f"🎨 Generating image from prompt")
        print(f"{'='*80}")
        print(f"Prompt: {enhanced_prompt[:120]}...")

        response = ImageSynthesis.call(
            api_key=api_key,
            model=image_model,
            prompt=enhanced_prompt,
            negative_prompt=_NO_TEXT_NEGATIVE_PROMPT,
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
            print(f"✅ Image generated successfully: {image_url[:80]}...")

            # Download and save image
            local_path = _download_and_save_image(image_url, prompt, str(chapter_dir))

            if local_path:
                print(f"💾 Image saved: {local_path}\n")
                return ImagePlaceholder(
                    description=prompt[:100],
                    url=local_path  # Return local path
                )
            else:
                print(f"⚠️ Failed to save image locally, using URL instead")
                return ImagePlaceholder(
                    description=prompt[:100],
                    url=image_url
                )
        else:
            print("❌ No image results returned")
            return None

    except Exception as e:
        print(f"❌ Error generating image: {e}\n")
        return None


def generate_chapter_image(
    title: str,
    summary: str,
    style: str = "educational",
    size: str = "1664*928",
    output_dir: str = "./books/images",
    chapter_name: str = "images",
    language: str = "English",
    image_model: str = "qwen-image-plus"
) -> Optional[ImagePlaceholder]:
    """
    Generate a single chapter introduction image using Qwen-Image-Plus (synchronous call).

    Downloads and saves the image locally in chapter subfolders.

    Args:
        title: Chapter title for image generation
        summary: Chapter summary to inform image content
        style: "educational", "story", or "artistic"
        size: Output resolution (1664*928 default for 16:9)
        output_dir: Parent directory to save images (will create chapter subfolder)
        chapter_name: Chapter name for organizing in subfolders
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

    # Configure DashScope API endpoint
    import dashscope
    dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'

    # Create chapter-specific output directory (nested structure)
    chapter_dir = Path(output_dir) / chapter_name
    chapter_dir.mkdir(parents=True, exist_ok=True)

    # Create descriptive prompt for chapter image
    prompt = _create_chapter_prompt(title, summary, style, language)

    try:
        print(f"\n{'='*80}")
        print(f"🎨 Generating chapter image: {title}")
        print(f"{'='*80}")
        print(f"Prompt: {prompt[:100]}...")

        response = ImageSynthesis.call(
            api_key=api_key,
            model=image_model,
            prompt=prompt,
            negative_prompt=_NO_TEXT_NEGATIVE_PROMPT,
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

            # Download and save image to chapter subfolder
            local_path = _download_and_save_image(image_url, title, str(chapter_dir))

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


def _enhance_prompt_with_style(prompt: str, style: str) -> str:
    """
    Add style guidance to a prompt. Explicitly instructs the model to
    produce pure illustration content with no text or typography of any kind.

    Args:
        prompt: Original image prompt/description
        style: Visual style ("educational", "story", "artistic")

    Returns:
        Enhanced prompt with style guidance
    """
    style_guides = {
        "educational": (
            "Educational illustration style, bright colors, clear and engaging, "
            "suitable for children's learning materials, friendly characters, simple clean design. "
            "Pure illustration only — no text, labels, captions, or written words anywhere in the image."
        ),
        "story": (
            "Storybook illustration style, warm and inviting, narrative-driven, "
            "rich colors, expressive characters, whimsical atmosphere. "
            "Pure illustration only — no text, labels, captions, or written words anywhere in the image."
        ),
        "artistic": (
            "High-quality artistic illustration, detailed, textured, professional artwork "
            "with beautiful composition and fine details. "
            "Pure illustration only — no text, labels, captions, or written words anywhere in the image."
        ),
    }

    style_desc = style_guides.get(style, style_guides["educational"])
    return f"{style_desc}\n{prompt}"


def _download_and_save_image(url: str, title: str, output_dir: str) -> Optional[str]:
    """
    Download image from URL and save it locally.

    Args:
        url: Image URL from DashScope
        title: Image description (used for filename)
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
    Explicitly instructs the model not to render any text or typography.

    Args:
        title: Chapter title
        summary: Chapter summary
        style: Visual style
        language: Language for the prompt

    Returns:
        Formatted prompt for image generation
    """
    style_guides = {
        "educational": (
            "Educational illustration style, bright colors, clear and engaging, "
            "suitable for children's learning materials, friendly characters, simple clean design. "
            "Pure illustration only — no text, labels, captions, or written words anywhere in the image."
        ),
        "story": (
            "Storybook illustration style, warm and inviting, narrative-driven, "
            "rich colors, expressive characters, whimsical atmosphere. "
            "Pure illustration only — no text, labels, captions, or written words anywhere in the image."
        ),
        "artistic": (
            "High-quality artistic illustration, detailed, textured, professional artwork "
            "with beautiful composition and fine details. "
            "Pure illustration only — no text, labels, captions, or written words anywhere in the image."
        ),
    }

    style_desc = style_guides.get(style, style_guides["educational"])

    prompt = (
        f"{style_desc}\n"
        f"Chapter title: {title}\n"
        f"Chapter topic: {summary[:200]}\n"
        f"Create a visually engaging chapter introduction image that represents the main topic. "
        f"Include relevant educational elements and make it age-appropriate for children. "
        f"The image must contain absolutely no text, words, numbers, or written characters of any kind — "
        f"convey all meaning through visual imagery alone.\n"
        f"[Generate this image in a way that would be appropriate for a {language}-speaking audience]"
    )

    return prompt