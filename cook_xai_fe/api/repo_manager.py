from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, HttpUrl
import urllib.parse
from core.config import settings
from core.github_client import github_api
from core.database import save_repo_token, get_all_connected_repos, remove_repo_token
from core.logger import logger

router = APIRouter()

class RepoRegistrationRequest(BaseModel):
    repo_full_name: str

@router.get("/api/user/repos")
async def get_user_repositories(request: Request):
    """Fetches the user's repositories from GitHub to display on the dashboard."""
    token = request.cookies.get("github_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    try:
        import requests
        resp = requests.get(
            "https://api.github.com/user/repos?sort=updated&per_page=100", 
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"},
            timeout=10
        )
        resp.raise_for_status()
        repos = resp.json()
        
        connected_repos = get_all_connected_repos()
        webhook_target_url = f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}/api/webhook"
        
        verified_connected_repos = set()
        
        # Auto-heal: verify currently "connected" repos against actual GitHub API webhooks
        for repo in repos:
            repo_name = repo["full_name"]
            if repo_name in connected_repos:
                if github_api.check_webhook_exists(repo_name, webhook_target_url, token):
                    verified_connected_repos.add(repo_name)
                else:
                    logger.warning(f"Webhook missing on GitHub for {repo_name}. Auto-healing DB.")
                    remove_repo_token(repo_name)
        
        # Filter down to just what the UI needs
        return [
            {
                "id": repo["id"],
                "full_name": repo["full_name"],
                "name": repo["name"],
                "private": repo["private"],
                "description": repo["description"],
                "language": repo["language"],
                "is_connected": repo["full_name"] in verified_connected_repos
            }
            for repo in repos
        ]
    except Exception as e:
        logger.error(f"Failed to fetch user repos: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch repositories from GitHub.")

@router.post("/api/register-repo")
async def register_repository(request: RepoRegistrationRequest, fastapi_req: Request):
    """
    Registers the backend's webhook onto the user's provided public GitHub repository.
    Stores their specific token in MongoDB to actuate future webhook events for their Repo.
    """
    repo_name = request.repo_full_name.strip()
    
    if not repo_name or "/" not in repo_name:
        raise HTTPException(status_code=400, detail="Invalid repository format. Expected username/repo.")

    logger.info(f"Attempting to register webhook for repository: {repo_name}")

    use_token = fastapi_req.cookies.get("github_token") or settings.GITHUB_TOKEN
    if not use_token:
        logger.error("No exact GITHUB_TOKEN passed and no default found.")
        raise HTTPException(status_code=401, detail="Please Sign in with GitHub first to connect a repository.")

    webhook_target_url = f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}/api/webhook"

    success = github_api.create_webhook(repo_name, webhook_target_url, settings.WEBHOOK_SECRET, use_token)

    if success:
        # Crucial Multi-Tenant Step: Save the PAT into Atlas mapped to this exact repo.
        save_repo_token(repo_name, use_token)
        return {
            "status": "success", 
            "repo": repo_name, 
            "message": f"Successfully connected to {repo_name}!"
        }
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to connect to {repo_name}. Ensure your GitHub Token has 'repo' admin rights."
        )
