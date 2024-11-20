#!/bin/sh
touch .env.local
docker compose --progress plain up -d app --build
docker compose logs --tail=25 -f
