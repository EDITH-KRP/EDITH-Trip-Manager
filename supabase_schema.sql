-- =============================================================================
-- EDITH TRIP MANAGER - SUPABASE POSTGRESQL PRODUCTION SCHEMA
-- Includes: Tables, Constraints, Indexes, Row Level Security (RLS), Policies,
-- and Pre-Seeded Crew Accounts: Prajwal (Admin), Parichay, Srujan, and Nitish.
--
-- How to apply:
-- 1. Open your Supabase Dashboard: https://supabase.com
-- 2. Go to SQL Editor -> New Query
-- 3. Paste this entire script and click "Run"
-- =============================================================================

-- Enable pgcrypto extension for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- 1. TABLE DEFINITIONS
-- -----------------------------------------------------------------------------

-- Users
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(32),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'member', -- 'admin' or 'member'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    created_by VARCHAR(64),
    must_change_password BOOLEAN NOT NULL DEFAULT FALSE
);

-- Groups
CREATE TABLE IF NOT EXISTS groups (
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name VARCHAR(120) NOT NULL,
    group_code VARCHAR(32) UNIQUE NOT NULL,
    monthly_contribution INTEGER NOT NULL DEFAULT 2000,
    duration_months INTEGER NOT NULL DEFAULT 12,
    start_date TIMESTAMPTZ,
    custody_holder_name VARCHAR(120),
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    created_by VARCHAR(64),
    trip_destination VARCHAR(255) DEFAULT 'Manali & Spiti Valley',
    trip_start_date DATE,
    trip_end_date DATE,
    planned_trip_budget INTEGER DEFAULT 96000,
    trip_notes TEXT DEFAULT '',
    trip_stops JSONB DEFAULT '[]'::jsonb,
    trip_title VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- Memberships
CREATE TABLE IF NOT EXISTS memberships (
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    group_id VARCHAR(64) NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_group_user UNIQUE(group_id, user_id)
);

-- Contributions (Savings Kitty)
CREATE TABLE IF NOT EXISTS contributions (
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    group_id VARCHAR(64) NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month_index INTEGER NOT NULL,
    cycle_month VARCHAR(32),
    due_date TIMESTAMPTZ NOT NULL,
    amount INTEGER NOT NULL DEFAULT 2000,
    amount_due INTEGER NOT NULL DEFAULT 2000,
    amount_paid INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'pending', -- 'pending', 'submitted', 'verified', 'rejected'
    utr_reference VARCHAR(64),
    payment_date TIMESTAMPTZ,
    proof_url TEXT,
    submitted_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    verified_by VARCHAR(64),
    rejected_at TIMESTAMPTZ,
    rejected_by VARCHAR(64),
    rejection_reason TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    CONSTRAINT uq_contrib_group_month_user UNIQUE(group_id, month_index, user_id)
);

-- Kitty Transactions (Disbursements & Audits)
CREATE TABLE IF NOT EXISTS kitty_transactions (
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    group_id VARCHAR(64) NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    type VARCHAR(32) NOT NULL, -- 'contribution_inflow', 'disbursement', 'reconciliation_adjustment'
    amount INTEGER NOT NULL,
    description TEXT NOT NULL,
    recipient_name VARCHAR(120),
    created_by VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    balance_after INTEGER NOT NULL,
    reference_id VARCHAR(64)
);

-- Expenses (Kitty Split)
CREATE TABLE IF NOT EXISTS expenses (
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    group_id VARCHAR(64) NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    amount INTEGER NOT NULL,
    paid_by_user_id VARCHAR(64) NOT NULL REFERENCES users(id),
    split_type VARCHAR(32) NOT NULL DEFAULT 'equal', -- 'equal', 'custom', 'percentage'
    category VARCHAR(64) NOT NULL DEFAULT 'Other',
    expense_date TIMESTAMPTZ NOT NULL,
    notes TEXT DEFAULT '',
    splits JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'active', -- 'active', 'reversed'
    is_reversal BOOLEAN NOT NULL DEFAULT FALSE,
    reversed_expense_id VARCHAR(64),
    reversal_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    created_by VARCHAR(64)
);

-- Settlements
CREATE TABLE IF NOT EXISTS settlements (
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    group_id VARCHAR(64) NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    from_user_id VARCHAR(64) NOT NULL REFERENCES users(id),
    to_user_id VARCHAR(64) NOT NULL REFERENCES users(id),
    amount INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending', -- 'pending', 'confirmed'
    reference_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    settled_at TIMESTAMPTZ,
    verified_by VARCHAR(64)
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    recipient_user_id VARCHAR(64) NOT NULL REFERENCES users(id),
    channel VARCHAR(32) NOT NULL DEFAULT 'sms',
    recipient_phone VARCHAR(32),
    recipient_email VARCHAR(255),
    template_id VARCHAR(64),
    message_text TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending', -- 'pending', 'sent', 'failed'
    gateway_response JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    sent_at TIMESTAMPTZ
);

-- Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    actor_user_id VARCHAR(64),
    actor_name VARCHAR(120),
    actor_email VARCHAR(255),
    action VARCHAR(64) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(64),
    before_state JSONB,
    after_state JSONB,
    notes TEXT,
    ip_address VARCHAR(64)
);

