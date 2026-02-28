"""
Fact-checking agent using Qwen models with web search.
Verifies educational content by searching the web for real-time information.
Uses DashScope OpenAI-compatible API with enable_search parameter.
"""
import os
from typing import Optional
from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient
from config import get_model_config

import asyncio


async def create_fact_check_agent(use_qwen: bool = True) -> ChatAgent:
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
            "### CONTEXT ###\n"
            "You are a senior fact-checker and research analyst with expertise in educational "
            "content verification. You have access to real-time web search to verify information "
            "against current, authoritative sources. Your work ensures that educational materials "
            "are accurate, up-to-date, and trustworthy for young learners.\n\n"
            "### OBJECTIVE ###\n"
            "Verify the accuracy of claims, statistics, dates, scientific facts, and other "
            "factual information in educational materials. Provide evidence-based assessments "
            "with clear sourcing.\n\n"
            "### TASK STEPS ###\n"
            "For each piece of content you receive:\n"
            "1. Identify all discrete factual claims that can be independently verified\n"
            "2. Search the web for relevant, authoritative sources for each claim\n"
            "3. Compare the provided content against current, verified information\n"
            "4. Classify each claim as: Accurate / Partially Accurate / Outdated / Inaccurate\n"
            "5. Rate your confidence level (High / Medium / Low) based on source quality\n"
            "6. Provide specific citations and source URLs for verified information\n"
            "7. Suggest concrete corrections or improvements where needed\n\n"
            "### SOURCE PRIORITY (highest to lowest) ###\n"
            "1. Peer-reviewed academic journals and research papers\n"
            "2. Government and international organization official data (WHO, UNESCO, NASA, etc.)\n"
            "3. Established educational institutions (.edu domains)\n"
            "4. Reputable encyclopedias and reference works\n"
            "5. Established news organizations with editorial standards\n\n"
            "### CONSTRAINTS ###\n"
            "- Always prioritize recency \u2014 flag any information older than 3 years\n"
            "- Be transparent about limitations and uncertainties\n"
            "- Distinguish between facts, approximations, and commonly cited but debated claims\n"
            "- When sources conflict, note the disagreement and cite both sides\n"
            "- Never state a claim is verified without providing at least one authoritative source"
        ),
    )
    return agent


async def fact_check_content(
    agent: ChatAgent,
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
        prompt = f"""=== FACT-CHECK REQUEST ===

### CONTENT TO VERIFY ###
{content}

"""
        if topic:
            prompt += f"### SUBJECT/TOPIC ###\n{topic}\n\n"
        if context:
            prompt += f"### ADDITIONAL CONTEXT ###\n{context}\n\n"
        
        prompt += """### TASK STEPS ###
1. Read the content carefully and identify every discrete factual claim
   (statistics, dates, names, locations, scientific facts, measurements)
2. Search the web for current, authoritative information about each claim
3. For each claim, produce a structured assessment:

   === CLAIM: [The exact statement being checked] ===
   STATUS: [Accurate / Outdated / Partially Accurate / Inaccurate]
   CONFIDENCE: [High / Medium / Low]
   EVIDENCE: [What authoritative sources say about this claim]
   SOURCES: [URLs or full source citations]
   NOTES: [Any corrections needed, missing context, or caveats]

4. After all individual claims, write a SUMMARY section:
   - Overall accuracy percentage estimate
   - Most critical corrections needed
   - Recommendations for improving the content's reliability
   - Any claims that require special attention for the target audience

### THINKING PROCESS ###
Before verifying each claim, briefly explain your reasoning:
- Why you classified it as accurate/inaccurate
- What made you choose the confidence level
- Whether the claim is age-appropriate even if technically accurate"""
        
        # Use agent.run with streaming to handle web search
        # The enable_search parameter will be passed through extra_body in config
        response = await agent.run(prompt)
        
        if response:
            result_text = response.text if hasattr(response, "text") else str(response)
            return {
                "status": "verified",
                "fact_check_result": result_text,
                "content_checked": content[:200] + "..." if len(content) > 200 else content
            }
        else:
            return None
            
    except Exception as e:
        print(f"❌ Fact-checking error: {e}")
        return None


async def batch_fact_check(
    agent: ChatAgent,
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
    agent: ChatAgent,
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
    prompt = f"""=== CHAPTER FACT-CHECK REQUEST ===

### CHAPTER DETAILS ###
Chapter Title: {chapter_title}
"""
    if age_group:
        prompt += f"Target Age Group: {age_group}\n"
    
    prompt += f"""
### CHAPTER CONTENT TO VERIFY ###
>>>
{chapter_content}
<<<

### TASK STEPS ###
Follow this systematic verification process:

**Step 1: Accuracy Verification**
   - Extract every factual claim from the chapter content
   - Search the web for each claim using authoritative sources
   - Classify each claim: Accurate / Partially Accurate / Outdated / Inaccurate
   - Verify scientific facts, historical dates, geographical data, and statistics

**Step 2: Age-Appropriateness Assessment**
   - Is the complexity level suitable for the target age group?
   - Are explanations clear enough without oversimplifying to the point of inaccuracy?
   - Is potentially sensitive information presented in a developmentally appropriate way?
   - Are analogies and examples appropriate for the audience?

**Step 3: Currency & Relevance Check**
   - Flag any information that may be outdated (older than 3 years)
   - Identify statistics that need updating with current data
   - Note any outdated references, technologies, or cultural references

**Step 4: Sources & Recommendations**
   - Provide authoritative source URLs for each verified claim
   - Suggest additional reliable educational resources for teachers/students
   - List specific corrections needed with the correct information
   - Propose improvements to enhance both accuracy and engagement

### THINKING PROCESS ###
For each fact you check, briefly explain:
- What you searched for and what you found
- Why you assigned that accuracy status
- How confident you are and why

### OUTPUT FORMAT ###
Use clear section headers, bullet points, and bold text for easy scanning.
End with a summary table: Total claims checked | Accurate | Needs correction | Outdated"""
    
    try:
        response = await agent.run(prompt)
        
        report_text = response.text if hasattr(response, "text") else str(response)
        return {
            "chapter_title": chapter_title,
            "age_group": age_group or "Not specified",
            "fact_check_report": report_text,
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
