-- Metadata, audit, and evaluation store (Aurora PostgreSQL Serverless v2)
-- Deliberately a separate cluster from the Knowledge Base's own Aurora
-- pgvector cluster -- Bedrock manages that one's internals, this one is
-- the application's own data layer.

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- for gen_random_uuid()

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       TEXT NOT NULL,
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    message_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id         UUID NOT NULL REFERENCES chat_sessions(session_id),
    role               TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content            TEXT NOT NULL,
    retrieved_sources  TEXT[],
    latency_ms         INTEGER,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_feedback (
    feedback_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id    UUID NOT NULL REFERENCES messages(message_id),
    rating        SMALLINT NOT NULL CHECK (rating IN (-1, 1)),
    comment       TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- faithfulness / answer_relevance / context_precision are populated from
-- real CloudWatch Embedded Metric Format data emitted by AgentCore's
-- batch evaluation feature (see eval/README.md) -- not hand-entered.
CREATE TABLE IF NOT EXISTS eval_runs (
    run_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_label       TEXT NOT NULL,
    faithfulness       NUMERIC(4,3),
    answer_relevance   NUMERIC(4,3),
    context_precision  NUMERIC(4,3),
    context_recall     NUMERIC(4,3),
    run_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_eval_runs_config ON eval_runs(config_label);
