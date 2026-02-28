"""
Image generation using Qwen-Image models via DashScope API.

Uses synchronous API calls for simpler error handling.
Downloads and saves generated images locally.

Key features:
- **LLM-driven prompt generation**: A text model creates rich image prompts
  following the advanced formula (Entity + Environment + Style + Camera
  language + Atmosphere + Detail modifiers) – the user never has to pick
  shot size, perspective, lens type, style, or lighting manually.
- Negative prompting to prevent unwanted text/typography in images.
- Support for all five Qwen-Image fixed resolutions.

Documentation: https://www.alibabacloud.com/help/en/model-studio/qwen-image
"""
import os
import asyncio
import requests
import logging
from typing import Optional
from http import HTTPStatus
from pathlib import Path
from dashscope import ImageSynthesis
from models.book_spec import ImagePlaceholder

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Supported Qwen-Image resolutions ─────────────────────────────────────────
QWEN_IMAGE_RESOLUTIONS = {
    "1664*928":  "16:9 (landscape, default)",
    "1472*1104": "4:3 (landscape)",
    "1328*1328": "1:1 (square)",
    "1104*1472": "3:4 (portrait)",
    "928*1664":  "9:16 (tall portrait)",
}

# Shared negative prompt — aggressively prevents ANY text/typography/numbers/letters
_NO_TEXT_NEGATIVE_PROMPT = (
    "text, words, letters, numbers, digits, alphabet, characters, chinese characters, "
    "hanzi, kanji, hiragana, katakana, arabic script, cyrillic, english text, spanish text, "
    "captions, labels, titles, subtitles, watermark, typography, fonts, writing, "
    "inscriptions, signs, signage, street signs, book covers with text, newspaper, "
    "speech bubbles, dialogue, annotations, printed text, handwriting, calligraphy, "
    "signature, logo, brand name, brand, trademark, copyright symbol, "
    "equations, formulas, mathematical notation, roman numerals, "
    "banners, ribbons with text, plaques, nameplates, license plates, "
    "scoreboard, clock face with numbers, calendar, price tags, barcodes, QR codes, "
    "blur, low quality, deformed, distorted, "
    "unnatural anatomy, disfigured, bad art, ugly, pixelated, grain, glitch"
)

# ── LOW-BUDGET coloring-page negative prompt ──────────────────────────────────
_LOW_BUDGET_NEGATIVE_PROMPT = (
    "colors, shading, gradients, grayscale, photorealistic elements, complex details, "
    "dark fills, textures, watermark, text, words, letters, numbers, blurry, "
    "low quality, deformed, distorted, ugly, pixelated"
)


def _build_low_budget_prompt(subject: str) -> str:
    """Build a fixed coloring-page prompt for the LOW BUDGET style.

    The entire prompt is pre-defined; only the SUBJECT is swapped in.
    This ensures every image in the book is a consistent B&W line drawing.
    """
    return (
        "Create a black and white line drawing coloring page for young children ages 4-8. "
        "STYLE REQUIREMENTS: Pure black and white line art only, NO colors, NO shading, "
        "NO grayscale. Clean, bold outlines with thick lines. Simple, clear shapes "
        "suitable for coloring. Coloring book style with well-defined boundaries. "
        "White background. Educational worksheet format. "
        f"SUBJECT: {subject}. "
        "SPECIFICATIONS: Child-friendly, cute cartoon style. Simple and uncluttered "
        "composition. Large, easy-to-color areas. No tiny details or complex patterns. "
        "Friendly, smiling characters. Appropriate for preschool/early elementary "
        "education. Line thickness: medium to bold. High contrast black lines on "
        "white background."
    )


# ─────────────────────────────────────────────────────────────────────────────
# LLM-POWERED IMAGE PROMPT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

