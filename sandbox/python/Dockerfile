FROM python:3.12-slim

# Create a non-root user — code always runs as 'runner'
RUN useradd -m -s /bin/sh runner

USER runner
WORKDIR /code

# Python standard library only — no external dependencies, no pip packages
# This image is used ephemerally: create → run → destroy per test case
