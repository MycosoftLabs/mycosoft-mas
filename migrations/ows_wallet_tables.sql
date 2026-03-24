-- OWS (Open Wallet Standard) Wallet Integration Tables
-- Target: MINDEX PostgreSQL (192.168.0.189:5432)
-- Created: March 24, 2026
--
-- Three tables:
--   ows_wallets      — Agent wallet registry (1:1 agent → wallet)
--   ows_transactions — Append-only transaction ledger
--   ows_balances     — Internal off-chain ledger balances for instant A2A transfers

BEGIN;

-- ---------------------------------------------------------------------------
-- Agent wallet registry
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ows_wallets (
    wallet_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        VARCHAR(64)  NOT NULL UNIQUE,
    wallet_name     VARCHAR(128) NOT NULL UNIQUE,
    wallet_type     VARCHAR(20)  NOT NULL DEFAULT 'internal',  -- internal | external | treasury
    passphrase_hash VARCHAR(256) NOT NULL,
    chains          JSONB        DEFAULT '{}',   -- {"solana:mainnet": "addr...", "eip155:1": "addr..."}
    status          VARCHAR(20)  DEFAULT 'active',  -- active | suspended | closed
    created_at      TIMESTAMP    DEFAULT NOW(),
    updated_at      TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ows_wallets_agent_id ON ows_wallets (agent_id);
CREATE INDEX IF NOT EXISTS idx_ows_wallets_wallet_type ON ows_wallets (wallet_type);
CREATE INDEX IF NOT EXISTS idx_ows_wallets_status ON ows_wallets (status);

-- ---------------------------------------------------------------------------
-- Transaction ledger (append-only)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ows_transactions (
    tx_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_wallet_id  UUID REFERENCES ows_wallets(wallet_id),
    to_wallet_id    UUID REFERENCES ows_wallets(wallet_id),
    from_agent_id   VARCHAR(64),
    to_agent_id     VARCHAR(64),
    amount          DECIMAL(20, 8) NOT NULL,
    currency        VARCHAR(10) NOT NULL,       -- SOL, USDC, ETH, BTC, etc.
    chain           VARCHAR(64) NOT NULL,       -- solana:mainnet, eip155:1, etc.
    tx_type         VARCHAR(30) NOT NULL,       -- api_payment, fund, withdraw, internal_transfer, service_fee
    tx_hash         VARCHAR(128),               -- On-chain tx hash (null for internal ledger transfers)
    status          VARCHAR(20) DEFAULT 'pending',  -- pending | confirmed | failed
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ows_tx_from_agent ON ows_transactions (from_agent_id);
CREATE INDEX IF NOT EXISTS idx_ows_tx_to_agent ON ows_transactions (to_agent_id);
CREATE INDEX IF NOT EXISTS idx_ows_tx_status ON ows_transactions (status);
CREATE INDEX IF NOT EXISTS idx_ows_tx_type ON ows_transactions (tx_type);
CREATE INDEX IF NOT EXISTS idx_ows_tx_created ON ows_transactions (created_at DESC);

-- ---------------------------------------------------------------------------
-- Internal ledger balances (off-chain tracking for instant internal transfers)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ows_balances (
    agent_id        VARCHAR(64) PRIMARY KEY REFERENCES ows_wallets(agent_id),
    sol_balance     DECIMAL(20, 8) DEFAULT 0,
    usdc_balance    DECIMAL(20, 8) DEFAULT 0,
    eth_balance     DECIMAL(20, 8) DEFAULT 0,
    btc_balance     DECIMAL(20, 8) DEFAULT 0,
    last_reconciled TIMESTAMP DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Treasury configuration (owner-controlled withdrawal addresses & settings)
-- CEO can change these at any time via the API.
-- Funds accumulate in the internal ledger; auto-sweep or manual withdraw
-- sends to these addresses.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ows_treasury_config (
    config_key   VARCHAR(64) PRIMARY KEY,
    config_value TEXT NOT NULL,
    updated_at   TIMESTAMP DEFAULT NOW(),
    updated_by   VARCHAR(64) DEFAULT 'system'
);

-- Seed default config rows (addresses start empty — CEO must set them)
-- confirmed addresses: what sweeps actually use (safe)
-- pending addresses: staged changes awaiting cooldown confirmation
INSERT INTO ows_treasury_config (config_key, config_value) VALUES
    ('withdrawal_address_solana',   ''),
    ('withdrawal_address_ethereum', ''),
    ('withdrawal_address_bitcoin',  ''),
    ('pending_address_solana',      ''),
    ('pending_address_ethereum',    ''),
    ('pending_address_bitcoin',     ''),
    ('pending_address_expires_at',  ''),
    ('address_change_cooldown_hours', '24'),
    ('sweep_locked',                'false'),
    ('treasury_fee_percent',        '5.0'),
    ('auto_sweep_enabled',          'false'),
    ('auto_sweep_threshold_sol',    '10.0'),
    ('auto_sweep_threshold_eth',    '0.5'),
    ('auto_sweep_threshold_btc',    '0.01')
ON CONFLICT (config_key) DO NOTHING;

-- Audit log for all treasury access attempts
CREATE TABLE IF NOT EXISTS ows_treasury_audit (
    audit_id    SERIAL PRIMARY KEY,
    action      VARCHAR(64) NOT NULL,
    success     BOOLEAN NOT NULL,
    ip_address  VARCHAR(45),
    details     JSONB DEFAULT '{}',
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_treasury_audit_created ON ows_treasury_audit (created_at DESC);

COMMIT;
