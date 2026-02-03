-- Migration 010: Blockchain Provenance Ledger
-- Created: February 3, 2026

CREATE SCHEMA IF NOT EXISTS ledger;

CREATE TABLE IF NOT EXISTS ledger.blocks (
    block_number BIGSERIAL PRIMARY KEY,
    previous_hash VARCHAR(64),
    block_hash VARCHAR(64) UNIQUE,
    merkle_root VARCHAR(64),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    data_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ledger.entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    block_number BIGINT REFERENCES ledger.blocks(block_number),
    entry_type VARCHAR(50),
    data_hash VARCHAR(64),
    metadata JSONB,
    signature VARCHAR(256),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ledger.ip_nfts (
    nft_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id UUID REFERENCES ledger.entries(id),
    title VARCHAR(255),
    creators JSONB,
    claim_type VARCHAR(50),
    status VARCHAR(20) DEFAULT ''pending'',
    minted_at TIMESTAMPTZ
);

CREATE INDEX idx_entries_block ON ledger.entries(block_number);
CREATE INDEX idx_entries_type ON ledger.entries(entry_type);
