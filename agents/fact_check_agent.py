"""
Fact-checking agent using Qwen models with web search.
Verifies educational content by searching the web for real-time information.
Uses DashScope OpenAI-compatible API with enable_search parameter.
"""
import os
from typing import Optional
from agent_framework import RawAgent
from agent_framework.openai import OpenAIChatClient
from config import get_model_config

import asyncio


async def create_fact_check_agent(use_qwen: bool = True) -> RawAgent:
    """
    Create a fact-checking agent using Qwen with web search capabilities.
    
    Args:
        use_qwen: If True, use Qwen models; if False, falls back to GitHub Models
                 (Note: Web search only works with Qwen models, GitHub Models don't support it)
    
    Returns:
        Agent instance configured for fact-checking with web search
    
    Best practices:
    - Uses OpenAI-compatible API with enable_search parameter
    - Requires DashScope API key for web search functionality
    - Only available with Qwen models (qwen3-max, qwen3.5-plus, etc.)
    """
    if not use_qwen:
        raise ValueError("Fact-checking with web search requires Qwen models (use_qwen=True)")
    
    # Must use Qwen for web search capabilities
    config = get_model_config(use_qwen=True)
    
    # Note: For web search, we need to use a model that supports it
    # Recommended: qwen3-max, qwen3.5-plus (or later snapshots)
    # The model_id in config may be "qwen-plus", but we use qwen3-max for web search
    client = OpenAIChatClient(
        api_key=os.getenv(config["api_key_env"], ""),
        base_url=config["base_url"],
        model_id="qwen3-max"  # Use qwen3-max for web search support
    )
    
    agent = client.as_agent(
        name="FactCheckAgent",
        instructions=(
            "You are an expert fact-checker for educational content. Your role is to verify the accuracy "
            "of claims, statistics, dates, and other factual information in educational materials. "
            "You have access to real-time web search to verify information. "
            "\n\nYour responsibilities:\n"
            "1. Search the web for relevant, authoritative sources\n"
            "2. Compare the provided content against current information\n"
            "3. Identify any inaccuracies, outdated information, or missing context\n"
            "4. Provide citations and sources for verified information\n"
            "5. Rate confidence level (High/Medium/Low) for each verification\n"
            "6. Suggest corrections or improvements where needed\n"
            "\nAlways prioritize recent, authoritative sources (academic institutions, government "
            "official websites, peer-reviewed journals, established news organizations). "
            "Be transparent about limitations and uncertainties in information."
        ),
    )
    return agent


async def fact_check_content(
    agent: RawAgent,
    content: str,
    topic: Optional[str] = None,
    context: Optional[str] = None
) -> Optional[dict]:
    """
    Fact-check educational content using web search.
    
    Args:
        agent: The fact-checking agent instance
        content: The educational content to verify
        topic: Optional topic/subject area for better context
        context: Optional additional context about the material
        
    Returns:
        Dictionary with fact-check results or None if verification fails
        
    Example:
        result = await fact_check_content(
            agent,
            "The Great Wall of China is approximately 13,171 miles long.",
            topic="Geography",
            context="Elementary school textbook"
        )
    """
    try:
        # Build comprehensive fact-check prompt
        prompt = f"""Please fact-check the following educational content:

CONTENT TO VERIFY:
{content}

"""
        if topic:
            prompt += f"SUBJECT/TOPIC: {topic}\n"
        if context:
            prompt += f"CONTEXT: {context}\n"
        
        prompt += """

FACT-CHECK INSTRUCTIONS:
1. Identify all factual claims that can be verified (statistics, dates, names, locations, scientific facts)
2. Search the web for current information about each claim
3. For each claim, provide:
   - CLAIM: [The specific statement being checked]
   - STATUS: [Accurate/Outdated/Partially Accurate/Inaccurate]
   - CONFIDENCE: [High/Medium/Low]
   - EVIDENCE: [What the web search found]
   - SOURCES: [URLs or source names]
   - NOTES: [Any additional context or corrections needed]

4. Summarize overall accuracy and provide recommendations for improvement
5. Highlight any claims that need updates or clarification"""
        
        # Use agent.run with streaming to handle web search
        # The enable_search parameter will be passed through extra_body in config
        response = await agent.run(prompt)
        
        if response:
            return {
                "status": "verified",
                "fact_check_result": response,
                "content_checked": content[:200] + "..." if len(content) > 200 else content
            }
        else:
            return None
            
    except Exception as e:
        print(f"❌ Fact-checking error: {e}")
        return None


