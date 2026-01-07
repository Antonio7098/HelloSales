BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> a1b4b67ec474

CREATE TABLE users (
    id UUID NOT NULL, 
    clerk_id VARCHAR(255) NOT NULL, 
    email VARCHAR(255), 
    display_name VARCHAR(255), 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_clerk_id ON users (clerk_id);

CREATE TABLE sessions (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    state VARCHAR(20) NOT NULL, 
    started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    ended_at TIMESTAMP WITHOUT TIME ZONE, 
    total_cost_cents INTEGER NOT NULL, 
    interaction_count INTEGER NOT NULL, 
    duration_ms INTEGER, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_sessions_state ON sessions (state);

CREATE INDEX ix_sessions_user_id ON sessions (user_id);

CREATE TABLE interactions (
    id UUID NOT NULL, 
    session_id UUID NOT NULL, 
    message_id UUID NOT NULL, 
    role VARCHAR(10) NOT NULL, 
    input_type VARCHAR(10), 
    content TEXT NOT NULL, 
    transcript TEXT, 
    audio_url VARCHAR(500), 
    audio_duration_ms INTEGER, 
    stt_cost_cents INTEGER NOT NULL, 
    llm_cost_cents INTEGER NOT NULL, 
    tts_cost_cents INTEGER NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

CREATE INDEX ix_interactions_created_at ON interactions (created_at);

CREATE UNIQUE INDEX ix_interactions_message_id ON interactions (message_id);

CREATE INDEX ix_interactions_session_id ON interactions (session_id);

CREATE TABLE provider_calls (
    id UUID NOT NULL, 
    request_id UUID, 
    session_id UUID, 
    user_id UUID, 
    provider VARCHAR(50) NOT NULL, 
    operation VARCHAR(20) NOT NULL, 
    model_id VARCHAR(100), 
    latency_ms INTEGER, 
    tokens_in INTEGER, 
    tokens_out INTEGER, 
    audio_ms INTEGER, 
    cost_cents INTEGER, 
    success BOOLEAN NOT NULL, 
    error TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE SET NULL, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_provider_calls_created_at ON provider_calls (created_at);

CREATE INDEX ix_provider_calls_provider ON provider_calls (provider);

CREATE INDEX ix_provider_calls_session_id ON provider_calls (session_id);

CREATE TABLE summary_state (
    id UUID NOT NULL, 
    session_id UUID NOT NULL, 
    turns_since INTEGER NOT NULL, 
    last_cutoff_idx INTEGER NOT NULL, 
    last_summary_at TIMESTAMP WITHOUT TIME ZONE, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_summary_state_session_id ON summary_state (session_id);

INSERT INTO alembic_version (version_num) VALUES ('a1b4b67ec474') RETURNING alembic_version.version_num;

-- Running upgrade a1b4b67ec474 -> c2e588b9b9e7

CREATE TABLE session_summaries (
    id UUID NOT NULL, 
    session_id UUID NOT NULL, 
    version INTEGER NOT NULL, 
    text TEXT NOT NULL, 
    cutoff_idx INTEGER, 
    token_count INTEGER, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_session_summaries_session_version UNIQUE (session_id, version), 
    FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

COMMENT ON COLUMN session_summaries.version IS 'Incrementing version per session';

COMMENT ON COLUMN session_summaries.text IS 'The compressed summary text';

COMMENT ON COLUMN session_summaries.cutoff_idx IS 'Interaction index this summary covers up to';

COMMENT ON COLUMN session_summaries.token_count IS 'Token count of this summary';

CREATE INDEX idx_session_summaries_session ON session_summaries (session_id);

UPDATE alembic_version SET version_num='c2e588b9b9e7' WHERE alembic_version.version_num = 'a1b4b67ec474';

-- Running upgrade c2e588b9b9e7 -> ae9527b7b4e3

ALTER TABLE interactions ADD COLUMN latency_ms INTEGER;

ALTER TABLE interactions ADD COLUMN tokens_in INTEGER;

ALTER TABLE interactions ADD COLUMN tokens_out INTEGER;

DROP INDEX idx_session_summaries_session;

CREATE INDEX ix_session_summaries_session_id ON session_summaries (session_id);

UPDATE alembic_version SET version_num='ae9527b7b4e3' WHERE alembic_version.version_num = 'c2e588b9b9e7';

-- Running upgrade ae9527b7b4e3 -> addec770b753

CREATE TABLE skills (
    id UUID NOT NULL, 
    slug VARCHAR(100) NOT NULL, 
    title VARCHAR(255) NOT NULL, 
    description TEXT, 
    levels JSONB NOT NULL, 
    category VARCHAR(100), 
    is_active BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_skills_slug UNIQUE (slug)
);

CREATE UNIQUE INDEX ix_skills_slug ON skills (slug);

CREATE INDEX ix_skills_is_active ON skills (is_active);

CREATE TABLE user_skills (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    skill_id UUID NOT NULL, 
    current_level INTEGER NOT NULL, 
    is_tracked BOOLEAN NOT NULL, 
    track_order INTEGER, 
    started_at TIMESTAMP WITHOUT TIME ZONE, 
    last_tracked_at TIMESTAMP WITHOUT TIME ZONE, 
    untracked_at TIMESTAMP WITHOUT TIME ZONE, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE CASCADE, 
    CONSTRAINT uq_user_skills_user_skill UNIQUE (user_id, skill_id), 
    CONSTRAINT valid_track_order CHECK (track_order IS NULL OR track_order IN (1, 2))
);

CREATE INDEX ix_user_skills_user_id ON user_skills (user_id);

CREATE INDEX idx_user_skills_tracked ON user_skills (user_id, is_tracked) WHERE is_tracked = true;

UPDATE alembic_version SET version_num='addec770b753' WHERE alembic_version.version_num = 'ae9527b7b4e3';

-- Running upgrade addec770b753 -> b7cfe0c9d123

CREATE TABLE assessments (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    session_id UUID NOT NULL, 
    interaction_id UUID, 
    group_id UUID NOT NULL, 
    triage_decision VARCHAR(50), 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE, 
    FOREIGN KEY(interaction_id) REFERENCES interactions (id)
);

CREATE INDEX idx_assessments_session ON assessments (session_id);

CREATE INDEX idx_assessments_user ON assessments (user_id);

CREATE INDEX idx_assessments_group ON assessments (group_id);

CREATE INDEX idx_assessments_interaction ON assessments (interaction_id);

CREATE TABLE skill_assessments (
    id UUID NOT NULL, 
    assessment_id UUID NOT NULL, 
    skill_id UUID NOT NULL, 
    level INTEGER NOT NULL, 
    confidence FLOAT, 
    summary TEXT, 
    feedback JSONB NOT NULL, 
    provider VARCHAR(50), 
    model_id VARCHAR(100), 
    tokens_used INTEGER, 
    cost_cents INTEGER, 
    latency_ms INTEGER, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE CASCADE, 
    FOREIGN KEY(skill_id) REFERENCES skills (id)
);

CREATE INDEX idx_skill_assessments_assessment ON skill_assessments (assessment_id);

CREATE INDEX idx_skill_assessments_skill ON skill_assessments (skill_id);

CREATE TABLE skill_level_history (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    skill_id UUID NOT NULL, 
    from_level INTEGER NOT NULL, 
    to_level INTEGER NOT NULL, 
    reason VARCHAR(100), 
    source_assessment_id UUID, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    FOREIGN KEY(skill_id) REFERENCES skills (id), 
    FOREIGN KEY(source_assessment_id) REFERENCES assessments (id)
);

CREATE INDEX idx_skill_level_history_user_skill ON skill_level_history (user_id, skill_id);

CREATE INDEX idx_skill_level_history_created ON skill_level_history (created_at);

CREATE TABLE triage_log (
    id UUID NOT NULL, 
    session_id UUID NOT NULL, 
    interaction_id UUID, 
    decision VARCHAR(20) NOT NULL, 
    reason VARCHAR(255), 
    latency_ms INTEGER, 
    tokens_used INTEGER, 
    cost_cents INTEGER, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE, 
    FOREIGN KEY(interaction_id) REFERENCES interactions (id)
);

CREATE INDEX idx_triage_log_session ON triage_log (session_id);

CREATE INDEX idx_triage_log_created ON triage_log (created_at);

UPDATE alembic_version SET version_num='b7cfe0c9d123' WHERE alembic_version.version_num = 'addec770b753';

-- Running upgrade b7cfe0c9d123 -> c4a8d2e1f789

CREATE TABLE user_profiles (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    name VARCHAR(100), 
    role JSONB, 
    goal JSONB, 
    contexts JSONB, 
    notes TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_user_profiles_user_id UNIQUE (user_id)
);

CREATE UNIQUE INDEX idx_user_profiles_user ON user_profiles (user_id);

UPDATE alembic_version SET version_num='c4a8d2e1f789' WHERE alembic_version.version_num = 'b7cfe0c9d123';

-- Running upgrade c4a8d2e1f789 -> d5f1c3b4a901

CREATE TABLE feedback_events (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    session_id UUID, 
    interaction_id UUID, 
    role VARCHAR(20), 
    category VARCHAR(50) NOT NULL, 
    name VARCHAR(150) NOT NULL, 
    short_reason VARCHAR(255), 
    time_bucket VARCHAR(50), 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE, 
    FOREIGN KEY(interaction_id) REFERENCES interactions (id)
);

CREATE INDEX idx_feedback_user ON feedback_events (user_id);

CREATE INDEX idx_feedback_session ON feedback_events (session_id);

CREATE INDEX idx_feedback_interaction ON feedback_events (interaction_id);

UPDATE alembic_version SET version_num='d5f1c3b4a901' WHERE alembic_version.version_num = 'c4a8d2e1f789';

-- Running upgrade d5f1c3b4a901 -> e3b7a4c2f012

ALTER TABLE assessments ADD COLUMN triage_override_label VARCHAR(50);

UPDATE alembic_version SET version_num='e3b7a4c2f012' WHERE alembic_version.version_num = 'd5f1c3b4a901';

-- Running upgrade b7cfe0c9d123 -> evl003_add_eval_tables

CREATE TABLE eval_test_suites (
    id UUID NOT NULL, 
    name TEXT NOT NULL, 
    description TEXT, 
    created_by TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE TABLE eval_test_cases (
    id UUID NOT NULL, 
    suite_id UUID NOT NULL, 
    name TEXT NOT NULL, 
    source_interaction_id UUID, 
    source_session_id UUID, 
    transcript TEXT NOT NULL, 
    context_summary TEXT, 
    tracked_skills JSONB, 
    expected_triage_decision TEXT, 
    triage_notes TEXT, 
    expected_assessments JSONB, 
    metadata JSONB DEFAULT '{}'::jsonb NOT NULL, 
    labeled_by TEXT, 
    labeled_at TIMESTAMP WITHOUT TIME ZONE, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(suite_id) REFERENCES eval_test_suites (id) ON DELETE CASCADE
);

CREATE TABLE eval_benchmark_runs (
    id UUID NOT NULL, 
    suite_id UUID, 
    name TEXT, 
    config JSONB NOT NULL, 
    status TEXT DEFAULT 'pending' NOT NULL, 
    started_at TIMESTAMP WITHOUT TIME ZONE, 
    completed_at TIMESTAMP WITHOUT TIME ZONE, 
    summary JSONB, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(suite_id) REFERENCES eval_test_suites (id)
);

CREATE TABLE eval_test_results (
    id UUID NOT NULL, 
    run_id UUID NOT NULL, 
    test_case_id UUID NOT NULL, 
    actual_triage_decision TEXT, 
    triage_correct BOOLEAN, 
    triage_latency_ms INTEGER, 
    actual_assessments JSONB, 
    assessment_scores JSONB, 
    overall_accuracy FLOAT, 
    total_latency_ms INTEGER, 
    tokens_in INTEGER, 
    tokens_out INTEGER, 
    cost_cents NUMERIC(10, 4), 
    raw_response JSONB, 
    error TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(run_id) REFERENCES eval_benchmark_runs (id) ON DELETE CASCADE, 
    FOREIGN KEY(test_case_id) REFERENCES eval_test_cases (id)
);

INSERT INTO alembic_version (version_num) VALUES ('evl003_add_eval_tables') RETURNING alembic_version.version_num;

-- Running upgrade evl003_add_eval_tables, e3b7a4c2f012 -> merge_eval_feedback

DELETE FROM alembic_version WHERE alembic_version.version_num = 'evl003_add_eval_tables';

UPDATE alembic_version SET version_num='merge_eval_feedback' WHERE alembic_version.version_num = 'e3b7a4c2f012';

-- Running upgrade merge_eval_feedback -> f7b9c1a2d4e8

ALTER TABLE assessments ADD COLUMN deleted_at TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE assessments ADD COLUMN deleted_reason VARCHAR(255);

CREATE INDEX idx_assessments_deleted_at ON assessments (deleted_at);

UPDATE alembic_version SET version_num='f7b9c1a2d4e8' WHERE alembic_version.version_num = 'merge_eval_feedback';

COMMIT;

