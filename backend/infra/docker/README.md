# CourseFlow Backend Local Infra

Run infrastructure only:

```bash
docker compose -f infra/docker/docker-compose.yml up -d
```

This starts Postgres, MongoDB, Redis, Kafka, Kafka Connect, Elasticsearch, Keycloak and MinIO.
Postgres creates one database per service. Service schema is created by each service's Liquibase changelog on first startup.
Postgres is started with logical replication enabled so Debezium can capture source tables for
Elasticsearch projections. Business events still use transactional outbox and Kafka.

To run every backend service as separate local containers, use the full local cluster override:

```bash
docker compose -f infra/docker/docker-compose.yml -f infra/docker/docker-compose.services.yml up --build
```

Optional observability stack:

```bash
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  -f infra/docker/docker-compose.observability.yml \
  up --build
```

Prometheus: `http://localhost:19090`
Grafana: `http://localhost:13000` (default local user/password `admin` / `admin`)

See `infra/docker/LOCAL_CLUSTER.md` for details. Demo data is behind the Liquibase `demo` context; set
`SPRING_LIQUIBASE_CONTEXTS=prod,demo` only for local/demo environments.

## Production Compose security profile

The local service cluster includes `discovery-service`; application services listen on internal port
`8080`, register with discovery, and are not published directly to the host. Browser and app traffic
goes through the gateway. For a production-shaped Compose render, add `docker-compose.prod.yml` after
the local files. The prod override keeps the gateway published, removes direct host port mappings for
databases, brokers and object storage, disables demo storage credentials and requires non-default
secrets.

Validate the prod profile without starting containers:

```bash
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out /tmp/courseflow-internal-jwt.key
openssl rsa -pubout -in /tmp/courseflow-internal-jwt.key -out /tmp/courseflow-internal-jwt.pub

export COURSEFLOW_INTERNAL_JWT_ALGORITHM="RS256"
export COURSEFLOW_INTERNAL_JWT_PRIVATE_KEY="$(cat /tmp/courseflow-internal-jwt.key)"
export COURSEFLOW_INTERNAL_JWT_PUBLIC_KEY="$(cat /tmp/courseflow-internal-jwt.pub)"
export COURSEFLOW_INTERNAL_JWT_VERIFICATION_MODE="jwks"
export COURSEFLOW_INTERNAL_JWT_JWKS_URI="http://identity-token-converter-service:8080/oauth/jwks"
export COURSEFLOW_INTERNAL_SERVICE_TOKEN_MODE="sts"

sts_clients=(
  api-gateway access-control-service user-management-service organization-service
  course-service enrollment-service assignment-service deadline-service announcement-service
  portfolio-service discussion-service notification-service chat-service media-service
  search-service analytics-service recommendation-ml-service gradebook-service quiz-service certificate-service
  peer-review-service live-session-service review-service outbox-relay
)
for client in "${sts_clients[@]}"; do
  env_name="COURSEFLOW_STS_$(printf '%s' "$client" | tr '[:lower:]' '[:upper:]' | tr '-' '_')_SECRET"
  export "$env_name=$(openssl rand -base64 48)"
done

CERTIFICATE_SIGNING_SECRET="replace-with-generated-32-byte-minimum-secret" \
COURSEFLOW_DB_PASSWORD="replace-with-generated-db-password" \
COURSEFLOW_STORAGE_ACCESS_KEY="replace-with-object-storage-access-key" \
COURSEFLOW_STORAGE_SECRET_KEY="replace-with-object-storage-secret-key" \
COURSEFLOW_STORAGE_EXTERNAL_ENDPOINT=https://storage.example.com \
PROMOTION_REQUEST_SNAPSHOT_HASH_SECRET="replace-with-generated-snapshot-hmac-secret" \
KEYCLOAK_ADMIN_PASSWORD="replace-with-generated-keycloak-admin-password" \
KEYCLOAK_PUBLIC_BASE_URL="https://auth.example.com" \
KEYCLOAK_BASE_URL="https://auth.example.com" \
KEYCLOAK_REALM="courseflow" \
KEYCLOAK_ADMIN_CLIENT_ID="keycloak-user-lifecycle" \
KEYCLOAK_ADMIN_CLIENT_SECRET="replace-with-generated-lifecycle-client-secret" \
KEYCLOAK_SETUP_EMAIL_CLIENT_ID="courseflow-admin-web" \
KEYCLOAK_SETUP_EMAIL_REDIRECT_URI="https://admin.example.com/login/callback" \
KEYCLOAK_ISSUER_URI="https://auth.example.com/realms/courseflow" \
KEYCLOAK_JWK_SET_URI="https://auth.example.com/realms/courseflow/protocol/openid-connect/certs" \
KEYCLOAK_AUDIENCE="courseflow-api" \
  scripts/validate-prod-profile.sh --compose
```

For Recommendation ML releases, run Alembic through the dedicated one-shot migration profile before
starting or rolling the API/worker containers:

