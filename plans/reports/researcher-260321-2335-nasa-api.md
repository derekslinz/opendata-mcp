# Research Report: NASA Open Data API

**Type**: researcher
**Date**: 260321
**Topic**: NASA API Integration

## Overview
NASA provides extensive open data through `api.nasa.gov`. Most endpoints are accessible via a `DEMO_KEY` (30 req/hr, 50 req/day).

## Selected Endpoints
1. **APOD (Astronomy Picture of the Day)**: Daily image and explanation.
2. **NeoWs (Near Earth Object Web Service)**: Asteroid tracking data.
3. **Mars Rover Photos**: Image archives from Curiosity, Opportunity, and Spirit.

## Technical Details
- Base URL: `https://api.nasa.gov`
- Auth: `api_key=DEMO_KEY` (Default)
- Documentation: [api.nasa.gov](https://api.nasa.gov/)
