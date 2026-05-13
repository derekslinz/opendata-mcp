"""
meta-data-mcp — the one MCP server.

A single MCP server that transparently routes user requests to internal
data plugins. The ~60 modules alongside this one are *plugins*, not
separate servers — they borrow the MCP tool/handler shape for code
organization but are exposed under this one server's tool namespace.

This module is both:

1. The discovery layer — exposing meta tools that let an LLM search the
   internal plugin registry (`opendata-find-providers`,
   `opendata-list-domains`, etc.).
2. The runtime entry point — `main()` discovers every plugin module
   under `meta_data_mcp.providers`, imports it, and merges its tools
   into the single server's tool list before serving.

The CLI's `meta-data-mcp run` calls `main()` here. There is no second
server.
"""

import importlib
import logging
import re
from typing import Any, List, Optional, Sequence

import mcp.types as types
from pydantic import AnyUrl, BaseModel, Field

from meta_data_mcp.utils import serialize_for_llm

from meta_data_mcp.registry import (
    REGISTRY,
    get_provider,
    list_domains,
    list_regions,
)
from meta_data_mcp.routing import RoutingEngine

log = logging.getLogger(__name__)

# Module-level singleton — cache survives across tool calls within the same server process.
_engine = RoutingEngine()

# Registration Variables
RESOURCES: List[Any] = []
RESOURCES_HANDLERS: dict[str, Any] = {}
TOOLS: List[types.Tool] = []
TOOLS_HANDLERS: dict[str, Any] = {}


###################
# find-providers
###################


class FindProvidersParams(BaseModel):
    """Filters for `opendata-find-providers`."""

    query: Optional[str] = Field(
        None,
        description="Free-text query. Matched against id, title, description, keywords, domains, regions. Tokens with exact keyword hits score higher.",
    )
    domain: Optional[str] = Field(
        None,
        description="Restrict to providers tagged with this domain (e.g. 'health', 'legal', 'finance'). Use opendata-list-domains to enumerate.",
    )
    region: Optional[str] = Field(
        None,
        description="Restrict to providers tagged with this region (e.g. 'us', 'eu', 'uk', 'global'). Use opendata-list-regions to enumerate.",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of providers to return (1-100, default 20).",
    )


