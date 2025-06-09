#! /bin/sh
# Build
docker network create grammar-network
docker compose --compatibility -f docker-compose.yaml up -d --build --force-recreate --remove-orphans
