"""
LangGraph State Machine for ChatOps Issue Triage
Implements cyclic graph architecture without WebSocket dependencies
"""
import logging
from typing import Dict, Any, TypedDict, Literal
from datetime import datetime

from langgraph.graph import StateGraph, END

from agents.nodes import classify_issue, retrieve_context, generate_solution

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
    
    All issue types use RAG to retrieve relevant context from documentation.
    
    Returns:
        Next node name (always retrieve_context for all classifications)
    """
    classification = state.get("classification")
    
    # All classifications should use RAG for context-aware responses
    logger.info(f"Routing {classification} to retrieve_context for RAG")
    return "retrieve_context"


async def classify_node(state: AgentState) -> AgentState:
    """Classify node"""
    logger.info("Node 1: Classifying issue...")
    state["processing_stage"] = "classifying"
    
    state = await classify_issue(state)
    logger.info(f"Issue classified as: {state.get('classification')}")
    return state


async def retrieve_node(state: AgentState) -> AgentState:
    """Retrieve node"""
    logger.info("Node 2: Retrieving context...")
    state["processing_stage"] = "retrieving_context"
    
    state = await retrieve_context(state)
    logger.info(f"Retrieved {len(state.get('retrieved_context', []))} context chunks")
    return state


async def generate_node(state: AgentState) -> AgentState:
    """Generate node"""
    logger.info("Node 3: Generating solution...")
    state["processing_stage"] = "generating_response"
    
    state = await generate_solution(state)
    logger.info("Solution generated successfully")
    
    # Set final state
    state["processing_stage"] = "awaiting_approval"
    state["approval_status"] = "pending"
    state["timestamp"] = datetime.utcnow().isoformat()
    
    return state


# Build the LangGraph workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("classify", classify_node)
workflow.add_node("retrieve_context", retrieve_node)
workflow.add_node("generate_solution", generate_node)

# Add edges
workflow.set_entry_point("classify")

# Conditional routing after classification
workflow.add_conditional_edges(
    "classify",
    route_after_classification,
    {
        "retrieve_context": "retrieve_context",
        "generate_solution": "generate_solution"
    }
)

# Linear edges
workflow.add_edge("retrieve_context", "generate_solution")
workflow.add_edge("generate_solution", END)

# Compile the graph
app = workflow.compile()


async def process_issue_with_agent(
    initial_state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process issue through LangGraph state machine
    
    Graph structure:
    START → classify → retrieve_context → generate_solution → END
    
    All issue types use RAG to retrieve relevant documentation context.
    
    Args:
        initial_state: Initial state dictionary with issue details
        
    Returns:
        Final state dictionary after processing
    """
    try:
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
        
        return error_state
