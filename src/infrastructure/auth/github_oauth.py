"""GitHub OAuth Integration - Session-based authentication."""
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import httpx
from fastapi import HTTPException, status
from src.infrastructure.security.crypto import encrypt_string, decrypt_string

logger = logging.getLogger(__name__)

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"


@dataclass
class GitHubUser:
    id: int
    login: str
    name: Optional[str]
    email: Optional[str]
    avatar_url: Optional[str]
    access_token: str


class GitHubOAuthClient:
    """GitHub OAuth flow handler."""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        
    def get_auth_url(self, state: str, redirect_uri: str) -> str:
        """Generate GitHub authorization URL."""
        scopes = "repo user:email"
        return f"{GITHUB_AUTH_URL}?client_id={self.client_id}&redirect_uri={redirect_uri}&scope={scopes}&state={state}"
    
    async def exchange_code(self, code: str, redirect_uri: str) -> GitHubUser:
        """Exchange OAuth code for access token."""
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                }
            )
            
            if token_resp.status_code != 200:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub auth failed")
            
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No access token")
            
            user_resp = await client.get(
                f"{GITHUB_API_URL}/user",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"}
            )
            
            user_data = user_resp.json()
            
            return GitHubUser(
                id=user_data["id"],
                login=user_data["login"],
                name=user_data.get("name"),
                email=user_data.get("email"),
                avatar_url=user_data.get("avatar_url"),
                access_token=encrypt_string(access_token)
            )
    
    async def list_repos(self, encrypted_token: str, page: int = 1) -> list[dict]:
        """List user's accessible repositories."""
        token = decrypt_string(encrypted_token)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GITHUB_API_URL}/user/repos",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                params={"sort": "updated", "per_page": 30, "page": page}
            )
            resp.raise_for_status()
            return resp.json()


_github_client: Optional[GitHubOAuthClient] = None

def get_github_client() -> GitHubOAuthClient:
    """Get GitHub OAuth client singleton."""
    global _github_client
    if _github_client is None:
        import os
        client_id = os.environ.get("GITHUB_CLIENT_ID", "")
        client_secret = os.environ.get("GITHUB_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise RuntimeError("GitHub OAuth not configured")
        _github_client = GitHubOAuthClient(client_id, client_secret)
    return _github_client