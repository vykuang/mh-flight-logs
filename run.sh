#! /usr/bin/env sh
# Usage: run.sh 

docker compose up
exit_code=$?
docker compose down
exit $exit_code
