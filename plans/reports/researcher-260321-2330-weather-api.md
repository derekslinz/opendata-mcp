# Research Report: Weather Provider (Open-Meteo)

**Type**: researcher
**Date**: 260321
**Topic**: Open-Meteo API

## Overview
Open-Meteo offers an open-source weather API that aggregates data from national meteorological services (NOAA, DWD, MeteoFrance, ECMWF, etc.). It is free for non-commercial use and requires no API key.

## Key Features
- **Global Coverage**: High-resolution models for most regions.
- **Official Sources**: Aggregates data from ECMWF (European Centre for Medium-Range Weather Forecasts), NOAA, DWD, and more.
- **Forecasts**: Hourly/daily forecasts for temperature, precipitation, wind, etc.
- **Historical Data**: Access to 80+ years of weather history.
- **No Key Required**: Perfectly aligns with the "Open Data" ease-of-use principle.

## Recommended Tools
1. `get-forecast`: Current and upcoming weather for a lat/lon.
2. `get-historical-weather`: Past weather conditions.
3. `get-air-quality`: Ozone, PM2.5, etc.

## Technical Details
- Endpoint: `https://api.open-meteo.com/v1/forecast`
- Documentation: [open-meteo.com](https://open-meteo.com/)
