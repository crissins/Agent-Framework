# app.py
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
from agents.pdf_generator import generate_pdf_book

load_dotenv()

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
    else:
        qwen_region = "singapore"

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
        image_style = st.selectbox(
            "🖼️ Illustration Style",
            ["educational", "story", "artistic"],
            help="Educational: Clear & learning-focused | Story: Warm & narrative | Artistic: High-quality & detailed"
        )
    else:
        image_style = "educational"

async def generate_book_async(
    request: BookRequest,
    generate_images: bool,
    image_style: str,
    use_qwen_models: bool = False,
    qwen_region: str = "singapore",
    images_dir: str = "./chapter_images"
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
    
    Best practices:
    - Clean error handling
    - Typed return values
    - Proper resource cleanup
    - Flexible model provider selection
    """
    use_qwen = use_qwen_models
    
    try:
        # Step 2: Generate curriculum
        curriculum_agent = await create_curriculum_agent(use_qwen=use_qwen_models)
        curriculum = await generate_curriculum(curriculum_agent, request)
        
        if not curriculum:
            raise ValueError("Failed to generate curriculum")

        # Step 3: Generate all chapters
        chapter_agent = await create_chapter_agent()
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
                # Generate one image per chapter as introduction
                if generate_images:
                    progress_placeholder.info(
                        f"📝 Chapter {i+1}/{len(curriculum.chapters)} - 🎨 Generating introduction image..."
                    )
                    img = generate_chapter_image(
                        title=chapter.chapter_title,
                        summary=outline.summary,
                        style=image_style,
                        output_dir=images_dir,
                        language=request.language
                    )
                    if img:
                        # Embed image at the beginning of chapter markdown
                        chapter.markdown_content = f"![{chapter.chapter_title}]({img.url})\n\n{chapter.markdown_content}"
                        chapter.generated_images = [img]
                        print(f"✅ Image embedded in chapter: {chapter.chapter_title}")
                    else:
                        print(f"⚠️ Failed to generate image for chapter: {chapter.chapter_title}")
                
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
        
        # Create images directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        images_dir = f"chapter_images_{timestamp}"
        
        curriculum, full_chapters = asyncio.run(
            generate_book_async(request, generate_images, image_style, use_qwen_models, qwen_region, images_dir)
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

            # Generate PDF
            pdf_path = pdf_dir / f"libro_interactivo.pdf"
            pdf_success = generate_pdf_book(request, curriculum, full_chapters, str(pdf_path))
            if pdf_success:
                print(f"✅ PDF saved: {pdf_path}")
                st.info(f"📄 PDF generated: {pdf_path}")
            else:
                st.warning("⚠️ PDF generation failed - try installing fpdf2")
                print(f"❌ PDF generation failed")

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