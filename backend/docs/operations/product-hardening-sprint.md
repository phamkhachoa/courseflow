# Product Hardening Sprint

This runbook defines the production-pilot gate for CourseFlow. The goal is not to add more surface
area; it is to prove that the core LMS workflow can be operated, audited and recovered.

## P0 Scope

- Golden flow: create course, submit review, approve, publish, enroll learner, learn content, submit
  assessment, grade, finalize, issue certificate, report.
- Course authoring preview: reviewers must inspect the server-side draft learner preview before
  approving the `learner-preview-checked` gate; learner runtime remains backed only by the published
  immutable curriculum snapshot.
- Published course runtime: publish must pin `courses.published_version_no`, freeze module status as
  `PUBLISHED` inside the snapshot, expose the pinned version to learner player/progress responses,
  and emit it on `course.published` events.
- Admin UX: operators must use pickers/search for common workflows, not raw UUID lookup as the
  primary path.
- Compliance baseline: admin can export identity-owned user data and deactivate an account with a
  recorded reason, token revocation and live role-grant revocation.
- Notification baseline: every notification has durable inbox state plus delivery status
  (`PENDING`, `DELIVERED`, `FAILED`) so operators can distinguish stored rows from delivery failures.
- Trust boundary baseline: downstream services only accept propagated `X-User-*` identity headers
  when the request also presents a valid short-lived internal JWT.
- Migration safety: fresh local databases must apply Liquibase changelogs without duplicate-column
  failures.

## Golden Flow Checklist

Use demo data or a disposable test tenant. Do not run this checklist against production user data.

| Step | Actor | Evidence |
|---|---|---|
| Login | Admin/instructor/student | Access token issued; gateway forwards `X-User-*` headers |
| Create course draft | Instructor | Course is `DRAFT`, modules are server-owned draft state |
| Submit review | Instructor | Review state changes to `IN_REVIEW` |
| Approve and publish | Non-owner scoped reviewer/admin | Course is `PUBLISHED`; enrollment capacity initializes |
| Search/discover | Public/learner | Published course appears in catalog/search |
| Enroll learner | Student or scoped staff | Enrollment is `ACTIVE`; unpublished courses are rejected |
| Learn content | Student | Module/item progress updates under enrolled course |
| Take quiz | Student | Attempt uses question snapshot and deadline guard |
| Grade/finalize | Staff | Grading queue shows missing/finalize-ready work; gradebook entry/final grade is scoped and auditable |
| Issue certificate | Staff | Verification code resolves publicly |
| Report | Staff/admin | Course reports require course staff scope; org dashboards require platform admin or matching org scope |
| Learner success | Staff | At-risk learners can be filtered by severity and opened directly in gradebook/certificate eligibility workflows |
| Notify learner | Staff/admin | Notification row has delivery status and appears in learner inbox |
| Privacy action | Admin | User privacy export downloads; deactivate revokes tokens/role grants |

## Verification Commands

Pull requests and pushes to `main`/`develop` run `.github/workflows/product-hardening.yml`:

- backend reactor tests
- admin web production build
- learner mobile static analysis
- gateway smoke script syntax validation
- promotion runtime smoke script syntax validation
- production Docker Compose/profile validation

Backend unit/regression gate:

```bash
cd backend
mvn test
```

Targeted hardening gate:

```bash
cd backend
mvn -pl services/access-control-service,services/user-management-service,services/notification-service -am test
mvn -pl services/analytics-service -am test
mvn -pl services/outbox-relay -am test
cd services/recommendation-ml-service
python -m pytest
python -m ruff check src tests
python -m mypy src tests
```

Admin frontend build gate:

```bash
cd web/react-admin
npm run build
```

Loyalty control-plane regression gate:

```bash
cd backend
mvn -q -pl services/loyalty-service,services/api-gateway -am \
  -Dtest=LoyaltyServiceTest,LoyaltyMetricsTest,LoyaltyServiceJpaSmokeTest,GatewayRouteConfigurationTest \
  -Dsurefire.failIfNoSpecifiedTests=false test
```

Gateway smoke gate with disposable user data:

```bash
cd backend
COURSEFLOW_API_URL=http://localhost:28080/api \
COURSEFLOW_SMOKE_ADMIN_EMAIL=admin@courseflow.local \
COURSEFLOW_SMOKE_ADMIN_PASSWORD=password \
node scripts/product-hardening-smoke.mjs
```

Keycloak security smoke gate against a running OIDC cluster. Run it from a runner/container that can
reach the internal token converter and at least one direct domain service. Application services are
not host-published in the discovery-based Compose topology, so use internal DNS names or an approved
temporary port-forward.

```bash
cd backend
COURSEFLOW_API_URL=http://localhost:28080/api \
COURSEFLOW_TOKEN_CONVERTER_URL=http://identity-token-converter-service:8080 \
COURSEFLOW_DIRECT_SERVICE_URL=http://course-service:8080 \
COURSEFLOW_SECURITY_SMOKE_ACCESS_TOKEN="<keycloak-access-token-from-approved-login>" \
COURSEFLOW_SECURITY_SMOKE_TOKEN_EXCHANGE_CLIENT_ID=api-gateway \
COURSEFLOW_SECURITY_SMOKE_TOKEN_EXCHANGE_CLIENT_SECRET="<api-gateway STS client secret>" \
COURSEFLOW_SECURITY_SMOKE_STS_CLIENT_ID=course-service \
COURSEFLOW_SECURITY_SMOKE_STS_CLIENT_SECRET="<course-service STS client secret>" \
node scripts/keycloak-security-smoke.mjs
```

This gate proves the security architecture, not the whole LMS workflow: Keycloak access token reaches
the gateway, the converter exchanges it for a CourseFlow internal JWT, converter JWKS verifies the
internal signature and `kid`, STS `client_credentials` issues a service token, public profile lookup
does not require a bearer token, profile summary batch remains protected, and a direct service call
with forged `X-User-*` headers is rejected. Do not use password grant for production smoke; the
script only supports it when `COURSEFLOW_SECURITY_SMOKE_ALLOW_PASSWORD_GRANT=true` is explicitly set
for local/demo realms.
Production JWKS configuration must use an HTTP(S) URL that is not localhost, loopback, `0.0.0.0`,
`::1`, or `host.docker.internal`; Docker service DNS for the token converter is acceptable inside the
prod Compose network.

Promotion runtime smoke gate against the local Docker cluster:

```bash
cd backend
node scripts/promotion-runtime-smoke.mjs
```

Default `local` mode seeds a disposable incentive application, checkout-service binding, campaign
fixture, five negative application/client-binding fixtures, a coupon-required abuse fixture, and a
dedicated hot quota fixture. The smoke first preflights the fixture shapes in Postgres, then proves
the intended service-only runtime chain: gateway browser routes for
`/api/v1/incentives/evaluate` and `/api/v1/incentives/reservations` stay closed, STS rejects the
wrong checkout secret, STS rejects runtime scopes for `promotion-service`, `checkout-service` can mint
only the explicit runtime scopes, direct runtime calls fail closed without a valid internal token,
each runtime operation rejects a token missing its matching `internal:promotion:<operation>` scope,
unknown incentive applications are rejected, unbound/suspended/empty/wrong-operation client binding
fixtures return `403` with no reservation rows, coupon abuse cases for missing/invalid/inactive/
not-started/expired/holder-mismatch/exhausted coupons fail closed without leaking raw coupon values
or creating reservations, idempotency keys are required for mutating operations, idempotency payload
conflicts return `409`, commit-after-cancel returns `committed=false` without a redemption,
`evaluate -> reserve -> commit` succeeds, reserve/commit idempotency replay returns the same ids,
cancel/reverse runtime operations are idempotent, committed and reversed redemption outbox events are
published, run-scoped reconciliation evidence proves cancel and commit/reverse ledger/outbox/quota
policy rows are balanced, hot quota parallel reserve has exactly one winner, and outbox relay has
zero open promotion DLQ rows.

