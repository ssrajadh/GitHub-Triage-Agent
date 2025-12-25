# GitHub Triage Agent

Intelligent Workflow Automation for Engineering Incident Response - An AI-powered system that automatically triages GitHub issues using LangGraph and RAG.

## Overview

The GitHub Triage Agent is an event-driven AI application that:
- Intercepts GitHub issue webhooks in real-time
- Uses LangGraph state machine for intelligent routing (BUG/FEATURE/QUESTION)
- Retrieves relevant context from your codebase using RAG (ChromaDB + OpenAI)
- Generates draft responses using GPT-5-nano
- Implements Human-in-the-Loop approval via React dashboard
- Posts approved responses to GitHub automatically

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   GitHub    │────────▶│   FastAPI    │────────▶│  LangGraph  │
│   Webhook   │         │   Backend    │         │    Agent    │
└─────────────┘         └──────────────┘         └─────────────┘
                               │                         │
                               │                         ▼
                               │                  ┌─────────────┐
                               │                  │  ChromaDB   │
                               │                  │  RAG Store  │
                               │                  └─────────────┘
                               ▼
                        ┌──────────────┐
                        │   WebSocket  │
                        │  Real-time   │
                        └──────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │    React     │
                        │  Dashboard   │
                        └──────────────┘
```

## Project Structure

```
GitHub-Triage-Agent/
├── .gitignore               # Git ignore rules
│
├── backend/                 # FastAPI backend
│   ├── main.py             # Application entry point
│   ├── requirements.txt    # Python dependencies
│   ├── start.sh           # Quick start script
│   │
│   ├── agents/            # LangGraph agent
│   │   ├── langgraph_agent.py  # State machine
│   │   └── nodes.py            # Processing nodes
│   │
│   ├── api/               # API endpoints
│   │   ├── webhook.py     # GitHub webhook handler
│   │   └── websocket.py   # WebSocket manager
│   │
│   ├── models/            # Data models
│   │   └── schemas.py     # Pydantic schemas
│   │
│   ├── services/          # External services
│   │   ├── rag_service.py     # Vector DB operations
│   │   └── github_service.py  # GitHub API client
│   │
│   └── scripts/           # Utility scripts
│       ├── init_vectordb.py   # RAG initialization
│       └── test_webhook.py    # Local testing
│
└── frontend/              # React + TypeScript dashboard
    ├── src/
    │   ├── components/    # React components
    │   ├── hooks/        # Custom hooks (WebSocket)
    │   ├── services/     # API client
    │   └── types/        # TypeScript types
    └── package.json
```

## How It Works

1. **Webhook Receives Issue**: GitHub sends `issue.opened` event
2. **Signature Verification**: HMAC-SHA256 validation ensures authenticity
3. **LangGraph Processing**:
   - **Node 1**: Classify issue (BUG/FEATURE/QUESTION)
   - **Node 2**: Retrieve context from vector DB (conditional)
   - **Node 3**: Generate draft response using GPT-5-nano
4. **WebSocket Broadcast**: Real-time updates to dashboard
5. **Human Review**: Engineer approves/edits/rejects on dashboard
6. **Post to GitHub**: Approved response posted as comment

## Security Features

- HMAC-SHA256 webhook signature verification
- Token-based approval workflow
- Human-in-the-Loop safety gate
- No direct GitHub write access without approval
- Environment variable isolation

## Features

### Backend (FastAPI)
- Async webhook processing
- WebSocket real-time updates
- LangGraph state machine
- RAG with ChromaDB
- GitHub API integration
- Comprehensive error handling

### Frontend (React + TypeScript)
- Live issue feed
- Side-by-side diff viewer
- One-click approve/reject
- Edit before approval
- Real-time WebSocket updates
- Auto-reconnection