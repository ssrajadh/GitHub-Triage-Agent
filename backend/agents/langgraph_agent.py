"""
LangGraph State Machine for Issue Triage
Implements cyclic graph architecture for intelligent routing
"""
import logging
from typing import Dict, Any, TypedDict, Literal
from datetime import datetime

from agents.nodes import classify_issue, retrieve_context, generate_solution
from api.websocket import ConnectionManager

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State schema for LangGraph agent"""
    issue_id: str
    issue_number: int
    issue_title: str
    issue_body: str
    repository_full_name: str
    classification: Literal["BUG", "FEATURE", "QUESTION"]
    retrieved_context: list
    draft_response: str
    approval_status: Literal["pending", "approved", "rejected"]
    processing_stage: str
    human_edits: str
    timestamp: str


async def process_issue_with_agent(
    initial_state: Dict[str, Any],
    manager: ConnectionManager
) -> Dict[str, Any]:
    """
    Process issue through LangGraph state machine
    
    Graph structure:
    START → classify_issue → [BUG/QUESTION] → retrieve_context → generate_solution → WAIT_APPROVAL
                          → [FEATURE] → generate_solution → WAIT_APPROVAL
    
    Args:
        initial_state: Initial state dictionary with issue details
        manager: WebSocket manager for broadcasting updates
        
    Returns:
        Final state dictionary after processing
    """
    state = initial_state.copy()
    
    try:
        # Node 1: Classify Issue
        logger.info("Node 1: Classifying issue...")
        state["processing_stage"] = "classifying"
        await manager.broadcast_state_update(state)
        
        state = await classify_issue(state)
        logger.info(f"Issue classified as: {state.get('classification')}")
        
        # Node 2: Retrieve Context (conditional based on classification)
        if state.get("classification") in ["BUG", "QUESTION"]:
            logger.info("Node 2: Retrieving context...")
            state["processing_stage"] = "retrieving_context"
            await manager.broadcast_state_update(state)
            
            state = await retrieve_context(state)
            logger.info(f"Retrieved {len(state.get('retrieved_context', []))} context chunks")
        else:
            # FEATURE requests skip RAG retrieval
            logger.info("Feature request - skipping context retrieval")
            state["retrieved_context"] = []
        
        # Node 3: Generate Solution
        logger.info("Node 3: Generating solution...")
        state["processing_stage"] = "generating_response"
        await manager.broadcast_state_update(state)
        
        state = await generate_solution(state)
        logger.info("Solution generated successfully")
        
        # Final state: Awaiting approval
        state["processing_stage"] = "awaiting_approval"
        state["approval_status"] = "pending"
        state["timestamp"] = datetime.utcnow().isoformat()
        
        await manager.broadcast_state_update(state)
        
        return state
        
    except Exception as e:
        logger.error(f"Error in agent processing: {str(e)}")
        
        # Set error state
        state["processing_stage"] = "error"
        state["approval_status"] = "rejected"
        state["draft_response"] = f"Error processing issue: {str(e)}"
        
        await manager.broadcast({
            "type": "error",
            "message": str(e),
            "data": state
        })
        
        return state


def should_retrieve_context(state: AgentState) -> bool:
    """Conditional edge: determine if RAG retrieval is needed"""
    return state.get("classification") in ["BUG", "QUESTION"]


def route_after_classification(state: AgentState) -> str:
    """
    Router function for conditional edges
    
    Returns:
        Next node name based on classification
    """
    classification = state.get("classification")
    
    if classification in ["BUG", "QUESTION"]:
        return "retrieve_context"
    elif classification == "FEATURE":
        return "generate_solution"
    else:
        return "generate_solution"