Promotion runtime smoke gate against staging/pre-production:

```bash
cd backend
PROMOTION_SMOKE_MODE=staging \
PROMOTION_SMOKE_TOKEN_CONVERTER_URL=https://token-converter.internal.example \
PROMOTION_SMOKE_PROMOTION_URL=https://promotion.internal.example \
PROMOTION_SMOKE_GATEWAY_URL=https://api.example.com/api \
PROMOTION_SMOKE_PROMETHEUS_URL=https://prometheus.internal.example \
PROMOTION_OBSERVABILITY_REQUIRED_TARGETS="api-gateway|courseflow-api-gateway|api-gateway:8080,identity-token-converter-service|courseflow-services|identity-token-converter-service:8080,promotion-service|courseflow-services|promotion-service:8080,outbox-relay|courseflow-services|outbox-relay:8080" \
PROMOTION_OBSERVABILITY_REQUIRED_COUPON_ABUSE_GUARD_RESULTS="limited" \
PROMOTION_OBSERVABILITY_REQUIRED_COUPON_LOOKUP_STORAGE_PATHS="current_hmac" \
PROMOTION_OBSERVABILITY_FORBIDDEN_COUPON_LOOKUP_STORAGE_PATHS="legacy_sha,legacy_raw" \
PROMOTION_OBSERVABILITY_MAX_FORBIDDEN_COUPON_LOOKUP_INCREASE=0 \
PROMOTION_OBSERVABILITY_ADMIN_OPERATION_RATE_GUARD_REQUIRED=true \
PROMOTION_OBSERVABILITY_REQUIRED_ADMIN_OPERATION_RATE_GUARD_RESULTS=allowed \
PROMOTION_OBSERVABILITY_REQUIRED_ADMIN_OPERATION_RATE_GUARD_OPERATIONS=coupon_import_dry_run \
PROMOTION_OBSERVABILITY_CUTOVER_WINDOW=24h \
PROMOTION_CUTOVER_ENVIRONMENT=staging \
PROMOTION_CUTOVER_EVIDENCE_ENABLED=true \
PROMOTION_CUTOVER_EVIDENCE_SCOPES="coupon_fixture|courseflow|<coupon fixture app>|<coupon fixture campaign UUID>|true|true" \
PROMOTION_CUTOVER_EVIDENCE_FILE=promotion-runtime-smoke-artifacts/promotion-cutover-evidence.json \
PROMOTION_SMOKE_CHECKOUT_CLIENT_SECRET="<checkout-service STS secret>" \
PROMOTION_SMOKE_PROMOTION_CLIENT_SECRET="<promotion-service STS secret>" \
PROMOTION_SMOKE_TENANT_ID=courseflow \
PROMOTION_SMOKE_APPLICATION_ID=lms \
PROMOTION_SMOKE_EXPECTED_CAMPAIGN_CODE="<pre-provisioned smoke campaign>" \
PROMOTION_SMOKE_UNBOUND_APPLICATION_ID="<active app with no checkout binding>" \
PROMOTION_SMOKE_SUSPENDED_APPLICATION_ID="<suspended app with active checkout binding>" \
PROMOTION_SMOKE_SUSPENDED_BINDING_APPLICATION_ID="<active app with suspended checkout binding>" \
PROMOTION_SMOKE_EMPTY_BINDING_APPLICATION_ID="<active app with checkout binding allowed_operations=[]>" \
PROMOTION_SMOKE_EVALUATE_ONLY_APPLICATION_ID="<active app with checkout binding allowed_operations=[evaluate]>" \
PROMOTION_SMOKE_COUPON_APPLICATION_ID="<active coupon-required fixture app>" \
PROMOTION_SMOKE_COUPON_CAMPAIGN_CODE="<pre-provisioned coupon-required smoke campaign>" \
PROMOTION_SMOKE_QUOTA_APPLICATION_ID="<active hot-quota fixture app>" \
PROMOTION_SMOKE_QUOTA_CAMPAIGN_CODE="<pre-provisioned max-one quota campaign>" \
PROMOTION_SMOKE_COUPON_FINGERPRINT_KEY_ID="<current coupon fingerprint key id>" \
PROMOTION_SMOKE_COUPON_FINGERPRINT_PEPPER="<current coupon fingerprint pepper>" \
PROMOTION_SMOKE_COUPON_VALID_CODE="<valid coupon code>" \
PROMOTION_SMOKE_COUPON_INACTIVE_CODE="<paused coupon code>" \
PROMOTION_SMOKE_COUPON_NOT_STARTED_CODE="<future coupon code>" \
PROMOTION_SMOKE_COUPON_EXPIRED_CODE="<expired coupon code>" \
PROMOTION_SMOKE_COUPON_HOLDER_MISMATCH_CODE="<holder-bound coupon code>" \
PROMOTION_SMOKE_COUPON_EXHAUSTED_CODE="<zero-quota coupon code>" \
PROMOTION_SMOKE_COUPON_INVALID_CODE="<nonexistent coupon code>" \
PROMOTION_SMOKE_COUPON_ABUSE_GUARD_BURST_ATTEMPTS=6 \
PROMOTION_SMOKE_HOT_QUOTA_PARALLEL_ATTEMPTS=12 \
PROMOTION_SMOKE_HOT_QUOTA_SOAK_WAVES=1 \
PROMOTION_SMOKE_HOT_QUOTA_SOAK_ARTIFACT_FILE=promotion-runtime-smoke-artifacts/promotion-hot-quota-soak.json \
PROMOTION_SMOKE_REQUIRE_COUPON_INVENTORY_READY=true \
PROMOTION_SMOKE_COUPON_IMPORT_GATEWAY_ENABLED=true \
PROMOTION_SMOKE_COUPON_CAMPAIGN_ID="<coupon fixture campaign UUID>" \
PROMOTION_SMOKE_ADMIN_ACCESS_TOKEN="<staging admin OAuth2 access token>" \
PROMOTION_COUPON_IMPORT_ISSUE_EXPORT_MAX_ROWS=10000 \
PROMOTION_SMOKE_PROMOTION_DATABASE_URL="<cf_promotion read connection>" \
PROMOTION_SMOKE_OUTBOX_DATABASE_URL="<cf_outbox read connection>" \
node scripts/promotion-runtime-smoke.mjs
node scripts/promotion-observability-smoke.mjs
```

Staging mode must use a pre-provisioned disposable fixture; it does not seed or mutate admin
configuration. `PROMOTION_SMOKE_EXPECTED_CAMPAIGN_CODE` and
`PROMOTION_SMOKE_QUOTA_CAMPAIGN_CODE` are required in staging so the smoke cannot select and consume
quota from arbitrary active campaigns. Database checks may only be skipped with
`PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS=true`, which makes the run a partial smoke and not a production
readiness gate. The five `PROMOTION_SMOKE_*_APPLICATION_ID` negative fixtures must be reviewed,
pre-provisioned staging applications: the unbound fixture has no checkout-service binding, the
suspended-application fixture has status `SUSPENDED`, the suspended-binding fixture has a
`SUSPENDED` checkout binding, the empty-binding fixture has an active checkout binding with
`allowed_operations=[]`, and the evaluate-only fixture has an active checkout binding with exactly
`["evaluate"]`. None of the negative applications may have a published campaign snapshot. The coupon
fixture application must have exactly one active published coupon-required campaign for the configured
campaign code and no active non-coupon fallback snapshot. Its coupons must use current HMAC storage,
store only masks in `code`/`code_mask`, and cover valid, inactive, not-started, expired,
holder-mismatch, exhausted, and invalid-missing scenarios. Treat raw coupon codes and fingerprint
pepper as secrets. The runtime smoke also checks active coupon storage inventory for both the
coupon fixture campaign and coupon fixture application: `legacy_sha`, `legacy_raw`, and `malformed`
must be zero, and `current_hmac` must be present. This check is enabled by default through
`PROMOTION_SMOKE_REQUIRE_COUPON_INVENTORY_READY=true`.

