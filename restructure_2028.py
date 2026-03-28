import os
import shutil
import glob

base_dir = r"D:\AI_Content_Studio\ai_blender_cinematic\antigravity\blender-mcp-server\src\project_kernel_runtime"

new_dirs = ['agents', 'cognition', 'memory', 'protocols', 'kernel']
for d in new_dirs:
    os.makedirs(os.path.join(base_dir, d), exist_ok=True)

# File mappings
moves = {
    # Agents
    r"core\vision_swarm.py": r"agents\vision_swarm.py",
    r"core\sre_swarm.py": r"agents\sre_swarm.py",
    r"core\watchdog.py": r"agents\watchdog.py",
    r"core\growth_swarm": r"agents\growth_swarm",
    
    # Cognition
    r"core\llm_provider.py": r"cognition\llm_provider.py",
    r"core\self_attention.py": r"cognition\self_attention.py",
    r"core\context_cluster.py": r"cognition\context_cluster.py",
    
    # Memory
    r"vector_db\base.py": r"memory\chroma_store.py",
    r"core\state_hub.py": r"memory\state_hub.py",
    
    # Protocols
    r"core\mcp_client.py": r"protocols\mcp_client.py",
    r"core\mcp_server.py": r"protocols\mcp_server.py",
    r"core\mesh_p2p.py": r"protocols\mesh_p2p.py",
    r"core\federated_hub.py": r"protocols\federated_hub.py",
}

# Perform precise moves
for src, dst in moves.items():
    src_path = os.path.join(base_dir, src)
    dst_path = os.path.join(base_dir, dst)
    if os.path.exists(src_path):
        if os.path.isdir(src_path):
            if os.path.exists(dst_path):
                shutil.rmtree(dst_path)
            shutil.move(src_path, dst_path)
        else:
            shutil.move(src_path, dst_path)
            print(f"Moved {src} -> {dst}")

# Move the rest of `core` to `kernel`
core_dir = os.path.join(base_dir, "core")
kernel_dir = os.path.join(base_dir, "kernel")
if os.path.exists(core_dir):
    for item in os.listdir(core_dir):
        # Ignore redundant folders to delete later
        if item in ['providers', '__pycache__']: continue
        s = os.path.join(core_dir, item)
        d = os.path.join(kernel_dir, item)
        if not os.path.exists(d):
            shutil.move(s, d)

# Delete redundant leftovers
for trash in ["llm_providers", "core", "vector_db"]:
    p = os.path.join(base_dir, trash)
    if os.path.exists(p):
        shutil.rmtree(p)
        print(f"Deleted pristine garbage: {trash}")

# Now, we must update imports across all .py files.
import_maps = {
    # Replace the moved explicit ones
    "project_kernel_runtime.memory.chroma_store": "project_kernel_runtime.memory.chroma_store",
    "project_kernel_runtime.memory.state_hub": "project_kernel_runtime.memory.state_hub",
    "project_kernel_runtime.cognition.llm_provider": "project_kernel_runtime.cognition.llm_provider",
    "project_kernel_runtime.cognition.self_attention": "project_kernel_runtime.cognition.self_attention",
    "project_kernel_runtime.cognition.context_cluster": "project_kernel_runtime.cognition.context_cluster",
    "project_kernel_runtime.protocols.mcp_client": "project_kernel_runtime.protocols.mcp_client",
    "project_kernel_runtime.protocols.mcp_server": "project_kernel_runtime.protocols.mcp_server",
    "project_kernel_runtime.protocols.mesh_p2p": "project_kernel_runtime.protocols.mesh_p2p",
    "project_kernel_runtime.protocols.federated_hub": "project_kernel_runtime.protocols.federated_hub",
    "project_kernel_runtime.agents.vision_swarm": "project_kernel_runtime.agents.vision_swarm",
    "project_kernel_runtime.agents.sre_swarm": "project_kernel_runtime.agents.sre_swarm",
    "project_kernel_runtime.agents.watchdog": "project_kernel_runtime.agents.watchdog",
    "project_kernel_runtime.agents.growth_swarm": "project_kernel_runtime.agents.growth_swarm",
    
    # Generic replacement for everything else that was core -> kernel
    "project_kernel_runtime.kernel.": "project_kernel_runtime.kernel.",
    "project_kernel_runtime.kernel import": "project_kernel_runtime.kernel import"
}

all_py_files = glob.glob(os.path.join(base_dir, "**", "*.py"), recursive=True)
for py_file in all_py_files:
    with open(py_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    new_content = content
    for old_mod, new_mod in import_maps.items():
        new_content = new_content.replace(old_mod, new_mod)
        
    if new_content != content:
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated imports in {os.path.basename(py_file)}")

print("Horizon 2028 Ascension Restructuring Complete.")
