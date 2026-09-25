FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    python3 \
    subfinder \
    httpx-toolkit \
    nuclei \
    nmap \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /scan
COPY scanner/run.sh /scan/run.sh
RUN chmod +x /scan/run.sh

ENTRYPOINT ["/scan/run.sh"]
