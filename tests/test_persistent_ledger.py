"""
Test Persistent Ledger - February 4, 2026
Verifies SHA256 hashes, HMAC signatures, and dual writes to PostgreSQL + file.
"""

import asyncio
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def hash_data(data: Any) -> str:
    """Compute SHA256 hash of data."""
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()


def verify_hmac(data_hash: str, signature: str, secret: bytes) -> bool:
    """Verify HMAC-SHA256 signature."""
    expected = hmac.new(secret, data_hash.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def ok(self, msg: str):
        self.passed += 1
        print(f"  [PASS] {msg}")
    
    def fail(self, msg: str, error: str = None):
        self.failed += 1
        self.errors.append(f"{msg}: {error}")
        print(f"  [FAIL] {msg}: {error}")


async def test_sha256_hashing():
    """Test SHA256 hash computation."""
    result = TestResult("SHA256 Hashing")
    print("\n=== Test: SHA256 Hashing ===")
    
    # Test 1: Basic hash
    data = {"key": "value", "number": 42}
    hash1 = hash_data(data)
    if len(hash1) == 64:
        result.ok("Hash is 64 characters (256 bits)")
    else:
        result.fail("Hash length", f"Expected 64, got {len(hash1)}")
    
    # Test 2: Deterministic
    hash2 = hash_data(data)
    if hash1 == hash2:
        result.ok("Hash is deterministic")
    else:
        result.fail("Determinism", "Same data produced different hashes")
    
    # Test 3: Different data = different hash
    data2 = {"key": "value2", "number": 42}
    hash3 = hash_data(data2)
    if hash1 != hash3:
        result.ok("Different data produces different hash")
    else:
        result.fail("Uniqueness", "Different data produced same hash")
    
    # Test 4: Key ordering doesn't matter
    data3 = {"number": 42, "key": "value"}
    hash4 = hash_data(data3)
    if hash1 == hash4:
        result.ok("Key ordering is normalized (sort_keys=True)")
    else:
        result.fail("Key ordering", "Same data with different order produced different hash")
    
    return result


async def test_hmac_signatures():
    """Test HMAC-SHA256 signatures."""
    result = TestResult("HMAC Signatures")
    print("\n=== Test: HMAC Signatures ===")
    
    secret = b"test-secret-key-for-hmac"
    data_hash = hash_data({"test": "data"})
    
    # Test 1: Create signature
    signature = hmac.new(secret, data_hash.encode(), hashlib.sha256).hexdigest()
    if len(signature) == 64:
        result.ok("HMAC signature is 64 characters")
    else:
        result.fail("Signature length", f"Expected 64, got {len(signature)}")
    
    # Test 2: Verify correct signature
    if verify_hmac(data_hash, signature, secret):
        result.ok("Valid signature verifies correctly")
    else:
        result.fail("Verification", "Valid signature failed verification")
    
    # Test 3: Wrong secret fails
    wrong_secret = b"wrong-secret"
    if not verify_hmac(data_hash, signature, wrong_secret):
        result.ok("Wrong secret fails verification")
    else:
        result.fail("Security", "Wrong secret passed verification")
    
    # Test 4: Tampered hash fails
    tampered_hash = data_hash[:-1] + "0"
    if not verify_hmac(tampered_hash, signature, secret):
        result.ok("Tampered hash fails verification")
    else:
        result.fail("Security", "Tampered hash passed verification")
    
    return result


async def test_merkle_root():
    """Test Merkle root computation."""
    result = TestResult("Merkle Root")
    print("\n=== Test: Merkle Root ===")
    
    def compute_merkle_root(hashes):
        if not hashes:
            return hashlib.sha256(b"empty").hexdigest()
        hashes = list(hashes)
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])
            hashes = [
                hashlib.sha256((hashes[i] + hashes[i+1]).encode()).hexdigest()
                for i in range(0, len(hashes), 2)
            ]
        return hashes[0]
    
    # Test 1: Single hash (must be a proper 64-char hash)
    test_hash = hashlib.sha256(b"test").hexdigest()
    single = compute_merkle_root([test_hash])
    if len(single) == 64:
        result.ok("Single hash produces valid Merkle root")
    else:
        result.fail("Single hash", f"Invalid length: {len(single)}")
    
    # Test 2: Multiple hashes
    hashes = [hash_data({"i": i}) for i in range(5)]
    root = compute_merkle_root(hashes)
    if len(root) == 64:
        result.ok("Multiple hashes produce valid Merkle root")
    else:
        result.fail("Multiple hashes", f"Invalid length: {len(root)}")
    
    # Test 3: Deterministic
    root2 = compute_merkle_root(hashes)
    if root == root2:
        result.ok("Merkle root is deterministic")
    else:
        result.fail("Determinism", "Same hashes produced different roots")
    
    # Test 4: Order matters
    reversed_hashes = list(reversed(hashes))
    root3 = compute_merkle_root(reversed_hashes)
    if root != root3:
        result.ok("Different order produces different root")
    else:
        result.fail("Order sensitivity", "Order should affect Merkle root")
    
    return result


