#!/bin/sh
touch .env.local
export PROJECT="${1:-test}-$(basename $PWD)"
docker compose -f docker-compose.yml -f docker-compose.test.yml --progress plain -p $PROJECT up app --build --exit-code-from app
docker compose --progress plain -p $PROJECT down