"""Headless-browser smoke tests for every ``ui://`` resource bundle.

Phase 6c of the v2.0 plan (see ``Plans/linear-swimming-pond.md`` §6c). Loads
each bundle in a real Chromium page via Playwright and asserts:

1. The page reaches ``DOMContentLoaded`` without uncaught JS errors.
2. The expected root element exists in the rendered DOM.
3. No ``console.error`` calls fire from the bundle's own inline JS (errors
   originating from CDN scripts — Plotly, Leaflet — are filtered out because
   they're network-dependent and not our bug).

These tests are deselected from the regular suite via the ``smoke`` marker
(see ``pyproject.toml::[tool.pytest.ini_options]``). To run locally:

    uv sync --group smoke
    uv run playwright install chromium
    uv run pytest -m smoke tests/smoke/

CI runs them as a separate ``smoke`` job (see ``.github/workflows/ci.yml``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip(
    "playwright.sync_api",
    reason="Playwright not installed — run `uv sync --group smoke` to enable smoke tests.",
)

pytestmark = pytest.mark.smoke

# ---------------------------------------------------------------------------
# Bundle directory + sample payloads
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BUNDLES_DIR = REPO_ROOT / "meta_data_mcp" / "ui_resources"


# Per-bundle sample payload (injected as ``window.__app_data__`` before script
# load). Apps that don't consume ``__app_data__`` get ``None`` — they render
# their idle/empty state, which is still a valid smoke target.
SAMPLE_PAYLOADS: dict[str, dict[str, Any] | None] = {
    "shape_timeseries_v1.html": {
        "points": [
            {"date": "2024-01-01", "value": 1.0, "series": "smoke"},
            {"date": "2024-01-02", "value": 1.5, "series": "smoke"},
        ],
        "axes": {"x": "Date", "y": "Value"},
    },
    "shape_geofeatures_v1.html": {
        "features": [
            {"lat": 0.0, "lon": 0.0, "attrs": {"name": "origin"}},
            {"lat": 51.5, "lon": -0.12, "attrs": {"name": "london"}},
        ],
    },
    "shape_records_v1.html": {
        "rows": [
            {"id": 1, "name": "smoke", "active": True},
            {"id": 2, "name": "test", "active": False},
        ],
        "schema": {
            "columns": [
                {"name": "id", "type": "number"},
                {"name": "name", "type": "string"},
                {"name": "active", "type": "boolean"},
            ]
        },
    },
    "app_discovery_v1.html": None,
    "app_vulnerability_v1.html": None,
}

# At least one element matching the selector must be present after load. We
# don't pin a single id (so bundle internals can evolve), only that *some*
# known mount point rendered.
ROOT_SELECTORS: dict[str, str] = {
    "shape_timeseries_v1.html": "#chart, #profile",
    "shape_geofeatures_v1.html": "#gf-map, #gf-info",
    "shape_records_v1.html": "#app, #facets-list",
    "app_discovery_v1.html": "#app",
    "app_vulnerability_v1.html": "#app",
}

# CDN origins to ignore in error filtering. Bundle's own inline JS has no
# source URL on its errors; CDN scripts identify themselves via the URL in
# the error's stack/location.
CDN_ORIGINS_TO_IGNORE = (
    "cdn.plot.ly",
    "unpkg.com",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def browser():
    """Module-scoped Chromium for cheap reuse across bundle parametrizations."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        try:
            yield b
        finally:
            b.close()


def _is_cdn_error(text: str) -> bool:
    return any(origin in text for origin in CDN_ORIGINS_TO_IGNORE)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bundle_name", sorted(SAMPLE_PAYLOADS))
def test_bundle_loads_without_uncaught_errors(browser, bundle_name: str) -> None:
    """Each ``ui://`` bundle reaches DOMContentLoaded without uncaught JS
    errors and exposes its expected root mount point."""
    bundle_path = BUNDLES_DIR / bundle_name
    assert bundle_path.exists(), f"bundle file missing: {bundle_path}"

    page = browser.new_page()
    page_errors: list[str] = []
    console_errors: list[str] = []
    page.on("pageerror", lambda e: page_errors.append(str(e)))
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )

    payload = SAMPLE_PAYLOADS[bundle_name]
    if payload is not None:
        page.add_init_script(f"window.__app_data__ = {json.dumps(payload)};")

    try:
        page.goto(bundle_path.as_uri(), wait_until="domcontentloaded")
        # Brief settle for inline scripts that run immediately after
        # DOMContentLoaded (the bundles register message listeners + paint
        # their initial state synchronously).
        page.wait_for_timeout(500)

        bundle_page_errors = [e for e in page_errors if not _is_cdn_error(e)]
        bundle_console_errors = [e for e in console_errors if not _is_cdn_error(e)]

        assert not bundle_page_errors, (
            f"{bundle_name} threw uncaught JS errors:\n  - "
            + "\n  - ".join(bundle_page_errors)
        )
        assert not bundle_console_errors, (
            f"{bundle_name} logged console.error from its own JS:\n  - "
            + "\n  - ".join(bundle_console_errors)
        )

        selector = ROOT_SELECTORS[bundle_name]
        count = page.locator(selector).count()
        assert count > 0, (
            f"{bundle_name} did not render any element matching {selector!r}. "
            "The bundle either crashed before mount or its root id changed; "
            "update ROOT_SELECTORS in this file if the change is intentional."
        )
    finally:
        page.close()


def test_every_bundle_in_repo_has_a_smoke_case() -> None:
    """If a new ``ui://`` bundle lands without a smoke entry, this fails
    loudly. Keeps Phase 6c coverage honest as Phase 5 ships more apps."""
    on_disk = {p.name for p in BUNDLES_DIR.glob("*.html")}
    covered = set(SAMPLE_PAYLOADS)
    missing = sorted(on_disk - covered)
    extra = sorted(covered - on_disk)
    assert not missing, (
        f"New bundle(s) without smoke coverage: {missing}. "
        f"Add an entry to SAMPLE_PAYLOADS + ROOT_SELECTORS in {Path(__file__).name}."
    )
    assert not extra, (
        f"SAMPLE_PAYLOADS references files that don't exist on disk: {extra}."
    )
