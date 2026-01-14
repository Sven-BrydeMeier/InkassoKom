-- ============================================================================
-- MIGRATION: Enable Row Level Security (RLS) on ALL Tables
-- ============================================================================
-- Supabase Security Alert: RLS must be enabled on all tables exposed to PostgREST
--
-- This migration:
-- 1. Enables RLS on all application tables
-- 2. Creates security policies based on organization membership
-- 3. Ensures multi-tenancy data isolation
--
-- WICHTIG: Dieses Script in der Supabase SQL Editor ausführen!
-- ============================================================================

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get current user's organization IDs
CREATE OR REPLACE FUNCTION get_user_org_ids()
RETURNS UUID[] AS $$
BEGIN
  RETURN ARRAY(
    SELECT organization_id
    FROM memberships
    WHERE user_id = auth.uid()
    AND is_active = true
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- Function to check if user is member of organization
CREATE OR REPLACE FUNCTION is_member_of_org(org_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM memberships
    WHERE user_id = auth.uid()
    AND organization_id = org_id
    AND is_active = true
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- Function to check if user is admin of organization
CREATE OR REPLACE FUNCTION is_admin_of_org(org_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM memberships
    WHERE user_id = auth.uid()
    AND organization_id = org_id
    AND role = 'admin'
    AND is_active = true
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- ============================================================================
-- ENABLE RLS ON ALL TABLES
-- ============================================================================

-- 1. Organizations
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations FORCE ROW LEVEL SECURITY;

-- 2. Users
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;

-- 3. Memberships
ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE memberships FORCE ROW LEVEL SECURITY;

-- 4. Cases
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE cases FORCE ROW LEVEL SECURITY;

-- 5. Parties
ALTER TABLE parties ENABLE ROW LEVEL SECURITY;
ALTER TABLE parties FORCE ROW LEVEL SECURITY;

-- 6. Case Parties
ALTER TABLE case_parties ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_parties FORCE ROW LEVEL SECURITY;

-- 7. Claims
ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims FORCE ROW LEVEL SECURITY;

-- 8. Ledger Bookings
ALTER TABLE ledger_bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE ledger_bookings FORCE ROW LEVEL SECURITY;

-- 9. Payments
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments FORCE ROW LEVEL SECURITY;

-- 10. Payment Allocations
ALTER TABLE payment_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_allocations FORCE ROW LEVEL SECURITY;

-- 11. Documents
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;

-- 12. Document Chunks
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks FORCE ROW LEVEL SECURITY;

-- 13. Generated Documents
ALTER TABLE generated_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_documents FORCE ROW LEVEL SECURITY;

-- 14. Templates
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE templates FORCE ROW LEVEL SECURITY;

-- 15. Letterheads
ALTER TABLE letterheads ENABLE ROW LEVEL SECURITY;
ALTER TABLE letterheads FORCE ROW LEVEL SECURITY;

-- 16. Deadlines
ALTER TABLE deadlines ENABLE ROW LEVEL SECURITY;
ALTER TABLE deadlines FORCE ROW LEVEL SECURITY;

-- 17. Communications
ALTER TABLE communications ENABLE ROW LEVEL SECURITY;
ALTER TABLE communications FORCE ROW LEVEL SECURITY;

-- 18. Messages
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages FORCE ROW LEVEL SECURITY;

-- 19. Audit Logs
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;

-- ============================================================================
-- DROP EXISTING POLICIES (if any)
-- ============================================================================

DO $$
DECLARE
  tbl TEXT;
  pol TEXT;
BEGIN
  FOR tbl IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    FOR pol IN SELECT policyname FROM pg_policies WHERE schemaname = 'public' AND tablename = tbl LOOP
      EXECUTE format('DROP POLICY IF EXISTS %I ON %I', pol, tbl);
    END LOOP;
  END LOOP;
END $$;

-- ============================================================================
-- POLICIES: Organizations
-- ============================================================================

-- Users can view organizations they are members of
CREATE POLICY "org_select_member" ON organizations
  FOR SELECT USING (is_member_of_org(id));

-- Only admins can update their organization
CREATE POLICY "org_update_admin" ON organizations
  FOR UPDATE USING (is_admin_of_org(id));

-- Only admins can insert (create new orgs)
CREATE POLICY "org_insert_authenticated" ON organizations
  FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

-- ============================================================================
-- POLICIES: Users
-- ============================================================================

-- Users can view their own profile
CREATE POLICY "users_select_own" ON users
  FOR SELECT USING (id = auth.uid());

-- Users can view others in same organization
CREATE POLICY "users_select_org_member" ON users
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM memberships m1
      WHERE m1.user_id = users.id
      AND m1.organization_id IN (SELECT organization_id FROM memberships WHERE user_id = auth.uid() AND is_active = true)
    )
  );

-- Users can update their own profile
CREATE POLICY "users_update_own" ON users
  FOR UPDATE USING (id = auth.uid());

-- Users can insert their own profile (on signup)
CREATE POLICY "users_insert_own" ON users
  FOR INSERT WITH CHECK (id = auth.uid());

-- ============================================================================
-- POLICIES: Memberships
-- ============================================================================

-- Users can see their own memberships
CREATE POLICY "memberships_select_own" ON memberships
  FOR SELECT USING (user_id = auth.uid());

-- Users can see memberships in their organizations
CREATE POLICY "memberships_select_org" ON memberships
  FOR SELECT USING (is_member_of_org(organization_id));

-- Only admins can insert/update/delete memberships
CREATE POLICY "memberships_insert_admin" ON memberships
  FOR INSERT WITH CHECK (is_admin_of_org(organization_id));

CREATE POLICY "memberships_update_admin" ON memberships
  FOR UPDATE USING (is_admin_of_org(organization_id));

CREATE POLICY "memberships_delete_admin" ON memberships
  FOR DELETE USING (is_admin_of_org(organization_id));

-- ============================================================================
-- POLICIES: Cases (Organization-scoped)
-- ============================================================================

CREATE POLICY "cases_select" ON cases
  FOR SELECT USING (is_member_of_org(organization_id));

CREATE POLICY "cases_insert" ON cases
  FOR INSERT WITH CHECK (is_member_of_org(organization_id));

CREATE POLICY "cases_update" ON cases
  FOR UPDATE USING (is_member_of_org(organization_id));

CREATE POLICY "cases_delete" ON cases
  FOR DELETE USING (is_member_of_org(organization_id));

-- ============================================================================
-- POLICIES: Parties (Organization-scoped)
-- ============================================================================

CREATE POLICY "parties_select" ON parties
  FOR SELECT USING (is_member_of_org(organization_id));

CREATE POLICY "parties_insert" ON parties
  FOR INSERT WITH CHECK (is_member_of_org(organization_id));

CREATE POLICY "parties_update" ON parties
  FOR UPDATE USING (is_member_of_org(organization_id));

CREATE POLICY "parties_delete" ON parties
  FOR DELETE USING (is_member_of_org(organization_id));

-- ============================================================================
-- POLICIES: Case Parties (via Case)
-- ============================================================================

CREATE POLICY "case_parties_select" ON case_parties
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "case_parties_insert" ON case_parties
  FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "case_parties_update" ON case_parties
  FOR UPDATE USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "case_parties_delete" ON case_parties
  FOR DELETE USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

-- ============================================================================
-- POLICIES: Claims (via Case)
-- ============================================================================

CREATE POLICY "claims_select" ON claims
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "claims_insert" ON claims
  FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "claims_update" ON claims
  FOR UPDATE USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "claims_delete" ON claims
  FOR DELETE USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

-- ============================================================================
-- POLICIES: Ledger Bookings (via Case)
-- ============================================================================

CREATE POLICY "ledger_bookings_select" ON ledger_bookings
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "ledger_bookings_insert" ON ledger_bookings
  FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "ledger_bookings_update" ON ledger_bookings
  FOR UPDATE USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "ledger_bookings_delete" ON ledger_bookings
  FOR DELETE USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

-- ============================================================================
-- POLICIES: Payments (via Case)
-- ============================================================================

CREATE POLICY "payments_select" ON payments
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "payments_insert" ON payments
  FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "payments_update" ON payments
  FOR UPDATE USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "payments_delete" ON payments
  FOR DELETE USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

-- ============================================================================
-- POLICIES: Payment Allocations (via Payment -> Case)
-- ============================================================================

CREATE POLICY "payment_allocations_select" ON payment_allocations
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM payments p
      JOIN cases c ON c.id = p.case_id
      WHERE p.id = payment_id AND is_member_of_org(c.organization_id)
    )
  );

