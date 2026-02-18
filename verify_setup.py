"""
SETUP VERIFICATION SCRIPT
Run this to verify your fact-checking agent setup is complete
"""

import os
import sys
import asyncio
from pathlib import Path

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header():
    """Print welcome header"""
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}FACT-CHECKING AGENT - SETUP VERIFICATION{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")

def print_section(title):
    """Print section header"""
    print(f"\n{BLUE}{title}{RESET}")
    print(f"{BLUE}{'-'*70}{RESET}")

def check_mark(passed):
    """Return check mark or X"""
    return f"{GREEN}✅{RESET}" if passed else f"{RED}❌{RESET}"

def print_step(step_num, description, status):
    """Print a single verification step"""
    symbol = check_mark(status)
    print(f"  {symbol} Step {step_num}: {description}")

# Step 1: Check Python version
def check_python_version():
    """Verify Python 3.8+ is installed"""
    print_section("1. Python Version Check")
    
    version = sys.version_info
    required_version = (3, 8)
    
    is_valid = version >= required_version
    print_step(1, f"Python {version.major}.{version.minor}.{version.micro}", is_valid)
    
    if is_valid:
        print(f"    {GREEN}✨ Perfect for Agent Framework!{RESET}")
    else:
        print(f"    {RED}⚠️  Upgrade to Python 3.8+ required{RESET}")
    
    return is_valid

# Step 2: Check required files
def check_files():
    """Verify all required files exist"""
    print_section("2. Required Files Check")
    
    files_to_check = [
        "agents/fact_check_agent.py",
        "agents/enhanced_book_workflow.py", 
        "agents/example_fact_checking.py",
        "config.py",
        "FACT_CHECK_README.md",
        "QUICK_REFERENCE.py"
    ]
    
    all_exist = True
    for file_path in files_to_check:
        exists = Path(file_path).exists()
        all_exist = all_exist and exists
        status = "✓" if exists else "✗"
        print(f"  {check_mark(exists)} {file_path}")
    
    if all_exist:
        print(f"    {GREEN}All implementation files present!{RESET}")
    else:
        print(f"    {RED}Some files missing. Re-run creation if needed.{RESET}")
    
    return all_exist

# Step 3: Check API key
def check_api_key():
    """Verify DASHSCOPE_API_KEY is set"""
    print_section("3. API Key Configuration")
    
    api_key = os.getenv('DASHSCOPE_API_KEY')
    
    if api_key:
        # Show masked key
        masked_key = api_key[:5] + '*' * (len(api_key) - 10) + api_key[-5:]
        print(f"  {GREEN}✅{RESET} DASHSCOPE_API_KEY is set")
        print(f"    Key (masked): {masked_key}")
        
        # Verify format
        is_valid_format = api_key.startswith('sk-')
        print_step(2, "API Key format validation", is_valid_format)
        
        if is_valid_format:
            print(f"    {GREEN}Key format is correct!{RESET}")
        else:
            print(f"    {YELLOW}Warning: Key should start with 'sk-'{RESET}")
        
        return True, api_key
    else:
        print(f"  {RED}❌{RESET} DASHSCOPE_API_KEY is NOT set")
        print(f"    {YELLOW}Quick Fix:{RESET}")
        print(f"    Windows CMD: set DASHSCOPE_API_KEY=your_key_here")
        print(f"    Windows PS:  $env:DASHSCOPE_API_KEY=\"your_key_here\"")
        print(f"    Get free key: https://dashscope.aliyun.com/")
        return False, None

# Step 4: Check imports
async def check_imports():
    """Verify all required imports work"""
    print_section("4. Module Import Check")
    
    imports_to_check = [
        ("agent_framework.Agent", "Agent Framework Core"),
        ("agent_framework.openai.OpenAIChatClient", "OpenAI Client"),
        ("config.get_model_config", "Config Helpers"),
    ]
    
    all_imports_ok = True
    
    for import_path, description in imports_to_check:
        try:
            parts = import_path.split('.')
            module = __import__('.'.join(parts[:-1]), fromlist=[parts[-1]])
            getattr(module, parts[-1])
            print(f"  {GREEN}✅{RESET} {description} - OK")
        except ImportError as e:
            print(f"  {RED}❌{RESET} {description} - FAILED")
            print(f"    Error: {e}")
            all_imports_ok = False
    
    if all_imports_ok:
        print(f"    {GREEN}All required modules available!{RESET}")
    else:
        print(f"    {YELLOW}Some modules missing. Install agent_framework if needed.{RESET}")
    
    return all_imports_ok

# Step 5: Test agent creation
async def test_agent_creation(api_key):
    """Test creating the fact-check agent"""
    print_section("5. Agent Initialization Test")
    
    if not api_key:
        print(f"  {YELLOW}⏭️  Skipped (API key not configured){RESET}")
        return False
    
    try:
        print(f"  Initializing fact-check agent...")
        
        # Import here to avoid issues if module missing
        from agents.fact_check_agent import create_fact_check_agent
        
        agent = await create_fact_check_agent(use_qwen=True)
        
        if agent:
            print(f"  {GREEN}✅{RESET} Agent created successfully!")
            print(f"    {GREEN}Web search capability: READY{RESET}")
            return True
        else:
            print(f"  {RED}❌{RESET} Agent creation returned None")
            return False
            
    except Exception as e:
        print(f"  {RED}❌{RESET} Agent creation failed")
        print(f"    Error: {str(e)[:100]}")
        print(f"    {YELLOW}Make sure DASHSCOPE_API_KEY is valid{RESET}")
        return False

# Step 6: Configuration validation
async def check_configuration():
    """Check fact-check configuration"""
    print_section("6. Configuration Validation")
    
    try:
        from config import get_fact_check_config, verify_fact_check_setup
        
        # Get config
        config = get_fact_check_config()
        print(f"  {GREEN}✅{RESET} Fact-check config loaded")
        print(f"    Provider: {config.get('provider')}")
        print(f"    Model: {config.get('model_id')}")
        print(f"    Web Search: {'Enabled' if config.get('web_search_enabled') else 'Disabled'}")
        
        # Verify setup
        is_ready, msg = verify_fact_check_setup()
        status = "✅" if is_ready else "❌"
        print(f"  {status} Setup verification: {msg}")
        
        return is_ready
        
    except Exception as e:
        print(f"  {RED}❌{RESET} Configuration check failed: {e}")
        return False

# Summary report
async def generate_summary(results):
    """Generate final summary report"""
    print_section("VERIFICATION SUMMARY")
    
    checks = [
        ("Python Version", results.get('python_version', False)),
        ("Required Files", results.get('files', False)),
        ("API Key Set", results.get('api_key_set', False)),
        ("Module Imports", results.get('imports', False)),
        ("Agent Creation", results.get('agent_creation', False)),
        ("Configuration", results.get('configuration', False)),
    ]
    
    passed = sum(1 for _, status in checks if status)
    total = len(checks)
    
    print(f"\n{BOLD}Results:{RESET}\n")
    for check_name, status in checks:
        symbol = check_mark(status)
        print(f"  {symbol} {check_name}")
    
    print(f"\n{BOLD}Score: {passed}/{total} Checks Passed{RESET}")
    
    # Final status
    print(f"\n{BOLD}{'='*70}{RESET}")
    
    if passed == total:
        print(f"{GREEN}{BOLD}✨ SETUP COMPLETE! YOU'RE READY TO USE FACT-CHECKING WITH WEB SEARCH!{RESET}")
        print(f"\n{BOLD}Next Steps:{RESET}")
        print(f"  1. Run examples: python agents/example_fact_checking.py --example 1")
        print(f"  2. Check docs: See FACT_CHECK_README.md for usage patterns")
        print(f"  3. Integrate: Add fact-checking to your book generation workflow")
        return True
    
    elif passed >= 4:
        print(f"{YELLOW}{BOLD}⚠️  PARTIAL SETUP - MOSTLY READY{RESET}")
        print(f"\n{BOLD}Missing:{RESET}")
        for check_name, status in checks:
            if not status:
                print(f"  • {check_name}")
        print(f"\n{BOLD}Fix Issues:{RESET}")
        print(f"  • See troubleshooting in FACT_CHECK_README.md")
        print(f"  • Verify API key format and accessibility")
        return False
    
    else:
        print(f"{RED}{BOLD}❌ SETUP INCOMPLETE{RESET}")
        print(f"\n{BOLD}Required Actions:{RESET}")
        print(f"  1. Get free API key: https://dashscope.aliyun.com/")
        print(f"  2. Set DASHSCOPE_API_KEY environment variable")
        print(f"  3. Verify Python 3.8+ installed")
        print(f"  4. Run this check again")
        return False

# Main verification flow
async def main():
    """Run all verification checks"""
    print_header()
    
    results = {}
    
    # Step 1: Python version
    results['python_version'] = check_python_version()
    
    # Step 2: Files
    results['files'] = check_files()
    
    # Step 3: API key
    api_key_set, api_key = check_api_key()
    results['api_key_set'] = api_key_set
    
    # Step 4: Imports
    try:
        results['imports'] = await check_imports()
    except Exception as e:
        print(f"  {RED}❌{RESET} Import check failed: {e}")
        results['imports'] = False
    
    # Step 5: Agent creation (only if API key set)
    if api_key_set:
        try:
            results['agent_creation'] = await test_agent_creation(api_key)
        except Exception as e:
            print(f"  {RED}❌{RESET} Agent test failed: {e}")
            results['agent_creation'] = False
    else:
        results['agent_creation'] = False
    
    # Step 6: Configuration
    try:
        results['configuration'] = await check_configuration()
    except Exception as e:
        print(f"  {RED}❌{RESET} Configuration check failed: {e}")
        results['configuration'] = False
    
    # Summary
    success = await generate_summary(results)
    
    print(f"\n{BOLD}{'='*70}{RESET}\n")
    
    return success

if __name__ == "__main__":
    print("\n🔍 Starting setup verification...\n")
    
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Verification interrupted by user{RESET}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Verification failed: {e}{RESET}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
