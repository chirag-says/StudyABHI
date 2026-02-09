-- ============================================================
-- PostgreSQL Indexes for UPSC AI Platform
-- Run these after initial schema creation
-- ============================================================

-- ==================== USER INDEXES ====================

-- Fast user lookup by email (login)
CREATE INDEX IF NOT EXISTS idx_users_email 
ON users(email);

-- Active users filter
CREATE INDEX IF NOT EXISTS idx_users_active 
ON users(is_active) WHERE is_active = true;

-- User role filtering (for admin queries)
CREATE INDEX IF NOT EXISTS idx_users_role 
ON users(role);


-- ==================== DOCUMENT INDEXES ====================

-- User's documents (dashboard)
CREATE INDEX IF NOT EXISTS idx_documents_user_id 
ON documents(user_id);

-- Documents by status (processing queue)
CREATE INDEX IF NOT EXISTS idx_documents_status 
ON documents(status);

-- User's documents sorted by date (list view)
CREATE INDEX IF NOT EXISTS idx_documents_user_created 
ON documents(user_id, created_at DESC);

-- Document chunks by document (for RAG retrieval)
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id 
ON document_chunks(document_id);

-- Chunks by embedding status (batch processing)
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedded 
ON document_chunks(is_embedded) WHERE is_embedded = false;


-- ==================== QUIZ INDEXES ====================

-- User's quizzes
CREATE INDEX IF NOT EXISTS idx_quizzes_created_by 
ON quizzes(created_by);

-- Published quizzes (public listing)
CREATE INDEX IF NOT EXISTS idx_quizzes_status 
ON quizzes(status) WHERE status = 'published';

-- Quiz questions by quiz
CREATE INDEX IF NOT EXISTS idx_quiz_questions_quiz_id 
ON quiz_questions(quiz_id);

-- Questions by topic (analytics)
CREATE INDEX IF NOT EXISTS idx_quiz_questions_topic_id 
ON quiz_questions(topic_id);


-- ==================== QUIZ ATTEMPTS INDEXES ====================

-- User's attempt history (dashboard)
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_id 
ON quiz_attempts(user_id);

-- User + quiz combination (check existing attempts)
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_quiz 
ON quiz_attempts(user_id, quiz_id);

-- Recent attempts for analytics (last 30 days)
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_date 
ON quiz_attempts(user_id, completed_at DESC);

-- In-progress attempts (resume functionality)
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_in_progress 
ON quiz_attempts(user_id, status) WHERE status = 'in_progress';

-- Question answers by attempt
CREATE INDEX IF NOT EXISTS idx_question_answers_attempt_id 
ON question_answers(attempt_id);


-- ==================== LEARNING ANALYTICS INDEXES ====================

-- Study sessions by user (dashboard)
CREATE INDEX IF NOT EXISTS idx_study_sessions_user_id 
ON study_sessions(user_id);

-- User's sessions by date (calendar view)
CREATE INDEX IF NOT EXISTS idx_study_sessions_user_date 
ON study_sessions(user_id, started_at DESC);

-- Sessions by topic (topic analytics)
CREATE INDEX IF NOT EXISTS idx_study_sessions_topic_id 
ON study_sessions(topic_id);

-- Daily progress by user and date
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_progress_user_date 
ON daily_progress(user_id, date);

-- Topic proficiency by user (weak areas)
CREATE INDEX IF NOT EXISTS idx_topic_proficiency_user_id 
ON topic_proficiency(user_id);

-- Topics needing revision
CREATE INDEX IF NOT EXISTS idx_topic_proficiency_revision 
ON topic_proficiency(user_id, needs_revision) WHERE needs_revision = true;

-- Weak areas
CREATE INDEX IF NOT EXISTS idx_topic_proficiency_weak 
ON topic_proficiency(user_id, is_weak_area) WHERE is_weak_area = true;

-- Learning goals by user and status
CREATE INDEX IF NOT EXISTS idx_learning_goals_user_status 
ON learning_goals(user_id, status);

-- Milestones by user (achievements page)
CREATE INDEX IF NOT EXISTS idx_learning_milestones_user_id 
ON learning_milestones(user_id);


-- ==================== ATTENTION TRACKING INDEXES ====================

-- Attention sessions by user
CREATE INDEX IF NOT EXISTS idx_attention_sessions_user_id 
ON attention_sessions(user_id);

-- User sessions by date (daily view)
CREATE INDEX IF NOT EXISTS idx_attention_sessions_user_date 
ON attention_sessions(user_id, created_at DESC);

-- Daily summaries by user
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_attention_user_date 
ON daily_attention_summaries(user_id, date);


-- ==================== SYLLABUS INDEXES ====================

-- Topics by subject
CREATE INDEX IF NOT EXISTS idx_topics_subject_id 
ON topics(subject_id);

-- Topics by parent (tree navigation)
CREATE INDEX IF NOT EXISTS idx_topics_parent_id 
ON topics(parent_topic_id);

-- Content by topic
CREATE INDEX IF NOT EXISTS idx_content_topics_topic 
ON content_topics(topic_id);


-- ==================== PRIVACY INDEXES ====================

-- Privacy settings by user (quick lookup)
CREATE UNIQUE INDEX IF NOT EXISTS idx_privacy_settings_user_id 
ON user_privacy_settings(user_id);

-- Pending export requests
CREATE INDEX IF NOT EXISTS idx_export_requests_pending 
ON data_export_requests(user_id, status) WHERE status = 'pending';

-- Pending deletion requests (scheduled job)
CREATE INDEX IF NOT EXISTS idx_deletion_requests_pending 
ON account_deletion_requests(status, scheduled_deletion_date) 
WHERE status = 'pending';


-- ==================== COMPOSITE INDEXES FOR ANALYTICS ====================

-- Quiz performance by user and topic (analytics dashboard)
CREATE INDEX IF NOT EXISTS idx_quiz_performance_analytics 
ON quiz_attempts(user_id, score_percentage, completed_at DESC);

-- Study time analytics
CREATE INDEX IF NOT EXISTS idx_study_analytics 
ON study_sessions(user_id, session_type, duration_minutes);


-- ==================== FULL-TEXT SEARCH INDEXES ====================

-- Content full-text search (if using PostgreSQL)
-- CREATE INDEX IF NOT EXISTS idx_content_fulltext 
-- ON contents USING GIN(to_tsvector('english', title || ' ' || body));

-- Document chunk search
-- CREATE INDEX IF NOT EXISTS idx_chunks_fulltext 
-- ON document_chunks USING GIN(to_tsvector('english', content));


-- ==================== JSONB INDEXES ====================

-- Quiz topic performance JSON (for filtering)
-- CREATE INDEX IF NOT EXISTS idx_quiz_attempt_topic_perf 
-- ON quiz_attempts USING GIN(topic_performance);


-- ============================================================
-- Index Maintenance Commands (run periodically)
-- ============================================================

-- Analyze tables for query planner
-- ANALYZE users;
-- ANALYZE documents;
-- ANALYZE quizzes;
-- ANALYZE quiz_attempts;
-- ANALYZE study_sessions;

-- Reindex if needed (during maintenance window)
-- REINDEX TABLE quiz_attempts;