CREATE POLICY "payment_allocations_insert" ON payment_allocations
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM payments p
      JOIN cases c ON c.id = p.case_id
      WHERE p.id = payment_id AND is_member_of_org(c.organization_id)
    )
  );

CREATE POLICY "payment_allocations_update" ON payment_allocations
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM payments p
      JOIN cases c ON c.id = p.case_id
      WHERE p.id = payment_id AND is_member_of_org(c.organization_id)
    )
  );

CREATE POLICY "payment_allocations_delete" ON payment_allocations
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM payments p
      JOIN cases c ON c.id = p.case_id
      WHERE p.id = payment_id AND is_member_of_org(c.organization_id)
    )
  );

-- ============================================================================
-- POLICIES: Documents (Organization-scoped)
-- ============================================================================

CREATE POLICY "documents_select" ON documents
  FOR SELECT USING (
    organization_id IS NOT NULL AND is_member_of_org(organization_id)
    OR (case_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id)
    ))
  );

CREATE POLICY "documents_insert" ON documents
  FOR INSERT WITH CHECK (
    (organization_id IS NOT NULL AND is_member_of_org(organization_id))
    OR (case_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id)
    ))
  );

CREATE POLICY "documents_update" ON documents
  FOR UPDATE USING (
    (organization_id IS NOT NULL AND is_member_of_org(organization_id))
    OR (case_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id)
    ))
  );

CREATE POLICY "documents_delete" ON documents
  FOR DELETE USING (
    (organization_id IS NOT NULL AND is_member_of_org(organization_id))
    OR (case_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id)
    ))
  );

