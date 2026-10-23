# Full HSK AI API/Bot QA runtime built from the selected P3 branch.
# This image is independent of Railway; it does not include production secrets.
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
RUN python -m py_compile \
    /app/scripts/local_p3_qa_bootstrap.py \
    /app/scripts/local_p3_qa_runtime_guard.py \
    /app/app/main.py

EXPOSE 8000
