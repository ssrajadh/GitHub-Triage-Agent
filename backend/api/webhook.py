"""
ChatOps Webhook Handler
Processes GitHub webhooks for issue creation and comment commands
"""
import hmac
import hashlib
import logging
from typing import Dict, Any
from datetime import datetime

from agents.langgraph_agent import process_issue_with_agent
from api.chatops import parse_command, format_draft_comment, format_approved_comment
from services.github_service import post_comment_to_issue, update_comment, delete_comment, get_bot_username

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


async def process_issue_webhook(
    payload: Dict[str, Any],
    bot_comments_db: Dict[int, int]
):
    """
    Process new issue webhook - generate draft and post to GitHub
    
    Args:
        payload: GitHub webhook payload for issues.opened event
        bot_comments_db: Dict mapping issue_number -> bot_comment_id
    """
    try:
        issue = payload.get("issue", {})
        repository = payload.get("repository", {})
        
        issue_number = issue.get("number")
        issue_title = issue.get("title")
        issue_body = issue.get("body", "")
        repo_full_name = repository.get("full_name")
        
        logger.info(f"Processing new issue #{issue_number}: {issue_title}")
        
        # Initialize state for LangGraph
        initial_state = {
            "issue_id": str(issue.get("id")),
            "issue_number": issue_number,
            "issue_title": issue_title,
            "issue_body": issue_body,
            "repository_full_name": repo_full_name,
            "classification": None,
            "retrieved_context": [],
            "draft_response": "",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Process with LangGraph agent (no WebSocket manager needed)
        final_state = await process_issue_with_agent(initial_state)
        
        # Format draft comment
        draft_text = final_state.get("draft_response", "I encountered an error processing this issue.")
        classification = final_state.get("classification", "QUESTION")
        
        formatted_comment = format_draft_comment(draft_text, classification)
        
        # Post draft comment to GitHub
        comment_id = await post_comment_to_issue(
            repo_full_name,
            issue_number,
            formatted_comment
        )
        
        if comment_id:
            # Store comment ID for later command processing
            bot_comments_db[issue_number] = comment_id
            logger.info(f"Posted draft comment {comment_id} to issue #{issue_number}")
        else:
            logger.error(f"Failed to post draft comment to issue #{issue_number}")
        
    except Exception as e:
        logger.error(f"Error processing issue webhook: {str(e)}", exc_info=True)


async def process_comment_webhook(
    payload: Dict[str, Any],
    bot_comments_db: Dict[int, int]
):
    """
    Process comment webhook - handle slash commands
    
    Args:
        payload: GitHub webhook payload for issue_comment.created event
        bot_comments_db: Dict mapping issue_number -> bot_comment_id
    """
    try:
        issue = payload.get("issue", {})
        comment = payload.get("comment", {})
        repository = payload.get("repository", {})
        
        issue_number = issue.get("number")
        comment_body = comment.get("body", "")
        comment_author = comment.get("user", {}).get("login", "")
        repo_full_name = repository.get("full_name")
        
        logger.info(f"Processing comment on issue #{issue_number} by {comment_author}")
        
        # Parse command from comment
        cmd = parse_command(comment_body)
        
        if not cmd:
            logger.info(f"No valid command found in comment")
            return
        
        # Check if we have a bot comment for this issue
        bot_comment_id = bot_comments_db.get(issue_number)
        if not bot_comment_id:
            logger.warning(f"No bot comment found for issue #{issue_number}")
            return
        
        logger.info(f"Executing command: /{cmd.command}")
        
        # Handle commands
        if cmd.command == "approve":
            await handle_approve(repo_full_name, issue_number, bot_comment_id, bot_comments_db)
        
        elif cmd.command == "revise":
            if not cmd.args:
                logger.warning("Revise command requires text argument")
                return
            await handle_revise(repo_full_name, issue_number, bot_comment_id, cmd.args, bot_comments_db)
        
        elif cmd.command == "reject":
            await handle_reject(repo_full_name, issue_number, bot_comment_id, bot_comments_db)
        
    except Exception as e:
        logger.error(f"Error processing comment webhook: {str(e)}", exc_info=True)


async def handle_approve(
    repo_full_name: str,
    issue_number: int,
    bot_comment_id: int,
    bot_comments_db: Dict[int, int]
):
    """
    Handle /approve command - remove draft markers from comment
    """
    try:
        # Get current comment
        from services.github_service import get_comment
        comment_body = await get_comment(repo_full_name, issue_number, bot_comment_id)
        
        if not comment_body:
            logger.error(f"Could not fetch comment {bot_comment_id}")
            return
        
        # Remove draft markers
        approved_text = format_approved_comment(comment_body)
        approved_text += "\n\n✅ **Approved by maintainer**"
        
        # Update comment
        success = await update_comment(repo_full_name, bot_comment_id, approved_text)
        
        if success:
            # Remove from tracking
            bot_comments_db.pop(issue_number, None)
            logger.info(f"Approved comment {bot_comment_id} on issue #{issue_number}")
        else:
            logger.error(f"Failed to approve comment {bot_comment_id}")
            
    except Exception as e:
        logger.error(f"Error in handle_approve: {str(e)}", exc_info=True)


async def handle_revise(
    repo_full_name: str,
    issue_number: int,
    bot_comment_id: int,
    new_text: str,
    bot_comments_db: Dict[int, int]
):
    """
    Handle /revise command - replace draft with new text
    """
    try:
        revised_text = f"{new_text}\n\n✅ **Revised and approved by maintainer**"
        
        # Update comment with new text
        success = await update_comment(repo_full_name, bot_comment_id, revised_text)
        
        if success:
            # Remove from tracking
            bot_comments_db.pop(issue_number, None)
            logger.info(f"Revised comment {bot_comment_id} on issue #{issue_number}")
        else:
            logger.error(f"Failed to revise comment {bot_comment_id}")
            
    except Exception as e:
        logger.error(f"Error in handle_revise: {str(e)}", exc_info=True)


async def handle_reject(
    repo_full_name: str,
    issue_number: int,
    bot_comment_id: int,
    bot_comments_db: Dict[int, int]
):
    """
    Handle /reject command - delete draft comment
    """
    try:
        # Delete comment
        success = await delete_comment(repo_full_name, bot_comment_id)
        
        if success:
            # Remove from tracking
            bot_comments_db.pop(issue_number, None)
            logger.info(f"Deleted comment {bot_comment_id} on issue #{issue_number}")
        else:
            logger.error(f"Failed to delete comment {bot_comment_id}")
            
    except Exception as e:
        logger.error(f"Error in handle_reject: {str(e)}", exc_info=True)
