-- Create plan_changes table to track all modifications to saas_plans and saas_plan_limits

CREATE TABLE plan_changes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id UUID NOT NULL REFERENCES saas_plans(id) ON DELETE CASCADE,
  change_type TEXT NOT NULL CHECK (change_type IN ('price_update', 'limit_update', 'status_change', 'plan_created')),
  field_name TEXT NOT NULL, -- 'monthly_price', 'yearly_price', 'max_users', 'is_active', etc
  old_value TEXT,
  new_value TEXT NOT NULL,
  changed_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Indexes for common queries
  CONSTRAINT plan_id_not_null CHECK (plan_id IS NOT NULL)
);

CREATE INDEX idx_plan_changes_plan_id ON plan_changes(plan_id);
CREATE INDEX idx_plan_changes_created_at ON plan_changes(created_at DESC);
CREATE INDEX idx_plan_changes_changed_by ON plan_changes(changed_by);

-- Enable RLS to prevent unauthorized access beyond org scope
-- Since this is admin-only, we'll restrict to admin users via application logic
ALTER TABLE plan_changes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admin users can view all plan changes"
  ON plan_changes
  FOR SELECT
  USING (auth.jwt() ->> 'user_metadata'->>'is_admin' = 'true');

COMMENT ON TABLE plan_changes IS 'Audit trail for all modifications to SaaS plans: pricing, limits, and status changes. Enables compliance and historical cost analysis per plan evolution.';
