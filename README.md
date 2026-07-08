# Autonomous AI Agent — Document Generation Pipeline

A production-quality autonomous AI agent that accepts natural language requests, creates its own task plan, executes each step, self-reflects on quality, and produces a polished Microsoft Word (`.docx`) document.

---

## Architecture

```
POST /api/v1/agent
        │
        ▼
  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
  │   Planner   │────▶│  Executor   │────▶│  Reflector  │────▶│ Doc Builder │
  │             │     │             │     │             │     │             │
  │ LLM → JSON  │     │ Task loop   │     │ Quality     │     │ python-docx │
  │ task plan   │     │ sequential  │     │ score + fix │     │ → .docx     │
  └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### Pipeline Stages

| Stage | File | Responsibility |
|-------|------|----------------|
| **Plan** | `agent/planner.py` | LLM generates a structured JSON task list with document type, title, objective, and assumptions |
| **Execute** | `agent/executor.py` | Each task runs sequentially; prior outputs accumulate as context for the next task |
| **Reflect** | `agent/reflector.py` | LLM self-reviews all outputs, scores quality 0–10, identifies gaps, revises weak sections |
| **Build** | `agent/doc_builder.py` | Assembles a formatted Word document with cover page, executive summary, sections, and appendix |

---

## Engineering Improvement: Multi-step Planning + Reflection

### What was implemented

The agent runs a **two-pass LLM loop**:

1. **Planning pass** — Before executing any work, the LLM generates a structured JSON task plan that defines discrete, ordered steps. This forces explicit reasoning about what needs to be done before doing it.

2. **Reflection pass** — After all tasks execute, the LLM acts as a senior editor: it reviews every task output, assigns a 0–10 quality score, lists gaps, and generates revised content for any section scoring below threshold. Revised content is injected back into the plan before the document is built.

### Why this approach

Multi-step planning forces the agent to decompose complex problems rather than hallucinate a single monolithic response. The reflection pass catches shallow content, missing sections, and inconsistencies — common failure modes of single-shot generation — without requiring the user to re-run the pipeline.

### How it improves the agent

| Without reflection | With reflection |
|--------------------|-----------------|
| Shallow sections go undetected | Gaps are identified and flagged |
| User must manually verify quality | Agent self-certifies with a score |
| No targeted revision | Weak sections are auto-regenerated |
| Single-shot, no iteration | Two-pass reasoning loop |

---

## Setup

### 1. Clone it

### 2. Create virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
copy .env.example .env
# Edit .env and set your GOOGLE_API_KEY
```

Get a free Gemini API key at: https://aistudio.google.com/app/apikey

### 5. Run the API

```bash
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

---

## API Reference

### `POST /api/v1/agent`

**Request:**
```json
{ "request": "Create a project proposal for a customer loyalty app..." }
```

**Response:**
```json
{
  "request_id": "a3f1b2c4",
  "document_type": "Project Proposal",
  "document_title": "Customer Loyalty Mobile App — Project Proposal",
  "objective": "...",
  "assumptions": ["...", "..."],
  "tasks": [
    { "id": 1, "title": "Context & Requirements Gathering", "status": "done", "output": "..." }
  ],
  "reflection": { "passed": true, "score": 8, "gaps": [], "improvements": [] },
  "document_filename": "Customer_Loyalty_Mobile_App_Project_Proposal.docx",
  "document_base64": "<base64-encoded .docx>",
  "status": "success"
}
```

### `POST /api/v1/agent/download`

Same as above but returns the `.docx` file directly as a download.

### `GET /api/v1/health`

```json
{ "status": "ok", "service": "autonomous-agent" }
```

---

## Test Inputs

```bash
python -m tests.test_inputs
```

### Test 1 — Standard Request

> *"Create a project proposal for building a customer loyalty mobile app for a mid-sized retail chain. The app should include points tracking, reward redemption, and push notifications. Budget is $150,000 and the timeline is 6 months."*

Clear, well-scoped request. Agent produces a structured project proposal with minimal assumptions.

### Test 2 — Complex / Ambiguous Request

> *"We need some kind of document about expanding to new markets. Not sure if it should be a report or a plan. The CEO wants it ASAP but also wants it to be thorough. We're a SaaS company but I can't tell you which markets yet. Also legal said something about compliance but I don't know the details. Make it look professional."*

Deliberately ambiguous: no document type, no markets named, conflicting urgency/thoroughness requirements, vague compliance concern. The agent:
- Decides the document type autonomously (Market Expansion Strategy)
- States all assumptions explicitly (which markets, compliance framework, etc.)
- Proceeds with realistic mock data
- Flags remaining gaps in the reflection appendix

---

## Project Structure

```
E:\Fluid Ai\
├── main.py                  # FastAPI app entry point
├── requirements.txt
├── .env.example
├── core/
│   ├── config.py            # Pydantic settings
│   └── llm.py               # Gemini client with retry logic
├── agent/
│   ├── models.py            # Shared Pydantic models
│   ├── planner.py           # Stage 1: task plan generation
│   ├── executor.py          # Stage 2: sequential task execution
│   ├── reflector.py         # Stage 3: quality review + revision
│   ├── doc_builder.py       # Stage 4: Word document assembly
│   └── pipeline.py          # Orchestrator
├── api/
│   └── routes.py            # FastAPI routes + request validation
├── tests/
│   └── test_inputs.py       # Two demonstration test cases
└── outputs/                 # Generated .docx files (auto-created)
```

---

## Stack

- **LLM**: Gorq Lamma3.3 70B 
- **API**: FastAPI + Uvicorn
- **Document**: python-docx
- **Retry**: tenacity (exponential backoff, 3 attempts)
- **Validation**: Pydantic v2 with field validators + guardrails
