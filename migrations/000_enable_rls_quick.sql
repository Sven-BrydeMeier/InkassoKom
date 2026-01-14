-- ============================================================================
-- QUICK FIX: Enable RLS on ALL Tables (Minimal)
-- ============================================================================
-- Run this FIRST to immediately resolve Supabase security alerts!
--
-- This script:
-- 1. Enables RLS on all tables
-- 2. Adds a simple "authenticated users only" policy
--
-- For full multi-tenancy security, also run 001_enable_rls_all_tables.sql
-- ============================================================================

-- Enable RLS on all application tables
ALTER TABLE IF EXISTS organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS parties ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS case_parties ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ledger_bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS payment_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS generated_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS letterheads ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS deadlines ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS communications ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS audit_logs ENABLE ROW LEVEL SECURITY;

-- Force RLS even for table owners
ALTER TABLE IF EXISTS organizations FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS users FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS memberships FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS cases FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS parties FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS case_parties FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS claims FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ledger_bookings FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS payments FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS payment_allocations FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS documents FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS document_chunks FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS generated_documents FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS templates FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS letterheads FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS deadlines FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS communications FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS messages FORCE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS audit_logs FORCE ROW LEVEL SECURITY;

-- Simple policy: Only authenticated users can access
-- (This is a temporary fallback - use 001 for proper multi-tenancy)

CREATE POLICY IF NOT EXISTS "auth_access" ON organizations FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON users FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON memberships FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON cases FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON parties FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON case_parties FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON claims FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON ledger_bookings FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON payments FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON payment_allocations FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON documents FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON document_chunks FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON generated_documents FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON templates FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON letterheads FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON deadlines FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON communications FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON messages FOR ALL USING (auth.uid() IS NOT NULL);
CREATE POLICY IF NOT EXISTS "auth_access" ON audit_logs FOR ALL USING (auth.uid() IS NOT NULL);

-- Verify RLS is enabled
SELECT
  schemaname,
  tablename,
  rowsecurity as "RLS Enabled"
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
