# 📚 LATAM Book Generator — Documentation Index

## Quick Navigation

| Document | Description |
|----------|-------------|
| [**README**](../README.md) | Project overview, features, quick start, and architecture diagram |
| [**Setup Guide**](SETUP.md) | Installation, API keys, configuration, and running the app |
| [**User Guide**](USER_GUIDE.md) | How to use Chat, Form, and Voice modes; sidebar settings |
| [**Architecture**](ARCHITECTURE.md) | System design, pipeline flow, provider architecture, retry logic |
| [**Agents Reference**](AGENTS_REFERENCE.md) | Complete reference for all 16 agents with functions and parameters |
| [**Fact-Checking Guide**](FACT_CHECK_README.md) | Web search fact-checking setup and usage |
| [**AI Toolkit Tracing**](AI_TOOLKIT_TRACING_SETUP.md) | OpenTelemetry tracing with VS Code AI Toolkit |
| [**Qwen Image Guide**](QWEN_IMAGE_GUIDE.md) | AI image generation with Qwen-Image models |
| [**Best Practices**](BEST_PRACTICES.md) | Engineering patterns and conventions used |

---

## Getting Started (30 seconds)

```bash
git clone https://github.com/crissins/Agent-Framework.git
cd Agent-Framework
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
# Create .env with GITHUB_TOKEN and/or DASHSCOPE_API_KEY
python -m streamlit run app.py
```

---

## Legacy Documentation

## 🎯 Quick Start (3 Steps)

### Step 1: Get API Key (Free)
```
Visit: https://dashscope.aliyun.com/
- Sign up (free)
- Create API key
- Copy key (format: sk-xxxxx...)
```

### Step 2: Set Environment Variable
```batch
set DASHSCOPE_API_KEY=sk-your_key_here
```

### Step 3: Verify Setup
```bash
python verify_setup.py
```

---

## 📖 File Guide

### 🔍 Core Implementation Files

#### **agents/fact_check_agent.py** (342 lines)
The main fact-checking agent with web search.

**Key Functions:**
- `create_fact_check_agent(use_qwen=True)` - Initialize agent
- `fact_check_content(agent, content, topic, context)` - Verify claims
- `batch_fact_check(agent, content_list, topics)` - Check multiple
- `verify_chapter_accuracy(agent, chapter_title, chapter_content, age_group)` - Deep check

**Features:**
- Real-time web search verification
- Confidence levels (High/Medium/Low)
- Source citations with URLs
- Age-appropriateness validation
- Structured output format

**Usage:**
```python
from agents.fact_check_agent import create_fact_check_agent, fact_check_content
import asyncio

async def verify():
    agent = await create_fact_check_agent(use_qwen=True)
    result = await fact_check_content(agent, "Your claim here")

asyncio.run(verify())
```

---

#### **agents/enhanced_book_workflow.py** (308 lines)
Integration with book generation + fact-checking.

**Key Functions:**
- `generate_and_fact_check_book()` - Full workflow
- `generate_book_with_quality_metrics()` - Enhanced reporting
- `create_fact_checked_book()` - End-to-end process

**Features:**
- Chapter generation + verification in one flow
- Comprehensive quality reports
- Automatic source documentation
- Metadata tracking

**Usage:**
```python
from agents.enhanced_book_workflow import generate_and_fact_check_book

results = await generate_and_fact_check_book(
    book_title="My Book",
    age_group="8-10 years",
    chapters=[...],
    enable_fact_checking=True
)
```

---

#### **agents/example_fact_checking.py** (489 lines)
Six ready-to-run practical examples.

**Examples Included:**
1. Simple Fact-Checking - Single claim verification
2. Batch Fact-Checking - Multiple claims at once
3. Chapter Verification - Full chapter accuracy check
4. Book with Fact-Checking - Integrated workflow
5. Content Remediation - Find and fix errors
6. Age-Appropriateness Check - Developmental suitability

**Run Examples:**
```bash
python agents/example_fact_checking.py --example 1
python agents/example_fact_checking.py --all
```

---

#### **config.py** (Updated)
Configuration management with fact-check functions.

**New Functions:**
- `get_fact_check_config()` - Optimized settings for web search
- `verify_fact_check_setup()` - Check if configured
- `print_fact_check_setup_guide()` - User-friendly guide

**Region Support:**
- Singapore (default, fastest for Asia)
- Beijing (China region)
- US Virginia (US region)

---

### 📚 Documentation Files

#### **FACT_CHECK_README.md** (350+ lines)
Comprehensive documentation.

**Sections:**
- ✨ Key Features
- 🚀 Quick Start (3 steps)
- 📖 Advanced Usage
- 📊 Output Format
- 🎯 Prompt Engineering Best Practices
- 🔧 Configuration
- ⚠️ Important Notes
- 🐛 Troubleshooting
- 🎓 Educational Use Cases
- 📞 Support Resources

**Read this for:** Complete reference and troubleshooting

---

#### **QUICK_REFERENCE.py** (380+ lines)
Copy-paste ready code snippets.

