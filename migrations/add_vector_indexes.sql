-- ==========================================================================
-- Vector Index Migration
-- Run this ONCE in your Supabase SQL Editor or via psql.
-- These are idempotent (IF NOT EXISTS / CREATE EXTENSION IF NOT EXISTS).
-- ==========================================================================

-- 1. Enable pgvector extension (Supabase usually has it pre-installed)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. HNSW index on technician_profiles.skill_embedding (cosine distance)
--    m=16: 16 connections per node (good balance of speed vs recall)
--    ef_construction=64: higher = better recall at build time, slower build
--    vector_cosine_ops: cosine similarity  (<=> operator)
CREATE INDEX IF NOT EXISTS idx_technician_skill_embedding_hnsw
    ON technician_profiles
    USING hnsw (skill_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 3. HNSW index on job_requests.job_embedding (cosine distance)
CREATE INDEX IF NOT EXISTS idx_job_embedding_hnsw
    ON job_requests
    USING hnsw (job_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 4. Partial index — only index rows that actually have an embedding
--    (Reduces index size if many rows have NULL embeddings)
CREATE INDEX IF NOT EXISTS idx_technician_skill_embedding_partial
    ON technician_profiles (id)
    WHERE skill_embedding IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_job_embedding_partial
    ON job_requests (id)
    WHERE job_embedding IS NOT NULL;

-- 5. Set default runtime ef_search for ANN recall tuning.
--    Can be overridden per-query with: SET LOCAL hnsw.ef_search = 128;
ALTER DATABASE postgres SET hnsw.ef_search = 64;

-- ==========================================================================
-- Verify indexes were created:
-- SELECT indexname, indexdef FROM pg_indexes
-- WHERE tablename IN ('technician_profiles', 'job_requests')
--   AND indexname LIKE '%embedding%';
-- ==========================================================================
