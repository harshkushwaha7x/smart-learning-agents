# Governed AI Content Pipeline

A deterministic, auditable AI pipeline for structured educational content generation.

Production-grade AI pipeline for generating, evaluating, and refining educational content with full auditability.

## Overview

Four AI agents orchestrated through a deterministic pipeline with strict governance:

| Agent | Role |
|-------|------|
| **Generator** | Produces schema-validated educational content (explanation + MCQs + teacher notes) with grade-appropriate language |
| **Reviewer** | Quantitative evaluation across 4 criteria with explicit pass/fail thresholds |
| **Refiner** | Improves content based on structured reviewer feedback (max 2 refinement attempts) |
| **Tagger** | Classifies approved content with metadata (subject, difficulty, Bloom's level) |

**Every execution produces a complete `RunArtifact`** capturing input, all attempts (draft → review → refinement), final decision, and timestamps.

## Why This System

Focuses on reliability through schema validation, quantitative evaluation, bounded refinement, and full auditability via RunArtifact.

**Pipeline Flow:**
```
Generator → Reviewer → Refiner → Tagger → RunArtifact → DB
```

## Architecture

```
Input (grade + topic)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│                  Orchestrator                        │
│                                                     │
│  ┌───────────┐     ┌───────────┐     ┌───────────┐  │
│  │ Generator │ ──▶ │ Reviewer  │ ──▶ │  Refiner  │  │
│  │  (schema  │     │ (scoring  │     │ (bounded  │  │
│  │  + retry) │     │  + pass/  │     │  max 2)   │  │
│  │           │     │   fail)   │     │           │  │
│  └───────────┘     └─────┬─────┘     └───────────┘  │
│                     Pass? │                          │
│                    ┌──────┴──────┐                   │
│                   Yes           No → Refine loop     │
│                    │                                 │
│                    ▼                                 │
│              ┌───────────┐                           │
│              │  Tagger   │ (approved only)            │
│              └───────────┘                           │
│                    │                                 │
│                    ▼                                 │
│              RunArtifact                             │
└─────────────────────────────────────────────────────┘
        │
        ▼
   FastAPI + SQLite
```

## Scoring Criteria

The Reviewer evaluates on a 1–5 scale:

| Criterion | What it measures |
|-----------|-----------------|
| Age Appropriateness | Language complexity, vocabulary, and concepts relative to grade level |
| Correctness | Factual accuracy of explanations and MCQ answers |
| Clarity | Readability and unambiguity of explanations and questions |
| Coverage | Depth and breadth of topic coverage |

**Pass criteria:** average ≥ 4.0 AND no individual score < 3.

## Project Structure

```
├── agents/
│   ├── generator.py       # Content generation with retry
│   ├── reviewer.py        # Quantitative evaluation
│   ├── refiner.py         # Feedback-driven refinement
│   ├── tagger.py          # Metadata classification
│   └── orchestrator.py    # Pipeline orchestration
├── schemas/
│   └── models.py          # Pydantic models and enums
├── api/
│   └── backend.py         # FastAPI endpoints
├── storage/
│   └── store.py           # SQLite persistence
├── tests/
│   └── test_pipeline.py   # 20+ test cases
├── ui/
│   └── app.py             # Streamlit interface
├── config.py              # Centralized configuration
├── run_api.py             # API launcher
├── example_usage.py       # CLI example
└── requirements.txt
```

## Setup

### Prerequisites

- Python 3.8+
- OpenAI API key ([platform.openai.com/api-keys](https://platform.openai.com/api-keys))

### Installation

```bash
pip install -r requirements.txt
```

### Configure API key

```bash
# Copy template and edit
cp .env.example .env

# Or set directly (PowerShell)
$env:OPENAI_API_KEY = "sk-..."

# Or set directly (Linux/Mac)
export OPENAI_API_KEY=sk-...
```

## Usage

### FastAPI Backend

```bash
python run_api.py
```

Available at `http://localhost:8000`. Interactive docs at `/docs`.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/generate` | Run full pipeline, returns RunArtifact |
| GET | `/history` | Paginated artifact history (optional user_id filter) |
| GET | `/artifact/{run_id}` | Retrieve specific RunArtifact |
| GET | `/health` | Health check |
| GET | `/stats` | Pipeline statistics |

### Streamlit UI

```bash
streamlit run ui/app.py
```

### Programmatic Usage

```python
from agents.orchestrator import Orchestrator

orchestrator = Orchestrator(api_key="sk-...")
artifact = orchestrator.execute(grade=5, topic="Fractions")

print(artifact.final.status.value)   # "approved" or "rejected"
print(len(artifact.attempts))        # number of attempts taken
print(artifact.model_dump_json())    # full audit trail as JSON
```

### CLI Example

```bash
python example_usage.py
```

## Running Tests

```bash
pytest tests/ -v
```

All tests use mocked LLM calls and cover:
- Schema validation failure handling
- Generator retry on validation errors
- Reviewer quantitative scoring
- Fail → refine → pass workflow
- Fail → refine → fail → reject workflow
- Tagger only runs on approved content
- Storage round-trip (write / read)
- API endpoint validation

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Max 2 refinement attempts | Prevents infinite loops while allowing recovery from marginal failures |
| Typed `FinalResult` model | Eliminates untyped `Dict[str, Any]` — all fields are schema-validated |
| Generator retry (1 max) | LLM outputs can be non-deterministic; a single retry handles transient parsing failures |
| Centralized config | Scoring thresholds, model names, and temperatures are defined once in `config.py` |
| Severity/Difficulty/BloomsLevel enums | Prevents invalid free-text values in review feedback and tags |

## Limitations

- Content quality depends on the underlying LLM
- MCQs are fixed at 4 options with a single correct answer
- Requires a valid OpenAI API key with available credits
- SQLite storage is suitable for development; production should use PostgreSQL
