# CourseFlow Local Cluster

This setup runs the shared infrastructure plus every backend service as a separate Docker container
on the same Compose network. It is not production deployment; it is a local cluster simulation for
integration testing service boundaries, gateway routing, service-to-service entitlement checks and
Kafka/outbox flow.

Application services listen on internal port `8080`, register with `discovery-service`, and are not
published directly to the host. Browser/app traffic should enter through `api-gateway`.

## Start

From `v2/courseflow/backend`:

```bash
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  up --build
```

Gateway:

```text
http://localhost:28080
```

If port `28080` is already in use:

```bash
API_GATEWAY_PORT=8080 docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  up --build
```

Internal services are reachable by other containers through Docker DNS, for example
`http://course-service:8080`. For host debugging, prefer gateway routes or run a temporary tool
container on the Compose network.

For production-shaped Compose validation, use `docker-compose.prod.yml` as an override instead of
changing these local files. The prod profile removes direct host ports for internal services and
requires non-default secrets before Compose will render.

## Web UIs

The Compose cluster starts backend services only. Run the web apps from the repo root in separate
terminals and point them at the gateway base path `/api`.

If the gateway is on the default port:

```bash
cd v2/courseflow/web/react-admin
VITE_API_GATEWAY_URL=http://localhost:28080/api npm run dev
```

```bash
cd v2/courseflow/web/next-learning
COURSEFLOW_API_URL=http://localhost:28080/api \
NEXT_PUBLIC_API_URL=http://localhost:28080/api \
npm run dev
```

If you started the backend with another `API_GATEWAY_PORT`, replace `28080` with that port.

Open:

```text
Admin web:   http://localhost:5173/login
Learner web: http://localhost:3000
Gateway:     http://localhost:28080/api
```

Do not put `/v1` in the environment variable. Frontend code already calls `/v1/...` for learner
APIs and `/admin/v1/...` for backoffice APIs.

## Demo Data

Local Compose loads demo rows by default (`prod,demo`) so the admin and learner UIs have accounts/data
to exercise. For a production-safe schema-only run:

```bash
SPRING_LIQUIBASE_CONTEXTS=prod docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  up --build
```

Load demo rows explicitly:

```bash
SPRING_LIQUIBASE_CONTEXTS=prod,demo docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  up --build
```

## Production Profile Dry Run

The prod profile is a security-oriented Compose render for shared environments. It keeps only the API
gateway published by default and blocks blank/default external JWT, internal JWT, certificate-signing
and DB password values. It also switches Liquibase to `prod` unless overridden.

From `backend/`, validate without booting the cluster:

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

Render the prod config:

The Compose command assumes the same prod variables are exported in the shell or injected by
CI/secret management.

```bash
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  -f infra/docker/docker-compose.prod.yml \
  config
```

If Prometheus/Grafana should be exposed too, include the observability files and set
`GRAFANA_ADMIN_PASSWORD`; otherwise leave them out.

## Debezium Search Sync

Course catalog search is projected through Debezium directly from source tables. Business workflows
still use transactional outbox and `outbox-relay`.

```text
cf_course.public.courses -> Debezium/Kafka Connect -> Kafka -> search-service -> Elasticsearch
```

The one-shot `debezium-course-search-setup` container registers/updates the Kafka Connect connector
named `courseflow-course-search-cdc`.

Useful local checks:

```bash
curl http://localhost:18083/connectors/courseflow-course-search-cdc/status
```

```bash
docker exec courseflow-kafka kafka-console-consumer \
  --bootstrap-server kafka:29092 \
  --topic courseflow.course.public.courses \
  --from-beginning
```

The `course.published` topic is still owned by the business outbox flow; the ES projection listens to
the Debezium table topic above.

## Observability

Start the local cluster with Prometheus and Grafana:

```bash
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  -f infra/docker/docker-compose.observability.yml \
  up --build
```

Open:

