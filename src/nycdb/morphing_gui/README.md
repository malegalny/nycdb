# Morphing Building Intelligence GUI

This front-end provides a modern, dynamic building analysis UI that now calls a local API endpoint (`/api/analyze`) for live responses.

## What this app does

- Morphing visual profile that changes with computed building risk.
- Cross-agency cards (DOB, HPD, DOF, OATH, DHS, DOHMH, DCP, OCA).
- Inference timeline showing progressive fusion per agency.
- API-backed analysis mode:
  - **database** mode when `DATABASE_URL` is set and queries succeed.
  - **simulated** mode fallback when a live database is unavailable.

## Run locally

From the repository root:

```bash
cd src/nycdb/morphing_gui
python3 server.py
```

Then open:

- <http://127.0.0.1:8080>

## API

```bash
curl "http://127.0.0.1:8080/api/analyze?building=1002610089"
```

Response fields include `mode`, `agencies[]`, `distress`, and `risk_index`.

## Optional live data mode

If you have a reachable nycdb Postgres instance, export a connection URL before starting the server:

```bash
export DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/DBNAME'
python3 server.py
```

If referenced tables are unavailable, the API automatically falls back to simulated mode.
