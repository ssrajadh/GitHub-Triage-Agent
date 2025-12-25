"""
Webhook handling and signature verification
Implements GitHub webhook security best practices
"""
import hmac
import hashlib
import logging
from typing import Dict, Any
from datetime import datetime

from api.websocket import ConnectionManager
from agents.langgraph_agent import process_issue_with_agent

logger = logging.getLogger(__name__)


def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify GitHub webhook signature using HMAC-SHA256
    
    Args:
        payload: Raw request body as bytes
        signature: X-Hub-Signature-256 header value
        secret: Webhook secret from environment
        
    Returns:
        bool: True if signature is valid
    """
    if not signature:
        return False
    
    # Compute expected signature
    expected_signature = "sha256=" + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)


async def process_webhook_event(
    payload: Dict[str, Any],
    manager: ConnectionManager,
    drafts_db: Dict[str, Any]
):
    """
    Process GitHub webhook event asynchronously
    Runs LangGraph agent and broadcasts updates via WebSocket
    
    Args:
        payload: GitHub webhook payload
        manager: WebSocket connection manager
        drafts_db: In-memory database for draft responses
    """
    try:
        issue = payload.get("issue", {})
        repository = payload.get("repository", {})
        
        issue_id = str(issue.get("id"))
        issue_number = issue.get("number")
        issue_title = issue.get("title")
        issue_body = issue.get("body", "")
        repo_full_name = repository.get("full_name")
        
        logger.info(f"Processing issue #{issue_number}: {issue_title}")
        
        # Initialize state
        initial_state = {
            "issue_id": issue_id,
            "issue_number": issue_number,
            "issue_title": issue_title,
            "issue_body": issue_body,
            "repository_full_name": repo_full_name,
            "classification": None,
            "retrieved_context": [],
            "draft_response": "",
            "approval_status": "pending",
            "processing_stage": "received",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Broadcast initial state
        await manager.broadcast({
            "type": "state_update",
            "data": initial_state,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Store in drafts_db
        drafts_db[issue_id] = initial_state
        
        # Process with LangGraph agent
        final_state = await process_issue_with_agent(
            initial_state,
            manager
        )
        
        # Update drafts_db with final state
        drafts_db[issue_id] = final_state
        
        logger.info(f"Issue #{issue_number} processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing webhook event: {str(e)}")
        
        # Broadcast error state
        await manager.broadcast({
            "type": "error",
            "message": f"Error processing issue: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        })
