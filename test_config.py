import asyncio
import os
from src.infrastructure.db.session import AsyncSessionLocal
from src.services.agent_loop.brain.config_loader import load_session_llm_config
from src.infrastructure.db.models.tenant_model import TenantModel

def mask_secrets(value):
    if isinstance(value, dict):
        return {k: ("***" if "key" in k.lower() else mask_secrets(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [mask_secrets(item) for item in value]
    return value

async def test():
    async with AsyncSessionLocal() as session:
        from src.infrastructure.db.models.session_model import SessionModel
        from sqlalchemy import select
        
        result = await session.execute(select(SessionModel).order_by(SessionModel.created_at.desc()).limit(1))
        s = result.scalar_one_or_none()
        if s:
            print("====================================")
            print(f"Testing session: {s.id}")
            print(f"Tenant ID: {s.tenant_id}")
            
            # Mocking context with no active_model_id (should default to first configured config)
            s.context = {}
            cfg_default = await load_session_llm_config(session, s.id, s)
            print("\n1. Loaded config with empty context (should select first configured, 'openai'):")
            print("   Model:", cfg_default.get("model"))
            print("   Base URL:", cfg_default.get("base_url"))
            print("   API Key:", "Found!" if cfg_default.get("api_key") else "None")
            
            # Mocking context with configured active_model_id = 'openai'
            s.context = {"active_model_id": "openai"}
            cfg_configured = await load_session_llm_config(session, s.id, s)
            print("\n2. Loaded config with active_model_id='openai' (explicitly configured):")
            print("   Model:", cfg_configured.get("model"))
            print("   Base URL:", cfg_configured.get("base_url"))
            print("   API Key:", "Found!" if cfg_configured.get("api_key") else "None")
            
            # Mocking context with unconfigured preset 'nvidia-minimax'
            s.context = {"active_model_id": "nvidia-minimax"}
            os.environ["NVIDIA_API_KEY"] = "mock_nvidia_key"
            cfg_unconfigured = await load_session_llm_config(session, s.id, s)
            print("\n3. Loaded config with active_model_id='nvidia-minimax' (unconfigured preset, should resolve default minimax):")
            print("   Model:", cfg_unconfigured.get("model"))
            print("   Base URL:", cfg_unconfigured.get("base_url"))
            print("   API Key:", "Found! (Value: " + cfg_unconfigured.get("api_key") + ")" if cfg_unconfigured.get("api_key") else "None")
            
            print("====================================")

asyncio.run(test())
