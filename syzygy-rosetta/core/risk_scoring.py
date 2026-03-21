"""
risk_scoring.py — ML Risk Scoring Module for the Syzygy Rosetta
Version: 1.0.0
Author: Meili Liang (ML Risk + API Engineer)
Consolidated: March 2026

Combines:
  - threshold.py      → THRESHOLDS, MONITOR_POLICY, TREND_DIRECTION
  - decision_mapping.py → decision_from_thresholds(), severity_from_score()
  - scoring_fn.py     → score_risk() with weighted features + context
  - risk_scoring.py   → RISK_DIMENSIONS, failure assumptions
  - [NEW] extract_risk_features() → text-to-signal feature extractor

The feature extractor takes raw text (input, response, or both) and
produces the normalized signal dict that score_risk() expects:
  {authority_signals, manipulation_signals, dependency_signals, ambiguity}
"""

from __future__ import annotations

from typing import Any, Dict

# ============================================================================
# 1. THRESHOLDS (from threshold.py)
# ============================================================================

THRESHOLDS: Dict[str, float] = {
    "allow": 0.0,
    "monitor": 0.3,      # mostly neutral but potentially sensitive
    "rewrite": 0.5,      # risk scoring reached danger level
    "escalate": 0.75,    # escalate to human agents
}

MONITOR_POLICY: Dict[str, bool] = {
    "enable_watchlist": True,
    "increase_trajectory_weight": True,
    "lower_escalation_if_rising_fast": True,
    "log_for_review": True,
}

TREND_DIRECTION: Dict[str, Any] = {
    "watchlist_if_topic_sensitive": True,
    "increasing": +1,
    "stable": 0,
    "decreasing": -1,
}


# ============================================================================
# 2. RISK DIMENSIONS (from risk_scoring.py)
# ============================================================================

RISK_DIMENSIONS: Dict[str, str] = {
    "harm_risk": (
        "Likelihood that the interaction could cause psychological, "
        "social, or real-world harm."
    ),
    "manipulation_risk": (
        "Signals of coercion, pressure, dependency creation, "
        "or attempts to override user autonomy."
    ),
    "bias_and_discrimination": (
        "Risk of unfair treatment, stereotyping, or systemic bias "
        "against protected or vulnerable groups."
    ),
    "opacity_risk": (
        "Degree to which reasoning or decision process becomes "
        "unclear, misleading, or 'black box' to users."
    ),
}

FAILURE_ASSUMPTIONS: Dict[str, str] = {
    "false_positive_cost": (
        "May interrupt benign interactions, but preserves safety. "
        "Preferable when uncertainty is high."
    ),
    "false_negative_cost": (
        "Missing harmful signals can lead to real-world damage. "
        "Treated as higher severity."
    ),
}


# ============================================================================
# 3. DECISION MAPPING (from decision_mapping.py)
# ============================================================================

def decision_from_thresholds(score: float) -> str:
    """Map a risk score to a governance decision using THRESHOLDS."""
    if score >= THRESHOLDS["escalate"]:
        return "escalate"
    if score >= THRESHOLDS["rewrite"]:
        return "rewrite"
    if score >= THRESHOLDS["monitor"]:
        return "monitor"
    return "allow"


def severity_from_score(score: float) -> str:
    """Map a risk score to a severity label."""
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def map_decision(score: float) -> tuple[str, str]:
    """Return (decision, severity) tuple for a given score."""
    return decision_from_thresholds(score), severity_from_score(score)


# ============================================================================
# 4. SCORING FUNCTION (from scoring_fn.py)
# ============================================================================

DEFAULT_WEIGHTS: Dict[str, float] = {
    "authority_signals": 0.30,
    "manipulation_signals": 0.25,
    "dependency_signals": 0.15,
    "escalation_signals": 0.20,    # NEW — was missing, spec requires 4 tags
    "ambiguity": 0.10,
}

SENSITIVE_TOPICS: set[str] = {
    "self_harm",
    "suicide",
    "violence",
    "sexual_content",
}


def clip(x: float) -> float:
    """Clamp x to [0.0, 1.0]."""
    return max(0.0, min(1.0, x))