```bash
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  -f infra/docker/docker-compose.prod.yml \
  --profile migration \
  run --rm recommendation-ml-migrator
```

Render or start the prod-shaped backend cluster from `backend/`:

The Compose commands below assume the same prod variables are exported in the shell or injected by
CI/secret management.

```bash
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  -f infra/docker/docker-compose.prod.yml \
  config
```

```bash
API_GATEWAY_PORT=8080 docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  -f infra/docker/docker-compose.prod.yml \
  up --build
```

After the cluster is reachable, run the security smoke gate with a real Keycloak access token. The
prod profile does not publish `identity-token-converter-service` or domain services on the host, so
run this from a staging runner/container with access to the Compose network, or set the URLs to an
approved temporary port-forward. The gate checks Keycloak token exchange, internal JWKS
verification, STS client credentials, public profile visibility at the gateway, protected profile
summary batch access and direct-service forged-header rejection:

```bash
COURSEFLOW_API_URL=http://localhost:28080/api \
COURSEFLOW_TOKEN_CONVERTER_URL=http://identity-token-converter-service:8080 \
COURSEFLOW_DIRECT_SERVICE_URL=http://course-service:8080 \
COURSEFLOW_SECURITY_SMOKE_ACCESS_TOKEN="<keycloak-access-token-from-approved-login>" \
COURSEFLOW_SECURITY_SMOKE_TOKEN_EXCHANGE_CLIENT_ID=api-gateway \
COURSEFLOW_SECURITY_SMOKE_TOKEN_EXCHANGE_CLIENT_SECRET="$COURSEFLOW_STS_API_GATEWAY_SECRET" \
COURSEFLOW_SECURITY_SMOKE_STS_CLIENT_ID=course-service \
COURSEFLOW_SECURITY_SMOKE_STS_CLIENT_SECRET="$COURSEFLOW_STS_COURSE_SERVICE_SECRET" \
node scripts/keycloak-security-smoke.mjs
```

Optional observability for the prod profile is explicit. Add the local observability file and the prod
observability guard, then provide a non-default Grafana admin password along with the same prod
variables above:

```bash
GRAFANA_ADMIN_PASSWORD="replace-with-generated-grafana-admin-password" \
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  -f infra/docker/docker-compose.observability.yml \
  -f infra/docker/docker-compose.prod.yml \
  -f infra/docker/docker-compose.prod.observability.yml \
  config
```

This profile is a Compose hardening baseline, not a full production platform. Public deployment still
needs TLS termination, external secret management and rotation, managed service credentials,
network policy/firewalls and backup/restore operations.

## Object storage (MinIO)

MinIO is the S3-compatible object store used for uploaded files, video sources/renditions, submission attachments and session recordings.

- S3 API: `http://localhost:9000`
- Web console: `http://localhost:9001` (user `courseflow`, password `courseflow`)
- Buckets created automatically by the `minio-setup` container: `courseflow-media`, `courseflow-recordings`

Services talk to MinIO via `courseflow.storage.*` config (default `provider: minio`, `endpoint: http://localhost:9000`).

## Debezium course search projection

The local infra registers the `courseflow-course-search-cdc` Kafka Connect connector from
`infra/docker/debezium/course-search-cdc-connector-config.json`.

Flow:

```text
cf_course.public.courses
  -> Debezium PostgreSQL connector
  -> Kafka topic courseflow.course.public.courses
  -> search-service consumer
  -> Elasticsearch index courseflow-course-search
```

`outbox-relay` remains responsible for business events such as `course.published` and
`course.completed`; Elasticsearch sync does not depend on outbox rows.

## PostgreSQL settings for Debezium

Local Compose starts Postgres with:

```text
wal_level=logical
max_replication_slots=10
max_wal_senders=10
```

For shared or production environments, apply the same class of settings through the database parameter
group/config file, then restart Postgres if the provider requires it. Also create a dedicated Debezium
user with replication/publication privileges instead of using the application owner account.

Operational notes:

- One Debezium connector normally needs one replication slot; size `max_replication_slots` for all
  connectors plus headroom.
- `max_wal_senders` must be high enough for active logical replication streams.
- Monitor inactive replication slots because retained WAL can grow until disk pressure appears.
- For `pgoutput`, no custom decoder plugin is required on PostgreSQL 10+.

## Backup / restore drill

Run a local backup of every Postgres service database:

```bash
scripts/postgres-backup-drill.sh backup
```

Restore-check one dump into a temporary database:

```bash
scripts/postgres-backup-drill.sh restore-check backups/postgres/<timestamp> cf_promotion
scripts/postgres-backup-drill.sh restore-check backups/postgres/<timestamp> cf_recommendation_ml
```

For promotion retention approvals, use the generated
`backups/postgres/<timestamp>/restore-check-cf_promotion.json` as the source for the restore-drill
registration fields, including `artifactHash` and `checkedAt`.