-- -----------------------------------------------------------------------------
-- 2. INDEXES
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_groups_code ON groups(group_code);
CREATE INDEX IF NOT EXISTS idx_memberships_group ON memberships(group_id);
CREATE INDEX IF NOT EXISTS idx_memberships_user ON memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_contrib_group_status ON contributions(group_id, status);
CREATE INDEX IF NOT EXISTS idx_contrib_utr ON contributions(utr_reference);
CREATE INDEX IF NOT EXISTS idx_kitty_tx_group_time ON kitty_transactions(group_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_expenses_group_date ON expenses(group_id, expense_date DESC);
CREATE INDEX IF NOT EXISTS idx_settlements_group ON settlements(group_id, status);
CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(recipient_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_time ON audit_logs(timestamp DESC);

-- -----------------------------------------------------------------------------
-- 3. ROW LEVEL SECURITY (RLS) ACTIVATION
-- -----------------------------------------------------------------------------
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE contributions ENABLE ROW LEVEL SECURITY;
ALTER TABLE kitty_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE settlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- 4. RLS POLICIES (Backend Access)
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "edith_all_users" ON users;
CREATE POLICY "edith_all_users" ON users FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "edith_all_groups" ON groups;
CREATE POLICY "edith_all_groups" ON groups FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "edith_all_memberships" ON memberships;
CREATE POLICY "edith_all_memberships" ON memberships FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "edith_all_contributions" ON contributions;
CREATE POLICY "edith_all_contributions" ON contributions FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "edith_all_kitty_tx" ON kitty_transactions;
CREATE POLICY "edith_all_kitty_tx" ON kitty_transactions FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "edith_all_expenses" ON expenses;
CREATE POLICY "edith_all_expenses" ON expenses FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "edith_all_settlements" ON settlements;
CREATE POLICY "edith_all_settlements" ON settlements FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "edith_all_notifications" ON notifications;
CREATE POLICY "edith_all_notifications" ON notifications FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "edith_all_audit_logs" ON audit_logs;
CREATE POLICY "edith_all_audit_logs" ON audit_logs FOR ALL USING (true) WITH CHECK (true);

-- -----------------------------------------------------------------------------
-- 5. OFFICIAL CREW PROVISIONING (Prajwal, Parichay, Srujan, Nitish)
-- -----------------------------------------------------------------------------
-- Password Hashes generated with Argon2id:
-- Prajwal  -> Prajwal784
-- Parichay -> Parichay392
-- Srujan   -> Srujan516
-- Nitish   -> Nitish628

INSERT INTO users (id, name, email, role, password_hash, is_active, created_at, must_change_password)
VALUES
    ('usr_prajwal_001', 'Prajwal', 'prajwal@edith.travel', 'admin', '$argon2id$v=19$m=65536,t=3,p=4$3BsjNkeIC0Jllm+irjZXFA$g0RNQvm64Qp1G10YZWzC3k9mlcZTeQETQdiqcpDc9Bk', TRUE, now(), FALSE),
    ('usr_parichay_002', 'Parichay', 'parichay@edith.travel', 'member', '$argon2id$v=19$m=65536,t=3,p=4$6is208yzrunFyjZrSX0KCA$kotOeUZhPs+qPOPy6GEjM2s7wg6bw5qKcRoJ8hgXRSY', TRUE, now(), FALSE),
    ('usr_srujan_003', 'Srujan', 'srujan@edith.travel', 'member', '$argon2id$v=19$m=65536,t=3,p=4$yQPbBh9HejWjFt9SNg0NCg$R/KKguSebvu10SlZy0fqbFfpNy38Wa+yngIdY0yWre0', TRUE, now(), FALSE),
    ('usr_nitish_004', 'Nitish', 'nitish@edith.travel', 'member', '$argon2id$v=19$m=65536,t=3,p=4$Dh8GYn3c0s29D4+MHZURFg$t8hKARr/NwQPQ6+/PwDmUJ3YkvzKdWxjDRUdfnHhVdM', TRUE, now(), FALSE)
ON CONFLICT (email) DO NOTHING;

-- Primary Trip Group
INSERT INTO groups (id, name, group_code, monthly_contribution, duration_months, custody_holder_name, currency, created_by, trip_destination, trip_start_date, trip_end_date, planned_trip_budget, trip_notes, trip_stops, trip_title, is_active, created_at)
VALUES (
    'grp_edith_001',
    'EDITH Annual Trip',
    'EDITH-TRIP-01',
    2000,
    12,
    'Prajwal',
    'INR',
    'usr_prajwal_001',
    'Manali & Spiti Valley',
    '2027-04-15',
    '2027-04-25',
    96000,
    'Official 4-member road trip through Himachal & Ladakh.',
    '[{"stop_number": 1, "destination_name": "Delhi", "arrival_date": "2027-04-15", "nights": 1, "transit_mode": "flight"}, {"stop_number": 2, "destination_name": "Manali", "arrival_date": "2027-04-16", "nights": 3, "transit_mode": "van"}, {"stop_number": 3, "destination_name": "Kaza / Spiti", "arrival_date": "2027-04-19", "nights": 4, "transit_mode": "suv"}, {"stop_number": 4, "destination_name": "Shimla", "arrival_date": "2027-04-23", "nights": 2, "transit_mode": "suv"}]'::jsonb,
    'EDITH Northern Expedition',
    TRUE,
    now()
)
ON CONFLICT (group_code) DO NOTHING;

-- Memberships
INSERT INTO memberships (group_id, user_id, role, joined_at, is_active)
VALUES
    ('grp_edith_001', 'usr_prajwal_001', 'admin', now(), TRUE),
    ('grp_edith_001', 'usr_parichay_002', 'member', now(), TRUE),
    ('grp_edith_001', 'usr_srujan_003', 'member', now(), TRUE),
    ('grp_edith_001', 'usr_nitish_004', 'member', now(), TRUE)
ON CONFLICT (group_id, user_id) DO NOTHING;

-- 12-Month Contribution Schedules for all 4 members
-- Month 1 to 12 at ₹2,000/month = ₹96,000 total pool
DO $$
DECLARE
    u_id text;
    m int;
    due timestamptz;
BEGIN
    FOR u_id IN SELECT id FROM users WHERE id IN ('usr_prajwal_001', 'usr_parichay_002', 'usr_srujan_003', 'usr_nitish_004') LOOP
        FOR m IN 1..12 LOOP
            due := (timezone('utc', now()) + (m || ' months')::interval);
            INSERT INTO contributions (group_id, user_id, month_index, due_date, amount, status, created_at)
            VALUES ('grp_edith_001', u_id, m, due, 2000, 'pending', now())
            ON CONFLICT (group_id, month_index, user_id) DO NOTHING;
        END LOOP;
    END LOOP;
END $$;
