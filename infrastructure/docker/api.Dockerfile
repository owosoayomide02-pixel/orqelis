FROM python:3.12-slim

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
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
