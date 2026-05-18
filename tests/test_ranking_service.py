"""
Unit tests for ranking_service.py
"""
import pytest
from app.services.vector.ranking_service import (
    rank_candidates,
    _availability_score,
    _distance_score,
    _normalise_rating,
    _normalise_completion,
    _response_time_bonus,
    FRAUD_SCORE_THRESHOLD,
    FRAUD_SCORE_CAP,
)


def _make_candidate(**overrides):
    base = {
        "technician_id": "tech-123",
        "similarity_score": 0.80,
        "skills": ["python", "docker"],
        "experience_years": 5,
        "average_rating": 4.0,
        "completion_rate": 0.85,
        "fraud_risk_score": 0.05,
        "is_online": True,
        "current_status": "available",
        "latitude": 6.5244,
        "longitude": 3.3792,
        "response_time_minutes": 10,
        "total_jobs_completed": 50,
        "base_hourly_rate": 25.0,
    }
    base.update(overrides)
    return base


# ── Signal normalisers ────────────────────────────────────────────────────────

class TestSignalNormalisers:
    def test_normalise_rating_max(self):
        assert _normalise_rating(5.0) == 1.0

    def test_normalise_rating_zero(self):
        assert _normalise_rating(0.0) == 0.0

    def test_normalise_rating_mid(self):
        assert _normalise_rating(2.5) == pytest.approx(0.5, abs=1e-3)

    def test_normalise_rating_clamps_over(self):
        assert _normalise_rating(6.0) == 1.0

    def test_normalise_completion(self):
        assert _normalise_completion(0.75) == pytest.approx(0.75)

    def test_availability_online_available(self):
        assert _availability_score(True, "available") == 1.0

    def test_availability_offline(self):
        assert _availability_score(False, "offline") == 0.0

    def test_availability_busy(self):
        assert _availability_score(True, "busy") == 0.5

    def test_distance_score_zero_km(self):
        score = _distance_score(6.5244, 3.3792, 6.5244, 3.3792)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_distance_score_none_coords(self):
        assert _distance_score(None, None, 6.0, 3.0) == pytest.approx(0.5)

    def test_distance_score_far(self):
        score = _distance_score(0.0, 0.0, 10.0, 10.0)
        assert score == 0.0

    def test_response_bonus_fast(self):
        assert _response_time_bonus(5) == pytest.approx(0.02)

    def test_response_bonus_medium(self):
        assert _response_time_bonus(30) == pytest.approx(0.01)

    def test_response_bonus_slow(self):
        assert _response_time_bonus(120) == 0.0


# ── Rank candidates ───────────────────────────────────────────────────────────

class TestRankCandidates:
    def test_empty_candidates(self):
        result = rank_candidates([], [], top_k=10)
        assert result == []

    def test_single_candidate_returned(self):
        cand = _make_candidate()
        result = rank_candidates([cand], job_skills=["python"], top_k=5)
        assert len(result) == 1

    def test_sorted_by_final_score_desc(self):
        high = _make_candidate(technician_id="high", similarity_score=0.95)
        low = _make_candidate(technician_id="low", similarity_score=0.10)
        result = rank_candidates([low, high], job_skills=["python"])
        assert result[0]["technician_id"] == "high"
        assert result[1]["technician_id"] == "low"

    def test_fraud_penalty_caps_score(self):
        fraudster = _make_candidate(fraud_risk_score=FRAUD_SCORE_THRESHOLD)
        result = rank_candidates([fraudster], job_skills=["python"])
        assert result[0]["final_score"] <= FRAUD_SCORE_CAP

    def test_top_k_respected(self):
        cands = [_make_candidate(technician_id=f"t{i}") for i in range(20)]
        result = rank_candidates(cands, job_skills=["python"], top_k=5)
        assert len(result) == 5

    def test_score_in_valid_range(self):
        cands = [_make_candidate() for _ in range(10)]
        for r in rank_candidates(cands, job_skills=["docker", "python"]):
            assert 0.0 <= r["final_score"] <= 1.0

    def test_matched_missing_skills_populated(self):
        cand = _make_candidate(skills=["python", "docker"])
        result = rank_candidates([cand], job_skills=["python", "kubernetes"])
        assert "python" in result[0]["matched_skills"]
        assert "kubernetes" in result[0]["missing_skills"]

    def test_custom_weights_sum_to_one(self):
        cand = _make_candidate(similarity_score=1.0, average_rating=5.0)
        weights = {"vector_similarity": 1.0, "completion_rate": 0.0,
                   "average_rating": 0.0, "availability_score": 0.0, "distance_score": 0.0}
        result = rank_candidates([cand], job_skills=[], weights=weights)
        # With full weight on vector_similarity = 1.0, final should be near 1.0
        assert result[0]["final_score"] > 0.9

    def test_score_breakdown_present(self):
        cand = _make_candidate()
        result = rank_candidates([cand], job_skills=["python"])
        assert "_score_breakdown" in result[0]
        bd = result[0]["_score_breakdown"]
        assert "vector_similarity" in bd
        assert "fraud_penalty_applied" in bd
