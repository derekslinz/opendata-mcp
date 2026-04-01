# Open Data Model Context Protocol

![vc3598_Hyper-realistic_Swiss_landscape_pristine_SBB_red_train_p_40803c2e-43f5-410e-89aa-f6bdcb4cd089](https://github.com/user-attachments/assets/80c823dd-0b26-4d06-98f9-5c6d7c9103de)

<p align="center">
    <em>Connect Open Data to LLMs in minutes!</em>
</p>
<p align="center">
   <a href="https://github.com/derekslinz/opendata-mcp/actions/workflows/ci.yml" target="_blank">
    <img src="https://github.com/derekslinz/opendata-mcp/actions/workflows/ci.yml/badge.svg" alt="CI">
   </a>
   <a href="https://pypi.org/project/opendata-mcp" target="_blank">
       <img src="https://img.shields.io/pypi/v/opendata-mcp?color=%2334D058&label=pypi%20package" alt="Package version">
   </a>
   <a href="https://github.com/derekslinz/opendata-mcp/blob/main/LICENSE" target="_blank">
      <img src="https://img.shields.io/github/license/derekslinz/opendata-mcp.svg" alt="License">
   </a>
   <a href="https://pepy.tech/badge/opendata-mcp" target="_blank">
      <img src="https://pepy.tech/badge/opendata-mcp?cache-control=no-cache" alt="License">
   </a>
   <a href="https://github.com/derekslinz/opendata-mcp/stargazers" target="_blank">
      <img src="https://img.shields.io/github/stars/derekslinz/opendata-mcp.svg?cache-control=no-cache" alt="Stars">
   </a>
</p>

## See it in action

https://github.com/user-attachments/assets/760e1a16-add6-49a1-bf71-dfbb335e893e

We enable 2 things:

* **Open Data Access**: Access to many public datasets right from your LLM application (starting with Claude, more to come).
* **Publishing**: Get community help and a distribution network to distribute your Open Data. Get everyone to use it!

How do we do that?

* **Access**: Setup our MCP servers in your LLM application in 2 clicks via our CLI tool (starting with Claude, see Roadmap for next steps).
* **Publish**: Use provided templates and guidelines to quickly contribute and publish on Open Data MCP. Make your data easily discoverable!

## Available Providers

| Provider | Name | Description |
|---|---|---|
| `ch_sbb` | Swiss Federal Railways (SBB) | Train network disruptions and service data |
| `de_db` | Deutsche Bahn (DB) | German railway open data |
| `eu_copernicus` | Copernicus (EU) | European Earth observation and climate datasets |
| `eu_eurostat` | Eurostat | European Union statistics |
| `global_open_meteo` | Open-Meteo | Global open-source weather forecast data |
| `nl_cbs` | Statistics Netherlands (CBS) | Dutch statistical datasets (OData v2/v3) |
| `nl_ndov` | NDOV Loket | Dutch public transport data |
| `nl_tweedekamer` | Tweede Kamer | Dutch Parliament open data |
| `us_data_gov` | Data.gov | US federal government open datasets |
| `us_doe_arm` | DOE ARM | US Dept of Energy atmospheric radiation data |
| `us_nasa` | NASA | Astronomy, near-Earth objects, Mars rover photos |

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

##### Overview

For local development and testing, use **`uv run opendata-mcp`**:

```bash
# show available commands
uv run opendata-mcp 

# show available providers
uv run opendata-mcp list

# show info about a provider
uv run opendata-mcp info $PROVIDER_NAME

# setup a provider's MCP server on your Claude Desktop app
uv run opendata-mcp setup $PROVIDER_NAME

# remove a provider's MCP server from your Claude Desktop app
uv run opendata-mcp remove $PROVIDER_NAME
```

Quickstart for the Switzerland SBB (train company) provider:

```bash
# make sure claude is installed
uv run opendata-mcp setup ch_sbb
```

Restart Claude and you should see a new hammer icon at the bottom right of the chat.

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

#### Publishing Instructions

1. **Create a New Provider Module**

   * Each data source needs its own python module.
   * Create a new Python module in `opendata_mcp/providers/`.
   * Use a descriptive name following the pattern: `{country_code}_{organization}.py` (e.g., `ch_sbb.py`).
   * Start with our [template file](https://github.com/derekslinz/opendata-mcp/blob/main/opendata_mcp/providers/__template__.py) as your base.
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
