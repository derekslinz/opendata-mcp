from datetime import datetime, timezone

from opendata_mcp.utils import to_json_text


def test_to_json_text_serializes_datetime():
    payload = {"updated_at": datetime(2024, 1, 1, tzinfo=timezone.utc)}
    text = to_json_text(payload)
    assert '"updated_at": "2024-01-01 00:00:00+00:00"' in text


def test_to_json_text_applies_max_chars():
    text = to_json_text({"value": "abcdef"}, max_chars=8)
    assert text == '{"value"'
