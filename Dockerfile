# Production fallback for Railway build-driver download failures.
# The runtime matches .python-version (3.12) and preserves ffmpeg
# previously installed through nixpacks.toml / railpack.json.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg ca-certificates libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway sets PORT and runs the start command from railway.toml.
# The script performs the existing Alembic migration guard/upgrade.
CMD ["bash", "scripts/start.sh"]
