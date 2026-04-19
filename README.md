# Adaptive Learning Content System

**Agent-driven pipeline for generating, evaluating, and refining educational content**

## Overview

This system implements two AI agents that work together to produce high-quality educational content:

1. **Generator Agent** — Creates age-appropriate educational content (explanations + MCQs)
2. **Reviewer Agent** — Evaluates content for quality, accuracy, and appropriateness

If the Reviewer returns a `fail` status, the Generator is re-run with the feedback embedded. Refinement is limited to one pass.

## Architecture

```
+-----------------------------------------------------------+
|                     Streamlit UI                          |
|  (Input: Grade & Topic  ->  Trigger Pipeline)             |
+----------------------------+------------------------------+
                             |
                             v
+-----------------------------------------------------------+
|                Orchestrator (Pipeline)                     |
|                                                           |
|   +--------------+       +--------------+                 |
|   |  Generator   | ----> |  Reviewer    |                 |
|   |   Agent      |       |   Agent      |                 |
|   +--------------+       +------+-------+                 |
|                                 |                         |
|                          Status: Pass?                    |
|                            /        \                     |
|                         Yes          No                   |
|                          |            |                   |
|                       [Done]    Refine + Re-review        |
|                                 (1 pass max)              |
+-----------------------------------------------------------+
                             |
                             v
+-----------------------------------------------------------+
|  Output Display                                           |
|  - Generated Content & Feedback                           |
|  - Refined Output (if applicable)                         |
|  - Export as JSON                                         |
+-----------------------------------------------------------+
```

## Project Structure

```
Eklavya.me/
├── agents/
│   ├── __init__.py          # Package exports
│   ├── generator.py         # GeneratorAgent class
│   ├── reviewer.py          # ReviewerAgent class
│   └── orchestrator.py      # Pipeline orchestration
├── ui/
│   └── app.py               # Streamlit web interface
├── config.py                # Configuration constants
├── example_usage.py         # CLI example for testing without UI
├── requirements.txt         # Python dependencies
├── .env.example             # API key template
├── .gitignore
└── README.md
```

## Setup

### Prerequisites

- Python 3.8+
- OpenAI API key ([platform.openai.com/api-keys](https://platform.openai.com/api-keys))

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API key:**
   ```bash
   cp .env.example .env
   # Edit .env and set OPENAI_API_KEY
   ```

   Or set the environment variable directly:
   ```bash
   # Windows (PowerShell):
   $env:OPENAI_API_KEY = "sk-..."

   # Linux/Mac:
   export OPENAI_API_KEY=sk-...
   ```

## Usage

### Web UI

```bash
streamlit run ui/app.py
```

The application opens at `http://localhost:8501`.

1. Select a **Grade Level** (1-12)
2. Enter a **Topic** (e.g., "Types of angles")
3. Click **Run Pipeline**
4. View results across three tabs:
   - **Generated Content** — explanation + MCQs
   - **Reviewer Feedback** — pass/fail with specific feedback items
   - **Refinement** — improved content if the initial output failed review
5. Download results as JSON

### Programmatic Usage

```python
from agents.orchestrator import Orchestrator

orchestrator = Orchestrator(api_key="sk-...")
result = orchestrator.run_pipeline(grade=4, topic="Types of angles")

print(result["generator_output"])
print(result["initial_reviewer_output"])
print(result["refined_output"])
print(result["final_status"])
```

### CLI Example

```bash
python example_usage.py
```

Runs two sample inputs and saves results as JSON files.

## Agent Specifications

### Generator Agent

**Input:**
```json
{
    "grade": 4,
    "topic": "Types of angles"
}
```

**Output:**
```json
{
    "explanation": "An angle is formed when two rays meet at a point...",
    "mcqs": [
        {
            "question": "What is an acute angle?",
            "options": ["Less than 90 degrees", "Exactly 90 degrees", "More than 90 degrees", "Exactly 180 degrees"],
            "answer": "A"
        }
    ]
}
```

### Reviewer Agent

**Input:** Content JSON from the Generator Agent.

**Output:**
```json
{
    "status": "pass",
    "feedback": [
        "Sentence 2 is too complex for Grade 4",
        "Question 3 tests a concept not introduced"
    ]
}
```

## Configuration

Both agents use `gpt-4o-mini` by default. To change the model, edit the `self.model` attribute in `agents/generator.py` and `agents/reviewer.py`.

Refinement is limited to **1 pass** by design. This is enforced in `agents/orchestrator.py`.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `OPENAI_API_KEY not set` | Set via `.env` file or environment variable |
| `Invalid JSON response` | Re-run; LLM output can be non-deterministic |
| Slow generation | System makes 2-3 LLM calls per run; use a faster model if needed |

## Limitations

- Content quality depends on the underlying LLM
- Refinement is limited to one pass to prevent infinite loops
- MCQs always have exactly 4 options with a single correct answer
- Requires a valid OpenAI API key with available credits

## License

This project is part of the Eklavya.me internship project.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review example usage in the UI
3. Check OpenAI API documentation (https://platform.openai.com/docs)
