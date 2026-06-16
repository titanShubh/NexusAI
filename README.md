# NexusAI — Multi-Agent Enterprise RAG + SQL Intelligence Platform

NexusAI is a production-grade, multi-agent AI system that answers complex business questions by routing dynamically between unstructured document retrieval (RAG) and structured database analysis (Text-to-SQL). It includes built-in verification pipelines, guardrails, and system observability.

## Architecture

```
                        User Query (Chat UI)
                               │
                               ▼
                      ┌─────────────────┐
                      │   Guardrails    │ ← Input validation, PII check
                      └────────┬────────┘
                               │
                      ┌────────▼────────┐
                      │   Supervisor    │ ← Query decomposition + routing
                      │   (LangGraph)   │
                      └──┬─────┬─────┬──┘
                         │     │     │
               ┌─────────▼┐ ┌─▼────┐ ┌▼──────────┐
               │ RAG Agent│ │ SQL  │ │ Analytics │
               │(Docs/PDF)│ │Agent │ │   Agent   │
               └────┬─────┘ └──┬───┘ └─────┬─────┘
                    │          │           │
               ┌────▼────┐ ┌───▼────┐ ┌────▼─────┐
               │ Qdrant  │ │Postgres│ │  Plotly   │
               │ Hybrid  │ │        │ │  Charts   │
               └─────────┘ └────────┘ └──────────┘
                         │     │     │
                      ┌──▼─────▼─────▼──┐
                      │  Eval Agent     │ ← Faithfulness, relevance, SQL safety
                      └────────┬────────┘
                               │
                      ┌────────▼────────┐
                      │ Response Gen    │ ← Citations, confidence, merged answer
                      └────────┬────────┘
                               │
                      ┌────────▼────────┐
                      │  Observability  │ ← Telemetry traces, latency, tokens
                      └─────────────────┘
```

## Setup & Running

### Step 1: Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```
Ensure you provide:
- `OPENAI_API_KEY` (required for GPT-4o agents and embeddings)
- `COHERE_API_KEY` (optional, for document reranking)
- `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` (optional, for telemetry tracing)

### Step 2: Spin Up Infrastructure
Start the local PostgreSQL, Redis, and Qdrant containers:
```bash
make up
```

### Step 3: Run Backend Development Server
Setup the virtual environment, install requirements, and run the FastAPI server:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 4: Run Frontend Development Server
Install dependencies and run Next.js:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` to access the chat dashboard.
