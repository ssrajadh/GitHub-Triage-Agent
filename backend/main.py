"""
FastAPI Backend for GitHub Triage Agent
Main application entry point with webhook handling and WebSocket support
"""
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import logging
from typing import Dict, Set

# Load environment variables from root .env file
root_dir = Path(__file__).parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

from api.webhook import verify_github_signature, process_webhook_event
from api.websocket import ConnectionManager
from models.schemas import WebhookPayload, DraftResponse, ApprovalRequest, RejectRequest, EditApprovalRequest

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="GitHub Triage Agent",
    description="Intelligent Workflow Automation for Engineering Incident Response",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
manager = ConnectionManager()

# In-memory storage for drafts (replace with database in production)
drafts_db: Dict[str, DraftResponse] = {}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "GitHub Triage Agent",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "websocket_connections": len(manager.active_connections)
    }


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    GitHub webhook endpoint for issue events
    Verifies signature and processes events asynchronously
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
        
        logger.info(f"Received {event_type} event for issue #{payload.get('issue', {}).get('number', 'unknown')}")
        
        # Process only issue events
        if event_type == "issues" and payload.get("action") == "opened":
            # Add to background tasks to return 200 immediately
            background_tasks.add_task(
                process_webhook_event,
                payload,
                manager,
                drafts_db
            )
            
            return JSONResponse(
                status_code=200,
                content={"status": "accepted", "message": "Webhook received and queued for processing"}
            )
        else:
            return JSONResponse(
                status_code=200,
                content={"status": "ignored", "message": f"Event type {event_type} not processed"}
            )
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates to frontend dashboard
    Broadcasts agent state changes to all connected clients
    """
    await manager.connect(websocket)
    try:
        # Keep connection alive and handle ping/pong
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")


@app.get("/api/drafts/pending")
async def get_pending_drafts():
    """Get all pending draft responses"""
    pending = [
        draft for draft in drafts_db.values()
        if draft.get("approval_status") == "pending"
    ]
    return pending


@app.get("/api/drafts/{draft_id}")
async def get_draft(draft_id: str):
    """Get specific draft by ID"""
    if draft_id not in drafts_db:
        raise HTTPException(status_code=404, detail="Draft not found")
    return drafts_db[draft_id]


@app.post("/api/drafts/{draft_id}/approve")
async def approve_draft(draft_id: str, request: ApprovalRequest):
    """
    Approve draft and post to GitHub
    Requires valid approval token for security
    """
    if draft_id not in drafts_db:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    draft = drafts_db[draft_id]
    
    # In production, verify the approval token signature
    # For now, we'll just update the status
    
    try:
        from services.github_service import post_comment_to_issue
        
        # Post comment to GitHub
        repo_full_name = draft.get("repository_full_name")
        issue_number = draft.get("issue_number")
        comment_body = draft.get("content")
        
        success = await post_comment_to_issue(repo_full_name, issue_number, comment_body)
        
        if success:
            draft["approval_status"] = "approved"
            logger.info(f"Draft {draft_id} approved and posted to GitHub")
            
            # Broadcast update via WebSocket
            await manager.broadcast({
                "type": "state_update",
                "data": {
                    "issue_id": draft_id,
                    "approval_status": "approved",
                    "processing_stage": "approved"
                }
            })
            
            return {"status": "success", "message": "Response posted to GitHub"}
        else:
            raise HTTPException(status_code=500, detail="Failed to post to GitHub")
            
    except Exception as e:
        logger.error(f"Error approving draft: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/drafts/{draft_id}/reject")
async def reject_draft(draft_id: str, request: RejectRequest):
    """Reject draft response"""
    if draft_id not in drafts_db:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    draft = drafts_db[draft_id]
    draft["approval_status"] = "rejected"
    draft["rejection_reason"] = request.reason
    
    logger.info(f"Draft {draft_id} rejected: {request.reason}")
    
    # Broadcast update via WebSocket
    await manager.broadcast({
        "type": "state_update",
        "data": {
            "issue_id": draft_id,
            "approval_status": "rejected",
            "processing_stage": "rejected"
        }
    })
    
    return {"status": "success", "message": "Draft rejected"}


@app.post("/api/drafts/{draft_id}/edit-approve")
async def edit_and_approve_draft(draft_id: str, request: EditApprovalRequest):
    """
    Edit draft content and approve
    Posts edited version to GitHub
    """
    if draft_id not in drafts_db:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    draft = drafts_db[draft_id]
    
    try:
        from services.github_service import post_comment_to_issue
        
        # Post edited comment to GitHub
        repo_full_name = draft.get("repository_full_name")
        issue_number = draft.get("issue_number")
        
        success = await post_comment_to_issue(
            repo_full_name,
            issue_number,
            request.edited_content
        )
        
        if success:
            draft["approval_status"] = "approved"
            draft["content"] = request.edited_content
            draft["human_edited"] = True
            
            logger.info(f"Draft {draft_id} edited and approved")
            
            # Broadcast update via WebSocket
            await manager.broadcast({
                "type": "state_update",
                "data": {
                    "issue_id": draft_id,
                    "approval_status": "approved",
                    "processing_stage": "approved",
                    "human_edits": request.edited_content
                }
            })
            
            return {"status": "success", "message": "Edited response posted to GitHub"}
        else:
            raise HTTPException(status_code=500, detail="Failed to post to GitHub")
            
    except Exception as e:
        logger.error(f"Error editing draft: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/issues")
async def get_issues():
    """Get all processed issues"""
    return list(drafts_db.values())


if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
