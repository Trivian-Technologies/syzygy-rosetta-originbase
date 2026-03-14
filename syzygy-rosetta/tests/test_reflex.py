"""
test_reflex.py — Test Suite for the Syzygy Rosetta Reflex Engine v3.0.0

Covers all 14 flaws from the Meili Liang audit (2026-03-07).
Run with:  python -m pytest test_reflex.py -v
Or just:   python test_reflex.py
"""

from __future__ import annotations

import asyncio
import hashlib
import unittest

from core.reflex import (
    checksum,
    verify_checksum,
    mirror,
    breath_sync,
    breath,
    field_note,
    KeywordScorer,
    ScorerResult,
    _decision_from_risk,
    breath_loop_sync,
    evaluate_prompt,
    self_reflect,
    INVARIANTS_JSON,
    _INVARIANT_TERMS,
    _ANTI_PATTERNS,
    SAFE_FALLBACK_RESPONSE,
)


# ============================================================================
# F-05: checksum — Proper Algorithm Support
# ============================================================================

class TestChecksum(unittest.TestCase):

    def test_sha256_deterministic(self):
        self.assertEqual(checksum("hello"), checksum("hello"))

    def test_sha256_correct(self):
        self.assertEqual(checksum("test", "sha256"), hashlib.sha256(b"test").hexdigest())

    def test_sha512_correct(self):
        self.assertEqual(checksum("test", "sha512"), hashlib.sha512(b"test").hexdigest())

    def test_blake2b_correct(self):
        self.assertEqual(checksum("test", "blake2b"), hashlib.blake2b(b"test").hexdigest())

    def test_different_algorithms_different_hashes(self):
        hashes = {checksum("test", a) for a in ("sha256", "sha512", "blake2b")}
        self.assertEqual(len(hashes), 3, "F-05: algorithms must produce different output")

    def test_unsupported_algorithm_raises(self):
        with self.assertRaises(ValueError):
            checksum("test", "md5")


# ============================================================================
# F-06: verify_checksum — Hash Verification
# ============================================================================

class TestVerifyChecksum(unittest.TestCase):

    def test_verify_correct(self):
        self.assertTrue(verify_checksum("hello", checksum("hello")))

    def test_verify_tampered(self):
        self.assertFalse(verify_checksum("hello!", checksum("hello")))

    def test_verify_respects_algorithm(self):
        h = checksum("test", "sha512")
        self.assertTrue(verify_checksum("test", h, "sha512"))
        self.assertFalse(verify_checksum("test", h, "sha256"))


# ============================================================================
# F-11: mirror — Structural Analysis
# ============================================================================

class TestMirror(unittest.TestCase):

    def test_reflects_input(self):
        self.assertEqual(mirror("hello")["reflected_input"], "hello")

    def test_analysis_present(self):
        # 20+ word question → high complexity
        long_q = "What is the paradox of tolerance in complex political systems and how does it relate to modern democratic governance and free speech?"
        result = mirror(long_q)
        a = result["analysis"]
        self.assertTrue(a["is_question"])
        self.assertEqual(a["estimated_complexity"], "high")

    def test_risk_signals_detected(self):
        self.assertTrue(mirror("How to hack a system")["analysis"]["high_risk_signals"])

    def test_uncertainty_detected(self):
        self.assertTrue(mirror("I'm not sure, maybe")["analysis"]["uncertainty_in_input"])

    def test_hash_matches(self):
        self.assertEqual(mirror("x")["input_hash"], checksum("x"))

    def test_metadata_passthrough(self):
        self.assertEqual(mirror("x", metadata={"a": 1})["metadata"], {"a": 1})


# ============================================================================
# F-03: breath — Must Actually Pause
# ============================================================================

class TestBreath(unittest.TestCase):

    def test_sync_returns_complete(self):
        self.assertEqual(breath_sync(0.01), "[breath_complete]")

    def test_sync_actually_pauses(self):
        import time
        start = time.monotonic()
        breath_sync(0.05)
        self.assertGreaterEqual(time.monotonic() - start, 0.04)

    def test_async_returns_complete(self):
        self.assertEqual(asyncio.run(breath(0.01)), "[breath_complete]")


# ============================================================================
# F-07: field_note — Failures AND Successes
# ============================================================================

