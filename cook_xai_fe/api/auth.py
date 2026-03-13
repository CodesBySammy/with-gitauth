import requests
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from core.config import settings
from core.logger import logger

router = APIRouter()

@router.get("/api/auth/login")
async def login_with_github():
    """Redirects the user to GitHub to authorize the application."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="OAuth App not configured. Missing GITHUB_CLIENT_ID.")
        
    # Request repo and admin:repo_hook permissions
    url = f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&scope=repo,admin:repo_hook"
    return RedirectResponse(url)

@router.get("/api/auth/callback")
async def github_callback(code: str):
    """Handles the OAuth callback, exchanges code for an access token, and sets a cookie."""
    url = "https://github.com/login/oauth/access_token"
    payload = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "code": code
    }
    headers = {"Accept": "application/json"}
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        access_token = data.get("access_token")
        if not access_token:
            logger.error(f"GitHub OAuth failed: {data}")
            return RedirectResponse("/?error=oauth_failed")
            
        # Redirect back to home with a success flag
        response = RedirectResponse(url="/?logged_in=1")
        
        # Store for 30 days. HttpOnly=True protects against XSS.
        response.set_cookie(
            key="github_token", 
            value=access_token, 
            max_age=30*24*3600, 
            httponly=True,
            samesite='lax'
        )
        return response
    except Exception as e:
        logger.error(f"OAuth Callback Error: {e}")
        return RedirectResponse("/?error=oauth_exception")

@router.get("/api/user")
async def get_current_user(request: Request):
    """Returns the currently authenticated GitHub user's profile."""
    token = request.cookies.get("github_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    try:
        resp = requests.get(
            "https://api.github.com/user", 
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        
        return {
            "login": data["login"],
            "avatar_url": data["avatar_url"],
            "name": data.get("name", data["login"])
        }
    except Exception as e:
        logger.error(f"Failed to fetch user profile: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@router.post("/api/auth/logout")
async def logout():
    """Clears the authentication cookie."""
    response = RedirectResponse(url="/")
    response.delete_cookie("github_token")
    return response
