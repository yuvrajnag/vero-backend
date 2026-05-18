"""
Unit tests for redis_cache.py
Tests use a mocked Redis client so no live Redis connection is needed.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

# ── Fixture: fake Redis ───────────────────────────────────────────────────────

@pytest.fixture
def mock_redis():
    """Return a MagicMock redis client injected into the cache module."""
    fake = MagicMock()
    fake.ping.return_value = True
    with patch("app.services.vector.redis_cache._redis_client", fake):
        yield fake


# ── Technician embedding cache ────────────────────────────────────────────────

class TestTechnicianEmbeddingCache:
    def test_get_hit(self, mock_redis):
        from app.services.vector.redis_cache import get_technician_embedding
        fake_vec = [0.1] * 384
        mock_redis.get.return_value = json.dumps(fake_vec)
        result = get_technician_embedding("tech-1")
        assert result == fake_vec

    def test_get_miss(self, mock_redis):
        from app.services.vector.redis_cache import get_technician_embedding
        mock_redis.get.return_value = None
        result = get_technician_embedding("tech-2")
        assert result is None

    def test_set(self, mock_redis):
        from app.services.vector.redis_cache import set_technician_embedding
        vec = [0.5] * 384
        set_technician_embedding("tech-3", vec)
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert "technician_embedding:tech-3" in call_args[0][0]

    def test_invalidate(self, mock_redis):
        from app.services.vector.redis_cache import invalidate_technician_embedding
        invalidate_technician_embedding("tech-4")
        mock_redis.delete.assert_called_once()


# ── Job embedding cache ───────────────────────────────────────────────────────

class TestJobEmbeddingCache:
    def test_get_hit(self, mock_redis):
        from app.services.vector.redis_cache import get_job_embedding
        vec = [0.2] * 384
        mock_redis.get.return_value = json.dumps(vec)
        result = get_job_embedding("job-1")
        assert result == vec

    def test_set_calls_setex(self, mock_redis):
        from app.services.vector.redis_cache import set_job_embedding
        set_job_embedding("job-1", [0.1] * 384)
        mock_redis.setex.assert_called_once()


# ── Match result cache ────────────────────────────────────────────────────────

class TestMatchResultCache:
    def test_round_trip(self, mock_redis):
        from app.services.vector.redis_cache import set_match_result, get_match_result
        data = [{"technician_id": "t1", "final_score": 0.95}]
        stored_payload = None

        def capture_setex(key, ttl, payload):
            nonlocal stored_payload
            stored_payload = payload
        mock_redis.setex.side_effect = capture_setex
        mock_redis.get.side_effect = lambda k: stored_payload

        set_match_result("job-x", data)
        result = get_match_result("job-x")
        assert result == data


# ── Enqueue / dequeue ─────────────────────────────────────────────────────────

class TestEmbeddingQueue:
    def test_enqueue(self, mock_redis):
        from app.services.vector.redis_cache import enqueue_embedding_rebuild
        enqueue_embedding_rebuild("technician", "tech-99")
        mock_redis.rpush.assert_called_once()
        key, payload = mock_redis.rpush.call_args[0]
        parsed = json.loads(payload)
        assert parsed["type"] == "technician"
        assert parsed["id"] == "tech-99"

    def test_dequeue_returns_none_on_timeout(self, mock_redis):
        from app.services.vector.redis_cache import dequeue_embedding_rebuild
        mock_redis.lpop.return_value = None
        result = dequeue_embedding_rebuild()
        assert result is None

    def test_dequeue_returns_task(self, mock_redis):
        from app.services.vector.redis_cache import dequeue_embedding_rebuild
        payload = json.dumps({"type": "job", "id": "job-42"})
        mock_redis.lpop.return_value = payload
        result = dequeue_embedding_rebuild()
        assert result == {"type": "job", "id": "job-42"}


# ── Analytics counters ────────────────────────────────────────────────────────

class TestAnalyticsCounters:
    def test_increment_counter(self, mock_redis):
        from app.services.vector.redis_cache import increment_counter
        increment_counter("cache_hits", 3)
        mock_redis.incrby.assert_called_once_with("vector_analytics:cache_hits", 3)

    def test_record_latency(self, mock_redis):
        from app.services.vector.redis_cache import record_latency
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value = mock_pipeline
        record_latency("ann_search", 42.5)
        mock_pipeline.hincrbyfloat.assert_called_once()
        mock_pipeline.execute.assert_called_once()