```text
Prometheus: http://localhost:19090
Grafana:    http://localhost:13000
```

Spring services expose metrics at `/actuator/prometheus`; Prometheus scrape targets are defined in
`infra/observability/prometheus.yml`. Basic alert rules live in `infra/observability/alerts.yml`,
and Grafana provisions the Prometheus datasource from `infra/observability/grafana/provisioning`.

## Backup / Restore Drill

Run a local dump of all service-owned Postgres databases:

```bash
scripts/postgres-backup-drill.sh backup
```

Validate a dump by restoring it into a temporary local database:

```bash
scripts/postgres-backup-drill.sh restore-check backups/postgres/<timestamp> cf_promotion
scripts/postgres-backup-drill.sh restore-check backups/postgres/<timestamp> cf_recommendation_ml
```

The restore check writes `restore-check-cf_promotion.json` in the backup directory. For promotion
retention testing, register the restore drill from that file instead of typing the artifact hash by
hand.

The Recommendation ML restore check writes `restore-check-cf_recommendation_ml.json` and also probes
the restored Alembic revision plus core ML tables. Keep that evidence with any release that changes
ML migrations, model registry storage, or activation approval storage.

## Trust Boundary

- Browser/client traffic goes through `api-gateway`.
- Gateway routes use service discovery (`lb://<service-id>`), so it does not need static service
  host ports.
- The gateway strips client-supplied identity/internal headers from inbound requests.
- After validating user JWTs, the gateway exchanges them for a short-lived internal JWT and forwards
  `X-User-*` plus `X-Internal-Authorization`.
- Downstream services reject `/internal/**` calls and propagated identity headers unless that
  internal JWT validates with the configured verifier. Local/dev defaults use HS256 with
  `COURSEFLOW_INTERNAL_JWT_SECRET`; the prod profile requires RS256, keeps
  `COURSEFLOW_INTERNAL_JWT_PRIVATE_KEY` only on `identity-token-converter-service`, and has domain
  services verify with `COURSEFLOW_INTERNAL_JWT_JWKS_URI`.
- Direct service clients use `InternalJwtService` from `common-library` to attach service/user
  internal JWTs. In the prod profile they request those tokens from `identity-token-converter-service`
  with their own per-client `COURSEFLOW_STS_*_SECRET`; the converter keeps the central
  `COURSEFLOW_STS_CLIENT_SECRETS` and `COURSEFLOW_STS_CLIENT_SCOPES` policy maps. Only the gateway
  and chat websocket adapter receive `internal:token-exchange` by default. Only topology-owning
  services such as organization-service and course-service receive `internal:authz:assert-topology`,
  promotion runtime operation scopes are granted only to trusted source/integrating clients such as
  `checkout-service` and `enrollment-service` while `promotion-service` keeps `internal:promotion:admin` by default,
  and role/permission policy reads require `internal:role-management:read` rather than generic
  `internal:service`. The next hardening step is operational key rotation and e2e verification
  against the running cluster.
- For a running OIDC cluster, run `node scripts/keycloak-security-smoke.mjs` from a context that can
  reach the gateway, token converter and one direct domain service.
- Custom password-login services are not part of the local Keycloak cluster.

## Course Chat

- `chat-service` runs as an internal `8080` service and owns course chat rooms/messages in MongoDB database `cf_chat`.
- Learner/admin REST traffic goes through `/api/v1/chat/**` or `/api/admin/v1/chat/**`.
- Realtime chat uses STOMP over WebSocket at `ws://localhost:28080/ws/chat`.
- STOMP `CONNECT` must carry `Authorization: Bearer <accessToken>`; the service validates the JWT and checks course enrollment/staff access before allowing subscribe/send.
- Redis pub/sub can be added later when `chat-service` has multiple replicas; MongoDB remains the durable source of truth.

## Stop

```bash
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  down
```

Remove volumes:

```bash
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  down -v
```
