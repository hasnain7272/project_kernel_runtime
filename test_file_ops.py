"""
Simple test for governance and file operations.
"""
import asyncio
import os
import sys
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

os.environ.setdefault("OLLAMA_API_BASE", "http://127.0.0.1:11500")


async def test_file_ops():
    print("="*60)
    print("FILE OPERATIONS TEST")
    print("="*60)
    
    from cognition.llm_provider import LLMProvider, LLMMessage
    import yaml
    
    # Load yaml config
    with open("runtime.yaml") as f:
        yaml_config = yaml.safe_load(f)
    
    class Config:
        pass
    config = Config()
    config.active_model = yaml_config.get("llm", {}).get("active_model", "ollama/llama3.1:8b")
    config.model_router = yaml_config.get("llm", {}).get("model_router", {})
    config.nvidia_nim = yaml_config.get("llm", {}).get("nvidia_nim", {})
    config.providers = yaml_config.get("llm", {}).get("providers", [])
    
    provider = LLMProvider(config=config)
    
    print(f"\n[1] Config from YAML:")
    print(f"    NIM enabled: {provider.nvidia_nim_enabled}")
    print(f"    NIM base: {provider.nvidia_nim_base}")
    print(f"    NIM models: {provider.nvidia_nim_models}")
    
    # Test folder
    test_folder = Path(r"D:\AI_Content_Studio\ai_blender_cinematic\antigravity\session_test_folder1")
    test_folder.mkdir(parents=True, exist_ok=True)
    print(f"\n[2] Test folder: {test_folder}")
    
    # Test governance context
    from kernel.manager import get_manager
    
    manager = get_manager(provider, None)
    ctx = manager._build_env_context(
        folders=[str(test_folder)],
        skills=["python", "file_ops"],
        mcp_servers=[],
        workspace=str(test_folder)
    )
    
    print(f"\n[3] Governance context:")
    print(f"    {ctx}")
    
    # Test model routing
    model = manager._try_model_fallback("planning")
    print(f"\n[4] Model fallback for planning: {model}")
    
    # Test: ask LLM to create a file
    print(f"\n[5] Testing LLM with governance message:")
    response = await provider.complete(
        messages=[
            LLMMessage(role="system", content=ctx),
            LLMMessage(role="user", content="Create a hello.py file in the test folder with a print hello function")
        ],
        task_type="execution"
    )
    print(f"    Response: {response.content[:200]}...")
    print(f"    Model used: {response.model}")
    
    # Create test file directly
    hello_file = test_folder / "hello.py"
    hello_file.write_text("""def hello():
    print('Hello from governance test!')
    
if __name__ == '__main__':
    hello()
""")
    
    print(f"\n[6] File created: {hello_file}")
    print(f"    Exists: {hello_file.exists()}")
    
    return True


if __name__ == "__main__":
    asyncio.run(test_file_ops())
    print("\nTEST COMPLETE")