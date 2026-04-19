# Quick Start

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Set API Key

**Option A: .env file**
```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY
```

**Option B: Environment variable**
```bash
# Windows (PowerShell):
$env:OPENAI_API_KEY = "sk-..."

# Linux/Mac:
export OPENAI_API_KEY=sk-...
```

## 3. Run the UI

```bash
streamlit run ui/app.py
```

Opens at `http://localhost:8501`.

## 4. Test

1. Set Grade to **4**
2. Set Topic to **Types of angles**
3. Click **Run Pipeline**
4. View results in the tabs

## Alternative: Run Without UI

```bash
python example_usage.py
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: streamlit` | Run `pip install -r requirements.txt` |
| `OPENAI_API_KEY not set` | See Step 2 above |
| `Invalid JSON response` | Re-run the pipeline |

See [README.md](README.md) for full documentation.
