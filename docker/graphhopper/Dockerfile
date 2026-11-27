# Stage 1: Build OpenRailRouting JAR from source (v1.1, GraphHopper 11.0), with the
# dashboard's extension for proposed tracks and tracks under construction:
#   orr/planned-tracks.patch  changes to existing OpenRailRouting files
#   orr/overlay/              new files (encoded value railway_status, its parser, tests)
# See docs/features/feature-routing.md → "Geplante und im Bau befindliche Gleise aus OSM".
FROM node:20-slim AS node
# Statically linked (musl): the runtime stage copies the binary on its own.
FROM busybox:1.37.0-musl AS busybox

FROM maven:3-eclipse-temurin-17 AS builder

# No apt in the stages `make test` builds: archive.ubuntu.com was slow enough from
# GitHub's runners to hold two runs (#372, #373) at the 30-minute job limit. The
# maven image already ships git and curl; node and npm (OpenRailRouting's pom
# builds its web frontend with the system npm) come from the official node image,
# the same major version as the frontend.
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && node --version && npm --version && git --version && curl --version | head -1

RUN git clone --depth 1 --branch v1.1 --recurse-submodules \
    https://github.com/geofabrik/OpenRailRouting.git /build

WORKDIR /build
COPY orr/planned-tracks.patch /tmp/planned-tracks.patch
COPY orr/overlay/ /build/
RUN git apply /tmp/planned-tracks.patch
RUN mvn clean install -DskipTests -q

# Everything that shapes the graph. The entrypoint rebuilds the graph cache when this
# value differs from the one the cache was built with. Built from the sources, not
# from the JAR, so that a rebuild of the same sources keeps the cache.
COPY config.yml /graphhopper/config.yml
COPY custom_models/ /graphhopper/custom_models/
RUN find /graphhopper/config.yml /graphhopper/custom_models /tmp/planned-tracks.patch /build/src/main -type f \
      | LC_ALL=C sort | xargs sha256sum | sha256sum | cut -d' ' -f1 > /graphhopper/fingerprint

# Stage 2: Checks (`make test`): unit tests of the extension, then the image's own
# entrypoint and configuration against a small network with planned tracks.
FROM builder AS test

# Through the JUnit console launcher, not `mvn test`: OpenRailRouting pins surefire 2.19 with
# the old junit-platform-surefire-provider, which does not run JUnit 5.9 tests reliably.
# --fail-if-no-tests: a test class that is not found must fail the build, not pass it.
RUN mvn -q test-compile dependency:build-classpath -Dmdep.outputFile=/tmp/test-classpath.txt -Dmdep.includeScope=test \
 && mvn -q dependency:copy -Dartifact=org.junit.platform:junit-platform-console-standalone:1.9.1 -DoutputDirectory=/tmp/junit \
 && java -jar /tmp/junit/junit-platform-console-standalone-1.9.1.jar \
      --class-path "target/test-classes:target/classes:$(cat /tmp/test-classpath.txt)" \
      --select-class de.geofabrik.railway_routing.reader.LifecycleTagsTest \
      --fail-if-no-tests --details=tree
RUN cp /build/target/railway_routing-*.jar /railway_routing.jar
COPY docker-entrypoint.sh /docker-entrypoint.sh
COPY test/ /test/
RUN chmod +x /docker-entrypoint.sh && sh /test/smoke.sh

# Stage 3: Runtime image
FROM eclipse-temurin:25-jre AS runtime

# No apt here either (#372, #373). The entrypoint downloads the OSM extract with
# curl, which the base image ships (with ca-certificates, so TLS is verified). The
# healthcheck in compose.yaml calls `wget -qO- http://localhost:8989/health`; that
# command must stay, because the compose.yaml on the server is updated by hand and a
# rollback runs older images under the current one. The base image ships GNU wget
# today; should a newer base image drop it, a static BusyBox wget takes its place.
# It is only meant for that plain-HTTP healthcheck: BusyBox does not verify TLS
# certificates, which is why the download does not use wget.
COPY --from=busybox /bin/busybox /usr/local/lib/busybox/busybox
RUN command -v wget > /dev/null || ln -s /usr/local/lib/busybox/busybox /usr/local/bin/wget \
 && curl --version | head -1 && wget --help > /dev/null 2>&1 \
 && ls /etc/ssl/certs/ca-certificates.crt

COPY --from=builder /build/target/railway_routing-*.jar /railway_routing.jar
COPY --from=builder /graphhopper/ /graphhopper/
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8989
ENTRYPOINT ["/docker-entrypoint.sh"]
