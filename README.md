# GitHub Triage Agent

An intelligent AI agent that automatically triages GitHub issues and proposes solutions using ChatOps commands.

## Overview

The GitHub Triage Agent monitors your repository for new issues, analyzes them using LangGraph + RAG, and posts draft responses directly as GitHub comments. Maintainers interact with the bot using simple slash commands without leaving GitHub.

### Key Features

- **Automatic Issue Analysis**: Classifies issues as BUG, FEATURE, or QUESTION
- **Context-Aware Solutions**: Uses RAG to retrieve relevant documentation
- **ChatOps Interface**: All interaction via GitHub comments (`/approve`, `/revise`, `/reject`)
- **No Frontend Required**: Zero context switching, works on mobile
- **Production Ready**: Docker Compose setup with ngrok integration

## Architecture

```
GitHub Issue Created
    ↓
Webhook → FastAPI Backend
    ↓
LangGraph State Machine
    ├─ Classify Issue (BUG/FEATURE/QUESTION)
    ├─ Retrieve Context (RAG via ChromaDB)
    └─ Generate Solution (GPT-4)
    ↓
Post Draft Comment to GitHub
    ↓
Maintainer Commands:
    • /approve   → Remove draft markers
    • /revise    → Replace with maintainer text
    • /reject    → Delete comment
```

## Prerequisites

- Docker & Docker Compose
- OpenAI API Key ([Get one here](https://platform.openai.com/api-keys))
- GitHub Personal Access Token with `repo` scope
- Python 3.13+ (for local development)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/GitHub-Triage-Agent.git
cd GitHub-Triage-Agent
```

### 2. Configure Environment

Create `backend/.env`:

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-proj-...

# GitHub Configuration
GITHUB_TOKEN=ghp_...
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# Database
CHROMA_PERSIST_DIRECTORY=./chroma_db

# Backend
API_HOST=0.0.0.0
API_PORT=8000
```

### 3. Index Your Repository (Optional)

```bash
cd backend
python scripts/init_vectordb.py --repo-path /path/to/your/repo
```

### 4. Launch with Docker Compose

```bash
docker-compose up -d
```

This starts:
- **Backend**: FastAPI server on port 8000
- **Redis**: Caching layer on port 6379
- **Ngrok**: Public webhook URL (web UI on port 4040)

### 5. Get Ngrok URL

```bash
curl http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'
```

Or visit: http://localhost:4040

### 6. Configure GitHub Webhook

1. Go to your repo → Settings → Webhooks → Add webhook
2. **Payload URL**: `https://your-ngrok-url.ngrok.io/webhook/github`
3. **Content type**: `application/json`
4. **Secret**: Same as `GITHUB_WEBHOOK_SECRET` in `.env`
5. **Events**: Select "Issues" and "Issue comments"
6. Click "Add webhook"

### Creating an Issue

1. Create a new issue in your repository
2. The bot analyzes it within 30 seconds
3. Bot posts a draft response:

```markdown
**Draft Response** (not yet approved)

Based on the error message, this appears to be a race condition in the 
telemetry buffering system. The issue occurs when multiple threads access
the `TelemetryBuffer` without proper synchronization...

---
**Maintainer Actions:**
- Reply `/approve` to mark this as final
- Reply `/revise "your text"` to replace with your version
- Reply `/reject` to delete this draft
```

### Approving a Draft

Reply to the bot's comment:

```
/approve
```

The bot removes draft markers and the comment becomes final.

### Revising a Draft

Reply with your corrected text:

```
/revise "This is actually caused by a timeout in the connection pool. 
Please increase `max_pool_size` to 50 in config.yaml"
```

The bot replaces its entire comment with your text.

### Rejecting a Draft

Reply to delete the bot's comment:

```
/reject
```

## Project Structure

```
GitHub-Triage-Agent/
├── backend/
│   ├── agents/
│   │   ├── nodes.py                 # LangGraph nodes (classify, retrieve, generate)
│   │   └── langgraph_agent_chatops.py  # State machine (no WebSocket)
│   ├── api/
│   │   ├── chatops.py               # Command parser (/approve, /revise, /reject)
│   │   └── webhook_chatops.py       # Webhook handlers
│   ├── services/
│   │   ├── github_service.py        # GitHub API client
│   │   └── vectordb_service.py      # ChromaDB RAG service
│   ├── scripts/
│   │   └── init_vectordb.py         # Repository indexing tool
│   ├── main.py                      # FastAPI application
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
└── notes.md
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT models | ✅ |
| `GITHUB_TOKEN` | GitHub PAT with `repo` scope (from bot account or GitHub App) | ✅ |
| `GITHUB_WEBHOOK_SECRET` | Secret for webhook signature verification | ✅ |
| `CHROMA_PERSIST_DIRECTORY` | Path to ChromaDB storage | ❌ (default: `./chroma_db`) |
| `API_HOST` | Backend host address | ❌ (default: `0.0.0.0`) |
| `API_PORT` | Backend port | ❌ (default: `8000`) |

### LangGraph Configuration

Edit `backend/agents/nodes.py` to customize:

- **Classification Prompts**: Change how issues are categorized
- **RAG Retrieval**: Adjust top-k results or reranking logic
- **Solution Generation**: Modify GPT-4 system prompts

## Testing

### Manual Testing

```bash
# Test webhook endpoint
curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=..." \
  -d @test_payload.json

# Test command parsing
curl -X POST http://localhost:8000/test/parse-command \
  -H "Content-Type: application/json" \
  -d '{"comment_body": "/approve"}'
```

