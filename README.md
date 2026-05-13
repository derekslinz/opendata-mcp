# meta-data-mcp

> A single MCP server that transparently routes user requests to ~60 open-data sources.

`meta-data-mcp` is one MCP server — not many. Under the hood it bundles ~60 *plugins*, each wrapping a different open-data API. The plugins are an implementation detail; from your LLM's perspective there is one server, one set of tools, and one place to ask "where can I find data about X?"

You install one server. You get all the data, discoverable through built-in routing tools.

## Why "meta"?

Finding open data isn't the hard part — there's an absurd amount of it available. The hard part is finding the right dataset *when you need it*. `meta-data-mcp` makes that automatic:

- The LLM calls `opendata-find-providers` ("FX rates", "court rulings", "earthquakes near Lisbon") and the server routes the query against an internal registry of every bundled plugin.
- The LLM then calls the matching tool directly. No setup step in between, no separate servers, no per-provider install rituals.

This project was forked from [opendata-mcp](https://github.com/OpenDataMCP/OpenDataMCP) and reshaped around the single-server idea once the catalogue passed a few dozen plugins.

## Installation

You'll need [Claude Desktop](https://claude.ai/download) and `uv` (a Python package manager).

```bash
# macOS — install uv via Homebrew so Claude Desktop can find it
brew install uv

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then register the server with Claude Desktop:

```bash
uv run meta-data-mcp setup
```

That single command:

- Adds **one** entry to `claude_desktop_config.json` — the key is `meta-data-mcp`.
- Removes any legacy entries left over from earlier multi-server setups (`opendata-mcp-meta`, `opendata-mcp-all`, and any individual `opendata-mcp-*` provider entries).
- Backs up your existing config to `claude_desktop_config.json.bak` before writing.

Restart Claude Desktop and you'll see one new server with discovery tools + every plugin's tools available under it.

## CLI

There is one server, so the CLI takes no "provider" argument. Every command operates on the one `meta-data-mcp` server.

| Command | What it does |
|---|---|
| `uv run meta-data-mcp run` | Run the server (default SSE; pass `--transport stdio` for Claude Desktop). |
| `uv run meta-data-mcp setup` | Register the server in Claude Desktop's config. |
| `uv run meta-data-mcp remove` | Unregister the server from Claude Desktop. |
| `uv run meta-data-mcp cleanup` | Detect and remove legacy multi-server entries (`--apply` to commit). |
| `uv run meta-data-mcp inspect` | Launch [mcp-inspector](https://modelcontextprotocol.io/docs/tools/inspector) against the server. |
| `uv run meta-data-mcp list` | Informational: list the internal plugins bundled in this server. |
| `uv run meta-data-mcp info` | Informational: show server overview. Pass `--plugin <name>` for plugin-level details. |
| `uv run meta-data-mcp version` | Print the package version. |

The `list` command exists for transparency about what's bundled — **plugins are not separately installable, runnable, or addressable**. They are loaded automatically when the server starts.

## Migrating from earlier multi-server setups

If you used an older version of this project that installed one MCP server per provider (or the two-server `opendata-mcp-meta` + `opendata-mcp-all` pattern), `setup` cleans those up automatically the next time you run it. To preview what will be removed without changing anything:

```bash
uv run meta-data-mcp cleanup            # preview
uv run meta-data-mcp cleanup --apply    # apply
```

## Server tools (what the LLM calls)

Once `meta-data-mcp` is running, the LLM has access to two layers of tools — and you don't need to mention either to the user:

1. **Meta tools** — the eight server-level tools below. They make routing transparent: the LLM uses them to find (or create) the right plugin without you telling it which tool to call.
2. **Plugin tools** — ~330 tools coming from the ~60 bundled plugins. They are merged into the same namespace at startup. The LLM picks one after consulting the meta tools.

### Meta tools

| Tool | Purpose |
|---|---|
| `opendata-find-providers` | Free-text search over the plugin registry. Returns ranked matches. When nothing matches the response carries a `no_match: true` flag and a `next_step` hint pointing at `opendata-draft-spec` + `opendata-create-plugin`. |
| `opendata-explain-choice` | Show the scoring breakdown for a search (useful for debugging routing decisions). |
| `opendata-list-domains` | Enumerate the controlled domain vocabulary (`health`, `legal`, `finance`, `earth-science`, …). |
| `opendata-list-regions` | Enumerate the controlled region vocabulary (`us`, `eu`, `uk`, `global`, …). |
| `opendata-describe-provider` | Full metadata for one plugin by id — title, description, domains, regions, keywords, homepage, required env vars. |
| `opendata-list-providers` | Paginated dump of the whole registry. |
| `opendata-draft-spec` | **Build a validated plugin YAML spec from structured inputs.** Takes id, base_url, tool definitions (name, endpoint, params), and registry metadata. Validates id/tool-name casing, path-placeholder/param consistency, and parameter types, then emits a YAML string ready to feed into `opendata-create-plugin`. Use this so the LLM never has to hand-author YAML. |
| `opendata-create-plugin` | **Autonomously create a new plugin.** Takes a YAML spec (typically produced by `opendata-draft-spec`), runs the generator, imports the new module, registers it in the live registry, and hot-loads its tools onto the running server. Use this when `opendata-find-providers` returns no match. |

### The autonomous discovery flow

The reason this server is called "meta" is that it routes data requests on the user's behalf — including by *creating* the route when one doesn't exist yet. The full flow:

1. **User asks for data**, e.g. "show me the most recent published CVEs."
2. **LLM calls `opendata-find-providers`** with the query (`cve`, `vulnerability`, …).
3. **If the registry has a match**: the LLM picks the matching plugin's tool and answers — done.
4. **If the registry has no match**: the response includes `no_match: true` and a `next_step` field that explains the autonomous creation path. The LLM:
   1. Tells the user it's about to add coverage for this data source.
   2. Web-searches for an open API that exposes the requested data (e.g. the NVD or CIRCL CVE API).
   3. Calls `opendata-draft-spec` with the API's id, base URL, and structured tool definitions. The server validates the inputs (id casing, path-placeholder consistency, parameter types) and returns a YAML string.
   4. Passes that YAML to `opendata-create-plugin`. The server materializes the plugin module + tests, imports the module, registers a `ProviderEntry` in the in-memory dynamic registry, and merges the new tools into the running server's tool list.
   5. Calls the newly-available tool to answer the user's original question.
5. **User gets their answer** — and the plugin remains available for the rest of the session.

The materialized plugin lives on disk (`meta_data_mcp/providers/{id}.py` + `tests/providers/test_{id}.py`); contributors can clean it up, add it to `meta_data_mcp/registry.py` as a static entry, and open a PR so it becomes part of every shipped install.

### Plugin tools

Every bundled plugin contributes its own tools under the one server. Their names are unique kebab-case identifiers, often using a provider-specific prefix (e.g. `usgs-eq-feed-significant-week`, `frankfurter-latest`, `wikipedia-fetch-summary`). The LLM discovers them through `opendata-find-providers` and `opendata-describe-provider`; you don't need to memorize them.

## Bundled plugins (~60)

This is what's inside the one server. You don't install these individually — they all come along.

### Government / Civic

| Plugin | Source | Description |
|---|---|---|
| `au_data_gov` | Australian Government Open Data | CKAN catalog at data.gov.au |
| `ca_open_gov` | Canada Open Data | CKAN catalog at open.canada.ca |
| `fr_data_gouv` | data.gouv.fr | French government open data platform |
| `nl_tweedekamer` | Tweede Kamer | Dutch Parliament open data |
| `sg_data_gov` | Singapore Open Data | data.gov.sg datasets and collections |
| `uk_gov` | data.gov.uk | UK government CKAN catalog |
| `us_data_gov` | Data.gov | US federal government open datasets |

### Statistics / Economics

| Plugin | Source | Description |
|---|---|---|
| `eu_eurostat` | Eurostat | European Union statistics |
| `global_imf` | International Monetary Fund | IMF SDMX 2.1 statistical data |
| `global_dbnomics` | DBnomics | Global economic data aggregator (IMF, World Bank, etc.) |
| `global_oecd` | OECD | OECD economic & social statistics (SDMX) |
| `global_world_bank` | World Bank | Development indicators by country |
| `nl_cbs` | Statistics Netherlands (CBS) | Dutch statistical datasets (OData v2/v3) |
| `uk_ons` | UK ONS | UK Office for National Statistics |

### Finance / Markets

| Plugin | Source | Description |
|---|---|---|
| `eu_ecb` | European Central Bank | ECB data portal (SDMX) — FX, monetary, banking |
| `global_coingecko` | CoinGecko | Cryptocurrency market data |
| `global_frankfurter` | Frankfurter | ECB reference FX rates (key-less) |
| `us_sec_edgar` | SEC EDGAR | Public company filings, XBRL financials |
| `us_treasury_fiscal` | US Treasury Fiscal Data | Federal debt, daily Treasury statement, FX rates |

### Health & Life Sciences

| Plugin | Source | Description |
|---|---|---|
| `global_disease_sh` | disease.sh | COVID-19, influenza, vaccine aggregator |
| `global_pubchem` | NCBI PubChem | Chemical compounds and substances |
| `global_rcsb_pdb` | RCSB PDB | 3D protein and macromolecular structures |
| `global_who_gho` | WHO GHO | WHO Global Health Observatory (OData) |
| `us_cdc_socrata` | US CDC | CDC open data via Socrata |
| `us_clinicaltrials` | ClinicalTrials.gov | NIH/NLM clinical trials registry v2 |
| `us_fda_openfda` | openFDA | FDA adverse events, recalls, labels |

### Earth Science / Weather / Environment

| Plugin | Source | Description |
|---|---|---|
| `eu_copernicus` | Copernicus (EU) | European Earth observation and climate datasets |
| `global_open_meteo` | Open-Meteo | Weather forecast + historical + air quality |
| `us_noaa_ncei` | NOAA NCEI | Climate data access services (key-less) |
| `us_noaa_tides` | NOAA Tides & Currents | Water levels, tides, currents |
| `us_usgs_earthquake` | USGS Earthquakes | Real-time and historical seismic events |

### Biodiversity / Space / Physics

| Plugin | Source | Description |
|---|---|---|
| `cern_opendata` | CERN Open Data | Particle physics datasets and software |
| `global_gbif` | GBIF | Global biodiversity occurrence records |
| `global_inaturalist` | iNaturalist | Citizen-science species observations |
| `global_opensky` | OpenSky Network | Live ADS-B flight tracking |
| `us_nasa` | NASA | APOD, Near Earth Objects, Mars rover photos |

### Geo / Mapping / Knowledge

| Plugin | Source | Description |
|---|---|---|
| `global_osm_nominatim` | OSM Nominatim | Geocoding / reverse-geocoding (1 req/sec) |
| `global_overpass` | OSM Overpass | Query OpenStreetMap with Overpass QL |
| `global_wikidata` | Wikidata | Structured knowledge graph + SPARQL |
| `global_wikipedia` | Wikipedia | Article summaries, related, page views |
| `us_census_geocoder` | US Census Geocoder | Address ⇄ coordinates ⇄ geographies |

### Transit / Aviation

| Plugin | Source | Description |
|---|---|---|
| `ch_sbb` | Swiss Federal Railways | Swiss train disruptions and service data |
| `de_db` | Deutsche Bahn | German railway open data |
| `nl_ndov` | NDOV Loket | Dutch public transport data |
| `us_faa_nasstatus` | FAA NAS Status | US airspace status, delays, ground stops (XML) |
| `us_noaa_awc` | NOAA Aviation Weather | METAR, TAF, and station weather data |

### Scholarly Literature

| Plugin | Source | Description |
|---|---|---|
| `global_arxiv` | arXiv | Preprint metadata (Atom XML) |
| `global_crossref` | Crossref | DOI metadata, citations, journals |
| `global_europepmc` | Europe PMC | Biomedical literature + fulltext XML |
| `global_openalex` | OpenAlex | Open scholarly metadata |

### Culture / Books

| Plugin | Source | Description |
|---|---|---|
| `global_met_museum` | Met Museum | Met Museum Open Access (CC0) |
| `global_open_library` | Open Library | Books, authors, works (Internet Archive) |
| `global_unesco_heritage` | UNESCO World Heritage Sites | Natural, cultural & mixed World Heritage Sites |

### Networking / Internet

| Plugin | Source | Description |
|---|---|---|
| `global_bgpview` | BGPView | BGP routing data — ASN info, prefixes, peers (key-less) |
| `global_ripe_stat` | RIPE NCC RIPEstat | Production-grade BGP data (key-less) |

### Legal

| Plugin | Source | Description |
|---|---|---|
| `nl_rechtspraak` | Dutch Rechtspraak | Dutch court rulings and case law (ECLI) |
| `uk_legislation` | UK legislation.gov.uk | UK Acts, statutory instruments (XML/Atom) |
| `us_courtlistener` | CourtListener | US court opinions, dockets, judges (Free Law Project) |
| `us_federal_register` | US Federal Register | Daily rules, notices, executive orders |

## Optional environment variables

A few bundled plugins accept optional API keys for higher rate limits. Set these in your shell or in the Claude Desktop server config's `env` block:

| Variable | Plugin | Purpose |
|---|---|---|
| `COURTLISTENER_API_TOKEN` | `us_courtlistener` | Anonymous access works at low volumes |
| `OPENDATA_MCP_CONTACT` | all | Your email, used in User-Agent for polite-pool APIs (Crossref, OpenAlex, OSM, SEC EDGAR). Defaults to `opendata-mcp@example.org`. |

## Transports

`run` defaults to **SSE** (HTTP, port 8000) so you can connect from the MCP Inspector or remote clients. For Claude Desktop (which the `setup` command targets), the spawned process uses **stdio**:

```bash
uv run meta-data-mcp run                                  # SSE on 127.0.0.1:8000
uv run meta-data-mcp run --transport stdio                # stdio
uv run meta-data-mcp run --host 0.0.0.0 --port 3001       # SSE bound to all interfaces
```

## Contributing a new plugin

A "plugin" here is a Python module under `meta_data_mcp/providers/` plus an entry in `meta_data_mcp/registry.py`. The unified server picks it up automatically at startup. Plugins are *not* MCP servers — they expose a `TOOLS` list and a `TOOLS_HANDLERS` dict that the meta server merges into its own tool namespace.

### Setup

```bash
git clone https://github.com/derekslinz/meta-data-mcp.git
cd meta-data-mcp
uv venv && source .venv/bin/activate
uv sync
pre-commit install
```

### Quick path: use the provider generator

For most REST/JSON APIs you can scaffold a plugin in minutes instead of writing it from scratch.

1. Copy `tools/specs/example_weather_alert.yaml` and edit it to describe your API.
2. Dry-run to preview the generated files:
   ```bash
   uv run python tools/generate_provider.py tools/specs/{your_spec}.yaml --dry-run
   ```
3. Write the files:
   ```bash
   uv run python tools/generate_provider.py tools/specs/{your_spec}.yaml
   ```
4. Add a `ProviderEntry` to `meta_data_mcp/registry.py` so the discovery layer can find your plugin.
5. Run `uv run pytest`. The generated tests should pass on the first try if the spec matches the live API.

See **[tools/specs/README.md](tools/specs/README.md)** for the full YAML field reference and the cases the generator doesn't handle (auth headers, POST, multi-step logic) — those still need the manual path below.

### Manual path: write a plugin from scratch

1. **Create a new plugin module** under `meta_data_mcp/providers/`, using `{country_code}_{org}.py` naming (e.g. `ch_sbb.py`). Start from `meta_data_mcp/providers/__template__.py`.
2. **Use `http_get` from `meta_data_mcp.utils`** for all outbound HTTP. It sets the required User-Agent and handles the TTL cache.
3. **Declare your tools** by populating module-level `TOOLS: list[types.Tool]` and `TOOLS_HANDLERS: dict[str, Callable]`. Use Pydantic for parameter schemas and clear, action-oriented `description=` strings — the LLM relies on those.
4. **Add a `ProviderEntry`** to `meta_data_mcp/registry.py` with accurate `domains`, `regions`, and `keywords` so the routing layer can find your plugin.
5. **Add tests** in `tests/providers/test_{your_plugin}.py`. Mock HTTP at the `http_get` boundary; add a live test under `tests/live/` if the API is keyless and stable.
6. **Run `uv run pytest`** to verify.

## Roadmap

- Autonomous plugin generation: when `opendata-find-providers` doesn't match the user's query, automatically search the web for an appropriate open API, scaffold a new plugin via `generate_provider.py`, register it, and answer the original query — all in one round-trip.
- Public hosted deployment with SSE so non-Claude clients can use the server remotely.
- Multi-language SDK clients for the discovery tools so non-MCP integrations get the same routing benefits.


## Credits

- Originally conceived by [grll](https://github.com/grll) as `opendata-mcp`.
- Forked and reshaped around the single-server "meta-mcp" model.
- Built on [Anthropic's open-source MCP spec](https://spec.modelcontextprotocol.io/).


## License

MIT — see [LICENSE](LICENSE).
