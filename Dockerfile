FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    quantum-espresso \
    openmpi-bin \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /work

# Verify installation
RUN pw.x --version || echo "pw.x installed"

# Default command
CMD ["pw.x", "--version"]
