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
- [ ] Implement APOD tool.
- [ ] Implement NeoWs (Asteroid) tool.
- [ ] Implement Mars Rover Photos tool.
- [ ] Implement Space Weather (ACE Solar Wind) tool.

## DB Transit Provider (`de_db.py`)
- [ ] Implement Station Search tool.
- [ ] Implement Arrivals/Departures tool.

## Verification
- Unit tests for both.
- CLI discovery verification.
