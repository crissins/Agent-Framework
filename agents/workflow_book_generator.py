

from agent_framework.observability import setup_observability

# workflow_book_generator.py
import asyncio
import os
from datetime import datetime
from typing import List, Dict, Any
from agent_framework import WorkflowBuilder, WorkflowContext, WorkflowOutputEvent, executor, WorkflowViz
from typing_extensions import Never

# Import agents
from agents.greet_agent import create_greet_agent, get_book_request
from agents.curriculum_agent import create_curriculum_agent, generate_curriculum
from agents.chapter_agent import create_chapter_agent, generate_chapter
from agents.html_css_agent import generate_html_book_from_data
from agents.markdown_agent import save_markdown_book

# Models
from models.book_spec import BookRequest, Curriculum, ChapterContent

# === Step 1: Executors ===

@executor(id="greet_executor")
async def greet_step(_: str, ctx: WorkflowContext[BookRequest]) -> None:
    agent = await create_greet_agent()
    request = await get_book_request(agent)
    await ctx.send_message(request)

@executor(id="curriculum_executor")
async def curriculum_step(request: BookRequest, ctx: WorkflowContext[tuple[BookRequest, Curriculum]]) -> None:
    agent = await create_curriculum_agent()
    curriculum = await generate_curriculum(agent, request)
    await ctx.send_message((request, curriculum))

@executor(id="chapter_executor")
async def chapter_step(data: tuple[BookRequest, Curriculum], ctx: WorkflowContext[BookOutput]) -> None:
    request, curriculum = data
    agent = await create_chapter_agent()
    chapters = []
    for outline in curriculum.chapters:
        chapter = await generate_chapter(agent, outline, {
            "age": request.target_audience_age,
            "country": request.country,
            "learning_method": request.learning_method,
            "language": request.language,
            "pages_per_chapter": request.pages_per_chapter
        })
        chapters.append(chapter)
    output = BookOutput(book_request=request, curriculum=curriculum, chapters=chapters)
    await ctx.send_message(output)

@executor(id="html_export_executor")
async def html_export_step(output: BookOutput, ctx: WorkflowContext[Never, str]) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"book_{timestamp}.html"
    generate_html_book(output, path)
    await ctx.yield_output(path)

@executor(id="markdown_export_executor")
async def markdown_export_step(output: BookOutput, ctx: WorkflowContext[Never, str]) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"book_{timestamp}.md"
    save_markdown_book(output, path)
    await ctx.yield_output(path)
# === Step 2: Build Workflow ===

async def main():
    workflow = (
        WorkflowBuilder()
        .add_edge(greet_step, curriculum_step)
        .add_edge(curriculum_step, chapter_step)
        .add_edge(chapter_step, html_export_executor)
        .add_edge(chapter_step, markdown_export_executor)
        .set_start_executor(greet_step)
        .build()
    )

    async for event in workflow.run_stream("start"):
        if isinstance(event, WorkflowOutputEvent):
            print(f"✅ Output: {event.data}")

    # === Generate and save workflow visualization ===
    viz = WorkflowViz(workflow)
    
    # Save Mermaid (for docs/Markdown)
    with open("workflow.mmd", "w") as f:
        f.write(viz.to_mermaid())
    
    # Save DOT (for Graphviz)
    with open("workflow.dot", "w") as f:
        f.write(viz.to_digraph())
    
    # Export SVG (requires Graphviz)
    try:
        svg_path = viz.export(format="svg", filename="workflow_diagram.svg")
        print(f"✅ Workflow diagram saved: {svg_path}")
    except Exception as e:
        print(f"⚠️  SVG export failed (install Graphviz): {e}")

    print("🚀 Starting LATAM Book Generation Workflow...\n")
    async for event in workflow.run_stream("start"):
        if isinstance(event, WorkflowOutputEvent):
            print(f"✅ Output saved: {event.data}")

if __name__ == "__main__":
    asyncio.run(main())