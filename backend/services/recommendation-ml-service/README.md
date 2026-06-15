# CourseFlow Recommendation ML Service

This is the Python ML boundary for CourseFlow related-course recommendations. It owns recommendation
training jobs, model metadata, versioned recommendation scores and internal inference endpoints.
Java services call it through internal APIs; they do not import model code or write the ML database
directly.

## Responsibilities

- Train related-course models from bounded, hashed learner interactions.
- Store training run history, active model versions and recommendation scores in
  `cf_recommendation_ml`.
- Expose internal endpoints compatible with the analytics service contract:
  - `POST /internal/recommendation-ml/related-courses:train`
  - `POST /internal/recommendation-ml/related-courses:enqueue`
  - `GET /internal/recommendation-ml/training-runs`
  - `GET /internal/recommendation-ml/training-runs/audit`
  - `GET /internal/recommendation-ml/training-runs/{trainingRunId}`
  - `POST /internal/recommendation-ml/training-runs/{trainingRunId}:cancel`
  - `POST /internal/recommendation-ml/training-runs/{trainingRunId}:requeue`
  - `GET /internal/recommendation-ml/models`
  - `GET /internal/recommendation-ml/models/active`
  - `GET /internal/recommendation-ml/models/activation-requests`
  - `POST /internal/recommendation-ml/models/{modelVersion}:request-activation`
  - `POST /internal/recommendation-ml/models/activation-requests/{approvalId}:approve`
  - `POST /internal/recommendation-ml/models/activation-requests/{approvalId}:reject`
  - `GET /internal/recommendation-ml/models/audit`
  - `GET /internal/recommendation-ml/courses/{courseId}/related`
- Verify internal JWTs and require least-privilege scopes:
  `internal:recommendation-ml:train` for training submission/status,
  `internal:recommendation-ml:infer` for inference, and
  `internal:recommendation-ml:ops` for model/training operations.
- Keep the algorithm layer framework-independent so the ML team can add new models without
  touching Spring services.

## Security Gate

The service fails closed when internal JWT verification is not configured. HS256 requires
`COURSEFLOW_INTERNAL_JWT_SECRET` with at least 32 bytes. RS256 local verification requires
`COURSEFLOW_INTERNAL_JWT_PUBLIC_KEY`; RS256 JWKS verification requires
`COURSEFLOW_INTERNAL_JWT_JWKS_URI`. The JWKS URI must be an HTTP(S) URL and must not point to
localhost, loopback, `0.0.0.0`, `::1`, or `host.docker.internal`; service DNS such as
`http://identity-token-converter-service:8080/oauth/jwks` is valid for the Docker prod profile.
All internal tokens must carry `iss`, `aud`, `sub`, `iat` and `exp` claims matching
`COURSEFLOW_INTERNAL_JWT_ISSUER` and `COURSEFLOW_INTERNAL_JWT_AUDIENCE`; the service rejects tokens
whose `exp - iat` exceeds `COURSEFLOW_INTERNAL_JWT_MAX_TTL_SECONDS` (default and maximum `900`).
Service tokens must carry the concrete endpoint scope; wildcard scopes are rejected at runtime even
if a token issuer misconfigures one.
JWKS verification uses a cached client with bounded timeout from
`COURSEFLOW_INTERNAL_JWT_JWKS_CACHE_TTL_SECONDS` and
`COURSEFLOW_INTERNAL_JWT_JWKS_TIMEOUT_SECONDS`; key lookup and decode failures fail closed as `403`
instead of leaking 500 responses.
FastAPI docs and OpenAPI are disabled by default; set `RECOMMENDATION_ML_DOCS_ENABLED=true` only in
controlled non-production environments.

## Project Layout

```text
src/courseflow_ml/
  api/              FastAPI routes and dependency wiring
  core/             config, security and telemetry
  domain/           ML domain records shared by training and persistence
  repositories/     database persistence boundary
  schemas/          external API contract
  services/         application services and idempotency rules
  training/         model training algorithms and batch CLI
migrations/         Alembic database migrations
tests/              fast algorithm and contract tests
```

## Local Development

```bash
python -m venv .venv
. .venv/bin/activate
make install
make test
make run
```

