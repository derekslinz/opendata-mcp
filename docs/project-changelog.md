# Project Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2026-03-21

### Added
- **Copernicus EO Provider**: Substantial integration for Earth Observation data.
  - `copernicus-list-collections`: STAC collection discovery.
  - `copernicus-search-products`: STAC search with bbox/datetime.
  - `copernicus-get-product-metadata`: OData detailed technical metadata.
  - Unit tests in `tests/providers/test_eu_copernicus.py`.
- **Open-Meteo Weather Provider**: Global weather data integration.
  - `weather-get-forecast`: Current and upcoming forecasts.
  - `weather-get-historical`: 80+ years of historical data.
  - `weather-get-air-quality`: PM2.5, NO2, O3, etc.
  - Unit tests in `tests/providers/test_global_open_meteo.py`.
- **NASA Provider**: Astronomy and planetary science data.
  - `nasa-get-apod`: Astronomy Picture of the Day.
  - `nasa-get-asteroids`: NeoWs asteroid tracking.
  - `nasa-get-mars-photos`: Photos from Curiosity, Opportunity, and Spirit.
  - `nasa-get-ace-data`: ACE Solar Wind science data.
- **Deutsche Bahn (DB) Transit Provider**: German rail connectivity.
  - `db-list-stations`: Station search and details.
- **DOE ARM Provider (LASSO)**: Atmospheric science simulations.
  - `arm-search-lasso`: Discover LASSO data bundles.
- **Verification**: New unit test suite in `tests/providers/test_new_scientific_providers.py`.

## [1.0.0] - 2024-11-20

### Added
- Initial release of OpenDataMCP.
- Providers: `ch_sbb`, `eu_eurostat`, `nl_cbs`, `nl_ndov`, `nl_tweedekamer`, `us_data_gov`.
- CLI tool for provider management and setup.
- MCP base infrastructure.
