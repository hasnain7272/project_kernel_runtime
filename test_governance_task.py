"""
Test complex task with file operations and governance-aware execution.
"""
import asyncio
import os
import sys
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

os.environ.setdefault("OLLAMA_API_BASE", "http://127.0.0.1:11500")


async def test_complex_file_operations():
    """Test file operations with governance-aware path control."""
    print("="*60)
    print("COMPLEX TASK: Create Project with File Operations")
    print("="*60)
    
    # Test folder
    test_folder = Path(r"D:\AI_Content_Studio\ai_blender_cinematic\antigravity\session_test_folder1")
    
    # Ensure folder exists
    test_folder.mkdir(parents=True, exist_ok=True)
    print(f"\n[1] Test folder: {test_folder}")
    print(f"    Exists: {test_folder.exists()}")
    
    from cognition.llm_provider import LLMProvider, LLMMessage
    
    # Load runtime.yaml config
    import yaml
    config_path = Path("runtime.yaml")
    with open(config_path) as f:
        yaml_config = yaml.safe_load(f)
    
    llm_config = yaml_config.get("llm", {})
    
    class RuntimeConfig:
        pass
    config = RuntimeConfig()
    config.active_model = llm_config.get("active_model", "ollama/llama3.1:8b")
    config.model_router = llm_config.get("model_router", {})
    config.nvidia_nim = llm_config.get("nvidia_nim", {})
    config.providers = llm_config.get("providers", [])
    
    provider = LLMProvider(config=config)
    
    print(f"\n[2] Provider initialized")
    print(f"    Active model: {provider.active_model}")
    print(f"    NIM enabled: {provider.nvidia_nim_enabled}")
    
    # Test Governance Context with allowed folder
    from kernel.manager import ManagerAgent
    from kernel.tool_executor import ToolExecutor
    
    executor = ToolExecutor()
    manager = ManagerAgent.get_instance(llm_provider=provider, tool_executor=executor)
    
    # Get tool schemas (file operations)
    tool_schemas = manager._get_tool_schemas([])
    tool_names = [t.get('function', {}).get('name', '') for t in tool_schemas]
    print(f"\n[3] Available tools: {len(tool_schemas)}")
    for t in tool_names[:5]:
        print(f"    - {t}")
    
    # Task: Create a basic project in the test folder
    task = f"""Create a basic Python project in {test_folder}.
    Create these files:
    1. README.md with project description
    2. main.py with a simple hello world function
    3. requirements.txt with dependencies"""
    
    # Execute with governance context
    context = {
        "workspace_path": str(test_folder),
        "folders": [str(test_folder)],  # GOV: Only allow this folder
        "skills": ["file_operations", "python"],
        "mcp_servers": [],
    }
    
    print(f"\n[4] Executing task:")
    print(f"    Task: Create project in {test_folder.name}")
    print(f"    Allowed folders: {context['folders']}")
    
    try:
        result = await manager.execute(
            task=task,
            session_id="test-governance",
            context=context
        )
        
        print(f"\n[5] Result:")
        print(f"    Status: {result.get('status')}")
        print(f"    Iterations: {result.get('iterations')}")
        print(f"    Response: {result.get('response', '')[:300]}...")
        print(f"    Results: {len(result.get('results', []))} tools executed")
        
        # Check created files
        created_files = list(test_folder.glob("*"))
        print(f"\n[6] Files created in {test_folder.name}:")
        for f in created_files:
            print(f"    + {f.name}")
        
        return result.get('status') == 'completed'
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    try:
        success = await test_complex_file_operations()
        print("\n" + "="*60)
        print("COMPLEX TASK TEST: " + ("PASSED" if success else "FAILED"))
        print("="*60)
        return success
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)