The default DB URL accepts either a SQLAlchemy URL or the existing CourseFlow JDBC-style env vars:
`RECOMMENDATION_ML_DB_URL`, `RECOMMENDATION_ML_DB_USERNAME` and
`RECOMMENDATION_ML_DB_PASSWORD`.

Run the Postgres/Alembic integration gate against a disposable database before promoting a migration
or repository change:

```bash
RECOMMENDATION_ML_INTEGRATION_DB_URL=postgresql://courseflow:courseflow@localhost:5432/cf_recommendation_ml \
COURSEFLOW_INTERNAL_JWT_SECRET=courseflow-local-internal-jwt-secret-change-me-32 \
make integration-test
```

The integration gate applies Alembic `upgrade head`, exercises async training, active-model
activation, production candidate approval/rejection when auto-activation is disabled,
maker-checker reactivation, direct-activation rejection, model/training operation audit, operator
cancellation audit, status-filtered ops queries, and DB-backed operational metrics on PostgreSQL.
It is skipped by default unless `RECOMMENDATION_ML_INTEGRATION_DB_URL` is set; CI runs it with a
disposable Postgres service.

In the production Compose profile, the API and worker containers run with
`RECOMMENDATION_ML_RUN_MIGRATIONS=false`. Apply migrations through the dedicated one-shot job before
rolling those containers:

```bash
cd ../../
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  -f infra/docker/docker-compose.prod.yml \
  --profile migration \
  run --rm recommendation-ml-migrator
```

Production also sets `RECOMMENDATION_ML_REQUIRE_ACTIVE_MODEL_READY=true`, so `/actuator/health`
returns `503` until a current active model exists. Keep the default `false` only for empty
environment bootstrap or local development where analytics can rely on deterministic fallback while
the first model is trained. Production sets `RECOMMENDATION_ML_AUTO_ACTIVATE_TRAINED_MODELS=false`;
successful training creates a `CANDIDATE` model and a `PENDING_ACTIVATION` run until a different ops
actor approves activation.
Ops audit evidence for training cancellation/requeue and model activation requests/reviews is
validated before persistence: sensitive field names or raw auth-looking values are rejected, payloads
must stay bounded, and JSON evidence, including composite maker-checker audit evidence, is no longer
truncated into partial audit records.
Queued training payloads persist only HMAC-SHA256 learner principal hashes, not raw `principalId`
values. Configure a dedicated `RECOMMENDATION_ML_PRINCIPAL_HASH_SECRET` for API, worker and migration
containers; do not reuse the internal JWT signing secret.
Model version identifiers are registry-safe: at most 80 characters, start with a letter or digit, and
may contain only letters, digits, `.`, `_`, `:`, or `-`. Values with spaces, slashes, or control
characters are rejected before a training run or activation request is persisted.
Ops list status filters are strict per domain. Unknown training-run, model-version, or activation
approval statuses return `400` instead of silently returning an empty list.
Training event types are validated before queue persistence and canonicalized to uppercase. The
accepted event types are `ENROLLMENT`, `CLICK`, and `IMPRESSION`; unsupported values return `400`.
Production also sets `RECOMMENDATION_ML_SYNC_TRAINING_ENABLED=false`. New training must enter through
`related-courses:enqueue` and be executed by a worker; the synchronous `related-courses:train`
endpoint remains only for local/demo compatibility and explicit non-production diagnostics.
The container Docker `HEALTHCHECK` uses `/health` as liveness so an otherwise healthy process is not
restarted while readiness is intentionally `503` during active-model bootstrap or incidents.

## Training Operations

`POST /internal/recommendation-ml/related-courses:train` remains available only when
`RECOMMENDATION_ML_SYNC_TRAINING_ENABLED=true`. Production disables it and uses
`related-courses:enqueue`, which persists a `QUEUED` training run and returns immediately. Worker
processes claim queued jobs with database row locks:

```bash
courseflow-ml worker --worker-id recommendation-ml-worker
```

For local one-shot checks:

```bash
courseflow-ml worker --once
```

