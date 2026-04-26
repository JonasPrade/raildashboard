# docker/db/Dockerfile
# Extends postgis/postgis with pgRouting, which the backend routing microservice requires.
# The PostgreSQL apt repository is already configured in the base image, so the package
# is available without additional source setup.

FROM imresamu/postgis:16-3.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-pgrouting \
    && rm -rf /var/lib/apt/lists/*
