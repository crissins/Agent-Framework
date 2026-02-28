"""
QUICK REFERENCE: Fact-Checking Agent
Copy-paste ready code snippets for common tasks
"""

# ============================================================================
# SETUP & CONFIGURATION
# ============================================================================

# 1. Set API Key (Windows Command Prompt)
"""
set DASHSCOPE_API_KEY=sk-your_key_here
"""

# 2. Set API Key (Windows PowerShell)
"""
$env:DASHSCOPE_API_KEY="sk-your_key_here"
"""

# 3. Set API Key (Python)
import os
os.environ['DASHSCOPE_API_KEY'] = 'sk-your_key_here'

# 4. Verify Setup
from config import verify_fact_check_setup
is_ready, msg = verify_fact_check_setup()
print(msg)

# ============================================================================
# BASIC USAGE
# ============================================================================

# Create a fact-checking agent with web search
from agents.fact_check_agent import create_fact_check_agent
import asyncio

async def setup_agent():
    agent = await create_fact_check_agent(use_qwen=True)
    return agent

# ============================================================================
# FACT-CHECK SINGLE CLAIM
# ============================================================================

from agents.fact_check_agent import fact_check_content

async def check_one_fact():
    agent = await create_fact_check_agent(use_qwen=True)
    
    result = await fact_check_content(
        agent,
        content="Mount Everest is 29,032 feet tall",
        topic="Geography",
        context="Educational textbook"
    )
    
    print(result['fact_check_result'])

# asyncio.run(check_one_fact())

# ============================================================================
# FACT-CHECK MULTIPLE CLAIMS
# ============================================================================

from agents.fact_check_agent import batch_fact_check

async def check_multiple_facts():
    agent = await create_fact_check_agent(use_qwen=True)
    
    claims = [
        "Paris is the capital of France",
        "The Great Wall is 13,171 miles long",
        "Water freezes at 32°F"
    ]
    
    topics = ["Geography", "History", "Physics"]
    
    results = await batch_fact_check(agent, claims, topics)
    
    for result in results:
        print(f"✅ {result}")

# asyncio.run(check_multiple_facts())

# ============================================================================
# FACT-CHECK EDUCATIONAL CHAPTER
# ============================================================================

from agents.fact_check_agent import verify_chapter_accuracy

async def check_chapter():
    agent = await create_fact_check_agent(use_qwen=True)
    
    chapter = """
    The Amazon rainforest produces about 20% of the world's oxygen.
    It spans approximately 5.5 million square kilometers.
    The rainforest is home to about 10% of all species on Earth.
    """
    
    result = await verify_chapter_accuracy(
        agent,
        chapter_title="The Amazon",
        chapter_content=chapter,
        age_group="10-12 years"
    )
    
    print(result['fact_check_report'])

# asyncio.run(check_chapter())

# ============================================================================
# GENERATE BOOK WITH FACT-CHECKING
# ============================================================================

from agents.enhanced_book_workflow import generate_and_fact_check_book

async def create_book():
    results = await generate_and_fact_check_book(
        book_title="Amazing Animals",
        age_group="8-10 years",
        chapters=[
            {"title": "Lions", "content_description": "Learn about lions"},
            {"title": "Dolphins", "content_description": "Smart ocean friends"}
        ],
        topics=["Animals", "Nature"],
        enable_fact_checking=True  # This enables web search!
    )
    
    return results

# results = asyncio.run(create_book())

# ============================================================================
# RUN EXAMPLES
# ============================================================================

"""
Run practical examples:

   python agents/example_fact_checking.py --example 1     # Simple check
   python agents/example_fact_checking.py --example 4     # Book generation
   python agents/example_fact_checking.py --all           # All examples
"""

# ============================================================================
# ERROR HANDLING
# ============================================================================

async def safe_fact_check():
    try:
        agent = await create_fact_check_agent(use_qwen=True)
        
        result = await fact_check_content(
            agent,
            "Some educational claim",
            topic="Science"
        )
        
        if result:
            print("✅ Success!")
        else:
            print("❌ No result")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Check that DASHSCOPE_API_KEY is set correctly")

# asyncio.run(safe_fact_check())

# ============================================================================
# INTEGRATED WITH BOOK GENERATION WORKFLOW
# ============================================================================

from agents.workflow_book_generator import create_book_chapter_agent

async def full_workflow():
    # Initialize both agents
    book_agent = await create_book_chapter_agent()
    fact_check_agent = await create_fact_check_agent(use_qwen=True)
    
    # Generate chapter
    chapter = await book_agent.run("Write chapter about photosynthesis for 8-year-olds")
    
    # Fact-check the generated chapter
    if chapter:
        verification = await fact_check_content(
            fact_check_agent,
            chapter,
            topic="Biology",
            context="Children's educational content"
        )
        
        print(f"Generated: {len(chapter)} characters")
        print(f"Verified: {verification['status']}")

