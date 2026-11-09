-- AI Runtime Database Initialization
-- This file runs only on first container startup.
-- Alembic migrations handle the actual schema.

-- Create test database (available for CI)
SELECT 'CREATE DATABASE ai_runtime_test OWNER ai_runtime_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ai_runtime_test')\gexec

-- Ensure uuid-ossp extension is available
\c ai_runtime;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c ai_runtime_test;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
