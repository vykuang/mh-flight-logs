#! /usr/bin/env sh
docker run \
    --rm \
    --env-file .env \
    --mount type=bind,source="$(pwd)/data",target="/data" \
    --mount type=bind,source="$(pwd)/templates",target="/templates" \
    --mount type=bind,source="$(pwd)/asean_flight_logs/main.py",target="/app/main.py" \
    --mount type-bind,source="$(pwd)/pyproject.toml",target="/app/pyproject.toml" \
    asean-flight-logs:dev \
        --arrival_date 2023-10-23 \
        --data_dir /data \
        --template_dir /templates \
        --local_json --local_tweet --loglevel debug
