"""
Antigravity Runtime — Entry Point

Usage:
  python main.py                    # default: localhost:8089
  python main.py --port 9000        # custom port
  python main.py --reload           # hot-reload for development
"""
import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Antigravity Runtime")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8089)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run(
        "src.api.fastapi_gateway:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
