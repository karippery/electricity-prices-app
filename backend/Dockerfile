# ==============================
# Stage 1: Build dependencies
# ==============================
FROM python:3.11-slim AS builder

RUN pip install --upgrade pip && pip install --no-cache-dir uv

WORKDIR /app

# Copy project metadata first for caching
COPY pyproject.toml .

# Create virtual environment
RUN uv venv --python 3.11 .venv

# Install dependencies + project (this reads pyproject.toml)
RUN uv pip install --python .venv/bin/python .

# ==============================
# Stage 2: Runtime
# ==============================
FROM python:3.11-slim AS runtime

RUN addgroup --system app && adduser --system --ingroup app app

RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy venv
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY . .

RUN chown -R app:app /app
USER app

EXPOSE 8000

CMD [".venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
