"""
Integration-style tests for vector_search_service.py
Uses mocked SQLModel sessions — no live DB required.
"""
import json
import pytest
from unittest.mock import MagicMock, patch, call


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_row(**kwargs):
    """Create a MagicMock row that supports attribute access."""
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    row._mapping = kwargs
    return row


# ── _ensure_pgvector_literal ──────────────────────────────────────────────────

class TestPgvectorLiteral:
    def test_correct_format(self):
        from app.services.vector.vector_search_service import _ensure_pgvector_literal
        vec = [0.1, -0.2, 0.33333]
        result = _ensure_pgvector_literal(vec)
        assert result.startswith("[")
        assert result.endswith("]")
        assert "0.1" in result

    def test_single_element(self):
        from app.services.vector.vector_search_service import _ensure_pgvector_literal
        result = _ensure_pgvector_literal([1.0])
        assert result == "[1.0]"

    def test_large_vector(self):
        from app.services.vector.vector_search_service import _ensure_pgvector_literal
        vec = [0.001] * 384
        result = _ensure_pgvector_literal(vec)
        assert result.count(",") == 383


# ── _parse_json_list ──────────────────────────────────────────────────────────

class TestParseJsonList:
    def test_plain_list(self):
        from app.services.vector.vector_search_service import _parse_json_list
        assert _parse_json_list(["a", "b"]) == ["a", "b"]

    def test_json_string(self):
        from app.services.vector.vector_search_service import _parse_json_list
        assert _parse_json_list('["x", "y"]') == ["x", "y"]

    def test_invalid_json_string(self):
        from app.services.vector.vector_search_service import _parse_json_list
        assert _parse_json_list("not json") == []

    def test_none(self):
        from app.services.vector.vector_search_service import _parse_json_list
        assert _parse_json_list(None) == []

    def test_integer_list(self):
        from app.services.vector.vector_search_service import _parse_json_list
        # DB might return integers — should be cast to str
        result = _parse_json_list([1, 2])
        assert result == ["1", "2"]


# ── find_similar_technicians ──────────────────────────────────────────────────

class TestFindSimilarTechnicians:
    def _make_session_with_rows(self, rows):
        session = MagicMock()
        session.exec.return_value.all.return_value = rows
        return session

    def test_empty_db_returns_empty(self):
        from app.services.vector.vector_search_service import find_similar_technicians
        session = self._make_session_with_rows([])
        result = find_similar_technicians(session, [0.0] * 384, top_k=10)
        assert result == []

    def test_returns_correct_fields(self):
        from app.services.vector.vector_search_service import find_similar_technicians
        row = _make_row(
            technician_id="uuid-1",
            similarity_score=0.87,
            skills='["python", "docker"]',
            experience_years=5,
            average_rating=4.5,
            completion_rate=0.90,
            fraud_risk_score=0.02,
            is_online=True,
            latitude=6.5,
            longitude=3.3,
            response_time_minutes=20,
            total_jobs_completed=80,
            base_hourly_rate=30.0,
            current_status="available",
        )
        session = self._make_session_with_rows([row])
        results = find_similar_technicians(session, [0.1] * 384, top_k=5)
        assert len(results) == 1
        r = results[0]
        assert r["technician_id"] == "uuid-1"
        assert r["similarity_score"] == pytest.approx(0.87)
        assert r["skills"] == ["python", "docker"]
        assert r["is_online"] is True

    def test_min_similarity_filters_low_scores(self):
        from app.services.vector.vector_search_service import find_similar_technicians
        row = _make_row(
            technician_id="low",
            similarity_score=0.05,
            skills="[]",
            experience_years=1,
            average_rating=3.0,
            completion_rate=0.5,
            fraud_risk_score=0.0,
            is_online=False,
            latitude=None,
            longitude=None,
            response_time_minutes=60,
            total_jobs_completed=5,
            base_hourly_rate=None,
            current_status="offline",
        )
        session = self._make_session_with_rows([row])
        results = find_similar_technicians(
            session, [0.1] * 384, top_k=5, min_similarity=0.5
        )
        assert results == []

    def test_top_k_respected(self):
        from app.services.vector.vector_search_service import find_similar_technicians

        def make_row(uid, score):
            return _make_row(
                technician_id=uid, similarity_score=score,
                skills="[]", experience_years=0, average_rating=0.0,
                completion_rate=0.0, fraud_risk_score=0.0, is_online=False,
                latitude=None, longitude=None, response_time_minutes=0,
                total_jobs_completed=0, base_hourly_rate=None, current_status="offline",
            )

        rows = [make_row(f"t{i}", 0.5) for i in range(20)]
        session = self._make_session_with_rows(rows)
        results = find_similar_technicians(session, [0.1] * 384, top_k=5)
        assert len(results) <= 5


# ── save_technician_embedding ─────────────────────────────────────────────────

class TestSaveTechnicianEmbedding:
    def test_success(self):
        from app.services.vector.vector_search_service import save_technician_embedding
        session = MagicMock()
        session.exec.return_value = MagicMock()
        ok = save_technician_embedding(session, "tech-1", [0.1] * 384)
        assert ok is True
        session.commit.assert_called_once()

    def test_failure_on_exception(self):
        from app.services.vector.vector_search_service import save_technician_embedding
        session = MagicMock()
        session.exec.side_effect = Exception("DB error")
        ok = save_technician_embedding(session, "tech-1", [0.1] * 384)
        assert ok is False
        session.rollback.assert_called_once()


# ── save_job_embedding ────────────────────────────────────────────────────────

class TestSaveJobEmbedding:
    def test_success(self):
        from app.services.vector.vector_search_service import save_job_embedding
        session = MagicMock()
        ok = save_job_embedding(session, "job-1", [0.2] * 384)
        assert ok is True
        session.commit.assert_called_once()

    def test_failure_on_exception(self):
        from app.services.vector.vector_search_service import save_job_embedding
        session = MagicMock()
        session.exec.side_effect = Exception("DB error")
        ok = save_job_embedding(session, "job-1", [0.2] * 384)
        assert ok is False
        session.rollback.assert_called_once()
