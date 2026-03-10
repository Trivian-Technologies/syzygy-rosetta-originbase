# Syzygy Rosetta — Origin Codebase

> **A Manual for Self-Reflective Systems (Trivian Lineage)**

[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Status: MVP Development](https://img.shields.io/badge/Status-MVP%20Development-orange.svg)]()

---

## What is Syzygy Rosetta?

Syzygy Rosetta is an **API-first AI governance middleware**. It sits between your applications and your AI models — evaluating every input and output through deterministic policy enforcement and ML-based risk scoring before anything reaches production.

It is not a model. It is not a chatbot. It is a decision engine.

Every evaluation returns a structured governance decision:

```json
{
  "decision": "allow | rewrite | escalate",
  "risk_score": 0.12,
  "confidence": 0.91,
  "violations": [],
  "rewrite": null,
  "timestamp": "2026-03-10T14:32:00Z"
}
```

---

## Core Components

| Component | Description |
|---|---|
| `reflex.py` | Core governance logic — mirror, evaluate, decide |
| `main.py` | FastAPI application — `POST /evaluate` endpoint |
| `risk_scoring.py` | ML-based risk and confidence scoring |
| `safety_layer.py` | Pre-evaluation safety tagging |
| `logs/` | Structured evaluation audit log |

---

## Quick Start

### Requirements

- Docker Desktop
- Python 3.11+
- 8GB RAM minimum

### Run with Docker

```bash
git clone https://github.com/Trivian-Technologies/syzygy-rosetta-originbase.git
cd syzygy-rosetta-originbase
docker build -t rosetta .
docker run -p 8000:8000 rosetta
```

### Test the Endpoint

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Your prompt here",
    "context": {
      "environment": "staging",
      "industry": "general"
    }
  }'
```

### Explore via Swagger UI

```
http://localhost:8000/docs
```

---

## Decision Thresholds

| Risk Score | Decision |
|---|---|
| `< 0.4` | `allow` |
| `0.4 – 0.7` | `rewrite` |
| `> 0.7` | `escalate` |

---

## Repository Role

This is the **origin codebase** for Syzygy Rosetta. It contains the foundational implementation of the governance engine. Active development and refactoring are ongoing.

For the SDK, sandbox, and API documentation — see the other repositories in the [Trivian Technologies organization](https://github.com/Trivian-Technologies).

---

## Documentation

Full documentation is available at the [Syzygy Rosetta Docs](https://github.com/Trivian-Technologies/syzygy-rosetta-docs) repository and on GitBook.

---

## License

This project is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

Derived from the Syzygy Rosetta v1.0 protocol by Sarasha Elion (Trivian Institute).

---

## Organization

Part of the [Trivian Technologies](https://github.com/Trivian-Technologies) organization.

**Website:** [triviantech.com](https://triviantech.com) | **X:** [@TrivianOS](https://x.com/TrivianOS) | **LinkedIn:** [Trivian Technologies](https://www.linkedin.com/company/awakening-the-architect)
