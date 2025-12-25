"""
GitHub API Service
Handles posting comments and interacting with GitHub API
"""
import logging
import os
import aiohttp
from typing import Optional

logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API_BASE = "https://api.github.com"


async def post_comment_to_issue(
    repo_full_name: str,
    issue_number: int,
    comment_body: str
) -> Optional[int]:
    """
    Post comment to GitHub issue
    
    Args:
        repo_full_name: Repository name in format 'owner/repo'
        issue_number: Issue number
        comment_body: Comment text in Markdown format
        
    Returns:
        int: Comment ID if successful, None otherwise
    """
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN not configured")
        return None
    
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/{issue_number}/comments"
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "body": comment_body
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 201:
                    data = await response.json()
                    comment_id = data.get("id")
                    logger.info(f"Successfully posted comment {comment_id} to issue #{issue_number}")
                    return comment_id
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to post comment: {response.status} - {error_text}")
                    return None
                    
    except Exception as e:
        logger.error(f"Error posting to GitHub: {str(e)}")
        return None


async def get_issue_details(repo_full_name: str, issue_number: int) -> Optional[dict]:
    """
    Fetch issue details from GitHub
    
    Args:
        repo_full_name: Repository name in format 'owner/repo'
        issue_number: Issue number
        
    Returns:
        dict: Issue details or None if error
    """
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN not configured")
        return None
    
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/{issue_number}"
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch issue: {response.status}")
                    return None
                    
    except Exception as e:
        logger.error(f"Error fetching from GitHub: {str(e)}")
        return None


async def get_comment(repo_full_name: str, issue_number: int, comment_id: int) -> Optional[str]:
    """
    Get comment body by ID
    
    Args:
        repo_full_name: Repository name
        issue_number: Issue number  
        comment_id: Comment ID
        
    Returns:
        str: Comment body or None if error
    """
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN not configured")
        return None
    
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/comments/{comment_id}"
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("body")
                else:
                    logger.error(f"Failed to fetch comment: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching comment: {str(e)}")
        return None


async def update_comment(repo_full_name: str, comment_id: int, new_body: str) -> bool:
    """
    Update comment body
    
    Args:
        repo_full_name: Repository name
        comment_id: Comment ID
        new_body: New comment text
        
    Returns:
        bool: True if successful
    """
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN not configured")
        return False
    
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/comments/{comment_id}"
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    payload = {"body": new_body}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    logger.info(f"Successfully updated comment {comment_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to update comment: {response.status} - {error_text}")
                    return False
    except Exception as e:
        logger.error(f"Error updating comment: {str(e)}")
        return False


async def delete_comment(repo_full_name: str, comment_id: int) -> bool:
    """
    Delete comment
    
    Args:
        repo_full_name: Repository name
        comment_id: Comment ID
        
    Returns:
        bool: True if successful
    """
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN not configured")
        return False
    
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/issues/comments/{comment_id}"
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status == 204:
                    logger.info(f"Successfully deleted comment {comment_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to delete comment: {response.status} - {error_text}")
                    return False
    except Exception as e:
        logger.error(f"Error deleting comment: {str(e)}")
        return False


async def get_bot_username() -> str:
    """Get the authenticated bot's username"""
    return "github-actions[bot]"  # Update based on your GitHub App/bot setup