The worker records successful models atomically and clears its lock metadata when the run reaches
`ACTIVE`, `PENDING_ACTIVATION`, `INSUFFICIENT_DATA`, or `FAILED`. Operators can poll
`GET /internal/recommendation-ml/training-runs/{trainingRunId}` for job status and generated scores.
If a worker exits after claiming a job, the next worker sweep treats `RUNNING` rows whose
`locked_at` is older than `RECOMMENDATION_ML_TRAINING_JOB_LEASE_SECONDS` as stale. Stale jobs are
requeued with `RECOMMENDATION_ML_TRAINING_JOB_REQUEUE_DELAY_SECONDS` backoff until
`RECOMMENDATION_ML_TRAINING_JOB_MAX_ATTEMPTS`; after that they are marked `FAILED` with
`WORKER_LEASE_EXPIRED`.

Successful training must pass activation quality gates before it can become a model candidate. The
service checks minimum event count, principal count, course count, generated pair count and quality
score. A run that trains recommendations but misses one of those gates ends as
`QUALITY_GATE_FAILED`, leaving the previous active model untouched. When
`RECOMMENDATION_ML_AUTO_ACTIVATE_TRAINED_MODELS=false`, a passing run writes a `CANDIDATE` model and
returns `PENDING_ACTIVATION`; approved maker-checker activation later changes the run to `ACTIVE`.
If the checker rejects the candidate, the model becomes `REJECTED` and the training run becomes
`ACTIVATION_REJECTED`, leaving the active model and learner read model unchanged.
When the flag is `true`, intended only for local/demo bootstrap, the service writes a new `ACTIVE`
model immediately after quality gates.

Model activation is governed through a maker-checker ops surface. Operators can list training runs
and model versions, request reactivation of a previous model version with mandatory reason/evidence,
and inspect `recommendation_model_ops_audit`. A model can have only one pending activation request;
operators must approve or reject the existing request before creating another. A different operator
must approve the pending activation request before the service switches the active model; the
requester cannot approve or reject their own request. Candidate activation, local/demo automatic
activation and approved prior model reactivation all use the same active-model advisory lock and
write audit rows.
Rejected activation requests also write model ops audit rows.

Training job operations are also audited. Operators can cancel `QUEUED`, `RUNNING`, or `STARTED`
runs, requeue failed/cancelled async runs that still have a stored payload, and inspect
`recommendation_training_ops_audit`. A cancelled run cannot be overwritten by a worker finish path,
and model activation checks the training run row before publishing a new active model.

## Data Lifecycle

Queued training jobs store `payload_json` only so workers can process the async request. The payload
contains bounded learner interaction events with hashed principal ids, but it is still treated as
sensitive behavioural data. After a run reaches a completed state, the service keeps run metadata,
request hash, model versions, recommendation scores and audit rows, but scrubs `payload_json` after
`RECOMMENDATION_ML_TRAINING_PAYLOAD_RETENTION_DAYS` days. Production sets this to `30` and the prod
profile validator rejects values outside `1..30`.

The worker performs this scrub on startup and then every
`RECOMMENDATION_ML_PAYLOAD_SCRUB_INTERVAL_SECONDS` seconds. Operators can also run a one-shot scrub:

```bash
courseflow-ml scrub-training-payloads
```

After a failed or cancelled run has aged past the retention window and its payload is scrubbed, it is
no longer requeueable; submit a new training run instead.

## Observability

`GET /actuator/prometheus` exposes DB-backed operational gauges at scrape time. SRE can alert on:

- `courseflow_recommendation_ml_http_requests_total{method,route,status_class}`
- `courseflow_recommendation_ml_http_request_duration_seconds_bucket{method,route,status_class,le}`
- `courseflow_recommendation_ml_training_runs_by_status{status="queued|running|..."}`
- `courseflow_recommendation_ml_training_stale_running_runs`
- `courseflow_recommendation_ml_training_oldest_queued_age_seconds`
- `courseflow_recommendation_ml_training_oldest_running_age_seconds`
- `courseflow_recommendation_ml_pending_activation_approvals`
- `courseflow_recommendation_ml_oldest_pending_activation_approval_age_seconds`
- `courseflow_recommendation_ml_active_model_present`
- `courseflow_recommendation_ml_active_model_age_seconds`
- `courseflow_recommendation_ml_active_model_stale`
- `courseflow_recommendation_ml_migration_ready`
- `courseflow_recommendation_ml_metrics_refresh_total{result="success|error"}`
- `courseflow_recommendation_ml_internal_auth_rejections_total{reason}`