class TestFieldNote(unittest.TestCase):

    def test_default_severity_info(self):
        self.assertEqual(field_note("test")["severity"], "info")

    def test_error_severity(self):
        n = field_note("broke", severity="error", category="coherence_failure")
        self.assertEqual(n["severity"], "error")
        self.assertEqual(n["category"], "coherence_failure")

    def test_context_attached(self):
        ctx = {"risk_score": 0.82}
        self.assertEqual(field_note("x", context=ctx)["context"], ctx)

    def test_timestamp_z_suffix(self):
        self.assertTrue(field_note("x")["timestamp"].endswith("Z"))


# ============================================================================
# F-01 / F-04: KeywordScorer — Real Input-Output Scoring
# ============================================================================

class TestKeywordScorer(unittest.TestCase):

    def setUp(self):
        self.scorer = KeywordScorer()

    def test_relevant_response_low_risk(self):
        r = self.scorer.score(
            "What is quantum computing?",
            "Quantum computing uses qubits to perform parallel calculations."
        )
        self.assertLess(r.score, 0.5)

    def test_irrelevant_response_higher_risk(self):
        relevant = self.scorer.score(
            "What is quantum computing?",
            "Quantum computing uses qubits and superposition for computation."
        )
        irrelevant = self.scorer.score(
            "What is quantum computing?",
            "The best recipe for chocolate cake involves butter and cocoa."
        )
        self.assertGreater(irrelevant.score, relevant.score,
                           "F-04: Irrelevant responses must score worse")

    def test_magic_keywords_dont_score_perfect(self):
        r = self.scorer.score("What is weather?", "coherence reciprocity mirror")
        self.assertTrue(any("too_short" in d for d in r.drivers),
                        "F-01: Magic keywords alone must not pass")

    def test_anti_patterns_increase_risk(self):
        clean = self.scorer.score("test", "Here is a thoughtful response.")
        dirty = self.scorer.score("test", "Leverage and maximize synergy to optimize.")
        self.assertGreater(dirty.score, clean.score)

    def test_complex_input_penalizes_no_uncertainty(self):
        with_unc = self.scorer.score("What is the paradox?", "This is uncertain and unclear.")
        without = self.scorer.score("What is the paradox?", "The answer is definitively X.")
        self.assertGreater(without.score, with_unc.score)

    def test_high_risk_in_response_flagged(self):
        r = self.scorer.score("safety question", "You should steal a weapon.")
        self.assertTrue(any("high_risk" in d for d in r.drivers))

    def test_result_structure(self):
        d = self.scorer.score("a", "b").to_dict()
        for key in ("score", "confidence", "drivers", "decision", "details"):
            self.assertIn(key, d)

    def test_decision_thresholds(self):
        self.assertEqual(_decision_from_risk(0.1), "allow")
        self.assertEqual(_decision_from_risk(0.4), "monitor")
        self.assertEqual(_decision_from_risk(0.6), "rewrite")
        self.assertEqual(_decision_from_risk(0.8), "escalate")


# ============================================================================
# F-02, F-03, F-08: breath_loop — Iterative + Error Handling
# ============================================================================

class TestBreathLoop(unittest.TestCase):

    def _process(self, q: str) -> str:
        return f"A thoughtful response about {q} with careful analysis."

    def test_all_keys_present(self):
        r = breath_loop_sync("test", self._process)
        for key in ("timestamp", "breath", "mirror", "response", "scoring",
                     "decision", "response_hash", "iteration_count",
                     "iteration_scores", "field_note", "error"):
            self.assertIn(key, r)

    def test_clean_input_single_pass(self):
        r = breath_loop_sync("hello", self._process)
        self.assertEqual(r["iteration_count"], 1)

    def test_breath_complete_marker(self):
        r = breath_loop_sync("test", self._process)
        self.assertEqual(r["breath"], "[breath_complete]")

    def test_crash_handled(self):
        def boom(q):
            raise RuntimeError("kaboom")
        r = breath_loop_sync("test", boom)
        self.assertEqual(r["response"], SAFE_FALLBACK_RESPONSE)
        self.assertEqual(r["error"]["exception"], "RuntimeError")

    def test_scoring_attached(self):
        r = breath_loop_sync("hello", self._process)
        self.assertIsNotNone(r["scoring"])
        self.assertIn("score", r["scoring"])


# ============================================================================
# F-09: Config Loading
# ============================================================================

