"""
Image generation using Qwen-Image-Plus model via DashScope API (simplified).

Uses synchronous API calls for simpler error handling.
Downloads and saves generated images locally.

Implements Qwen best practices for prompt engineering including:
- Advanced prompt formula: Entity + Environment + Style + Camera language + Atmosphere + Detail modifiers
- Support for prompt dictionary elements: shot size, perspective, lens type, style, and lighting
- Negative prompting to prevent unwanted text/typography in images
- Multiple artistic style options

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
    shot_size: str = "",
    perspective: str = "",
    lens_type: str = "",
    lighting: str = "",
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
        shot_size: Shot size description (optional)
        perspective: Perspective description (optional)
        lens_type: Lens type description (optional)
        lighting: Lighting description (optional)

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
        chapter_name,
        shot_size,
        perspective,
        lens_type,
        lighting
    )


def _generate_image_sync(
    prompt: str,
    style: str = "educational",
    size: str = "1664*928",
    output_dir: str = "./books/images",
    chapter_name: str = "images",
    shot_size: str = "",
    perspective: str = "",
    lens_type: str = "",
    lighting: str = "",
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
        shot_size: Shot size description (optional)
        perspective: Perspective description (optional)
        lens_type: Lens type description (optional)
        lighting: Lighting description (optional)

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

    # Add style guidance to prompt with optional prompt dictionary elements
    enhanced_prompt = _enhance_prompt_with_style(prompt, style, shot_size, perspective, lens_type, lighting)

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
            prompt_extend=False,
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
    shot_size: str = "",
    perspective: str = "",
    lens_type: str = "",
    lighting: str = "",
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
        shot_size: Shot size description (optional)
        perspective: Perspective description (optional)
        lens_type: Lens type description (optional)
        lighting: Lighting description (optional)

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

        # Enhance the prompt with optional elements from the prompt dictionary
        enhanced_prompt = _enhance_prompt_with_style(prompt, style, shot_size, perspective, lens_type, lighting)

        response = ImageSynthesis.call(
            api_key=api_key,
            model=image_model,
            prompt=enhanced_prompt,
            negative_prompt=_NO_TEXT_NEGATIVE_PROMPT,
            n=1,
            size=size,
            prompt_extend=False,
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


def _enhance_prompt_with_style(prompt: str, style: str, shot_size: str = "", perspective: str = "", lens_type: str = "", lighting: str = "") -> str:
    """
    Add style guidance to a prompt. Explicitly instructs the model to
    produce pure illustration content with no text or typography of any kind.
    Incorporates the five key elements from the prompt dictionary: shot size, 
    perspective, lens type, style, and lighting when provided.

    Args:
        prompt: Original image prompt/description
        style: Visual style ("educational", "story", "artistic")
        shot_size: Shot size description (optional)
        perspective: Perspective description (optional)
        lens_type: Lens type description (optional)
        lighting: Lighting description (optional)

    Returns:
        Enhanced prompt with style guidance and prompt dictionary elements
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
        "ink painting": (
            "Ink painting, white space composition, Wu Guanzhong-inspired aesthetic, delicate brushstrokes, "
            "texture of rice paper, minimal color, expressive lines and artistic conception. "
            "Aim for traditional Chinese ink painting feel — no modern typography or printed text."
        ),
        "3D cartoon": (
            "3D cartoon style with smooth surfaces, vibrant colors, and animated character design. "
            "Professional animation quality with attention to form and depth. "
            "No text or typography anywhere in the image."
        ),
        "post-apocalyptic": (
            "Post-apocalyptic art style, gritty and atmospheric, depicting scenes of decay and abandonment. "
            "Muted colors, rough textures, and dystopian themes. "
            "Pure illustration only — no text, labels, captions, or written words anywhere in the image."
        ),
        "pointillism": (
            "Pointillism style using small dots of color to form the image, inspired by artists like Seurat. "
            "Color theory applied through juxtaposed dots, creating luminosity and vibrant color effects. "
            "No text or typography in the image."
        ),
        "surrealism": (
            "Surrealist art style with dreamlike, fantastical imagery, unexpected juxtapositions, and illogical scenes. "
            "Imaginative and abstract compositions with symbolic elements. "
            "No text or typography in the image."
        ),
        "watercolor": (
            "Watercolor painting style with translucent washes of color, soft edges, and flowing paint effects. "
            "Paper texture and natural flow of pigments create organic look. "
            "No text or typography in the image."
        ),
        "clay": (
            "Claymation or clay modeling style with sculptural forms, matte textures, and three-dimensional appearance. "
            "Soft, malleable look with subtle color variations and tactile surfaces. "
            "No text or typography in the image."
        ),
        "realistic": (
            "Hyper-realistic style with photographic accuracy, detailed textures, and true-to-life representation. "
            "Attention to light, shadow, and minute details for lifelike appearance. "
            "No text or typography in the image."
        ),
        "ceramic": (
            "Ceramic or pottery style with glossy finish, smooth textures, and characteristic ceramic appearance. "
            "Attention to glaze effects, reflections, and typical ceramic properties. "
            "No text or typography in the image."
        ),
        "3D": (
            "3D rendering style with computer-generated graphics, realistic lighting, and dimensional depth. "
            "Clean surfaces, accurate shadows, and professional CG quality. "
            "No text or typography in the image."
        ),
        "origami": (
            "Origami style with folded paper appearance, geometric shapes, and crisp edges. "
            "Papercraft aesthetic with attention to folding patterns and paper texture. "
            "No text or typography in the image."
        ),
        "gongbi": (
            "Gongbi style traditional Chinese painting with meticulous brushwork, fine detail, and delicate coloring. "
            "Rich cultural heritage with refined techniques and elegant subjects. "
            "No text or typography in the image."
        ),
        "chinese ink": (
            "Chinese ink painting style with brush strokes, ink wash techniques, and traditional aesthetics. "
            "Emphasis on brushwork, ink tones, and philosophical expression. "
            "No text or typography in the image."
        ),
    }

    style_desc = style_guides.get(style, style_guides["educational"])
    
    # Build the enhanced prompt using the advanced formula: 
    # Entity (Entity description) + Environment (Environment description) + Style (Style definition) 
    # + Camera language + Atmosphere + Detail modifiers
    
    # Parse the prompt into entity and environment components
    if ":" in prompt:
        parts = prompt.split(":", 1)
        entity = parts[0].strip()
        environment = parts[1].strip()
    else:
        entity = "Main subject"
        environment = prompt
    
    # Determine camera language based on provided parameters
    camera_elements = []
    if shot_size:
        camera_elements.append(shot_size)
    if perspective:
        camera_elements.append(perspective)
    if lens_type:
        camera_elements.append(lens_type)
    
    camera_language = ", ".join(camera_elements) if camera_elements else "medium shot, centered composition, clear focal point"
    
    # Determine lighting
    lighting_element = lighting if lighting else "natural lighting as appropriate"
    
    # Construct the enhanced prompt using advanced formula
    enhanced_prompt = (
        f"{style_desc}\n"
        f"Entity: {entity}.\n"
        f"Environment: {environment}.\n"
        f"Style: {style}.\n"
        f"Camera: {camera_language}.\n"
        f"Lighting: {lighting_element}.\n"
        f"Atmosphere: Professional quality, visually appealing, appropriate for target audience.\n"
        f"Details: High resolution, fine detail, clean composition, no text or typography anywhere in the image."
    )
    
    return enhanced_prompt


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
        "ink painting": (
            "Ink painting, white space composition, Wu Guanzhong-inspired aesthetic, delicate brushstrokes, "
            "texture of rice paper, minimal color, expressive lines and artistic conception. "
            "Aim for traditional Chinese ink painting feel — no modern typography or printed text."
        ),
        "3D cartoon": (
            "3D cartoon style with smooth surfaces, vibrant colors, and animated character design. "
            "Professional animation quality with attention to form and depth. "
            "No text or typography anywhere in the image."
        ),
        "post-apocalyptic": (
            "Post-apocalyptic art style, gritty and atmospheric, depicting scenes of decay and abandonment. "
            "Muted colors, rough textures, and dystopian themes. "
            "Pure illustration only — no text, labels, captions, or written words anywhere in the image."
        ),
        "pointillism": (
            "Pointillism style using small dots of color to form the image, inspired by artists like Seurat. "
            "Color theory applied through juxtaposed dots, creating luminosity and vibrant color effects. "
            "No text or typography in the image."
        ),
        "surrealism": (
            "Surrealist art style with dreamlike, fantastical imagery, unexpected juxtapositions, and illogical scenes. "
            "Imaginative and abstract compositions with symbolic elements. "
            "No text or typography in the image."
        ),
        "watercolor": (
            "Watercolor painting style with translucent washes of color, soft edges, and flowing paint effects. "
            "Paper texture and natural flow of pigments create organic look. "
            "No text or typography in the image."
        ),
        "clay": (
            "Claymation or clay modeling style with sculptural forms, matte textures, and three-dimensional appearance. "
            "Soft, malleable look with subtle color variations and tactile surfaces. "
            "No text or typography in the image."
        ),
        "realistic": (
            "Hyper-realistic style with photographic accuracy, detailed textures, and true-to-life representation. "
            "Attention to light, shadow, and minute details for lifelike appearance. "
            "No text or typography in the image."
        ),
        "ceramic": (
            "Ceramic or pottery style with glossy finish, smooth textures, and characteristic ceramic appearance. "
            "Attention to glaze effects, reflections, and typical ceramic properties. "
            "No text or typography in the image."
        ),
        "3D": (
            "3D rendering style with computer-generated graphics, realistic lighting, and dimensional depth. "
            "Clean surfaces, accurate shadows, and professional CG quality. "
            "No text or typography in the image."
        ),
        "origami": (
            "Origami style with folded paper appearance, geometric shapes, and crisp edges. "
            "Papercraft aesthetic with attention to folding patterns and paper texture. "
            "No text or typography in the image."
        ),
        "gongbi": (
            "Gongbi style traditional Chinese painting with meticulous brushwork, fine detail, and delicate coloring. "
            "Rich cultural heritage with refined techniques and elegant subjects. "
            "No text or typography in the image."
        ),
        "chinese ink": (
            "Chinese ink painting style with brush strokes, ink wash techniques, and traditional aesthetics. "
            "Emphasis on brushwork, ink tones, and philosophical expression. "
            "No text or typography in the image."
        ),
    }

    style_desc = style_guides.get(style, style_guides["educational"])

    # Advanced prompt composition: Entity + Environment + Style + Camera language + Atmosphere + Detail modifiers
    entity = title
    environment = summary[:240] if summary else "a simple illustrative scene"
    
    prompt = (
        f"{style_desc}\n"
        f"Entity: {entity}.\n"
        f"Environment: {environment}.\n"
        f"Style notes: Follow the {style} style guidance above.\n"
        f"Create a visually engaging chapter introduction image that represents the main topic. "
        f"Include relevant educational elements and make it age-appropriate for the target audience. "
        f"The image must contain absolutely no text, words, numbers, or written characters of any kind — "
        f"convey all meaning through visual imagery alone.\n"
        f"[Generate this image in a way that would be appropriate for a {language}-speaking audience.]"
    )

    return prompt