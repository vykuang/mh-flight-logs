#! /usr/bin/env sh
docker run \
    --env-file .env \
    --mount type=bind,source="$(pwd)/data",target="/app/data" \
    asean-flight-logs:v0