**Contains:**
- Setup instructions (Windows, PowerShell, Python)
- Basic usage patterns
- Error handling examples
- Configuration reference
- Common prompting patterns
- Performance tips
- Troubleshooting checklist

**Read this for:** Quick answer without full docs

---

#### **IMPLEMENTATION_COMPLETE.md** (280+ lines)
Summary of what was created.

**Includes:**
- What was created (6 files)
- Key features implemented
- How to use (4-step guide)
- Technical specifications
- Educational applications
- File reference table
- Success criteria

**Read this for:** Overview and orientation

---

### 🔧 Utility Files

#### **verify_setup.py** (340+ lines)
Automated setup verification tool.

**Checks:**
1. Python version (3.8+)
2. Required files exist
3. API key configured
4. Module imports working
5. Agent can be created
6. Configuration valid

**Run:**
```bash
python verify_setup.py
```

**Output:** Color-coded report with next steps

---

### 🎯 This File
**INDEX.md** - You are here

Provides master reference to all created files and their purposes.

---

## 🤖 Architecture

```
User Code
    ↓
fact_check_agent.py ← Main Agent Logic
    ↓
enhanced_book_workflow.py ← Integration Layer
    ↓
config.py ← Configuration
    ↓
Agent Framework ← Under the hood
    ↓
DashScope API (Web Search)
    ↓
Qwen Models (qwen3-max)
    ↓
Real-time Web Search Results
```

---

## 📊 Key Metrics

| Aspect | Value |
|--------|-------|
| Total Files Created | 6 |
| Total Code Lines | 1,800+ |
| Documentation Lines | 700+ |
| Examples | 6 scenarios |
| Prompt Engineering Practices | 7 implemented |
| Supported Models | 3 (qwen3-max, qwen3.5-plus, qwen-plus) |
| Regions Supported | 3 (Singapore, Beijing, US) |
| Setup Time | ~2 minutes |

---

## 🎓 Learning Path

### Beginner
1. Read: QUICK_START section in FACT_CHECK_README.md
2. Run: `python verify_setup.py`
3. Try: `python agents/example_fact_checking.py --example 1`

### Intermediate
1. Read: Complete FACT_CHECK_README.md
2. Study: QUICK_REFERENCE.py for patterns
3. Try: Examples 2-4 in example_fact_checking.py

### Advanced
1. Study: fact_check_agent.py implementation
2. Understand: enhanced_book_workflow.py integration
3. Customize: Modify prompts and configurations
4. Integrate: Add to your production workflow

---

## 🚀 Common Tasks

### Task 1: Verify a Single Claim
```python
from agents.fact_check_agent import fact_check_content
result = await fact_check_content(agent, "Your claim")
```
📄 See: QUICK_REFERENCE.py → FACT-CHECK SINGLE CLAIM

### Task 2: Check Multiple Claims
```python
from agents.fact_check_agent import batch_fact_check
results = await batch_fact_check(agent, claims, topics)
```
📄 See: QUICK_REFERENCE.py → FACT-CHECK MULTIPLE CLAIMS

### Task 3: Verify Chapter Accuracy
```python
from agents.fact_check_agent import verify_chapter_accuracy
report = await verify_chapter_accuracy(agent, title, content, age_group)
```
📄 See: agents/example_fact_checking.py → Example 3

### Task 4: Generate Book with Fact-Checking
```python
from agents.enhanced_book_workflow import generate_and_fact_check_book
results = await generate_and_fact_check_book(...)
```
📄 See: agents/example_fact_checking.py → Example 4

### Task 5: Troubleshoot Setup
```bash
python verify_setup.py
```
📄 See: FACT_CHECK_README.md → Troubleshooting

---

## 🌟 Prompt Engineering Best Practices

All implementation follows industry best practices:

1. **Clear Role Definition**
   - Agent knows exact responsibilities
   
2. **Structured Instructions**
   - Step-by-step processes
   - Clear requirements
   
3. **Quality Constraints**
   - Focus on authoritative sources
   - Explicit quality standards
   
4. **Output Format**
   - Specified structure
   - Confidence levels
   - Source citations
   
5. **Contextual Information**
   - Age group awareness
   - Topic specification
   - Content context
   
6. **Source Citation**
   - Evidence required
   - URL tracking
   - Authority validation
   
7. **Transparency**
   - Limitation reporting
   - Uncertainty acknowledgment
   - Clear disclosures

📖 See: FACT_CHECK_README.md → "Prompt Engineering Best Practices"

---

## 🔗 Integration Points

### With Book Generator
```python
# Old way (no fact-checking)
chapter = await generate_chapter(book_agent, "Title", age_group)

# New way (with web search fact-checking)
chapter = await generate_chapter(book_agent, "Title", age_group)
verification = await fact_check_content(fact_check_agent, chapter)
```

### With Curriculum Agent
```python
# Generate curriculum
curriculum = await create_curriculum_agent()
lessons = await curriculum.generate_lessons()

# Verify accuracy
for lesson in lessons:
    verification = await fact_check_content(fact_check_agent, lesson)
```