Coupon import issue exports are intentionally bounded while the admin API still returns CSV content
inside a JSON DTO. `PROMOTION_COUPON_IMPORT_ISSUE_EXPORT_MAX_ROWS` defaults to `10000`; an export
request above that limit must fail with `EXPORT_TOO_LARGE` before loading row payloads into memory.
The production profile validator requires this setting, when overridden, to be a positive integer.
Use narrower row-status filters for operator evidence until a later sprint adds paged or streaming
downloads.

When `PROMOTION_SMOKE_COUPON_IMPORT_GATEWAY_ENABLED=true`, the runtime smoke also exercises the
operator lane through the real gateway path `/api/admin/v1/incentives/**` using
`PROMOTION_SMOKE_ADMIN_ACCESS_TOKEN`. That opt-in gate proves bearer enforcement, storage inventory,
multipart coupon import dry-run, dry-run idempotency replay, history/detail lookup, and masked issue
export without using direct `/internal/**` URLs or service STS tokens. The smoke asserts that the
admin response/export does not leak raw coupon codes, normalized codes, fingerprints, or idempotency
keys. Keep the gate disabled in local runs until an admin OAuth2 token is available.

The hot quota fixture application must have an active checkout-service binding for
`evaluate`, `reserve`, `commit`, `cancel`, and `reverse`, exactly one active published non-coupon
campaign for `PROMOTION_SMOKE_QUOTA_CAMPAIGN_CODE`, `max_redemptions=1`, no active fallback
campaign snapshot in the same fixture application, and no coupon requirement. The smoke fires
parallel reserve attempts with distinct idempotency keys, profiles, and external references, then
requires exactly one reserved response, all other attempts to return `QUOTA_EXHAUSTED`, exactly one
reservation, one `RESERVE` ledger row, a bounded campaign quota counter, and zero quota counters with
`used_count < 0` or `used_count > limit_count`. After capturing evidence, the smoke cancels the
winning reservation and verifies a `CANCEL` ledger row plus `used_count=0`, so the staging fixture can
be reused safely by the next release-candidate run.

The staging guard fixture must be configured so the coupon abuse guard can prove a real limited
decision within `PROMOTION_SMOKE_COUPON_ABUSE_GUARD_BURST_ATTEMPTS`. For release evidence, run the
fixture environment with `PROMOTION_COUPON_ABUSE_GUARD_MODE=enforced` or an equivalent pre-production
profile. Production may roll out the same guard in `shadow` first, but a release candidate is not
proven unless staging shows burst invalid evaluate and reserve attempts return generic `RATE_LIMITED`
declines without creating reservations or exposing coupon secrets.

Database checks are part of the release gate, not optional evidence. The runtime smoke validates the
run-scoped reconciliation trail after the money lifecycle: a cancelled reservation must have exactly
one `RESERVE` ledger row, one `CANCEL` ledger row, no redemption, no commit/reverse ledger rows, and
the `RELEASE_RESERVED_QUOTA` policy; a committed then reversed redemption must have exactly one
`RESERVE`, one `COMMIT`, one `REVERSE`, no cancel row, published committed/reversed outbox events
with the smoke correlation/source client, non-empty effects, status `REVERSED`, and the
`NO_RELEASE_ON_COMMITTED_REVERSAL` policy. These checks also scan the ledger/outbox evidence for raw
coupon-code or fingerprint leakage.

The staging promotion smoke is also available as the `run_promotion_runtime_smoke` manual workflow
input in `.github/workflows/product-hardening.yml`. Configure the `COURSEFLOW_PROMOTION_SMOKE_*`
repository variables/secrets to the same values shown above. The workflow intentionally forces
`PROMOTION_SMOKE_ALLOW_SKIP_DB_CHECKS=false`, installs `psql`, checks Prometheus target/metric/alert
evidence, proves the hot quota concurrency fixture, and uploads the smoke log artifacts so pilot
releases have durable evidence. The
observability smoke also requires a recent promotion runtime metric increase within
`PROMOTION_OBSERVABILITY_RUNTIME_RECENT_WINDOW` (default `15m`), no unpublished promotion outbox
backlog above `PROMOTION_OBSERVABILITY_MAX_OUTBOX_UNPUBLISHED` (default `0`), no oldest unpublished
outbox age above `PROMOTION_OBSERVABILITY_MAX_OUTBOX_OLDEST_AGE_SECONDS` (default `0`), and zero open
promotion relay DLQ rows. It also verifies recent bounded coupon-match metrics for
`not_supplied`, `not_found`, `inactive`, `not_started`, `expired`, `holder_mismatch`, and `matched`
with `coupon_required=true`, plus recent bounded coupon abuse guard metrics such as
`promotion_coupon_abuse_guard_total{result="limited"}`. For fresh deployments, the observability
smoke accepts either a Prometheus `increase()` or a recent `max_over_time()` observation so a guard
event that happened before the first scrape is still valid release evidence within the same smoke
window. It also verifies coupon lookup cutover evidence: current HMAC storage paths must have recent
runtime evidence, while forbidden legacy paths such as `legacy_sha` and `legacy_raw` must not
increase in the same smoke window. Finally, it verifies recent quota evidence for
`promotion_quota_total` consumed/exhausted/released results and
`promotion_quota_reserve_fallback_total` candidate-conflict/exhausted results.
When the coupon import gateway lane is enabled, the observability smoke also requires
`promotion_admin_operation_rate_guard_total` evidence for
`operation=coupon_import_dry_run,result=allowed`. This proves admin import traffic traversed the
bounded-cardinality admin operation guard without requiring a deliberately rate-limited operator
request.

When `PROMOTION_CUTOVER_EVIDENCE_ENABLED=true`, the observability smoke writes a retained JSON
artifact to `PROMOTION_CUTOVER_EVIDENCE_FILE`. Each entry in
`PROMOTION_CUTOVER_EVIDENCE_SCOPES` is semicolon-separated and uses:
`name|tenantId|applicationId|campaignId?|activeOnly?|requireNonEmpty?`. The artifact includes
`schemaVersion`, `artifactType=promotion_coupon_hmac_cutover_evidence`, environment, GitHub run
metadata when present, exact scope, gateway inventory counts, Prometheus lookup evidence for
`PROMOTION_OBSERVABILITY_CUTOVER_WINDOW` (default `24h`), redaction evidence, failed check names, and
`decision.status`. Staging fixture scopes should set `requireNonEmpty=true`; production read-only
scopes may leave it false when proving an application that currently has no active coupons. The
artifact must not contain raw coupon codes, normalized codes, HMAC fingerprints, coupon ids, key ids,
holder profile ids, peppers, idempotency keys, or uploaded CSV content.

This gate now covers the full disposable learning path through the gateway:
public catalog, protected module access, authoring draft/module/item creation,
review approval, publish, enrollment, learner login, learner module read, item
progress completion, course-completion enrollment status, quiz authoring,
sanitized learner quiz view, attempt snapshot, auto-grading, gradebook ingestion,
final grade, automatic certificate issue, public certificate verification,
notification delivery, privacy export, and user deactivation.

PostgreSQL backup/restore drill:

```bash
cd backend
scripts/postgres-backup-drill.sh backup
scripts/postgres-backup-drill.sh restore-check backups/postgres/<timestamp> cf_promotion
scripts/postgres-backup-drill.sh restore-check backups/postgres/<timestamp> cf_recommendation_ml
```

