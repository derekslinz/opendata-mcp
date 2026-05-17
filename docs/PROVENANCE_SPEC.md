# Provenance Specification

**Version**: 1
**Status**: Stable (shipped on `feat/provenance-meta` / PR #90)
**Companion code**: `meta_data_mcp/provenance.py`
**Companion tests**: `tests/test_provenance.py`

This document is the **canonicalization spec** for the optional
provenance metadata meta-data-mcp attaches to every `tools/call`
result when `META_DATA_MCP_PROVENANCE` is enabled. A receiver
following this document — without source-diving the server code —
can independently recompute the advertised sha256 digest from the
visible response, verifying that the result has not been tampered
with in transit and that it was produced by the exact `(tool,
arguments)` pair the receiver thinks it was.

The spec is intentionally narrow. Every load-bearing kwarg is
documented; nothing is left implicit. Implementing this in any
language with a Pydantic-equivalent JSON serializer and a sha256
library should produce identical bytes.

---

## 1. Enabling

Set `META_DATA_MCP_PROVENANCE` to a truthy value:

| Truthy (case-insensitive, whitespace-trimmed) | Falsy |
|---|---|
| `1`, `true`, `yes`, `on` | unset, empty string, `0`, `false`, `no`, `off`, anything else |

When falsy/unset, no provenance metadata is attached and no overhead
is incurred. This document only applies when the env var is truthy.

## 2. Placement

When enabled, every successful `tools/call` response carries
provenance metadata on the **first content block's** `_meta` field
under a single namespaced key:

```json
{
  "content": [
    {
      "type": "text",
      "text": "<tool result>",
      "_meta": {
        "meta-data-mcp/provenance": {
          "sha256": "<64-char lowercase hex digest>",
          "timestamp": "YYYY-MM-DDTHH:MM:SS.mmmZ"
        }
      }
    },
    {
      "type": "text",
      "text": "<additional block>"
    }
  ]
}
```

Provenance is placed on the **first block only**. Subsequent blocks
are not modified. Any pre-existing `_meta` entries on the first block
are preserved — the `meta-data-mcp/provenance` key is merged in,
existing keys remain.

### 2.1 Empty content

If the tool handler returns an empty content list, a stub
`TextContent(type="text", text="")` block is synthesized to carry the
provenance metadata, and the server logs a `WARNING` naming the tool
(operators should investigate — an empty result is almost always a
bug). The receiver sees exactly one content block in this case.

## 3. The `sha256` field

A 64-character lowercase hexadecimal sha256 digest of the canonical
bytes described in §5. Standard sha256 — no HMAC, no key. This
provides **integrity** and **input-output binding**, not
authenticity. A future variant may add HMAC; this spec does not.

## 4. The `timestamp` field

ISO 8601 UTC with millisecond precision and a trailing `Z`:

```
YYYY-MM-DDTHH:MM:SS.mmmZ
```

Captured at dispatch-completion time on the server. Not covered by
the digest (it is part of the provenance payload itself, which is
excluded from the canonical bytes — see §5.1).

Note: clock skew between the server and a downstream auditor is not
addressed by this spec. If you need authoritative time, layer NTP or
a trusted timestamping service on top.

## 5. Canonical bytes (the spec)

The advertised sha256 is computed over the following byte sequence:

```python
canonical = json.dumps(
    envelope,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=True,
).encode("utf-8")
digest = hashlib.sha256(canonical).hexdigest()
```

Where `envelope` is built as follows.

### 5.1 The envelope shape

```python
envelope = {
    "tool":      <str, the tool name from CallToolRequest.params.name>,
    "arguments": <dict, CallToolRequest.params.arguments or {}>,
    "content":   <list of dumped content blocks, see §5.2>,
}
```

`arguments=None` and `arguments={}` are equivalent — both yield `{}`
in the envelope. This means two callers expressing "no arguments"
two different ways agree on the digest.

The provenance metadata itself does **not** appear in the envelope.
It is stripped per-block in §5.2.

### 5.2 Per-block rendering

Each content block is converted via Pydantic's `model_dump` and
then stripped of any `_meta` entry:

```python
rendered = []
for block in response_content:
    dumped = block.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    dumped.pop("_meta", None)
    rendered.append(dumped)
envelope["content"] = rendered
```

### 5.3 Why each kwarg matters

Every kwarg in this section is **load-bearing**. Changing any of
them produces a different digest, breaking the spec for receivers.

| Kwarg | Why required |
|---|---|
| `model_dump(mode="json")` | Coerces nested non-JSON-native fields (`AnyUrl`, `Decimal`, `datetime`) to JSON-native types. Without this, an `EmbeddedResource` whose nested `resource.uri` is `AnyUrl` blows up the serializer. |
| `model_dump(by_alias=True)` | Pydantic uses the wire-format field names. MCP's `_meta` field is aliased — `meta` is the Python attribute name. Using attribute names would put `meta` in the bytes instead of `_meta`. |
| `model_dump(exclude_none=True)` | Optional fields default to `None` on the sender side. Including them as `null` in the bytes would diverge from the wire format the receiver sees. |
| `dumped.pop("_meta", None)` | The provenance metadata is in `_meta`. The digest must be reproducible by a receiver that *sees* `_meta` (we can't ask them to recompute over input they don't have). Stripping `_meta` per-block before hashing means the receiver strips the same way and matches. |
| `json.dumps(sort_keys=True)` | Insertion order differs between Pydantic dumps and arbitrary receiver dicts. Sorting keys at every nesting level collapses the variability. |
| `json.dumps(separators=(",", ":"))` | The default `json.dumps` inserts `", "` and `": "` (with spaces). The compact separator removes the whitespace; without this, a receiver using compact serialization would compute different bytes. |
| `json.dumps(ensure_ascii=True)` | Non-ASCII characters like `"café"` are escaped as `"café"`. With `ensure_ascii=False`, they'd be UTF-8 directly. The two byte sequences hash differently. We pin `True` because it is the JSON standard and stable across language ecosystems. |
| `.encode("utf-8")` | The output of `json.dumps` is a Python `str`; sha256 hashes bytes. UTF-8 is the canonical encoding for JSON. |

## 6. Receiver verification recipe

The exact code a receiver runs to verify a result. This is canonical:

```python
import hashlib
import json

# Inputs the receiver has:
#   - tool_name: the tool the caller invoked
#   - arguments: the arguments the caller supplied (or None)
#   - response.content: the list of content blocks the server returned
#   - advertised: response.content[0]._meta["meta-data-mcp/provenance"]["sha256"]

rendered = []
for block in response_content:
    dumped = block.model_dump(mode="json", by_alias=True, exclude_none=True)
    dumped.pop("_meta", None)
    rendered.append(dumped)

envelope = {
    "tool": tool_name,
    "arguments": arguments or {},
    "content": rendered,
}
canonical = json.dumps(
    envelope,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=True,
).encode("utf-8")
recomputed = hashlib.sha256(canonical).hexdigest()

assert recomputed == advertised, "provenance digest mismatch"
```

For non-Python receivers: implement an equivalent JSON canonicalizer
that emits the same byte sequence. The 8-row table in §5.3 enumerates
every behavior that must match.

## 7. What the spec guarantees

| Property | Guarantee | Mechanism |
|---|---|---|
| **Tamper-evidence on content** | A receiver detects any modification to the returned `content` blocks. | Bit-level digest over the canonical bytes. |
| **Input-output binding** | A receiver detects a result delivered for the wrong `(tool, arguments)`. | The envelope includes `tool` + `arguments`. |
| **Reproducibility from visible data only** | A receiver can verify without source-diving the server. | This spec is the public contract; stripping `_meta` before hashing makes the round-trip work. |
| **Stability across languages** | A receiver implemented in Go, Rust, etc. can verify a Python-server digest. | Every kwarg is explicit; no implementation-defined behavior. |

## 8. What the spec does NOT guarantee

| Limitation | Reason |
|---|---|
| **Authenticity** (no proof of who produced the digest) | sha256 is unkeyed. A future HMAC variant would add this; out of scope here. |
| **Time integrity** (no proof the timestamp is correct) | Server clock is trusted. Use NTP/trusted timestamping for stronger guarantees. |
| **Provenance across hops** | The digest covers one server's response. A pipeline that re-serializes results downstream loses the chain. |
| **Replay protection** | A captured `(call, response, digest)` tuple is reusable. Use nonces / TTL in the application layer if needed. |
| **Side-channel observation** | The digest doesn't hide the response from anyone who can see the wire. |

## 9. Versioning

This spec is version 1. Future breaking changes will ship under a
new key (`meta-data-mcp/provenance-v2`) alongside v1, never replacing
it; receivers can detect which version is present by inspecting
which keys appear in `_meta`.

The current implementation in `meta_data_mcp/provenance.py` always
emits v1 metadata. The constant
`provenance.PROVENANCE_META_KEY = "meta-data-mcp/provenance"` (no
version suffix) is the v1 key by definition.

## 10. References

- Companion ADR: ADR 0001 (no persistent state — health/cache state
  resets between processes; provenance does not change this)
- Companion code: `meta_data_mcp/provenance.py` — implementation
- Companion tests: `tests/test_provenance.py` — 34 tests covering
  every property in §7 plus 7 negative cases (digest changes with
  content, tool name, arguments)
- Roadmap entry: v2.2 in `docs/ROADMAP.md`
- Related: README "Server runtime flags" section (
  `META_DATA_MCP_PROVENANCE` env var documentation)
