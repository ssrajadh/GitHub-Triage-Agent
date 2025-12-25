# FastAPI Backend - GitHub Triage Agent

Intelligent workflow automation backend for GitHub issue triage using LangGraph and RAG.

## Features

- **Webhook Handler**: Secure GitHub webhook receiver with HMAC-SHA256 verification
- **LangGraph Agent**: Cyclic state machine for intelligent issue routing
- **RAG System**: ChromaDB vector store for context retrieval
- **WebSocket Server**: Real-time updates to frontend dashboard
- **Human-in-the-Loop**: Approval workflow for AI-generated responses

## Quick Start

### Prerequisites
- Python 3.10+
- Virtual environment activated
- OpenAI API key (optional for testing)
- GitHub Personal Access Token

### Installation

```bash
# From project root, configure environment
cp .env.example .env
# Edit .env with your credentials

# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Environment variables are configured in the root `.env` file (not in backend directory).

See `.env.example` in project root for all available options.

```env
# Required for LLM features
OPENAI_API_KEY=sk-your-key-here

# Required for posting to GitHub
GITHUB_TOKEN=ghp_your-token-here

# Required for webhook security
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# Optional - defaults shown
API_HOST=0.0.0.0
API_PORT=8000
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

### Run Backend

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Test Webhook

```bash
# Update .env with GITHUB_WEBHOOK_SECRET=test-secret first
python scripts/test_webhook.py

# Or with custom parameters
python scripts/test_webhook.py --url http://localhost:8000/webhook/github --secret test-secret
```

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

## Troubleshooting

**Import errors after pip install**
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

**Webhook signature verification fails**
```bash
# Check GITHUB_WEBHOOK_SECRET matches GitHub settings
# For local testing, use: test-secret
```

**WebSocket won't connect**
```bash
# Check CORS settings in main.py
# Ensure frontend URL is in allow_origins list
```

**RAG returns empty context**
```bash
# Initialize vector database first
python scripts/init_vectordb.py --repo-path /path/to/repo
```

## Development

### Add New Node

```python
# In agents/nodes.py
async def new_node(state: Dict[str, Any]) -> Dict[str, Any]:
    # Process state
    state["new_field"] = "value"
    return state
```

### Add New Endpoint

```python
# In main.py
@app.get("/api/custom")
async def custom_endpoint():
    return {"data": "value"}
```

## Production Deployment

```bash
# Use production ASGI server
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker

# Or with Docker
docker build -t github-triage-agent .
docker run -p 8000:8000 --env-file .env github-triage-agent
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| OPENAI_API_KEY | No* | - | OpenAI API key for LLM |
| GITHUB_TOKEN | Yes | - | GitHub PAT for API |
| GITHUB_WEBHOOK_SECRET | Yes | - | Webhook HMAC secret |
| API_HOST | No | 0.0.0.0 | Server bind address |
| API_PORT | No | 8000 | Server port |
| CHROMA_PERSIST_DIRECTORY | No | ./chroma_db | Vector DB path |

*Not required for testing - will use mock mode
