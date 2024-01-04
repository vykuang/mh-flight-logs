# slim doesn't have curl
FROM python:3.11 as builder

ENV POETRY_VERSION=1.4.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_HOME=/etc/poetry \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# install poetry and add to PATH
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

FROM python:3.11-slim as runtime
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
# for :prod; otherwise mount during dev to avoid rebuilding
#COPY asean_flight_logs/main.py ./main.py
WORKDIR /app
VOLUME [ "/data", "/templates" ]
ENTRYPOINT [ "python", "main.py" ]