The Java analytics consumer also exposes
`courseflow_analytics_recommendation_ml_client_requests_total{operation,result,reason}`. Alert on
fallback outcomes there to catch cases where the ML service is reachable but production traffic is
not receiving active ML recommendations.
HTTP labels use bounded FastAPI route templates such as
`/internal/recommendation-ml/courses/{course_id}/related`; unmatched paths are collapsed to
`__unmatched__` so learner/course identifiers never become Prometheus label values.

`RECOMMENDATION_ML_ACTIVE_MODEL_STALE_AFTER_SECONDS` controls the stale-model threshold exposed by
`courseflow_recommendation_ml_active_model_stale`; the default is seven days. Metrics refresh errors
do not break the scrape response, but increment `result="error"` so Prometheus can alert separately.

Run the ops smoke from the backend root before promoting a Recommendation ML release:

```bash
cd ../../
RECOMMENDATION_ML_SMOKE_URL=http://localhost:8080 \
COURSEFLOW_INTERNAL_JWT_SECRET=courseflow-local-internal-jwt-secret-change-me-32 \
RECOMMENDATION_ML_SMOKE_EVIDENCE_FILE=recommendation-ml-smoke-evidence.json \
node scripts/recommendation-ml-ops-smoke.mjs
```

For a repeatable local HTTP gate, run the wrapper below from the backend root. It starts a disposable
Postgres container, applies Alembic migrations, seeds an active baseline model, runs the FastAPI app
and worker with production-like activation governance plus disabled sync training, executes the
maker-checker mutation smoke through `enqueue`, writes the evidence JSON and removes the temporary
runtime:

```bash
scripts/recommendation-ml-local-http-smoke.sh
```

The wrapper uses `$PYTHON` when provided, otherwise it falls back to `python3.12`, `python3.11`,
`python3` or `python`. The product-hardening workflow runs this local HTTP smoke after the Python
unit, type, lint and Postgres integration gates. The same workflow also builds the Docker image,
checks the image contract for non-root runtime, liveness healthcheck, exposed port and gated
migration command, runs the built image against disposable Postgres to prove Docker liveness remains
healthy while readiness is `503` without an active model, then uploads
`backend/recommendation-ml-smoke-artifacts` with image-contract evidence, image-runtime evidence,
local HTTP smoke evidence JSON and Uvicorn log.

