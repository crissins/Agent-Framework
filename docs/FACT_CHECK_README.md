# 🔍 Fact-Checking Agent with Web Search

A powerful fact-checking agent that uses **Qwen AI models with real-time web search** to verify educational content accuracy. Perfect for validating book content, educational materials, and learning resources.

## ✨ Key Features

- 🌐 **Real-Time Web Search**: Verify facts with current information from the internet
- 📚 **Educational Focus**: Specialized in checking textbook and learning material accuracy
- 🎯 **Age-Appropriate Checking**: Validates content suitability for specific age groups
- 📊 **Confidence Levels**: Reports confidence (High/Medium/Low) for each verification
- 🔗 **Source Citations**: Provides URLs and sources for verified information
- 🔄 **Book Integration**: Seamlessly integrates with book generation workflow
- ✅ **Detailed Reports**: Comprehensive fact-check reports with recommendations

## 🚀 Quick Start

### 1. Get Your API Key (Free)

Visit [DashScope](https://dashscope.aliyun.com/) to get your free API key:

1. Sign up for free account
2. Navigate to API Keys section
3. Create new API key
4. Copy the key (format: `sk-xxxxx...`)

### 2. Set Environment Variable

**Windows Command Prompt:**
```batch
set DASHSCOPE_API_KEY=sk-your_api_key_here
```

**Windows PowerShell:**
```powershell
$env:DASHSCOPE_API_KEY="sk-your_api_key_here"
```

**In Python Code:**
```python
import os
os.environ['DASHSCOPE_API_KEY'] = 'sk-your_api_key_here'
```

### 3. Basic Usage

```python
from agents.fact_check_agent import create_fact_check_agent, fact_check_content
import asyncio

async def verify_fact():
    # Create agent with web search
    agent = await create_fact_check_agent(use_qwen=True)
    
    # Fact-check content
    content = "Mount Everest is the tallest mountain at 29,032 feet."
    
    result = await fact_check_content(
        agent,
        content,
        topic="Geography",
        context="Educational textbook"
    )
    
    print(result['fact_check_result'])

asyncio.run(verify_fact())
```

## 📖 Advanced Usage

### Fact-Check Educational Chapters

```python
from agents.fact_check_agent import verify_chapter_accuracy
import asyncio

async def check_chapter():
    agent = await create_fact_check_agent(use_qwen=True)
    
    chapter_content = """
    The Great Wall of China spans approximately 13,171 miles.
    It was built over many centuries, primarily during the Ming Dynasty.
    The wall served as a defensive fortification against invasions.
    """
    
    report = await verify_chapter_accuracy(
        agent,
        chapter_title="The Great Wall of China",
        chapter_content=chapter_content,
        age_group="10-12 years"
    )
    
    print(report['fact_check_report'])

asyncio.run(check_chapter())
```

### Batch Fact-Checking

```python
from agents.fact_check_agent import batch_fact_check
import asyncio

async def check_multiple():
    agent = await create_fact_check_agent(use_qwen=True)
    
    content_list = [
        "The Earth orbits the Sun in 365.25 days.",
        "Photosynthesis converts light energy into chemical energy.",
        "The Amazon rainforest produces about 20% of the world's oxygen."
    ]
    
    topics = ["Astronomy", "Biology", "Ecology"]
    
    results = await batch_fact_check(agent, content_list, topics)
    
    for result in results:
        print(f"✅ {result}")

asyncio.run(check_multiple())
```

### Integrated with Book Generation

```python
from agents.enhanced_book_workflow import generate_and_fact_check_book
import asyncio

async def create_verified_book():
    results = await generate_and_fact_check_book(
        book_title="Amazing Animals: Learning Through Discovery",
        age_group="8-10 years",
        chapters=[
            {"title": "Lions", "content_description": "Learn about lion behavior"},
            {"title": "Dolphins", "content_description": "Ocean intelligence"}
        ],
        topics=["Wildlife", "Animals", "Conservation"],
        enable_fact_checking=True  # Enables web search verification!
    )
    
    print(results['summary_report'])

asyncio.run(create_verified_book())
```

## 📊 Output Format

The fact-checking agent returns structured results with:

```json
{
  "chapter_title": "Chapter Name",
  "age_group": "8-10 years",
  "fact_check_report": {
    "CLAIM": "The specific statement being checked",
    "STATUS": "Accurate/Outdated/Partially Accurate/Inaccurate",
    "CONFIDENCE": "High/Medium/Low",
    "EVIDENCE": "Information found from web search",
    "SOURCES": ["URL1", "URL2"],
    "NOTES": "Additional context or correction recommendations"
  }
}
```

## 🎯 Prompt Engineering Best Practices

The agent implements industry-proven prompting techniques:

### 1. **Clear Role Definition**
Agent understands it's a specialized fact-checker with specific expertise
```python
"You are an expert fact-checker for educational content..."
```

### 2. **Structured Instructions**
Step-by-step fact-checking process with explicit requirements
```
1. Identify all factual claims
2. Search the web for verification
3. Provide structured results
4. Rate confidence levels
```

### 3. **Quality Constraints**
Emphasis on authoritative sources
```python
"Prioritize recent, authoritative sources (academic institutions, 
government official websites, peer-reviewed journals)"
```

### 4. **Output Format Specification**
Explicit structure for results with confidence levels and sources

### 5. **Contextual Information**
Age group, topic, and educational context for better accuracy

### 6. **Source Citation**
Transparent requirement for citing sources and evidence

### 7. **Transparency**
Agent explicitly reports limitations and uncertainties

## 🔧 Configuration

### Supported Models

**Recommended for Web Search:**
- `qwen3-max` - Most capable, best for web search (recommended)
- `qwen3.5-plus` - Good alternative
- `qwen-plus` - Basic web search support

**Note:** Web search only works with Qwen models. GitHub Models don't support web search.

### Region Selection

```python
from config import get_model_config

# Singapore region (default)
config = get_model_config(use_qwen=True, qwen_region="singapore")

# Beijing region
config = get_model_config(use_qwen=True, qwen_region="beijing")

# US Virginia region  
config = get_model_config(use_qwen=True, qwen_region="us-virginia")
```

## ⚠️ Important Notes

- **Active Internet Required**: Web search needs internet connectivity
- **Rate Limits**: Depending on DashScope plan, may have usage limits
- **Free Tier**: Available with free DashScope account
- **Specialized Topics**: Some niche claims may not be web-searchable
- **Multiple Sources**: Always verify critical information with multiple sources
- **Confidence Levels**: Agent indicates confidence for transparency

## 🐛 Troubleshooting

### "API key not found" Error
**Solution:** Verify DASHSCOPE_API_KEY is set correctly
```python
import os
print(os.getenv('DASHSCOPE_API_KEY'))  # Should show your key
```

### "Model not found" Error
**Solution:** Ensure using supported Qwen model
```python
agent = await create_fact_check_agent(use_qwen=True)
# Internally uses qwen3-max
```

### Web Search Not Working
**Solution:** Verify:
1. DASHSCOPE_API_KEY is correctly set
2. Using Qwen models (not GitHub Models)
3. Internet connection is active
4. DashScope plan supports web search

### Slow Responses
**Solution:** Web search adds latency - this is normal
- `qwen3-max` is faster than alternatives
- Consider batch processing for multiple items

## 📚 Integration Examples

### With Curriculum Agent
```python
from agents.curriculum_agent import create_curriculum_agent
from agents.fact_check_agent import fact_check_content

# Generate curriculum
curriculum = await create_curriculum_agent()
content = await curriculum.generate_lesson()

# Verify accuracy
fact_check = await create_fact_check_agent(use_qwen=True)
verification = await fact_check_content(fact_check, content)
```

### With Image Search Agent
```python
from agents.image_search_agent import search_images
from agents.fact_check_agent import fact_check_content

# Find images for topic
images = await search_images("Mountain Geography")

# Verify descriptive content
fact_check_agent = await create_fact_check_agent(use_qwen=True)
# Fact-check captions and descriptions...
```

## 🎓 Educational Use Cases

1. **Textbook Verification**: Ensure accuracy before publishing education materials
2. **Lesson Plan Validation**: Verify facts in lesson plans and teaching materials  
3. **Student Project Review**: Check student research accuracy
4. **Interactive Learning**: Provide fact-checked information in educational apps
5. **Curriculum Quality**: Maintain accuracy across entire curricula
6. **Multi-language Education**: Verify translations maintain accuracy

## 🔐 API Best Practices

- Never hardcode API keys in source code
- Use environment variables for sensitive data
- Rotate API keys regularly
- Monitor DashScope usage and costs
- Use region closest to your location for better latency

## 📖 Related Files

- [agents/fact_check_agent.py](agents/fact_check_agent.py) - Main fact-checking agent
- [agents/enhanced_book_workflow.py](agents/enhanced_book_workflow.py) - Book generation with fact-checking
- [config.py](config.py) - Configuration and setup utilities

## 🤝 Contributing

Found an issue or have an improvement? 
- Report issues with clear examples
- Suggest new fact-checking capabilities
- Share prompt engineering improvements

## 📞 Support

For DashScope-related issues: [DashScope Documentation](https://dashscope.aliyun.com/docs/)
For Qwen model info: [Qwen Models](https://qwen.aliyun.com/)

## ✅ Verification Checklist

Before using in production:

- [ ] DASHSCOPE_API_KEY is set
- [ ] Test fact-checking on sample content
- [ ] Verify sources are current and authoritative
- [ ] Check internet connection during operation
- [ ] Review confidence levels for critical information
- [ ] Monitor DashScope usage and billing (if applicable)

---

**🚀 Ready to build accurate, verified educational content with AI!**

Get started now:
```python
from agents.fact_check_agent import create_fact_check_agent
agent = await create_fact_check_agent(use_qwen=True)
# Start fact-checking with web search!
```
