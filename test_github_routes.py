"""Quick test for GitHub routes."""
import httpx
import asyncio

async def test_routes():
    """Test if GitHub routes are accessible."""
    async with httpx.AsyncClient(base_url="http://localhost:8089") as client:
        # Test health endpoint
        resp = await client.get("/health")
        print(f"Health: {resp.status_code} - {resp.json()}")
        
        # Test OpenAPI docs
        resp = await client.get("/api/docs")
        print(f"Docs: {resp.status_code}")
        
        # Check if GitHub routes exist
        from src.api.fastapi_gateway import app
        routes = [route.path for route in app.routes]
        
        github_routes = [r for r in routes if "/github" in r]
        print(f"\nGitHub routes found:")
        for route in github_routes:
            print(f"  - {route}")

if __name__ == "__main__":
    asyncio.run(test_routes())