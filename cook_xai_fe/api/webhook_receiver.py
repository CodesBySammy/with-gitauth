import json
import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from core.config import settings
from core.logger import logger
from services.review_orchestrator import process_pipeline
from core.github_client import github_api
from services.auto_fixer import auto_fixer
from core.database import get_repo_token

router = APIRouter()

def verify_signature(payload: bytes, signature: str) -> bool:
    expected_sig = "sha256=" + hmac.new(
        settings.WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_sig)

@router.post("/api/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.body()
    signature = request.headers.get("x-hub-signature-256")

    if not signature or not verify_signature(payload, signature):
        logger.warning("Unverified webhook received!")
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = json.loads(payload)
    event_type = request.headers.get("x-github-event")

    repo_name = data.get("repository", {}).get("full_name")

    # 1. PR Code Push
    if event_type == "pull_request" and data.get("action") in ["opened", "synchronize"]:
        pr_number = data["pull_request"]["number"]
        head_sha = data["pull_request"]["head"]["sha"]
        
        token = get_repo_token(repo_name)

        logger.info(f"Webhook Validated: PR #{pr_number} on {repo_name}")
        background_tasks.add_task(process_pipeline, repo_name, pr_number, head_sha, token)
        return {"status": "Review pipeline triggered"}

    # 2. Issue Comment Intercept (Auto-Fix command)
    if event_type == "issue_comment" and data.get("action") == "created":
        if "pull_request" in data.get("issue", {}):
            pr_number = data["issue"]["number"]
            comment_body = data["comment"]["body"]
            
            if "/fix" in comment_body.lower():
                token = get_repo_token(repo_name)
                logger.info(f"Auto-Fix command intercepted: {comment_body}")
                background_tasks.add_task(auto_fixer.process_fix_command, repo_name, pr_number, comment_body, token)
                return {"status": "Auto-Fix pipeline triggered"}

    return {"status": "Event ignored"}