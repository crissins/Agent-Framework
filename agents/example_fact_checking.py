"""
PRACTICAL EXAMPLES: Fact-Checking Agent with Web Search
Real-world usage patterns and demonstrations
"""

import asyncio
import os
import sys
from agents.fact_check_agent import (
    create_fact_check_agent,
    fact_check_content,
    verify_chapter_accuracy,
    batch_fact_check
)
from agents.enhanced_book_workflow import generate_and_fact_check_book
from config import verify_fact_check_setup, print_fact_check_setup_guide


# Example 1: Simple Fact-Checking
async def example_simple_fact_check():
    """Basic fact-checking example - verify a single claim"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Simple Fact-Checking")
    print("="*70)
    
    agent = await create_fact_check_agent(use_qwen=True)
    
    # Single claim to verify
    claim = "The Great Wall of China is approximately 13,171 miles long."
    
    print(f"\nVerifying claim: {claim}\n")
    
    result = await fact_check_content(
        agent,
        claim,
        topic="Geography",
        context="Educational textbook for 10-12 year olds"
    )
    
    if result:
        print("✅ Fact-Check Complete!")
        print(f"\nResult: {result['fact_check_result']}")
    else:
        print("❌ Fact-check failed")
    
    return result


# Example 2: Multiple Claims
async def example_batch_fact_check():
    """Fact-check multiple claims efficiently"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Batch Fact-Checking")
    print("="*70)
    
    agent = await create_fact_check_agent(use_qwen=True)
    
    # Multiple claims to verify
    claims = [
        "The Amazon rainforest produces about 20% of the world's oxygen.",
        "Jupiter is the largest planet in our solar system.",
        "Photosynthesis converts light energy into chemical energy.",
        "The human heart beats approximately 100,000 times per day.",
        "Paris is the capital of France."
    ]
    
    topics = [
        "Ecology",
        "Astronomy", 
        "Biology",
        "Medicine",
        "Geography"
    ]
    
    print(f"\nVerifying {len(claims)} claims...\n")
    
    results = await batch_fact_check(agent, claims, topics)
    
    print(f"✅ Completed {len(results)} fact-checks!")
    
    return results


# Example 3: Chapter-Level Verification
async def example_chapter_verification():
    """Fact-check an entire educational chapter"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Chapter-Level Fact-Checking")
    print("="*70)
    
    agent = await create_fact_check_agent(use_qwen=True)
    
    chapter_content = """
    CHAPTER: THE WATER CYCLE
    
    Water constantly moves between Earth's surface and the atmosphere in
    a process called the water cycle. This cycle has several key stages:
    
    Evaporation: Water from oceans, lakes, and rivers turns into water
    vapor due to heat from the Sun. This process occurs at 212°F (100°C),
    the boiling point of water.
    
    Condensation: As water vapor rises into the atmosphere, it cools down
    and turns back into liquid water droplets, forming clouds. Clouds are
    made of millions of tiny water droplets.
    
    Precipitation: When clouds become heavy with water droplets, they fall
    to Earth as rain, snow, sleet, or hail. About 400,000 cubic kilometers
    of water falls as precipitation each year.
    
    Collection: Water collects in oceans (97% of Earth's water), lakes,
    rivers, and underground aquifers. This water then evaporates again,
    continuing the cycle.
    
    The water cycle is essential for life on Earth. It distributes fresh
    water across the planet and regulates Earth's temperature.
    """
    
    print(f"\nFact-checking chapter with {len(chapter_content)} characters...\n")
    
    result = await verify_chapter_accuracy(
        agent,
        chapter_title="The Water Cycle",
        chapter_content=chapter_content,
        age_group="8-10 years"
    )
    
    if result:
        print("✅ Chapter Verification Complete!")
        print(f"\nStatus: {result['status']}")
        print(f"\nReport:\n{result['fact_check_report']}")
    
    return result


# Example 4: Book Generation with Fact-Checking
async def example_book_with_fact_checking():
    """Generate an educational book with automatic fact-checking"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Book Generation with Fact-Checking")
    print("="*70)
    
    book_spec = {
        "title": "Amazing Animals Around the World",
        "age_group": "8-10 years",
        "chapters": [
            {
                "title": "Lions: Kings of the Savanna",
                "content_description": (
                    "Learn about lion behavior, habitat, social structure, "
                    "hunting patterns, and where they live in Africa"
                )
            },
            {
                "title": "Dolphins: Intelligent Ocean Dwellers",
                "content_description": (
                    "Explore dolphin intelligence, communication methods, "
                    "marine ecosystems, and how they interact with humans"
                )
            },
            {
                "title": "Polar Bears: Masters of the Arctic",
                "content_description": (
                    "Discover polar bear adaptations, Arctic habitats, "
                    "diet, and conservation efforts"
                )
            }
        ],
        "topics": ["Wildlife", "Animal Behavior", "Habitats", "Conservation"]
    }
    
    print(f"\nGenerating book: {book_spec['title']}")
    print(f"Age Group: {book_spec['age_group']}")
    print(f"Chapters: {len(book_spec['chapters'])}")
    print(f"\nGenerating chapters and fact-checking with web search...\n")
    
    results = await generate_and_fact_check_book(
        book_title=book_spec["title"],
        age_group=book_spec["age_group"],
        chapters=book_spec["chapters"],
        topics=book_spec["topics"],
        enable_fact_checking=True
    )
    
    if results:
        print("\n✅ Book Generation Complete!")
        print(f"\nSummary:")
        for key, value in results['summary_report'].items():
            print(f"  {key}: {value}")
    
    return results


