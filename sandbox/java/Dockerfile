FROM eclipse-temurin:21-jdk-alpine

# Create a non-root user — code always runs as 'runner'
RUN adduser -D -s /bin/sh runner

USER runner
WORKDIR /code

# JDK only — no external dependencies, no pip, no package managers
# This image is used ephemerally: create → run → destroy per test case
