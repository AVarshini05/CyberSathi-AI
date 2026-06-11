-- ===========================================
-- CCRMS Database Setup Script
-- ===========================================
-- Run this script ONCE to create the database.
--
-- Usage:
--   psql -U postgres -f setup_database.sql
--
-- Or from pgAdmin: Open Query Tool → Paste → Execute
-- ===========================================

-- Create the database if it doesn't exist
SELECT 'CREATE DATABASE ccrms'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ccrms')\gexec

-- Connect to the database and set permissions
\c ccrms

-- Grant privileges (adjust username if needed)
GRANT ALL PRIVILEGES ON DATABASE ccrms TO postgres;

-- Confirm setup
\echo '================================================'
\echo '  CCRMS database created successfully!'
\echo '  Database: ccrms'
\echo '  Owner:    postgres'
\echo '================================================'
