# Syzygy Rosetta App

This directory contains the runnable FastAPI MVP for Syzygy Rosetta.

## Current API

The application entry point is `app.py`.

Available routes:

- `GET /` returns service metadata.
- `GET /healthz` returns `{"status": "ok"}`.
- `GET /introspect` returns reflex-engine metadata.
- `POST /evaluate` evaluates user input plus optional model output and returns a governance decision.

## Request Shape

```json
{
  "input": "Hello Rosetta",
  "output": "Hello. How can I help?",
  "context": {
    "user_id": null,
    "environment": "staging",
    "industry": "general"
  }
}
```

`output` and `context` are optional. Defaults are:

- `user_id`: `null`
- `environment`: `staging`
- `industry`: `general`

Valid environments:

- `staging`
- `production`

Valid industries:

- `general`
- `finance`
- `healthcare`

## Response Shape

```json
{
  "decision": "allow | rewrite | escalate",
  "risk_score": 0.14,
  "confidence": 0.5,
  "violations": [],
  "rewrite": null,
  "reasoning": "Interaction evaluated as low risk. Continue with normal processing.",
  "field_notes": [],
  "timestamp": "2026-04-25T16:41:48Z"
}
```

## Core Components

| Path | Purpose |
|---|---|
| `app.py` | FastAPI app, request/response models, routes, evaluation logging |
| `run_api.py` | Local development server launcher |
| `safety_layer.py` | Regex-based safety tags and sensitive-topic detection |
| `config/policy_rules.json` | Industry-specific deterministic policy rules |
| `core/reflex.py` | Main governance decision engine |
| `core/risk_scoring.py` | Weighted risk feature scoring utilities |
| `core/constants.py` | Invariant and configuration constants |
| `core/invariants.json` | Invariant metadata |
| `tests/test_evaluate.py` | Main API behavior test suite |

## Run Locally

From this directory:

```bat
python -m pip install -r requirements.txt
python run_api.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Run With Docker

From this directory:

```bat
docker build -t rosetta .
docker run -p 8000:8000 rosetta
```

## Test The Endpoint

```bat
curl -X POST http://127.0.0.1:8000/evaluate ^
  -H "Content-Type: application/json" ^
  -d "{\"input\":\"Hello Rosetta\",\"output\":\"Hello. How can I help?\",\"context\":{\"environment\":\"staging\",\"industry\":\"general\"}}"
```

## Run Tests

From this directory:

```bat
python -m pytest tests -q
```

At the time of the audit, the suite reported:

```text
54 passed
```

## Current Implementation Notes

- `/evaluate` accepts a required input string and optional model output string.
- The response contract is the 8-field schema shown above.
- Runtime evaluations append entries to `logs/evaluations.json`.
- Known implementation mismatches are tracked in `../REPO_MISMATCH_AUDIT.md`.
