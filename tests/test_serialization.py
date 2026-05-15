from datetime import datetime, timezone
import json

import pytest

from meta_data_mcp.utils import MAX_RESPONSE_CHARS, to_geofeatures_text, to_json_text


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
    low, high = 1, 200
    while low < high:
        mid = (low + high) // 2
        if '"preview"' in to_json_text(source_payload, max_chars=mid):
            high = mid
        else:
            low = mid + 1
    max_chars = low
    text = to_json_text(source_payload, max_chars=max_chars)
    payload = json.loads(text)
    assert payload["truncated"] is True
    assert payload["preview"].startswith("{")


def test_to_json_text_rejects_too_small_max_chars():
    with pytest.raises(ValueError, match="max_chars must be >= 2"):
        to_json_text({"value": "abcdef"}, max_chars=1)


def test_to_geofeatures_text_trims_feature_list_to_valid_json():
    payload = {
        "features": [
            {
                "lat": 1.0,
                "lon": 2.0,
                "attrs": {"name": f"feature-{i}", "blob": "x" * 150},
            }
            for i in range(200)
        ]
    }

    text = to_geofeatures_text(payload, max_chars=MAX_RESPONSE_CHARS)

    assert len(text) <= MAX_RESPONSE_CHARS
    bounded = json.loads(text)
    assert isinstance(bounded["features"], list)
    assert 0 < len(bounded["features"]) < len(payload["features"])


def test_to_geofeatures_text_trims_geojson_feature_collection_to_valid_json():
    payload = {
        "features": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": f"feature-{i}",
                    "geometry": {"type": "Point", "coordinates": [i, i]},
                    "properties": {"blob": "y" * 400},
                }
                for i in range(200)
            ],
        }
    }

    text = to_geofeatures_text(payload, max_chars=MAX_RESPONSE_CHARS)

    assert len(text) <= MAX_RESPONSE_CHARS
    bounded = json.loads(text)
    assert bounded["features"]["type"] == "FeatureCollection"
    assert (
        0 < len(bounded["features"]["features"]) < len(payload["features"]["features"])
    )
