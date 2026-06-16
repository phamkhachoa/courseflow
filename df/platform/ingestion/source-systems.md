# Enterprise Source Systems

This registry is for the enterprise data platform, not only for CourseFlow LMS.
CourseFlow LMS is the first onboarded product/source domain and should set the
repeatable pattern for future enterprise products.

## Reusable Onboarding Pattern

`source-registry.yaml` is the machine-readable control artifact for this mapping. It binds each
product source to its canonical topic, Bronze target, schema subject, bridge or normalizer mode,
privacy handling and production evidence requirements. This document gives the review narrative and
open gaps behind those registry entries.

For each product source domain, the platform should capture:

- Product and domain ownership.
- Source service and source database ownership.
- Event publication mode: transactional outbox, CDC, HTTP collector, or batch export.
- Current operational consumers so platform ingestion does not break existing flows.
- Bronze target and event contract, when present.
- Privacy, tenant isolation, idempotency, and replay risks.

P0 production onboarding must also apply:

- [Schema registry decision and checklist](schema-registry.md).
- [Bronze landing specification](bronze-landing.md).
- [Source offset, hash and idempotency standard](source-offset-hash-idempotency.md).
- [Source-to-Bronze production readiness](source-to-bronze-readiness.md).

CourseFlow LMS currently uses database-per-service ownership, transactional
outbox tables drained by `outbox-relay`, selected service-local relays, Kafka
consumers, analytics HTTP collectors, and one known CDC-style search feed.

## Review Scope

Reviewed for this minimal mapping:

- `df/contracts/topics/*` and Bronze data product contracts for CourseFlow P0 events.
- `backend/event-contracts/src/main/java/edu/courseflow/events/**`.
- `backend/services/outbox-relay` relay behavior and configured producer databases.
- P0 backend producer/consumer paths for course publication, enrollment completion,
  final grade update, and recommendation tracking.
- P1 backend producer/consumer paths for assignment, quiz, peer review, course
  completion, promotion, loyalty, analytics marketing funnel, and warehouse CSV export.

Not fully reviewed yet:

- Full payload audit for announcement, deadline, certificate, media, review,
  discussion, and live-session outbox topics.
- Debezium/Kafka Connect runtime configs for the search CDC topic.
- Non-Java product sources beyond CourseFlow LMS.
- Schema registry compatibility, because contracts are currently repository
  artifacts rather than enforced broker schemas.

## Priority Semantics

- P0: first enterprise sources to onboard into enterprise Bronze with governed replay, lineage,
  quality gates and PII controls. Enterprise Commerce finance is the first non-LMS proof source.
- P1: next sources that support learner activity, assessment, incentive, loyalty, customer,
  workforce, risk and operational analytics datasets.

## Production-Ready Source Proof

`enterprise-commerce-benefit-settled-outbox` is the first source that can pass
`source_readiness_report.v1`: the source registry entry is `production_ready`, the bridge is direct
canonical and ready, the schema subject is compatible, Bronze ingestion preserves source offsets,
replay is idempotent, change-control is approved, and catalog/OpenLineage evidence proves
topic-to-Bronze lineage.

CourseFlow LMS P0 sources now have a local source bridge preflight. The registered normalizers can
convert raw course publication, enrollment completion, final-grade and recommendation tracking JSONL
into canonical enterprise envelopes, preserve source position and produce a bridge manifest that is
bound to Bronze ingestion by content hash. This moves those sources from unmapped gap to pilot
evidence, but not to production-ready: staging/prod still require live schema registry, offset ledger,
change-control, catalog, OpenLineage and runtime attestations.

## P0 CourseFlow LMS Source Systems

