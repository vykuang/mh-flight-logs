#! /usr/bin/env sh
docker run \
    --rm \
    --env-file .env \
    --mount type=bind,source="$(pwd)/data",target="/data" \
    --mount type=bind,source="$(pwd)/asean_flight_logs/main.py",target="/app/main.py" \
    asean-flight-logs:dev --arrival_date 2023-09-24 --local_json --local_tweet --loglevel debug