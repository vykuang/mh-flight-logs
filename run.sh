#! /usr/bin/env sh
# Usage: docker-up.sh 

docker compose up
exit_code=$?
docker compose down
exit $exit_code
