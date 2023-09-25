#! /usr/bin/env sh
docker run \
    --rm \
    --env-file .env \
    --mount type=bind,source="$(pwd)/data",target="/data" \
    --mount type=bind,source="$(pwd)/asean_flight_logs/main.py",target="/app/main.py" \
    asean-flight-logs:dev /app/main.py --loglevel debug --use_local