The restore-check writes `backups/postgres/<timestamp>/restore-check-cf_promotion.json` after a
successful `pg_restore` probe. Register promotion retention restore drills from that evidence file's
`restoreDrillRef`, `databaseName`, `backupPath`, `artifactHash`, `status`, and `checkedAt` values,
not from manually typed hashes.
For Recommendation ML releases, retain
`backups/postgres/<timestamp>/restore-check-cf_recommendation_ml.json`; its probe also checks the
restored Alembic revision and core ML tables.

Before rolling Recommendation ML API or worker containers in a production-shaped Compose release, run
the dedicated Alembic migration job:

```bash
cd backend
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  -f infra/docker/docker-compose.prod.yml \
  --profile migration \
  run --rm recommendation-ml-migrator
```

The production profile keeps `RECOMMENDATION_ML_DOCS_ENABLED=false`; API docs/OpenAPI may only be
enabled in controlled non-production environments.
It also keeps `RECOMMENDATION_ML_REQUIRE_ACTIVE_MODEL_READY=true`, so production readiness returns
`503` until a current active model exists, and
`RECOMMENDATION_ML_AUTO_ACTIVATE_TRAINED_MODELS=false`, so new trained models stay
`PENDING_ACTIVATION`/`CANDIDATE` until a different ops checker approves them. Rejected candidates
close as `REJECTED`/`ACTIVATION_REJECTED` with audit and do not affect the active read model.
Only one pending activation request is allowed per model version.
Recommendation ML training/model ops audit evidence must be secret-safe and bounded before
persistence; raw auth-looking fields or values are rejected instead of being truncated into partial
JSON audit records. Composite maker-checker model activation audit evidence must remain parseable
even when it embeds bounded request and review evidence.
Queued Recommendation ML training payloads must store learner principals as HMAC-SHA256 hashes using
a dedicated `RECOMMENDATION_ML_PRINCIPAL_HASH_SECRET`; raw `principalId` values and JWT signing
secrets must not be used for persisted ML training payload identity.
Recommendation ML model version identifiers must be URL/audit safe: at most 80 characters, start
with a letter or digit, and contain only letters, digits, `.`, `_`, `:`, or `-`.
Recommendation ML ops list status filters must be strict per domain; typo/unknown training-run,
model-version, or activation-request statuses must return `400` rather than an empty list.
Recommendation ML training input must reject unsupported event types before queue persistence; only
`ENROLLMENT`, `CLICK`, and `IMPRESSION` are accepted and stored canonically.
Production also sets `RECOMMENDATION_ML_SYNC_TRAINING_ENABLED=false`; training must be submitted
through the queued endpoint and executed by the worker, while the synchronous training endpoint is
reserved for local/demo compatibility.
The readiness endpoint exposes `activationGovernance`; production-like readiness is `DOWN` if active
models are required but trained models would still auto-activate.
The Docker image healthcheck must stay on `/health` liveness, not `/actuator/health` readiness, so
the container is not restarted simply because production readiness is correctly blocking traffic
until an active model exists.

Recommendation ML ops smoke gate against staging/pre-production:

