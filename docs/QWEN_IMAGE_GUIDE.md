# Qwen Image Setup & Troubleshooting Guide

## Quick Start

### 1. Get API Key

1. Visit [Alibaba Cloud Model Studio](https://www.alibabacloud.com/help/en/model-studio/get-api-key)
2. Sign up or log in
3. Create new API key
4. Choose region:
   - **Singapore**: For international/low-latency access
   - **Beijing**: For China-based operations

⚠️ **Important**: API keys are region-specific. Don't mix them!

### 2. Configure Environment

Add to `.env`:
```bash
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxx
```

### 3. Install Dependencies

```bash
pip install dashscope
```

### 4. Test It

```python
from agents.qwen_image_agent import generate_image_with_qwen
import asyncio

async def test():
    image = await generate_image_with_qwen(
        prompt="A friendly robot teaching children mathematics",
        style="educational",
        size="1664*928"
    )
    if image:
        print(f"✅ Success: {image.url}")
    else:
        print("❌ Failed")

asyncio.run(test())
```

---

## API Features

### Image Sizes

| Size | Aspect Ratio | Best For |
|------|-------------|----------|
| `1664*928` | 16:9 | Book pages (default) |
| `1328*1328` | 1:1 | Square covers |
| `1472*1104` | 4:3 | Traditional format |
| `1104*1472` | 3:4 | Portrait/vertical |
| `928*1664` | 9:16 | Mobile/story format |

### Artistic Styles

**Educational**: Clear, engaging, child-friendly
```python
await generate_image_with_qwen(
    prompt="...",
    style="educational"  # Adds learning-focused guidance
)
```

**Story**: Warm, narrative-driven, expressive
```python
await generate_image_with_qwen(
    prompt="...",
    style="story"  # Makes it more whimsical
)
```

**Artistic**: High-quality, detailed, professional
```python
await generate_image_with_qwen(
    prompt="...",
    style="artistic"  # Emphasizes detail and quality
)
```

**Technical**: Clear diagrams, informative, organized
```python
await generate_image_with_qwen(
    prompt="...",
    style="technical"  # For instructional graphics
)
```

### Prompt Tips

**Good prompts** (what Qwen does best):
```python
# Complex text with images
"Educational poster with title 'Learn Math!' in blue bold font,
subtitle in green, and illustration of children solving problems."

# Specific styles
"Hand-drawn storybook illustration, warm colors, cheerful atmosphere"

# Detailed requirements
"Three puppies playing with a ball, green grass, birds flying above,
colorful decorative elements, children's book style"
```

**Bad prompts** (avoid):
```python
# Too vague
"Make a nice image"

# Contradictory
"Realistic AND cartoon style"

# Impossible
"Exact replica of copyrighted character"
```

### Negative Prompts

Use to exclude unwanted elements:

```python
await generate_image_with_qwen(
    prompt="Educational illustration for children",
    negative_prompt="scary, dark, violent, low quality, blurry"
)
```

### Reproducibility

Use `seed` parameter for consistent results:

```python
# Generate same image twice
await generate_image_with_qwen(
    prompt="Same prompt",
    seed=42  # Fixed seed
)

await generate_image_with_qwen(
    prompt="Same prompt",
    seed=42  # Same seed = similar result
)
```

---

## Performance & Pricing

### Timing
- Task creation: ~1 second
- Processing: ~15-30 seconds
- Image available for: 24 hours

### API Response Pattern

```python
# Step 1: Task created
task_id = "xyz"

# Step 2: Poll every 3-5 seconds
status = PENDING → RUNNING → SUCCEEDED

# Step 3: Download image
# ⚠️ URL expires in 24 hours!
```

### Cost Optimization

**Sequential Generation** (recommended for development):
```python
# Generate one at a time - cheaper, slower
images = await generate_multiple_images(
    prompts=[...],
    parallel=False  # 1 API call at a time
)
```

**Parallel Generation** (for production):
```python
# Generate all at once - faster, uses more quota
images = await generate_multiple_images(
    prompts=[...],
    parallel=True  # All at once
)
```

---

## Troubleshooting

### ❌ "DASHSCOPE_API_KEY not set"

**Solution**: Add to `.env`:
```bash
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxx
```

Then reload Python:
```bash
python your_script.py
```

### ❌ "Current user api does not support synchronous calls"

**Solution**: Using wrong model. Use:
- ✅ `qwen-image-plus`
- ✅ `qwen-image`
- ❌ `qwen-image-max` (async only - handled internally)

Current code handles this automatically.

### ❌ "Authentication failed / Invalid API key"

**Solution**:
1. Verify API key is correct
2. Check region matches (Singapore vs Beijing)
3. Try creating new key in Model Studio
4. Wait a few seconds for key activation

### ❌ "Task timeout / Polling exceeded"

**Solution**:
- Increase timeout: `await generate_image_with_qwen(..., timeout=120)`
- Check Alibaba Cloud status (may be temporarily slow)
- Simplify prompt to reduce processing time

### ❌ "Image URL expired"

**Solution**:
- Download immediately after generation
- Store image locally, not just the URL
- URLs are only valid for 24 hours

### ⚠️ "Prompt was modified / Different image than expected"

Because `prompt_extend=True` is enabled (default), Qwen may enhance your prompt.

To disable:
```python
# In qwen_image_agent.py, change:
prompt_extend=False  # Disable enhancement
```

---

## Integration Examples

### In Main Workflow

```python
from agents.qwen_image_agent import generate_image_with_qwen

# After generating chapter content with image placeholders
for placeholder_text in chapter.image_placeholders:
    image = await generate_image_with_qwen(
        prompt=placeholder_text,
        style="educational",
        size="1664*928"
    )
    if image:
        chapter.images.append(image)
```

### In Streamlit App

```python
import streamlit as st
from agents.qwen_image_agent import generate_image_with_qwen

if st.button("🎨 Generate Illustrations"):
    for prompt in image_prompts:
        image = await generate_image_with_qwen(prompt)
        st.image(image.url)
        
        # Download immediately
        response = requests.get(image.url)
        with open(f"image_{i}.png", "wb") as f:
            f.write(response.content)
```

### Batch Generation

```python
import asyncio
from agents.qwen_image_agent import generate_multiple_images

# Generate 10 images for book chapters
images = await generate_multiple_images(
    prompts=[
        "Title page illustration",
        "Chapter 1 intro image",
        # ... more prompts
    ],
    style="story",
    parallel=False  # Sequential (cheaper)
)

# Save all images
import requests
for i, img in enumerate(images):
    if img:
        response = requests.get(img.url)
        with open(f"chapter_{i}.png", "wb") as f:
            f.write(response.content)
```

---

## Real-World Example

### Generate Book Chapter Illustrations

```python
async def create_chapter_with_images(chapter_outline, age, learning_method):
    # 1. Generate chapter content
    chapter = await generate_chapter(...)
    
    # 2. Extract image prompts
    image_prompts = chapter.image_placeholders
    
    # 3. Generate illustrations
    print("🎨 Creating illustrations...")
    for prompt in image_prompts[:3]:  # Max 3 images per chapter
        img = await generate_image_with_qwen(
            prompt=prompt,
            style="educational",
            size="1664*928"
        )
        
        if img:
            # 4. Save image locally
            import requests
            response = requests.get(img.url)
            filename = f"ch_{chapter.id}_img_{len(chapter.images)}.png"
            with open(filename, "wb") as f:
                f.write(response.content)
            
            chapter.images.append({
                "description": prompt,
                "local_path": filename,
                "url": img.url
            })
    
    return chapter
```

---

## Performance Metrics

### Expected Generation Time

```
Prompt submission:    ~1-2 seconds
Queue wait:          ~5-10 seconds (varies)
Processing:          ~10-20 seconds
Download:            ~2-5 seconds (depends on connection)
TOTAL:               ~20-35 seconds per image
```

### Batch Processing

```
1 image:   ~30 seconds
3 images: ~100-110 seconds (sequential)
10 images: ~300-350 seconds (sequential)

Parallel:
10 images: ~50-60 seconds (all at same time)
```

---

## References

- [Qwen Image Official Docs](https://www.alibabacloud.com/help/en/model-studio/qwen-image)
- [DashScope SDK](https://dashscope-doc.oss-cn-hangzhou.aliyuncs.com/python/latest/index.html)
- [Model Studio API Keys](https://www.alibabacloud.com/help/en/model-studio/get-api-key)
- [API Region Info](https://www.alibabacloud.com/help/en/model-studio/endpoints-overview)
