#!/usr/bin/env python3
"""Test script to find correct imports from agent_framework"""

import sys

try:
    # Try different import paths
    print("Attempting imports...")
    
    # Method 1: Direct Agent import
    try:
        from agent_framework import Agent
        print("✅ from agent_framework import Agent - SUCCESS")
    except ImportError as e:
        print(f"❌ from agent_framework import Agent - FAILED: {e}")
    
    # Method 2: From core
    try:
        from agent_framework.core import Agent
        print("✅ from agent_framework.core import Agent - SUCCESS")
    except ImportError as e:
        print(f"❌ from agent_framework.core import Agent - FAILED: {e}")
    
    # Method 3: Check what's available
    try:
        import agent_framework
        af_contents = [item for item in dir(agent_framework) if not item.startswith('_')]
        print(f"\nAvailable in agent_framework: {af_contents[:10]}")
    except Exception as e:
        print(f"Error checking agent_framework: {e}")
    
    # Method 4: Try OpenAI import
    try:
        from agent_framework.openai import OpenAIChatClient
        print("✅ from agent_framework.openai import OpenAIChatClient - SUCCESS")
    except ImportError as e:
        print(f"❌ from agent_framework.openai import OpenAIChatClient - FAILED: {e}")
        
    # Method 5: Check agent_framework submodules
    import pkgutil
    import agent_framework
    print("\nSubmodules in agent_framework:")
    for importer, modname, ispkg in pkgutil.iter_modules(agent_framework.__path__):
        print(f"  - {modname}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
