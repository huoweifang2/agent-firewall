# ── Stage 1: Builder ────────────────────────────────────
FROM python:3.12-slim AS builder

RUN echo "Acquire::ForceIPv4 \"true\";" > /etc/apt/apt.conf.d/99force-ipv4 && \
    sed -i -e "s/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g" \
           -e "s/security.debian.org\/debian-security/mirrors.tuna.tsinghua.edu.cn\/debian-security/g" \
           /etc/apt/sources.list.d/debian.sources 2>/dev/null || true

RUN apt-get update -y --fix-missing && apt-get install -y --no-install-recommends --fix-missing \
    build-essential g++ \
    libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 libffi-dev libcairo2 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache .

# ── Stage 2: Runtime ────────────────────────────────────
FROM python:3.12-slim

RUN echo "Acquire::ForceIPv4 \"true\";" > /etc/apt/apt.conf.d/99force-ipv4 && \
    sed -i -e "s/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g" \
           -e "s/security.debian.org\/debian-security/mirrors.tuna.tsinghua.edu.cn\/debian-security/g" \
           /etc/apt/sources.list.d/debian.sources 2>/dev/null || true

RUN apt-get update -y --fix-missing && apt-get install -y --no-install-recommends --fix-missing \
    libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 libcairo2 libglib2.0-0 \
    fonts-liberation fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY src/ src/
COPY data/ data/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
