-- Vero / Summersaas — PostgreSQL schema aligned with frontend forms
-- Run on a fresh database, or use migrations to ALTER existing tables.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

DO $$ BEGIN
    CREATE TYPE userrole AS ENUM ('ADMIN', 'TECHNICIAN', 'CUSTOMER');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE jobstatus AS ENUM (
        'pending', 'matched', 'negotiating', 'accepted',
        'in_progress', 'completed', 'cancelled'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE assignmentstatus AS ENUM ('pending', 'accepted', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ---------------------------------------------------------------------------
-- Auth: signup (full_name, email, password) / login (email, password)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email               VARCHAR(255) NOT NULL UNIQUE,
    full_name           VARCHAR(255),
    role                userrole NOT NULL DEFAULT 'CUSTOMER',
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    hashed_password     VARCHAR(255),
    user_type           VARCHAR(50),
    onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
    profile_status      VARCHAR(50) NOT NULL DEFAULT 'active',
    is_verified         BOOLEAN NOT NULL DEFAULT FALSE,
    trust_score         DOUBLE PRECISION NOT NULL DEFAULT 0,
    last_active_at      TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles (email);
CREATE INDEX IF NOT EXISTS idx_profiles_role ON profiles (role);

-- ---------------------------------------------------------------------------
-- Worker onboarding (WorkerOnboarding.tsx) — 5 stages
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS technician_profiles (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                     UUID NOT NULL UNIQUE REFERENCES profiles(id) ON DELETE CASCADE,

    -- Stage 1: fullName, email, phone, location, address, profilePicture
    full_name                   VARCHAR(255),
    email                       VARCHAR(255),
    phone                       VARCHAR(15),
    location                    VARCHAR(255),
    address                     TEXT,
    profile_picture_url         TEXT,

    -- Stage 2: role, industry, skills, experience, workType, languages
    role                        VARCHAR(255),
    industry                    VARCHAR(255),
    skills                      JSONB NOT NULL DEFAULT '[]',
    experience_years            INTEGER NOT NULL DEFAULT 0,
    preferred_work_types        JSONB NOT NULL DEFAULT '[]',
    languages                   JSONB NOT NULL DEFAULT '[]',

    -- Stage 3: days, hoursStart, hoursEnd, remote, currency, rate, prefLocations, emergency
    available_days              JSONB NOT NULL DEFAULT '[]',
    hours_start                 VARCHAR(8),
    hours_end                   VARCHAR(8),
    remote_pref                 VARCHAR(50),
    currency                    VARCHAR(20),
    daily_rate                  DOUBLE PRECISION,
    preferred_locations         VARCHAR(255),
    emergency_availability      VARCHAR(10),

    -- Stage 4: education, companies, history, bio, resume, linkedin
    education                   TEXT,
    previous_employers          TEXT,
    work_history                TEXT,
    bio                         TEXT,
    resume_url                  TEXT,
    linkedin_url                TEXT,

    -- Stage 5: certificates, licenses, governmentId, links[{platform,url}]
    certificates_url            TEXT,
    licenses_url                TEXT,
    government_id_url           TEXT,
    verification_links          JSONB NOT NULL DEFAULT '[]',

    -- Worker dashboard: custom matching message (max 72 chars)
    custom_status_message       VARCHAR(72),

    -- Platform / AI fields
    skill_embedding             vector(384),
    embedding_updated_at        TIMESTAMPTZ,
    embedding_version           INTEGER NOT NULL DEFAULT 0,
    success_score               DOUBLE PRECISION NOT NULL DEFAULT 0,
    fraud_risk_score            DOUBLE PRECISION NOT NULL DEFAULT 0,
    completion_rate             DOUBLE PRECISION NOT NULL DEFAULT 0,
    response_time_minutes       INTEGER NOT NULL DEFAULT 0,
    is_online                   BOOLEAN NOT NULL DEFAULT FALSE,
    is_emergency_available      BOOLEAN NOT NULL DEFAULT FALSE,
    current_status              VARCHAR(50) NOT NULL DEFAULT 'offline',
    last_seen_at                TIMESTAMPTZ,
    base_hourly_rate            DOUBLE PRECISION,
    minimum_acceptance_rate     DOUBLE PRECISION,
    surge_multiplier            DOUBLE PRECISION NOT NULL DEFAULT 1,
    total_jobs_completed        INTEGER NOT NULL DEFAULT 0,
    total_reviews               INTEGER NOT NULL DEFAULT 0,
    average_rating              DOUBLE PRECISION NOT NULL DEFAULT 0,
    is_background_verified      BOOLEAN NOT NULL DEFAULT FALSE,
    verification_level          VARCHAR(50) NOT NULL DEFAULT 'basic',
    latitude                    DOUBLE PRECISION,
    longitude                   DOUBLE PRECISION,
    service_radius_km           INTEGER NOT NULL DEFAULT 10,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_technician_profiles_user_id ON technician_profiles (user_id);

-- ---------------------------------------------------------------------------
-- Company onboarding (CompanyOnboarding.tsx) — 5 stages
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS company_profiles (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                     UUID NOT NULL UNIQUE REFERENCES profiles(id) ON DELETE CASCADE,

    -- Stage 1: companyName, email, phone, address, hqLocation, logo
    company_name                VARCHAR(255),
    email                       VARCHAR(255),
    phone                       VARCHAR(15),
    address                     TEXT,
    hq_location                 VARCHAR(255),
    logo_url                    TEXT,

    -- Stage 2: industry, otherIndustry, companySize, businessCategory, website, regions, about
    industry                    VARCHAR(100),
    other_industry              VARCHAR(255),
    company_size                VARCHAR(20),
    business_categories         JSONB NOT NULL DEFAULT '[]',
    website_url                 VARCHAR(500),
    operating_regions           JSONB NOT NULL DEFAULT '[]',
    about                       TEXT,

    -- Stage 3: workforceType, hiringFreq, remotePref, urgency, verificationReqs, currency, budget
    preferred_workforce_types   JSONB NOT NULL DEFAULT '[]',
    hiring_frequency            VARCHAR(50),
    remote_pref                 VARCHAR(50),
    urgency_handling            VARCHAR(50),
    verification_requirements JSONB NOT NULL DEFAULT '[]',
    currency                    VARCHAR(20),
    project_budget              DOUBLE PRECISION,

    -- Stage 4: teamSize, activeProjects, workforceGoals, assignmentWorkflow, commsPref, notifications
    current_team_size           INTEGER,
    active_projects_count       INTEGER,
    workforce_goals             JSONB NOT NULL DEFAULT '[]',
    assignment_workflow         VARCHAR(50),
    communication_preferences   JSONB NOT NULL DEFAULT '[]',
    notification_settings       VARCHAR(50),

    -- Stage 5: registration, taxDocs, rep, identity, portfolio, links[{platform,url}]
    registration_doc_url        TEXT,
    tax_docs_url                TEXT,
    identity_verification_url   TEXT,
    portfolio_url               TEXT,
    authorized_rep_name         VARCHAR(255),
    verification_links          JSONB NOT NULL DEFAULT '[]',

    -- Company dashboard profile edit: hiringPreferences
    hiring_preferences          TEXT,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_company_profiles_user_id ON company_profiles (user_id);

-- ---------------------------------------------------------------------------
-- Company dashboard — Create Workforce Request
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_requests (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id             UUID REFERENCES profiles(id) ON DELETE SET NULL,
    assigned_technician_id  UUID REFERENCES technician_profiles(id) ON DELETE SET NULL,

    required_role           VARCHAR(255),
    title                   VARCHAR(255) NOT NULL,
    description             TEXT,
    required_skills         JSONB NOT NULL DEFAULT '[]',
    budget                  DOUBLE PRECISION,
    location                VARCHAR(255),
    urgency_level           VARCHAR(20) NOT NULL DEFAULT 'normal',
    duration                VARCHAR(100),
    certifications_required TEXT,

    proposed_price          DOUBLE PRECISION,
    final_price             DOUBLE PRECISION,
    status                  jobstatus NOT NULL DEFAULT 'pending',
    latitude                DOUBLE PRECISION,
    longitude               DOUBLE PRECISION,
    address                 TEXT,
    scheduled_at            TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,
    negotiation_status      VARCHAR(50) NOT NULL DEFAULT 'none',
    ai_match_score          DOUBLE PRECISION,
    job_embedding           vector(384),

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_requests_customer_id ON job_requests (customer_id);
CREATE INDEX IF NOT EXISTS idx_job_requests_status ON job_requests (status);

-- ---------------------------------------------------------------------------
-- Profile page — Add Completed Assignment modal
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS technician_portfolio_entries (
    id                              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    technician_id                   UUID NOT NULL REFERENCES technician_profiles(id) ON DELETE CASCADE,
    operation_title                 VARCHAR(255) NOT NULL,
    scope_of_work                   TEXT,
    technical_role                  VARCHAR(255),
    commercial_client               VARCHAR(255),
    completion_year                 VARCHAR(10),
    skills_certifications_applied   JSONB NOT NULL DEFAULT '[]',
    proof_image_url                 VARCHAR(500),
    registry_verification_url       VARCHAR(500),
    is_featured                     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portfolio_technician_id ON technician_portfolio_entries (technician_id);

-- ---------------------------------------------------------------------------
-- Migration helpers for existing databases (idempotent column adds)
-- ---------------------------------------------------------------------------
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS phone VARCHAR(15);
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS location VARCHAR(255);
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS profile_picture_url TEXT;
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS role VARCHAR(255);
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS industry VARCHAR(255);
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS preferred_work_types JSONB NOT NULL DEFAULT '[]';
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS languages JSONB NOT NULL DEFAULT '[]';
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS available_days JSONB NOT NULL DEFAULT '[]';
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS hours_start VARCHAR(8);
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS hours_end VARCHAR(8);
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS remote_pref VARCHAR(50);
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS currency VARCHAR(20);
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS education TEXT;
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS work_history TEXT;
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS resume_url TEXT;
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS linkedin_url TEXT;
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS certificates_url TEXT;
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS licenses_url TEXT;
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS government_id_url TEXT;
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS embedding_updated_at TIMESTAMPTZ;
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS embedding_version INTEGER NOT NULL DEFAULT 0;
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS previous_employers TEXT;
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS preferred_locations VARCHAR(255);
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS emergency_availability VARCHAR(10);
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS custom_status_message VARCHAR(72);
ALTER TABLE technician_profiles ADD COLUMN IF NOT EXISTS verification_links JSONB NOT NULL DEFAULT '[]';

ALTER TABLE company_profiles ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES profiles(id) ON DELETE CASCADE;
ALTER TABLE company_profiles ADD COLUMN IF NOT EXISTS hiring_preferences TEXT;
ALTER TABLE company_profiles ADD COLUMN IF NOT EXISTS verification_links JSONB NOT NULL DEFAULT '[]';

ALTER TABLE job_requests ADD COLUMN IF NOT EXISTS required_role VARCHAR(255);
ALTER TABLE job_requests ADD COLUMN IF NOT EXISTS location VARCHAR(255);
ALTER TABLE job_requests ADD COLUMN IF NOT EXISTS duration VARCHAR(100);
ALTER TABLE job_requests ADD COLUMN IF NOT EXISTS certifications_required TEXT;

-- pgvector (Supabase: enable in Dashboard → Database → Extensions if this fails)
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE job_requests ADD COLUMN IF NOT EXISTS job_embedding vector(384);

-- Full operational schema: see backend/migrations/001_full_operational_schema.sql
-- Applied automatically on API startup via app.core.migrations.run_sql_migrations()