```bash
cd backend
scripts/recommendation-ml-local-http-smoke.sh

RECOMMENDATION_ML_SMOKE_URL=https://recommendation-ml.<env>.courseflow.internal \
RECOMMENDATION_ML_SMOKE_ENVIRONMENT=staging \
RECOMMENDATION_ML_SMOKE_REQUIRE_HTTPS_URLS=true \
RECOMMENDATION_ML_SMOKE_REJECT_LOCAL_URLS=true \
RECOMMENDATION_ML_SMOKE_ANALYTICS_URL=https://analytics.<env>.courseflow.internal \
RECOMMENDATION_ML_SMOKE_PROMETHEUS_URL=https://prometheus.<env>.courseflow.internal \
RECOMMENDATION_ML_SMOKE_REQUIRED_TARGETS='recommendation-ml|courseflow-services|recommendation-ml-service:8080,analytics|courseflow-services|analytics-service:8080' \
RECOMMENDATION_ML_SMOKE_TRAIN_TOKEN='<sts-issued-train-token>' \
RECOMMENDATION_ML_SMOKE_INFER_TOKEN='<sts-issued-infer-token>' \
RECOMMENDATION_ML_SMOKE_OPS_TOKEN='<sts-issued-ops-token>' \
RECOMMENDATION_ML_SMOKE_OPS_CHECKER_TOKEN='<sts-issued-ops-token-for-different-actor>' \
RECOMMENDATION_ML_SMOKE_ANALYTICS_MODEL_TOKEN='<sts-issued-analytics-model-write-token>' \
RECOMMENDATION_ML_SMOKE_REQUIRE_PREMINTED_TOKENS=true \
RECOMMENDATION_ML_SMOKE_MAX_QUEUED_AGE_SECONDS=900 \
RECOMMENDATION_ML_SMOKE_MAX_RUNNING_AGE_SECONDS=3600 \
RECOMMENDATION_ML_SMOKE_MAX_PENDING_ACTIVATION_APPROVAL_AGE_SECONDS=86400 \
RECOMMENDATION_ML_SMOKE_MAX_TOKEN_TTL_SECONDS=900 \
RECOMMENDATION_ML_SMOKE_ANALYTICS_CLIENT_METRIC_WINDOW=30m \
RECOMMENDATION_ML_SMOKE_ANALYTICS_CLIENT_METRIC_REQUIRED=true \
RECOMMENDATION_ML_SMOKE_CI_PROVIDER=github_actions \
RECOMMENDATION_ML_SMOKE_REPOSITORY='<org>/<repo>' \
RECOMMENDATION_ML_SMOKE_COMMIT_SHA='<40-char-git-sha>' \
RECOMMENDATION_ML_SMOKE_REF='<release-branch-or-tag>' \
RECOMMENDATION_ML_SMOKE_WORKFLOW='Product Hardening Gates' \
RECOMMENDATION_ML_SMOKE_JOB=recommendation-ml-ops-smoke \
RECOMMENDATION_ML_SMOKE_RUN_ID='<github-run-id>' \
RECOMMENDATION_ML_SMOKE_RUN_ATTEMPT='<github-run-attempt>' \
RECOMMENDATION_ML_SMOKE_ACTOR='<github-actor>' \
RECOMMENDATION_ML_SMOKE_RUN_URL='<github-run-url>' \
RECOMMENDATION_ML_SMOKE_EVIDENCE_FILE=recommendation-ml-smoke-artifacts/recommendation-ml-ops-smoke-evidence.json \
node scripts/recommendation-ml-ops-smoke.mjs
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

The local wrapper is a pre-staging HTTP gate: it starts disposable Postgres, applies Alembic
migrations, seeds an active model, boots the FastAPI app and worker with production-like activation
governance, proves synchronous training is disabled, executes queued training through the worker, and
runs the maker-checker mutation smoke. It does not replace the staging/pre-production smoke because
it cannot prove real Prometheus scrape targets or deployed STS/token wiring. Set `PYTHON`
to force the interpreter; otherwise the wrapper chooses `python3.12`, `python3.11`, `python3`, or
`python`. The product-hardening workflow runs this wrapper after the Python unit/lint/type and
Postgres integration gates. It also builds the Recommendation ML Docker image, validates the image
contract for non-root runtime, liveness healthcheck, exposed port and gated migration command, runs
the built image against disposable Postgres to prove Docker liveness remains healthy while readiness
is `503` without an active model, then uploads `backend/recommendation-ml-smoke-artifacts` with
image-contract evidence, image-runtime evidence, local HTTP smoke evidence JSON and Uvicorn log.

Use explicit short-lived `RECOMMENDATION_ML_SMOKE_TRAIN_TOKEN`,
`RECOMMENDATION_ML_SMOKE_INFER_TOKEN`, `RECOMMENDATION_ML_SMOKE_OPS_TOKEN` and
`RECOMMENDATION_ML_SMOKE_OPS_CHECKER_TOKEN`, plus
`RECOMMENDATION_ML_SMOKE_ANALYTICS_MODEL_TOKEN` with `internal:analytics:model-write`, from STS for
staging/pre-production signoff. Local HS256 smoke tokens are acceptable only for local/demo wrappers;
they are not production release evidence.
Staging smoke also requires `RECOMMENDATION_ML_SMOKE_REQUIRE_HTTPS_URLS=true` and
`RECOMMENDATION_ML_SMOKE_REJECT_LOCAL_URLS=true`; the verifier rejects release evidence whose
Recommendation ML, analytics, or Prometheus URL is not HTTPS or points to localhost/loopback.
The smoke decodes JWT claims without storing token values and fails staging signoff unless each
train/infer/ops/checker/analytics token is an unexpired `token_use=internal`, `actor_type=service`
JWT containing `iat`, `exp`, the expected scope and a TTL no greater than
`RECOMMENDATION_ML_SMOKE_MAX_TOKEN_TTL_SECONDS` (default and maximum `900` seconds). The service also
enforces the same max lifetime at runtime with `COURSEFLOW_INTERNAL_JWT_MAX_TTL_SECONDS`. It records
only subject hashes and rejects staging evidence unless the ops maker token and ops checker token
resolve to different service subjects.
The smoke also requires `courseflow_recommendation_ml_internal_auth_rejections_total{reason="invalid_jwt"}`
to increment after the invalid-JWT probe, so auth-boundary failures are visible outside HTTP 403
status-class metrics.
When a controlled negative token is available, set `RECOMMENDATION_ML_SMOKE_WILDCARD_TOKEN`; the
smoke must prove a signed token with `scope="*"` is still rejected by Recommendation ML runtime
scope checks.
Staging release evidence must also include `RECOMMENDATION_ML_SMOKE_ENVIRONMENT` and
`sourceProvenance` fields tying the artifact to a GitHub Actions workflow run, repository, ref,
40-character commit SHA, run attempt and actor. The workflow fills these automatically; manual
staging runs must provide the `RECOMMENDATION_ML_SMOKE_*` provenance variables shown above.
The smoke requires an active model by default. It proves service health/readiness, Alembic readiness,
DB-backed Prometheus metrics, invalid internal-JWT rejection, training/model/audit ops reads,
active-model inference readiness, train/infer/ops least-privilege scope separation, disabled direct
activation (`409`), disabled deployed docs/OpenAPI/Redoc, disabled synchronous training in
production-like runs, required Prometheus targets, pending activation approval count/age metrics, and
no firing critical Recommendation ML alerts. Set
`RECOMMENDATION_ML_SMOKE_REQUIRE_ACTIVE_MODEL=false` only for a first empty-environment bootstrap; that
run is not sufficient production release evidence.
For staging/pre-production signoff, set `RECOMMENDATION_ML_SMOKE_MUTATION_FLOW_ENABLED=true` and
provide `RECOMMENDATION_ML_SMOKE_OPS_CHECKER_TOKEN` for a different actor than
`RECOMMENDATION_ML_SMOKE_OPS_TOKEN`; the smoke then enqueues a synthetic training job, waits for the
worker to create a candidate, proves duplicate pending and maker-self-review rejection, and
checker-rejects the candidate so the active model is not changed. The smoke first verifies readiness
`activationGovernance=UP`, so mutation flow cannot run against an environment that would auto-activate
trained models. The mutation flow also proves activation audit evidence rejects sensitive fields
before any approval request is persisted, then scrapes
Recommendation ML metrics while the synthetic approval is pending, proving pending approval count/age
metrics observe the maker-checker queue. If the mutation
flow fails after training the candidate or creating the activation request, the smoke attempts a
best-effort checker rejection cleanup. The evidence JSON records the synthetic mutation `smokeRunId`,
`trainingRunId`, `modelVersion`, `approvalId`, terminal status and cleanup result so SRE can trace
or clean the exact candidate touched by the smoke.
Prometheus evidence must include non-firing request SLI alerts backed by
`courseflow_recommendation_ml_http_requests_total{method,route,status_class}` and
`courseflow_recommendation_ml_http_request_duration_seconds_bucket{method,route,status_class,le}`.
The smoke queries Prometheus `/api/v1/rules?type=alert` and release evidence is rejected unless
every `RECOMMENDATION_ML_SMOKE_REQUIRED_ALERTS` rule is loaded and healthy; the default list covers
no active model, stuck training, migration readiness, metrics refresh failure, and analytics
consumer fallback.
The smoke also calls `analytics-service` to materialize the active ML model into the learner-facing
read model, then verifies
`courseflow_analytics_recommendation_ml_client_requests_total{operation="active_model",result="available"}`
in Prometheus and zero fallback increase for
`courseflow_analytics_recommendation_ml_client_requests_total{result="fallback"}` within
`RECOMMENDATION_ML_SMOKE_ANALYTICS_CLIENT_METRIC_WINDOW` (default `30m`). Fallback results must be
explained by a controlled bootstrap, planned disablement, or an approved incident.

The same gate is available from the `Product Hardening Gates` workflow with
`run_recommendation_ml_ops_smoke=true`. Configure:

- repository variables:
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_URL`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_ENVIRONMENT`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_REQUIRE_HTTPS_URLS=true`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_REJECT_LOCAL_URLS=true`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_ANALYTICS_URL`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_PROMETHEUS_URL`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_REQUIRED_TARGETS`;
- optional repository variables:
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_MAX_QUEUED_AGE_SECONDS`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_MAX_RUNNING_AGE_SECONDS`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_MAX_PENDING_ACTIVATION_APPROVAL_AGE_SECONDS`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_MUTATION_FLOW_ENABLED=true`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_EXPECT_SYNC_TRAIN_DISABLED=true`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_REQUIRE_PREMINTED_TOKENS=true`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_MAX_TOKEN_TTL_SECONDS=900`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_MAX_EVIDENCE_AGE_HOURS=24`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_MAX_EVIDENCE_FUTURE_SKEW_MINUTES=10`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_ANALYTICS_CLIENT_METRIC_REQUIRED=true`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_ANALYTICS_CLIENT_METRIC_WINDOW=30m`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_CRITICAL_ALERTS`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_REQUIRED_ALERTS`;
- repository secrets:
  all of `COURSEFLOW_RECOMMENDATION_ML_SMOKE_TRAIN_TOKEN`,
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_INFER_TOKEN` and
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_OPS_TOKEN`, plus
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_OPS_CHECKER_TOKEN` for a different actor, and
  `COURSEFLOW_RECOMMENDATION_ML_SMOKE_ANALYTICS_MODEL_TOKEN` with
  `internal:analytics:model-write`.

