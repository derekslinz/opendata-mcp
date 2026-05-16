"""Optional sha256 + timestamp provenance for tool-call results.

Opt in by setting the ``META_DATA_MCP_PROVENANCE`` environment variable
to a truthy value (``1``, ``true``, ``yes``, ``on`` — case-insensitive,
surrounding whitespace ignored). When enabled, the server wraps every
``call_tool`` response with provenance metadata attached to the first
content block's ``_meta`` field, under the key
``meta-data-mcp/provenance``:

    {
        "sha256": "<lowercase hex digest>",
        "timestamp": "YYYY-MM-DDTHH:MM:SS.mmmZ"
    }

The digest covers the canonical JSON form of the content blocks with
the provenance metadata itself stripped — so any caller that receives
the response can recompute the digest from the visible content and
verify it. The timestamp is dispatch-completion time in UTC with
millisecond precision.

Default is OFF. Callers that need tamper-evidence or an audit trail
opt in; everyone else pays zero per-call overhead. The flip happens at
the dispatcher in :func:`meta_data_mcp.server.create_mcp_server` so
provenance applies uniformly to every tool — meta tools, plugin tools,
future tools — without per-handler wiring.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Sequence

from mcp import types

PROVENANCE_META_KEY = "meta-data-mcp/provenance"

_ENV_VAR = "META_DATA_MCP_PROVENANCE"
_TRUTHY = frozenset({"1", "true", "yes", "on"})

Content = types.TextContent | types.ImageContent | types.EmbeddedResource


def is_enabled() -> bool:
    """True iff ``META_DATA_MCP_PROVENANCE`` is set to a truthy value."""
    return os.getenv(_ENV_VAR, "").strip().lower() in _TRUTHY


def _canonicalize(content: Sequence[Content]) -> bytes:
    """Stable byte form of the content blocks used as the digest input.

    Each block is dumped with ``by_alias=True, exclude_none=True`` so
    the SDK's wire format is what gets hashed, and the ``_meta`` field
    is stripped from every block — the advertised digest must be
    reproducible by a caller that doesn't see the provenance metadata
    itself.
    """
    rendered: list[dict[str, Any]] = []
    for block in content:
        dumped = block.model_dump(by_alias=True, exclude_none=True)
        dumped.pop("_meta", None)
        rendered.append(dumped)
    return json.dumps(rendered, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _utc_iso_ms() -> str:
    """ISO 8601 UTC with millisecond precision and a trailing ``Z``."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def attach(content: Sequence[Content]) -> list[Content]:
    """Return a fresh content list with provenance attached.

    Provenance is added to the first content block's ``_meta`` field
    under :data:`PROVENANCE_META_KEY`. Any pre-existing ``_meta`` on
    that block is preserved (the provenance key is merged in). When
    ``content`` is empty, a stub ``TextContent(text="")`` is synthesized
    to carry the metadata — so callers still get a fingerprint even on
    no-content responses.

    The input sequence is not mutated; the first block is rebuilt via
    :py:meth:`pydantic.BaseModel.model_copy`.
    """
    digest = hashlib.sha256(_canonicalize(content)).hexdigest()
    payload = {
        PROVENANCE_META_KEY: {
            "sha256": digest,
            "timestamp": _utc_iso_ms(),
        }
    }

    blocks: list[Content] = list(content)
    if not blocks:
        return [types.TextContent(type="text", text="", _meta=payload)]

    first = blocks[0]
    merged_meta = dict(first.meta) if first.meta else {}
    merged_meta.update(payload)
    blocks[0] = first.model_copy(update={"meta": merged_meta})
    return blocks


__all__ = ["PROVENANCE_META_KEY", "attach", "is_enabled"]