# Example 5: Content Remediation (Fixing Inaccurate Content)
async def example_content_remediation():
    """Identify and correct inaccurate educational content"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Content Remediation")
    print("="*70)
    
    agent = await create_fact_check_agent(use_qwen=True)
    
    # Intentionally inaccurate content
    inaccurate_content = """
    FACTS ABOUT PLANETS
    
    Mercury is the hottest planet in our solar system.
    Venus orbits the Sun in exactly 365 days.
    Mars has three moons.
    Earth completes one rotation in 24 hours and 30 minutes.
    """
    
    print(f"\nChecking content for inaccuracies...\n")
    print(f"Content to verify:\n{inaccurate_content}\n")
    
    # Add specific instructions for remediation
    custom_prompt = f"""
Please identify all factual errors in this content about planets:

{inaccurate_content}

For each error:
1. STATE THE INCORRECT CLAIM
2. PROVIDE THE CORRECT INFORMATION
3. EXPLAIN WHY THE ORIGINAL WAS WRONG
4. CITE AUTHORITATIVE SOURCE
5. SUGGEST HOW TO REPHRASE FOR 10-YEAR-OLD STUDENTS

Format clearly with sections for easy reading.
"""
    
    result = await agent.run(custom_prompt)
    
    print("✅ Content Issues Identified!")
    print(f"\nRemediation Report:\n{result}")
    
    return result


# Example 6: Age-Appropriateness Check
async def example_age_appropriate_check():
    """Verify content is appropriately presented for target age group"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Age-Appropriateness Verification")
    print("="*70)
    
    agent = await create_fact_check_agent(use_qwen=True)
    
    age_groups_and_content = [
        {
            "age": "5-7 years",
            "content": "An atom is the smallest particle of matter."
        },
        {
            "age": "10-12 years", 
            "content": "Atoms are composed of protons, neutrons, and electrons orbiting the nucleus."
        },
        {
            "age": "14-16 years",
            "content": "Electrons exist in probability clouds (orbitals) around the nucleus, described by quantum mechanics."
        }
    ]
    
    print("\nVerifying age-appropriate complexity levels...\n")
    
    for item in age_groups_and_content:
        print(f"Age Group: {item['age']}")
        print(f"Content: {item['content']}\n")
    
    # Check all items
    for item in age_groups_and_content:
        result = await fact_check_content(
            agent,
            item['content'],
            topic="Physics/Chemistry",
            context=f"Educational content for {item['age']} years old"
        )
        
        if result:
            print(f"✅ Verified for {item['age']}")
        
        await asyncio.sleep(1)
    
    return True


# Helper function to run individual examples
async def run_example(example_number: int):
    """Run a specific example"""
    examples = {
        1: ("Simple Fact-Checking", example_simple_fact_check),
        2: ("Batch Fact-Checking", example_batch_fact_check),
        3: ("Chapter Verification", example_chapter_verification),
        4: ("Book with Fact-Checking", example_book_with_fact_checking),
        5: ("Content Remediation", example_content_remediation),
        6: ("Age-Appropriateness Check", example_age_appropriate_check),
    }
    
    if example_number not in examples:
        print(f"❌ Example {example_number} not found")
        return
    
    name, func = examples[example_number]
    
    try:
        await func()
    except Exception as e:
        print(f"❌ Error running example: {e}")
        import traceback
        traceback.print_exc()


# Main demonstration
async def main():
    """Run all examples with setup verification"""
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + " "*15 + "FACT-CHECKING AGENT - PRACTICAL EXAMPLES" + " "*12 + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝\n")
    
    # Check setup
    print("🔍 Checking fact-check setup...\n")
    is_ready, msg = verify_fact_check_setup()
    print(msg)
    
    if not is_ready:
        print("\n" + "="*70)
        print("SETUP REQUIRED")
        print("="*70)
        print_fact_check_setup_guide()
        return
    
    print("\n" + "="*70)
    print("AVAILABLE EXAMPLES")
    print("="*70)
    print("""
1. Simple Fact-Checking
   └─ Verify a single educational claim with web search

2. Batch Fact-Checking  
   └─ Verify multiple claims efficiently

3. Chapter-Level Verification
   └─ Fact-check entire educational chapter content

4. Book with Fact-Checking
   └─ Generate book chapters and automatically verify accuracy

5. Content Remediation
   └─ Identify and fix inaccurate content

6. Age-Appropriateness Check
   └─ Verify content meets developmental appropriateness

QUICK START:
    python agents/example_fact_checking.py --example 1

RUN ALL:
    python agents/example_fact_checking.py --all
""")
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            print("\n🚀 Running all examples...\n")
            for i in range(1, 7):
                await run_example(i)
        elif sys.argv[1] == "--example" and len(sys.argv) > 2:
            try:
                example_num = int(sys.argv[2])
                await run_example(example_num)
            except ValueError:
                print(f"❌ Invalid example number: {sys.argv[2]}")
        else:
            print(f"❌ Unknown argument: {sys.argv[1]}")
            print("Use: --all or --example 1")
    else:
        print("\n💡 Tip: Run with arguments to execute examples:")
        print("   --example 1          (run single example)")
        print("   --all                (run all examples)")
        print("\nExample:")
        print("   python agents/example_fact_checking.py --example 1")


if __name__ == "__main__":
    asyncio.run(main())
