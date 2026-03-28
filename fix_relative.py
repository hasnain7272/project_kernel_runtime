import os
import re

kernel_dir = r"D:\AI_Content_Studio\ai_blender_cinematic\antigravity\blender-mcp-server\src\project_kernel_runtime\kernel"
base_pkg = "project_kernel_runtime"

# Things ripped out of kernel -> where they live now
moves_map = {
    "vision_swarm": "agents.vision_swarm",
    "sre_swarm": "agents.sre_swarm",
    "watchdog": "agents.watchdog",
    "growth_swarm": "agents.growth_swarm",
    "llm_provider": "cognition.llm_provider",
    "self_attention": "cognition.self_attention",
    "context_cluster": "cognition.context_cluster",
    "chroma_store": "memory.chroma_store",
    "state_hub": "memory.state_hub",
    "mcp_client": "protocols.mcp_client",
    "mcp_server": "protocols.mcp_server",
    "mesh_p2p": "protocols.mesh_p2p",
    "federated_hub": "protocols.federated_hub"
}

import glob
for py_file in glob.glob(os.path.join(kernel_dir, "*.py")):
    with open(py_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    new_content = content
    # Look for `from .<module_name> import ...`
    for old_name, new_path in moves_map.items():
        # Replace `from .llm_provider import ` with `from project_kernel_runtime.cognition.llm_provider import `
        new_content = re.sub(
            r"from \." + old_name + r"\b",
            f"from {base_pkg}.{new_path}",
            new_content
        )
        
        # Also fix absolute imports that were accidentally changed to kernel by my previous script
        # My previous script did `core` -> `kernel` globally.
        # So `from project_kernel_runtime.kernel.llm_provider import ...`
        bad_abs = f"from {base_pkg}.kernel.{old_name}"
        good_abs = f"from {base_pkg}.{new_path}"
        new_content = new_content.replace(bad_abs, good_abs)
        
        bad_import = f"import {base_pkg}.kernel.{old_name}"
        good_import = f"import {base_pkg}.{new_path}"
        new_content = new_content.replace(bad_import, good_import)

    if new_content != content:
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Fixed relative imports in {os.path.basename(py_file)}")
