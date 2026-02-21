#!/usr/bin/env python3
"""
Streamlit application for LATAM book generation.
Integrates Microsoft Agent Framework with best practices:
- Proper error handling and user feedback
- Structured logging
- Clean separation of concerns
- Qwen-Image-Max for AI-powered illustrations
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from models.book_spec import BookRequest, Curriculum, ChapterContent, BookOutput
from config import validate_api_keys

# Import agents
from agents.curriculum_agent import create_curriculum_agent, generate_curriculum
from agents.chapter_agent import create_chapter_agent, generate_chapter
from agents.qwen_image_agent import generate_chapter_image
from agents.html_css_agent import generate_html_css_book_from_json
from agents.markdown_agent import save_markdown_book

# Load environment variables
load_dotenv()

# Configure OpenTelemetry tracing for AI Toolkit integration
try:
    from agent_framework.observability import configure_otel_providers
    configure_otel_providers(
        vs_code_extension_port=4317,  # AI Toolkit gRPC port
        enable_sensitive_data=True     # Capture prompts and completions for debugging
    )
except ImportError:
    print("Warning: agent_framework not found. Tracing will be disabled.", file=sys.stderr)

st.set_page_config(page_title="📚 LATAM Book Generator", layout="wide")
st.title("📚 LATAM Book Generator with AI Illustrations")

# === Initialize session state ===
if "book_generated" not in st.session_state:
    st.session_state.book_generated = False
    st.session_state.json_path = None
    st.session_state.html_path = None
    st.session_state.md_path = None
    st.session_state.pdf_path = None
    st.session_state.output_data = None
    st.session_state.curriculum = None
    st.session_state.full_chapters = None


# === UI Controls ===
col1, col2, col3 = st.columns(3)
with col1:
    topic = st.text_input("📚 Topic", value="La IA en México 2025")
with col2:
    country = st.selectbox("🌎 Country", ["Mexico", "Colombia", "Argentina", "Chile", "Peru", "Brazil", "Other"])
with col3:
    language = st.selectbox("🗣️ Language", ["Spanish", "Portuguese", "English"])

col4, col5, col6 = st.columns(3)
with col4:
    target_audience_age = st.slider("👧 Age", 8, 16, 8)
with col5:
    learning_method = st.selectbox("🧠 Learning Method", ["Scandinavian", "Montessori", "Project-Based"])
with col6:
    num_chapters = st.slider("📖 Chapters", 2, 12, 2)
    pages_per_chapter = st.slider("📄 Pages/Chapter", 1, 20, 1)

# === Model and Generation Settings ===
st.divider()
st.subheader("⚙️ Model & Generation Settings")

col_model1, col_model2 = st.columns(2)
with col_model1:
    use_qwen_models = st.checkbox(
        "🔄 Use Qwen Models (via DashScope)",
        value=False,
        help="Toggle between GitHub Models (free/dev) and Qwen (production-ready)"
    )
    
with col_model2:
    if use_qwen_models:
        qwen_region = st.selectbox(
            "🌍 Qwen Region",
            ["singapore", "beijing", "us-virginia"],
            help="Select the DashScope region (API keys differ by region)"
        )
        # Allow explicit selection of Qwen text and image models
        qwen_text_model = st.selectbox(
            "🧠 Qwen Text Model",
            ["qwen-plus", "qwen-max", "qwen-flash", "qwen3-max"],
            index=0,
            help="Select the Qwen model to use for text/LLM generation"
        )
        qwen_image_model = st.selectbox(
            "🖼️ Qwen Image Model",
            ["qwen-image-plus", "qwen-image-max-2025-12-30", "qwen-image-max", "qwen-image"],
            index=0,
            help="Select the Qwen model to use for image generation"
        )
    else:
        qwen_region = "singapore"
        qwen_text_model = None
        qwen_image_model = None

# Validate API keys
is_valid, message = validate_api_keys(use_qwen_models)
if is_valid:
    st.success(message)
else:
    st.error(message)
    st.info("📚 **Quick setup:** Copy `.env.example` to `.env` and add your API keys")

# === Image generation settings ===
col_img1, col_img2 = st.columns(2)
with col_img1:
    generate_images = st.checkbox("🎨 Generate AI Illustrations (Qwen-Image-Max)", value=True)
with col_img2:
    if generate_images:
        # Advanced Image Settings Expander
        with st.expander("🎨 Advanced Image Settings", expanded=True):
            col_style1, col_style2 = st.columns(2)
            with col_style1:
                image_style = st.selectbox(
                    "🖼️ Illustration Style",
                    [
                        "educational", "story", "artistic", "3D", "watercolor", 
                        "surrealism", "realistic", "3D cartoon", "ink painting", 
                        "post-apocalyptic", "pointillism", "clay", "ceramic", 
                        "origami", "gongbi", "chinese ink"
                    ],
                    index=0,
                    help="Select the artistic style for the illustrations"
                )
            with col_style2:
                images_per_chapter = st.slider("🖼️ Images / Chapter", 1, 5, 1)
            
            st.caption("📸 Camera & Lighting (Optional)")
            col_cam1, col_cam2, col_cam3, col_cam4 = st.columns(4)
            with col_cam1:
                shot_size = st.selectbox("📏 Shot Size", ["", "Long Shot", "Medium Shot", "Close Up", "Extreme Close Up"], index=0)
            with col_cam2:
                perspective = st.selectbox("👁️ Perspective", ["", "Eye Level", "Low Angle", "High Angle", "Bird's Eye View", "Worm's Eye View"], index=0)
            with col_cam3:
                lens_type = st.selectbox("🔍 Lens", ["", "Wide Angle", "Telephoto", "Macro", "Fisheye"], index=0)
            with col_cam4:
                lighting = st.selectbox("💡 Lighting", ["", "Natural", "Cinematic", "Studio", "Golden Hour", "Blue Hour", "Dramatic", "Soft"], index=0)
    else:
        image_style = "educational"
        images_per_chapter = 0
        shot_size = ""
        perspective = ""
        lens_type = ""
        lighting = ""

async def generate_book_async(
    request: BookRequest,
    generate_images: bool,
    image_style: str,
    use_qwen_models: bool = False,
    qwen_region: str = "singapore",
    images_dir: str = "./books/images",
    text_model: str | None = None,
    image_model: str | None = None,
    images_per_chapter: int = 1,
    shot_size: str = "",
    perspective: str = "",
    lens_type: str = "",
    lighting: str = ""
) -> tuple:
    """
    Async book generation orchestration with optional image generation.
    
    Args:
        request: BookRequest configuration
        generate_images: Whether to generate illustrations
        image_style: Style for illustrations ('educational', 'story', 'artistic')
        use_qwen_models: If True, use Qwen models; if False, use GitHub Models
        qwen_region: Region for Qwen models ('singapore', 'beijing', 'us-virginia')
        images_dir: Directory to save generated images
        shot_size: Camera shot size
        perspective: Camera perspective
        lens_type: Camera lens type
        lighting: Scene lighting
    
    Best practices:
    - Clean error handling
    - Typed return values
    - Proper resource cleanup
    - Flexible model provider selection
    """
    use_qwen = use_qwen_models
    
    try:
        # Step 2: Generate curriculum (use selected text model when provided)
        curriculum_agent = await create_curriculum_agent(use_qwen=use_qwen_models, model_id=text_model)
        curriculum = await generate_curriculum(curriculum_agent, request)
        
        if not curriculum:
            raise ValueError("Failed to generate curriculum")

        # Step 3: Generate all chapters (use selected text model when provided)
        chapter_agent = await create_chapter_agent(use_qwen=use_qwen_models, model_id=text_model)
        context = {
            "age": request.target_audience_age,
            "country": request.country,
            "learning_method": request.learning_method,
            "language": request.language,
            "pages_per_chapter": request.pages_per_chapter
        }

        full_chapters = []
        progress_placeholder = st.empty()
        
        for i, outline in enumerate(curriculum.chapters):
            progress_placeholder.info(f"📝 Generating Chapter {i+1}/{len(curriculum.chapters)}...")
            chapter = await generate_chapter(chapter_agent, outline, context)
            
            if chapter:
                # Generate N images per chapter as introduction
                if generate_images and images_per_chapter and images_per_chapter > 0:
                    progress_placeholder.info(
                        f"📝 Chapter {i+1}/{len(curriculum.chapters)} - 🎨 Generating introduction image..."
                    )
                    # Create clean chapter folder name
                    chapter_folder = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in chapter.chapter_title)
                    chapter_folder = chapter_folder.replace(' ', '_')[:50]
                    chapter.generated_images = []
                    image_markdown_lines = []
                    for idx in range(images_per_chapter):
                        # Ensure unique title per image to avoid filename collisions
                        img_title = f"{chapter.chapter_title} - {idx+1}"
                        img = generate_chapter_image(
                            title=img_title,
                            summary=outline.summary,
                            style=image_style,
                            output_dir=images_dir,
                            chapter_name=chapter_folder,
                            language=request.language,
                            image_model=image_model,
                            shot_size=shot_size,
                            perspective=perspective,
                            lens_type=lens_type,
                            lighting=lighting
                        )
                        if img:
                            image_markdown_lines.append(f"![{chapter.chapter_title} - {idx+1}]({img.url})")
                            chapter.generated_images.append(img)
                            print(f"✅ Image {idx+1} embedded in chapter: {chapter.chapter_title}")
                        else:
                            print(f"⚠️ Failed to generate image {idx+1} for chapter: {chapter.chapter_title}")

                    if image_markdown_lines:
                        imgs_md = "\n\n".join(image_markdown_lines) + "\n\n"
                        chapter.markdown_content = f"{imgs_md}{chapter.markdown_content}"
                
                full_chapters.append(chapter)
            else:
                st.warning(f"⚠️ Failed to generate chapter: {outline.title}")

        progress_placeholder.empty()
        
        if not full_chapters:
            raise ValueError("No chapters were successfully generated")

        return curriculum, full_chapters
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error during generation: {str(e)}"
        print(f"\n{'='*60}")
        print(f"ERROR: {error_msg}")
        print(f"Traceback:\n{traceback.format_exc()}")
        print(f"{'='*60}\n")
        st.error(error_msg)
        return None, None


if st.button("🚀 Generate Full Book"):
    # Create book request
    request = BookRequest(
        topic=topic,
        target_audience_age=target_audience_age,
        language=language,
        country=country,
        learning_method=learning_method,
        num_chapters=num_chapters,
        pages_per_chapter=pages_per_chapter
    )

    # Generate book asynchronously
    try:
        print(f"\n{'='*60}")
        print(f"📚 Starting book generation...")
        print(f"  Topic: {topic}")
        print(f"  Chapters: {num_chapters}")
        print(f"  Country: {country}")
        print(f"  Language: {language}")
        print(f"{'='*60}\n")
        
        # Create images directory inside books/images/{timestamp}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_books_dir = Path("books")
        images_dir_path = base_books_dir / "images" / timestamp
        images_dir_path.mkdir(parents=True, exist_ok=True)

        curriculum, full_chapters = asyncio.run(
            generate_book_async(
                request,
                generate_images,
                image_style,
                use_qwen_models,
                qwen_region,
                str(images_dir_path),
                text_model=qwen_text_model,
                image_model=qwen_image_model,
                images_per_chapter=images_per_chapter,
                shot_size=shot_size,
                perspective=perspective,
                lens_type=lens_type,
                lighting=lighting
            )
        )
        
        if not curriculum or not full_chapters:
            print("\n❌ Book generation failed - curriculum or chapters is None\n")
            st.error("Book generation failed. Please try again.")
        else:
            # Step 4: Create output folder structure: books/{json,html,md,pdf}/{timestamp}
            output_data = {
                "book_request": request.model_dump(),
                "curriculum": curriculum.model_dump(),
                "chapters": [c.model_dump() for c in full_chapters]
            }
            
            # Create directory structure
            base_books_dir = Path("books")
            json_dir = base_books_dir / "json" / timestamp
            html_dir = base_books_dir / "html" / timestamp
            md_dir = base_books_dir / "md" / timestamp
            pdf_dir = base_books_dir / "pdf" / timestamp
            
            # Create all directories
            json_dir.mkdir(parents=True, exist_ok=True)
            html_dir.mkdir(parents=True, exist_ok=True)
            md_dir.mkdir(parents=True, exist_ok=True)
            pdf_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"\n📁 Folder structure created:")
            print(f"   {json_dir}/")
            print(f"   {html_dir}/")
            print(f"   {md_dir}/")
            print(f"   {pdf_dir}/")
            
            # Save JSON
            json_path = json_dir / f"book_output.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"✅ JSON saved: {json_path}")

            # Generate HTML
            html_path = html_dir / f"libro_interactivo.html"
            generate_html_css_book_from_json(request, curriculum, full_chapters, str(html_path))
            print(f"✅ HTML saved: {html_path}")

            # Generate Markdown
            md_path = md_dir / f"libro_interactivo.md"
            book_output = BookOutput(
                book_request=request,
                curriculum=curriculum,
                chapters=full_chapters
            )
            save_markdown_book(book_output, str(md_path))
            print(f"✅ Markdown saved: {md_path}")

            # Generate PDF from HTML (optional - shows alternatives if unavailable)
            pdf_path = pdf_dir / f"libro_interactivo.pdf"
            try:
                # Lazy import to avoid loading weasyprint at module level
                from agents.html_to_pdf_converter import convert_html_to_pdf
                
                pdf_success = convert_html_to_pdf(str(html_path), str(pdf_path))
                if pdf_success:
                    print(f"✅ PDF saved: {pdf_path}")
                    st.success(f"📄 PDF generated successfully!")
                else:
                    print(f"⚠️ PDF generation skipped - HTML available")
                    st.info(f"📱 PDF not available, but HTML is ready to open or print to PDF from browser")
            except Exception as e:
                print(f"⚠️  Error converting HTML to PDF: {e}")
                pdf_success = False

            # Save to session state
            st.session_state.book_generated = True
            st.session_state.json_path = str(json_path)
            st.session_state.html_path = str(html_path)
            st.session_state.md_path = str(md_path)
            st.session_state.pdf_path = str(pdf_path)
            st.session_state.output_data = output_data
            st.session_state.curriculum = curriculum
            st.session_state.full_chapters = full_chapters
            
            print(f"\n✅ Book generated successfully in organized folders!\n")
            st.success("✅ Book generated successfully!")
            
    except Exception as e:
        import traceback
        error_msg = f"❌ Unexpected error: {str(e)}"
        print(f"\n{'='*60}")
        print(f"ERROR: {error_msg}")
        print(f"Traceback:\n{traceback.format_exc()}")
        print(f"{'='*60}\n")
        st.error(error_msg)


# === Display output if generated ===
if st.session_state.book_generated and st.session_state.curriculum:
    st.divider()
    st.subheader("📘 Curriculum")
    st.json(st.session_state.curriculum.model_dump())

    st.subheader("📖 Full Chapters (Preview)")
    for i, ch in enumerate(st.session_state.full_chapters):
        with st.expander(f"Capítulo {i+1}: {ch.chapter_title}"):
            st.markdown(ch.markdown_content)
            
            # Display generated images if available
            if hasattr(ch, 'generated_images') and ch.generated_images:
                st.markdown("**Illustrations:**")
                for j, img in enumerate(ch.generated_images, 1):
                    st.markdown(f"*{img.description}*")
                    st.image(img.url, use_column_width=True)

    # === Download Buttons ===
    st.divider()
    st.subheader("📥 Download Your Book")
    colA, colB, colC, colD = st.columns(4)
    
    with colA:
        with open(st.session_state.json_path, "rb") as f:
            st.download_button(
                label="📊 JSON (Data)",
                data=f,
                file_name="book_output.json",
                mime="application/json"
            )
    
    with colB:
        with open(st.session_state.html_path, "rb") as f:
            st.download_button(
                label="🌐 HTML (Interactive)",
                data=f,
                file_name="libro_interactivo.html",
                mime="text/html"
            )
    
    with colC:
        with open(st.session_state.md_path, "rb") as f:
            st.download_button(
                label="📝 Markdown",
                data=f,
                file_name="libro_interactivo.md",
                mime="text/markdown"
            )
    
    with colD:
        if st.session_state.pdf_path and os.path.exists(st.session_state.pdf_path):
            with open(st.session_state.pdf_path, "rb") as f:
                st.download_button(
                    label="📄 PDF (Print)",
                    data=f,
                    file_name="libro_interactivo.pdf",
                    mime="application/pdf"
                )