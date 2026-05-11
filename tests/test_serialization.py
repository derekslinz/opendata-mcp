from datetime import datetime, timezone
import json

from opendata_mcp.utils import to_json_text


def test_to_json_text_serializes_datetime():
    payload = {"updated_at": datetime(2024, 1, 1, tzinfo=timezone.utc)}
    text = to_json_text(payload)
    assert '"updated_at":"2024-01-01 00:00:00+00:00"' in text


def test_to_json_text_applies_max_chars():
    max_chars = 20
    text = to_json_text({"value": "a" * 100}, max_chars=max_chars)
    assert len(text) <= max_chars
    payload = json.loads(text)
    assert payload["truncated"] is True


def test_to_json_text_sorts_keys():
    text = to_json_text({"b": 2, "a": 1})
    assert text == '{"a":1,"b":2}'


def test_to_json_text_truncation_remains_valid_json():
    source_payload = {"value": "a" * 100}
    max_chars = next(
        size
        for size in range(1, 200)
        if '"preview"' in to_json_text(source_payload, max_chars=size)
    )
    text = to_json_text(source_payload, max_chars=max_chars)
    payload = json.loads(text)
    assert payload["truncated"] is True
    assert payload["preview"].startswith("{")
