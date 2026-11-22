FROM gcc:13-bookworm

# Create a non-root user — code always runs as 'runner'
RUN useradd -m -s /bin/sh runner

USER runner
WORKDIR /code

# G++ C++ compiler only — standard libraries, no network, ephemeral execution
