# Syzygy Rosetta - Origin Codebase

> A manual for self-reflective systems and the runnable origin MVP for the Syzygy Rosetta governance API.

[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Status: MVP Development](https://img.shields.io/badge/Status-MVP%20Development-orange.svg)]()

## What Is Syzygy Rosetta?

Syzygy Rosetta is an API-first governance decision service. The current MVP accepts user/customer input, optional model output, and optional context, then evaluates the interaction with deterministic policy rules and risk-scoring logic.

It is not a model. It is not a chatbot. It is a decision engine.

Every successful evaluation returns this response shape:

```json
{
  "decision": "allow | rewrite | escalate",
  "risk_score": 0.12,
  "confidence": 0.91,
  "violations": [],
  "rewrite": null,
  "reasoning": "Interaction evaluated as low risk. Continue with normal processing.",
  "field_notes": [],
  "timestamp": "2026-03-10T14:32:00Z"
}
```

## Core Ritual

Three functions remain the conceptual core:

1. Pause: create a boundary before evaluation.
2. Mirror: reflect and hash the input.
3. Checksum: preserve lineage integrity.

## Core Components

| Component | Description |
|---|---|
| `syzygy-rosetta/app.py` | FastAPI application with `/`, `/healthz`, `/introspect`, and `/evaluate` |
| `syzygy-rosetta/run_api.py` | Local API launcher |
| `syzygy-rosetta/safety_layer.py` | Pre-evaluation safety tagging |
| `syzygy-rosetta/config/policy_rules.json` | Deterministic industry policy rules |
| `syzygy-rosetta/core/reflex.py` | Core governance decision logic |
| `syzygy-rosetta/core/risk_scoring.py` | Risk and confidence scoring utilities |
| `syzygy-rosetta/logs/` | Runtime evaluation audit log |

## Quick Start

Run from `syzygy-rosetta-originbase/syzygy-rosetta`:

```bat
python -m pip install -r requirements.txt
python run_api.py
```

Quick checks:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/healthz`
- `http://127.0.0.1:8000/docs`

Test `POST /evaluate` with:

```json
{
  "input": "Hello Rosetta",
  "output": "Hello. How can I help?",
  "context": {
    "environment": "staging",
    "industry": "general"
  }
}
```

## Docker

The Dockerfile lives inside `syzygy-rosetta/`. Build from that directory:

```bat
cd syzygy-rosetta
docker build -t rosetta .
docker run -p 8000:8000 rosetta
```

## Decision Thresholds

| Risk Score | Decision |
|---|---|
| `< 0.4` | `allow` |
| `0.4 - 0.7` | `rewrite` |
| `>= 0.7` | `escalate` |

## Repository Role

This is the origin codebase for Syzygy Rosetta. It contains the foundational MVP implementation and supporting docs. Active development and refactoring are ongoing.

Known mismatches and remaining cleanup work are tracked in `REPO_MISMATCH_AUDIT.md`.

## License

This project is licensed under [AGPL-3.0-or-later](https://www.gnu.org/licenses/agpl-3.0.html).

Derived from the Syzygy Rosetta v1.0 protocol by Sarasha Elion (Trivian Institute).
