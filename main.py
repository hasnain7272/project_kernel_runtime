"""
Antigravity Runtime — Entry Point

Usage:
  python main.py                    # default: localhost:8089
  python main.py --port 9000        # custom port
  python main.py --reload           # hot-reload for development
"""
import argparse
import uvicorn
import os


def main():
    parser = argparse.ArgumentParser(description="Antigravity Runtime")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8089)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--no-worker", action="store_true", help="Disable background worker (stateless mode)")
    args = parser.parse_args()

    # Set hybrid mode based on user preference
    os.environ["HYBRID_MODE"] = "false" if args.no_worker else "true"

    banner_color = "\033[96m" if not args.no_worker else "\033[93m"
    mode_name = "HYBRID MODE (API + WORKER)" if not args.no_worker else "STATELESS MODE (API ONLY)"
    
    print(banner_color + "="*60)
    print(f"🚀 ANTIGRAVITY RUNTIME: {mode_name}")
    print("="*60)
    if not args.no_worker:
        print("Note: The agent worker is running in the background of this process.")
        print("For production scaling, use --no-worker and run workers separately.")
    else:
        print("⚠️  Process is API-only. Be sure to run workers separately.")
    print("="*60 + "\033[0m")

    uvicorn.run(
        "src.api.fastapi_gateway:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
