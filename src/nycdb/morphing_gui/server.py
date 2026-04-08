#!/usr/bin/env python3
"""Local demo server for the morphing GUI.

Serves static files and provides /api/analyze?building=<id>.
If DATABASE_URL is configured and nycdb tables are available, the endpoint uses
real query counts from selected agencies. Otherwise it falls back to deterministic
simulated scores.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

AGENCIES: list[dict[str, Any]] = [
    {"id": "DOB", "signal": "Permits, violations, job filings", "base": 48},
    {"id": "HPD", "signal": "Complaints, registrations, vacate activity", "base": 57},
    {"id": "DOF", "signal": "Sales, valuations, exemptions, tax lien", "base": 41},
    {"id": "OATH", "signal": "Hearings and enforcement outcomes", "base": 35},
    {"id": "DHS", "signal": "Shelter pressure in nearby catchments", "base": 29},
    {"id": "DOHMH", "signal": "Rodent and public health indicators", "base": 33},
    {"id": "DCP", "signal": "Land use and district context", "base": 39},
    {"id": "OCA", "signal": "Housing court patterns and filings", "base": 45},
]


@dataclass
class QueryResult:
    agency: str
    score: int
    signal: str
    source: str


def _clamp(value: float, low: int, high: int) -> int:
    return max(low, min(high, int(round(value))))


def _sim_score(base: int, building: str, idx: int) -> int:
    seed = len(building) * (idx + 2.17) + idx * 11.19
    jitter = math.sin(seed) * 14 + math.cos(seed / 2.3) * 9
    return _clamp(base + jitter, 8, 98)


def _build_simulated(building: str) -> list[QueryResult]:
    return [
        QueryResult(
            agency=agency["id"],
            score=_sim_score(agency["base"], building, idx),
            signal=agency["signal"],
            source="simulated",
        )
        for idx, agency in enumerate(AGENCIES)
    ]


def _build_live(building: str) -> list[QueryResult] | None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return None

    try:
        import psycopg
    except Exception:
        return None

    building_key = building.strip().lower()
    if not building_key:
        return None

    queries: list[tuple[str, str, str]] = [
        ("DOB", "Permits, violations, job filings", "select count(*) from dob_violations where lower(bbl::text) = %s"),
        ("HPD", "Complaints, registrations, vacate activity", "select count(*) from hpd_violations where lower(bbl::text) = %s"),
        ("DOF", "Sales, valuations, exemptions, tax lien", "select count(*) from dof_sales where lower(bbl::text) = %s"),
        ("OATH", "Hearings and enforcement outcomes", "select count(*) from oath_hearings where lower(bbl::text) = %s"),
        ("DHS", "Shelter pressure in nearby catchments", "select 0"),
        ("DOHMH", "Rodent and public health indicators", "select count(*) from dohmh_rodent_inspections where lower(bbl::text) = %s"),
        ("DCP", "Land use and district context", "select count(*) from pluto_latest where lower(bbl::text) = %s"),
        ("OCA", "Housing court patterns and filings", "select count(*) from oca where lower(bbl::text) = %s"),
    ]

    rows: list[QueryResult] = []
    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                for idx, (agency, signal, sql) in enumerate(queries):
                    params = None if "%s" not in sql else (building_key,)
                    cur.execute(sql, params)
                    count = int(cur.fetchone()[0])
                    # Smooth log-ish mapping of count to score, with base contribution.
                    base = AGENCIES[idx]["base"]
                    score = _clamp(base + math.log1p(count) * 12, 5, 99)
                    rows.append(QueryResult(agency, score, signal, "database"))
        return rows
    except Exception:
        return None


def analyze_building(building: str) -> dict[str, Any]:
    live_rows = _build_live(building)
    rows = live_rows if live_rows else _build_simulated(building)
    avg = round(sum(row.score for row in rows) / len(rows))

    return {
        "building": building,
        "mode": "database" if live_rows else "simulated",
        "agencies": [
            {
                "id": row.agency,
                "score": row.score,
                "signal": row.signal,
                "source": row.source,
            }
            for row in rows
        ],
        "distress": "Low" if avg < 45 else "Elevated" if avg < 68 else "High",
        "risk_index": avg,
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/analyze":
            params = parse_qs(parsed.query)
            building = (params.get("building") or [""])[0].strip()
            if not building:
                return self._send_json({"error": "building query param is required"}, HTTPStatus.BAD_REQUEST)
            payload = analyze_building(building)
            return self._send_json(payload)
        return super().do_GET()

    def _send_json(self, payload: dict[str, Any], code: int = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    host = os.getenv("MORPH_GUI_HOST", "0.0.0.0")
    port = int(os.getenv("MORPH_GUI_PORT", "8080"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Morphing GUI server listening on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
