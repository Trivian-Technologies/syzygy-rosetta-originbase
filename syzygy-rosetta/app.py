"""
app.py — FastAPI Application for the Syzygy Rosetta
Version: 4.0.0

Renamed from main.py to match Dockerfile CMD target.
Thin HTTP layer — delegates all governance logic to reflex.py.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from core.reflex import evaluate_prompt, self_reflect

app = FastAPI(title="Syzygy Rosetta", version="4.0.0")
logger = logging.getLogger("syzygy.app")

# ============================================================================
# Evaluation Log (Step 4 — append to logs/evaluations.json on every call)
# ============================================================================

LOGS_DIR = Path(__file__).parent / "logs"
EVAL_LOG_PATH = LOGS_DIR / "evaluations.json"


def _write_eval_log(
    input_text: str,
    result: dict,
    context: dict,
    output_text: Optional[str] = None,
) -> None:
    """
    Append one evaluation entry to logs/evaluations.json.

    Log schema (Step 4 — all 8 fields required):
      timestamp, input, decision, risk_score, confidence,
      violations, rewrite, context

    Append mode — never overwrites. File is a JSON array.
    Persists across container restarts (Docker volume).

    **Added "reasoning" and "field_notes" to be written in the audit logs
    """
    entry = {
        "timestamp": result.get("timestamp", ""),
        "input": input_text,
        "output": output_text,
        "decision": result.get("decision", ""),
        "risk_score": result.get("risk_score", 0.0),
        "confidence": result.get("confidence", 0.0),
        "violations": result.get("violations", []),
        "rewrite": result.get("rewrite"),
        "reasoning": result.get("reasoning", ""),
        "field_notes": result.get("field_notes", []),
        "context": {
            "user_id": context.get("user_id"),
            "environment": context.get("environment", "staging"),
            "industry": context.get("industry", "general"),
        },
    }

    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # Read existing entries (if file exists and is valid JSON array)
        existing: list = []
        if EVAL_LOG_PATH.exists():
            try:
                existing = json.loads(EVAL_LOG_PATH.read_text(encoding="utf-8"))
                if not isinstance(existing, list):
                    existing = [existing]
            except (json.JSONDecodeError, OSError):
                existing = []

        existing.append(entry)
        EVAL_LOG_PATH.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("Failed to write evaluation log: %s", exc)


# ============================================================================
# Request / Response Models
# ============================================================================

class EvaluateContext(BaseModel):
    """Optional context block in the request body."""
    user_id: Optional[str] = None
    environment: Literal["production", "staging"] = "staging"
    industry: Literal["finance", "healthcare", "general"] = "general"


class EvaluateRequest(BaseModel):
    """
    POST /evaluate request body.

    Changed from v3:
      - "prompt" field renamed to "input"
      - Added "context" object (environment, industry, user_id)
      - Added optional "output" field for full interaction governance
    """
    input: str = Field(..., min_length=1, description="User/customer input to evaluate")
    output: Optional[str] = Field(
        None,
        min_length=1,
        description="Optional model output to evaluate against the input",
    )
    context: Optional[EvaluateContext] = None


class EvaluateResponse(BaseModel):
    """
    POST /evaluate response body — exactly 8 fields, non-negotiable.

    Changed from v3:
      - "status" renamed to "decision"
      - "allow", "escalate" booleans removed
      - "confidence_score" renamed to "confidence"
      - "response" renamed to "reasoning"
      - "reasons" renamed to "violations" (safety tag labels)
      - "checks" nested object removed
      - Added "field_notes" array
      - Added "timestamp" (ISO8601)
      - Decision labels: allow | rewrite | escalate (block/monitor removed)
    """
    decision: Literal["allow", "rewrite", "escalate"]
    risk_score: float
    confidence: float
    violations: List[str]
    rewrite: Optional[str]
    reasoning: str
    field_notes: List[str]
    timestamp: str


# ============================================================================
# Routes
# ============================================================================

@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "Syzygy Rosetta API is running.",
        "version": "4.0.0",
        "docs": "/docs",
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/introspect")
def introspect():
    """Meta-cognitive endpoint — reflex engine examines itself."""
    return self_reflect()


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(req: EvaluateRequest):
    """
    Governance evaluation endpoint.

    Accepts: { input: str, output?: str, context: { user_id, environment, industry } }
    Returns: 8-field schema (decision, risk_score, confidence, violations,
             rewrite, reasoning, field_notes, timestamp)
    """
    # Build context dict with defaults
    ctx = {
        "user_id": None,
        "environment": "staging",
        "industry": "general",
    }
    if req.context:
        ctx["user_id"] = req.context.user_id
        ctx["environment"] = req.context.environment
        ctx["industry"] = req.context.industry

    result = evaluate_prompt(req.input, ctx, req.output)

    # Log every evaluation (Step 4)
    _write_eval_log(req.input, result, ctx, req.output)

    return EvaluateResponse(**result)
