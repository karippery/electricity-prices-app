# ==============================
# Stage 1: Build dependencies
# ==============================
FROM python:3.11-slim AS builder

RUN pip install --upgrade pip && pip install --no-cache-dir uv

WORKDIR /app

# 1. Copy ONLY dependency metadata first
COPY pyproject.toml ./

# 2. Create venv BEFORE copying source code
RUN uv venv --python 3.11 .venv

# 3. Install dependencies using pyproject.toml
RUN uv pip install --python .venv/bin/python .

# 4. NOW copy the rest of the source code
COPY . .

# ==============================
# Stage 2: Runtime
# ==============================
FROM python:3.11-slim AS runtime

RUN addgroup --system app && adduser --system --ingroup app app

RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:${PATH}"

RUN chown -R app:app /app
USER app

EXPOSE 8000

CMD [".venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]