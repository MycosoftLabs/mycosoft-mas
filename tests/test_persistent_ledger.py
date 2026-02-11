"""
Persistent Ledger Tests (pytest)

This file previously contained an async CLI-style test runner. Converted to
normal pytest assertions so the suite runs under CI/pytest.
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List
from uuid import uuid4

import pytest


def hash_data(data: Any) -> str:
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()


def verify_hmac(data_hash: str, signature: str, secret: bytes) -> bool:
    expected = hmac.new(secret, data_hash.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def compute_merkle_root(hashes: Iterable[str]) -> str:
    hashes_list: List[str] = list(hashes)
    if not hashes_list:
        return hashlib.sha256(b"empty").hexdigest()
    while len(hashes_list) > 1:
        if len(hashes_list) % 2 == 1:
            hashes_list.append(hashes_list[-1])
        hashes_list = [
            hashlib.sha256((hashes_list[i] + hashes_list[i + 1]).encode()).hexdigest()
            for i in range(0, len(hashes_list), 2)
        ]
    return hashes_list[0]


def test_sha256_hashing() -> None:
    data = {"key": "value", "number": 42}
    h1 = hash_data(data)
    assert len(h1) == 64
    assert h1 == hash_data(data)  # deterministic
    assert h1 != hash_data({"key": "value2", "number": 42})
    assert h1 == hash_data({"number": 42, "key": "value"})  # ordering normalized


def test_hmac_signatures() -> None:
    secret = b"test-secret-key-for-hmac"
    data_hash = hash_data({"test": "data"})
    signature = hmac.new(secret, data_hash.encode(), hashlib.sha256).hexdigest()
    assert len(signature) == 64
    assert verify_hmac(data_hash, signature, secret) is True
    assert verify_hmac(data_hash, signature, b"wrong-secret") is False
    tampered_hash = data_hash[:-1] + "0"
    assert verify_hmac(tampered_hash, signature, secret) is False


def test_merkle_root() -> None:
    test_hash = hashlib.sha256(b"test").hexdigest()
    assert len(compute_merkle_root([test_hash])) == 64

    hashes = [hash_data({"i": i}) for i in range(5)]
    root = compute_merkle_root(hashes)
    assert len(root) == 64
    assert root == compute_merkle_root(hashes)  # deterministic
    assert root != compute_merkle_root(list(reversed(hashes)))  # order matters


def test_block_chain_linking() -> None:
    class MockBlock:
        def __init__(self, number: int, prev_hash: str, data: Dict[str, Any]):
            self.block_number = number
            self.previous_hash = prev_hash
            self.data = data
            self.timestamp = datetime.now(timezone.utc).isoformat()
            self.block_hash = self._compute_hash()

        def _compute_hash(self) -> str:
            content = json.dumps(
                {
                    "block_number": self.block_number,
                    "previous_hash": self.previous_hash,
                    "data": self.data,
                    "timestamp": self.timestamp,
                },
                sort_keys=True,
            )
            return hashlib.sha256(content.encode()).hexdigest()

    genesis = MockBlock(0, "0" * 64, {"genesis": True})
    block1 = MockBlock(1, genesis.block_hash, {"entry": 1})
    block2 = MockBlock(2, block1.block_hash, {"entry": 2})

    assert len(genesis.block_hash) == 64
    assert block1.previous_hash == genesis.block_hash
    assert block2.previous_hash == block1.block_hash

    original_hash = block1.block_hash
    block1.data = {"entry": 999}
    new_hash = block1._compute_hash()
    assert original_hash != new_hash
    assert block2.previous_hash != new_hash  # chain break


@pytest.mark.asyncio
async def test_dual_write_simulation() -> None:
    class MockPostgresLedger:
        def __init__(self):
            self.entries: List[Dict[str, Any]] = []

        async def add_entry(self, entry_id, data_hash, signature):
            self.entries.append(
                {
                    "id": str(entry_id),
                    "data_hash": data_hash,
                    "signature": signature,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            return True

    class MockFileLedger:
        def __init__(self):
            self.lines: List[str] = []

        async def append_entry(self, entry_id, data_hash, metadata):
            self.lines.append(
                json.dumps(
                    {
                        "record_type": "entry",
                        "entry_id": str(entry_id),
                        "data_hash": data_hash,
                        "metadata": metadata,
                    }
                )
            )
            return True

    pg = MockPostgresLedger()
    file = MockFileLedger()

    async def dual_write(data: Dict[str, Any]) -> Dict[str, Any]:
        entry_id = uuid4()
        data_hash = hash_data(data)
        secret = b"test-secret"
        signature = hmac.new(secret, data_hash.encode(), hashlib.sha256).hexdigest()
        pg_ok = await pg.add_entry(entry_id, data_hash, signature)
        file_ok = await file.append_entry(entry_id, data_hash, {"source": "test"})
        return {"entry_id": str(entry_id), "data_hash": data_hash, "postgres_recorded": pg_ok, "file_recorded": file_ok}

    result1 = await dual_write({"test": 1})
    assert result1["postgres_recorded"] is True
    assert result1["file_recorded"] is True

    assert len(pg.entries) == 1
    assert len(file.lines) == 1
    assert pg.entries[0]["data_hash"] == json.loads(file.lines[0])["data_hash"]

    for i in range(5):
        await dual_write({"test": i + 2})

    assert len(pg.entries) == 6
    assert len(file.lines) == 6
    assert len({e["id"] for e in pg.entries}) == 6
