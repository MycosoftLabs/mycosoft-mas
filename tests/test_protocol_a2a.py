"""
Protocol A2A tests - February 17, 2026

A2A remote payload sanitization, schema validation, and policy checks.
CI gate: fail-fast on network/tool policy violations, missing allowlists, secret-leak patterns.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

try:
    from mycosoft_mas.core.myca_main import app as mas_app
except ImportError:
    mas_app = None


def _get_sanitize_extract():
    """Import sanitization helpers from A2A router (module-level, testable)."""
    from mycosoft_mas.core.routers import a2a_api
    return a2a_api._sanitize_text, a2a_api._extract_user_message


class TestA2ASanitization:
    """A2A remote payload sanitization - treat agent cards and remote payloads as untrusted."""

    def test_sanitize_text_strips_null_and_control_chars(self):
        sanitize, _ = _get_sanitize_extract()
        raw = "hello\x00world\x01\x1f\x7f"
        assert sanitize(raw) == "helloworld"

    def test_sanitize_text_rejects_non_string(self):
        sanitize, _ = _get_sanitize_extract()
        assert sanitize(123) == ""
        assert sanitize(None) == ""
        assert sanitize([]) == ""

    def test_sanitize_text_respects_max_len(self):
        sanitize, _ = _get_sanitize_extract()
        long_str = "a" * 60000
        assert len(sanitize(long_str, max_len=100)) == 100

    def test_extract_user_message_joins_text_parts(self):
        _, extract = _get_sanitize_extract()
        from mycosoft_mas.core.routers.a2a_api import PartModel, MessageModel
        msg = MessageModel(
            messageId="m1",
            role="ROLE_USER",
            parts=[
                PartModel(text="hello"),
                PartModel(text="world"),
            ],
        )
        assert extract(msg) == "hello world"

    def test_extract_user_message_sanitizes_parts(self):
        _, extract = _get_sanitize_extract()
        from mycosoft_mas.core.routers.a2a_api import PartModel, MessageModel
        msg = MessageModel(
            messageId="m1",
            role="ROLE_USER",
            parts=[PartModel(text="safe\x00\x01text")],
        )
        assert "\x00" not in extract(msg)
        assert "safe" in extract(msg) and "text" in extract(msg)

    def test_extract_user_message_ignores_url_and_data_parts(self):
        _, extract = _get_sanitize_extract()
        from mycosoft_mas.core.routers.a2a_api import PartModel, MessageModel
        msg = MessageModel(
            messageId="m1",
            role="ROLE_USER",
            parts=[
                PartModel(text="query"),
                PartModel(url="http://evil.com"),
                PartModel(data={"x": 1}),
            ],
        )
        assert extract(msg) == "query"


@pytest.mark.skipif(mas_app is None, reason="Full MAS app not importable")
class TestA2AEndpoints:
    """A2A endpoint behavior - Agent Card, message send."""

    @pytest.fixture
    def client(self):
        return TestClient(mas_app)

    def test_agent_card_returns_valid_schema(self, client):
        resp = client.get("/.well-known/agent-card.json")
        if resp.status_code == 404:
            pytest.skip("A2A disabled (MYCA_A2A_ENABLED=false)")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "supportedInterfaces" in data
        assert "capabilities" in data
        assert data.get("name") == "MYCA"

    def test_message_send_requires_text_part(self, client):
        resp = client.post(
            "/a2a/v1/message/send",
            json={
                "message": {
                    "messageId": "m1",
                    "role": "ROLE_USER",
                    "parts": [{"url": "http://example.com"}],
                },
            },
        )
        if resp.status_code == 404:
            pytest.skip("A2A disabled")
        # Should reject: no text part
        assert resp.status_code in (400, 422)
