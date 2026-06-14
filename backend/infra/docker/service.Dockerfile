FROM maven:3.9.9-eclipse-temurin-21 AS build

WORKDIR /workspace
ARG MODULE
ARG SKIP_MAVEN_BUILD=false

COPY . .
RUN if [ "$SKIP_MAVEN_BUILD" != "true" ]; then \
        mvn -q -pl "${MODULE}" -am -DskipTests package; \
    fi
RUN mkdir -p /opt/courseflow \
    && cp "${MODULE}"/target/*.jar /opt/courseflow/app.jar

FROM eclipse-temurin:21-jre

WORKDIR /app
COPY --from=build /opt/courseflow/app.jar /app/app.jar

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
