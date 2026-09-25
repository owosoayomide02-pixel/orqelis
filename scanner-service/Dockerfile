FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git ca-certificates nmap unzip \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSfL https://raw.githubusercontent.com/projectdiscovery/subfinder/main/install.sh | sh -s -- -b /usr/local/bin \
    && curl -sSfL https://raw.githubusercontent.com/projectdiscovery/httpx/main/install.sh | sh -s -- -b /usr/local/bin \
    && curl -sSfL https://raw.githubusercontent.com/projectdiscovery/nuclei/main/install.sh | sh -s -- -b /usr/local/bin \
    && nuclei -update-templates

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" httpx

ENV SCANNER_INTERNAL_TOKEN=
EXPOSE 9000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
