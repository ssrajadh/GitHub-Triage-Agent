"""
Individual LangGraph nodes for issue processing
Each node performs a specific task and updates state
"""
import logging
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)

# Check if OpenAI API key is available
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HAS_OPENAI = bool(OPENAI_API_KEY) and OPENAI_API_KEY != "sk-your-key-here"

if HAS_OPENAI:
    try:
        from langchain_openai import ChatOpenAI
        from langchain.prompts import ChatPromptTemplate
        logger.info(f"OpenAI integration enabled (key: {OPENAI_API_KEY[:10]}...)")
    except ImportError as e:
        logger.warning(f"LangChain OpenAI not available - using mock responses: {e}")
        HAS_OPENAI = False
else:
    logger.info("OpenAI API key not configured - using mock responses")


async def classify_issue(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 1: Classify issue as BUG, FEATURE, or QUESTION
    
    Uses LLM to analyze issue sentiment and technical depth
    """
    issue_title = state.get("issue_title", "")
    issue_body = state.get("issue_body", "")
    
    logger.info(f"Classifying issue: {issue_title}")
    
    if not HAS_OPENAI:
        # Mock classification for testing
        if "bug" in issue_title.lower() or "error" in issue_title.lower():
            classification = "BUG"
        elif "feature" in issue_title.lower() or "add" in issue_title.lower():
            classification = "FEATURE"
        else:
            classification = "QUESTION"
        
        state["classification"] = classification
        logger.info(f"Mock classification: {classification}")
        return state
    
    try:
        # Real LLM classification
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at triaging software engineering issues.
Classify the issue as one of:
- BUG: Something is broken or not working as expected
- FEATURE: Request for new functionality or enhancement
- QUESTION: General question or clarification needed

Respond with ONLY one word: BUG, FEATURE, or QUESTION"""),
            ("user", "Title: {title}\n\nBody: {body}")
        ])
        
        chain = prompt | llm
        response = await chain.ainvoke({
            "title": issue_title,
            "body": issue_body[:1000]  # Limit body length
        })
        
        # Handle None response
        if response is None or not hasattr(response, 'content'):
            raise ValueError("LLM returned no response")
        
        classification = response.content.strip().upper()
        
        # Validate classification
        if classification not in ["BUG", "FEATURE", "QUESTION"]:
            classification = "QUESTION"  # Default fallback
        
        state["classification"] = classification
        logger.info(f"LLM classification: {classification}")
        
    except Exception as e:
        logger.error(f"Error in classify_issue: {str(e)}")
        state["classification"] = "QUESTION"  # Safe default
    
    return state


async def retrieve_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 2: Retrieve relevant context using RAG
    
    Searches vector database for relevant documentation and past issues
    """
    issue_body = state.get("issue_body", "")
    
    logger.info("Retrieving context from vector database...")
    
    try:
        from services.rag_service import search_relevant_context
        
        # Search vector database
        context_chunks = await search_relevant_context(issue_body, top_k=5)
        
        state["retrieved_context"] = context_chunks
        logger.info(f"Retrieved {len(context_chunks)} context chunks")
        
    except Exception as e:
        logger.error(f"Error in retrieve_context: {str(e)}")
        state["retrieved_context"] = []
    
    return state


async def generate_solution(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 3: Generate draft response using LLM
    
    Synthesizes issue details and retrieved context into actionable response
    """
    issue_title = state.get("issue_title", "")
    issue_body = state.get("issue_body", "")
    classification = state.get("classification", "QUESTION")
    context_chunks = state.get("retrieved_context", [])
    
    logger.info("Generating solution draft...")
    
    if not HAS_OPENAI:
        # Mock response for testing
        draft = f"""## Analysis
This appears to be a {classification} issue.

## Proposed Solution
Thank you for reporting this issue. Our team will investigate and provide more details soon.

**Issue Summary:** {issue_title}

This is a mock response for testing purposes. Configure OPENAI_API_KEY for real responses.
"""
        state["draft_response"] = draft
        logger.info("Generated mock response")
        return state
    
    try:
        # Real LLM generation
        llm = ChatOpenAI(model="gpt-4", temperature=0.7)
        
        # Build context string
        context_str = "\n\n".join([
            f"**Context {i+1}:**\n{chunk}"
            for i, chunk in enumerate(context_chunks[:3])  # Limit to top 3
        ])
        
        if classification == "BUG":
            prompt_template = """You are an expert software engineer helping to triage a bug report.

**Issue Title:** {title}

**Issue Description:**
{body}

**Retrieved Context from Documentation:**
{context}

Generate a helpful, professional response that:
1. Acknowledges the issue
2. Provides initial analysis based on the documentation
3. Suggests potential root causes or workarounds
4. Asks clarifying questions if needed
5. Is formatted in clear Markdown

Keep the response concise (under 300 words) and actionable."""

        elif classification == "FEATURE":
            prompt_template = """You are an expert software engineer helping to evaluate a feature request.

**Feature Request:** {title}

**Description:**
{body}

**Retrieved Context from Documentation:**
{context}

Generate a helpful, professional response that:
1. Acknowledges the request
2. Evaluates feasibility based on current architecture
3. Suggests implementation approach or alternatives
4. Asks clarifying questions about requirements
5. Is formatted in clear Markdown

Keep the response concise (under 300 words) and constructive."""

        else:  # QUESTION
            prompt_template = """You are an expert software engineer helping to answer a technical question.

**Question:** {title}

**Details:**
{body}

**Retrieved Context from Documentation:**
{context}

Generate a helpful, professional response that:
1. Directly answers the question
2. References relevant documentation
3. Provides examples if helpful
4. Suggests related resources
5. Is formatted in clear Markdown

Keep the response concise (under 300 words) and informative."""

        prompt = ChatPromptTemplate.from_messages([
        chain = prompt | llm
        response = await chain.ainvoke({
            "title": issue_title,
            "body": issue_body[:2000],  # Limit length
            "context": context_str if context_str else "No specific documentation found."
        })
        
        # Handle None response
        if response is None or not hasattr(response, 'content'):
            raise ValueError("LLM returned no response")
        
        state["draft_response"] = response.content
        logger.info("Generated LLM response")_str else "No specific documentation found."
        })
        
        state["draft_response"] = response.content
        logger.info("Generated LLM response")
        
    except Exception as e:
        logger.error(f"Error in generate_solution: {str(e)}")
        state["draft_response"] = f"""## Error Generating Response

We encountered an issue while processing your request: {str(e)}

Please try again or contact support if the issue persists."""
    
    return state
