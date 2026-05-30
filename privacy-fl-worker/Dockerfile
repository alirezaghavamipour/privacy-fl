FROM python:3.12-slim

LABEL org.opencontainers.image.description="Worker: CP encrypt/decrypt + AS homomorphic aggregation for privacy-preserving FL"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir tenseal vantage6-algorithm-tools cryptography

COPY worker_pkg/ ./worker_pkg/
COPY setup.py .
RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1
ARG PKG_NAME="worker_pkg"
ENV PKG_NAME=${PKG_NAME}

CMD python -c "from vantage6.algorithm.tools.wrap import wrap_algorithm; wrap_algorithm()"
