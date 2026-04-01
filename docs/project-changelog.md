# Project Changelog

All notable changes to this project will be documented in this file.

## [2.0.0a0] - 2026-04-01

### Added
- Initial v2 alpha release of OpenDataMCP.
- Major version bump and preparatory changes for the 2.x line.
- See provider and API documentation for full details of v2 changes.
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
  - `nasa-get-ace-data`: ACE/DSCOVR Solar Wind real-time data.
  - *Hardened with explicit timeouts and error handling.*
- **Deutsche Bahn (DB) Transit Provider**: German rail connectivity using public API.
  - `db-list-stations`: Live station search and details.
  - `db-get-timetable`: Real-time departures and arrivals.
- **DOE ARM Provider (LASSO)**: Atmospheric science simulations.
  - `arm-search-lasso`: Discover LASSO data bundles.
- **Verification**: Dedicated unit test suite per provider in `tests/providers/`.
  - Added `test_de_db.py`, `test_us_nasa.py`, `test_us_doe_arm.py`.
  - Hardened `test_eu_copernicus.py`.

## [1.0.0] - 2024-11-20

### Added
- Initial release of OpenDataMCP.
- Providers: `ch_sbb`, `eu_eurostat`, `nl_cbs`, `nl_ndov`, `nl_tweedekamer`, `us_data_gov`.
- CLI tool for provider management and setup.
- MCP base infrastructure.
