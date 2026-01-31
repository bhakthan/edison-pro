# EDISON PRO - Copilot Instructions

## Project Overview
EDISON PRO is an engineering diagram analysis tool that uses AI to extract, analyze, and understand technical drawings (P&ID, electrical schematics, civil plans, etc.).

## Tech Stack
- **Backend**: Python 3.10+, FastAPI, Azure OpenAI (o3-pro), Azure AI Search, Azure Document Intelligence
- **Frontend**: Vite, React, TypeScript, Tailwind CSS, Recharts
- **Infrastructure**: Azure Blob Storage, Azure AI Search (vector + keyword hybrid search)

## Key Architecture
- `edisonpro.py` - Main CLI entry point
- `api.py` / `api_server.py` - FastAPI REST API
- `edisonpro_ui.py` - Gradio web interface
- `agents/` - AI agent modules (flickering system, memory atlas, etc.)
- `frontend/` - React + TypeScript frontend

## Code Conventions
- Use type hints in Python
- Follow PEP 8 style guidelines
- Use async/await for API calls
- Environment variables for all secrets (see `.env.example`)

## Running the Project
```bash
# Backend API
python api.py

# Gradio UI (alternative)
python edisonpro_ui.py

# Frontend
cd frontend && npm run dev
```

## Environment Setup
Copy `.env.example` to `.env` and configure Azure credentials.
