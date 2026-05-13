"""Tests for tools/generate_provider.py.

These tests exercise the generator end-to-end against the
example_weather_alert.yaml spec. They never write anything to disk —
all output is captured in-memory or via --dry-run on stdout.
"""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPO_ROOT / "tools" / "specs" / "example_weather_alert.yaml"
GENERATOR_PATH = REPO_ROOT / "tools" / "generate_provider.py"


# ---------------------------------------------------------------------------
# Import the generator module directly so we can call its functions.
# ---------------------------------------------------------------------------


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_provider", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generator():
    return _load_generator()


@pytest.fixture(scope="module")
def spec(generator):
    return generator.load_spec(SPEC_PATH)


# ---------------------------------------------------------------------------
# Spec parsing
# ---------------------------------------------------------------------------


def test_example_spec_parses(spec):
    """The example spec loads with all expected top-level fields."""
    assert spec["id"] == "us_nws_alerts"
    assert spec["server_name"] == "us-nws-alerts"
    assert spec["base_url"] == "https://api.weather.gov"
    assert "National Weather Service" in spec["description"]
    assert spec["homepage"].startswith("https://www.weather.gov/")
    assert isinstance(spec["tools"], list)
    assert len(spec["tools"]) == 5


def test_example_spec_tools_have_required_fields(spec):
    """Every tool entry exposes name, description, endpoint, params."""
    tool_names = {t["name"] for t in spec["tools"]}
    expected = {
        "nws-list-alerts",
        "nws-get-alert",
        "nws-get-point-forecast",
        "nws-list-zones",
        "nws-get-zone-forecast",
    }
    assert tool_names == expected
    for tool in spec["tools"]:
        assert "name" in tool
        assert "description" in tool
        assert "endpoint" in tool
        assert isinstance(tool.get("params", []), list)


def test_path_param_detection(generator):
    """The path-param regex finds {name} placeholders, including
    multiple placeholders in a single segment."""
    assert generator._path_params("/alerts/active") == []
    assert generator._path_params("/alerts/{alert_id}") == ["alert_id"]
    assert generator._path_params("/points/{latitude},{longitude}") == [
        "latitude",
        "longitude",
    ]
    assert generator._path_params("/zones/{zone_type}/{zone_id}/forecast") == [
        "zone_type",
        "zone_id",
    ]


# ---------------------------------------------------------------------------
# Render output checks (in-memory, no IO)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def rendered(generator, spec):
    provider = generator.render_provider(spec)
    tests = generator.render_tests(spec)
    return {"provider": provider, "tests": tests}


def test_rendered_provider_contains_key_identifiers(rendered):
    src = rendered["provider"]
    # BASE_URL line
    assert "BASE_URL = " in src and "api.weather.gov" in src
    # Module docstring mentions the homepage
    assert "https://www.weather.gov/" in src
    # All tool names appear in TOOLS.append registration lines
    for tool_name in (
        "nws-list-alerts",
        "nws-get-alert",
        "nws-get-point-forecast",
        "nws-list-zones",
        "nws-get-zone-forecast",
    ):
        assert f"name='{tool_name}'" in src or f'name="{tool_name}"' in src

    # Pydantic params classes for each tool (PascalCase + "Params")
    for class_name in (
        "NwsListAlertsParams",
        "NwsGetAlertParams",
        "NwsGetPointForecastParams",
        "NwsListZonesParams",
        "NwsGetZoneForecastParams",
    ):
        assert f"class {class_name}(BaseModel)" in src

    # Handler functions
    for handler in (
        "handle_nws_list_alerts",
        "handle_nws_get_alert",
        "handle_nws_get_point_forecast",
    ):
        assert f"async def {handler}" in src

    # Path-param interpolation for the get-alert endpoint
    assert "{params.alert_id}" in src
    assert "{params.latitude}" in src
    assert "{params.longitude}" in src
    # And the multi-placeholder zone endpoint
    assert "{params.zone_type}" in src
    assert "{params.zone_id}" in src

    # http_get + serialize_for_llm + run_server + create_mcp_server are
    # imported from utils.
    assert "from meta_data_mcp.utils import (" in src
    assert "http_get" in src
    assert "serialize_for_llm" in src
    assert "run_server" in src
    assert "create_mcp_server" in src

    # main() block + __main__ guard
    assert "async def main(" in src
    assert 'if __name__ == "__main__":' in src
    assert "anyio.run(main)" in src


def test_rendered_tests_contains_key_identifiers(rendered):
    src = rendered["tests"]
    # Imports
    assert "from unittest.mock import" in src
    assert "import httpx" in src
    assert "import pytest" in src
    assert "from meta_data_mcp.providers.us_nws_alerts import" in src

    # One success + one error test per tool
    expected_tests = [
        "test_nws_list_alerts_success",
        "test_nws_list_alerts_http_error",
        "test_nws_get_alert_success",
        "test_nws_get_alert_http_error",
        "test_nws_get_point_forecast_success",
        "test_nws_get_point_forecast_http_error",
        "test_nws_list_zones_success",
        "test_nws_list_zones_http_error",
        "test_nws_get_zone_forecast_success",
        "test_nws_get_zone_forecast_http_error",
    ]
    for name in expected_tests:
        assert f"async def {name}" in src


def test_rendered_provider_is_valid_python(rendered):
    """Generated provider code must parse cleanly."""
    ast.parse(rendered["provider"])


def test_rendered_tests_are_valid_python(rendered):
    """Generated test code must parse cleanly."""
    ast.parse(rendered["tests"])


# ---------------------------------------------------------------------------
# CLI / dry-run integration
# ---------------------------------------------------------------------------


def test_dry_run_prints_both_files_to_stdout():
    """`--dry-run` writes everything to stdout and creates no files."""
    result = subprocess.run(
        [
            sys.executable,
            str(GENERATOR_PATH),
            str(SPEC_PATH),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    stdout = result.stdout
    assert "WOULD WRITE" in stdout
    assert "meta_data_mcp/providers/us_nws_alerts.py" in stdout
    assert "tests/providers/test_us_nws_alerts.py" in stdout
    assert 'BASE_URL = "https://api.weather.gov"' in stdout
    assert "class NwsGetAlertParams(BaseModel)" in stdout
    assert "async def handle_nws_get_alert" in stdout

    # Sanity-check: no files were created.
    provider_target = REPO_ROOT / "meta_data_mcp" / "providers" / "us_nws_alerts.py"
    test_target = REPO_ROOT / "tests" / "providers" / "test_us_nws_alerts.py"
    assert not provider_target.exists()
    assert not test_target.exists()


def test_invalid_spec_returns_nonzero(tmp_path):
    """Malformed specs exit with a non-zero status."""
    bad_spec = tmp_path / "bad.yaml"
    bad_spec.write_text("id: 123-not-snake\nserver_name: x\n")
    result = subprocess.run(
        [sys.executable, str(GENERATOR_PATH), str(bad_spec), "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "error" in result.stderr.lower()
