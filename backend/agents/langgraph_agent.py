"""
LangGraph State Machine for Issue Triage
Implements cyclic graph architecture for intelligent routing
"""
import logging
from typing import Dict, Any, TypedDict, Literal, Annotated
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

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


def route_after_classification(state: AgentState) -> str:
    """
    Router function for conditional edges after classification
    
    Returns:
        Next node name based on classification
    """
    classification = state.get("classification")
    
    if classification in ["BUG", "QUESTION"]:
        logger.info(f"Routing {classification} to retrieve_context")
        return "retrieve_context"
    else:
        logger.info(f"Routing {classification} directly to generate_solution")
        return "generate_solution"


# Wrapper nodes that handle WebSocket broadcasting
_manager: ConnectionManager = None

def set_websocket_manager(manager: ConnectionManager):
    """Set the global WebSocket manager for broadcasting"""
    global _manager
    _manager = manager


async def classify_node(state: AgentState) -> AgentState:
    """Classify node with WebSocket broadcasting"""
    logger.info("Node 1: Classifying issue...")
    if _manager:
        state["processing_stage"] = "classifying"
        await _manager.broadcast_state_update(state)
    
    state = await classify_issue(state)
    logger.info(f"Issue classified as: {state.get('classification')}")
    return state


async def retrieve_node(state: AgentState) -> AgentState:
    """Retrieve node with WebSocket broadcasting"""
    logger.info("Node 2: Retrieving context...")
    if _manager:
        state["processing_stage"] = "retrieving_context"
        await _manager.broadcast_state_update(state)
    
    state = await retrieve_context(state)
    logger.info(f"Retrieved {len(state.get('retrieved_context', []))} context chunks")
    return state


async def generate_node(state: AgentState) -> AgentState:
    """Generate node with WebSocket broadcasting"""
    logger.info("Node 3: Generating solution...")
    if _manager:
        state["processing_stage"] = "generating_response"
        await _manager.broadcast_state_update(state)
    
    state = await generate_solution(state)
    logger.info("Solution generated successfully")
    
    # Set final state
    state["processing_stage"] = "awaiting_approval"
    state["approval_status"] = "pending"
    state["timestamp"] = datetime.utcnow().isoformat()
    
    if _manager:
        await _manager.broadcast_state_update(state)
    
    return state


# Build the LangGraph workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("classify", classify_node)

workflow.add_edge("generate_solution", END)

# Compile the graph
app = workflow.compile()


async def process_issue_with_agent(
    initial_state: Dict[str, Any],
    manager: ConnectionManager
) -> Dict[str, Any]:
    """
    Process issue through LangGraph state machine
    
    Graph structure:
    START → classify → [BUG/QUESTION] → retrieve_context → generate_solution → END
                    → [FEATURE] → generate_solution → END
    
    Args:
        initial_state: Initial state dictionary with issue details
        manager: WebSocket manager for broadcasting updates
        
    Returns:
        Final state dictionary after processing
    """
    try:
        # Set the WebSocket manager for broadcasting
        set_websocket_manager(manager)
        
        # Execute the graph
        final_state = await app.ainvoke(initial_state)
        
        return final_state
        
    except Exception as e:
        logger.error(f"Error in agent processing: {str(e)}", exc_info=True)
        
        # Set error state
        error_state = initial_state.copy()
        error_state["processing_stage"] = "error"
        error_state["approval_status"] = "rejected"
        error_state["draft_response"] = f"Error processing issue: {str(e)}"
        
        await manager.broadcast({
            "type": "error",
            "message": str(e),
            "data": error_state
        })
        
        return error_state


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
