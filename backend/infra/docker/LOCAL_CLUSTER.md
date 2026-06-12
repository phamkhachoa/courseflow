# CourseFlow Local Cluster

This setup runs the shared infrastructure plus every backend service as a separate Docker container
on the same Compose network. It is not production deployment; it is a local cluster simulation for
integration testing service boundaries, gateway routing, service-to-service entitlement checks and
Kafka/outbox flow.

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

Each service is also exposed on its configured local port for debugging.

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
LIQUIBASE_CONTEXTS=prod docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  up --build
```

Load demo rows explicitly:

```bash
LIQUIBASE_CONTEXTS=prod,demo docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  up --build
```

## Trust Boundary

- Browser/client traffic goes through `api-gateway`.
- The gateway strips `X-User-*` and `X-Service-Token` headers from inbound requests.
- Internal entitlement checks use `COURSEFLOW_SERVICE_TOKEN` directly between services.
- Default local token is only for this Compose cluster; override it for any shared environment.

## Course Chat

- `chat-service` runs on `8104` and owns course chat rooms/messages in MongoDB database `cf_chat`.
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