async def handle_find_providers(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opendata-find-providers tool call.

    Uses sophisticated multi-criteria routing for intelligent provider ranking.
    Falls back to original token-based search if needed.
    """
    try:
        params = FindProvidersParams(**(arguments or {}))

        scored_results = await _engine.route(
            query=params.query,
            domain=params.domain,
            region=params.region,
            limit=params.limit,
            explain=False,
        )

        # Extract entries for compatibility
        matches = [result.entry for result in scored_results]

        payload: dict[str, Any] = {
            "count": len(matches),
            "providers": [entry.to_dict() for entry in matches],
        }

        # When the user supplied a query but nothing matched, hand the LLM
        # the next move: it can autonomously create a new plugin for this
        # query by calling `opendata-create-plugin` with a YAML spec.
        if params.query and not matches:
            payload["no_match"] = True
            payload["next_step"] = (
                "No registered plugin matches this query. To serve this "
                "request autonomously: (1) web-search for an open/public "
                "API that exposes the requested data, (2) call "
                "`opendata-draft-spec` with the API's id, base_url, and "
                "tool definitions to get a validated YAML spec, (3) pass "
                "that spec to `opendata-create-plugin` to materialize, "
                "register, and hot-load a new plugin in this running "
                "server. Its tools will become available immediately "
                "afterwards."
            )

        return [types.TextContent(type="text", text=serialize_for_llm(payload))]
    except Exception as e:
        log.error(f"Error in opendata-find-providers: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opendata-find-providers",
        description=(
            "Search the meta-data-mcp plugin registry. Returns plugins that "
            "match a free-text query and/or domain/region filters. Use this "
            "FIRST when you don't know which plugin can answer a question. "
            "If no plugin matches, the response includes a `next_step` field "
            "that explains how to autonomously create one via "
            "`opendata-create-plugin`."
        ),
        inputSchema=FindProvidersParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opendata-find-providers"] = handle_find_providers


###################
# create-plugin (autonomous plugin generation)
###################


class CreatePluginParams(BaseModel):
    """Parameters for `opendata-create-plugin`.

    The LLM is expected to draft `spec_yaml` after web-searching for an open
    API that fits the user's query. The YAML follows the schema described in
    `tools/specs/README.md`; use `tools/specs/example_weather_alert.yaml`
    as a template.
    """

    spec_yaml: str = Field(
        ...,
        description=(
            "Full YAML spec for the new plugin. Must include id, server_name, "
            "base_url, description, homepage, and at least one tool. See "
            "tools/specs/example_weather_alert.yaml for the canonical form."
        ),
    )
    domains: list[str] = Field(
        default_factory=list,
        description=(
            "Registry domains for the new plugin (e.g. ['security']). "
            "Use `opendata-list-domains` to see existing values, but new "
            "domain names are allowed."
        ),
    )
    regions: list[str] = Field(
        default_factory=list,
        description=(
            "Registry regions for the new plugin (e.g. ['global', 'us']). "
            "Use `opendata-list-regions` to see existing values."
        ),
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Search keywords that should match this plugin.",
    )
    license_note: str = Field(
        default="",
        description="Optional short licensing/attribution note for the data source.",
    )
    requires_env: list[str] = Field(
        default_factory=list,
        description=(
            "Names of any environment variables the new plugin needs "
            "(e.g. API keys). Leave empty for keyless APIs."
        ),
    )


async def handle_create_plugin(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Materialize a new plugin from a YAML spec, register it, and hot-load.

    Pipeline:
        1. Validate the spec (parse YAML, sanity-check required keys).
        2. Write the spec to ``tools/specs/{id}.yaml``.
        3. Invoke ``tools/generate_provider.py`` to write the plugin module
           and its test stub.
        4. Import the new module.
        5. Register a ``ProviderEntry`` in the in-memory dynamic registry.
        6. Merge the new module's TOOLS / TOOLS_HANDLERS into the running
           server's tool list.

    The new tools become available in the same server process. The MCP
    client will see them on its next ``tools/list`` request.
    """
    import contextlib
    import subprocess
    import sys as _sys

    import yaml as _yaml

    from meta_data_mcp.registry import (
        ProviderEntry,
        get_provider,
        register_plugin,
    )

    try:
        params = CreatePluginParams(**(arguments or {}))

        try:
            spec = _yaml.safe_load(params.spec_yaml)
        except _yaml.YAMLError as exc:
            return [
                types.TextContent(
                    type="text",
                    text=serialize_for_llm({"error": f"YAML parse error: {exc}"}),
                )
            ]

        if not isinstance(spec, dict):
            return [
                types.TextContent(
                    type="text",
                    text=serialize_for_llm(
                        {"error": "Spec must be a YAML mapping at the top level."}
                    ),
                )
            ]

        required = ("id", "server_name", "base_url", "description", "tools")
        missing = [k for k in required if k not in spec]
        if missing:
            return [
                types.TextContent(
                    type="text",
                    text=serialize_for_llm(
                        {"error": f"Spec missing required keys: {missing}"}
                    ),
                )
            ]

        plugin_id = spec["id"]

        if get_provider(plugin_id) is not None:
            return [
                types.TextContent(
                    type="text",
                    text=serialize_for_llm(
                        {
                            "error": (
                                f"Plugin '{plugin_id}' already registered. "
                                "Use a different id or call its existing tools."
                            )
                        }
                    ),
                )
            ]

        # Resolve repo paths. When installed via uvx, the source tree is in
        # the read-only uv cache — we still try to write because the failure
        # is informative.
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[2]
        specs_dir = repo_root / "tools" / "specs"
        generator = repo_root / "tools" / "generate_provider.py"

        if not generator.exists():
            return [
                types.TextContent(
                    type="text",
                    text=serialize_for_llm(
                        {
                            "error": (
                                f"Generator not found at {generator}. Autonomous "
                                "plugin creation requires running from a source "
                                "checkout, not a uvx install."
                            )
                        }
                    ),
                )
            ]

        try:
            specs_dir.mkdir(parents=True, exist_ok=True)
            spec_path = specs_dir / f"{plugin_id}.yaml"
            spec_path.write_text(params.spec_yaml)
        except OSError as exc:
            return [
                types.TextContent(
                    type="text",
                    text=serialize_for_llm(
                        {"error": f"Could not write spec file: {exc}"}
                    ),
                )
            ]

        proc = subprocess.run(
            [_sys.executable, str(generator), str(spec_path), "--force"],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            with contextlib.suppress(OSError):
                spec_path.unlink()
            return [
                types.TextContent(
                    type="text",
                    text=serialize_for_llm(
                        {
                            "error": "Generator failed",
                            "stderr": proc.stderr,
                            "stdout": proc.stdout,
                        }
                    ),
                )
            ]

        # Import the freshly-written plugin module.
        try:
            new_module = importlib.import_module(f"meta_data_mcp.providers.{plugin_id}")
        except Exception as exc:  # noqa: BLE001 — surface any import error
            with contextlib.suppress(OSError):
                spec_path.unlink()
            return [
                types.TextContent(
                    type="text",
                    text=serialize_for_llm(
                        {"error": f"Generated plugin failed to import: {exc}"}
                    ),
                )
            ]

        # Register in the in-memory dynamic registry.
        entry = ProviderEntry(
            id=plugin_id,
            server_name=spec.get("server_name", plugin_id.replace("_", "-")),
            title=spec.get("title", plugin_id),
            description=spec.get("description", ""),
            domains=tuple(params.domains),
            regions=tuple(params.regions),
            keywords=tuple(params.keywords),
            homepage=spec.get("homepage", ""),
            license_note=params.license_note,
            requires_env=tuple(params.requires_env),
        )
        register_plugin(entry)

        # Hot-load the new module's tools into this running server.
        owner_by_tool = {name: "(existing)" for name in TOOLS_HANDLERS}
        added = _merge_plugin(new_module, plugin_id, owner_by_tool)

        new_tool_names = [t.name for t in (getattr(new_module, "TOOLS", None) or [])]

        return [
            types.TextContent(
                type="text",
                text=serialize_for_llm(
                    {
                        "status": "ok",
                        "plugin_id": plugin_id,
                        "tools_added": added,
                        "new_tool_names": new_tool_names,
                        "registry_entry": entry.to_dict(),
                        "message": (
                            f"Plugin '{plugin_id}' is now live. "
                            f"{added} new tool(s) available: {new_tool_names}. "
                            "Call them directly to answer the user's original query."
                        ),
                    }
                ),
            )
        ]
    except Exception as e:
        log.error(f"Error in opendata-create-plugin: {e}")
        return [
            types.TextContent(
                type="text",
                text=serialize_for_llm({"error": str(e)}),
            )
        ]


TOOLS.append(
    types.Tool(
        name="opendata-create-plugin",
        description=(
            "Autonomously create a new plugin for this meta-data-mcp server "
            "from a YAML spec. Use this when `opendata-find-providers` "
            "returned no match. Recommended flow: first call "
            "`opendata-draft-spec` with structured fields to get a valid "
            "YAML spec, then pass it here. The new plugin is materialized "
            "to disk, imported, registered in the live registry, and its "
            "tools become available immediately."
        ),
        inputSchema=CreatePluginParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opendata-create-plugin"] = handle_create_plugin


###################
# draft-spec (build a YAML plugin spec from structured inputs)
###################


class DraftSpecToolParam(BaseModel):
    """One parameter on a tool inside a draft spec."""

    name: str = Field(
        ...,
        description="Parameter name (snake_case, matches API query/path param).",
    )
    type: str = Field(
        ...,
        description="Type: one of 'str', 'int', 'float', 'bool'.",
    )
    required: bool = Field(
        default=False,
        description="Whether the parameter is required.",
    )
    description: str = Field(
        default="",
        description="Short human-readable description of the parameter.",
    )
    default: Any | None = Field(
        default=None,
        description="Optional default value when the parameter is not required.",
    )


class DraftSpecTool(BaseModel):
    """One tool entry in a draft plugin spec."""

    name: str = Field(
        ...,
        description=(
            "Tool name in globally unique kebab-case, often using a "
            "provider-specific prefix (e.g. 'nvd-list-cves')."
        ),
    )
    description: str = Field(
        ...,
        description="Concise description of what the tool returns. The LLM sees this.",
    )
    endpoint: str = Field(
        ...,
        description=(
            "URL path relative to base_url. May contain {placeholders} for "
            "path parameters (e.g. '/cves/{cve_id}'). Each placeholder must "
            "appear as a required param of matching name."
        ),
    )
    response_format: str = Field(
        default="json",
        description="'json' (default) or 'text' for plain-text responses.",
    )
    params: list[DraftSpecToolParam] = Field(
        default_factory=list,
        description="Query parameters and path-placeholder parameters for this tool.",
    )


class DraftSpecParams(BaseModel):
    """Structured inputs that produce a valid plugin YAML spec."""

    id: str = Field(
        ...,
        description=(
            "Plugin id in snake_case, e.g. 'global_nvd_cve'. Becomes the "
            "Python module name under meta_data_mcp/providers/."
        ),
    )
    title: str = Field(
        ...,
        description="Human-readable title for the registry entry.",
    )
    base_url: str = Field(
        ...,
        description="API base URL with no trailing slash (e.g. 'https://services.nvd.nist.gov').",
    )
    description: str = Field(
        ...,
        description="One- or two-sentence description of what this plugin covers.",
    )
    homepage: str = Field(
        ...,
        description="URL to the API documentation or provider homepage.",
    )
    tools: list[DraftSpecTool] = Field(
        ...,
        min_length=1,
        description="At least one tool definition. Each becomes one MCP tool on the server.",
    )
    server_name: str | None = Field(
        default=None,
        description=(
            "kebab-case server name for the plugin registry entry. "
            "Defaults to id with underscores replaced by hyphens."
        ),
    )
    domains: list[str] = Field(
        default_factory=list,
        description="Registry domains (e.g. ['security', 'government']).",
    )
    regions: list[str] = Field(
        default_factory=list,
        description="Registry regions (e.g. ['global', 'us']).",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Search keywords that should match this plugin in opendata-find-providers.",
    )
    requires_env: list[str] = Field(
        default_factory=list,
        description="Names of environment variables this API needs (e.g. ['NVD_API_KEY']).",
    )


_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_ALLOWED_PARAM_TYPES = ("str", "int", "float", "bool")


async def handle_draft_spec(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Compose a validated plugin YAML spec from structured inputs.

    Use this BEFORE calling `opendata-create-plugin`. The output is a
    YAML string that's syntactically valid, schema-compliant, and ready
    to pass straight through. This eliminates the need to hand-author
    YAML and surfaces validation errors up-front.
    """
    import yaml as _yaml

    try:
        params = DraftSpecParams(**(arguments or {}))

        if not _ID_RE.match(params.id):
            return [
                types.TextContent(
                    type="text",
                    text=serialize_for_llm(
                        {
                            "error": (
                                f"id {params.id!r} must be lowercase snake_case "
                                "(matches /^[a-z][a-z0-9_]*$/)."
                            )
                        }
                    ),
                )
            ]

        server_name = params.server_name or params.id.replace("_", "-")
        if not _TOOL_NAME_RE.match(server_name):
            return [
                types.TextContent(
                    type="text",
                    text=serialize_for_llm(
                        {
                            "error": (
                                f"server_name {server_name!r} must be lowercase "
                                "kebab-case."
                            )
                        }
                    ),
                )
            ]

        # Validate every tool entry.
        for i, tool in enumerate(params.tools):
            if not _TOOL_NAME_RE.match(tool.name):
                return [
                    types.TextContent(
                        type="text",
                        text=serialize_for_llm(
                            {
                                "error": (
                                    f"tools[{i}].name {tool.name!r} must be "
                                    "lowercase kebab-case."
                                )
                            }
                        ),
                    )
                ]
            if tool.response_format not in ("json", "text"):
                return [
                    types.TextContent(
                        type="text",
                        text=serialize_for_llm(
                            {
                                "error": (
                                    f"tools[{i}].response_format must be 'json' "
                                    f"or 'text', got {tool.response_format!r}."
                                )
                            }
                        ),
                    )
                ]
            placeholders = _PLACEHOLDER_RE.findall(tool.endpoint)
            param_names = {p.name for p in tool.params}
            missing_placeholders = [p for p in placeholders if p not in param_names]
            if missing_placeholders:
                return [
                    types.TextContent(
                        type="text",
                        text=serialize_for_llm(
                            {
                                "error": (
                                    f"tools[{i}] endpoint has placeholders "
                                    f"{missing_placeholders} that are not declared "
                                    "as params."
                                )
                            }
                        ),
                    )
                ]
            for j, p in enumerate(tool.params):
                if p.type not in _ALLOWED_PARAM_TYPES:
                    return [
                        types.TextContent(
                            type="text",
                            text=serialize_for_llm(
                                {
                                    "error": (
                                        f"tools[{i}].params[{j}].type "
                                        f"{p.type!r} must be one of "
                                        f"{list(_ALLOWED_PARAM_TYPES)}."
                                    )
                                }
                            ),
                        )
                    ]
                if p.name in placeholders and not p.required:
                    return [
                        types.TextContent(
                            type="text",
                            text=serialize_for_llm(
                                {
                                    "error": (
                                        f"tools[{i}].params[{j}] {p.name!r} is a "
                                        "path placeholder and must be required=true."
                                    )
                                }
                            ),
                        )
                    ]

        # Build the plain-dict spec, in the same field order the example uses
        # so the emitted YAML matches the project's existing style.
        spec_dict: dict[str, Any] = {
            "id": params.id,
            "server_name": server_name,
            "title": params.title,
            "base_url": params.base_url,
            "description": params.description,
            "homepage": params.homepage,
        }
        if params.domains:
            spec_dict["domains"] = list(params.domains)
        if params.regions:
            spec_dict["regions"] = list(params.regions)
        if params.keywords:
            spec_dict["keywords"] = list(params.keywords)
        if params.requires_env:
            spec_dict["requires_env"] = list(params.requires_env)

        spec_dict["tools"] = []
        for tool in params.tools:
            tool_dict: dict[str, Any] = {
                "name": tool.name,
                "description": tool.description,
                "endpoint": tool.endpoint,
                "response_format": tool.response_format,
            }
            if tool.params:
                tool_dict["params"] = []
                for p in tool.params:
                    p_dict: dict[str, Any] = {
                        "name": p.name,
                        "type": p.type,
                        "required": p.required,
                        "description": p.description,
                    }
                    if p.default is not None:
                        p_dict["default"] = p.default
                    tool_dict["params"].append(p_dict)
            spec_dict["tools"].append(tool_dict)

        spec_yaml = _yaml.safe_dump(spec_dict, sort_keys=False, width=88)

        return [
            types.TextContent(
                type="text",
                text=serialize_for_llm(
                    {
                        "status": "ok",
                        "spec_yaml": spec_yaml,
                        "next_step": (
                            "Pass `spec_yaml` (and your chosen domains/regions/"
                            "keywords/requires_env) to `opendata-create-plugin` to "
                            "materialize and hot-load the plugin."
                        ),
                    }
                ),
            )
        ]
    except Exception as e:
        log.error(f"Error in opendata-draft-spec: {e}")
        return [
            types.TextContent(
                type="text",
                text=serialize_for_llm({"error": str(e)}),
            )
        ]


TOOLS.append(
    types.Tool(
        name="opendata-draft-spec",
        description=(
            "Build a validated YAML plugin spec from structured inputs. "
            "Use this BEFORE `opendata-create-plugin` to avoid hand-writing "
            "YAML. Validates id format, kebab-case tool names, path-"
            "placeholder/param consistency, parameter types, and response "
            "format. Returns the YAML string ready to feed into "
            "`opendata-create-plugin`."
        ),
        inputSchema=DraftSpecParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opendata-draft-spec"] = handle_draft_spec


###################
# explain-choice
###################


class ExplainChoiceParams(BaseModel):
    """Parameters for explain-choice tool."""

    query: Optional[str] = Field(
        None,
        description="The original search query to explain scoring for.",
    )
    domain: Optional[str] = Field(
        None,
        description="Domain filter used in search.",
    )
    region: Optional[str] = Field(
        None,
        description="Region filter used in search.",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of top providers to explain (1-20, default 5).",
    )


async def handle_explain_choice(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Explain the scoring breakdown for a provider search query.

    Shows how each provider was ranked, including the contribution of
    token matching, fuzzy matching, semantic similarity, and metadata filters.
    """
    try:
        params = ExplainChoiceParams(**(arguments or {}))

        scored_results = await _engine.route(
            query=params.query,
            domain=params.domain,
            region=params.region,
            limit=params.limit,
            explain=True,
        )

        # Format explanation
        explanations = []
        for i, result in enumerate(scored_results, 1):
            explanation = {
                "rank": i,
                "provider_id": result.entry.id,
                "provider_title": result.entry.title,
                "overall_score": round(result.score, 3),
                "scoring_breakdown": result.breakdown,
            }
            explanations.append(explanation)

        payload = {
            "query": params.query,
            "domain_filter": params.domain,
            "region_filter": params.region,
            "results": explanations,
        }

        return [types.TextContent(type="text", text=serialize_for_llm(payload))]
    except Exception as e:
        log.error(f"Error in opendata-explain-choice: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opendata-explain-choice",
        description="Explain the scoring breakdown for a provider search. Shows how each provider was ranked using token matching, fuzzy matching, semantic similarity, and metadata filters.",
        inputSchema=ExplainChoiceParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opendata-explain-choice"] = handle_explain_choice


###################
# list-domains
###################


class ListDomainsParams(BaseModel):
    """No parameters."""


async def handle_list_domains(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opendata-list-domains tool call."""
    try:
        return [
            types.TextContent(
                type="text",
                text=serialize_for_llm({"domains": list_domains()}),
            )
        ]
    except Exception as e:
        log.error(f"Error in opendata-list-domains: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opendata-list-domains",
        description="List the controlled domain vocabulary used by the provider registry (e.g. 'health', 'legal', 'finance', 'earth-science').",
        inputSchema=ListDomainsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opendata-list-domains"] = handle_list_domains


###################
# list-regions
###################


class ListRegionsParams(BaseModel):
    """No parameters."""


async def handle_list_regions(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opendata-list-regions tool call."""
    try:
        return [
            types.TextContent(
                type="text",
                text=serialize_for_llm({"regions": list_regions()}),
            )
        ]
    except Exception as e:
        log.error(f"Error in opendata-list-regions: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opendata-list-regions",
        description="List the controlled region vocabulary used by the provider registry (e.g. 'us', 'eu', 'uk', 'global').",
        inputSchema=ListRegionsParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opendata-list-regions"] = handle_list_regions


###################
# describe-provider
###################


class DescribeProviderParams(BaseModel):
    """Lookup a single registry entry by provider id."""

    provider_id: str = Field(
        ...,
        description="The provider id (e.g. 'us_nasa', 'global_world_bank', 'us_courtlistener').",
    )


async def handle_describe_provider(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opendata-describe-provider tool call."""
    try:
        if not arguments or "provider_id" not in arguments:
            raise ValueError("provider_id is required")
        params = DescribeProviderParams(**arguments)
        entry = get_provider(params.provider_id)
        if entry is None:
            payload = {"error": f"Provider '{params.provider_id}' not found"}
        else:
            payload = entry.to_dict()
        return [types.TextContent(type="text", text=serialize_for_llm(payload))]
    except Exception as e:
        log.error(f"Error in opendata-describe-provider: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opendata-describe-provider",
        description="Fetch the full registry entry for a single provider id — title, description, domains, regions, keywords, homepage, license note, required environment variables.",
        inputSchema=DescribeProviderParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opendata-describe-provider"] = handle_describe_provider


###################
# list-providers
###################


class ListProvidersParams(BaseModel):
    """Pagination over the full registry."""

    limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of entries to return (1-200, default 50).",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of entries to skip (default 0).",
    )


async def handle_list_providers(
    arguments: dict[str, Any] | None = None,
) -> Sequence[types.TextContent]:
    """Handle the opendata-list-providers tool call."""
    try:
        params = ListProvidersParams(**(arguments or {}))
        slice_ = REGISTRY[params.offset : params.offset + params.limit]
        payload = {
            "total": len(REGISTRY),
            "offset": params.offset,
            "limit": params.limit,
            "providers": [
                {
                    "id": entry.id,
                    "title": entry.title,
                    "domains": list(entry.domains),
                    "regions": list(entry.regions),
                    "requires_env": list(entry.requires_env),
                }
                for entry in slice_
            ],
        }
        return [types.TextContent(type="text", text=serialize_for_llm(payload))]
    except Exception as e:
        log.error(f"Error in opendata-list-providers: {e}")
        raise


TOOLS.append(
    types.Tool(
        name="opendata-list-providers",
        description="Enumerate all providers in the opendata-mcp registry (paginated, terse). Returns id, title, domains, regions, and any required env vars per provider.",
        inputSchema=ListProvidersParams.model_json_schema(),
    )
)
TOOLS_HANDLERS["opendata-list-providers"] = handle_list_providers


###################
# Resources
###################

RESOURCES.append(
    types.Resource(
        uri="registry://all-providers",
        name="All OpenData Providers",
        description="A complete list of all currently registered OpenData MCP providers and their metadata.",
        mimeType="application/json",
    )
)


def handle_read_all_providers(uri: AnyUrl) -> str:
    payload = [entry.to_dict() for entry in REGISTRY]
    return serialize_for_llm(payload)


RESOURCES_HANDLERS["registry://all-providers"] = handle_read_all_providers

###################
# Prompts
###################

# Create a module-level variable for prompts
PROMPTS: List[types.Prompt] = []
PROMPTS_HANDLERS: dict[str, Any] = {}

PROMPTS.append(
    types.Prompt(
        name="discover-providers",
        description="Ask the LLM to analyze your needs and suggest the best OpenData MCP providers.",
        arguments=[
            types.PromptArgument(
                name="use_case",
                description="What are you trying to build? (e.g., 'a dashboard for weather and flights')",
                required=True,
            )
        ],
    )
)


async def handle_discover_providers(
    arguments: dict[str, str] | None,
) -> types.GetPromptResult:
    use_case = (arguments or {}).get("use_case", "General exploration")

    return types.GetPromptResult(
        description=f"Suggest providers for: {use_case}",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=f"I want to build the following: {use_case}\n\nPlease use your `opendata-find-providers` tool to search the registry and recommend the 3 most relevant providers for my project. Explain why each one is a good fit and how I can use them together.",
                ),
            )
        ],
    )


PROMPTS_HANDLERS["discover-providers"] = handle_discover_providers

# Predefined Use Cases
USE_CASES = {
    "usecase-financial-research": {
        "title": "Financial & Economic Research",
        "description": "Analyze economic indicators, exchange rates, and financial markets.",
        "text": "I am building a financial research tool. Please suggest 3-5 providers from the registry that deal with economics, finance, exchange rates, or central banks (e.g., FRED, ECB, World Bank, DBnomics). Explain what data each provides and how they can be correlated.",
    },
    "usecase-climate-dashboard": {
        "title": "Climate & Environment Dashboard",
        "description": "Build tools to track weather, climate change, and environmental data.",
        "text": "I am building a climate and environment dashboard. Please suggest 3-5 providers from the registry that deal with weather, climate, emissions, or earth science (e.g., NOAA, Copernicus, OpenMeteo). Explain what data each provides and how to combine them for a comprehensive view.",
    },
    "usecase-healthcare-analytics": {
        "title": "Healthcare & Epidemiology Analytics",
        "description": "Track diseases, clinical trials, and public health data.",
        "text": "I am building a healthcare analytics platform. Please suggest 3-5 providers from the registry that deal with public health, epidemiology, or clinical trials (e.g., CDC, FDA, WHO, Disease.sh). Explain what datasets they offer and how they might be used together.",
    },
    "usecase-academic-literature": {
        "title": "Academic Literature Review",
        "description": "Search for scholarly articles, preprints, and citations.",
        "text": "I am conducting an academic literature review. Please suggest 3-5 providers from the registry that offer access to scholarly publications, metadata, and citations (e.g., ArXiv, CrossRef, EuropePMC, OpenAlex). Explain how to use them together for a comprehensive literature search.",
    },
}

for prompt_id, case_info in USE_CASES.items():
    PROMPTS.append(
        types.Prompt(name=prompt_id, description=case_info["description"], arguments=[])
    )

    # Need a factory function to capture the correct text in the closure
    def make_handler(text: str, title: str):
        async def handler(arguments: dict[str, str] | None) -> types.GetPromptResult:
            return types.GetPromptResult(
                description=f"Recommendations for: {title}",
                messages=[
                    types.PromptMessage(
                        role="user", content=types.TextContent(type="text", text=text)
                    )
                ],
            )

        return handler

    PROMPTS_HANDLERS[prompt_id] = make_handler(case_info["text"], case_info["title"])


# ---------------------------------------------------------------------------
# Plugin loading
# ---------------------------------------------------------------------------
#
# A plugin is a sibling module under meta_data_mcp.providers that exposes
# `TOOLS` and `TOOLS_HANDLERS`. At server start we import every plugin
# listed in the registry and merge its tools into THIS server's tool
# namespace. The result: one server, every plugin's tools available.

# Module names that should never be loaded as data plugins.
_NON_PLUGIN_MODULES: frozenset[str] = frozenset(
    {
        "__template__",
        "meta_data_mcp",  # this file
        "meta_data_mcp_all",  # legacy aggregator (removed but defensively skipped)
    }
)


def _merge_plugin(
    module: Any,
    plugin_id: str,
    owner_by_tool: dict[str, str],
) -> int:
    """Merge a plugin module's TOOLS/TOOLS_HANDLERS into the server.

    Returns the number of tools actually added (after collision filtering).
    """
    plugin_tools = getattr(module, "TOOLS", None) or []
    plugin_handlers = getattr(module, "TOOLS_HANDLERS", None) or {}

    added = 0
    for tool in plugin_tools:
        name = tool.name
        if name in owner_by_tool:
            log.warning(
                "Tool name collision: '%s' already registered by '%s'; "
                "skipping duplicate from '%s'.",
                name,
                owner_by_tool[name],
                plugin_id,
            )
            continue
        handler = plugin_handlers.get(name)
        if handler is None:
            log.warning(
                "Plugin '%s' lists tool '%s' but has no handler; skipping.",
                plugin_id,
                name,
            )
            continue
        TOOLS.append(tool)
        TOOLS_HANDLERS[name] = handler
        owner_by_tool[name] = plugin_id
        added += 1
    return added


def _load_all_plugins() -> tuple[int, int]:
    """Import every registered plugin and merge its tools into THIS server.

    Returns (plugins_loaded, tools_added).
    """
    owner_by_tool: dict[str, str] = {name: "meta" for name in TOOLS_HANDLERS}
    loaded = 0
    added = 0
    for entry in REGISTRY:
        if entry.id in _NON_PLUGIN_MODULES:
            continue
        try:
            module = importlib.import_module(f"meta_data_mcp.providers.{entry.id}")
        except ImportError as exc:
            log.warning("Plugin '%s' could not be imported: %s", entry.id, exc)
            continue
        except Exception as exc:  # noqa: BLE001 — one broken plugin must not block the rest
            log.warning("Plugin '%s' raised during import: %s", entry.id, exc)
            continue
        added += _merge_plugin(module, entry.id, owner_by_tool)
        loaded += 1
    return loaded, added


async def main(transport: str = "stdio", port: int = 8000, host: str = "127.0.0.1"):
    from meta_data_mcp.utils import create_mcp_server, run_server

    plugins_loaded, plugin_tools_added = _load_all_plugins()
    log.info(
        "meta-data-mcp — %d plugins loaded, %d plugin tools + %d discovery tools",
        plugins_loaded,
        plugin_tools_added,
        len(TOOLS) - plugin_tools_added,
    )

    server = create_mcp_server(
        "meta-data-mcp",
        resources=RESOURCES,
        resources_handlers=RESOURCES_HANDLERS,
        tools=TOOLS,
        tools_handlers=TOOLS_HANDLERS,
        prompts=PROMPTS,
        prompts_handlers=PROMPTS_HANDLERS,
    )

    await run_server(server, transport, port, host)


if __name__ == "__main__":
    import anyio

    anyio.run(main)
