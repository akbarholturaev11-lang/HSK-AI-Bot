# Disposable Railway STAGING schema-only operator.
# PostgreSQL 18 client tools are shipped with the pinned major-version base.
# Contains no production credentials, no product runtime and no user data.
FROM postgres:18
RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends python3 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/hsk-qa
COPY scripts/qa_schema_only_bootstrap.py /opt/hsk-qa/scripts/qa_schema_only_bootstrap.py
USER postgres
ENTRYPOINT ["python3", "-u", "scripts/qa_schema_only_bootstrap.py"]