The workflow intentionally rejects `COURSEFLOW_RECOMMENDATION_ML_SMOKE_REQUIRE_ACTIVE_MODEL=false`,
`COURSEFLOW_RECOMMENDATION_ML_SMOKE_MUTATION_FLOW_ENABLED=false`, and
`COURSEFLOW_RECOMMENDATION_ML_SMOKE_EXPECT_SYNC_TRAIN_DISABLED=false`, and
`COURSEFLOW_RECOMMENDATION_ML_SMOKE_REQUIRE_PREMINTED_TOKENS=false`, and
`COURSEFLOW_RECOMMENDATION_ML_SMOKE_ANALYTICS_CLIENT_METRIC_REQUIRED=false`, and staging URL policy
set to anything other than HTTPS/non-local. It also runs
`scripts/recommendation-ml-evidence-verify.mjs --mode=staging`, which rejects release evidence unless
the artifact proves pre-minted token usage, active model `trainingRunId`, Prometheus target health,
loaded healthy Prometheus alert rules, non-firing critical alerts, analytics active-model
materialization, analytics ML client metrics with zero fallback, and terminal maker-checker
rejection of the synthetic candidate. The verifier also rejects staging evidence that lacks
environment/source provenance for the GitHub Actions run and exact commit SHA, whose provenance does
not match the expected release repository/commit/ref/workflow/job/run metadata, whose target
environment or Recommendation ML/analytics/Prometheus endpoints do not match the release target, or
whose Prometheus target/alert evidence does not match the expected monitoring policy, or that uses
internal JWTs without the expected claims, scope and short TTL, or whose queued/running job,
pending approval, token TTL, or analytics metric-window thresholds do not match the release policy,
or that was run against local/non-TLS URLs.
It also requires `checkedAt` to be a fresh UTC timestamp: no older than the configured evidence age
window, and not beyond the configured future clock-skew allowance.
Retain the uploaded `recommendation-ml-ops-staging-smoke-artifacts` artifact, especially
`recommendation-ml-ops-smoke-evidence.json`, `recommendation-ml-ops-smoke.log`,
`recommendation-ml-ops-smoke-manifest.json`, and
`recommendation-ml-ops-smoke-manifest.json.sha256`, with the ML release record. The manifest records
SHA-256 hashes, byte sizes, source provenance, target, threshold, monitoring and synthetic mutation
summary without storing token values. The workflow verifies the manifest sidecar and every recorded
file hash before upload, requires `evidenceFile` to match a hashed file entry, and reconciles the
manifest summary with that referenced evidence JSON.

Mobile static gate when Flutter is installed:

```bash
cd app
flutter analyze
```

Mobile static gate without a host Flutter SDK:

```bash
docker run --rm \
  -v "$PWD/app":/workspace \
  -w /workspace \
  ghcr.io/cirruslabs/flutter:stable \
  bash -lc 'flutter pub get && flutter analyze'
```

## Local Smoke Gate

Start the local cluster:

```bash
cd backend
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  up --build
```

Then check:

- `GET http://localhost:28080/api/v1/courses` returns only published courses.
- Direct service calls that forge `X-User-*` without a valid internal JWT return `401`.
- `node scripts/keycloak-security-smoke.mjs` passes with `Keycloak security smoke passed`.
- Admin course publish emits lifecycle events and enrollment capacity is created.
- Disposable authoring courses can move from draft to approved and published.
- Course review/publish/archive rejects staff outside the course department scope.
- A newly enrolled learner can read published modules and complete required item progress.
- Quiz attempts produce a persisted snapshot, auto-grade, and a gradebook row through the outbox/Kafka chain.
- Finalized passing grades auto-issue certificates that verify publicly without exposing student id or grade.
- Reporting endpoints reject cross-org dashboards and unscoped cross-student analytics.
- `GET http://localhost:18083/connectors/courseflow-course-search-cdc/status` is healthy.
- Admin notifications can send a `SYSTEM` notification and show `DELIVERED` or `FAILED`.
- Admin user detail can download privacy export JSON and deactivate a disposable account.
- `node scripts/product-hardening-smoke.mjs` passes with `Smoke passed`.
- `node scripts/promotion-runtime-smoke.mjs` passes with `Promotion runtime smoke passed`.
- `promotion-cutover-evidence.json`, when enabled, has
  `artifactType=promotion_coupon_hmac_cutover_evidence` and `decision.status=pass`.
- Prometheus can scrape service `/actuator/prometheus` targets when the observability compose override is enabled.
- Token converter metrics show token exchange request/success/failure/duration and JWKS request
  counters: `courseflow.token_converter.*`.
- Token converter emits structured security audit logs on
  `courseflow.security.token_converter.audit` for exchange success/failure without raw bearer tokens
  or client secrets.
- Production token converter runs with `ACCESS_CONTROL_RESOLUTION_MODE=required`; it must not fall
  back to roles embedded in external token claims when `access-control-service` is unavailable.
- Production STS client credentials use an explicit `COURSEFLOW_STS_ALLOWED_CLIENTS` allowlist; `*`
  is reserved for local/demo only.
- Production STS service scopes are explicit; wildcard `COURSEFLOW_STS_ALLOWED_SERVICE_SCOPES=*`
  is rejected, and the list must include the endpoint-level scopes enforced by
  `TrustedGatewayHeaderFilter`, including the concrete `internal:promotion:<operation>` scopes.
  Recommendation ML also rejects wildcard service-token scopes at runtime; each call must carry the
  concrete `internal:recommendation-ml:train`, `infer`, or `ops` scope.
- Promotion service-to-service calls are fail-closed twice: the common internal JWT filter rejects
  generic `internal:service` tokens for `/internal/incentives/**`, and promotion access checks
  require the matching `internal:promotion:<operation>` scope before honoring the client binding.
  Runtime operation scopes are granted only to deployed source clients. In the current production
  topology, enrollment-service owns checkout/order/payment boundary calls; do not require a
  `checkout-service` STS client until a real service is deployed. The `promotion-service` STS client
  keeps `internal:promotion:admin` plus only the loyalty scopes needed for readiness and reversal
  compensation.
- Downstream services expose internal JWT rejection counters through
  `courseflow.internal_jwt.rejections` for `/internal/**`, `/backoffice/**` and identity-header
  requests. Recommendation ML exposes the equivalent Python metric
  `courseflow_recommendation_ml_internal_auth_rejections_total{reason}`.
- Access-control exposes authorization decision counters through
  `courseflow.access_control.authz.checks` and persists denied decisions in
  `access_control_audit_logs`.
- Scoped authorization smoke covers an assignment at an ancestor scope, such as `DEPARTMENT`, being
  honored for a child `COURSE` check only when the service caller supplies server-derived
  `ancestorScopes` with `internal:authz:assert-topology`.
- Chat WebSocket `CONNECT` succeeds with a Keycloak access token only through token converter ->
  internal JWT verification, and direct legacy HS256 JWT verification is not used in Keycloak mode.
- Kafka Connect is verified through `GET /connectors/courseflow-course-search-cdc/status`; it is not a Spring actuator target.
- Grafana starts with the CourseFlow Prometheus datasource provisioned.
- Prometheus loads `infra/observability/alerts.yml` and evaluates basic service-down alerts.
- Promotion coupon storage inventory is reachable through the gateway for an admin:
  `GET /api/admin/v1/incentives/coupons/storage-inventory?tenantId=courseflow&applicationId=lms`.
  The response must be aggregate-only, include all five storage buckets, and must not expose coupon
  code, `normalizedCode`, fingerprint, coupon id, key id, or holder profile id.
- Before disabling `PROMOTION_COUPON_LEGACY_FALLBACK_ENABLED`, coupon inventory must report
  `legacyCoupons=0`, `malformedCoupons=0`, and `fallbackDisableReady=true` for the active scope, and
  Prometheus must show no `legacy_sha` or `legacy_raw` lookup hits for the agreed observation window.
  The production profile must set `PROMOTION_COUPON_LEGACY_FALLBACK_ENABLED` explicitly to `true` or
  `false`; `true` means the migration window is still open, not that cutover is complete.
  Local release smoke must also prove the internal admin inventory route rejects unauthenticated direct
  calls and returns only aggregate cutover evidence when called through a trusted internal admin JWT.
- Promotion retention policy registry is reachable through the gateway for an operator:
  `GET /api/admin/v1/incentives/retention/policies`.
- Promotion retention dry-run is reachable through the gateway for an admin:
  `POST /api/admin/v1/incentives/retention/dry-runs`. It must be aggregate-only, non-destructive, and
  must not expose raw request/response JSON, outbox payload, idempotency key, coupon code, fingerprint,
  profile id, external reference, or row ids.
- Promotion terminal reservation request snapshot redaction is reachable through the gateway for an
  admin only after a fresh approved dry-run:
  `POST /api/admin/v1/incentives/retention/executions`. It must require a persisted `approvalId`,
  `idempotencyKey`, `confirm=true`, and `X-Correlation-Id`; it must return aggregate counts only.
