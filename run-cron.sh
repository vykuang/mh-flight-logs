#! /usr/bin/env sh
# Usage: run.sh 
PROJ_DIR=~/projects/mh-flight-logs
docker compose --project-directory=$PROJ_DIR up
exit_code=$?
docker compose --project-directory=$PROJ_DIR down
exit $exit_code