# asyncio.run(full_workflow())

# ============================================================================
# CONFIGURATION REFERENCE
# ============================================================================

"""
SUPPORTED MODELS (for web search):
  - qwen3-max (recommended) - Most capable
  - qwen3.5-plus           - Good alternative
  - qwen-plus              - Basic support

REGIONS:
  - singapore (default)    - Fastest for Asia
  - beijing                - China region
  - us-virginia            - US region

API ENDPOINTS:
  DashScope OpenAI-compatible: https://api.openai.com/v1
  
ENVIRONMENT VARIABLES:
  - DASHSCOPE_API_KEY      - Required for web search fact-checking
  - GITHUB_TOKEN           - For fallback GitHub Models (no web search)
"""

# ============================================================================
# COMMON PROMPTING PATTERNS
# ============================================================================

"""
PATTERN 1: Verify specific types of claims
────────────────────────────────────────
"Verify the accuracy of these historical dates:
- Napoleon died in 1821
- The American Civil War ended in 1865
Provide sources for each date."

PATTERN 2: Age-appropriate content check
─────────────────────────────────────────
"Is this content appropriate for 6-8 year old students?
[content here]

Check:
1. Vocabulary complexity
2. Factual accuracy
3. Concept difficulty level
4. Safety concerns"

PATTERN 3: Source quality assessment
────────────────────────────────────
"These claims come from [source].
Verify using authoritative sources:
- Academic institutions
- Government official websites
- Peer-reviewed journals
- Reputable news organizations"

PATTERN 4: Correction required
──────────────────────────────
"Find errors in this content and provide corrected version:
[content here]

Format corrections as:
- INCORRECT: [original text]
- CORRECT: [fixed text]
- REASON: [why it was wrong]"
"""

# ============================================================================
# PERFORMANCE TIPS
# ============================================================================

"""
1. BATCH PROCESSING
   Use batch_fact_check() for multiple claims at once
   
2. CACHING
   Consider caching results for frequently-checked facts
   
3. PARALLEL REQUESTS
   Use asyncio.gather() for concurrent fact-checking of multiple chapters
   
4. SPECIFIC PROMPTS
   More specific prompts = more accurate fact-checks
   Include context like age group and educational level
   
5. TIMEOUT HANDLING
   Web search can be slow - allow adequate time for responses
   
6. ERROR RECOVERY
   Implement retry logic for network issues
"""

# Example: Parallel fact-checking
async def parallel_fact_check():
    agent = await create_fact_check_agent(use_qwen=True)
    
    claims = [
        "Claim 1",
        "Claim 2",
        "Claim 3"
    ]
    
    # Check all claims in parallel
    tasks = [
        fact_check_content(agent, claim, topic="Science")
        for claim in claims
    ]
    
    results = await asyncio.gather(*tasks)
    return results

# ============================================================================
# TROUBLESHOOTING CHECKLIST
# ============================================================================

"""
✓ API Key Setup
  - Is DASHSCOPE_API_KEY set? (run: echo %DASHSCOPE_API_KEY%)
  - Does key start with 'sk-'?
  - Is it for correct DashScope account?

✓ Model Configuration
  - Using qwen models? (not GitHub Models)
  - Model supports web search? (qwen3-max recommended)
  - Correct region selected?

✓ Network & Connectivity
  - Is internet connection active?
  - Can you access dashscope.aliyun.com?
  - No firewall blocking DashScope API?

✓ Rate Limits
  - Check DashScope dashboard for usage
  - May need to wait if at limit
  - Consider upgrading plan if needed

✓ Content Issues
  - Very short content may not have enough to verify
  - Extremely niche topics may not have web search results
  - Controversial topics might have varying sources
"""

# ============================================================================
# GETTING HELP
# ============================================================================

"""
DOCUMENTATION:
- DashScope: https://dashscope.aliyun.com/docs/
- Qwen Models: https://qwen.aliyun.com/
- Full README: See FACT_CHECK_README.md

CODE EXAMPLES:
- agents/example_fact_checking.py - Practical examples

COMMON ISSUES:
- See FACT_CHECK_README.md troubleshooting section
"""

print("""
╔════════════════════════════════════════════════════════════════════════╗
║                    QUICK REFERENCE LOADED                             ║
║                                                                        ║
║ Copy code snippets to use fact-checking in your projects!             ║
║ See detailed examples in: agents/example_fact_checking.py             ║
║                                                                        ║
│ NEXT STEPS:                                                            ║
║ 1. Set DASHSCOPE_API_KEY environment variable                         ║
║ 2. Run: python agents/example_fact_checking.py --example 1            ║
║ 3. Integrate into your workflow using snippets above                  ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝
""")
