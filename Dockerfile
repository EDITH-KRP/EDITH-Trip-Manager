# Multi-stage production container for EDITH-TRIP MANAGER
FROM python:3.12-slim AS builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final runtime stage
FROM python:3.12-slim AS runner

WORKDIR /app
COPY --from=builder /install /usr/local
COPY ./app ./app
COPY ./frontend ./frontend

# Run unprivileged user for security
RUN adduser --disabled-password --gecos "" edithuser && chown -R edithuser:edithuser /app
USER edithuser

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --proxy-headers"]