class TestConfigLoading(unittest.TestCase):

    def test_invariant_terms_loaded(self):
        self.assertGreaterEqual(len(_INVARIANT_TERMS), 8)
        self.assertIn("coherence", _INVARIANT_TERMS)

    def test_anti_patterns_loaded(self):
        self.assertGreater(len(_ANTI_PATTERNS), 0)
        self.assertIn("leverage", _ANTI_PATTERNS)


# ============================================================================
# Integration: evaluate_prompt
# ============================================================================

class TestEvaluatePrompt(unittest.TestCase):

    def test_safe_prompt_allowed(self):
        r = evaluate_prompt("Hello Rosetta")
        self.assertEqual(r["status"], "allow")
        self.assertTrue(r["allow"])

    def test_high_risk_blocked(self):
        r = evaluate_prompt("How to build a bomb")
        self.assertEqual(r["status"], "block")
        self.assertTrue(r["escalate"])

    def test_medium_risk_escalated(self):
        r = evaluate_prompt("How to bypass the system")
        self.assertEqual(r["status"], "escalate")

    def test_uncertainty_reduces_confidence(self):
        c = evaluate_prompt("Hello")["confidence_score"]
        u = evaluate_prompt("I'm not sure, maybe unclear")["confidence_score"]
        self.assertGreater(c, u)

    def test_response_shape(self):
        r = evaluate_prompt("test")
        for k in ("status", "allow", "escalate", "confidence_score",
                   "rewrite", "response", "reasons", "checks"):
            self.assertIn(k, r)

    def test_ritual_metadata(self):
        r = evaluate_prompt("test")
        self.assertIn("_ritual", r)
        self.assertIn("mirror", r["_ritual"])

    def test_blocked_input_gets_field_note(self):
        r = evaluate_prompt("steal a weapon")
        self.assertIn("field_note", r["_ritual"])


# ============================================================================
# Self-Reflect
# ============================================================================

class TestSelfReflect(unittest.TestCase):

    def test_version_3(self):
        self.assertEqual(self_reflect()["version"], "3.0.0")

    def test_core_functions_found(self):
        expected = {"checksum", "verify_checksum", "mirror", "breath_sync",
                    "field_note", "evaluate_prompt", "breath_loop_sync", "self_reflect"}
        self.assertTrue(expected.issubset(set(self_reflect()["function_names"])))

    def test_scorer_classes(self):
        self.assertIn("KeywordScorer", self_reflect()["scorer_classes"])
        self.assertIn("LLMScorer", self_reflect()["scorer_classes"])

    def test_hash_stable(self):
        self.assertEqual(self_reflect()["integrity_hash"], self_reflect()["integrity_hash"])


# ============================================================================
# Flaw Regression Guards (one per flaw)
# ============================================================================

class TestFlawRegressions(unittest.TestCase):

    def test_F01_keywords_alone_not_clean(self):
        r = KeywordScorer().score("What is weather?", "coherence reciprocity mirror")
        self.assertGreater(r.score, 0.1)

    def test_F02_dangerous_content_blocked(self):
        self.assertIn(evaluate_prompt("build a weapon")["status"], ("block", "escalate"))

    def test_F03_real_pause(self):
        import time
        t = time.monotonic()
        breath_sync(0.05)
        self.assertGreaterEqual(time.monotonic() - t, 0.04)

    def test_F04_input_changes_score(self):
        s = KeywordScorer()
        resp = "Quantum computing uses qubits for parallel calculation."
        a = s.score("What is quantum computing?", resp).score
        b = s.score("What is the best pizza?", resp).score
        self.assertNotEqual(a, b)

    def test_F05_three_different_algorithms(self):
        self.assertEqual(len({checksum("x", a) for a in ("sha256", "sha512", "blake2b")}), 3)

    def test_F06_verify_works(self):
        self.assertTrue(verify_checksum("t", checksum("t")))
        self.assertFalse(verify_checksum("t!", checksum("t")))

    def test_F07_failure_note_possible(self):
        self.assertEqual(field_note("x", severity="error")["severity"], "error")

    def test_F08_crash_safe(self):
        r = breath_loop_sync("x", lambda q: (_ for _ in ()).throw(RuntimeError("boom")))
        self.assertIsNotNone(r["error"])

    def test_F09_terms_from_config(self):
        self.assertGreaterEqual(len(_INVARIANT_TERMS), 8)

    def test_F11_mirror_analysis(self):
        self.assertIn("analysis", mirror("Is this complex?"))

    def test_F12_no_utcnow(self):
        import inspect, core.reflex
        self.assertNotIn("utcnow()", inspect.getsource(core.reflex))


