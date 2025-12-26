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
HAS_OPENAI = bool(OPENAI_API_KEY)

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
        llm = ChatOpenAI(model="gpt-4o-mini")
        
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
        logger.info("Invoking LLM for classification...")
        response = await chain.ainvoke({
            "title": issue_title,
            "body": (issue_body or "")[:1000]  # Limit body length, handle None
        })
        logger.info(f"LLM response type: {type(response)}, content: {response}")
        
        # Handle None response
        if response is None or not hasattr(response, 'content'):
            logger.error(f"LLM returned invalid response: {response}")
            raise ValueError("LLM returned no response")
        
        classification = response.content.strip().upper()
        
        # Validate classification
        if classification not in ["BUG", "FEATURE", "QUESTION"]:
            classification = "QUESTION"  # Default fallback
        
        state["classification"] = classification
        logger.info(f"LLM classification: {classification}")
        
    except Exception as e:
        logger.error(f"Error in classify_issue: {str(e)}", exc_info=True)
        state["classification"] = "QUESTION"  # Safe default
    
    return state


async def retrieve_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 2: Retrieve relevant context using RAG
    
    Searches vector database for relevant documentation and code
    """
    issue_title = state.get("issue_title", "")
    issue_body = state.get("issue_body", "")
    
    logger.info("Retrieving context from vector database...")
    
    try:
        from services.rag_service import search_relevant_context
        
        # Combine title and body for better search query (title often has key terms)
        search_query = f"{issue_title}\n\n{issue_body}".strip()
        
        # Retrieve more chunks (10) for better context coverage
        context_chunks = await search_relevant_context(search_query, top_k=10)
        
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
        llm = ChatOpenAI(model="gpt-4o-mini")
        
        # Build context string with source information if available
        # Use all retrieved chunks (up to 10) for comprehensive context
        context_str = "\n\n".join([
            f"**Context {i+1}:**\n{chunk}"
            for i, chunk in enumerate(context_chunks)
        ])
        
        # Log retrieved context for debugging
        logger.info(f"Using {len(context_chunks)} context chunks for generation")
        if context_chunks:
            logger.debug(f"First context chunk preview: {context_chunks[0][:200]}...")
        
        if classification == "BUG":
            prompt_template = """You are an expert software engineer helping to triage a bug report using the actual codebase context.

**Issue Title:** {title}

**Issue Description:**
{body}

**Retrieved Context from Codebase (IMPORTANT - Use this to understand the actual implementation):**
{context}

**CRITICAL INSTRUCTIONS:**
- You MUST reference specific code, file paths, or error handling patterns from the retrieved context above
- Base your analysis on the ACTUAL code shown in the context
- Quote or reference specific code sections if relevant (e.g., "In [filename], the error handling for this case is...")
- Do NOT provide generic advice - be specific based on what you see in the context

Generate a helpful, professional response that:
1. Acknowledges the issue
2. References specific code/files from the context to analyze the problem
3. Suggests potential root causes based on the actual implementation
4. Provides workarounds or fixes referencing specific code patterns from the codebase
5. Asks clarifying questions if needed
6. Is formatted in clear Markdown

Keep the response concise (under 400 words) and actionable. If the context doesn't contain relevant information, acknowledge that and ask for more details."""

        elif classification == "FEATURE":
            prompt_template = """You are an expert software engineer helping to evaluate a feature request using the actual codebase context.

**Feature Request:** {title}

**Description:**
{body}

**Retrieved Context from Codebase (IMPORTANT - Use this to understand the actual implementation):**
{context}

**CRITICAL INSTRUCTIONS:**
- You MUST reference specific code, file paths, API endpoints, or data structures from the retrieved context above
- Base your feasibility assessment on the ACTUAL architecture shown in the context
- If you see relevant code in the context, quote it or reference it explicitly (e.g., "Looking at [filename], the current implementation uses...")
- If the context provides partial information, explain what you found and what additional details would be needed
- Do NOT provide generic advice - be specific based on what you see in the context, or explicitly state what information is missing
- If multiple files are mentioned, consider how they interact together

Generate a helpful, professional response that:
1. Acknowledges the request
2. References specific code/files from the retrieved context to evaluate feasibility
3. Suggests concrete implementation approach based on existing patterns in the codebase
4. Mentions specific files, functions, or data structures that would need to be modified
5. Asks clarifying questions if the context doesn't provide enough detail
6. Is formatted in clear Markdown

Keep the response concise (under 400 words) and constructive. If the context doesn't contain relevant information, acknowledge that and ask for more details."""

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
            ("system", "You are a helpful engineering assistant."),
            ("user", prompt_template)
        ])
        
        chain = prompt | llm
        logger.info("Invoking LLM for solution generation...")
        response = await chain.ainvoke({
            "title": issue_title,
            "body": (issue_body or "")[:2000],  # Limit length, handle None
            "context": context_str if context_str else "No specific documentation found."
        })
        logger.info(f"LLM response type: {type(response)}, has content: {hasattr(response, 'content') if response else False}")
        
        # Handle None response
        if response is None or not hasattr(response, 'content'):
            logger.error(f"LLM returned invalid response: {response}")
            raise ValueError("LLM returned no response")
        
        state["draft_response"] = response.content
        logger.info("Generated LLM response")
        
    except Exception as e:
        logger.error(f"Error in generate_solution: {str(e)}", exc_info=True)
        state["draft_response"] = f"""## Error Generating Response

We encountered an issue while processing your request: {str(e)}

Please try again or contact support if the issue persists."""
    
    return state
