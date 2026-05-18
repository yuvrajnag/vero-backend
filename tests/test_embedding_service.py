"""
Unit tests for embedding_service.py
"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.vector.embedding_service import (
    build_technician_profile_text,
    build_job_profile_text,
    compute_skill_overlap,
)


# ── Profile text builders ─────────────────────────────────────────────────────

class TestBuildTechnicianProfileText:
    def test_full_profile(self):
        tech = {
            "role": "Electrician",
            "industry": "Construction",
            "experience_years": 7,
            "skills": ["wiring", "solar", "transformers"],
            "bio": "Specialises in industrial electrical systems.",
            "languages": ["English", "French"],
            "average_rating": 4.8,
            "total_jobs_completed": 120,
            "verification_level": "premium",
        }
        text = build_technician_profile_text(tech)
        assert "Electrician" in text
        assert "Construction" in text
        assert "7 years" in text
        assert "wiring" in text
        assert "solar" in text
        assert "English" in text
        assert "120" in text
        assert "premium" in text

    def test_minimal_profile(self):
        tech = {}
        text = build_technician_profile_text(tech)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_empty_skills(self):
        tech = {"skills": [], "experience_years": 3}
        text = build_technician_profile_text(tech)
        assert "3 years" in text

    def test_deterministic(self):
        tech = {"role": "Plumber", "skills": ["pipe fitting"], "experience_years": 2}
        assert build_technician_profile_text(tech) == build_technician_profile_text(tech)


class TestBuildJobProfileText:
    def test_full_job(self):
        job = {
            "title": "Solar Panel Installation",
            "description": "Install 10kW solar system on rooftop.",
            "required_skills": ["solar", "electrical"],
            "urgency_level": "urgent",
        }
        text = build_job_profile_text(job)
        assert "Solar Panel Installation" in text
        assert "10kW" in text
        assert "solar" in text
        assert "urgent" in text

    def test_normal_urgency_not_included(self):
        job = {"title": "Fix Pipe", "required_skills": [], "urgency_level": "normal"}
        text = build_job_profile_text(job)
        assert "normal" not in text

    def test_deterministic(self):
        job = {"title": "A", "description": "B", "required_skills": ["X"]}
        assert build_job_profile_text(job) == build_job_profile_text(job)


# ── Skill overlap ─────────────────────────────────────────────────────────────

class TestComputeSkillOverlap:
    def test_perfect_match(self):
        result = compute_skill_overlap(["Python", "Docker"], ["python", "docker"])
        assert set(result["matched_skills"]) == {"python", "docker"}
        assert result["missing_skills"] == []

    def test_partial_match(self):
        result = compute_skill_overlap(["Python", "Kubernetes"], ["python", "docker"])
        assert "python" in result["matched_skills"]
        assert "kubernetes" in result["missing_skills"]

    def test_no_match(self):
        result = compute_skill_overlap(["Python"], ["Java"])
        assert result["matched_skills"] == []
        assert "python" in result["missing_skills"]

    def test_empty_inputs(self):
        result = compute_skill_overlap([], [])
        assert result["matched_skills"] == []
        assert result["missing_skills"] == []

    def test_case_insensitive(self):
        result = compute_skill_overlap(["AWS"], ["aws"])
        assert "aws" in result["matched_skills"]


# ── Encode with mocked model ──────────────────────────────────────────────────

class TestEncodeText:
    def test_empty_text_returns_zero_vector(self):
        from app.services.vector.embedding_service import encode_text
        result = encode_text("")
        assert result == [0.0] * 384
        assert len(result) == 384

    def test_whitespace_text_returns_zero_vector(self):
        from app.services.vector.embedding_service import encode_text
        result = encode_text("   ")
        assert result == [0.0] * 384

    def test_encode_uses_model(self):
        import numpy as np
        from app.services.vector.embedding_service import encode_text
        fake_vector = np.array([0.1] * 384)
        mock_model = MagicMock()
        mock_model.encode.return_value = fake_vector

        with patch("app.services.vector.embedding_service.get_model", return_value=mock_model):
            result = encode_text("Test technician profile text")
        assert len(result) == 384
        mock_model.encode.assert_called_once()

    def test_encode_batch(self):
        import numpy as np
        from app.services.vector.embedding_service import encode_batch
        fake_vectors = np.array([[0.1] * 384, [0.2] * 384])
        mock_model = MagicMock()
        mock_model.encode.return_value = fake_vectors

        with patch("app.services.vector.embedding_service.get_model", return_value=mock_model):
            result = encode_batch(["text one", "text two"])
        assert len(result) == 2
        assert len(result[0]) == 384
