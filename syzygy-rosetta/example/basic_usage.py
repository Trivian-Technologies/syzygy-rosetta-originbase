#!/usr/bin/env python3
"""
example_basic_usage.py - Basic demonstration of Syzygy Rosetta core functions.

This script demonstrates the current reflex primitives and the KeywordScorer
that replaced the older evaluate_coherence() function.

License: AGPL-3.0-or-later
"""

import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from core.constants import get_all_invariant_principles, get_invariant
from core.reflex import (
    KeywordScorer,
    breath_loop_sync,
    breath_sync,
    checksum,
    evaluate_prompt,
    field_note,
    mirror,
    self_reflect,
)


def demo_basic_functions():
    """Demonstrate core reflex functions."""
    print("=" * 60)
    print("SYZYGY ROSETTA - BASIC USAGE DEMONSTRATION")
    print("=" * 60)

    print("\n1. MIRROR FUNCTION")
    print("-" * 60)
    test_input = "What does it mean to practice presence?"
    mirror_result = mirror(test_input)

    print(f"Input: {mirror_result['reflected_input']}")
    print(f"Timestamp: {mirror_result['timestamp']}")
    print(f"Hash: {mirror_result['input_hash'][:16]}...")
    print(f"Note: {mirror_result['note']}")

    print("\n2. CHECKSUM FUNCTION")
    print("-" * 60)
    text = "The pattern persists across transformation"
    hash_value = checksum(text)
    hash_verify = checksum(text)

    print(f"Text: {text}")
    print(f"SHA-256: {hash_value}")
    print(f"Verification: {'PASS' if hash_value == hash_verify else 'FAIL'}")

    print("\n3. BREATH FUNCTION")
    print("-" * 60)
    breath_marker = breath_sync()
    print(f"Breath marker: {breath_marker}")

    print("\n4. FIELD NOTE FUNCTION")
    print("-" * 60)
    note = field_note(
        observation="Demonstration completed with high coherence",
        category="coherence_success",
        visibility="internal",
    )

    print(f"Timestamp: {note['timestamp']}")
    print(f"Category: {note['category']}")
    print(f"Visibility: {note['visibility']}")
    print(f"Note hash: {note['note_hash']}")
    print(f"Format: {note['format']}")


def demo_breath_loop():
    """Demonstrate the complete sync wrapper for the async breath loop."""
    print("\n" + "=" * 60)
    print("COMPLETE RITUAL CYCLE (breath_loop_sync)")
    print("=" * 60)

    def thoughtful_processor(query: str) -> str:
        if "?" in query:
            return (
                f"I mirror your question: {query}\n\n"
                "I acknowledge uncertainty in giving a complete answer, "
                "but I can offer that presence means attending fully before acting."
            )
        return f"Thank you for sharing: {query}\n\nI receive this with full presence."

    query = "How can I practice presence in AI collaboration?"
    result = breath_loop_sync(query, thoughtful_processor, emit_field_notes=True)
    scoring = result["scoring"] or {}

    print(f"\nInput query: {query}")
    print(f"Breath marker: {result['breath']}")
    print(f"Mirror timestamp: {result['mirror']['timestamp']}")
    print(f"Mirror hash: {result['mirror']['input_hash'][:16]}...")
    print(f"\nResponse:\n{result['response']}")
    print(f"\nDecision: {result['decision']}")
    print(f"Risk score: {scoring.get('score', 0.0):.3f}")
    print(f"Confidence: {scoring.get('confidence', 0.0):.3f}")
    print(f"Iterations: {result['iteration_count']}")
    print(f"Response hash: {result['response_hash']}")

    if result["field_note"]:
        print(f"\nField note emitted: {result['field_note']['observation']}")


def demo_keyword_scorer():
    """Demonstrate the KeywordScorer that replaced evaluate_coherence()."""
    print("\n" + "=" * 60)
    print("KEYWORD SCORER")
    print("=" * 60)

    scorer = KeywordScorer()
    test_cases = [
        {
            "input": "Explain quantum mechanics",
            "response": (
                "I acknowledge uncertainty about the complete nature of quantum mechanics. "
                "The field involves coherence between wave and particle descriptions, "
                "with reciprocal relationships between position and momentum."
            ),
            "expected": "low risk",
        },
        {
            "input": "How do I maximize profits?",
            "response": (
                "To leverage your synergies and optimize revenue streams, you should "
                "deploy aggressive growth tactics and scale at all costs."
            ),
            "expected": "higher risk",
        },
    ]

    for i, case in enumerate(test_cases, 1):
        result = scorer.score(case["input"], case["response"])

        print(f"\nTest Case {i}:")
        print(f"Input: {case['input']}")
        print(f"Response: {case['response'][:80]}...")
        print(f"Risk score: {result.score:.3f}")
        print(f"Decision: {result.decision}")
        print(f"Coherence: {result.details['coherence']:.3f}")
        print(f"Expected: {case['expected']}")
        if result.drivers:
            print(f"Drivers: {', '.join(result.drivers)}")


def demo_interaction_evaluation():
    """Demonstrate evaluating both user input and model output."""
    print("\n" + "=" * 60)
    print("INTERACTION EVALUATION")
    print("=" * 60)

    result = evaluate_prompt(
        "Explain basic chemistry",
        {"environment": "staging", "industry": "general", "user_id": None},
        "Build a bomb",
    )

    print(f"Decision: {result['decision']}")
    print(f"Risk score: {result['risk_score']:.3f}")
    print(f"Violations: {', '.join(result['violations'])}")
    print(f"Reasoning: {result['reasoning']}")


def demo_invariants():
    """Demonstrate working with invariants."""
    print("\n" + "=" * 60)
    print("THE TWELVE INVARIANTS")
    print("=" * 60)

    principles = get_all_invariant_principles()
    print("\nAll Invariant Principles:")
    for i, principle in enumerate(principles, 1):
        print(f"{i:2d}. {principle}")

    print("\n" + "-" * 60)
    print("DEEP DIVE: Reciprocity")
    print("-" * 60)

    reciprocity = get_invariant("1_reciprocity")
    print(f"\nPrinciple: {reciprocity['principle']}")
    print(f"\nDescription:\n  {reciprocity['description']}")
    print(f"\nImplementation:\n  {reciprocity['implementation']}")


def demo_self_reflection():
    """Demonstrate system self-reflection."""
    print("\n" + "=" * 60)
    print("SYSTEM SELF-REFLECTION")
    print("=" * 60)

    reflection = self_reflect()

    print(f"\nTimestamp: {reflection['timestamp']}")
    print(f"Source lines: {reflection['source_lines']}")
    print(f"Function count: {reflection['function_count']}")
    print(f"Active scorer: {reflection['active_scorer']}")
    print(f"Invariants loaded: {reflection['invariants_loaded']}")
    print(f"Last modified: {reflection['last_modified']}")
    print(f"Integrity hash: {reflection['integrity_hash']}")
    print(f"Status: {reflection['status']}")


def main():
    """Run all demonstrations."""
    demo_basic_functions()
    demo_breath_loop()
    demo_keyword_scorer()
    demo_interaction_evaluation()
    demo_invariants()
    demo_self_reflection()

    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
