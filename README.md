
# Environmental AI Scientist

A complete VS Code-ready RAG environmental intelligence website.

## Features
- Real retrievable knowledge layer using TF-IDF vectorization + cosine similarity.
- Structured environmental metrics in JSON.
- Multi-turn conversation memory.
- Clarifying questions for missing variables.
- Multi-metric reasoning across soil, climate, land use, biodiversity and human impact.
- Evidence-backed recommendations with source metadata.
- Text and JSON input.
- Optional OpenAI integration; the app works without an API key using its local reasoning engine.
- No Node.js/npm required.

## Run in VS Code

Requirements: Python 3.10+.

### Windows PowerShell
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

If PowerShell activation is blocked:
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:8000

Click **Load Example**, then **Analyze Environment**.

## Optional LLM mode
Copy `.env.example` to `.env` and add an API key. Without a key, the local RAG + reasoning engine is used.

## Architecture
Knowledge documents -> TF-IDF vectorization -> cosine retrieval -> environmental state -> multi-metric reasoning -> recommendations -> cited response.

## API
GET /api/health
GET /api/knowledge
POST /api/analyze
POST /api/chat
POST /api/reset/{session_id}

## Example JSON
{
  "soil": {"ph": 6.5, "organic_carbon": 0.3, "moisture": 12},
  "climate": {"temperature": 29, "rainfall": 480},
  "land": {"crop": "wheat", "land_use": "monoculture"},
  "biodiversity": {"species_richness": 5, "habitat_diversity": "low"},
  "human_impact": {"pollution": "medium", "deforestation": "low"},
  "location": "Semi-arid agricultural region"
}

Scientific effect sizes are intentionally not invented. Site-specific improvements depend on soil, climate, species, management and study design.
