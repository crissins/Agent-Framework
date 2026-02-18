"""
Enhanced Book Generator Workflow with Fact-Checking Integration
Combines the book generation pipeline with real-time fact verification using web search.
"""
import asyncio
from typing import Optional, List
from agents.workflow_book_generator import (
    create_book_chapter_agent,
    generate_chapter,
    save_chapter_to_file
)
from agents.fact_check_agent import create_fact_check_agent, verify_chapter_accuracy
import json
from datetime import datetime


async def generate_and_fact_check_book(
    book_title: str,
    age_group: str,
    chapters: List[dict],
    topics: List[str],
    output_dir: str = "output_books",
    enable_fact_checking: bool = True
) -> dict:
    """
    Generate an educational book with automatic fact-checking using web search.
    
    Args:
        book_title: Title of the book
        age_group: Target age group (e.g., "8-10 years")
        chapters: List of chapter specifications with 'title' and 'content_description'
        topics: List of educational topics
        output_dir: Directory to save outputs
        enable_fact_checking: Whether to enable web search fact-checking
        
    Returns:
        Dictionary with generation results and fact-check reports
        
    Prompt Engineering Best Practices Applied:
    1. Clear role definition for both agents
    2. Structured output formats
    3. Explicit constraints and requirements
    4. Contextual information for better results
    5. Step-by-step instructions
    """
    
    results = {
        "book_title": book_title,
        "age_group": age_group,
        "generation_date": datetime.now().isoformat(),
        "chapters_generated": [],
        "fact_checks": [],
        "summary_report": {}
    }
    
    try:
        # Initialize agents
        print(f"\n📚 Initializing Book Generation Workflow...")
        print(f"📖 Book: {book_title}")
        print(f"👥 Age Group: {age_group}")
        
        book_agent = await create_book_chapter_agent()
        print("✅ Book generation agent initialized")
        
        fact_check_agent = None
        if enable_fact_checking:
            try:
                fact_check_agent = await create_fact_check_agent(use_qwen=True)
                print("✅ Fact-check agent initialized with web search")
            except Exception as e:
                print(f"⚠️  Fact-checking unavailable: {e}")
                print("   Continuing with book generation only...")
                enable_fact_checking = False
        
        # Generate chapters
        print(f"\n📝 Generating {len(chapters)} chapters...")
        for i, chapter_spec in enumerate(chapters, 1):
            print(f"\n[{i}/{len(chapters)}] Generating: {chapter_spec['title']}")
            
            # Generate chapter
            chapter_content = await generate_chapter(
                agent=book_agent,
                chapter_title=chapter_spec['title'],
                age_group=age_group,
                description=chapter_spec.get('content_description', ''),
                previous_chapters=results["chapters_generated"]
            )
            
            if chapter_content:
                chapter_data = {
                    "chapter_number": i,
                    "title": chapter_spec['title'],
                    "content": chapter_content,
                    "content_length": len(chapter_content),
                    "generation_status": "success"
                }
                results["chapters_generated"].append(chapter_data)
                
                # Fact-check if enabled
                if enable_fact_checking and fact_check_agent:
                    print(f"   🔍 Fact-checking chapter with web search...")
                    fact_check_result = await verify_chapter_accuracy(
                        agent=fact_check_agent,
                        chapter_title=chapter_spec['title'],
                        chapter_content=chapter_content,
                        age_group=age_group
                    )
                    
                    if fact_check_result:
                        results["fact_checks"].append(fact_check_result)
                        print(f"   ✅ Fact-check completed")
                    
                    # Small delay between chapters
                    await asyncio.sleep(2)
            else:
                print(f"   ❌ Failed to generate chapter")
                chapter_data = {
                    "chapter_number": i,
                    "title": chapter_spec['title'],
                    "generation_status": "failed"
                }
                results["chapters_generated"].append(chapter_data)
        
        # Generate summary report
        results["summary_report"] = {
            "total_chapters": len(chapters),
            "chapters_successful": len([c for c in results["chapters_generated"] if c.get("generation_status") == "success"]),
            "fact_checks_performed": len(results["fact_checks"]),
            "total_content_length": sum([c.get("content_length", 0) for c in results["chapters_generated"]])
        }
        
        print(f"\n{'='*60}")
        print(f"📊 GENERATION SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Chapters Generated: {results['summary_report']['chapters_successful']}/{results['summary_report']['total_chapters']}")
        print(f"🔍 Fact-Checks Performed: {results['summary_report']['fact_checks_performed']}")
        print(f"📄 Total Content Length: {results['summary_report']['total_content_length']} characters")
        
        return results
        
    except Exception as e:
        print(f"❌ Workflow error: {e}")
        results["error"] = str(e)
        return results


