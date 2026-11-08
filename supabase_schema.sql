-- =============================================================================
-- EDITH TRIP MANAGER - SUPABASE POSTGRESQL SCHEMA
-- Multi-destination trip planner, savings kitty, and shared expense manager.
-- Run this in your Supabase SQL Editor (Dashboard -> SQL Editor -> New Query -> Run)
-- =============================================================================

-- Enable pgcrypto / uuid extension for cryptographic UUIDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. USERS TABLE
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

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- 2. GROUPS TABLE
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
    trip_destination VARCHAR(255) DEFAULT 'To be decided',
    trip_start_date DATE,
    trip_end_date DATE,
    planned_trip_budget INTEGER DEFAULT 0,
    trip_notes TEXT DEFAULT '',
    trip_stops JSONB DEFAULT '[]'::jsonb,
    trip_title VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_groups_code ON groups(group_code);

-- 3. MEMBERSHIPS TABLE
CREATE TABLE IF NOT EXISTS memberships (
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    group_id VARCHAR(64) NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_group_user UNIQUE(group_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_memberships_group ON memberships(group_id);
CREATE INDEX IF NOT EXISTS idx_memberships_user ON memberships(user_id);

-- 4. CONTRIBUTIONS TABLE (Savings Kitty)
CREATE TABLE IF NOT EXISTS contributions (
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    group_id VARCHAR(64) NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month_index INTEGER NOT NULL,
    due_date TIMESTAMPTZ NOT NULL,
    amount INTEGER NOT NULL DEFAULT 2000,
    status VARCHAR(32) NOT NULL DEFAULT 'pending', -- 'pending', 'submitted', 'verified', 'rejected'
    utr_reference VARCHAR(64),
    payment_date TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    verified_by VARCHAR(64),
    rejected_at TIMESTAMPTZ,
    rejected_by VARCHAR(64),
    rejection_reason TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    CONSTRAINT uq_contrib_group_month_user UNIQUE(group_id, month_index, user_id)
);

CREATE INDEX IF NOT EXISTS idx_contrib_group_status ON contributions(group_id, status);
CREATE INDEX IF NOT EXISTS idx_contrib_utr ON contributions(utr_reference);

-- 5. KITTY TRANSACTIONS TABLE (Disbursements & Audits)
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

CREATE INDEX IF NOT EXISTS idx_kitty_tx_group_time ON kitty_transactions(group_id, created_at DESC);

-- 6. EXPENSES TABLE (Shared Trip Expenses)
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

CREATE INDEX IF NOT EXISTS idx_expenses_group_date ON expenses(group_id, expense_date DESC);

-- 7. SETTLEMENTS TABLE
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

CREATE INDEX IF NOT EXISTS idx_settlements_group ON settlements(group_id, status);

-- 8. NOTIFICATIONS TABLE
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

CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(recipient_user_id, created_at DESC);

-- 9. AUDIT LOGS TABLE
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

CREATE INDEX IF NOT EXISTS idx_audit_logs_time ON audit_logs(timestamp DESC);

