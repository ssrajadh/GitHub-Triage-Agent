"""
FastAPI Backend for GitHub Triage Agent - ChatOps Version
Main application entry point with webhook handling for slash commands
"""
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import logging
from typing import Dict

# Load environment variables from root .env file
root_dir = Path(__file__).parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

from api.webhook import verify_github_signature, process_issue_webhook, process_comment_webhook
from models.schemas import WebhookPayload

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="GitHub Triage Agent (ChatOps)",
    description="AI-powered issue triage with slash command approval workflow",
    version="2.0.0"
)

# Configure CORS (minimal since no frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for bot comment IDs (maps issue_number -> comment_id)
# In production, use a database
bot_comments_db: Dict[int, int] = {}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "GitHub Triage Agent (ChatOps)",
        "status": "running",
        "version": "2.0.0",
        "mode": "ChatOps - interact via GitHub comments",
        "commands": ["/approve", "/revise", "/reject"]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "tracked_issues": len(bot_comments_db),
        "has_github_token": bool(os.getenv("GITHUB_TOKEN")),
        "has_openai_key": bool(os.getenv("OPENAI_API_KEY")),
        "has_webhook_secret": bool(os.getenv("GITHUB_WEBHOOK_SECRET"))
    }


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    GitHub webhook endpoint for issue and comment events
    Handles:
    - issues.opened - Generate and post draft comment
    - issue_comment.created - Parse slash commands (/approve, /revise, /reject)
    """
    try:
        # Get raw body and headers
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256")
        event_type = request.headers.get("X-GitHub-Event")
        
        # Verify signature
        secret = os.getenv("GITHUB_WEBHOOK_SECRET")
        if not secret:
            logger.error("GITHUB_WEBHOOK_SECRET not configured")
            raise HTTPException(status_code=500, detail="Webhook secret not configured")
        
        if not verify_github_signature(body, signature, secret):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse payload
        payload = json.loads(body)
        
        # Handle issue opened events
        if event_type == "issues" and payload.get("action") == "opened":
            issue_number = payload.get("issue", {}).get("number")
            logger.info(f"Received issue opened event for #{issue_number}")
            
            background_tasks.add_task(
                process_issue_webhook,
                payload,
                bot_comments_db
            )
            
            return JSONResponse(
                status_code=200,
                content={"status": "accepted", "message": "Issue webhook queued for processing"}
            )
        
        # Handle comment created events (for slash commands)
        elif event_type == "issue_comment" and payload.get("action") == "created":
            issue_number = payload.get("issue", {}).get("number")
            comment_id = payload.get("comment", {}).get("id")
            logger.info(f"Received comment on issue #{issue_number}, comment ID: {comment_id}")
            
            background_tasks.add_task(
                process_comment_webhook,
                payload,
                bot_comments_db
            )
            
            return JSONResponse(
                status_code=200,
                content={"status": "accepted", "message": "Comment webhook queued for processing"}
            )
        
        else:
            return JSONResponse(
                status_code=200,
                content={"status": "ignored", "message": f"Event {event_type}.{payload.get('action')} not processed"}
            )
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get bot statistics"""
    return {
        "active_drafts": len(bot_comments_db),
        "tracked_issues": list(bot_comments_db.keys())
    }


if __name__ == "__main__":
    # Cloud Run sets PORT env var automatically
    # Fallback to API_PORT for local development, then default to 8000
    port = int(os.getenv("PORT", os.getenv("API_PORT", 8000)))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    # Disable reload in production (Cloud Run)
    reload = os.getenv("ENVIRONMENT") != "production"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
