FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY scripts ./scripts
COPY alembic ./alembic
COPY alembic.ini ./
COPY localization ./localization
# A mistaken inherited start command must fail, never start production workers.
RUN rm app/main.py scripts/start.sh \
 && useradd --uid 10001 --create-home qa && chown -R qa:qa /app
USER qa
CMD ["sh", "-c", "exec uvicorn app.smart_reminder_qa:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --no-access-log"]