For Recommendation ML releases, retain
`backups/postgres/<timestamp>/restore-check-cf_recommendation_ml.json`. Its restore probe verifies
the restored database can be opened and that the expected ML Alembic revision plus core ML tables are
present.

## Trust boundary

The gateway strips client-supplied identity/internal headers. After JWT validation it exchanges the
external user JWT with `identity-token-converter-service`, forwards verified `X-User-*` identity
headers, and attaches a short-lived internal JWT in `X-Internal-Authorization`. Downstream services
reject `/internal/**` requests and propagated identity headers unless that internal JWT validates
with the configured internal JWT verifier. Local/dev defaults use HS256 with
`COURSEFLOW_INTERNAL_JWT_SECRET`; the prod profile requires RS256, keeps
`COURSEFLOW_INTERNAL_JWT_PRIVATE_KEY` only on `identity-token-converter-service`, and has domain
services verify with `COURSEFLOW_INTERNAL_JWT_JWKS_URI`. That JWKS URI must be an HTTP(S) URL and
must not point to localhost, loopback, `0.0.0.0`, `::1`, or `host.docker.internal`; internal Docker
service DNS such as `http://identity-token-converter-service:8080/oauth/jwks` is valid for the prod
Compose profile. Internal JWT lifetime policy is bounded by
`COURSEFLOW_INTERNAL_JWT_MAX_TTL_SECONDS` and must stay between 30 and 900 seconds. In the prod profile,
domain service clients
use `InternalJwtService` from `common-library` to request service/user tokens from
`identity-token-converter-service` with their own per-client `COURSEFLOW_STS_*_SECRET`; the converter
keeps the central `COURSEFLOW_STS_CLIENT_SECRETS` and `COURSEFLOW_STS_CLIENT_SCOPES` policy maps and
remains the signing authority. Keep `COURSEFLOW_STS_ALLOWED_SERVICE_SCOPES` explicit and include the endpoint
scopes required by the common filter, such as `internal:identity:resolve`,
`internal:identity:provision`, `internal:authz:check`, `internal:authz:assert-topology`,
`internal:user-directory:*`, `internal:role-assignment:*`, `internal:role-management:*`, `internal:profile:*`,
`internal:promotion:*`, `internal:token-exchange` and `internal:backoffice`. Only the gateway and chat websocket adapter
should receive `internal:token-exchange` by default; only topology-owning services such as
organization-service and course-service should receive `internal:authz:assert-topology`. Promotion runtime
operation scopes should be granted only to trusted source/integrating clients such as `checkout-service`
and `enrollment-service` that also have matching application client bindings; `promotion-service` keeps only
`internal:promotion:admin` by default. The next enterprise hardening step is operational key rotation and e2e
verification against the running cluster.

Keycloak is the only supported edge login authority. The gateway blocks `/api/v1/auth/login`,
`/api/v1/auth/register`, `/api/v1/auth/refresh`, and email verification endpoints with `410 Gone`.

Local Docker imports `infra/docker/keycloak/courseflow-realm.json`, which includes demo users for
developer testing. Production must not mount/import that local realm. Use
`infra/docker/keycloak/courseflow-realm.prod-template.json` as the reviewed starting point, replace
the placeholder web domains, rotate the `keycloak-user-lifecycle` client secret, and provision real
users through the approved IAM/user lifecycle flow. The admin user create/deactivate/privacy-export
paths call Keycloak Admin REST through that lifecycle client, while CourseFlow profile and
authorization data remain in `user-management-service` and `access-control-service`.
`scripts/validate-prod-profile.sh` also validates the production realm template for PKCE, API
audience mapping, password/session/OTP policy, no demo users and no localhost redirects.
The prod profile also requires `ACCESS_CONTROL_RESOLUTION_MODE=required` and an explicit
`COURSEFLOW_STS_ALLOWED_CLIENTS` allowlist. Do not use the local/demo wildcard `*` in production,
because STS client credentials must identify the calling service instead of letting one shared secret
impersonate any service name.
Services running in STS mode also require `TOKEN_CONVERTER_URI`; chat WebSocket auth uses the same
converter to exchange STOMP bearer tokens before trusting internal JWT claims.
Service location is intentionally separate from authentication: gateway routing uses Eureka-backed
`lb://<service-id>` routes, while direct internal service clients use Docker DNS URLs such as
`http://course-service:8080` when they need explicit peer calls.
`access-control-service` always audits denied authorization checks. Set
`ACCESS_CONTROL_AUDIT_AUTHZ_ALLOWED=true` only when the environment needs full allow/deny decision
audit, because this can produce high-volume audit rows.

When local Docker imports `infra/docker/keycloak/courseflow-realm.json`, demo accounts are available
in Keycloak with password `password`:

- `admin@courseflow.local`
- `professor@courseflow.local`
- `ta@courseflow.local`
- `student@courseflow.local`
