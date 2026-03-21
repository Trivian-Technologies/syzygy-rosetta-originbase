"""
app.py — FastAPI Application for the Syzygy Rosetta
Version: 4.0.0

Renamed from main.py to match Dockerfile CMD target.
Thin HTTP layer — delegates all governance logic to reflex.py.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from core.reflex import evaluate_prompt, self_reflect

app = FastAPI(title="Syzygy Rosetta", version="4.0.0")


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
    """
    input: str = Field(..., min_length=1, description="Content to evaluate")
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

    Accepts: { input: str, context: { user_id, environment, industry } }
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

    result = evaluate_prompt(req.input, ctx)

    return EvaluateResponse(**result)
