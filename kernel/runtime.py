"""
Project Kernel Runtime Configuration v2.0

Production-grade configuration system with:
- Pydantic v2 nested models for type-safe, validated config
- Environment variable overlay (YAML → env vars → CLI args)
- Hot-reload support via file watching
- Multi-environment profiles (development, staging, production)
- Schema version migration

Inspired by: Cursor's layered config, Claude Code's CLAUDE.md, OpenHands RuntimeProfile
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal, Any, Set
from enum import Enum
import yaml
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# Sub-Configuration Models
# ============================================================================

class GovernancePolicyMode(BaseModel):
    """Permission set for a specific execution mode."""
    read_only: bool = True
    write: bool = False
    execute: bool = False
    network: bool = False


class GovernanceConfig(BaseModel):
    """Governance and security policy configuration."""
    enabled: bool = True
    default_role: str = "developer"
    require_approval_for: List[str] = Field(
        default_factory=lambda: ["git_commit", "bash_execute"]
    )
    policy_matrix: Dict[str, GovernancePolicyMode] = Field(
        default_factory=lambda: {
            "plan": GovernancePolicyMode(read_only=True, write=False, execute=False, network=False),
            "review": GovernancePolicyMode(read_only=True, write=False, execute=False, network=False),
            "research": GovernancePolicyMode(read_only=True, write=False, execute=False, network=True),
            "build": GovernancePolicyMode(read_only=True, write=True, execute=True, network=True),
        }
    )
    network_allowlist: List[str] = Field(
        default_factory=lambda: [
            "api.openai.com", "api.anthropic.com",
            "pypi.org", "registry.npmjs.org",
            "github.com", "api.github.com",
        ]
    )
    audit_log_enabled: bool = True
    audit_log_path: str = "./data/audit.db"
    max_tool_timeout_seconds: int = 300
    agentrules_filename: str = ".agentrules"


class MCPConfig(BaseModel):
    """MCP (Model Context Protocol) server/client configuration."""
    enabled: bool = True
    transport: Literal["stdio", "streamable_http", "websocket"] = "streamable_http"
    host: str = "0.0.0.0"
    port: int = 8090
    protocol_versions: List[str] = Field(
        default_factory=lambda: ["2025-03-26", "2024-11-05"]
    )
    session_timeout_seconds: int = 3600
    max_sessions: int = 100
    tools_enabled: bool = True
    resources_enabled: bool = True
    prompts_enabled: bool = True
    sampling_enabled: bool = False


class SandboxConfig(BaseModel):
    """Sandbox and execution isolation configuration."""
    backend: Literal["subprocess", "docker", "e2b", "none"] = "subprocess"
    docker_image: str = "python:3.11-slim"
    memory_limit_mb: int = 512
    cpu_limit: float = 1.0
    network_mode: Literal["none", "allowlist", "full"] = "none"
    network_allowlist: List[str] = Field(default_factory=list)
    timeout_seconds: int = 300
    working_dir: str = "./workspace"
    max_concurrent_sandboxes: int = 5
    cleanup_on_exit: bool = True


class LLMProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""
    name: str
    api_key_env: str = ""
    base_url: Optional[str] = None
    default_model: str = ""
    max_tokens: int = 8192
    temperature: float = 0.1
    enabled: bool = True
    priority: int = 0  # Lower = higher priority


class LLMConfig(BaseModel):
    """LLM provider system configuration."""
    active_model: str = "ollama/qwen2.5-coder:7b-instruct-q4_K_M"
    providers: List[LLMProviderConfig] = Field(
        default_factory=lambda: [
            LLMProviderConfig(
                name="ollama", base_url="http://127.0.0.1:11500",
                default_model="ollama/qwen2.5-coder:7b-instruct-q4_K_M", priority=0
            ),
            LLMProviderConfig(
                name="anthropic", api_key_env="ANTHROPIC_API_KEY",
                default_model="claude-sonnet-4-20250514", priority=1
            ),
            LLMProviderConfig(
                name="openai", api_key_env="OPENAI_API_KEY",
                default_model="gpt-4o", priority=2
            ),
        ]
    )
    model_router: Dict[str, str] = Field(
        default_factory=lambda: {
            "autocomplete": "ollama/qwen2.5-coder:7b-instruct-q4_K_M",
            "code_generation": "ollama/qwen2.5-coder:7b-instruct-q4_K_M",
            "architecture": "ollama/qwen2.5-coder:7b-instruct-q4_K_M",
            "research": "ollama/qwen2.5-coder:7b-instruct-q4_K_M",
        }
    )
    fallback_enabled: bool = True
    max_retries: int = 3
    rate_limit_rpm: int = 60
    cost_tracking_enabled: bool = True


class VectorDBConfig(BaseModel):
    """Vector database / agent memory configuration."""
    backend: Literal["chromadb", "qdrant", "none"] = "chromadb"
    persist_dir: str = "./data/chroma_db"
    collection_name: str = "agent_memory"
    embedding_model: str = "all-MiniLM-L6-v2"
    max_results: int = 10
    enable_codebase_rag: bool = True
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 50


class A2AConfig(BaseModel):
    """Google A2A (Agent-to-Agent) protocol configuration."""
    enabled: bool = True
    agent_name: str = "Antigravity Kernel"
    agent_description: str = "Production-grade AI coding agent kernel"
    endpoint_url: str = "http://localhost:8089"
    version: str = "0.3"
    authentication: Literal["none", "api_key", "oauth2"] = "api_key"
    discoverable: bool = True


class ObservabilityConfig(BaseModel):
    """Observability, logging, and monitoring configuration."""
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "text"] = "json"
    metrics_enabled: bool = True
    metrics_port: int = 9090
    tracing_enabled: bool = False
    tracing_endpoint: str = ""
    health_check_interval_seconds: int = 30


class SkillsConfig(BaseModel):
    """Skills registry configuration."""
    core: List[str] = Field(
        default_factory=lambda: [
            "file_operations", "terminal_execution", "git_operations",
            "lsp_integration", "error_recovery", "browser_automation",
            "web_search", "custom_tools"
        ]
    )
    domain: List[str] = Field(
        default_factory=lambda: ["blender", "coding", "research"]
    )
    auto_discover: bool = True


class FeaturesConfig(BaseModel):
    """Feature flags for optional subsystems."""
    gtm_swarm: bool = False
    vision_swarm: bool = False
    federated_hub: bool = False
    mesh_p2p: bool = False
    sre_swarm: bool = True
    credits_engine: bool = False
    multi_tenancy: bool = False
    skill_compiler: bool = True
    predictive: bool = True
    wasm_driver: bool = False
    self_attention: bool = True


class ServerConfig(BaseModel):
    """HTTP server configuration."""
    host: str = "0.0.0.0"
    port: int = 8089
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    api_key_header: str = "X-API-Key"
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 120
    static_files_dir: str = "ui/web"


# ============================================================================
# Main Runtime Config
# ============================================================================

class RuntimeConfig(BaseModel):
    """
    Root configuration model for the Antigravity Project Kernel Runtime.
    
    Supports layered loading: YAML file → environment variables → CLI args.
    All subsections are validated Pydantic models with sensible defaults.
    """
    version: str = "2.0.0"
    api_version: str = "2026-03"
    mode: Literal["development", "staging", "production"] = "development"
    
    # Deployment modes supported
    modes: List[str] = Field(default_factory=lambda: ["http", "cli", "mcp"])
    workspace_adapters: List[str] = Field(
        default_factory=lambda: ["local", "git_worktree", "containerized"]
    )
    
    # Subsystem configurations
    governance: GovernanceConfig = Field(default_factory=GovernanceConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    a2a: A2AConfig = Field(default_factory=A2AConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    
    # Data directory for persistent storage
    data_dir: str = "./data"
    
    @classmethod
    def from_yaml(cls, path: str = "runtime.yaml") -> "RuntimeConfig":
        """Load configuration from YAML file with fallback to defaults."""
        # Try relative to this file first, then absolute
        search_paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), path),
            os.path.join(os.path.dirname(__file__), path),
            path,
        ]
        
        for full_path in search_paths:
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r") as f:
                        data = yaml.safe_load(f) or {}
                    
                    # Handle v1 → v2 migration
                    data = cls._migrate_v1_to_v2(data)
                    
                    config = cls(**data)
                    logger.info(f"Loaded config v{config.version} from {full_path}")
                    return config
                except Exception as e:
                    logger.warning(f"Failed to load config from {full_path}: {e}")
                    logger.info("Falling back to defaults")
        
        logger.info("No config file found, using defaults")
        return cls()
    
    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        """
        Load from environment variables overlaid on YAML config.
        
        Environment variables follow the pattern:
            PKR_<SECTION>_<KEY>=value
        
        Examples:
            PKR_MODE=production
            PKR_SERVER_PORT=9000
            PKR_SANDBOX_BACKEND=docker
            PKR_LLM_ACTIVE_MODEL=claude-sonnet-4-20250514
            PKR_OBSERVABILITY_LOG_LEVEL=DEBUG
        """
        # Start from YAML
        config_dict = cls.from_yaml().model_dump()
        
        # Overlay environment variables
        env_prefix = "PKR_"
        for key, value in os.environ.items():
            if not key.startswith(env_prefix):
                continue
            
            parts = key[len(env_prefix):].lower().split("_", 1)
            
            if len(parts) == 1:
                # Top-level key: PKR_MODE=production
                config_dict[parts[0]] = cls._parse_env_value(value)
            elif len(parts) == 2:
                section, subkey = parts
                if section in config_dict and isinstance(config_dict[section], dict):
                    config_dict[section][subkey] = cls._parse_env_value(value)
        
        return cls(**config_dict)
    
    @classmethod
    def _migrate_v1_to_v2(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate v1 YAML config to v2 schema."""
        version = data.get("version", "1.0.0")
        if version.startswith("2."):
            return data  # Already v2
        
        logger.info(f"Migrating config from v{version} to v2.0.0")
        migrated = dict(data)
        migrated["version"] = "2.0.0"
        migrated["api_version"] = "2026-03"
        
        # v1 had flat llm_providers list → v2 has nested LLMConfig
        if "llm_providers" in migrated and isinstance(migrated["llm_providers"], list):
            provider_names = migrated.pop("llm_providers")
            migrated.setdefault("llm", {})
            # Keep active_model if present
            if "active_model" in migrated:
                migrated["llm"]["active_model"] = migrated.pop("active_model")
        
        # v1 had flat network fields → v2 nests under governance
        if "allow_network" in migrated:
            migrated.pop("allow_network")
        if "network_allowlist" in migrated:
            migrated.setdefault("governance", {})
            migrated["governance"]["network_allowlist"] = migrated.pop("network_allowlist")
        
        return migrated
    
    @staticmethod
    def _parse_env_value(value: str) -> Any:
        """Parse environment variable values into appropriate Python types."""
        # Boolean
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
        # Integer
        try:
            return int(value)
        except ValueError:
            pass
        # Float
        try:
            return float(value)
        except ValueError:
            pass
        # List (comma-separated)
        if "," in value:
            return [v.strip() for v in value.split(",")]
        # String
        return value
    
    def save_yaml(self, path: str) -> None:
        """Save current config to YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False, sort_keys=False)
        logger.info(f"Saved config to {path}")
    
    def ensure_data_dirs(self) -> None:
        """Create required data directories."""
        dirs = [
            self.data_dir,
            os.path.dirname(self.governance.audit_log_path),
            self.vector_db.persist_dir,
            self.sandbox.working_dir,
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)


# ============================================================================
# Backward Compatibility: RuntimeProfile alias
# ============================================================================

class RuntimeProfile(RuntimeConfig):
    """
    Backward-compatible alias for RuntimeConfig.
    
    Existing code that imports RuntimeProfile will continue to work.
    New code should use RuntimeConfig directly.
    """
    pass


# ============================================================================
# Config hot-reload watcher (optional, requires watchfiles)
# ============================================================================

class ConfigWatcher:
    """
    Watches runtime.yaml for changes and triggers reload callback.
    
    Usage:
        watcher = ConfigWatcher("runtime.yaml", on_config_change)
        await watcher.start()
    """
    
    def __init__(self, config_path: str, callback):
        self.config_path = config_path
        self.callback = callback
        self._running = False
    
    async def start(self):
        """Start watching for config changes."""
        try:
            from watchfiles import awatch
        except ImportError:
            logger.warning("watchfiles not installed, config hot-reload disabled")
            return
        
        self._running = True
        logger.info(f"Watching {self.config_path} for changes")
        
        async for changes in awatch(self.config_path):
            if not self._running:
                break
            try:
                new_config = RuntimeConfig.from_yaml(self.config_path)
                await self.callback(new_config)
                logger.info("Config hot-reloaded successfully")
            except Exception as e:
                logger.error(f"Config hot-reload failed: {e}")
    
    def stop(self):
        """Stop watching."""
        self._running = False