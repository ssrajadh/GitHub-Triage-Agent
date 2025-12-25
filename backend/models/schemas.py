"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


class WebhookPayload(BaseModel):
    """GitHub webhook payload schema"""
    action: str
    issue: dict
    repository: dict


class AgentState(BaseModel):
    """LangGraph agent state schema"""
    issue_id: str
    issue_number: int
    issue_title: str
    issue_body: str
    repository_full_name: str
    classification: Optional[Literal["BUG", "FEATURE", "QUESTION"]] = None
    retrieved_context: List[str] = Field(default_factory=list)
    draft_response: str = ""
    approval_status: Literal["pending", "approved", "rejected"] = "pending"
    processing_stage: str = "received"
    human_edits: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class DraftResponse(BaseModel):
    """Draft response from agent"""
    id: str
    issue_id: str
    issue_number: int
    repository_full_name: str
    content: str
    retrieved_context: List[str]
    classification: str
    approval_status: str = "pending"
    created_at: str
    approval_token: Optional[str] = None
    human_edited: bool = False


class ApprovalRequest(BaseModel):
    """Request to approve a draft"""
    approval_token: str


class RejectRequest(BaseModel):
    """Request to reject a draft"""
    reason: Optional[str] = "Manual rejection"


class EditApprovalRequest(BaseModel):
    """Request to edit and approve a draft"""
    edited_content: str
    approval_token: str


class WebSocketMessage(BaseModel):
    """WebSocket message schema"""
    type: Literal["state_update", "error", "connection", "ping"]
    data: Optional[dict] = None
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
