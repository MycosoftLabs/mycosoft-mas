# Cryptographic Integrity System
## Created: February 4, 2026

## Overview

The Cryptographic Integrity System ensures all memory operations are cryptographically verified and permanently recorded in a blockchain-like ledger.

## Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                  Cryptographic Integrity Engine                  â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                  â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚                    Integrity Service                     â”‚   â”‚
â”‚  â”‚  - SHA256 Hashing                                        â”‚   â”‚
â”‚  â”‚  - HMAC-SHA256 Signatures                               â”‚   â”‚
â”‚  â”‚  - Automatic Recording                                   â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                              â”‚                                   â”‚
â”‚              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                  â”‚
â”‚              â”‚               â”‚               â”‚                  â”‚
â”‚       â”Œâ”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â” â”Œâ”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”          â”‚
â”‚       â”‚ PostgreSQL  â”‚ â”‚  JSONL File â”‚ â”‚  Merkle    â”‚          â”‚
â”‚       â”‚   Ledger    â”‚ â”‚   Backup    â”‚ â”‚   Trees    â”‚          â”‚
â”‚       â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜          â”‚
â”‚                                                                  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Components

### 1. Integrity Service (`integrity_service.py`)

The core service that wraps all cryptographic operations:

```python
from mycosoft_mas.security.integrity_service import hash_and_record

# Hash and record data with cryptographic proof
result = await hash_and_record(
    entry_type="memory_write",
    data={"key": "value"},
    metadata={"scope": "user"},
    with_signature=True
)

# Returns:
# {
#     "entry_id": "uuid",
#     "data_hash": "sha256_hash",
#     "signature": "hmac_signature",
#     "postgres_recorded": True,
#     "file_recorded": True,
#     "timestamp": "2026-02-04T12:00:00Z"
# }
```

### 2. Persistent Chain (`persistent_chain.py`)

PostgreSQL-backed blockchain ledger:

```python
from mycosoft_mas.ledger.persistent_chain import get_ledger

ledger = get_ledger()
await ledger.initialize()

# Add entry to pending
await ledger.add_entry(
    entry_type="memory_write",
    data={"key": "value"},
    signature="hmac_signature"
)

# Commit block (batches pending entries)
block = await ledger.commit_block()
print(f"Block {block.block_number}: {block.block_hash}")
```

### 3. File Ledger (`file_ledger.py`)

Append-only JSONL file backup:

```python
from mycosoft_mas.ledger.file_ledger import get_file_ledger

file_ledger = get_file_ledger()

# Append entry
await file_ledger.append_entry(
    entry_type="memory_write",
    entry_id=uuid4(),
    data_hash="sha256_hash",
    metadata={"scope": "user"}
)

# Verify file integrity
result = await file_ledger.verify_file_integrity()
# {"valid": True, "block_count": 100, "entry_count": 5000}
```

## Data Flow

1. **Memory Write Request** arrives at `/api/memory/write`
2. **Data is stored** in Redis/PostgreSQL
3. **Integrity Service** is called:
   - Computes SHA256 hash of data
   - Generates HMAC-SHA256 signature
   - Writes to PostgreSQL ledger (pending)
   - Appends to JSONL file
4. **Block Commit** (every 100 entries or 5 minutes):
   - Computes Merkle root of pending entries
   - Creates new block with previous hash
   - Inserts block and entries into PostgreSQL

## Database Schema

```sql
-- Blocks table
CREATE TABLE ledger.blocks (
    block_number BIGSERIAL PRIMARY KEY,
    previous_hash VARCHAR(64) NOT NULL,
    block_hash VARCHAR(64) UNIQUE NOT NULL,
    merkle_root VARCHAR(64) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    data_count INTEGER DEFAULT 0
);

-- Entries table
CREATE TABLE ledger.entries (
    id UUID PRIMARY KEY,
    block_number BIGINT REFERENCES ledger.blocks(block_number),
    entry_type VARCHAR(100) NOT NULL,
    data_hash VARCHAR(64) NOT NULL,
    metadata JSONB DEFAULT '{}',
    signature VARCHAR(256),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## JSONL File Format

Each line is a JSON object:

```json
{"record_type":"entry","entry_id":"uuid","entry_type":"memory_write","data_hash":"sha256","metadata":{},"timestamp":"ISO8601"}
{"record_type":"block","block_number":1,"previous_hash":"...","block_hash":"...","merkle_root":"...","timestamp":"ISO8601"}
```

## Verification

### Chain Verification

```python
# Verify PostgreSQL chain
ledger = get_ledger()
is_valid = await ledger.verify_chain()
# Checks that each block's previous_hash matches prior block's block_hash

# Verify file chain
file_ledger = get_file_ledger()
result = await file_ledger.verify_file_integrity()
# Checks block continuity in JSONL file
```

### Entry Verification

```python
from mycosoft_mas.security.integrity_service import get_integrity_service

service = get_integrity_service()
result = await service.verify_entry(entry_id, original_data)
# {
#     "verified": True,
#     "hash_valid": True,
#     "signature_valid": True,
#     "block_number": 42
# }
```

### Full Chain Verification

```python
result = await service.verify_chain()
# {
#     "postgres_chain": {"valid": True},
#     "file_chain": {"valid": True, "block_count": 100},
#     "overall_valid": True
# }
```

## Hashing Details

### SHA256 Hash

```python
import hashlib
import json

def hash_data(data: Any) -> str:
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()
```

### HMAC-SHA256 Signature

```python
import hmac

def create_signature(data_hash: str, secret: bytes) -> str:
    return hmac.new(
        secret,
        data_hash.encode(),
        hashlib.sha256
    ).hexdigest()
```

### Merkle Root

```python
def compute_merkle_root(hashes: List[str]) -> str:
    if not hashes:
        return hashlib.sha256(b"empty").hexdigest()
    
    while len(hashes) > 1:
        if len(hashes) % 2 == 1:
            hashes.append(hashes[-1])
        hashes = [
            hashlib.sha256((hashes[i] + hashes[i+1]).encode()).hexdigest()
            for i in range(0, len(hashes), 2)
        ]
    
    return hashes[0]
```

## Security Considerations

1. **HMAC Secret**: Stored in environment variable `INTEGRITY_HMAC_SECRET`
2. **File Permissions**: JSONL file has restricted write access
3. **Block Finality**: Once committed, blocks cannot be modified
4. **Dual Write**: Both PostgreSQL and file must succeed
5. **NAS Backup**: JSONL file stored on NAS mount for redundancy

## Deployment

The cryptographic ledger runs on the dedicated MINDEX VM:

- **VM**: 192.168.0.189 (MINDEX-VM)
- **Storage**: 200GB data disk + NAS mount
- **Snapshots**: Daily Proxmox snapshots at 2:00 AM
- **Backup**: JSONL file synced to NAS

## Related Documentation

- [System Registry](./SYSTEM_REGISTRY_FEB04_2026.md)
- [Memory Integration Guide](./MEMORY_INTEGRATION_GUIDE_FEB04_2026.md)
- [MINDEX VM Spec](../infra/mindex-vm/MINDEX_VM_SPEC_FEB04_2026.md)
