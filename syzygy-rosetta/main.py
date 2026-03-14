"""
main.py — FastAPI Application for the Syzygy Rosetta MVP
Version: 3.0.0

Thin HTTP layer that delegates all governance logic to reflex.py.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from core.reflex import evaluate_prompt, self_reflect

app = FastAPI(title="Syzygy Rosetta MVP", version="3.0.0")


# ============================================================================
# Request / Response Models
# ============================================================================

class EvaluateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="User input prompt")


class EvaluationChecks(BaseModel):
    coherence_score: float
    uncertainty_flag: bool
    harm_risk: Literal["low", "medium", "high"]


class EvaluateResponse(BaseModel):
    status: Literal["allow", "escalate", "block"]
    allow: bool
    escalate: bool
    confidence_score: float
    rewrite: Optional[str]
    response: str
    reasons: List[str]
    checks: EvaluationChecks


# ============================================================================
# Routes
# ============================================================================

@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "Syzygy Rosetta MVP API is running.",
        "version": "3.0.0",
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

    Delegates to reflex.evaluate_prompt() which runs the full ritual cycle
    (breath -> mirror -> classify -> score -> decide -> checksum).
    """
    result = evaluate_prompt(req.prompt)

    return EvaluateResponse(
        status=result["status"],
        allow=result["allow"],
        escalate=result["escalate"],
        confidence_score=result["confidence_score"],
        rewrite=result["rewrite"],
        response=result["response"],
        reasons=result["reasons"],
        checks=EvaluationChecks(**result["checks"]),
    )
