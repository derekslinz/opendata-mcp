---
title: Implement NASA and DB Transit Providers
description: Expand the OpenDataMCP ecosystem with NASA (Space) and Deutsche Bahn (German Rail) data.
status: in-progress
priority: High
effort: High
branch: feat/nasa-db-integration
tags: [nasa, transit, db, open-data]
created: 2026-03-21
---

# Plan: NASA & DB Integration

## NASA Provider (`us_nasa.py`)
- [x] Implement APOD tool.
- [x] Implement NeoWs (Asteroid) tool.
- [x] Implement Mars Rover Photos tool.
- [x] Implement Space Weather (ACE Solar Wind) tool.

## DB Transit Provider (`de_db.py`)
- [x] Implement Station Search tool.
- [x] Implement Arrivals/Departures tool.

## Verification
- [x] Unit tests for both.
- [x] CLI discovery verification.
