FROM maven:3.9.9-eclipse-temurin-8 AS build
WORKDIR /src
COPY deployment/maven-settings.xml /tmp/settings.xml
COPY upstream/jshERP-boot/pom.xml .
RUN mvn -s /tmp/settings.xml -B dependency:go-offline
COPY upstream/jshERP-boot/src ./src
COPY upstream/jshERP-boot/docs ./docs
RUN mvn -s /tmp/settings.xml -B package

FROM eclipse-temurin:8-jre-jammy
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -r -u 10001 -d /app erp \
    && mkdir -p /app/upload /app/logs /app/tmp /app/plugins /app/pluginConfig /app/exports \
    && chown -R erp:erp /app
WORKDIR /app
COPY --from=build --chown=erp:erp /src/target/jshERP.jar /app/jshERP.jar
USER erp
EXPOSE 9999
ENTRYPOINT ["java", "-Xms128m", "-Xmx768m", "-Dfile.encoding=UTF-8", "-Dlogs.home=/app/logs", "-Dflowpilot.export.dir=/app/exports", "-jar", "/app/jshERP.jar"]
