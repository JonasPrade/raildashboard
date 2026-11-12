# docker/db/Dockerfile
# Extends postgis/postgis with pgRouting, which the backend routing microservice requires.
# The PostgreSQL apt repository is already configured in the base image, so the package
# is available without additional source setup.

FROM imresamu/postgis:16-3.4

# postgresql-16 is installed together with pgRouting: the current pgRouting package
# requires a newer PostgreSQL 16 minor release than the base image ships (#366). A
# minor update keeps the on-disk format, so existing data directories stay valid.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16 postgresql-16-pgrouting \
    && rm -rf /var/lib/apt/lists/*

# Pre-migration backup, run by the one-shot `backup` service in compose.yaml with
# this image's own pg_dump (same major version as the server).
COPY backup.sh /usr/local/bin/backup-before-migrate
