"""
Project Kernel Runtime: Antigravity Agentic OS
Master Entry Point (Horizon 2028 Architecture)
"""

import argparse
import sys
from pathlib import Path

# Always insert src into path to ensure project_kernel_runtime is found globally
src_path = str(Path(__file__).parent.parent.absolute())
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from project_kernel_runtime.services.fastapi_server import run_server

def main():
    """Single Unified Pipeline Bootstrapper"""
    parser = argparse.ArgumentParser(description="Antigravity Agentic OS - Supervisor Runtime")
    parser.add_argument("--host", default="0.0.0.0", help="Host address for the REST/SSE/WebSocket gateway")
    parser.add_argument("--port", type=int, default=8089, help="Port for the FastAPI Edge Node")

    args = parser.parse_args()

    print(f"==================================================")
    print(f"🚀 Booting Antigravity Edge Node on {args.host}:{args.port}")
    print(f"==================================================")
    
    # Run the unified FastAPI server (which lazily boots the Coordinator sub-systems)
    run_server(host=args.host, port=args.port)

if __name__ == "__main__":
    main()