| Priority | Product source domain | Source service | Source DB | Current outbox/topic or source | Current operational consumers | Enterprise data platform target | Main risks / required alignment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | CourseFlow LMS / Course catalog | `course-service` | `cf_course` | Outbox event `course.published`; contract topic exists as `course.published.v1` | `enrollment-service` consumes `course.published` to initialize course capacity | `bronze.events_course_published` | Backend publishes unversioned `course.published` because `outbox-relay` uses `event_type` as topic. Contract expects `course.published.v1`, `orgId`, `coursePublishedAt`, `publishingState`, and optional visibility. Backend payload has course metadata and `publishedAt`, but no explicit `orgId`; ingestion needs a versioned topic bridge or normalizer. |
| P0 | CourseFlow LMS / Enrollment | `enrollment-service` | `cf_enrollment` | Outbox event `enrollment.completed`; contract topic exists as `enrollment.completed.v1` | No direct backend consumer found for `enrollment.completed`; `analytics-service` currently consumes `enrollment.created` for operational metrics and recommendation enrollment signals | `bronze.events_enrollment_completed` | Backend emits raw `studentId` and often lacks `completedAt` and `orgId` in the completion payload. Contract requires `learnerIdHash`, `completedAt`, and tenant isolation. Ingestion needs hashing/tokenization and completion-time normalization before Bronze. |
| P0 | CourseFlow LMS / Gradebook | `gradebook-service` | `cf_gradebook` | Outbox event `gradebook.final_grade.updated`; contract file exists for `gradebook.final_grade.updated.v1` | `certificate-service` consumes `gradebook.final_grade.updated` to auto-issue certificates on passing grades | `bronze.events_gradebook_final_grade_updated` | Contract topic naming now aligns on the underscore canonical form. Backend payload still needs a versioned bridge from `finalGradeId`, `studentId`, `finalScore`, `letter`, `passed`, `status`, `updatedAt` into the approved contract fields `orgId`, `gradebookId`, `learnerIdHash`, `finalGradeValue`, `finalGradeScale`, and `gradeUpdatedAt`. |
| P0 | CourseFlow LMS / Recommendation tracking | `analytics-service` plus `web-next-learning` collector | `cf_analytics` table `recommendation_tracking_events` | Contract topic exists as `recommendation.tracking.v1`; backend currently ingests via HTTP endpoints `/public/analytics/recommendations/events` and `/internal/analytics/recommendations/events` | `analytics-service` stores events, trains/materializes related-course recommendations, and records enrollment signals from `enrollment.created` | `bronze.events_recommendation_tracking` and `silver.learner_activity` | Current source is API/table based, not a Kafka producer. Backend stores `student_id` and `session_id`; contract expects `learnerIdHash`/`sessionIdHash`, `orgId`, and source offsets. Need decide whether platform ingests via a new event collector, analytics outbox, or CDC over `recommendation_tracking_events`. |

## P1 CourseFlow LMS Source Systems

