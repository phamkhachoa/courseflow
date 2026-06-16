# CourseFlow LMS

CourseFlow là hệ thống Learning Management System hướng production cho đào tạo online và vận hành học tập doanh nghiệp. Workspace này cũng là nơi đặt hai platform ngang dùng lại cho tập đoàn: `ai/` cho ML/AI service boundary và `df/` cho Enterprise Data Foundation. LMS là sản phẩm đầu tiên được onboard, không phải giới hạn của nền tảng dữ liệu/AI.

Dự án bao gồm trải nghiệm learner, backoffice admin/instructor/support, mobile app, backend microservices tách boundary rõ ràng cho course, enrollment, assessment, certificate, analytics, notification, incentive và identity/authorization, cùng các nền tảng dữ liệu/ML phục vụ vận hành enterprise.

Mục tiêu của CourseFlow không chỉ là CRUD khóa học. Hệ thống được thiết kế để vận hành được vòng đời đầy đủ: tạo khóa học, review, publish, learner học nội dung, làm quiz/assignment, chấm điểm, cấp chứng chỉ, gửi thông báo, phân tích tiến độ, vận hành ưu đãi và xử lý các ca lỗi cần audit/recovery.

> Trạng thái hiện tại: hệ thống đã có nhiều capability lõi và có thể demo/hardening theo luồng nghiệp vụ chính. Chưa nên gọi production-ready enterprise nếu chưa hoàn tất các P0 gate ở phần [Production Readiness](#production-readiness).

## Mục Tiêu Sản Phẩm

| Nhóm | Mục tiêu |
|---|---|
| Learner | Tìm khóa học, đăng ký, học theo module, theo dõi tiến độ, nhận gợi ý khóa học, làm bài, xem điểm/chứng chỉ và lịch sử benefit |
| Instructor | Soạn course, quản lý curriculum, review readiness, theo dõi học viên, chấm điểm, phản hồi và vận hành lớp học |
| Admin/Ops | Quản lý user, role, course lifecycle, enrollment, notification, incentive, audit, reconciliation và remediation |
| Platform | Tách service ownership, event-driven integration, internal JWT, observability, DLT/outbox governance, AI model ops, Data Foundation và khả năng mở rộng |

## Source Map

```text
courseflow/
  backend/                 Spring Boot services, gateway, workers, infra, docs
    common-library/        Shared response/error/correlation/security utilities
    event-contracts/       Immutable event records shared across services
    services/              Business microservices
    infra/                 Local Docker Compose, Keycloak realm, observability
    docs/                  Backend architecture, API, incentive, operation docs
  web/
    next-learning/         Learner/public web app using Next.js
    react-admin/           Backoffice/admin console using React + Vite
  app/                     Flutter learner mobile app
  ai/                      Python ML/AI services, model ops, training and serving
    recommendation-ml-service/
                            First ML use case: related-course recommendation
  df/                      Group-wide Enterprise Data Foundation
    contracts/             Event, topic, data-product and policy contracts
    products/              Product onboarding: LMS, commerce, billing, CRM, support, HRIS
    domains/               Enterprise data mesh domains and semantic ownership
    platform/              Ingestion, lakehouse, quality, catalog, serving, runtime, ops
    src/enterprise_df/     Local validators and operating CLIs
  docs/                    Cross-cutting engineering and review notes
```

## Kiến Trúc Tổng Thể

CourseFlow được tổ chức theo ba lớp lớn:

- Product systems: web/mobile/backend services sở hữu nghiệp vụ LMS và các transaction source of truth.
- AI platform: Python service boundary cho huấn luyện, registry, activation, inference và model ops; use case đầu tiên là gợi ý khóa học liên quan.
- Enterprise Data Foundation: nền tảng dữ liệu dùng chung cấp tập đoàn cho ingestion, lakehouse, semantic serving, governance, quality, lineage, reconciliation, BI và feature datasets.

```mermaid
flowchart TB
  subgraph Experience["Experience Layer"]
    LearnerWeb["Learner Web<br/>Next.js"]
    AdminWeb["Admin Web<br/>React/Vite"]
    MobileApp["Mobile App<br/>Flutter"]
    BI["BI / Executive / Ops Analytics"]
  end

  subgraph Edge["Edge, Identity And Access"]
    Gateway["api-gateway"]
    Keycloak["Keycloak<br/>OIDC/SSO/MFA"]
    Converter["identity-token-converter-service"]
    Access["access-control-service"]
    Users["user-management-service"]
  end

  subgraph LMS["CourseFlow Product Backend"]
    Course["Course / Authoring / Publish"]
    Enrollment["Enrollment / Learner Runtime"]
    Assessment["Assignment / Quiz / Gradebook / Certificate"]
    Engagement["Notification / Discussion / Live / Review"]
    Incentive["Promotion / Loyalty / Coupon / Incentive Ops"]
    Analytics["analytics-service<br/>read models and recommendation integration"]
    Search["search-service"]
    Relay["outbox-relay"]
  end

  subgraph Stores["Operational Data Plane"]
    OLTP["Owned PostgreSQL schemas"]
    Docs["MongoDB document domains"]
    Redis["Redis cache"]
    Elastic["Elasticsearch"]
    Kafka["Kafka event backbone"]
    Debezium["Debezium CDC"]
  end

  subgraph AI["AI Platform (ai/)"]
    MLApi["recommendation-ml-service<br/>FastAPI internal API"]
    MLWorker["Training worker"]
    ModelRegistry["Model registry and active versions"]
    Inference["Inference endpoints"]
    FeatureConsumer["Feature/dataset consumer"]
  end

  subgraph DF["Enterprise Data Foundation (df/)"]
    SourceRegistry["Source registry and contracts"]
    Ingestion["CDC / outbox / batch ingestion"]
    Bronze["Bronze raw lakehouse"]
    Silver["Silver conformed domains"]
    Gold["Gold marts and semantic datasets"]
    Quality["Quality, lineage, catalog, access policy"]
    Serving["Trino P0 / Dremio candidate"]
    ControlTower["Data Product Control Tower"]
  end

  LearnerWeb --> Gateway
  AdminWeb --> Gateway
  MobileApp --> Gateway
  Gateway --> Keycloak
  Gateway --> Converter
  Converter --> Access
  Gateway --> Course
  Gateway --> Enrollment
  Gateway --> Assessment
  Gateway --> Engagement
  Gateway --> Incentive
  Gateway --> Analytics
  Gateway --> Search
  Access --> Users

  Course --> OLTP
  Enrollment --> OLTP
  Assessment --> OLTP
  Engagement --> Docs
  Incentive --> OLTP
  Analytics --> OLTP
  Search --> Elastic
  Course --> Relay
  Enrollment --> Relay
  Assessment --> Relay
  Incentive --> Relay
  Relay --> Kafka
  OLTP --> Debezium
  Debezium --> Kafka

  Analytics --> MLApi
  MLApi --> Inference
  MLApi --> ModelRegistry
  MLWorker --> ModelRegistry
  FeatureConsumer --> MLWorker
  Inference --> Analytics

  Kafka --> SourceRegistry
  SourceRegistry --> Ingestion
  Ingestion --> Bronze
  Bronze --> Silver
  Silver --> Gold
  Gold --> Serving
  Gold --> FeatureConsumer
  Quality --> Bronze
  Quality --> Silver
  Quality --> Gold
  Serving --> BI
  ControlTower --> Quality
```

### Data And AI Flow

```mermaid
flowchart LR
  ProductEvents["Product events<br/>LMS, commerce, billing, CRM, support, identity"] --> Contracts["Versioned contracts<br/>schema, owner, PII, SLA"]
  Contracts --> Ingest["Governed ingestion<br/>outbox, CDC, batch, source bridge"]
  Ingest --> Bronze["Bronze<br/>append-only raw events"]
  Bronze --> Silver["Silver<br/>conformed enterprise domains"]
  Silver --> Gold["Gold<br/>certified marts and feature datasets"]
  Gold --> BI["BI / finance reconciliation / ops reports"]
  Gold --> Features["Feature datasets<br/>offline ML inputs"]
  Features --> Train["AI training jobs"]
  Train --> Registry["Model registry<br/>candidate, approved, active"]
  Registry --> Serve["Internal inference APIs"]
  Serve --> ProductUX["Product UX/BFF<br/>recommendations, next action, risk signals"]
  Serve --> Audit["Model/audit evidence<br/>version, score, reason, generatedAt"]
  Audit --> Control["DF Control Tower<br/>quality, lineage, access, release evidence"]
```

Architecture rules:

- Backend services own transactional state. DF and AI must not read product OLTP databases directly.
- Integration uses API contracts, events, outbox, CDC and governed source bridges, not shared tables.
- AI models consume approved feature datasets or bounded hashed interaction payloads, then return scored outputs with model version, reason code and audit metadata.
- DF is group-wide. New enterprise products onboard through source registry, contracts, quality gates and catalog/lineage evidence.

## Product Surfaces

| Surface | Primary users | Main jobs |
|---|---|---|
| Learner Web | Public visitors, students | Course discovery, course detail, learning runtime, next action, related courses, reviews, progress |
| Admin Web | Admin, instructor, operator, support | Course authoring, publish governance, grading, learner success, notification, incentive ops |
| Mobile App | Students | Learning on the go, notification, progress and lightweight learner workflows |
| Backend APIs | Web/mobile/internal services | Identity propagation, domain workflows, reporting, events, audit and operational controls |
| AI Platform | ML engineer, platform engineer, product services | Training jobs, model registry, activation approval, inference APIs and model audit |
| Enterprise Data Foundation | Data platform, data steward, BI, finance, risk, AI teams | Data contracts, ingestion, lakehouse, quality, lineage, semantic datasets, feature datasets and Control Tower |

## Capability Overview

### Core LMS

- Course catalog, module/item authoring, material metadata and learner-facing course pages.
- Publish governance with draft/review/published state, immutable published curriculum snapshot and rollback/versioning direction.
- Enrollment, roster, waitlist/capacity decision boundary and learner progress.
- Learner Course Player and Next Action BFF direction for “học tiếp gì bây giờ”.
- Assignment, quiz, gradebook, peer review and certificate services for assessment lifecycle.
- Live session, discussion, announcement, deadline, portfolio and review domains for learning operations.

### Identity, Access And User Boundary

CourseFlow target architecture uses:

- Keycloak for enterprise IAM: login, SSO, MFA, password/session policy, federation and external access tokens.
- `identity-token-converter-service` for exchanging verified Keycloak tokens into short-lived CourseFlow internal JWTs.
- `access-control-service` for CourseFlow authorization: roles, permissions, scoped grants, product user status and authorization audit.
- `user-management-service` for profile/directory data: display name, avatar, bio, locale/timezone, profile visibility and admin user lifecycle facade.

The old custom password/JWT identity boundary is no longer the target architecture. If any `identity-service` style dependency still exists, treat it as legacy/compatibility debt and remove it only after a dependency audit confirms no active route, client or migration still depends on it.

### Enrollment, Commerce And Incentives

- Enrollment owns learner/course enrollment state and should not become the payment source of truth.
- Paid checkout/order boundary is required before production for any `finalAmount > 0`: order/payment must be authoritative, and promotion commit should happen only after payment success.
- Promotion service covers campaign/version/publish/rollback, coupon catalog/import, evaluate/reserve/commit/reverse runtime and audit/outbox.
- Loyalty service covers account/ledger/reward/tier skeleton, approval, benefit lifecycle direction and reconciliation hooks.
- Incentive production operation still needs unified support console, remediation, reconciliation, maker-checker and DLT governance before enterprise launch.

### Analytics And Recommendations

- `analytics-service` owns reporting read models, learner tracking ingestion, manual curated related courses and the learner-facing related-course read model.
- `ai/recommendation-ml-service` is the first standalone Python ML project under the AI platform. It owns recommendation training pipelines, model registry, active model version, implicit collaborative filtering scores and internal inference endpoints.
- Related course recommendation now runs in two layers: analytics sends bounded, hashed training interactions to the Python ML service; ML trains/version-activates an item-item implicit collaborative filtering model; analytics materializes `source=ML` rows for learner display.
- Recommendation ML training accepts only `ENROLLMENT`, `CLICK` and `IMPRESSION` interaction event types; input is canonicalized before queue persistence so unsupported training data fails fast.
- If ML is disabled, unavailable or returns insufficient data, analytics falls back to the deterministic behavioral/co-enrollment heuristic so learner course pages do not go empty.
- Every generated recommendation carries source, reason code, model version, score and generated time. Public related-course output still filters to published courses only.

### Enterprise Data Foundation And AI Platform

- `df/` is the group-wide data foundation, not an LMS-only warehouse. CourseFlow LMS is the pilot product; commerce, billing, CRM, support, identity and workforce can onboard through the same registry and contract model.
- DF owns Bronze/Silver/Gold data products, event/topic contracts, source activation evidence, quality checks, catalog/lineage, semantic metrics, runtime readiness, access policy and Data Product Control Tower.
- AI owns model lifecycle concerns: training, model registry, activation workflow, inference, model audit, feature consumption and production model readiness.
- Recommendation is only the first AI use case. Future ML use cases should be added as new model/use-case modules inside the shared AI platform boundary when they can reuse model ops, security, observability and feature governance.
- DF provides governed feature datasets and semantic data products to AI. AI feeds scored outputs back to product services through internal APIs or governed activation datasets.

### Operations, Audit And Recovery

- Transactional outbox and Kafka are used for business-event integration.
- Debezium CDC is used where a projection should follow source tables, such as course search sync.
- DLT/outbox governance is a production gate: payload hash, topic/offset, retry count, error class, idempotent replay/discard and audit must be visible to operators.
- High-risk operations such as reverse redemption, reward override, large adjustment, expiry execution and DLT replay/discard need reason, evidence, threshold policy and maker-checker.

## Backend Architecture

CourseFlow backend is a set of Spring Boot services with explicit data ownership. Services should not share LMS business rules through common modules. Shared modules stay narrow:

| Module | Allowed responsibility |
|---|---|
| `common-library` | Response wrapper, error model, correlation id, service-info, narrow security helpers |
| `event-contracts` | Immutable event records only |

Current service map:

| Domain | Services |
|---|---|
| Platform/security | `api-gateway`, `discovery-service`, `identity-token-converter-service`, `access-control-service`, `user-management-service` |
| Course/runtime | `course-service`, `enrollment-service`, `organization-service`, `media-service`, `search-service` |
| Assessment | `assignment-service`, `quiz-service`, `gradebook-service`, `certificate-service`, `peer-review-service` |
| Engagement | `announcement-service`, `deadline-service`, `discussion-service`, `chat-service`, `notification-service`, `live-session-service`, `review-service`, `portfolio-service` |
| Analytics/incentive | `analytics-service`, `promotion-service`, `loyalty-service`, `outbox-relay` |
| AI/ML | `ai/recommendation-ml-service` |

Standard service package shape:

```text
edu.courseflow.<service>/
  config/          Framework config, security, clients, messaging
  controller/      REST API boundary
  service/         Use cases and transaction scripts
  repository/      Persistence ports/adapters
  model/           Entities/documents/domain models
  dto/             Request/response DTOs
```

## Backend Runtime Architecture

Sơ đồ này tập trung vào runtime backend của CourseFlow. Sơ đồ tổng thể ở trên thể hiện thêm lớp AI và Enterprise Data Foundation.

```mermaid
flowchart LR
  Browser["Web/Mobile Client"] --> Gateway["api-gateway"]
  Gateway --> Keycloak["Keycloak"]
  Gateway --> Converter["identity-token-converter-service"]
  Converter --> Access["access-control-service"]
  Gateway --> Domain["Domain service"]
  Domain --> Authz["access-control-service /internal/authz/check"]
  Domain --> Store["Owned database"]
  Domain --> Outbox["outbox_events"]
  Outbox --> Relay["outbox-relay"]
  Relay --> Kafka["Kafka"]
  Kafka --> Consumers["Search / Analytics / Notification / Gradebook / Certificate"]
  Store --> Debezium["Debezium CDC"]
  Debezium --> Kafka
```

Important rules:

- `api-gateway` is the only client entrypoint and strips client-supplied identity headers.
- Domain services trust propagated identity only when a valid short-lived internal JWT is present.
- Each service owns its database/schema and exposes contracts through API/events, not direct table access.
- Search and analytics are read-model boundaries; source-of-truth data remains in the owning service.
- Gateway stays thin: routing, auth, CORS/rate limit, correlation id and header hardening.

## API Route Convention

| Gateway path | Audience |
|---|---|
| `/api/v1/**` | Learner/public API; public GET where explicitly allowed, otherwise JWT |
| `/api/admin/v1/**` | Admin/backoffice API; operator role required before routing |
| `/internal/**` | Service-to-service only; internal JWT/scope required |
| `/ws/**` | Realtime/WebSocket endpoints |

Service-internal controllers may use `/public/**`, `/internal/**`, `/backoffice/**` or service-specific paths, but gateway-facing API should keep the audience-first convention.

## Tech Stack

| Layer | Technology |
|---|---|
| Learner web | Next.js 15, React 19, TypeScript, TanStack Query, Tailwind CSS |
| Admin web | React 19, Vite, TypeScript, TanStack Query, Tailwind CSS, lucide-react |
| Mobile | Flutter |
| Backend | Java 21, Spring Boot 3, Spring Cloud Gateway |
| Identity/Auth | Keycloak OAuth2/OIDC, internal JWT/JWKS, CourseFlow access-control |
| Data | PostgreSQL per service, MongoDB for document/chat-style domains, Redis |
| Search | Elasticsearch, Spring Data Elasticsearch |
| Events | Kafka, transactional outbox, Debezium CDC, Kafka Connect |
| Storage | MinIO/S3-compatible object storage |
| AI/ML | Python 3.11+, FastAPI, SQLAlchemy, Alembic, NumPy, scikit-learn, Prometheus metrics |
| Data Foundation | Kafka/outbox/CDC, Schema Registry, S3-compatible object storage, Apache Iceberg, Spark/dbt direction, Trino P0 serving |
| Data serving candidates | Dremio for semantic lakehouse/BI after POC; TiDB + TiFlash only for measured product-level HTAP needs |
| Migration/Local infra | Liquibase, Docker Compose |

## Local Development

Start local infrastructure from `backend/`:

```bash
cd backend
docker compose -f infra/docker/docker-compose.yml up -d
```

Start the full backend cluster:

```bash
cd backend
docker compose \
  -f infra/docker/docker-compose.yml \
  -f infra/docker/docker-compose.services.yml \
  up --build
```

Run learner web:

```bash
cd web/next-learning
COURSEFLOW_API_URL=http://localhost:28080/api \
NEXT_PUBLIC_API_URL=http://localhost:28080/api \
npm run dev
```

Run admin web:

```bash
cd web/react-admin
VITE_API_GATEWAY_URL=http://localhost:28080/api npm run dev
```

Default local URLs:

| Component | URL |
|---|---|
| Learner web | `http://localhost:3000` |
| Admin web | `http://localhost:5173` |
| API gateway | `http://localhost:28080/api` |
| Keycloak | `http://localhost:18080` |
| Kafka Connect | `http://localhost:18083` |
| Elasticsearch | `http://localhost:9200` |
| MinIO console | `http://localhost:9001` |

Check course-search Debezium connector:

```bash
curl http://localhost:18083/connectors/courseflow-course-search-cdc/status
```

## Verification

Backend:

```bash
cd backend
mvn test
```

Targeted service gates:

```bash
cd backend
mvn -pl services/analytics-service -am test
mvn -pl services/access-control-service,services/user-management-service,services/notification-service -am test
mvn -pl services/outbox-relay -am test
```

AI service:

```bash
cd ai/recommendation-ml-service
make test
```

Enterprise Data Foundation:

```bash
cd df
make check
```

Learner web:

```bash
cd web/next-learning
npm run lint
npm test
npm run build
```

Admin web:

```bash
cd web/react-admin
npm run lint
npm test
npm run build
```

Product hardening and smoke scripts are documented in [`backend/docs/operations/product-hardening-sprint.md`](backend/docs/operations/product-hardening-sprint.md).

## Production Readiness

CourseFlow should not be treated as enterprise production-ready until these P0 gates are complete and verified:

| P0 gate | Required outcome |
|---|---|
| Production Security Gate | Service-to-service JWT, access-control model, user-management boundary and old identity mechanism fully retired |
| Core LMS Authoring | Course Builder, module/item CRUD, readiness checks and preview are operator-ready |
| Publish Governance | Review audit, checklist, diff, rollback and immutable snapshot guarantee |
| Learner Runtime | Course Player and Learner Next Action BFF are stable for paid/public learning |
| Paid Checkout / Order Boundary | Paid enrollment requires valid order/payment source of truth before activation |
| Incentive Ops | Unified support console for enrollment, promotion, coupon, loyalty, outbox/DLT and audit lookup |
| Remediation Workflow | `COMMIT_FAILED`, `MANUAL_REVIEW`, expired `RESERVED` and similar cases have assignee, notes, actions, retries, SLA age and audit |
| Financial / Benefit Reconciliation | Detect and resolve drift across promotion, loyalty, enrollment, reward and points ledger |
| Maker-checker | High-risk operations require reason, evidence, thresholds and separate approver |
| Outbox/DLT Governance | Unified DLT queue with idempotent replay/discard, payload hash, retry metadata and audit |
| AI/ML Production Gate | Internal JWT, async training worker, model registry, maker-checker activation, active-model readiness, model audit, observability and fallback contract are verified |
| Enterprise Data Foundation Gate | Source contracts, readiness bundle, Bronze/Silver/Gold quality, catalog/lineage/access policy, Control Tower report and runtime evidence are verified before production use |

P1 after P0:

- Reward fulfillment lifecycle with provider adapter, webhook callback, retry/backoff, SLA and learner-visible status.
- Loyalty tiers with qualification window, downgrade/grace policy, audit and learner tier progress.
- Coupon distribution lifecycle with cohort/section/course/segment targeting, preview, approval, notification and revoke.
- Learner Incentive Hub for coupon, points, reward, pending benefit, history, eligibility reason and support case.
- Promotion simulation before publish.
- Refund/drop policy matrix for discount reverse, points clawback and reward reversal.
- Learner Success + Assessment Ops: at-risk dashboard, grading queue, certificate eligibility and grade publish audit.

P2 after core stability:

- Advanced stacking policy, marketing funnel analytics, fraud scoring, warehouse/export expansion, A/B incentive testing, realtime SSE, cohort/learning path expansion and enterprise component kit.

## Key Documents

- Backend architecture: [`backend/docs/architecture/backend-architecture.md`](backend/docs/architecture/backend-architecture.md)
- Keycloak enterprise adoption: [`backend/docs/architecture/keycloak-enterprise-adoption.md`](backend/docs/architecture/keycloak-enterprise-adoption.md)
- Incentive platform design: [`backend/docs/architecture/incentive-platform-design.md`](backend/docs/architecture/incentive-platform-design.md)
- Loyalty bounded context ADR: [`backend/docs/architecture/loyalty-bounded-context-adr.md`](backend/docs/architecture/loyalty-bounded-context-adr.md)
- AI recommendation service: [`ai/recommendation-ml-service/README.md`](ai/recommendation-ml-service/README.md)
- Enterprise Data Foundation: [`df/README.md`](df/README.md)
- DF serving platform: [`df/platform/serving/README.md`](df/platform/serving/README.md)
- DF runtime and IaC: [`df/platform/runtime/README.md`](df/platform/runtime/README.md)
- API overview: [`backend/docs/api/courseflow-api.md`](backend/docs/api/courseflow-api.md)
- Product hardening sprint: [`backend/docs/operations/product-hardening-sprint.md`](backend/docs/operations/product-hardening-sprint.md)
- Engineering conventions: [`docs/engineering-conventions.md`](docs/engineering-conventions.md)
- Architecture review backlog: [`docs/architecture-review-backlog.md`](docs/architecture-review-backlog.md)
- Open-source research notes: [`docs/open-source-research.md`](docs/open-source-research.md)