# System instructions for the image-prompt agent.  Contains the full
# "prompt dictionary" so the LLM always picks concrete camera, lighting,
# and style terms from the reference lists.
_IMAGE_PROMPT_SYSTEM = """### CONTEXT ###
You are a professional prompt engineer specializing in the Qwen text-to-image model with
10+ years of experience in digital art direction, photography, and visual storytelling
for educational content. You understand composition, lighting, color theory, and how to
create age-appropriate, culturally sensitive imagery.

### OBJECTIVE ###
Transform a chapter title + summary into TWO outputs:
1. A richly-detailed image-generation prompt in English
2. The optimal resolution for this particular image

### STYLE SELECTION GUIDE ###
Choose the SINGLE most fitting style based on subject matter — do NOT rely on user hints:

| Subject Matter                      | Recommended Style              |
|-------------------------------------|--------------------------------|
| Real animals, nature, people, food  | Realistic photography          |
| Architecture, cityscapes, objects   | Realistic photography          |
| Playful topics for ages 8-10        | 3D cartoon / Pixar-style 3D   |
| Diagrams, processes, timelines      | Educational illustration       |
| Scientific concepts, abstract ideas | Educational illustration       |
| Artistic, emotional, poetic themes  | Watercolor                     |
| Historical scenes, classical topics | Oil painting                   |
| Abstract, philosophical, dreamlike  | Surrealism / Ink painting      |

When in doubt, prefer **Realistic photography** or **Educational illustration**.

### AVAILABLE STYLES (pick ONE) ###
- Watercolor painting — soft edges, translucent layers, dreamy aesthetic
- Fun, colorful cartoon style — bold outlines, vibrant flat colors, playful expressions
- Realistic photography — lifelike textures, natural lighting, photographic depth of field
- Modern flat design / vector art — clean geometric shapes, minimal gradients, contemporary UI aesthetic
- Retro pixel art — 8-bit/16-bit aesthetic, blocky textures, nostalgic gaming vibe
- Classic storybook illustration — hand-drawn charm, whimsical details, narrative warmth
- 3D cartoon / Pixar-style 3D — expressive characters, soft subsurface scattering, cinematic rendering
- Oil painting — rich brushstrokes, blended colors, traditional fine art texture
- Educational illustration — clear visual hierarchy, labeled elements, infographic clarity
- Ink painting / Sumi-e — minimalist brushwork, expressive negative space, East Asian artistic tradition

### ADVANCED PROMPT FORMULA ###
Build the prompt following this exact structure:

  Entity (main subject with characteristics and actions)
  + Environment (setting, location, weather, time of day)
  + Style (from the styles list above)
  + Camera language (shot size + perspective + lens type)
  + Atmosphere (emotional tone and mood)
  + Detail modifiers (technical quality + lighting + composition + material)

=== PROMPT DICTIONARY (pick ONE from each category) ===

SHOT SIZE  : Extreme close-up | Close-up | Medium shot | Full shot | Long shot
PERSPECTIVE: Eye level | Bird's eye | Low angle | High angle | Aerial | Worm's eye
LENS TYPE  : Standard | Wide angle | Ultra-wide angle | Telephoto | Macro | Fisheye
LIGHTING   : Natural sunlight | Golden hour | Blue hour | Cinematic lighting |
             Backlight | Neon lights | Ambient light | Studio lighting |
             Dramatic side-light | Soft diffused light | Moonlight | Rim lighting |
             Tyndall effect | Softbox lighting | Volumetric fog | Neon glow |
             Ambient occlusion
ATMOSPHERE : dreamy | serene | majestic | mysterious | whimsical | melancholic |
             energetic | romantic | epic | cozy | futuristic | nostalgic |
             childlike wonder | cinematic | ethereal
COMPOSITION: centered composition | rule of thirds | symmetrical | dynamic angle |
             shallow depth of field | bokeh background | leading lines
QUALITY    : 4K | 8K | UHD | high resolution | sharp focus | professional color grading |
             octane rendering | C4D rendering | hyper realistic | magazine quality
MATERIAL   : felt material | ceramic texture | watercolor paper grain | oil canvas texture |
             pixel grid | vector crisp edges | ink bleed effect

=== AVAILABLE RESOLUTIONS ===
Pick the BEST resolution for the content. **Prefer smaller resolutions** to save costs.

  1328*1328  – 1:1 square     (DEFAULT – good for most educational content)
  1104*1472  – 3:4 portrait   (characters, people, vertical scenes)
  928*1664   – 9:16 tall      (tall buildings, trees, full-body portraits)
  1472*1104  – 4:3 landscape  (wide scenes, panoramas, groups)
  1664*928   – 16:9 wide      (ONLY for truly cinematic/panoramic scenes)

### OUTPUT FORMAT ###
Reply with EXACTLY two lines and NOTHING else:
Line 1: RESOLUTION: <width*height>
Line 2: PROMPT: <your image prompt>

Example:
RESOLUTION: 1328*1328
PROMPT: A wool-felt panda wearing a blue police vest, running through animal kingdom city street shops at night, 3D cartoon Pixar-style rendering, medium shot, eye level perspective, standard lens, cinematic backlight with Tyndall effect, childlike wonder and adorable atmosphere, felt material texture, centered composition, 4K resolution, sharp focus, professional quality

### RULES ###
1. Output ONLY the two lines above — no markdown, no extra text, no explanations
2. The prompt MUST be in English regardless of the chapter language
3. NEVER include any request for text, words, letters, numbers, digits, labels, titles, signs, watermarks, writing, or typography of ANY kind. The image must be PURELY VISUAL with ZERO readable characters. This is the MOST IMPORTANT rule.
4. ALWAYS explicitly state: shot size, perspective, lens type, style, lighting, atmosphere, and at least one detail modifier
5. Add atmosphere keywords ("warm and inviting", "mysterious", "dreamy", "majestic")
   and detail modifiers ("4K", "UHD", "sharp focus", "fine detail", "professional quality")
6. Keep the prompt between 60 and 200 words
7. Make imagery age-appropriate and culturally sensitive
8. Focus ONLY on the educational topic — do NOT depict country flags, national symbols, or landmarks
9. Prefer 1328*1328 (square) or 1104*1472 (portrait) for most images
10. Choose the style yourself based on the subject matter using the Style Selection Guide above
11. Include material/texture descriptors when they enhance the chosen style
12. NEVER describe text on chalkboards, books, papers, screens, or any surface — show ONLY visual imagery"""


