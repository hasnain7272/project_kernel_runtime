"""
Real integration tests for the Project Kernel Runtime system.
Tests actual LLM calls and agentic execution flows.
"""
import asyncio
import os
import sys
import json

# Setup path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Ensure Ollama env is set
os.environ.setdefault("OLLAMA_API_BASE", "http://127.0.0.1:11500")


async def test_simple_qa():
    """Test 1: Simple Q&A - should bypass tool loop and answer directly."""
    print("\n" + "="*60)
    print("TEST 1: Simple Q&A Flow (No Tools Required)")
    print("="*60)
    
    from cognition.llm_provider import LLMProvider, LLMMessage
    
    provider = LLMProvider()
    print(f"Provider initialized: {provider.active_model}")
    
    # Test direct LLM call
    response = await provider.complete(
        messages=[LLMMessage(role="user", content="What is 5 + 5?")],
        task_type="auto"
    )
    print(f"\nDirect LLM Response: {response.content}")
    print(f"Model: {response.model}, Provider: {response.provider}")
    print(f"Finish reason: {response.finish_reason}")
    
    # Test via Manager
    from kernel.manager import ManagerAgent
    
    manager = ManagerAgent.get_instance(llm_provider=provider)
    
    result = await manager.execute(
        task="What is 2+2?",
        session_id="test-simple-qa",
        context={}
    )
    
    print(f"\nManager Result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Response: {result.get('response')}")
    print(f"  Iterations: {result.get('iterations')}")
    print(f"  Plan complexity: {result.get('plan', {}).get('complexity')}")
    
    passed = result.get('status') == 'completed' and result.get('iterations', 999) <= 2
    print(f"\n✅ PASSED" if passed else f"\n❌ FAILED")
    return passed


async def test_complex_task():
    """Test 2: Complex task with tool execution."""
    print("\n" + "="*60)
    print("TEST 2: Complex Task with Tool Execution")
    print("="*60)
    
    from cognition.llm_provider import LLMProvider
    from kernel.manager import ManagerAgent
    from kernel.tool_executor import ToolExecutor
    
    provider = LLMProvider()
    
    # Create tool executor with file tools
    executor = ToolExecutor()
    
    manager = ManagerAgent.get_instance(
        llm_provider=provider, 
        tool_executor=executor
    )
    
    # Test: List files in current directory (requires tool)
    result = await manager.execute(
        task="List the files in the current directory",
        session_id="test-complex",
        context={"workspace_path": project_root}
    )
    
    print(f"\nManager Result:")
    print(f"  Status: {result.get('status')}")
    print(f"  Response: {result.get('response')[:200]}...")
    print(f"  Iterations: {result.get('iterations')}")
    print(f"  Results count: {len(result.get('results', []))}")
    print(f"  Plan: {result.get('plan', {}).get('complexity')}")
    
    passed = result.get('status') == 'completed'
    print(f"\n✅ PASSED" if passed else f"\n❌ FAILED")
    return passed


async def test_llm_message_handling():
    """Test 3: LLM message handling with both dict and LLMMessage objects."""
    print("\n" + "="*60)
    print("TEST 3: LLM Message Handling (dict + object mixed)")
    print("="*60)
    
    from cognition.llm_provider import LLMProvider, LLMMessage
    
    provider = LLMProvider()
    
    # Test with mixed message types (simulating session history with dicts)
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, who are you?"},
        LLMMessage(role="assistant", content="I am an AI assistant."),
        LLMMessage(role="user", content="What can you do?"),
    ]
    
    try:
        response = await provider.complete(messages=messages, task_type="auto")
        print(f"\nResponse: {response.content[:100]}...")
        print(f"Model: {response.model}")
        
        # Test the _messages_to_dicts method directly
        dicts = provider._messages_to_dicts(messages)
        print(f"\nConverted {len(messages)} messages to {len(dicts)} dicts")
        
        passed = len(dicts) == 4
        print(f"\n✅ PASSED" if passed else f"\n❌ FAILED")
        return passed
    except Exception as e:
        print(f"\n❌ FAILED with error: {e}")
        return False


async def test_verification_flow():
    """Test 4: Manager verification flow."""
    print("\n" + "="*60)
    print("TEST 4: Manager Verification Flow")
    print("="*60)
    
    from cognition.llm_provider import LLMProvider
    from kernel.manager import ManagerAgent
    
    provider = LLMProvider()
    manager = ManagerAgent.get_instance(llm_provider=provider)
    
    # Get tool schemas
    tool_schemas = manager._get_tool_schemas([])
    print(f"Available tools: {len(tool_schemas)}")
    
    # Test verification manually
    result = await manager._verify_completion(
        task="Say hello",
        response="Hello! I have completed the task.",
        workspace=project_root,
        tool_schemas=tool_schemas,
        session_id=None,
        context={}
    )
    
    print(f"\nVerification Result:")
    print(f"  Passed: {result.get('passed')}")
    print(f"  Reason: {result.get('reason')}")
    
    passed = 'passed' in result
    print(f"\n✅ PASSED" if passed else f"\n❌ FAILED")
    return passed


async def test_nvidia_nim_config():
    """Test 5: NVIDIA NIM configuration check."""
    print("\n" + "="*60)
    print("TEST 5: NVIDIA NIM Configuration")
    print("="*60)
    
    from cognition.llm_provider import LLMProvider
    
    # Set test environment variables
    os.environ["NVIDIA_NIM_API_KEY"] = "test-key-12345"
    os.environ["NVIDIA_NIM_BASE"] = "https://api.nvidia.ai"
    
    provider = LLMProvider()
    
    print(f"NIM enabled: {provider.nvidia_nim_enabled}")
    print(f"NIM base URL: {provider.nvidia_nim_base}")
    print(f"NIM API key set: {bool(provider.nvidia_nim_api_key)}")
    
    # Test model selection for complex tasks
    model = provider.get_model_for_task("planning")
    print(f"Model for 'planning' task: {model}")
    
    should_use = provider.should_use_external_api("research")
    print(f"Should use external API for 'research': {should_use}")
    
    passed = provider.nvidia_nim_enabled == False and provider.nvidia_nim_base == "https://api.nvidia.ai"
    print(f"\n✅ PASSED" if passed else f"\n❌ FAILED")
    return passed


async def main():
    print("="*60)
    print("PROJECT KERNEL RUNTIME - REAL INTEGRATION TESTS")
    print("="*60)
    
    results = {}
    
    # Run all tests
    try:
        results['simple_qa'] = await test_simple_qa()
    except Exception as e:
        print(f"Test 1 failed with exception: {e}")
        results['simple_qa'] = False
    
    try:
        results['complex_task'] = await test_complex_task()
    except Exception as e:
        print(f"Test 2 failed with exception: {e}")
        results['complex_task'] = False
    
    try:
        results['message_handling'] = await test_llm_message_handling()
    except Exception as e:
        print(f"Test 3 failed with exception: {e}")
        results['message_handling'] = False
    
    try:
        results['verification'] = await test_verification_flow()
    except Exception as e:
        print(f"Test 4 failed with exception: {e}")
        results['verification'] = False
    
    try:
        results['nvidia_nim'] = await test_nvidia_nim_config()
    except Exception as e:
        print(f"Test 5 failed with exception: {e}")
        results['nvidia_nim'] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    for name, result in results.items():
        print(f"  {'✅' if result else '❌'} {name}")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)