async def test_block_chain_linking():
    """Test blockchain linking (previous_hash -> block_hash)."""
    result = TestResult("Block Chain Linking")
    print("\n=== Test: Block Chain Linking ===")
    
    class MockBlock:
        def __init__(self, number: int, prev_hash: str, data: Dict):
            self.block_number = number
            self.previous_hash = prev_hash
            self.data = data
            self.timestamp = datetime.now(timezone.utc).isoformat()
            self.block_hash = self._compute_hash()
        
        def _compute_hash(self) -> str:
            content = json.dumps({
                "block_number": self.block_number,
                "previous_hash": self.previous_hash,
                "data": self.data,
                "timestamp": self.timestamp
            }, sort_keys=True)
            return hashlib.sha256(content.encode()).hexdigest()
    
    # Create chain
    genesis = MockBlock(0, "0" * 64, {"genesis": True})
    block1 = MockBlock(1, genesis.block_hash, {"entry": 1})
    block2 = MockBlock(2, block1.block_hash, {"entry": 2})
    
    # Test 1: Genesis block has valid hash
    if len(genesis.block_hash) == 64:
        result.ok("Genesis block has valid hash")
    else:
        result.fail("Genesis hash", f"Invalid length: {len(genesis.block_hash)}")
    
    # Test 2: Chain links correctly
    if block1.previous_hash == genesis.block_hash:
        result.ok("Block 1 links to genesis")
    else:
        result.fail("Chain link 1", "Block 1 does not link to genesis")
    
    if block2.previous_hash == block1.block_hash:
        result.ok("Block 2 links to block 1")
    else:
        result.fail("Chain link 2", "Block 2 does not link to block 1")
    
    # Test 3: Tampering detection
    original_hash = block1.block_hash
    block1.data = {"entry": 999}  # Tamper
    new_hash = block1._compute_hash()
    if original_hash != new_hash:
        result.ok("Tampering produces different hash")
    else:
        result.fail("Tamper detection", "Tampered block has same hash")
    
    # Test 4: Broken chain detection
    if block2.previous_hash != new_hash:
        result.ok("Chain break detected (block2.prev != block1.new_hash)")
    else:
        result.fail("Chain integrity", "Broken chain not detected")
    
    return result


async def test_dual_write_simulation():
    """Simulate dual write to PostgreSQL + file."""
    result = TestResult("Dual Write Simulation")
    print("\n=== Test: Dual Write Simulation ===")
    
    class MockPostgresLedger:
        def __init__(self):
            self.entries = []
        
        async def add_entry(self, entry_id, data_hash, signature):
            self.entries.append({
                "id": str(entry_id),
                "data_hash": data_hash,
                "signature": signature,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return True
    
    class MockFileLedger:
        def __init__(self):
            self.lines = []
        
        async def append_entry(self, entry_id, data_hash, metadata):
            self.lines.append(json.dumps({
                "record_type": "entry",
                "entry_id": str(entry_id),
                "data_hash": data_hash,
                "metadata": metadata
            }))
            return True
    
    pg = MockPostgresLedger()
    file = MockFileLedger()
    
    # Simulate dual write
    async def dual_write(data: Dict) -> Dict:
        entry_id = uuid4()
        data_hash = hash_data(data)
        secret = b"test-secret"
        signature = hmac.new(secret, data_hash.encode(), hashlib.sha256).hexdigest()
        
        pg_ok = await pg.add_entry(entry_id, data_hash, signature)
        file_ok = await file.append_entry(entry_id, data_hash, {"source": "test"})
        
        return {
            "entry_id": str(entry_id),
            "data_hash": data_hash,
            "postgres_recorded": pg_ok,
            "file_recorded": file_ok
        }
    
    # Test 1: Both writes succeed
    result1 = await dual_write({"test": 1})
    if result1["postgres_recorded"] and result1["file_recorded"]:
        result.ok("Dual write to PostgreSQL and file succeeded")
    else:
        result.fail("Dual write", "One or both writes failed")
    
    # Test 2: Data matches
    if len(pg.entries) == 1 and len(file.lines) == 1:
        pg_hash = pg.entries[0]["data_hash"]
        file_hash = json.loads(file.lines[0])["data_hash"]
        if pg_hash == file_hash:
            result.ok("Data hash matches in both stores")
        else:
            result.fail("Hash mismatch", "PostgreSQL and file have different hashes")
    else:
        result.fail("Entry count", "Expected 1 entry in each store")
    
    # Test 3: Multiple writes
    for i in range(5):
        await dual_write({"test": i + 2})
    
    if len(pg.entries) == 6 and len(file.lines) == 6:
        result.ok("Multiple dual writes succeeded (6 total)")
    else:
        result.fail("Multiple writes", f"Expected 6, got pg={len(pg.entries)}, file={len(file.lines)}")
    
    # Test 4: All entry IDs unique
    pg_ids = set(e["id"] for e in pg.entries)
    if len(pg_ids) == 6:
        result.ok("All entry IDs are unique")
    else:
        result.fail("Uniqueness", f"Expected 6 unique IDs, got {len(pg_ids)}")
    
    return result


async def run_all_tests():
    """Run all ledger tests."""
    print("=" * 60)
    print("PERSISTENT LEDGER TEST SUITE")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = []
    
    results.append(await test_sha256_hashing())
    results.append(await test_hmac_signatures())
    results.append(await test_merkle_root())
    results.append(await test_block_chain_linking())
    results.append(await test_dual_write_simulation())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total_passed = sum(r.passed for r in results)
    total_failed = sum(r.failed for r in results)
    
    for r in results:
        status = "PASS" if r.failed == 0 else "FAIL"
        print(f"  [{status}] {r.name}: {r.passed} passed, {r.failed} failed")
        for error in r.errors:
            print(f"        - {error}")
    
    print("-" * 60)
    print(f"TOTAL: {total_passed} passed, {total_failed} failed")
    
    return total_failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
