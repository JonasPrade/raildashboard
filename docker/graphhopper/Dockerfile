FROM eclipse-temurin:17-jre-alpine

ARG GH_VERSION=9.1

RUN apk add --no-cache wget \
 && wget -q -O /graphhopper.jar \
      "https://github.com/graphhopper/graphhopper/releases/download/${GH_VERSION}/graphhopper-web-${GH_VERSION}.jar" \
 && mkdir -p /graphhopper

COPY config.yml /graphhopper/config.yml
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8989
ENTRYPOINT ["/docker-entrypoint.sh"]
