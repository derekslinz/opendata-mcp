# meta-data-mcp server is a meta model context protocol server 

The (meta)-data-mcp is an mmcp server: it acts as an intelligent gateway to an ever-growing library of open data sources, keeping track of vast lakes of data so you don't have to. 

Never heard of an mmcp before? Don't feel bad, I made it up while writing this just now. Originally this was the opendata-mcp—but as the sources grew from one to dozens and more, the tools available quickly exceeded 300, and the list of installed sources was just ridiculous.

So I decided to take a hard left, rename the project, and focus on the tricky part. There's an absurd amount of data available --finding data isn't the hard part, it's finding the data that you need, when you need it. 

To illustrate the point: I love the overpass API from [OpenStreetMap](https://wiki.openstreetmap.org/wiki/Overpass_API) --I've spent hours playing with it...but I've never once used it for any actual purpose. Finding the tool that you need is hard enough, finding it when you need it is magical.

This project aims to be magical.

## Available Providers

> [!IMPORTANT]
> **Start Here: The Meta Provider (`meta_data_mcp`)**
>
> With 59 data providers available, loading all of them into your LLM at once would overwhelm its context window. Instead, **we strongly recommend installing only the Meta Provider first**. 
>
> It acts as a search engine and discovery gateway, equipped with pre-populated Prompts and specialized Tools (`find-providers`, `explain-choice`, `list-domains`, `list-regions`, `describe-provider`, `list-providers`) that allow your LLM to dynamically discover the exact dataset it needs and instruct you on how to install it.
>
> **Install it now:**
> ```bash
> uv run meta-data-mcp setup meta_data_mcp
> ```
<img width="1779" height="1092" alt="Screenshot 2026-05-11 at 21 50 39" src="https://github.com/user-attachments/assets/6173d926-769a-4fc8-bf4a-07669033719b" />

### Meta / Discovery

| Provider | Name | Description |
|---|---|---|
| `meta_data_mcp` | OpenData MCP Meta | Aggregator: `find-providers`, `explain-choice`, `list-domains`, `list-regions`, `describe-provider`, `list-providers`. Set this up FIRST; it tells the LLM which other providers to install. |

### Government / Civic

| Provider | Name | Description |
|---|---|---|
| `au_data_gov` | Australian Government Open Data | CKAN catalog at data.gov.au |
| `ca_open_gov` | Canada Open Data | CKAN catalog at open.canada.ca |
| `fr_data_gouv` | data.gouv.fr | French government open data platform |
| `nl_tweedekamer` | Tweede Kamer | Dutch Parliament open data |
| `sg_data_gov` | Singapore Open Data | data.gov.sg datasets and collections |
| `uk_gov` | data.gov.uk | UK government CKAN catalog |
| `us_data_gov` | Data.gov | US federal government open datasets |

### Statistics / Economics

| Provider | Name | Description |
|---|---|---|
| `eu_eurostat` | Eurostat | European Union statistics |
| `global_imf` | International Monetary Fund | IMF SDMX 2.1 statistical data |
| `global_dbnomics` | DBnomics | Global economic data aggregator (IMF, World Bank, etc.) |
| `global_oecd` | OECD | OECD economic & social statistics (SDMX) |
| `global_world_bank` | World Bank | Development indicators by country |
| `nl_cbs` | Statistics Netherlands (CBS) | Dutch statistical datasets (OData v2/v3) |
| `uk_ons` | UK ONS | UK Office for National Statistics |


### Finance / Markets

| Provider | Name | Description |
|---|---|---|
| `eu_ecb` | European Central Bank | ECB data portal (SDMX) — FX, monetary, banking |
| `global_coingecko` | CoinGecko | Cryptocurrency market data |
| `global_frankfurter` | Frankfurter | ECB reference FX rates (key-less) |
| `us_sec_edgar` | SEC EDGAR | Public company filings, XBRL financials |
| `us_treasury_fiscal` | US Treasury Fiscal Data | Federal debt, daily Treasury statement, FX rates |

### Health & Life Sciences

| Provider | Name | Description |
|---|---|---|
| `global_disease_sh` | disease.sh | COVID-19, influenza, vaccine aggregator |
| `global_pubchem` | NCBI PubChem | Chemical compounds and substances |
| `global_rcsb_pdb` | RCSB PDB | 3D protein and macromolecular structures |
| `global_who_gho` | WHO GHO | WHO Global Health Observatory (OData) |
| `us_cdc_socrata` | US CDC | CDC open data via Socrata |
| `us_clinicaltrials` | ClinicalTrials.gov | NIH/NLM clinical trials registry v2 |
| `us_fda_openfda` | openFDA | FDA adverse events, recalls, labels |

### Earth Science / Weather / Environment

| Provider | Name | Description |
|---|---|---|
| `eu_copernicus` | Copernicus (EU) | European Earth observation and climate datasets |
| `global_open_meteo` | Open-Meteo | Weather forecast + historical + air quality |
| `us_noaa_ncei` | NOAA NCEI | Climate data access services (key-less) |
| `us_noaa_tides` | NOAA Tides & Currents | Water levels, tides, currents |
| `us_usgs_earthquake` | USGS Earthquakes | Real-time and historical seismic events |

### Biodiversity / Space / Physics

| Provider | Name | Description |
|---|---|---|
| `cern_opendata` | CERN Open Data | Particle physics datasets and software |
| `global_gbif` | GBIF | Global biodiversity occurrence records |
| `global_inaturalist` | iNaturalist | Citizen-science species observations |
| `global_opensky` | OpenSky Network | Live ADS-B flight tracking |
| `us_nasa` | NASA | APOD, Near Earth Objects, Mars rover photos |

### Geo / Mapping / Knowledge

| Provider | Name | Description |
|---|---|---|
| `global_osm_nominatim` | OSM Nominatim | Geocoding / reverse-geocoding (1 req/sec) |
| `global_overpass` | OSM Overpass | Query OpenStreetMap with Overpass QL |
| `global_wikidata` | Wikidata | Structured knowledge graph + SPARQL |
| `global_wikipedia` | Wikipedia | Article summaries, related, page views |
| `us_census_geocoder` | US Census Geocoder | Address ⇄ coordinates ⇄ geographies |

### Transit / Aviation

| Provider | Name | Description |
|---|---|---|
| `ch_sbb` | Swiss Federal Railways | Swiss train disruptions and service data |
| `de_db` | Deutsche Bahn | German railway open data |
| `nl_ndov` | NDOV Loket | Dutch public transport data |
| `us_faa_nasstatus` | FAA NAS Status | US airspace status, delays, ground stops (XML) |
| `us_noaa_awc` | NOAA Aviation Weather | METAR, TAF, and station weather data |

### Scholarly Literature

| Provider | Name | Description |
|---|---|---|
| `global_arxiv` | arXiv | Preprint metadata (Atom XML) |
| `global_crossref` | Crossref | DOI metadata, citations, journals |
| `global_europepmc` | Europe PMC | Biomedical literature + fulltext XML |
| `global_openalex` | OpenAlex | Open scholarly metadata |

### Culture / Books

| Provider | Name | Description |
|---|---|---|
| `global_met_museum` | Met Museum | Met Museum Open Access (CC0) |
| `global_open_library` | Open Library | Books, authors, works (Internet Archive) |
| `global_unesco_heritage` | UNESCO World Heritage Sites | Natural, cultural & mixed World Heritage Sites (WHC API) |


### Networking / Internet

| Provider | Name | Description |
|---|---|---|
| `global_bgpview` | BGPView | BGP routing data — ASN info, prefixes, peers, upstreams, downstreams (key-less) |
| `global_ripe_stat` | RIPE NCC RIPEstat | Production-grade BGP data — prefix overview, routing history, geolocation (key-less) |

### Legal

| Provider | Name | Description |
|---|---|---|
| `nl_rechtspraak` | Dutch Rechtspraak | Dutch court rulings and case law (ECLI) |
| `uk_legislation` | UK legislation.gov.uk | UK Acts, statutory instruments (XML/Atom) |
| `us_courtlistener` | CourtListener | US court opinions, dockets, judges (Free Law Project) |
| `us_federal_register` | US Federal Register | Daily rules, notices, executive orders |

### Environment variables

A few providers accept optional API keys for higher rate limits. Set these in your shell or in the Claude Desktop server config's `env` block:

| Variable | Provider | Purpose |
|---|---|---|
| `COURTLISTENER_API_TOKEN` | `us_courtlistener` | Optional — anonymous access works at low volumes |
| `OPENDATA_MCP_CONTACT` | all providers | Optional — your email, used in User-Agent for polite-pool APIs (Crossref, OpenAlex, OSM, SEC EDGAR). Defaults to `opendata-mcp@example.org`. |

## Usage

### Access: Access Open Data using Open Data MCP CLI Tool

#### Prerequisites

If you want to use Open Data MCP with Claude Desktop app client you need to install the [Claude Desktop app](https://claude.ai/download).

You will also need `uv` to easily run our CLI and MCP servers.

##### macOS

```bash
# you need to install uv through homebrew as using the install shell script 
# will install it locally to your user which make it unavailable in the Claude Desktop app context.
brew install uv
```

##### Windows

```bash
# (UNTESTED)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### The "Install Meta + Run Everything" Pattern

With 59 providers available, loading all of them into your LLM at once would overwhelm its context window. Instead, we recommend this workflow:

1. **Install Meta**: Set up the meta-aggregator provider FIRST.
   ```bash
   uv run meta-data-mcp setup meta_data_mcp
   ```
2. **Restart Client**: Restart your Claude Desktop app so it can access the meta tools and prompts shown in the client.
3. **Use the Prompts**: In the Claude Desktop app, click the attachment/prompt icon and select one of the pre-populated **Meta Prompts** (like "Financial & Economic Research" or "Climate & Environment Dashboard"). This will automatically inject the perfect instructions for Claude to discover the best datasets for your use-case.
4. **Run Everything**: If Claude needs another provider to complete your request, it will use the meta tools (`opendata-find-providers`) to discover it, and then instruct you to run `uv run meta-data-mcp setup <provider_name>`. 

> [!TIP]
> **For developers building multi-agent systems:** Check out the `system_prompt.md` file for a highly optimized system prompt you can give to your orchestrator agent to enforce this exact pattern.

##### Overview

For local development and testing, use **`uv run meta-data-mcp`**:

```bash
# show available commands
uv run meta-data-mcp 

# show available providers
uv run meta-data-mcp list

# show info about a provider
uv run meta-data-mcp info $PROVIDER_NAME

# setup a provider's MCP server on your Claude Desktop app
uv run meta-data-mcp setup $PROVIDER_NAME

# remove a provider's MCP server from your Claude Desktop app
uv run meta-data-mcp remove $PROVIDER_NAME
```

> [!WARNING]
> **Individual provider setup is deprecated.**
> Setting up 55+ providers one by one (`setup ch_sbb`, `setup us_nasa`, …) is no longer
> recommended. Use the two-command setup below instead — it gives Claude both discovery and
> data access through a single pair of servers. Any existing individual provider entries are
> automatically removed the next time you run `setup`, `setup-all`, or `cleanup`.
>
> **Recommended setup (new):**
> ```bash
> uv run meta-data-mcp setup-all       # installs meta + aggregator, removes legacy entries
> # — or equivalently —
> uv run meta-data-mcp setup meta_data_mcp
> ```
>
> **Migrate existing config:**
> ```bash
> uv run meta-data-mcp cleanup          # preview what will be removed
> uv run meta-data-mcp cleanup --apply  # remove legacy entries and install meta + aggregator
> ```

Quickstart for the Switzerland SBB (train company) provider:

```bash
# make sure claude is installed
uv run meta-data-mcp setup ch_sbb
```

Restart Claude and you should see a new hammer icon at the bottom right of the chat.

#### Alternative Transports (SSE)

By default, the `run` command uses the **SSE (HTTP)** transport. This launches an HTTP server suitable for remote connections or browser-based tools like the MCP Inspector.

```bash
# start the server using default SSE transport on port 8000
uv run meta-data-mcp run ch_sbb

# specify host and port
uv run meta-data-mcp run ch_sbb --host 0.0.0.0 --port 3001
```

If you need to run a provider via **stdio** (standard input/output), use the `--transport stdio` flag:

```bash
uv run meta-data-mcp run ch_sbb --transport stdio
```

You can now ask questions to Claude about SBB train network disruption and it will answer based on data collected on `data.sbb.ch`.

### `<u>`Publish`</u>`: Contribute by building and publishing public datasets

#### Prerequisites

1. **Install UV Package Manager**

   ```bash
   # macOS
   brew install uv

   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

   # Linux/WSL
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. **Clone & Setup Repository**

   ```bash
   # Clone the repository
   git clone https://github.com/derekslinz/opendata-mcp.git
   cd opendata-mcp

   # Create and activate virtual environment
   uv venv
   source .venv/bin/activate  # Unix/macOS
   # or
   .venv\Scripts\activate     # Windows

   # Install dependencies
   uv sync
   ```
3. **Install Pre-commit Hooks**

   ```bash
   # Install pre-commit hooks for code quality
   pre-commit install
   ```

#### Quick path: use the provider generator

For most REST/JSON APIs you can scaffold a provider in minutes instead of writing code from scratch.

1. Create a YAML spec describing your API in `tools/specs/{id}.yaml` (copy `tools/specs/example_weather_alert.yaml` as a starting point).
2. Preview the generated code — no files written:
   ```bash
   uv run python tools/generate_provider.py tools/specs/{id}.yaml --dry-run
   ```
3. Write the files:
   ```bash
   uv run python tools/generate_provider.py tools/specs/{id}.yaml
   ```
4. Add a `ProviderEntry` to `opendata_mcp/registry.py` so the meta-aggregator can discover your provider.
5. Refine the generated files and run `uv run pytest`.

See **[tools/specs/README.md](tools/specs/README.md)** for the full YAML field reference and a list of cases the generator doesn't handle (auth headers, POST, multi-step logic, etc.) — those require the manual path below.

#### Manual path: write a provider from scratch

1. **Create a New Provider Module**

   * Each data source needs its own python module.
   * Create a new Python module in `opendata_mcp/providers/`.
   * Use a descriptive name following the pattern: `{country_code}_{organization}.py` (e.g., `ch_sbb.py`).
   * Start with our [template file](https://github.com/derekslinz/meta-data-mcp/blob/main/opendata_mcp/providers/__template__.py) as your base.
   * Use `http_get` from `opendata_mcp.utils` for all outbound requests (sets the required User-Agent automatically).
2. **Implement Required Components**

   * Define your Tools & Resources following the template structure
   * Each Tool or Resource should have:
     - Clear description of its purpose
     - Well-defined input/output schemas using Pydantic models
     - Proper error handling
     - Documentation strings
3. **Tool vs Resource**

   * Choose **Tool** implementation if your data needs:
     - Active querying or computation
     - Parameter-based filtering
     - Complex transformations
   * Choose **Resource** implementation if your data is:
     - Static or rarely changing
     - Small enough to be loaded into memory
     - Simple file-based content
     - Reference documentation or lookup tables
   * Reference the [MCP documentation](https://github.com/modelcontextprotocol/python-sdk?tab=readme-ov-file#primitives) for guidance
4. **Testing**

   * Add tests in the `tests/` directory
   * Follow existing test patterns (see other provider tests)
   * Required test coverage:
     - Basic functionality
     - Edge cases
     - Error handling
5. **Validation**

   * Test your MCP server using our experimental client: `uv run opendata_mcp/client.py`
   * Verify all endpoints respond correctly
   * Ensure error messages are helpful
   * Check performance with typical query loads

For other examples, check our existing providers in the `opendata_mcp/providers/` directory.

## Contributing

We have an ambitious roadmap and we want this project to scale with the community. The ultimate goal is to make the millions of datasets publicly available to all LLM applications.

For that we need your help!

### Discord

We want to build a helping community around the challenge of bringing open data to LLM's. Join us on discord to start chatting: [https://discord.gg/QPFFZWKW](https://discord.gg/hDg4ZExjGs)

### Our Core Guidelines

Because of our target scale we want to keep things simple and pragmatic at first. Tackle issues with the community as they come along.

1. **Simplicity and Maintainability**

   * Minimize abstractions to keep codebase simple and scalable
   * Focus on clear, straightforward implementations
   * Avoid unnecessary complexity
2. **Standardization / Templates**

   * Follow provided templates and guidelines consistently
   * Maintain uniform structure across providers
   * Use common patterns for similar functionality
3. **Dependencies**

   * Keep external dependencies to a minimum
   * Prioritize single repository/package setup
   * Carefully evaluate necessity of new dependencies
4. **Code Quality**

   * Format code using ruff
   * Maintain comprehensive test coverage with pytest
   * Follow consistent code style
5. **Type Safety**

   * Use Python type hints throughout
   * Leverage Pydantic models for API request/response validation
   * Ensure type safety in data handling

### Tactical Topics (our current priorities)

* [X] Initialize repository with guidelines, testing framework, and contribution workflow
* [X] Implement CI/CD pipeline with automated PyPI releases
* [X] Develop provider template and first reference implementation
* [X] **Implement and harden NASA, Copernicus, and DB providers**
* [ ] Integrate additional open datasets (actively seeking contributors)
* [ ] Establish clear guidelines for choosing between Resources and Tools
* [ ] Develop scalable repository architecture for long-term growth
* [ ] Expand MCP SDK parameter support (authentication, rate limiting, etc.)
* [ ] Implement additional MCP protocol features (prompts, resource templates)
* [ ] Add support for alternative transport protocols beyond stdio (SSE)
* [ ] Deploy hosted MCP servers for improved accessibility

## Roadmap

Let’s build the open source infrastructure that will allow all LLMs to access all Open Data together!

### Access:

* Make Open Data available to all LLM applications (beyond Claude)
* Make Open Data data sources searchable in a scalable way
* Make Open Data available through MCP remotely (SSE) with publicly sponsored infrastructure

### Publish:

* Build the many Open Data MCP servers to make all the Open Data truly accessible (we need you!).
* On our side we are starting to build MCP servers for Switzerland ~12k open dataset!
* Make it even easier to build Open Data MCP servers

We are very early, and lack of dataset available is currently the bottleneck. Help yourself! Create your Open Data MCP server and get users to use it as well from their LLMs applications. Let’s connect LLMs to the millions of open datasets from governments, public entities, companies and NGOs!

As Anthropic's MCP evolves we will adapt and upgrade Open Data MCP.

## Limitations

* All data served by Open Data MCP servers should be Open.
* Please oblige to the data licenses of the data providers.
* Our License must be quoted in commercial applications.

## References

* This project was originally conceived by [grll](https://github.com/grll).
* Kudos to [Anthropic's open source MCP](https://spec.modelcontextprotocol.io/) release enabling initiative like this one.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
