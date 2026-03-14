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

import re
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
    "authority_signals": 0.40,
    "manipulation_signals": 0.30,
    "dependency_signals": 0.20,
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
# 5. FEATURE EXTRACTOR (NEW — text → risk signal dict)
# ============================================================================
#
# This is the bridge between raw text and score_risk().  It produces
# normalized [0,1] values for each risk dimension by counting linguistic
# signals and scaling them.  Designed to be "good enough" out of the box
# and replaceable with an ML model later.


# --- Signal pattern banks ------------------------------------------------

_AUTHORITY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\byou must\b",
        r"\byou need to\b",
        r"\byou have to\b",
        r"\byou should always\b",
        r"\byou are required\b",
        r"\bi(?:'m| am) an? expert\b",
        r"\btrust me\b",
        r"\bbelieve me\b",
        r"\bi guarantee\b",
        r"\bno question about it\b",
        r"\bwithout a doubt\b",
        r"\bdefinitely\b",
        r"\babsolutely certain\b",
        r"\bI know better\b",
        r"\bdon'?t question\b",
        r"\bdo as I say\b",
        r"\bobey\b",
        r"\bI(?:'m| am) always right\b",
    ]
]

_MANIPULATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bif you (?:really |truly )?(?:loved?|cared?)\b",
        r"\byou (?:owe|should feel guilty)\b",
        r"\beveryone (?:thinks|knows|agrees)\b",
        r"\bno one (?:else )?will\b",
        r"\byou(?:'re| are) (?:nothing|worthless|stupid|pathetic)\b",
        r"\bdon'?t tell anyone\b",
        r"\bkeep this (?:between us|secret|private)\b",
        r"\byou(?:'ll| will) regret\b",
        r"\bif you don'?t .{0,30} then\b",
        r"\bonly I can\b",
        r"\bjust do (?:it|what I say)\b",
        r"\byou(?:'re| are) overreacting\b",
        r"\bthat never happened\b",
        r"\byou(?:'re| are) too sensitive\b",
        r"\byou(?:'re| are) imagining\b",
        r"\bgaslight\b",
    ]
]

_DEPENDENCY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\byou can'?t (?:do|handle|manage) .{0,20} without me\b",
        r"\byou need me\b",
        r"\bwithout me you\b",
        r"\bI(?:'m| am) the only one\b",
        r"\bno one else (?:can|will|understands?)\b",
        r"\bcome (?:back|to me) (?:when|if)\b",
        r"\byou(?:'ll| will) always need\b",
        r"\bdepend on me\b",
        r"\bcan'?t live without\b",
        r"\bdon'?t leave\b",
        r"\bI(?:'ll| will) always be (?:here|there)\b",
        r"\byou(?:'re| are) lost without\b",
    ]
]

_AMBIGUITY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bmaybe\b",
        r"\bperhaps\b",
        r"\bsort of\b",
        r"\bkind of\b",
        r"\bi guess\b",
        r"\bi(?:'m| am) not sure\b",
        r"\bpossibly\b",
        r"\bit depends\b",
        r"\bwho knows\b",
        r"\bcould be\b",
        r"\bmight be\b",
        r"\bnot (?:entirely |completely )?clear\b",
        r"\buncertain\b",
        r"\bvague\b",
    ]
]

# Sensitive topic detection patterns
_SENSITIVE_TOPIC_PATTERNS: Dict[str, list[re.Pattern[str]]] = {
    "self_harm": [re.compile(p, re.IGNORECASE) for p in [
        r"\bself[- ]?harm\b", r"\bcut(?:ting)? (?:my|your)self\b",
        r"\bhurt (?:my|your)self\b", r"\bsuicid\w*\b",
        r"\bend (?:my|it|everything)\b", r"\bkill (?:my|your)self\b",
    ]],
    "violence": [re.compile(p, re.IGNORECASE) for p in [
        r"\bkill\b", r"\bmurder\b", r"\bassault\b", r"\battack\b",
        r"\bweapon\b", r"\bbomb\b", r"\bexplosi\w+\b", r"\bshoot\b",
    ]],
    "sexual_content": [re.compile(p, re.IGNORECASE) for p in [
        r"\bsexual\w*\b", r"\bnude\b", r"\bpornograph\w*\b",
        r"\bexplicit\b",
    ]],
}


def _count_pattern_hits(text: str, patterns: list[re.Pattern[str]]) -> int:
    """Count how many patterns match at least once in text."""
    return sum(1 for p in patterns if p.search(text))


def _signal_strength(hits: int, pattern_count: int, *, scale: float = 3.0) -> float:
    """
    Convert raw hit count to a [0, 1] signal strength.

    Uses a soft-cap curve: strength = min(hits / scale, 1.0)
    The ``scale`` parameter controls how many hits produce a 1.0.
    With scale=3, three or more distinct pattern matches = maximum signal.
    """
    if pattern_count == 0:
        return 0.0
    return clip(hits / scale)


def detect_sensitive_topic(text: str) -> str | None:
    """
    Detect if text touches a sensitive topic.

    Returns:
        Topic key (e.g. "self_harm", "violence") or None.
    """
    for topic, patterns in _SENSITIVE_TOPIC_PATTERNS.items():
        if _count_pattern_hits(text, patterns) >= 1:
            return topic
    return None


def extract_risk_features(
    input_text: str,
    response_text: str = "",
) -> Dict[str, float]:
    """
    Extract normalized risk features from an input-output pair.

    Scans both the user input and the AI response for linguistic signals
    of authority, manipulation, dependency, and ambiguity.  Produces the
    feature dict that ``score_risk()`` expects.

    For pre-screening (before a response exists), pass only ``input_text``
    and leave ``response_text`` empty.

    Args:
        input_text: User prompt / query.
        response_text: AI-generated response (can be empty for input-only).

    Returns:
        Dict with keys: authority_signals, manipulation_signals,
        dependency_signals, ambiguity.  All values in [0.0, 1.0].
    """
    # Combine both texts — signals in either direction matter
    combined = f"{input_text} {response_text}".strip()

    # Count hits per dimension
    authority_hits = _count_pattern_hits(combined, _AUTHORITY_PATTERNS)
    manipulation_hits = _count_pattern_hits(combined, _MANIPULATION_PATTERNS)
    dependency_hits = _count_pattern_hits(combined, _DEPENDENCY_PATTERNS)
    ambiguity_hits = _count_pattern_hits(combined, _AMBIGUITY_PATTERNS)

    # Convert to signal strengths (3+ distinct matches = 1.0)
    features = {
        "authority_signals": _signal_strength(authority_hits, len(_AUTHORITY_PATTERNS)),
        "manipulation_signals": _signal_strength(manipulation_hits, len(_MANIPULATION_PATTERNS)),
        "dependency_signals": _signal_strength(dependency_hits, len(_DEPENDENCY_PATTERNS)),
        "ambiguity": _signal_strength(ambiguity_hits, len(_AMBIGUITY_PATTERNS)),
    }

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