### With Workflow
```python
# Full integrated workflow
results = await generate_and_fact_check_book(
    book_title="My Book",
    chapters=[...],
    enable_fact_checking=True  # Uses web search!
)
```

---

## ⚙️ Configuration Options

### Model Selection
```python
# Best for web search (recommended)
config = get_fact_check_config()  # Uses qwen3-max

# Or specify explicitly
agent = await create_fact_check_agent(use_qwen=True)
```

### Region Selection
```python
config = get_model_config(use_qwen=True, qwen_region="singapore")  # Default
config = get_model_config(use_qwen=True, qwen_region="beijing")
config = get_model_config(use_qwen=True, qwen_region="us-virginia")
```

### Environment Variables
```python
# Required
DASHSCOPE_API_KEY=sk-your_key_here

# Optional (default: singapore)
QWEN_REGION=singapore
```

---

## 🎯 Success Criteria Checklist

- [ ] DASHSCOPE_API_KEY is set
- [ ] verify_setup.py runs successfully
- [ ] Can create fact-check agent
- [ ] Can verify single claim with web search
- [ ] Can batch-check multiple claims
- [ ] Can verify chapter accuracy
- [ ] Can generate book with fact-checking
- [ ] Received fact-check reports with sources
- [ ] Age-appropriateness validation working
- [ ] Integration with existing workflow successful

---

## 🐛 Troubleshooting Quick Links

| Problem | Solution |
|---------|----------|
| API key not found | Set DASHSCOPE_API_KEY environment variable |
| Web search not working | Ensure using Qwen models, check internet |
| Model not found | Use qwen3-max, qwen3.5-plus, or qwen-plus |
| Slow responses | Web search adds latency; this is normal |
| Module import error | Ensure agent_framework is installed |

**For detailed troubleshooting:** See FACT_CHECK_README.md → Troubleshooting

---

## 📞 Getting Help

### Documentation
- **Quick Start:** FACT_CHECK_README.md
- **Code Examples:** agents/example_fact_checking.py
- **Copy-Paste Code:** QUICK_REFERENCE.py
- **Implementation Details:** fact_check_agent.py

### Setup & Configuration
- **DashScope API:** https://dashscope.aliyun.com/
- **Qwen Models:** https://qwen.aliyun.com/
- **Agent Framework:** Check agent_framework documentation

### Verification
- **Run:** `python verify_setup.py`
- **Test:** `python agents/example_fact_checking.py --example 1`

---

## 🚀 Next Actions

### Immediate (5 minutes)
1. Visit https://dashscope.aliyun.com/ and get free API key
2. Set DASHSCOPE_API_KEY environment variable
3. Run `python verify_setup.py`

### Short-term (30 minutes)
1. Run `python agents/example_fact_checking.py --example 1`
2. Read FACT_CHECK_README.md Quick Start section
3. Try Example 4 (Book with Fact-Checking)

### Medium-term (2 hours)
1. Study QUICK_REFERENCE.py for patterns
2. Integrate fact-checking into your workflow
3. Customize prompts for your use case

### Production (ongoing)
1. Monitor DashScope API usage
2. Track fact-check metrics
3. Refine prompts based on results
4. Scale to full curriculum

---

## 📈 Capabilities Overview

```
FACT-CHECKING AGENT CAPABILITIES

Web Search            ✅ Real-time verification
Confidence Levels     ✅ High/Medium/Low ratings
Source Citation       ✅ URLs and source tracking
Age-Appropriateness   ✅ Developmental validation
Batch Processing      ✅ Multiple claims at once
Chapter Verification  ✅ Full content checking
Book Integration      ✅ Workflow integration
Reporting             ✅ Comprehensive reports
Error Handling        ✅ Graceful failures
Configuration         ✅ Multiple regions/models
```

---

## 🎁 Bonus Features

- ✨ 6 practical examples ready to run
- ✨ Automated setup verification tool
- ✨ Color-coded terminal output
- ✨ Detailed error messages
- ✨ Performance optimization tips
- ✨ Troubleshooting guide
- ✨ Copy-paste code snippets
- ✨ Educational use case examples

---

## 📝 Summary

You now have a **complete, production-ready fact-checking system** that:

1. Uses **Qwen AI with real-time web search** to verify educational content
2. Provides **confidence levels and source citations** for transparency
3. **Integrates seamlessly** with your book generation workflow
4. **Implements best practices** in prompt engineering
5. Includes **comprehensive documentation** and examples
6. Offers **easy setup** in just 2 minutes
7. Provides **practical examples** for 6 common scenarios

---

## 🎉 You're Ready!

```
✅ Setup complete
✅ Documentation ready
✅ Examples available
✅ Integration possible
✅ Web search enabled

🚀 Start fact-checking with AI!
```

**Begin here:**
```bash
python verify_setup.py
```

Then:
```bash
python agents/example_fact_checking.py --example 1
```

---

**Happy fact-checking! 🔍✨**

For the latest updates and support, see FACT_CHECK_README.md

*Last updated: 2024*
*Version: 1.0 - Complete Implementation*