For staging/pre-production, set `RECOMMENDATION_ML_SMOKE_ANALYTICS_URL`,
`RECOMMENDATION_ML_SMOKE_ENVIRONMENT`, `RECOMMENDATION_ML_SMOKE_PROMETHEUS_URL` and
`RECOMMENDATION_ML_SMOKE_REQUIRED_TARGETS` so the smoke also proves analytics-service integration,
Prometheus target health and no critical Recommendation ML alerts are firing. It also verifies every
`RECOMMENDATION_ML_SMOKE_REQUIRED_ALERTS` rule is loaded and healthy in Prometheus; the default list
covers no active model, stuck training, migration readiness, metrics refresh failure and analytics
consumer fallback. Staging evidence must include GitHub Actions source provenance for repository,
ref, commit SHA, run URL, run attempt and actor; the product-hardening workflow fills those fields
automatically. Use explicit short-lived `RECOMMENDATION_ML_SMOKE_TRAIN_TOKEN`,
`RECOMMENDATION_ML_SMOKE_INFER_TOKEN` and `RECOMMENDATION_ML_SMOKE_OPS_TOKEN`, plus
`RECOMMENDATION_ML_SMOKE_OPS_CHECKER_TOKEN` and `RECOMMENDATION_ML_SMOKE_ANALYTICS_MODEL_TOKEN`, from
STS. The analytics token must carry `internal:analytics:model-write`.
For staging signoff, keep `RECOMMENDATION_ML_SMOKE_REQUIRE_HTTPS_URLS=true` and
`RECOMMENDATION_ML_SMOKE_REJECT_LOCAL_URLS=true`; evidence using localhost, loopback, or non-HTTPS
Recommendation ML, analytics, or Prometheus URLs is rejected.
The smoke decodes JWT claims for evidence without storing token values and requires each staging
token to be an unexpired `token_use=internal`, `actor_type=service` JWT with `iat`, `exp`, the
expected scope and TTL no greater than `RECOMMENDATION_ML_SMOKE_MAX_TOKEN_TTL_SECONDS` (default and
maximum `900`). The service enforces the same max TTL at runtime through
`COURSEFLOW_INTERNAL_JWT_MAX_TTL_SECONDS`. It records subject hashes only and requires the ops maker
token and ops checker token to resolve to different service subjects. The local wrapper also proves
that a wildcard service scope is rejected; staging can provide
`RECOMMENDATION_ML_SMOKE_WILDCARD_TOKEN` for the same runtime probe when a controlled negative token
is available.
When the maker-checker mutation flow is enabled, the smoke also proves activation audit evidence
rejects sensitive fields before any approval request is persisted.
Set `RECOMMENDATION_ML_SMOKE_REQUIRE_PREMINTED_TOKENS=true` for staging/pre-production signoff; local
HS256 fallback tokens are only for local wrappers. The smoke requires an active model by default and
also verifies train/infer/ops
least-privilege scope separation, deployed docs/OpenAPI/Redoc are disabled, synchronous training is
blocked in production-like runs, and direct model activation is disabled in favor of maker-checker
approval.
Set `RECOMMENDATION_ML_SMOKE_MUTATION_FLOW_ENABLED=true` in staging/pre-production to create a
synthetic candidate, request activation, prove duplicate-pending and maker-self-review guards, then
reject the candidate with `RECOMMENDATION_ML_SMOKE_OPS_CHECKER_TOKEN` so the active model is not
changed. The smoke first verifies the readiness `activationGovernance` component so mutation flow
cannot run while trained models would auto-activate. The mutation flow also scrapes
`/actuator/prometheus` while the request is pending to prove the approval count/age metrics observe
the queue. The checker token must resolve to a different actor than `RECOMMENDATION_ML_SMOKE_OPS_TOKEN`.
If a mutation assertion fails after an activation request is created, or after a candidate is trained
but before the approval ID is captured, the smoke attempts a best-effort checker rejection cleanup
before returning failure.
Set `RECOMMENDATION_ML_SMOKE_ANALYTICS_CLIENT_METRIC_REQUIRED=true` for staging/pre-production. The
smoke calls analytics-service to materialize the active ML model into the learner-facing read model,
then requires Prometheus evidence that
`courseflow_analytics_recommendation_ml_client_requests_total{operation="active_model",result="available"}`
is present with a positive value and that
`courseflow_analytics_recommendation_ml_client_requests_total{result="fallback"}` did not increase
within `RECOMMENDATION_ML_SMOKE_ANALYTICS_CLIENT_METRIC_WINDOW` (default `30m`).
The product-hardening GitHub workflow exposes the same production-grade check through
`run_recommendation_ml_ops_smoke=true` and uploads `recommendation-ml-ops-smoke-evidence.json` for the
release record. The evidence includes the synthetic mutation `smokeRunId`, `trainingRunId`,
`modelVersion`, `approvalId`, terminal status and cleanup result so SRE can trace or clean the exact
candidate touched by the smoke. The workflow also writes
`recommendation-ml-ops-smoke-manifest.json` and `.sha256` with SHA-256 hashes, byte sizes and a
non-secret evidence summary; manifest verification also requires `evidenceFile` to match a hashed
file entry and reconciles the summary with that referenced evidence JSON. Retain those alongside the
evidence JSON and log.
The staging verifier treats this as a fresh release artifact: `checkedAt` must be a UTC timestamp,
must not be more than `RECOMMENDATION_ML_SMOKE_MAX_EVIDENCE_FUTURE_SKEW_MINUTES` ahead of verifier
time, and must be no older than `RECOMMENDATION_ML_SMOKE_MAX_EVIDENCE_AGE_HOURS` (default `24`).
It also binds the artifact to the release source by requiring expected repository, commit SHA,
ref, workflow, job, run ID, run attempt, actor and run URL to match `sourceProvenance`, and to the
release target by requiring expected environment, Recommendation ML URL, analytics URL and Prometheus
URL to match the evidence. The same verifier also binds the Prometheus monitoring policy: expected
scrape targets and required alert rules must match `requiredTargets`, `requiredAlerts`, Prometheus
target results and loaded alert-rule evidence. Threshold policy is also bound: queued/running job
age, pending activation approval age, token TTL and analytics metric window must match the release
configuration.
For production signoff, keep `RECOMMENDATION_ML_SMOKE_EXPECT_SYNC_TRAIN_DISABLED=true` and
`RECOMMENDATION_ML_SMOKE_REQUIRE_PREMINTED_TOKENS=true` and
`RECOMMENDATION_ML_SMOKE_ANALYTICS_CLIENT_METRIC_REQUIRED=true`; the workflow rejects staging smoke
configuration that does not prove the synchronous training endpoint is blocked, analytics ML client
metrics are healthy, or that relies on locally minted HS256 smoke tokens. Verify retained evidence
with:

