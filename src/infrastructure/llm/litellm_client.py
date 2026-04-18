"""
LiteLLM Adapter

Provides a fault-tolerant, resilient interface to foundational models
with built-in retry and fallback logic.
"""
import logging
from typing import List, Dict, Any, Optional

from src.domain.exceptions import BaseDomainError

logger = logging.getLogger(__name__)

class LLMExecutionError(BaseDomainError):
    pass

class LLMClient:
    def __init__(self, primary_model: str = "gpt-4o", fallback_model: str = "claude-3-5-sonnet-20240620"):
        self.primary_model = primary_model
        self.fallback_model = fallback_model

    async def generate(self, messages: List[Dict[str, str]], tools: Optional[List[Dict]] = None, temperature: float = 0.2, api_key: Optional[str] = None) -> Any:
        try:
            import litellm
            # litellm requires the model name as the first positional or kwarg correctly styled
            litellm.set_verbose = False
            
            completion_kwargs = {
                "model": self.primary_model,
                "messages": messages,
                "tools": tools,
                "temperature": temperature,
                "fallbacks": [{"model": self.fallback_model}],
                "num_retries": 3,
            }
            if api_key:
                completion_kwargs["api_key"] = api_key
            
            response = await litellm.acompletion(**completion_kwargs)
            return response
            
        except ImportError:
            raise LLMExecutionError("litellm package not installed.")
        except Exception as e:
            logger.error(f"LLM Generation failed entirely: {str(e)}")
            raise LLMExecutionError(f"Failed to communicate with LLM: {str(e)}")
