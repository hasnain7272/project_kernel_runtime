import psutil
import subprocess
import os
from typing import Optional, Dict, Any
from project_kernel_runtime.memory.state_hub import state_hub

class InstanceManager:
    """
    Manages external application instances (Blender, Unity, Browsers) required for MCP tasks.
    """
    def __init__(self):
        self.app_registry = {
            "blender": {"proc_name": "blender", "path": "blender"},
            "browser": {"proc_name": "chrome", "path": "google-chrome"},
            "unity": {"proc_name": "unity", "path": "unity"}
        }

    def is_app_running(self, app_key: str) -> bool:
        """Check if a specific app is currently running on the host OS."""
        config = self.app_registry.get(app_key.lower())
        if not config:
            return False
            
        proc_name = config["proc_name"]
        for proc in psutil.process_iter(['name']):
            if proc_name in proc.info['name'].lower():
                return True
        return False

    def launch_app(self, app_key: str, custom_path: Optional[str] = None):
        """Autonomously launch a registered application."""
        config = self.app_registry.get(app_key.lower())
        if not config:
            state_hub.record_thought("InstanceManager", "Error", f"App '{app_key}' not in registry.")
            return False

        if self.is_app_running(app_key):
            state_hub.record_thought("InstanceManager", "Health", f"{app_key} is already running.")
            return True

        path = custom_path or config["path"]
        state_hub.record_thought("InstanceManager", "Action", f"Attempting to launch {app_key} from {path}...")
        try:
            subprocess.Popen([path], start_new_session=True)
            state_hub.record_thought("InstanceManager", "Success", f"{app_key} launch sequence initiated.")
            return True
        except Exception as e:
            state_hub.record_thought("InstanceManager", "Error", f"Failed to launch {app_key}: {str(e)}")
            return False

# Global Instance
instance_manager = InstanceManager()