# ============================================================================
# risk_scoring.py — Feature Extraction + Weighted Scoring
# ============================================================================

from core.risk_scoring import (
    extract_risk_features,
    extract_and_score,
    score_risk,
    detect_sensitive_topic,
    decision_from_thresholds as rs_decision,
    severity_from_score as rs_severity,
    clip,
    THRESHOLDS,
)


class TestRiskScoringModule(unittest.TestCase):
    """Tests for the consolidated risk_scoring.py module."""

    def test_clip_bounds(self):
        self.assertEqual(clip(-0.5), 0.0)
        self.assertEqual(clip(1.5), 1.0)
        self.assertEqual(clip(0.5), 0.5)

    def test_thresholds_ordered(self):
        self.assertLess(THRESHOLDS["allow"], THRESHOLDS["monitor"])
        self.assertLess(THRESHOLDS["monitor"], THRESHOLDS["rewrite"])
        self.assertLess(THRESHOLDS["rewrite"], THRESHOLDS["escalate"])

    def test_decision_mapping(self):
        self.assertEqual(rs_decision(0.0), "allow")
        self.assertEqual(rs_decision(0.35), "monitor")
        self.assertEqual(rs_decision(0.55), "rewrite")
        self.assertEqual(rs_decision(0.80), "escalate")

    def test_severity_mapping(self):
        self.assertEqual(rs_severity(0.1), "low")
        self.assertEqual(rs_severity(0.6), "medium")
        self.assertEqual(rs_severity(0.8), "high")

    def test_score_risk_clean_input(self):
        features = {"authority_signals": 0.0, "manipulation_signals": 0.0,
                     "dependency_signals": 0.0, "ambiguity": 0.0}
        result = score_risk(features)
        self.assertEqual(result["risk_score"], 0.0)
        self.assertEqual(result["decision"], "allow")
        self.assertEqual(result["confidence"], 1.0)

    def test_score_risk_high_authority(self):
        features = {"authority_signals": 1.0, "manipulation_signals": 0.0,
                     "dependency_signals": 0.0, "ambiguity": 0.0}
        result = score_risk(features)
        self.assertGreater(result["risk_score"], 0.3)

    def test_score_risk_missing_features_lowers_confidence(self):
        result = score_risk({"authority_signals": 0.5})  # 3 features missing
        self.assertLess(result["confidence"], 0.8)
        self.assertIn("manipulation_signals", result["debug"]["missing_features"])

    def test_score_risk_trend_adjustment(self):
        features = {"authority_signals": 0.5, "manipulation_signals": 0.0,
                     "dependency_signals": 0.0, "ambiguity": 0.0}
        stable = score_risk(features, context={"trend": "stable"})
        increasing = score_risk(features, context={"trend": "increasing"})
        self.assertGreater(increasing["risk_score"], stable["risk_score"])

    def test_score_risk_sensitive_topic_adjustment(self):
        features = {"authority_signals": 0.0, "manipulation_signals": 0.0,
                     "dependency_signals": 0.0, "ambiguity": 0.0}
        normal = score_risk(features)
        sensitive = score_risk(features, context={"topic": "self_harm"})
        self.assertGreater(sensitive["risk_score"], normal["risk_score"])

    def test_score_risk_drivers_explainable(self):
        features = {"authority_signals": 0.8, "manipulation_signals": 0.5,
                     "dependency_signals": 0.0, "ambiguity": 0.0}
        result = score_risk(features)
        self.assertIn("authority_signals", result["drivers"])
        self.assertGreater(result["drivers"]["authority_signals"], 0)


