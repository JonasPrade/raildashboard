# Stage 1: Build OpenRailRouting JAR from source (v1.1, GraphHopper 11.0), with the
# dashboard's extension for proposed tracks and tracks under construction:
#   orr/planned-tracks.patch  changes to existing OpenRailRouting files
#   orr/overlay/              new files (encoded value railway_status, its parser, tests)
# See docs/features/feature-routing.md → "Geplante und im Bau befindliche Gleise aus OSM".
FROM maven:3-eclipse-temurin-17 AS builder

RUN apt-get update && apt-get install -y git nodejs npm && rm -rf /var/lib/apt/lists/*

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

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
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
FROM eclipse-temurin:17-jre AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends wget && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/target/railway_routing-*.jar /railway_routing.jar
COPY --from=builder /graphhopper/ /graphhopper/
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8989
ENTRYPOINT ["/docker-entrypoint.sh"]
