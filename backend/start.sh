#!/bin/bash
# Start the FastAPI backend server

# Navigate to backend directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Start server (will load .env from root via python-dotenv)
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