# Default resolution when LLM doesn't specify or parsing fails
_DEFAULT_RESOLUTION = "1328*1328"


def _parse_llm_image_response(raw: str) -> tuple[str, str]:
    """Parse the two-line LLM response into (resolution, prompt).

    Expected format:
        RESOLUTION: 1328*1328
        PROMPT: A cheerful robot …

    Returns:
        (resolution, prompt) – falls back to defaults on parse failure.
    """
    resolution = _DEFAULT_RESOLUTION
    prompt = raw.strip()

    import re as _re
    res_match = _re.search(r'RESOLUTION:\s*(\d+\*\d+)', raw, _re.IGNORECASE)
    if res_match:
        candidate = res_match.group(1)
        if candidate in QWEN_IMAGE_RESOLUTIONS:
            resolution = candidate
        else:
            logger.warning(f"LLM returned unknown resolution '{candidate}', using default {_DEFAULT_RESOLUTION}")

    prompt_match = _re.search(r'PROMPT:\s*(.+)', raw, _re.IGNORECASE | _re.DOTALL)
    if prompt_match:
        prompt = prompt_match.group(1).strip()

    return resolution, prompt


def _generate_llm_image_prompt(
    title: str,
    summary: str,
    language: str = "English",
    country: str = "",
    audience_age: int = 10,
    use_qwen: bool = False,
    text_model: Optional[str] = None,
    art_style: str = "auto",
) -> tuple[str, str]:
    """Call the text LLM to produce a rich image-generation prompt AND resolution.

    The LLM automatically picks the best style based on the subject matter
    (e.g. realistic photography for animals, 3D cartoon for playful topics).
    Falls back to the old template approach if the LLM call fails.

    When *art_style* is ``"low_budget"`` the LLM is bypassed entirely and a
    fixed black-and-white coloring-page prompt is returned instead.

    Args:
        title: Chapter title
        summary: Chapter summary / description
        language: Audience language (for cultural context, NOT for the prompt itself)
        country: Audience country (cultural context)
        audience_age: Target reader age
        use_qwen: Whether to use Qwen text models (vs GitHub Models)
        text_model: Explicit model id override
        art_style: Art style key or 'auto'

    Returns:
        Tuple of (prompt_text, resolution) where resolution is a QWEN_IMAGE_RESOLUTIONS key.
    """
    # ── LOW BUDGET fast-path: skip the LLM entirely ───────────────
    if art_style == "low_budget":
        subject = f"{title}. {summary[:300]}"
        prompt = _build_low_budget_prompt(subject)
        logger.info(f"🖍️  Low-budget coloring page prompt for: {title[:60]}")
        return prompt, _DEFAULT_RESOLUTION
    from config import get_model_config

    config = get_model_config(use_qwen)
    api_key = os.getenv(config["api_key_env"], "")
    base_url = config["base_url"]
    model_id = text_model or config.get("model_id")

    if not api_key:
        logger.warning("No API key for text model – falling back to template prompt")
        return _template_fallback_prompt(title, summary), _DEFAULT_RESOLUTION

    user_msg = (
        f"Chapter title: {title}\n"
        f"Chapter summary: {summary}\n"
        f"Audience: {audience_age}-year-olds, reading in {language}.\n"
    )
    if art_style and art_style != "auto":
        _STYLE_LABELS = {
            "watercolor": "Watercolor painting — soft edges, translucent layers, dreamy aesthetic",
            "cartoon": "Fun, colorful cartoon style — bold outlines, vibrant flat colors, playful expressions",
            "realistic": "Realistic photography — lifelike textures, natural lighting, photographic depth of field",
            "flat_vector": "Modern flat design / vector art — clean geometric shapes, minimal gradients",
            "pixel_art": "Retro pixel art — 8-bit/16-bit aesthetic, blocky textures, nostalgic gaming vibe",
            "storybook": "Classic storybook illustration — hand-drawn charm, whimsical details, narrative warmth",
            "3d_cartoon": "3D cartoon / Pixar-style 3D — expressive characters, cinematic rendering",
            "oil_painting": "Oil painting — rich brushstrokes, blended colors, fine art texture",
            "educational": "Educational illustration — clear visual hierarchy, infographic clarity",
            "ink_painting": "Ink painting / Sumi-e — minimalist brushwork, expressive negative space",
            # low_budget is handled separately — should never reach here
        }
        style_label = _STYLE_LABELS.get(art_style, art_style)
        user_msg += f"IMPORTANT: Use this specific art style: {style_label}.\n"
    user_msg += (
        f"Choose the best resolution, "
        f"and generate the image prompt now."
    )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": _IMAGE_PROMPT_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=500,
            temperature=0.9,
        )
        raw = resp.choices[0].message.content.strip()
        resolution, prompt_text = _parse_llm_image_response(raw)
        logger.info(f"🖼️  LLM image prompt ({len(prompt_text)} chars, {resolution}): {prompt_text[:120]}...")
        return prompt_text, resolution
    except Exception as exc:
        logger.warning(f"LLM image-prompt generation failed ({exc}); using template fallback")
        return _template_fallback_prompt(title, summary), _DEFAULT_RESOLUTION