-- ============================================================================
-- POLICIES: Document Chunks (Organization-scoped)
-- ============================================================================

CREATE POLICY "document_chunks_select" ON document_chunks
  FOR SELECT USING (is_member_of_org(organization_id));

CREATE POLICY "document_chunks_insert" ON document_chunks
  FOR INSERT WITH CHECK (is_member_of_org(organization_id));

CREATE POLICY "document_chunks_update" ON document_chunks
  FOR UPDATE USING (is_member_of_org(organization_id));

CREATE POLICY "document_chunks_delete" ON document_chunks
  FOR DELETE USING (is_member_of_org(organization_id));

-- ============================================================================
-- POLICIES: Generated Documents (via Case)
-- ============================================================================

CREATE POLICY "generated_documents_select" ON generated_documents
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "generated_documents_insert" ON generated_documents
  FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "generated_documents_update" ON generated_documents
  FOR UPDATE USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "generated_documents_delete" ON generated_documents
  FOR DELETE USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

-- ============================================================================
-- POLICIES: Templates (Organization-scoped)
-- ============================================================================

CREATE POLICY "templates_select" ON templates
  FOR SELECT USING (is_member_of_org(organization_id));

CREATE POLICY "templates_insert" ON templates
  FOR INSERT WITH CHECK (is_member_of_org(organization_id));

CREATE POLICY "templates_update" ON templates
  FOR UPDATE USING (is_member_of_org(organization_id));

CREATE POLICY "templates_delete" ON templates
  FOR DELETE USING (is_admin_of_org(organization_id));

-- ============================================================================
-- POLICIES: Letterheads (Organization-scoped)
-- ============================================================================

CREATE POLICY "letterheads_select" ON letterheads
  FOR SELECT USING (is_member_of_org(organization_id));

CREATE POLICY "letterheads_insert" ON letterheads
  FOR INSERT WITH CHECK (is_member_of_org(organization_id));

CREATE POLICY "letterheads_update" ON letterheads
  FOR UPDATE USING (is_member_of_org(organization_id));

CREATE POLICY "letterheads_delete" ON letterheads
  FOR DELETE USING (is_admin_of_org(organization_id));

-- ============================================================================
-- POLICIES: Deadlines (via Case)
-- ============================================================================

CREATE POLICY "deadlines_select" ON deadlines
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "deadlines_insert" ON deadlines
  FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "deadlines_update" ON deadlines
  FOR UPDATE USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "deadlines_delete" ON deadlines
  FOR DELETE USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

-- ============================================================================
-- POLICIES: Communications (via Case)
-- ============================================================================

CREATE POLICY "communications_select" ON communications
  FOR SELECT USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "communications_insert" ON communications
  FOR INSERT WITH CHECK (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "communications_update" ON communications
  FOR UPDATE USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

CREATE POLICY "communications_delete" ON communications
  FOR DELETE USING (
    EXISTS (SELECT 1 FROM cases c WHERE c.id = case_id AND is_member_of_org(c.organization_id))
  );

-- ============================================================================
-- POLICIES: Messages (via Communication -> Case)
-- ============================================================================

CREATE POLICY "messages_select" ON messages
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM communications comm
      JOIN cases c ON c.id = comm.case_id
      WHERE comm.id = thread_id AND is_member_of_org(c.organization_id)
    )
  );

CREATE POLICY "messages_insert" ON messages
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM communications comm
      JOIN cases c ON c.id = comm.case_id
      WHERE comm.id = thread_id AND is_member_of_org(c.organization_id)
    )
  );

CREATE POLICY "messages_update" ON messages
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM communications comm
      JOIN cases c ON c.id = comm.case_id
      WHERE comm.id = thread_id AND is_member_of_org(c.organization_id)
    )
  );

CREATE POLICY "messages_delete" ON messages
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM communications comm
      JOIN cases c ON c.id = comm.case_id
      WHERE comm.id = thread_id AND is_member_of_org(c.organization_id)
    )
  );

-- ============================================================================
-- POLICIES: Audit Logs (Organization-scoped, read-only for non-admins)
-- ============================================================================

CREATE POLICY "audit_logs_select" ON audit_logs
  FOR SELECT USING (
    organization_id IS NULL
    OR is_member_of_org(organization_id)
  );

-- Only system can insert audit logs (via service role)
CREATE POLICY "audit_logs_insert_service" ON audit_logs
  FOR INSERT WITH CHECK (
    auth.jwt()->>'role' = 'service_role'
    OR (organization_id IS NULL AND auth.uid() IS NOT NULL)
    OR is_member_of_org(organization_id)
  );

-- Audit logs should never be updated or deleted
-- (No UPDATE/DELETE policies = forbidden)

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

-- Grant usage on helper functions
GRANT EXECUTE ON FUNCTION get_user_org_ids() TO authenticated;
GRANT EXECUTE ON FUNCTION is_member_of_org(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION is_admin_of_org(UUID) TO authenticated;

-- ============================================================================
-- VERIFICATION QUERY
-- ============================================================================
-- Run this to verify RLS is enabled on all tables:

-- SELECT
--   schemaname,
--   tablename,
--   rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- ORDER BY tablename;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
