-- ============================================================
-- XSSniper — Supabase Schema  (run once in SQL Editor)
-- https://supabase.com/dashboard/project/<your-id>/sql/new
-- ============================================================

-- ── Users ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.users (
    id                     BIGSERIAL    PRIMARY KEY,
    username               TEXT UNIQUE  NOT NULL,
    email                  TEXT UNIQUE,
    password               TEXT         NOT NULL,
    role                   TEXT         NOT NULL DEFAULT 'user',
    email_verified         BOOLEAN      NOT NULL DEFAULT FALSE,
    failed_login_attempts  INTEGER      NOT NULL DEFAULT 0,
    locked_until           TIMESTAMPTZ,
    preferences            JSONB,
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Migration: add new columns if table already exists
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS email_verified        BOOLEAN     NOT NULL DEFAULT FALSE;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER     NOT NULL DEFAULT 0;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS locked_until          TIMESTAMPTZ;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS preferences           JSONB;

-- ── Scans ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.scans (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT           REFERENCES public.users(id) ON DELETE SET NULL,
    date             TEXT             NOT NULL,
    url              TEXT             NOT NULL,
    status           TEXT             NOT NULL,
    vulnerabilities  INTEGER          NOT NULL DEFAULT 0,
    log_output       TEXT,
    config           TEXT,
    duration         DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at       TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

-- Migration: add user_id if table already exists (run this if upgrading)
ALTER TABLE public.scans ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES public.users(id) ON DELETE SET NULL;

-- ── Password Resets ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.password_resets (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT      NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token      TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Email Verifications ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.email_verifications (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT      NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token      TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Row Level Security ────────────────────────────────────────
ALTER TABLE public.users                ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scans                ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.password_resets      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.email_verifications  ENABLE ROW LEVEL SECURITY;

-- ── Indexes ───────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_scans_date            ON public.scans (date DESC);
CREATE INDEX IF NOT EXISTS idx_scans_user_id         ON public.scans (user_id);
CREATE INDEX IF NOT EXISTS idx_users_email           ON public.users (email);
CREATE INDEX IF NOT EXISTS idx_users_username        ON public.users (username);
CREATE INDEX IF NOT EXISTS idx_resets_token          ON public.password_resets (token);
CREATE INDEX IF NOT EXISTS idx_resets_user_id        ON public.password_resets (user_id);
CREATE INDEX IF NOT EXISTS idx_email_verif_token     ON public.email_verifications (token);
CREATE INDEX IF NOT EXISTS idx_email_verif_user      ON public.email_verifications (user_id);

-- ============================================================
-- Done! Admin is pre-verified. username: admin | password: Admin@1234
-- ============================================================