- Promotion retention approval requires a registered successful `cf_promotion` restore drill,
  a fresh matching dry-run hash, reason, change ticket, and reviewer approval by a different human
  actor before execution can run.
- Promotion restore-drill registration must reject non-`cf_promotion` databases, malformed
  `sha256:<64-hex>` artifact hashes, and `checkedAt` values in the future.
- Promotion retention approval must be unique for an active dry-run scope
  (`policyId + scopeKey + dryRunId + resultHash + batchLimit`) so a single dry-run cannot be
  approved into multiple destructive executions.
- Promotion retention execution must persist an `IN_PROGRESS` operation before destructive work,
  transition failed attempts to `FAILED`, and transition the approval to `EXECUTION_FAILED` after
  rollback.
- Prometheus must expose `promotion_retention_execution_stale_in_progress`; alerts must fire for
  failed and stuck destructive retention execution attempts.
- `scripts/postgres-backup-drill.sh` must include `cf_promotion` and `cf_recommendation_ml`. The
  operator must run a restore-check against `cf_promotion` before the first production redaction
  execution and against `cf_recommendation_ml` before ML migration/model-ops releases. The generated
  restore-check evidence must be retained with the release record and used as the source for the
  relevant approval or restore-drill registration.
- Promotion application client bindings are fail-closed: a binding with `allowedOperations=[]` must
  reject every operation. Runtime/admin operation smoke should grant only the needed explicit
  operations, for example `admin`, `evaluate`, `reserve`, `commit`, `cancel`, or `reverse`.
- Promotion coupon brute-force protection is active for coupon-required campaigns: repeated suspicious
  invalid evaluate/reserve attempts must be keyed through HMAC/peppered Redis buckets, return a
  generic `RATE_LIMITED` decline when enforced, create no reservation, and expose only bounded
  `promotion_coupon_abuse_guard_total` metrics.
- Promotion admin coupon operations are rate guarded before expensive preview, parsing, export,
  approval, commit, or generation side effects. Admin preview, dry-run, issue export, approval
  request, approval approve/reject, commit, and generate must key bounded HMAC/peppered Redis buckets
  by application, campaign, actor, source client, and content where applicable, return only
  `429 RATE_LIMITED` when enforced, and expose bounded
  `promotion_admin_operation_rate_guard_total` metrics.
- Promotion coupon import commit is database-concurrency gated through `PromotionServiceJpaSmokeTest`:
  same dry-run/approval plus the same idempotency key must replay to one import operation and one
  coupon write set, crash-window retries must replay from the durable import operation and heal an
  `IN_PROGRESS` idempotency key to `SUCCEEDED`, and different-key double-submit must fail closed
  after the first commit.
- Promotion coupon import operation export is an audit-safe receipt only: CSV and audit payload must
  exclude raw coupon codes, uploaded CSV content, normalized codes, request/content/idempotency
  hashes, response JSON, metadata, fingerprints, and profile PII while preserving receipt fields such
  as import/dry-run/approval ids, status, result hash, row counts, actor/source client, correlation,
  reason, and change ticket.
- Promotion hot quota correctness is release-gated: a dedicated `max_redemptions=1` fixture campaign
  must allow exactly one successful parallel reserve, return `QUOTA_EXHAUSTED` for the rest, create
  exactly one reservation/ledger pair, leave no quota counter outside `[0, limit_count]`, then cancel
  the winning reservation and prove the quota counter is released for reruns. Staging/nightly can
  raise `PROMOTION_SMOKE_HOT_QUOTA_SOAK_WAVES` above `1` to repeat the same bounded race and retain
  `promotion_hot_quota_soak_evidence` JSON with wave counts, winner counts, release evidence, and
  latency summary.
- Outbox relay DLQ is operator-visible: `GET /api/admin/v1/outbox/dead-letters?status=OPEN`
  returns metadata only and must not expose raw payload.
- Outbox relay DLQ live replay/discard requires platform `ADMIN`, an idempotency key, a reason, and
  an approved maker-checker `approvalId`. Approval requests carry action, reason, evidence reference,
  payload hash, request hash, and `OUTBOX_DLT_DUAL_CONTROL_V1`; the requester cannot approve their
  own action. Replay uses the stored topic/key/payload and cannot be redirected by the request body.
- Promotion operator redemption reverse requires maker-checker before production. Operators request
  approval with the target redemption, execution idempotency key, reason, change ticket, subject hash,
  and `NO_RELEASE_ON_COMMITTED_REVERSAL` evidence; a different reviewer approves; execution requires
  the approved `approvalId` and a different executor, then marks the approval executed after the
  compensating `REVERSE` ledger and `incentive.redemption.reversed` outbox event are written.
- Enrollment paid checkout is release-gated by the order boundary: any positive `finalAmount`
  creates a `PAYMENT_PENDING` order and `PENDING_PAYMENT` enrollment, promotion commit is deferred
  until the order is `PAID`, and only checkout/payment service actors can record payment events.
  `PAID` events must include amount, currency, provider, and provider reference; provider/reference
  pairs are unique and idempotent across orders; mismatches, duplicate references, or replay
  conflicts must open assigned remediation cases. Failed commits, manual reviews, and stale
  reservations must also open assigned remediation cases, and successful retries/corrections must
  auto-resolve the open case. Active remediation cases are database-deduped per source order or
  promotion application, while resolved cases remain as history. Each remediation action is mirrored
  into `enrollment_audit_log` with the case id, action, reason code, note, case-status transition,
  and correlation payload without overloading the enrollment status columns.
- Unified incentive ops console must keep the case view anchored: enrollment reconciliation and
  audit can be filtered by enrollment/course/learner/correlation, promotion reservation/redemption
  and coupon evidence by redemption/coupon/enrollment external reference, loyalty evidence by
  account/reward/correlation, remediation cases by learner/course/enrollment/coupon/redemption/
  correlation with assign/note/resolve actions, and outbox/DLT evidence by service/event/aggregate/
  payload hash.
- Loyalty benefit reconciliation must distinguish missing ledger evidence from mismatched ledger
  evidence: promotion earn/reverse and reward reverse rows are not `MATCHED` unless entry type,
  restored points, source reference/reversal link and account evidence align with the expected
  benefit.
- Loyalty reward fulfillment override requires maker-checker before production. Operators request
  approval with target status/reference, reason, idempotency key and correlation id; a different
  reviewer approves in the shared loyalty approval queue; live PATCH requires the approved
  `approvalId` and rechecks redemption scope plus current fulfillment state before execution.
  Fulfillment-only approvals intentionally carry zero point delta, and the database constraint must
  allow that only when the approval metadata operation is `REWARD_FULFILLMENT_OVERRIDE`.
- Outbox relay Prometheus metrics include `outbox_relay_dead_letters_open`,
  `outbox_relay_dead_letter_oldest_age_seconds`, `outbox_relay_replay_total`, and
  `outbox_relay_publish_failures_total`.
- Outbox-relay destructive published-row cleanup remains disabled unless `OUTBOX_PURGE_ENABLED=true`
  is explicitly set after a separate retention execution approval.
- Promotion reservation expiry is multi-replica safe: expired `RESERVED` rows are claimed through a
  JPA native `FOR UPDATE SKIP LOCKED` query, ordered by `expires_at, id`, and each expired
  reservation must produce at most one `EXPIRE` ledger entry.
- Promotion reservation request snapshots are minimized at write time: raw profile ids, external
  references, coupon codes, coupon fingerprints, item ids, item attributes, and free-form attribute
  values must not appear in new `request_json` snapshots or preview audit payloads.
- Production must configure a dedicated `courseflow.promotion.request-snapshot.hash-secret` for
  deterministic HMAC fingerprints before treating snapshot minimization as enterprise-ready.
- `scripts/postgres-backup-drill.sh restore-check ...` passes for at least one service database.

## No-Go Criteria

