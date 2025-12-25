# FastAPI Backend - GitHub Triage Agent

Intelligent workflow automation backend for GitHub issue triage using LangGraph and RAG.

## Features

- **Webhook Handler**: Secure GitHub webhook receiver with HMAC-SHA256 verification
- **LangGraph Agent**: Cyclic state machine for intelligent issue routing
- **RAG System**: ChromaDB vector store for context retrieval
- **WebSocket Server**: Real-time updates to frontend dashboard
- **Human-in-the-Loop**: Approval workflow for AI-generated responses

## Architecture

```
backend/
├── main.py                    # FastAPI app + endpoints
├── api/
│   ├── webhook.py             # Webhook handling + signature verification
│   └── websocket.py           # WebSocket connection manager
├── agents/
│   ├── langgraph_agent.py     # State machine orchestrator
│   └── nodes.py               # Individual processing nodes
├── services/
│   ├── rag_service.py         # Vector DB operations
│   └── github_service.py      # GitHub API client
├── models/
│   └── schemas.py             # Pydantic models
└── scripts/
    ├── init_vectordb.py       # Initialize RAG database
    └── test_webhook.py        # Test webhook locally
```

## API Endpoints

### Core Endpoints

- `GET /` - Root endpoint with service info
- `GET /health` - Health check + connection stats
- `POST /webhook/github` - GitHub webhook receiver
- `WS /ws` - WebSocket for real-time updates

### Draft Management

- `GET /api/drafts/pending` - List pending drafts
- `GET /api/drafts/{id}` - Get specific draft
- `POST /api/drafts/{id}/approve` - Approve and post to GitHub
- `POST /api/drafts/{id}/reject` - Reject draft
- `POST /api/drafts/{id}/edit-approve` - Edit and approve

## LangGraph Flow

```
START → classify_issue → [BUG/QUESTION] → retrieve_context → generate_solution → AWAIT_APPROVAL
                       → [FEATURE] → generate_solution → AWAIT_APPROVAL
```

### Node Descriptions

1. **classify_issue**: Analyzes issue and categorizes as BUG, FEATURE, or QUESTION
2. **retrieve_context**: Searches vector DB for relevant documentation (conditional)
3. **generate_solution**: Creates draft response using LLM with context

## WebSocket Protocol

### Message Types

**state_update**: Agent processing update
```json
{
  "type": "state_update",
  "data": {
    "issue_id": "123456789",
    "processing_stage": "classifying",
    "classification": "BUG",
    "draft_response": "..."
  },
  "timestamp": "2025-12-24T12:00:00Z"
}
```

**error**: Error notification
```json
{
  "type": "error",
  "message": "Error description",
  "timestamp": "2025-12-24T12:00:00Z"
}
```

**connection**: Connection confirmation
```json
{
  "type": "connection",
  "message": "Connected to GitHub Triage Agent",
  "timestamp": "2025-12-24T12:00:00Z"
}
```

## Testing Without OpenAI

The backend works without OpenAI API key in mock mode:
- Classification uses keyword matching
- Context retrieval returns mock data
- Response generation uses templates

This allows full testing of webhook → websocket → frontend flow.

## Security

### Webhook Verification

```python
# Automatic HMAC-SHA256 signature verification
# Set GITHUB_WEBHOOK_SECRET in .env
# Matches GitHub's X-Hub-Signature-256 header
```

### Token-Based Approval

Draft responses include approval tokens to prevent unauthorized posting.

## Monitoring

Check logs for:
- Webhook signature failures
- LLM API errors
- WebSocket disconnections
- Processing times

```bash
# View logs in real-time
tail -f logs/app.log  # If file logging configured

# Or in console when running with --reload
```