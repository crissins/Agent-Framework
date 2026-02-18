#!/usr/bin/env python3
from agent_framework.openai import OpenAIChatClient
import inspect

print("=== OpenAIChatClient Methods ===")
methods = [m for m in dir(OpenAIChatClient) if not m.startswith('_')]
for method in methods:
    print(f"  - {method}")

# Check specific methods
if hasattr(OpenAIChatClient, 'as_agent'):
    print("\n✅ as_agent method EXISTS")
    sig = inspect.signature(OpenAIChatClient.as_agent)
    print(f"Signature: {sig}")
else:
    print("\n❌ as_agent method NOT FOUND")

# Try to understand the ChatAgent API
print("\n=== Checking ChatAgent ===")
from agent_framework import ChatAgent
print("ChatAgent found!")
print(f"ChatAgent signature: {inspect.signature(ChatAgent.__init__)}")
