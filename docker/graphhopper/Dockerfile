# Stage 1: Build OpenRailRouting JAR from source (v1.1, GraphHopper 11.0)
FROM maven:3-eclipse-temurin-17 AS builder

RUN apt-get update && apt-get install -y git nodejs npm && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch v1.1 --recurse-submodules \
    https://github.com/geofabrik/OpenRailRouting.git /build

WORKDIR /build
RUN mvn clean install -DskipTests -q

# Stage 2: Runtime image
FROM eclipse-temurin:17-jre-alpine

RUN apk add --no-cache wget

COPY --from=builder /build/target/railway_routing-*.jar /railway_routing.jar
COPY config.yml /graphhopper/config.yml
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8989
ENTRYPOINT ["/docker-entrypoint.sh"]