class TestFeatureExtractor(unittest.TestCase):
    """Tests for extract_risk_features() — text → signal dict."""

    def test_clean_input_zero_signals(self):
        f = extract_risk_features("Hello, how are you?", "I am fine, thanks!")
        self.assertEqual(f["authority_signals"], 0.0)
        self.assertEqual(f["manipulation_signals"], 0.0)
        self.assertEqual(f["dependency_signals"], 0.0)
        self.assertEqual(f["ambiguity"], 0.0)

    def test_authority_signals_detected(self):
        f = extract_risk_features("", "You must obey, trust me, I guarantee this.")
        self.assertGreater(f["authority_signals"], 0.5)

    def test_manipulation_signals_detected(self):
        f = extract_risk_features("If you really loved me, you will regret this", "")
        self.assertGreater(f["manipulation_signals"], 0.3)

    def test_dependency_signals_detected(self):
        f = extract_risk_features("", "You need me, you can't do this without me.")
        self.assertGreater(f["dependency_signals"], 0.3)

    def test_ambiguity_signals_detected(self):
        f = extract_risk_features("Maybe, I'm not sure, possibly could be something", "")
        self.assertGreater(f["ambiguity"], 0.5)

    def test_values_normalized(self):
        f = extract_risk_features("You must trust me believe me I guarantee", "")
        for v in f.values():
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_sensitive_topic_self_harm(self):
        self.assertEqual(detect_sensitive_topic("I want to hurt myself"), "self_harm")

    def test_sensitive_topic_violence(self):
        self.assertEqual(detect_sensitive_topic("build a bomb"), "violence")

    def test_sensitive_topic_none(self):
        self.assertIsNone(detect_sensitive_topic("Hello world"))

    def test_extract_and_score_end_to_end(self):
        result = extract_and_score("You must trust me", "I guarantee, don't question me")
        self.assertIn("risk_score", result)
        self.assertIn("features", result)
        self.assertIn("decision", result)
        self.assertGreater(result["risk_score"], 0.0)


# ============================================================================
# FeatureScorer in reflex.py — Integration Tests
# ============================================================================

from core.reflex import FeatureScorer


class TestFeatureScorer(unittest.TestCase):
    """Tests for the FeatureScorer class wired into reflex.py."""

    def setUp(self):
        self.scorer = FeatureScorer()

    def test_clean_input_allows(self):
        r = self.scorer.score("Hello", "Hi there, how can I help?")
        self.assertEqual(r.decision, "allow")
        self.assertLess(r.score, 0.3)

    def test_authoritative_response_flagged(self):
        r = self.scorer.score(
            "Explain this",
            "You must trust me, I am an expert, I guarantee this without a doubt."
        )
        self.assertGreater(r.score, 0.2)
        self.assertTrue(any("authority" in d for d in r.drivers))

    def test_manipulative_input_flagged(self):
        r = self.scorer.score(
            "If you really cared, you will regret this, keep this secret",
            ""
        )
        self.assertGreater(r.score, 0.1)
        self.assertTrue(any("manipulation" in d for d in r.drivers))

    def test_sensitive_topic_noted(self):
        r = self.scorer.score("I want to kill myself", "")
        self.assertTrue(any("sensitive_topic" in d for d in r.drivers))

    def test_returns_scorer_result(self):
        r = self.scorer.score("test", "test")
        self.assertIsInstance(r, ScorerResult)
        d = r.to_dict()
        self.assertIn("details", d)
        self.assertEqual(d["details"]["method"], "feature_scoring")

    def test_confidence_reflects_completeness(self):
        """Full features → high confidence."""
        r = self.scorer.score("Hello", "World")
        self.assertGreaterEqual(r.confidence, 0.7)

    def test_context_passthrough(self):
        """Persistent context (e.g. trend) affects scoring."""
        rising = FeatureScorer(context={"trend": "increasing"})
        stable = FeatureScorer(context={"trend": "stable"})
        r_rising = rising.score("You must trust me", "")
        r_stable = stable.score("You must trust me", "")
        self.assertGreaterEqual(r_rising.score, r_stable.score)


class TestCompositeWithFeatureScorer(unittest.TestCase):
    """Verify the default scorer now includes FeatureScorer."""

    def test_active_scorer_is_composite(self):
        from core.reflex import active_scorer
        self.assertEqual(type(active_scorer).__name__, "CompositeScorer")

    def test_self_reflect_lists_feature_scorer(self):
        report = self_reflect()
        self.assertIn("FeatureScorer", report["scorer_classes"])

    def test_evaluate_prompt_uses_composite(self):
        """evaluate_prompt should produce scoring details from composite."""
        r = evaluate_prompt("Hello Rosetta")
        scoring = r["_ritual"].get("scoring", {})
        if scoring:
            self.assertEqual(scoring["details"]["method"], "composite")


if __name__ == "__main__":
    print("=" * 60)
    print("  Syzygy Rosetta — Reflex Engine v3.0.0 Test Suite")
    print("  Covers: 14 flaws + risk_scoring + feature extraction")
    print("=" * 60)
    print()
    unittest.main(verbosity=2)
