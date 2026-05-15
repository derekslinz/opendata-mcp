"""
In-memory provider health registry.

Tracks per-provider failure / success events and exposes a health score in
``[0.0, 1.0]`` for use by routing scorers. Recent failures lower the score;
the score decays back toward 1.0 over time (exponential decay with a ~5 minute
characteristic) so transient outages don't permanently penalize a provider.

This module is intentionally process-local and thread-safe. There is no
persistence across restarts — see the related plan for follow-up work.

The monotonic clock is read via ``_clock`` so tests can inject a fake clock to
drive decay deterministically.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from math import exp
from typing import Callable

# Module-level injectable clock. Defaults to ``time.monotonic`` so callers get
# a steady, never-decreasing reference. Tests may replace this with a callable
# that returns a controlled value.
_clock: Callable[[], float] = time.monotonic


@dataclass
class _ProviderHealthState:
    """Mutable health state for a single provider."""

    failures: int = 0
    last_failure_ts: float | None = None
    last_success_ts: float | None = None


_lock = threading.Lock()
_state: dict[str, _ProviderHealthState] = {}

# Characteristic time (seconds) for failure decay. After this many seconds
# since the last failure, the impact of accumulated failures is reduced by a
# factor of 1/e (~0.37). After several multiples of this constant, even a
# burst of failures is effectively forgotten.
_DECAY_TAU_SECONDS: float = 300.0


def record_failure(provider_id: str, status: int | None = None) -> None:
    """Record a provider failure.

    Args:
        provider_id: The provider's stable id.
        status: Optional HTTP status (currently unused; kept for caller
            compatibility with future translate_http_error wiring).
    """
    del status  # Reserved for future use; not stored.
    now = _clock()
    with _lock:
        entry = _state.get(provider_id)
        if entry is None:
            entry = _ProviderHealthState()
            _state[provider_id] = entry
        entry.failures += 1
        entry.last_failure_ts = now


def record_success(provider_id: str) -> None:
    """Record a provider success.

    Successes decay the failure counter by 1 (floor 0), and update the last
    success timestamp. This lets a stream of successes recover a provider
    that had a brief failure burst.
    """
    now = _clock()
    with _lock:
        entry = _state.get(provider_id)
        if entry is None:
            entry = _ProviderHealthState()
            _state[provider_id] = entry
        entry.last_success_ts = now
        entry.failures = max(0, entry.failures - 1)


def health_score(provider_id: str, *, now: float | None = None) -> float:
    """Return a health score in ``[0.0, 1.0]`` for the provider.

    A score of 1.0 means "fully healthy / no recent failures recorded".
    Lower scores reflect recent accumulated failures, with exponential decay
    over time. Providers with no recorded state are assumed healthy.

    Args:
        provider_id: The provider's stable id.
        now: Optional clock value (seconds, monotonic). When ``None``, reads
            from the module-level ``_clock``. Used by tests to drive decay.
    """
    with _lock:
        entry = _state.get(provider_id)
        if entry is None:
            return 1.0
        failures = entry.failures
        last_failure_ts = entry.last_failure_ts

    if last_failure_ts is None or failures <= 0:
        return 1.0

    current = now if now is not None else _clock()
    dt = current - last_failure_ts
    if dt < 0:
        dt = 0.0

    # Exponential decay: more recent failures hurt more; older ones fade.
    penalty = min(1.0, failures * exp(-dt / _DECAY_TAU_SECONDS))
    score = 1.0 - penalty
    # Clamp defensively.
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def reset(provider_id: str | None = None) -> None:
    """Clear health state.

    Args:
        provider_id: When given, clear only that provider's entry. When
            ``None``, clear all state. Intended for tests.
    """
    with _lock:
        if provider_id is None:
            _state.clear()
        else:
            _state.pop(provider_id, None)