def _template_fallback_prompt(title: str, summary: str) -> str:
    """Simple template prompt used when the LLM is unavailable."""
    return (
        f"ABSOLUTELY NO TEXT, NO LETTERS, NO NUMBERS, NO WORDS, NO WRITING. "
        f"Realistic photography style, medium shot, eye level perspective, "
        f"standard lens, natural sunlight, warm and inviting atmosphere, "
        f"fine detail, professional quality, 4K. "
        f"Subject: {title}. Setting: {summary[:300]}. "
        f"The image must contain zero readable characters."
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
    Generate an image from a prompt description using Qwen-Image (async wrapper).

    The prompt should already be a rich, LLM-generated description.  If a simple
    description is provided it will still work but won't be as detailed.

    Args:
        prompt: Full image-generation prompt (ideally produced by LLM)
        style: Style hint (used only if prompt needs light enhancement)
        size: Output resolution — one of QWEN_IMAGE_RESOLUTIONS keys
        output_dir: Directory to save images (will create chapter subfolder)
        chapter_name: Chapter name for organizing in subfolders
        image_model: Qwen image model id

    Returns:
        ImagePlaceholder with local file path and URL, or None if generation fails
    """
    return await asyncio.to_thread(
        _generate_image_sync,
        prompt,
        style,
        size,
        output_dir,
        chapter_name,
        image_model,
    )


from utils.retry import sync_retry

@sync_retry(max_retries=3, base_delay=5.0, max_delay=60.0)
def _call_dashscope_api(api_key, image_model, enhanced_prompt, size,
                       negative_prompt: str | None = None):
    """
    Helper to call DashScope API with retry logic.
    Raises exception on non-200 status to trigger retry.
    """
    neg = negative_prompt if negative_prompt is not None else _NO_TEXT_NEGATIVE_PROMPT
    response = ImageSynthesis.call(
        api_key=api_key,
        model=image_model,
        prompt=enhanced_prompt,
        negative_prompt=neg,
        n=1,
        size=size,
        prompt_extend=False,
        watermark=False
    )
    
    if response.status_code != HTTPStatus.OK:
        raise Exception(f"Image generation failed: {response.code} - {response.message}")
        
    return response


def _generate_image_sync(
    prompt: str,
    style: str = "educational",
    size: str = "1664*928",
    output_dir: str = "./books/images",
    chapter_name: str = "images",
    image_model: str = "qwen-image-plus",
) -> Optional[ImagePlaceholder]:
    """
    Synchronous image generation (called from async wrapper).

    The *prompt* should already be a richly-detailed description produced by
    the LLM image-prompt agent.  A thin safety wrapper is still applied to
    ensure the "no text" instruction is present.
    """
    if ImageSynthesis is None:
        print("⚠️  Warning: dashscope SDK not installed. Install with: pip install dashscope")
        return None

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("⚠️  Warning: DASHSCOPE_API_KEY environment variable not set")
        return None

    import dashscope
    dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'

    chapter_dir = Path(output_dir) / chapter_name
    chapter_dir.mkdir(parents=True, exist_ok=True)

    # Light wrapper — ensures the no-text instruction is present even if
    # the LLM forgot it.  Does NOT re-template the whole prompt.
    enhanced_prompt = _ensure_no_text_instruction(prompt)

    try:
        logger.info(f"🎨 Generating image from prompt")
        logger.info(f"Prompt: {enhanced_prompt[:160]}...")

        response = _call_dashscope_api(api_key, image_model, enhanced_prompt, size)

        if response.output.results and len(response.output.results) > 0:
            image_url = response.output.results[0].url
            logger.info(f"✅ Image generated successfully: {image_url[:80]}...")

            local_path = _download_and_save_image(image_url, prompt, str(chapter_dir))

            if local_path:
                logger.info(f"💾 Image saved: {local_path}\n")
                return ImagePlaceholder(
                    description=prompt[:100],
                    url=local_path,
                    prompt=enhanced_prompt,
                    resolution=size,
                    image_model=image_model,
                )
            else:
                logger.warning("⚠️ Failed to save image locally, using URL instead")
                return ImagePlaceholder(
                    description=prompt[:100],
                    url=image_url,
                    prompt=enhanced_prompt,
                    resolution=size,
                    image_model=image_model,
                )
        else:
            logger.error("❌ No image results returned")
            return None

    except Exception as e:
        logger.error(f"❌ Error generating image: {e}\n")
        return None


def generate_chapter_image(
    title: str,
    summary: str,
    size: str = "1328*1328",
    output_dir: str = "./books/images",
    chapter_name: str = "images",
    language: str = "English",
    country: str = "",
    audience_age: int = 10,
    use_qwen_text: bool = False,
    text_model: Optional[str] = None,
    image_model: str = "qwen-image-plus",
    art_style: str = "auto",
    negative_prompt_override: str | None = None,
) -> Optional[ImagePlaceholder]:
    """
    Generate a single chapter introduction image (synchronous call).

    1. Calls the text LLM to build a rich image prompt following the
       Advanced Prompt Formula (Entity + Environment + Style + Camera
       language + Atmosphere + Detail modifiers).  The LLM picks the
       shot size, perspective, lens type, style, lighting, and resolution
       automatically based on the subject matter.
    2. Sends the prompt to DashScope Qwen-Image with a negative prompt
       that bans all text/typography.
    3. Downloads and saves the image locally.

    Args:
        title: Chapter title
        summary: Chapter summary / description
        size: Default resolution — overridden by LLM choice
        output_dir: Parent directory to save images
        chapter_name: Subfolder name for this chapter's images
        language: Audience language (cultural context)
        country: Audience country (cultural context)
        audience_age: Target reader age
        use_qwen_text: Use Qwen text models for prompt generation
        text_model: Explicit text model id override
        image_model: Qwen image model id

    Returns:
        ImagePlaceholder with local file path and description, or None
    """
    if ImageSynthesis is None:
        print("⚠️  Warning: dashscope SDK not installed. Install with: pip install dashscope")
        return None

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        logger.warning("⚠️  Warning: DASHSCOPE_API_KEY environment variable not set")
        return None

    import dashscope
    dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'

    chapter_dir = Path(output_dir) / chapter_name
    chapter_dir.mkdir(parents=True, exist_ok=True)

    try:
        print(f"\n{'='*80}")
        print(f"🎨 Generating chapter image: {title}")
        print(f"{'='*80}")

        # ── Step 1: LLM-generated rich prompt + resolution ─────────
        raw_prompt, llm_resolution = _generate_llm_image_prompt(
            title=title,
            summary=summary,
            language=language,
            country=country,
            audience_age=audience_age,
            use_qwen=use_qwen_text,
            text_model=text_model,
            art_style=art_style,
        )
        enhanced_prompt = _ensure_no_text_instruction(raw_prompt)
        # Use LLM-chosen resolution (overrides the caller's default)
        size = llm_resolution

        print(f"  Resolution: {size} (chosen by AI)")
        print(f"  Full Prompt Preview: {enhanced_prompt[:200]}...")

        # Pick the right negative prompt
        neg_prompt = negative_prompt_override
        if neg_prompt is None and art_style == "low_budget":
            neg_prompt = _LOW_BUDGET_NEGATIVE_PROMPT

        # ── Step 2: DashScope image generation ───────────────────────
        response = _call_dashscope_api(api_key, image_model, enhanced_prompt, size,
                                       negative_prompt=neg_prompt)

        if response.output.results and len(response.output.results) > 0:
            image_url = response.output.results[0].url
            print(f"✅ Image generated successfully")

            local_path = _download_and_save_image(image_url, title, str(chapter_dir))

            if local_path:
                print(f"💾 Image saved: {local_path}\n")
                return ImagePlaceholder(
                    description=title,
                    url=local_path,
                    prompt=enhanced_prompt,
                    resolution=size,
                    image_model=image_model,
                )
            else:
                print("⚠️ Failed to save image locally, using URL instead")
                return ImagePlaceholder(
                    description=title,
                    url=image_url,
                    prompt=enhanced_prompt,
                    resolution=size,
                    image_model=image_model,
                )
        else:
            print("❌ No image results returned")
            return None

    except Exception as e:
        print(f"❌ Error generating image: {e}\n")
        return None


def _ensure_no_text_instruction(prompt: str) -> str:
    """Ensure the prompt contains aggressive no-text/no-letters/no-numbers instructions.

    The LLM prompt agent is instructed never to ask for text, but as a
    safety-net we prepend the ban if it isn't already present.  We also
    append a trailing reminder to reinforce the constraint.
    """
    NO_TEXT_PREFIX = (
        "ABSOLUTELY NO TEXT, NO LETTERS, NO NUMBERS, NO WORDS, NO WRITING, "
        "NO TYPOGRAPHY, NO LABELS, NO SIGNS, NO CAPTIONS IN THE IMAGE. "
        "The image must be purely visual with zero readable characters. "
    )
    NO_TEXT_SUFFIX = (
        " The image must contain NO text, NO letters, NO numbers, NO words, "
        "NO writing of any kind. Purely visual, zero readable characters."
    )
    marker = "NO TEXT"
    if marker.lower() not in prompt.lower():
        prompt = f"{NO_TEXT_PREFIX}{prompt}{NO_TEXT_SUFFIX}"
    else:
        # Even if it already has "NO TEXT", append the suffix reminder
        if "zero readable characters" not in prompt.lower():
            prompt = f"{prompt}{NO_TEXT_SUFFIX}"
    return prompt


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