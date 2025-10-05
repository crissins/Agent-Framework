# workflow_book_generator.py
import asyncio
import os
from typing import List
from agent_framework import WorkflowBuilder, WorkflowContext, WorkflowOutputEvent, executor
from typing_extensions import Never

# Import agents
from agents.greet_agent import create_greet_agent, get_book_request
from agents.curriculum_agent import create_curriculum_agent, generate_curriculum
from agents.chapter_agent import create_chapter_agent, generate_chapter
from agents.image_search_agent import image_search_tool
from agents.video_search_agent import video_search_tool

# Import models
from models.book_spec import BookRequest, Curriculum, ChapterContent

# Import HTML agent
from agents.html_agent import generate_html_book


@executor(id="greet_executor")
async def greet_step(_: str, ctx: WorkflowContext[BookRequest]) -> None:
    agent = await create_greet_agent()
    request = await get_book_request(agent)
    await ctx.send_message(request)


@executor(id="curriculum_executor")
async def curriculum_step(request: BookRequest, ctx: WorkflowContext[Curriculum]) -> None:
    agent = await create_curriculum_agent()
    curriculum = await generate_curriculum(agent, request)
    await ctx.send_message(curriculum)


@executor(id="chapter_executor")
async def chapter_step(curriculum: Curriculum, ctx: WorkflowContext[Never, List[ChapterContent]]) -> None:
    agent = await create_chapter_agent()
    context = {
        "age": curriculum.chapters[0].estimated_pages,
        "country": "Mexico",
        "learning_method": "Scandinavian",
        "language": "Spanish"
    }

    chapters: List[ChapterContent] = []
    for i, outline in enumerate(curriculum.chapters):
        print(f"📝 Generating chapter {i+1}/{len(curriculum.chapters)}: {outline.title}")
        chapter = await generate_chapter(agent, outline, context)
        chapters.append(chapter)

    await ctx.yield_output(chapters)


@executor(id="html_export_executor")
async def html_export_step(chapters: List[ChapterContent], ctx: WorkflowContext[Never, str]) -> None:
    html_content = await generate_html_book(chapters)
    await ctx.yield_output(html_content)


async def main():
    workflow = (
        WorkflowBuilder()
        .add_edge(greet_step, curriculum_step)
        .add_edge(curriculum_step, chapter_step)
        .add_edge(chapter_step, html_export_step)
        .set_start_executor(greet_step)
        .build()
    )

    print("🚀 Starting LATAM Book Generation Workflow...\n")

    async for event in workflow.run_stream("start"):
        if isinstance(event, WorkflowOutputEvent):
            if isinstance(event.data, str) and event.data.startswith("<!DOCTYPE html>"):
                # Save HTML output
                with open("libro_interactivo.html", "w", encoding="utf-8") as f:
                    f.write(event.data)
                print("\n✅ Book saved as 'libro_interactivo.html'")
            else:
                print(f"✅ Workflow output: {type(event.data)}")

if __name__ == "__main__":
    asyncio.run(main())