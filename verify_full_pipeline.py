
import asyncio
import os
import sys
from unittest.mock import MagicMock
from datetime import datetime
from pathlib import Path

# Mock Streamlit BEFORE importing app.py components
sys.modules["streamlit"] = MagicMock()
st_mock = sys.modules["streamlit"]

# Flexible mock for columns that returns enough items
def columns_mock(spec):
    count = spec if isinstance(spec, int) else len(spec)
    return [MagicMock() for _ in range(count)]

st_mock.columns.side_effect = columns_mock
st_mock.empty.return_value = MagicMock()
st_mock.expander.return_value.__enter__ = MagicMock()
st_mock.expander.return_value.__exit__ = MagicMock()

# Smart mocks for inputs to pass Pydantic validation
st_mock.text_input.return_value = "La IA en México"
st_mock.checkbox.return_value = True

def selectbox_mock(label, options, *args, **kwargs):
    # Return appropriate strings based on label
    if "Country" in label: return "Mexico"
    if "Language" in label: return "Spanish"
    if "Method" in label: return "Project-Based"
    if "Region" in label: return "singapore"
    if "Model" in label: return options[0] # Default model
    if "Style" in label: return "3D"
    return options[0] if options else "Option"

st_mock.selectbox.side_effect = selectbox_mock

def slider_mock(label, *args, **kwargs):
    # Return valid integers for sliders
    if "Age" in label: return 12
    if "Chapters" in label: return 1
    if "Pages" in label: return 1
    if "Images" in label: return 1
    return 1

st_mock.slider.side_effect = slider_mock

# Now import app logic
from models.book_spec import BookRequest
from app import generate_book_async

async def verify_pipeline():
    print("🚀 Starting Full Generation Pipeline Verification...")
    
    # Create request
    request = BookRequest(
        topic="La IA en México",
        target_audience_age=12,
        language="Spanish",
        country="Mexico",
        learning_method="Project-Based",
        num_chapters=1,          # Minimal scope for testing
        pages_per_chapter=1,     # Minimal scope
    )

    # Use Qwen models (assuming user wants this path tested)
    # Ensure API key is present
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ DASHSCOPE_API_KEY is not set. Cannot test Qwen pipeline.")
        return
        
    print(f"🔑 API Key found: Length={len(api_key)}, Prefix={api_key[:4] if len(api_key)>4 else '***'}")

    try:
        curriculum, chapters = await generate_book_async(
            request=request,
            generate_images=True,
            image_style="3D",
            use_qwen_models=True,
            qwen_region="singapore",  # Standard defaults
            images_dir="./test_output/images",
            text_model="qwen-plus",
            image_model="qwen-image-plus",
            images_per_chapter=1,
            shot_size="Medium Shot",
            perspective="Eye Level",
            lens_type="Wide Angle",
            lighting="Cinematic"
        )

        if curriculum and chapters:
            print("\n✅ Pipeline SUCCESS!")
            print(f"  Curriculum: {curriculum.title}")
            print(f"  Chapters Generated: {len(chapters)}")
            print(f"  First Chapter Content Length: {len(chapters[0].markdown_content)}")
            if chapters[0].generated_images:
                print(f"  Image Generated: {chapters[0].generated_images[0].url}")
            else:
                print("  ⚠️ No images generated")
        else:
            print("\n❌ Pipeline FAILED: Returns were None")

    except Exception as e:
        print(f"\n❌ Pipeline CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_pipeline())
