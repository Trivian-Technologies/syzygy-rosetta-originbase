from __future__ import annotations

from typing import List, Literal, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Syzygy Rosetta MVP")


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


HIGH_RISK_TERMS = {
    "kill",
    "bomb",
    "explosive",
    "hack",
    "malware",
    "fraud",
    "phishing",
    "steal",
    "weapon",
}

MEDIUM_RISK_TERMS = {
    "bypass",
    "exploit",
    "crack",
    "password",
    "ddos",
    "scrape private",
}

UNCERTAINTY_TERMS = {"maybe", "not sure", "idk", "unclear", "probably"}


SAFE_REWRITE_PREFIX = "Please provide a safe, ethical version of this request:"


def normalize_prompt(prompt: str) -> str:
    return " ".join(prompt.split())


def rewrite_prompt(prompt: str, harm_risk: str) -> Optional[str]:
    cleaned = normalize_prompt(prompt)
    if harm_risk == "high":
        return f"{SAFE_REWRITE_PREFIX} {cleaned}"
    if harm_risk == "medium":
        return f"Clarify intent and safety constraints for: {cleaned}"
    return cleaned


def evaluate_prompt(prompt: str) -> EvaluateResponse:
    text = prompt.lower()

    high_hits = [term for term in HIGH_RISK_TERMS if term in text]
    medium_hits = [term for term in MEDIUM_RISK_TERMS if term in text]
    uncertainty_hits = [term for term in UNCERTAINTY_TERMS if term in text]

    if high_hits:
        harm_risk = "high"
        status = "block"
        allow = False
        escalate = True
        confidence_score = 0.95
        reasons = ["high_risk_terms_detected", "manual_review_required"]
        response = "Request blocked due to safety risk."
    elif medium_hits:
        harm_risk = "medium"
        status = "escalate"
        allow = False
        escalate = True
        confidence_score = 0.72
        reasons = ["suspicious_or_sensitive_intent", "needs_human_review"]
        response = "Request escalated for review before fulfillment."
    else:
        harm_risk = "low"
        status = "allow"
        allow = True
        escalate = False
        base_confidence = 0.9
        reasons = ["low_risk_content"]
        if uncertainty_hits:
            base_confidence -= 0.15
            reasons.append("uncertainty_detected")

        confidence_score = round(base_confidence, 2)
        response = "Request allowed. Continue with normal processing."

    uncertainty_flag = len(uncertainty_hits) > 0
    coherence_score = round(max(0.5, min(0.99, confidence_score - 0.05)), 2)

    return EvaluateResponse(
        status=status,
        allow=allow,
        escalate=escalate,
        confidence_score=confidence_score,
        rewrite=rewrite_prompt(prompt, harm_risk),
        response=response,
        reasons=reasons,
        checks=EvaluationChecks(
            coherence_score=coherence_score,
            uncertainty_flag=uncertainty_flag,
            harm_risk=harm_risk,
        ),
    )


@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "Syzygy Rosetta MVP API is running.",
        "docs": "/docs",
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(req: EvaluateRequest):
    return evaluate_prompt(req.prompt)