async def generate_book_with_quality_metrics(
    book_title: str,
    age_group: str,
    chapters: List[dict],
    topics: List[str],
    quality_checks: bool = True
) -> dict:
    """
    Generate book with enhanced quality metrics and reporting.
    
    Args:
        book_title: Title of the book
        age_group: Target age group
        chapters: Chapter specifications
        topics: Educational topics
        quality_checks: Include detailed quality metrics
        
    Returns:
        Results with quality metrics and fact-check details
    """
    
    results = await generate_and_fact_check_book(
        book_title=book_title,
        age_group=age_group,
        chapters=chapters,
        topics=topics,
        enable_fact_checking=True
    )
    
    if quality_checks and results.get("fact_checks"):
        # Add quality metrics
        results["quality_metrics"] = {
            "fact_check_coverage": len(results["fact_checks"]) / len(results["chapters_generated"]) if results["chapters_generated"] else 0,
            "average_content_length": results["summary_report"]["total_content_length"] / results["summary_report"]["chapters_successful"] if results["summary_report"]["chapters_successful"] > 0 else 0,
            "overall_status": "Complete with fact-verification" if results["fact_checks"] else "Complete (no fact-checks available)"
        }
    
    return results


async def create_fact_checked_book(
    book_spec: dict,
    output_dir: str = "output_books"
) -> Optional[str]:
    """
    End-to-end book creation with fact-checking.
    
    Args:
        book_spec: Book specification dictionary with title, age_group, chapters, topics
        output_dir: Directory for saving output files and reports
        
    Returns:
        Path to generated book report or None if failed
    """
    
    try:
        # Generate and fact-check
        results = await generate_book_with_quality_metrics(
            book_title=book_spec.get("title"),
            age_group=book_spec.get("age_group"),
            chapters=book_spec.get("chapters", []),
            topics=book_spec.get("topics", []),
            quality_checks=True
        )
        
        # Save comprehensive report
        report_filename = f"{book_spec.get('title', 'book').replace(' ', '_')}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = f"{output_dir}/{report_filename}"
        
        # Create output directory if needed
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ Report saved to: {report_path}")
        return report_path
        
    except Exception as e:
        print(f"❌ Error creating book: {e}")
        return None


# Example usage
if __name__ == "__main__":
    async def demo():
        """Demo the enhanced workflow with fact-checking."""
        
        # Example book specification
        book_spec = {
            "title": "Amazing Animals: Learning Through Discovery",
            "age_group": "8-10 years",
            "chapters": [
                {
                    "title": "Lions: Kings of the Savanna",
                    "content_description": "Learn about lion behavior, habitat, and how they hunt"
                },
                {
                    "title": "Dolphins: Intelligent Ocean Dwellers", 
                    "content_description": "Explore dolphin intelligence, communication, and marine habitats"
                },
                {
                    "title": "Elephants: Gentle Giants",
                    "content_description": "Discover elephant families, memory, and conservation efforts"
                }
            ],
            "topics": ["Wildlife", "Animal Behavior", "Natural Habitats", "Conservation"]
        }
        
        print("🚀 Starting Enhanced Book Generation with Fact-Checking...")
        print("This workflow includes web search verification!\n")
        
        results = await generate_and_fact_check_book(
            book_title=book_spec["title"],
            age_group=book_spec["age_group"],
            chapters=book_spec["chapters"],
            topics=book_spec["topics"],
            enable_fact_checking=True
        )
        
        print("\n📊 Results Summary:")
        print(json.dumps(results["summary_report"], indent=2))

    asyncio.run(demo())
