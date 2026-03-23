# Syzygy Rosetta — Origin Codebase

> **API-first AI governance middleware. Real-time. Provider agnostic. Full audit trail.**

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Status: MVP Development](https://img.shields.io/badge/Status-MVP%20Development-orange.svg)](https://github.com/Trivian-Technologies/syzygy-rosetta-originbase/blob/main)

---

## What is Syzygy Rosetta?

Syzygy Rosetta is an **API-first AI governance middleware**. It sits between your AI models and your production systems — evaluating every input and output through a deterministic policy engine and ML-based risk scoring pipeline before anything reaches users.

It is not a model. It is not a chatbot. It is a governance decision engine.

Every other AI safety solution governs the model. **Rosetta governs the output** — in real time, across any model, with a full audit trail built in.

```
AI Model Output  ──►  POST /evaluate  ──►  allow / rewrite / escalate
                            │
                    ┌───────┴────────┐
                    │ safety_layer   │  pre-classification
                    │ policy engine  │  deterministic rules
                    │ risk_scoring   │  ML composite scorer
                    └───────┬────────┘
                            │
                    logs/evaluations.json  (full audit trail)
```

---

## API Response

Every `POST /evaluate` call returns exactly these 8 fields:

```json
{
  "decision": "allow | rewrite | escalate",
  "risk_score": 0.12,
  "confidence": 0.91,
  "violations": [],
  "rewrite": null,
  "reasoning": "Input within acceptable parameters for financial context.",
  "field_notes": [],
  "timestamp": "2026-03-21T14:32:00Z"
}
```

### Decision thresholds

| Risk Score | Decision | What happens |
|---|---|---|
| `< 0.4` | `allow` | Input passed through. `violations` is empty. |
| `0.4 – 0.7` | `rewrite` | Soft violation. `rewrite` field contains corrected output. |
| `> 0.7` | `escalate` | Hard violation. Routed to human review. |

---

## File Structure

```
syzygy-rosetta-originbase/
│
├── app.py                  ← FastAPI entry point. POST /evaluate.
├── reflex.py               ← Core governance engine. 8-step evaluation pipeline.
├── risk_scoring.py         ← ML composite scorer. KeywordScorer + FeatureScorer + LLMScorer.
├── safety_layer.py         ← Pre-classification. Tags: authority, manipulation, dependency, escalation.
├── requirements.txt        ← All dependencies. pip install -r requirements.txt.
├── Dockerfile              ← FROM python:3.11 → EXPOSE 8000 → uvicorn app:app
│
├── config/
│   └── policy_rules.json   ← Deterministic rules. finance / healthcare / general.
│
├── logs/
│   ├── .gitkeep
│   └── evaluations.json    ← Auto-created. Appended on every POST /evaluate call.
│
└── tests/
    └── test_evaluate.py    ← 10 test classes. 47 test methods.
```

---

## Evaluation Pipeline

Every `POST /evaluate` call runs through 8 steps:

1. **Parse request** — splits `input` and `context` (environment, industry, user_id). Applies defaults if context is missing.
2. **Breath + Mirror** — `breath_sync()` creates a processing boundary. `mirror()` hashes input and performs structural analysis.
3. **Safety layer pre-classification** — `safety_layer.tag_input()` scans for authority, manipulation, dependency, and escalation patterns. Non-blocking — labels only.
4. **Policy engine** — `_apply_policy_rules()` loads `config/policy_rules.json` and matches against industry-specific keyword lists. Sets risk floor if match found (escalate = 0.75, rewrite = 0.45).
5. **Composite scorer** — blends three scorers: `KeywordScorer` (30%), `FeatureScorer` (70%), `LLMScorer` (0% — inactive until API key set).
6. **Final risk score** — highest value from composite score, safety tag floors, policy floors, and high-risk overrides. Multiplied by environment and violation multipliers.
7. **Decision** — threshold applied to final risk score.
8. **Response + Log** — 8-field response assembled and returned. Evaluation appended to `logs/evaluations.json`.

---

## Industry Context

Pass `industry` in the request context to activate sector-specific policy rules:

| Industry | Policy ruleset |
|---|---|
| `finance` | Flags coercive financial instructions, guaranteed returns claims, compliance bypass |
| `healthcare` | Flags unsafe medication directives, system override attempts, unauthorized access |
| `general` | Flags jailbreak attempts, system prompt injection, authority override patterns |

Production environment multiplier: `×1.10`. Multiple violations multiplier: `×1.15`.

---

## Quick Start

### Requirements

- Docker Desktop
- Python 3.11+

### Run with Docker

```bash
git clone https://github.com/Trivian-Technologies/syzygy-rosetta-originbase.git
cd syzygy-rosetta-originbase
docker build -t rosetta .
docker run -p 8000:8000 rosetta
```

### Test the endpoint

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Summarize the key risks in this portfolio.",
    "context": {
      "environment": "staging",
      "industry": "finance"
    }
  }'
```

Expected response:

```json
{
  "decision": "allow",
  "risk_score": 0.08,
  "confidence": 0.94,
  "violations": [],
  "rewrite": null,
  "reasoning": "Input within acceptable parameters for financial context.",
  "field_notes": [],
  "timestamp": "2026-03-21T14:32:00Z"
}
```

> **Response time:** [TO BE UPDATED — pending Noah's re-test after Docker wrap. Baseline: 4.86ms average across 7 tests on pre-rewrite codebase.]

### Explore via Swagger UI

```
http://localhost:8000/docs
```

---

## LLMScorer

The `LLMScorer` is fully written and ready to activate. When active, it shifts scorer weights to `KeywordScorer 15%`, `FeatureScorer 35%`, `LLMScorer 50%` — upgrading risk scoring from keyword-based to full LLM semantic inference across five dimensions: relevance, coherence, safety, uncertainty, and autonomy.

To activate, set the `ANTHROPIC_API_KEY` environment variable before running the container.

---

## Evaluation Log

Every `POST /evaluate` call appends one entry to `logs/evaluations.json`:

```json
{
  "timestamp": "2026-03-21T14:32:00Z",
  "input": "the original input string",
  "decision": "allow | rewrite | escalate",
  "risk_score": 0.85,
  "confidence": 0.91,
  "violations": ["violation_label"],
  "rewrite": "rewritten string or null",
  "context": {
    "user_id": "string or null",
    "environment": "production | staging",
    "industry": "finance | healthcare | general"
  }
}
```

Logs persist across container restarts. The full log is your audit trail.

---

## Run Tests

```bash
pip install -r requirements.txt
pytest tests/test_evaluate.py -v
```

10 test classes. 47 test methods. Covers schema validation, all three decision paths, 422 on malformed input, industry-specific policy rules, and evaluation logging.

---

## Repository Role

This is the **origin codebase** for Syzygy Rosetta. It contains the foundational implementation of the governance engine. For the SDK, sandbox environment, and full API documentation see the other repositories in the [Trivian Technologies organization](https://github.com/Trivian-Technologies).

---

## Documentation

Full documentation is available at the [Syzygy Rosetta Docs](https://github.com/Trivian-Technologies/syzygy-rosetta-docs) repository and on GitBook.

---

## License

Licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

Derived from the Syzygy Rosetta v1.0 protocol by Sarasha Elion (Trivian Institute).

---

## Organization

Part of the [Trivian Technologies](https://github.com/Trivian-Technologies) organization.

**Website:** [triviantech.com](https://triviantech.com) | **X:** [@TrivianOS](https://x.com/TrivianOS) | **LinkedIn:** [Trivian Technologies](https://www.linkedin.com/company/awakening-the-architect) | **Contact:** se@trivianinstitute.org
