#! /usr/bin/env sh
# Usage: run.sh
PROJ_DIR=~/projects/mh-flight-logs
docker compose -f docker-compose.yml -f compose.prod.yml --project-directory=$PROJ_DIR up airline-2
exit_code=$?
docker compose --project-directory=$PROJ_DIR down
exit $exit_code
