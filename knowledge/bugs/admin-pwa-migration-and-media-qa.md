# Admin PWA migration and media QA boundaries

- Cause: a migration rehearsal had its own literal 0130 upper bound after the
  standalone initializer deferred the new 0131 table. Local model-created
  fixtures concealed the missing real migration. CI also ran real video tests
  before installing ffprobe/FFmpeg.
- Fix: the disposable PostgreSQL rehearsal derives its reviewed boundary from
  `scripts.qa_standalone_bootstrap.EXPECTED_HEAD`, runs each real 0103..head
  migration and verifies deferred table/column parity. CI installs FFmpeg
  before unit and browser media tests.
- Risk: this is the isolated empty-QA migration path, not permission to run
  historical cold-start migrations or a schema initializer on a populated DB.
  A missing production encoder still fails closed with unavailable.
- Prevention: update the explicit initializer head/deferred models and real
  Alembic migration together. Keep true video decoding/encoding tests; do not
  replace them with mocks or skip them to conceal absent CI dependencies.