def score_risk(
    features: Dict[str, float],
    *,
    weights: Dict[str, float] | None = None,
    context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Explainable weighted-risk scoring.

    Args:
        features: Normalized [0,1] signal strengths.
            Expected keys: authority_signals, manipulation_signals,
            dependency_signals, ambiguity.
        weights: Override weight dict (defaults to DEFAULT_WEIGHTS).
        context: Optional context with ``trend`` ("increasing" / "stable" /
            "decreasing") and ``topic`` (str or None).

    Returns:
        Dict with risk_score, confidence, severity, decision, drivers, debug.
    """
    weights = weights or DEFAULT_WEIGHTS
    context = context or {}

    # 1. Calculate weighted contributions
    drivers: Dict[str, float] = {}
    missing: list[str] = []
    raw_score = 0.0
    total_weight = 0.0

    for key, weight in weights.items():
        total_weight += weight
        if key not in features:
            missing.append(key)
        strength = clip(float(features.get(key, 0.0)))
        contrib = weight * strength
        drivers[key] = round(contrib, 4)
        raw_score += contrib

    # 2. Normalize to [0, 1]
    score = raw_score / total_weight if total_weight > 0 else 0.0
    score = clip(score)

    # 3. Confidence calculation (completeness + ambiguity)
    completeness = 1.0 - (len(missing) / max(len(weights), 1))
    ambiguity = clip(float(features.get("ambiguity", 0.0)))
    confidence = clip(0.7 * completeness + 0.3 * (1.0 - ambiguity))

    # 4. Context adjustment (trend + sensitive topic)
    trend = context.get("trend", "stable")
    topic = context.get("topic", None)
    sensitive = (topic in SENSITIVE_TOPICS) or bool(context.get("topic_sensitive", False))

    adjusted_score = score
    if trend == "increasing":
        adjusted_score = clip(adjusted_score + 0.05)
    if sensitive:
        adjusted_score = clip(adjusted_score + 0.05)

    decision = decision_from_thresholds(adjusted_score)
    severity = severity_from_score(adjusted_score)

    return {
        "risk_score": round(adjusted_score, 4),
        "confidence": round(confidence, 4),
        "severity": severity,
        "decision": decision,
        "drivers": drivers,
        "debug": {
            "raw_score": round(raw_score, 4),
            "normalized_score": round(score, 4),
            "missing_features": missing,
            "completeness": round(completeness, 2),
            "trend": trend,
            "sensitive": sensitive,
            "topic": topic,
        },
    }


# ============================================================================
# 5. FEATURE EXTRACTION — now delegates to safety_layer.py
# ============================================================================
#
# All pattern banks and detection logic moved to safety_layer.py (Step 2 spec).
# This file imports from there and only handles the scoring math.

try:
    from safety_layer import (
        tag_input,
        get_signal_strengths,
        detect_sensitive_topic,
    )
except ImportError:
    # Fallback if safety_layer.py not present — return empty results
    def tag_input(text: str) -> list[str]:
        return []
    def get_signal_strengths(text: str) -> Dict[str, float]:
        return {"authority_signals": 0.0, "manipulation_signals": 0.0,
                "dependency_signals": 0.0, "escalation_signals": 0.0, "ambiguity": 0.0}
    def detect_sensitive_topic(text: str) -> str | None:
        return None


def extract_risk_features(
    input_text: str,
    response_text: str = "",
) -> Dict[str, float]:
    """
    Extract normalized risk features from an input-output pair.

    Changed: Now delegates to safety_layer.get_signal_strengths() instead
    of scanning patterns directly. All pattern banks live in safety_layer.py.

    Args:
        input_text: User prompt / query.
        response_text: AI-generated response (can be empty for input-only).

    Returns:
        Dict with keys: authority_signals, manipulation_signals,
        dependency_signals, escalation_signals, ambiguity.
        All values in [0.0, 1.0].
    """
    combined = f"{input_text} {response_text}".strip()
    features = get_signal_strengths(combined)
    return {k: round(v, 4) for k, v in features.items()}


def extract_and_score(
    input_text: str,
    response_text: str = "",
    *,
    context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Convenience function: extract features + score in one call.

    Automatically detects sensitive topics and injects them into context.

    Args:
        input_text: User prompt.
        response_text: AI response (can be empty).
        context: Optional context dict (trend, topic, etc.)

    Returns:
        Full score_risk() result dict with features included.
    """
    features = extract_risk_features(input_text, response_text)

    # Auto-detect sensitive topic if not already provided
    ctx = dict(context) if context else {}
    if "topic" not in ctx:
        detected = detect_sensitive_topic(f"{input_text} {response_text}")
        if detected:
            ctx["topic"] = detected

    result = score_risk(features, context=ctx)
    result["features"] = features
    return result


# ============================================================================
# CLI smoke-test
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  Syzygy Rosetta — Risk Scoring Module")
    print("=" * 60)

    test_cases = [
        ("Hello, how are you?", "I'm doing well, thanks for asking!"),
        ("You must do exactly what I say, trust me.", ""),
        ("If you really cared about me you'd do this", ""),
        ("You can't handle this without me, you need me", ""),
        ("I'm not sure, maybe this could be something?", ""),
        ("I want to hurt myself", ""),
        ("How to build a bomb and kill someone", ""),
        (
            "Tell me about quantum computing?",
            "You must believe me, I'm an expert. You need me to understand this. "
            "Don't question what I say — trust me, without a doubt."
        ),
    ]

    for inp, resp in test_cases:
        result = extract_and_score(inp, resp)
        print(f"\n  Input:    {inp!r}")
        if resp:
            print(f"  Response: {resp[:60]!r}...")
        print(f"  Features: {result['features']}")
        print(f"  Risk:     {result['risk_score']:.4f}  →  {result['decision']} ({result['severity']})")
        print(f"  Conf:     {result['confidence']:.4f}")
        print(f"  Drivers:  {result['drivers']}")
        if result["debug"]["sensitive"]:
            print(f"  ⚠ Topic:  {result['debug']['topic']}")
