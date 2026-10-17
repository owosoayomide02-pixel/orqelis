FROM golang:1.24-bookworm AS scanner-tool-builder

ARG AMASS_VERSION=v4.2.0
ARG FFUF_VERSION=v2.1.0
RUN go install github.com/owasp-amass/amass/v4/...@${AMASS_VERSION} \
    && go install github.com/ffuf/ffuf/v2@${FFUF_VERSION}

FROM python:3.12-slim

COPY --from=scanner-tool-builder /go/bin/amass /usr/local/bin/amass
COPY --from=scanner-tool-builder /go/bin/ffuf /usr/local/bin/ffuf

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git ca-certificates nmap build-essential unzip gobuster dirb whatweb perl \
    libnet-ssleay-perl libio-socket-ssl-perl libwww-perl \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/sullo/nikto.git /opt/nikto \
    && chmod +x /opt/nikto/program/nikto.pl \
    && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto

RUN git clone --depth 1 --branch 3.2 https://github.com/testssl/testssl.sh.git /opt/testssl \
    && chmod +x /opt/testssl/testssl.sh \
    && ln -s /opt/testssl/testssl.sh /usr/local/bin/testssl.sh

RUN git clone --depth 1 --filter=blob:none --sparse https://github.com/danielmiessler/SecLists.git /usr/share/seclists \
    && git -C /usr/share/seclists sparse-checkout set --no-cone /Discovery/Web-Content/common.txt

# ProjectDiscovery tools (Hunter Option A — in-process scans)
COPY infrastructure/docker/install_projectdiscovery.py /tmp/install_projectdiscovery.py
RUN python /tmp/install_projectdiscovery.py /usr/local/bin
RUN mv /usr/local/bin/httpx /usr/local/bin/httpx-projectdiscovery

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
    -e /app/services/api \
    wapiti3

RUN apt-get update && apt-get install -y --no-install-recommends libxml-writer-perl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/local/bin/httpx-projectdiscovery /usr/local/bin/httpx \
    && for tool in amass ffuf subfinder httpx tlsx katana dnsx whatweb testssl.sh wapiti nmap nuclei gobuster nikto; do \
        command -v "$tool" >/dev/null || exit 1; \
    done \
    && httpx -version \
    && nikto -Version \
    && test -s /usr/share/seclists/Discovery/Web-Content/common.txt \
    && test -d /root/nuclei-templates

WORKDIR /app/services/api
ENV SCANNER_MODE=local
ENV ENVIRONMENT=production
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
