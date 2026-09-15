-- ====================================================================
-- Database Creation Script
-- Execute this script as a superuser (e.g., postgres) to create the 
-- Spec2IS database and role before running the schema initialization.
-- ====================================================================

-- 1. Create a dedicated user/role (Change password in production)
-- CREATE ROLE spec2is_user WITH LOGIN PASSWORD 'your_secure_password';

-- 2. Create the database
-- Note: PostgreSQL does not support CREATE DATABASE inside a transaction block.
-- Run this statement independently.
CREATE DATABASE spec2is_db;

-- 3. Grant privileges
-- GRANT ALL PRIVILEGES ON DATABASE spec2is_db TO spec2is_user;

-- 4. Connect to the new database
\c spec2is_db

-- 5. Enable required extensions in the new database
CREATE EXTENSION IF NOT EXISTS vector;
