#!/bin/bash
# Setup script for NYCDB Morphing GUI with live data

echo "Starting NYCDB database..."
cd /workspaces/nycdb
docker-compose up -d

echo "Waiting for database to be ready..."
sleep 10

echo "Loading some sample data (HPD violations)..."
docker-compose run --rm nycdb --download hpd_violations
docker-compose run --rm nycdb --load hpd_violations

echo "Starting GUI server with live database connection..."
export DATABASE_URL="postgresql://nycdb:nycdb@localhost:5432/nycdb"
cd src/nycdb/morphing_gui
python3 server.py