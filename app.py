# app.py
import asyncio
import json
import os
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from models.book_spec import BookRequest, Curriculum, ChapterContent

# Import agents
from agents.greet_agent import create_greet_agent, get_book_request
from agents.curriculum_agent import create_curriculum_agent, generate_curriculum
from agents.chapter_agent import create_chapter_agent, generate_chapter
from agents.html_agent import generate_html_book

load_dotenv()

st.set_page_config(page_title="📚 LATAM Book Generator", layout="wide")
st.title("📚 LATAM Book Generator (Dev UI Proxy)")

# === Initialize session state ===
if "book_generated" not in st.session_state:
    st.session_state.book_generated = False
    st.session_state.json_path = None
    st.session_state.html_path = None
    st.session_state.output_data = None

# === UI Controls ===
col1, col2, col3 = st.columns(3)
with col1:
    topic = st.text_input("📚 Topic", value="La IA en mexico 2025")
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

if st.button("🚀 Generate Full Book"):
    # === Step 1: Book Request ===
    request = BookRequest(
        topic=topic,
        target_audience_age=target_audience_age,
        language=language,
        country=country,
        learning_method=learning_method,
        num_chapters=num_chapters,
        pages_per_chapter=pages_per_chapter
    )

    # === Step 2: Curriculum ===
    curriculum_agent = asyncio.run(create_curriculum_agent())
    curriculum = asyncio.run(generate_curriculum(curriculum_agent, request))

    # === Step 3: Generate ALL Chapters ===
    chapter_agent = asyncio.run(create_chapter_agent())
    context = {
        "age": request.target_audience_age,
        "country": request.country,
        "learning_method": request.learning_method,
        "language": request.language,
        "pages_per_chapter": request.pages_per_chapter
    }

    full_chapters = []
    for i, outline in enumerate(curriculum.chapters):
        with st.spinner(f"📝 Generating Chapter {i+1}/{len(curriculum.chapters)}..."):
            chapter = asyncio.run(generate_chapter(chapter_agent, outline, context))
            full_chapters.append(chapter)

    # === Step 4: Save JSON ===
    output_data = {
        "book_request": request.model_dump(),
        "curriculum": curriculum.model_dump(),
        "chapters": [c.model_dump() for c in full_chapters]
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = f"book_output_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # === Step 5: Generate HTML ===
    html_content = asyncio.run(generate_html_book(full_chapters))
    html_path = f"libro_interactivo_{timestamp}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # === Save to session state ===
    st.session_state.book_generated = True
    st.session_state.json_path = json_path
    st.session_state.html_path = html_path
    st.session_state.output_data = output_data
    st.session_state.curriculum = curriculum
    st.session_state.full_chapters = full_chapters

# === Display output if generated ===
if st.session_state.book_generated:
    st.success("✅ Book generated successfully!")

    st.subheader("📘 Curriculum")
    st.json(st.session_state.curriculum.model_dump())

    st.subheader("📖 Full Chapters (Preview)")
    for i, ch in enumerate(st.session_state.full_chapters):
        with st.expander(f"Capítulo {i+1}: {ch.chapter_title}"):
            st.markdown(ch.markdown_content)
            if ch.videos:
                st.video(ch.videos[0].url)
                st.image(f"{ch.videos[0].qr_code}", width=120, caption="Scan to watch")

    # === Download Buttons (always visible after generation) ===
    colA, colB = st.columns(2)
    with colA:
        with open(st.session_state.json_path, "rb") as f:
            st.download_button("📥 Download JSON", f, file_name=st.session_state.json_path, mime="application/json")
    with colB:
        with open(st.session_state.html_path, "rb") as f:
            st.download_button("🌐 Download HTML Book", f, file_name=st.session_state.html_path, mime="text/html")