```bash
node scripts/recommendation-ml-evidence-verify.mjs \
  recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke-evidence.json \
  --mode=staging \
  --expected-environment="$RECOMMENDATION_ML_SMOKE_ENVIRONMENT" \
  --expected-service-url="$RECOMMENDATION_ML_SMOKE_URL" \
  --expected-analytics-url="$RECOMMENDATION_ML_SMOKE_ANALYTICS_URL" \
  --expected-prometheus-url="$RECOMMENDATION_ML_SMOKE_PROMETHEUS_URL" \
  --expected-prometheus-targets="$RECOMMENDATION_ML_SMOKE_REQUIRED_TARGETS" \
  --expected-required-alerts="$RECOMMENDATION_ML_SMOKE_REQUIRED_ALERTS" \
  --expected-max-queued-age-seconds="$RECOMMENDATION_ML_SMOKE_MAX_QUEUED_AGE_SECONDS" \
  --expected-max-running-age-seconds="$RECOMMENDATION_ML_SMOKE_MAX_RUNNING_AGE_SECONDS" \
  --expected-max-pending-activation-approval-age-seconds="$RECOMMENDATION_ML_SMOKE_MAX_PENDING_ACTIVATION_APPROVAL_AGE_SECONDS" \
  --expected-max-token-ttl-seconds="$RECOMMENDATION_ML_SMOKE_MAX_TOKEN_TTL_SECONDS" \
  --expected-analytics-metric-window="$RECOMMENDATION_ML_SMOKE_ANALYTICS_CLIENT_METRIC_WINDOW" \
  --max-age-hours=24 \
  --max-future-skew-minutes=10 \
  --expected-repository="$RECOMMENDATION_ML_SMOKE_REPOSITORY" \
  --expected-commit-sha="$RECOMMENDATION_ML_SMOKE_COMMIT_SHA" \
  --expected-ref="$RECOMMENDATION_ML_SMOKE_REF" \
  --expected-workflow="$RECOMMENDATION_ML_SMOKE_WORKFLOW" \
  --expected-job="$RECOMMENDATION_ML_SMOKE_JOB" \
  --expected-run-id="$RECOMMENDATION_ML_SMOKE_RUN_ID" \
  --expected-run-attempt="$RECOMMENDATION_ML_SMOKE_RUN_ATTEMPT" \
  --expected-actor="$RECOMMENDATION_ML_SMOKE_ACTOR" \
  --expected-run-url="$RECOMMENDATION_ML_SMOKE_RUN_URL"
node scripts/recommendation-ml-evidence-manifest.mjs \
  --output=recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke-manifest.json \
  --checksum-output=recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke-manifest.json.sha256 \
  recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke-evidence.json \
  recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke.log
node scripts/recommendation-ml-evidence-manifest.mjs \
  --verify=recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke-manifest.json \
  --checksum=recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke-manifest.json.sha256
```

## Current Recommendation Model

`IMPLICIT_ITEM_CF_V1` is an item-item collaborative filtering model over learner-course
interactions. Enrollment events carry the strongest implicit signal, followed by clicks and
impressions. The service stores score, similarity, support count, reason code and model version for
each generated pair.

## Enterprise Extension Points

Add new packages under `training/` only when they serve the recommendation domain, such as a
content-similarity fallback, personalized ranking, or re-ranking model for related courses. New ML
domains such as learner-risk prediction, fraud scoring or assessment integrity should become sibling
Python services with their own database, scopes, routes and service ownership.