Do not call a build production-ready if any item below is true:

- A normal operator must paste UUIDs for the golden flow.
- A learner can access unpublished or unenrolled course assessment content.
- A reviewer can approve `learner-preview-checked` without a server-side draft preview of the
  current authoring curriculum.
- Learner runtime selects the latest `course_versions.state=PUBLISHED` row instead of the pinned
  `courses.published_version_no`, or published snapshots still contain draft module status.
- Browser-facing course module routes expose service-only verified completion or cross-student
  progress lookup endpoints.
- Browser-facing enrollment routes expose service-only checkout/payment membership endpoints or
  admin-only promotion remediation, benefit reconciliation, batch, stats, and audit endpoints.
- Quiz attempts can be graded from mutable live question data instead of saved attempt snapshots.
- Grade changes, grading queue state, or final-grade finalize actions lack reason/audit evidence.
- Learner success dashboards list at-risk learners without severity triage or direct remediation
  links to gradebook and certificate eligibility workflows.
- Notification send creates an inbox row with no delivery status.
- Identity privacy export/deactivation lacks audit or token revocation.
- Token converter can issue a user internal JWT from external claims without resolving
  `access-control-service`.
- STS client credentials allow `COURSEFLOW_STS_ALLOWED_CLIENTS=*` in production.
- Downstream services trust `X-User-*` headers without internal JWT attestation.
- `/backoffice/**` service endpoints are reachable without a valid internal JWT.
- Staff roles can read org dashboards or student analytics without matching org/course scope.
- Department/org-scoped roles false-deny child course/section actions because callers omitted
  `ancestorScopes`.
- Chat/WebSocket accepts external bearer tokens directly instead of exchanging the bearer token
  through `identity-token-converter-service`.
- Fresh Liquibase migration fails from an empty database.
- Promotion legacy coupon fallback is disabled while active inventory still has `legacy_sha`,
  `legacy_raw`, or `malformed` rows, or while `promotion_coupon_lookup_total` still reports legacy
  runtime lookup hits in the cutover window.
- Promotion coupon write paths, including coupon import commit, can acquire idempotency, re-evaluate
  import rows, write coupons, write operations, execute approvals, or write audit events after the
  fallback-disabled cutover guard detects active legacy or malformed inventory.
- Any incentive application client binding with an empty `allowedOperations` list grants access to an
  operation instead of denying all operations.
- Gateway exposes browser-facing runtime incentive routes, or `promotion-service` can mint
  `internal:promotion:evaluate|reserve|commit|cancel|reverse` runtime scopes intended for source
  clients such as `checkout-service`.
- Promotion runtime smoke cannot prove `evaluate -> reserve -> commit`, idempotency replay, a
  cancelled reservation replay, reversed redemption replay, operation-scope denial, missing-key and
  payload-conflict idempotency denial, client-binding fixture denials, coupon abuse declines without
  raw coupon leakage, coupon abuse guard burst limiting for evaluate and reserve, commit-after-cancel
  no-redemption behavior, published committed/reversed redemption outbox events, run-scoped
  reconciliation evidence for cancel and commit/reverse, hot quota concurrent reserve evidence, and
  zero open promotion outbox relay DLQ rows.
- Promotion staging smoke runs without `PROMOTION_SMOKE_EXPECTED_CAMPAIGN_CODE`, skips database
  checks, lacks the five required negative application fixtures, lacks the coupon abuse fixture
  campaign/codes/fingerprint config, finds legacy or malformed active coupon inventory in the coupon
  fixture campaign/application scope, lacks the hot quota fixture app/campaign config, cannot
  trigger a bounded coupon abuse guard limit within the configured burst attempts, cannot prove
  exactly one hot quota reserve winner under parallel attempts, finds a fixture shape mismatch, lacks
  a retained log artifact, lacks a retained hot quota soak evidence JSON artifact when configured
  waves exceed `1`, or lacks a retained cutover evidence JSON artifact for the release candidate.
- Promotion observability smoke cannot prove gateway/token-converter/promotion/outbox-relay scrape
  targets are up, promotion runtime metrics are present and increased recently after the run,
  bounded coupon-match metrics increased for all smoke abuse outcomes, bounded coupon abuse guard
  metric evidence exists for the configured guard results in the recent smoke window, current-HMAC
  coupon lookup evidence exists while forbidden legacy lookup paths do not increase, quota
  consumed/exhausted/released and fallback metrics have recent evidence, promotion outbox backlog/DLQ
  metrics are healthy, and critical promotion/outbox/token-converter alerts are not firing.
- Promotion admin import gateway lane is enabled but Prometheus cannot show recent
  `promotion_admin_operation_rate_guard_total{operation="coupon_import_dry_run",result="allowed"}`
  evidence, or guard evidence is required while the gateway lane is disabled.
- Promotion admin gateway issue-export smoke returns a masked CSV but cannot prove a matching
  `coupon.import_issue_export_downloaded` audit row in `incentive_audit_events`, or the audit payload
  contains CSV content, raw coupon codes, normalized codes, HMAC/fingerprint text, idempotency keys, or
  import content hashes.
- Promotion cutover evidence artifact is enabled but missing, has `decision.status=fail`, omits exact
  tenant/application/campaign scope, uses a skipped database check run as production evidence, or
  contains raw coupon codes, normalized codes, HMAC fingerprints, key ids, coupon ids, holder profile
  ids, peppers, idempotency keys, or uploaded CSV content.
- Promotion admin operation guard is disabled in a production profile, has no dedicated key id or
  pepper, accepts a weak/local pepper, or exposes actor/source-client/content identifiers in Redis
  keys or metrics.
- Promotion admin preview, coupon import approval approve/reject, import commit, issue export,
  operation export, dry-run, or coupon generation can proceed to decisioning, batch validation,
  mutation, audit, export generation, or writes after the admin operation rate guard denies the
  request.
- Any retention endpoint deletes, updates, purges, or redacts target business rows without a fresh
  approved dry-run reference, audit event, change ticket, idempotency key, and restore drill.
- Promotion retention execution can run without a persisted approved `approvalId`, with a stale
  dry-run, mismatched result hash, missing `X-Correlation-Id`, invalid restore drill, same approver
  and executor, or without `FOR UPDATE SKIP LOCKED` row claiming.
- More than one active promotion retention approval can exist for the same dry-run/scope/batch.
- A failed promotion retention execution leaves no durable `FAILED` operation, no
  `EXECUTION_FAILED` approval state, or no failure alert surface.
- New promotion reservation snapshots or preview audit payloads store raw profile id, external
  reference, coupon code, coupon fingerprint, item id, item attributes, or free-form request
  attribute values.
- Promotion reservation expiry blocks or double-processes rows when more than one writer replica is
  running.
- Outbox-relay published-row purge is enabled in production without an approved retention execution
  design.
- No metrics endpoint exists for backend services.
- No restore-checked backup evidence JSON exists for the Postgres service database being used by a
  destructive operation, or the restore-drill registration values do not match that evidence.
- Backend tests or admin build fail.
- Mobile `flutter analyze` fails.

## Production Follow-Up

- For notification delivery, local/dev uses `LoggingNotificationDeliveryPort`. Production can switch
  to webhook mode without changing business code:

  ```bash
  NOTIFICATION_DELIVERY_MODE=webhook
  NOTIFICATION_DELIVERY_WEBHOOK_URL=https://notification-provider.example.com/courseflow
  ```

  The webhook endpoint receives notification id, user id, type, title and body. Replace or extend
  this adapter with a native email/push provider when provider-specific tracking is required.
- Add e2e tests that drive the golden flow through the gateway and admin/learner UIs.
- Add OpenTelemetry traces, Kafka lag/DLQ dashboards, backup/PITR checks and incident runbooks.
- Decide tenant model before adding SaaS billing, branding or tenant-scoped quotas.
