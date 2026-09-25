FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git ca-certificates nmap build-essential unzip \
    && rm -rf /var/lib/apt/lists/*

# ProjectDiscovery tools (Hunter Option A — in-process scans)
RUN curl -sSfL https://raw.githubusercontent.com/projectdiscovery/subfinder/main/install.sh | sh -s -- -b /usr/local/bin \
    && curl -sSfL https://raw.githubusercontent.com/projectdiscovery/httpx/main/install.sh | sh -s -- -b /usr/local/bin \
    && curl -sSfL https://raw.githubusercontent.com/projectdiscovery/nuclei/main/install.sh | sh -s -- -b /usr/local/bin

RUN nuclei -update-templates

WORKDIR /app
COPY packages/security /app/packages/security
COPY packages/shared /app/packages/shared
COPY services/detection /app/services/detection
COPY services/ai /app/services/ai
COPY services/api /app/services/api

RUN pip install --no-cache-dir \
    -e /app/packages/security \
    -e /app/packages/shared \
    -e /app/services/detection \
    -e /app/services/ai \
    -e /app/services/api

WORKDIR /app/services/api
ENV SCANNER_MODE=local
ENV ENVIRONMENT=production
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
