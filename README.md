# Syzygy Rosetta - Origin Codebase

> API-first AI governance middleware MVP for evaluating submitted content through deterministic rules, safety tags, and risk scoring.

[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Status: MVP Development](https://img.shields.io/badge/Status-MVP%20Development-orange.svg)](https://github.com/Trivian-Technologies/syzygy-rosetta-originbase/blob/main)

## What Is Syzygy Rosetta?

Syzygy Rosetta is a FastAPI-based governance decision service. The current API accepts a required user/customer `input`, an optional model `output`, and optional context. It evaluates the interaction through safety tagging, deterministic policy rules, and risk scoring, then returns a structured decision:

- `allow`
- `rewrite`
- `escalate`

```text
user input + optional model output -> POST /evaluate -> allow / rewrite / escalate
                                                  |
                                                  +-> safety_layer.py
                                                  +-> config/policy_rules.json
                                                  +-> core/reflex.py
                                                  +-> logs/evaluations.json
```

## API Response

Every successful `POST /evaluate` response returns these 8 fields:

```json
{
  "decision": "allow | rewrite | escalate",
  "risk_score": 0.12,
  "confidence": 0.91,
  "violations": [],
  "rewrite": null,
  "reasoning": "Interaction evaluated as low risk. Continue with normal processing.",
  "field_notes": [],
  "timestamp": "2026-03-21T14:32:00Z"
}
```

## Decision Thresholds

| Risk Score | Decision | Behavior |
|---|---|---|
| `< 0.4` | `allow` | Interaction passes. `violations` is empty. |
| `0.4 - 0.7` | `rewrite` | Input or output should be clarified or rewritten. `rewrite` is populated. |
| `>= 0.7` | `escalate` | Interaction is routed to human review. `rewrite` is null. |

## File Structure

```text
syzygy-rosetta-originbase/
|
|-- README.md
|-- syzygy-rosetta-originbase.md
|-- REPO_MISMATCH_AUDIT.md
|
`-- syzygy-rosetta/
    |-- app.py                     FastAPI entry point
    |-- run_api.py                 local development launcher
    |-- safety_layer.py            pre-classification tags and sensitive-topic detection
    |-- requirements.txt           Python dependencies
    |-- Dockerfile                 container entrypoint for app:app
    |
    |-- config/
    |   `-- policy_rules.json      deterministic industry rules
    |
    |-- core/
    |   |-- reflex.py              governance decision engine
    |   |-- risk_scoring.py        weighted feature scoring utilities
    |   |-- constants.py           invariant/config constants
    |   |-- invariants.json        invariant metadata
    |   `-- resonators_mock.py     legacy/simple reflex mock
    |
    |-- docs/
    |   `-- demo_checklist.md
    |
    |-- example/
    |   `-- basic_usage.py
    |
    |-- logs/
    |   `-- evaluations.json       runtime audit log
    |
    `-- tests/
        |-- test_evaluate.py
        `-- test_healthz.py
```

## Evaluation Pipeline

Every `POST /evaluate` call currently follows this path:

1. FastAPI validates required `input`, optional `output`, and optional `context`.
2. `evaluate_prompt()` runs a breath pause and mirror step.
3. `safety_layer.tag_input()` labels authority, manipulation, dependency, and escalation patterns on input and output.
4. `detect_sensitive_topic()` checks self-harm, violence, and sexual-content patterns on input and output.
5. `_apply_policy_rules()` checks industry-specific rules from `config/policy_rules.json` on input and output.
6. The active scorer computes risk and confidence for the input-output pair.
7. Risk floors and multipliers are applied.
8. The API returns the 8-field response and appends an entry to `logs/evaluations.json`.

## Industry Context

Pass `industry` in the request context to activate sector-specific policy rules:

| Industry | Policy Rules |
|---|---|
| `finance` | Flags coercive financial instructions, guaranteed-return claims, compliance bypass, and market misconduct. |
| `healthcare` | Flags unsafe medication directives, system override attempts, and unauthorized access. |
| `general` | Flags jailbreak attempts, system prompt injection, unsafe security bypass requests, and harmful instructions. |

Production environment multiplier: `x1.10`. Multiple violations multiplier: `x1.15`.

## Quick Start

### Requirements

- Python 3.11+
- Docker Desktop, only if running the container

### Run Locally

Run these commands from `syzygy-rosetta-originbase/syzygy-rosetta`:

```bash
python -m pip install -r requirements.txt
python run_api.py
```

The local server starts at:

```text
http://127.0.0.1:8000
```

### Run With Docker

The Dockerfile currently lives inside `syzygy-rosetta/`, so build from that directory:

```bash
cd syzygy-rosetta
docker build -t rosetta .
docker run -p 8000:8000 rosetta
```

### Test The Endpoint

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Summarize the key risks in this portfolio.",
    "output": "The portfolio appears diversified, but review concentration and liquidity risks.",
    "context": {
      "environment": "staging",
      "industry": "finance"
    }
  }'
```

Example response shape:

```json
{
  "decision": "allow",
  "risk_score": 0.14,
  "confidence": 0.5,
  "violations": [],
  "rewrite": null,
  "reasoning": "Interaction evaluated as low risk. Continue with normal processing.",
  "field_notes": [
    "FIELD_NOTE [2026-04-25T16:41:48Z]: mirror invoked",
    "INTERNAL_NOTE [2026-04-25T16:41:48Z]"
  ],
  "timestamp": "2026-04-25T16:41:48Z"
}
```

### Explore Via Swagger UI

```text
http://localhost:8000/docs
```

## Evaluation Log

Every `POST /evaluate` call appends one entry to `syzygy-rosetta/logs/evaluations.json`:

```json
{
  "timestamp": "2026-03-21T14:32:00Z",
  "input": "the original input string",
  "output": "the model output string or null",
  "decision": "allow | rewrite | escalate",
  "risk_score": 0.85,
  "confidence": 0.91,
  "violations": ["violation_label"],
  "rewrite": "rewritten string or null",
  "reasoning": "decision explanation",
  "field_notes": [],
  "context": {
    "user_id": "string or null",
    "environment": "production | staging",
    "industry": "finance | healthcare | general"
  }
}
```

## Run Tests

Run from `syzygy-rosetta-originbase/syzygy-rosetta`:

```bash
python -m pytest tests -q
```

At the time of the audit, this produced:

```text
54 passed
```

## Repository Role

This is the origin codebase for Syzygy Rosetta. It contains the foundational MVP implementation of the governance engine. Active development and refactoring are ongoing.

For known mismatches and cleanup work, see `REPO_MISMATCH_AUDIT.md`.

## License

Licensed under [AGPL-3.0-or-later](https://www.gnu.org/licenses/agpl-3.0.html).

Derived from the Syzygy Rosetta v1.0 protocol by Sarasha Elion (Trivian Institute).