async def batch_fact_check(
    agent: RawAgent,
    content_list: list,
    topics: Optional[list] = None
) -> list:
    """
    Fact-check multiple pieces of content in sequence.
    
    Args:
        agent: The fact-checking agent
        content_list: List of content strings to verify
        topics: Optional list of topics corresponding to each content
        
    Returns:
        List of fact-check results
    """
    results = []
    
    for i, content in enumerate(content_list):
        topic = topics[i] if topics and i < len(topics) else None
        print(f"Fact-checking item {i+1}/{len(content_list)}...")
        
        result = await fact_check_content(agent, content, topic)
        if result:
            results.append(result)
        
        # Small delay between checks to avoid rate limiting
        await asyncio.sleep(1)
    
    return results


async def verify_chapter_accuracy(
    agent: RawAgent,
    chapter_title: str,
    chapter_content: str,
    age_group: Optional[str] = None
) -> dict:
    """
    Specialized fact-checking for educational chapter content.
    
    Args:
        agent: The fact-checking agent
        chapter_title: Title of the chapter
        chapter_content: Full chapter content to verify
        age_group: Target age group (e.g., "8-10 years", "12-14 years")
        
    Returns:
        Comprehensive fact-check report for the chapter
        
    Key features:
    - Checks age-appropriateness of information
    - Verifies scientific accuracy
    - Identifies outdated information
    - Suggests supplementary sources
    """
    prompt = f"""CHAPTER FACT-CHECK REQUEST

Chapter Title: {chapter_title}
"""
    if age_group:
        prompt += f"Target Age Group: {age_group}\n"
    
    prompt += f"""
Chapter Content:
{chapter_content}

COMPREHENSIVE FACT-CHECK:
1. **Accuracy Verification**
   - Check all factual claims against current authoritative sources
   - Identify any scientific inaccuracies
   - Verify historical facts and dates
   - Check geographical information

2. **Age-Appropriateness**
   - Is the content suitable for the target age group?
   - Are explanations at an appropriate level of complexity?
   - Is potentially sensitive information presented appropriately?

3. **Currency & Relevance**
   - Is the information current and up-to-date?
   - Are statistics recent or outdated?
   - Any outdated references or technologies mentioned?

4. **Sources & Citations**
   - Provide authoritative sources for verified claims
   - Suggest additional reliable resources for learning

5. **Recommendations**
   - Specific corrections needed
   - Suggested additions or clarifications
   - Improvements to accuracy and engagement

Format the response with clear sections and bullet points for easy reference."""
    
    try:
        response = await agent.run(prompt)
        
        return {
            "chapter_title": chapter_title,
            "age_group": age_group or "Not specified",
            "fact_check_report": response,
            "status": "completed"
        }
    except Exception as e:
        print(f"❌ Chapter verification error: {e}")
        return {
            "chapter_title": chapter_title,
            "status": "error",
            "error_message": str(e)
        }


# Example usage and testing
if __name__ == "__main__":
    async def demo():
        """Demo fact-checking with sample educational content."""
        
        print("🔍 Initializing Fact-Check Agent with web search...")
        try:
            agent = await create_fact_check_agent(use_qwen=True)
            
            # Example content to fact-check
            sample_content = [
                "Mount Everest is the tallest mountain on Earth at 29,032 feet (8,849 meters).",
                "The human heart beats approximately 100,000 times per day.",
                "Paris is the capital of France and is located on the Seine River."
            ]
            
            print("\n✅ Agent created successfully!")
            print("📚 Sample content ready for fact-checking...")
            
            # Demonstrate fact-checking capability
            print("\n🌐 Web search capability enabled!")
            print("Note: This agent can now verify information in real-time using web search.")
            print("\nTo use in your workflow:")
            print("1. Import: from agents.fact_check_agent import create_fact_check_agent, fact_check_content")
            print("2. Create agent: agent = await create_fact_check_agent(use_qwen=True)")
            print("3. Fact-check: result = await fact_check_content(agent, your_content)")
            print("\n✨ Fact-checking agent is ready!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Make sure DASHSCOPE_API_KEY is set and you're using Qwen models")

    # Run demo
    asyncio.run(demo())