| Priority | Product source domain | Source service | Source DB | Current outbox/topic or source | Current operational consumers | Enterprise data platform target | Main risks / required alignment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | CourseFlow LMS / Assessment submissions | `assignment-service` | `cf_assignment` | Outbox events `submission.created`, `submission.graded` | `analytics-service` consumes `submission.created`; `course-service` consumes created/graded for progress; `portfolio-service` consumes created for evidence; `gradebook-service` consumes graded | Future Bronze assessment and learner activity events | No DF topic contract yet. Payloads include raw `studentId` and assignment/submission details; downstream consumers expect different required fields. Platform should standardize assessment event schema before onboarding. |
| P1 | CourseFlow LMS / Quiz attempts | `quiz-service` | `cf_quiz` | Observed outbox event `quiz.attempt.graded`; event contracts also include quiz attempt records | `gradebook-service` and `course-service` consume `quiz.attempt.graded` | Future Bronze quiz attempt and assessment score events | No DF topic contract yet. Backend emits raw learner id and unversioned topic. Need decide whether submitted and graded are separate platform facts. |
| P1 | CourseFlow LMS / Peer review | `peer-review-service` | `cf_peer_review` | Outbox events `peer_review.assigned`, `peer_review.finalized` | `gradebook-service` consumes `peer_review.finalized` | Future Bronze peer-review assignment/finalized events | Topic naming uses underscore. Some finalized events may omit `courseId`/`maxScore`, and gradebook has fallback logic. Platform should require a complete v1 schema before ingestion. |
| P1 | CourseFlow LMS / Course completion | `course-service` | `cf_course` | Outbox event `course.completed` from learner progress | `enrollment-service` consumes `course.completed` and emits `enrollment.completed` after status transition | Future Bronze learner course completion event; supports P0 enrollment completion lineage | This is an upstream operational trigger for P0 enrollment completion, but not yet a governed platform contract. Payload has raw `studentId` and no org field. |
| P1 | CourseFlow LMS / Incentive redemption | `promotion-service` | `cf_promotion` | Outbox events `incentive.redemption.committed`, `incentive.redemption.reversed` | `loyalty-service` consumes committed/reversed to apply promotion point effects and records inbound DLTs | Future Bronze incentive redemption and finance/loyalty reconciliation events | Payload includes tenant/application, campaign, coupon/profile references, and effects. Needs privacy classification and a DF contract before enterprise ingestion. |
| P1 | CourseFlow LMS / Loyalty ledger and rewards | `loyalty-service` | `cf_loyalty` | Outbox events such as `loyalty.points.earned`, `loyalty.points.burned`, `loyalty.points.reversed`, `loyalty.points.adjusted`, `loyalty.points.expired`, and reward redemption lifecycle events | No current non-loyalty backend consumer confirmed in this pass | Future Bronze loyalty ledger and reward fulfillment events | Event type is derived from ledger entry type or reward lifecycle action. Need explicit topic list, retention policy, and sensitive profile/account handling. |
| P1 | CourseFlow LMS / Marketing funnel analytics | `analytics-service` | `cf_analytics` tables `marketing_funnel_event_receipts`, `marketing_funnel_metrics` | HTTP endpoint `/internal/analytics/marketing/funnel/events`; not outbox/Kafka | `analytics-service` reporting and warehouse CSV export | Future Bronze marketing funnel event receipts and Silver daily funnel metrics | Ingest event receipts, not only aggregated metrics, or replay and attribution will be weak. Safe dimensions are enforced in service code, but no DF topic/data product contract exists yet. |
| P1 | CourseFlow LMS / Analytics warehouse export | `analytics-service` | `cf_analytics` operational read models | HTTP endpoint `/internal/analytics/warehouse/exports` produces CSV for `MARKETING_FUNNEL_DAILY`, `COURSE_COMPLETION_SNAPSHOT`, and `ORG_DASHBOARD_SNAPSHOT` | Admin/service users with analytics export scope | Migration/backfill source only; not a long-term enterprise canonical source | CSV export is an operational convenience, not governed platform ingestion. Treat as temporary backfill/reference until the platform owns Bronze/Silver/Gold pipelines. |
| P1 | CourseFlow LMS / Course search CDC | `course-service` | `cf_course` | Search consumer listens to `${courseflow.search.kafka.course-cdc-topic:courseflow.course.public.courses}` | `search-service` updates search index | Future CDC source for catalog dimension, if needed | Runtime connector config was not fully reviewed. CDC should be used for state replication/dimensions, while outbox remains preferred for business facts. |

## Cross-Cutting Risks

- Topic versioning gap: backend outbox topics are raw `event_type` values, while
  DF contracts use versioned topic names. The platform needs a compatibility
  bridge, producer change, or ingestion-side alias map.
- Envelope gap: many backend events are raw JSON payloads, not the DF shared
  envelope with source topic, partition, offset, published time, and schema id.
- PII and tenant gap: CourseFlow events often carry raw `studentId`, `profileId`,
  or account identifiers. P0 contracts require hashed learner/session ids and
  explicit tenant/org isolation.
- Idempotency: backend consumers use `processed_events` tables or natural keys.
  Platform ingestion must deduplicate by source position when available and by
  event id otherwise.
- Contract status: current DF topic and data product contracts are `DRAFT`.
  Treat this mapping as onboarding guidance, not a claim that schemas are broker
  enforced.
- Enterprise reuse: future products should follow the same sections in this file
  with their own product name, source services, databases, publication modes,
  current consumers, Bronze targets, and privacy risks.

## TODO

- Add a product-level owner field once enterprise ownership taxonomy is agreed.
- Promote the CourseFlow bridge preflight to a production runtime adapter or producer-side
  dual-publish implementation with broker schema registry enforcement.
- Add DF contracts for selected P1 assessment, incentive, loyalty, and marketing
  funnel events.
- Define a product-source onboarding checklist that can be reused by the next
  enterprise product after CourseFlow LMS.
