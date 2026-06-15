# ML Service Boundary Strategy

## Decision

CourseFlow should use one deployable Python ML service per major ML use case or risk boundary, not
one generic service that serves every model in the system.

The current `recommendation-ml-service` is the first vertical ML service and serves only the
related-course recommendation domain. It should not become the shared home for learner-risk, fraud,
assessment integrity, content understanding, pricing, incentive optimization or other unrelated ML
problems.

## Why Not One Big ML Service

A single generic ML service looks efficient early, but it becomes expensive in an enterprise system:

- Models have different source data, privacy rules, retraining cadence and consumers.
- Online inference latency and availability needs differ by use case.
- A failure in a low-risk model can impact high-risk workflows if they share the same runtime.
- Authorization scopes become too broad and hard to audit.
- Release cadence slows because every model team shares the same deployable.
- DB schemas and migration ownership become tangled.
- Monitoring becomes vague: one service is healthy while one business model is broken.

## Recommended Split

Use a shared Python ML project template and conventions, but separate deployable services:

| Use case | Service | Owned database | Example consumers |
|---|---|---|---|
| Related courses | `recommendation-ml-service` | `cf_recommendation_ml` | `analytics-service`, learner related-course read model |
| Learner risk / success | `learner-risk-ml-service` | `cf_learner_risk_ml` | learner-success dashboard, next-action BFF |
| Fraud / abuse scoring | `fraud-ml-service` | `cf_fraud_ml` | checkout, promotion, loyalty |
| Content understanding | `content-ml-service` | `cf_content_ml` | search, course authoring, media |
| Assessment integrity | `assessment-integrity-ml-service` | `cf_assessment_integrity_ml` | quiz, assignment, gradebook |

The shared part should be a template or small internal library for security, telemetry, model
metadata conventions, test fixtures and Docker/Alembic structure. It should not own business model
state for every use case.

## Split Criteria

Create a new ML service when any of these is true:

- The model serves a different business workflow or bounded context.
- It needs different source datasets or different PII/privacy controls.
- It has different online inference SLA, throughput or cost profile.
- It makes higher-risk decisions that need stricter audit, reason codes or human review.
- It will be trained, deployed or tuned by a different team/cadence.
- It has a separate fallback path and business owner.
- Its failure should not degrade recommendation.

Keep a model inside `recommendation-ml-service` only when it is part of the recommendation decision
stack, such as candidate generation, content-similarity fallback, personalized ranking or re-ranking
for related courses.

## Standard Service Shape

Each ML service should follow the same production shape:

```text
backend/services/<usecase>-ml-service/
  pyproject.toml
  Dockerfile
  alembic.ini
  migrations/
  src/courseflow_<usecase>_ml/
    api/
    core/
    domain/
    repositories/
    schemas/
    services/
    training/
  tests/
```

Each service owns:

- A dedicated database/schema.
- Internal JWT scopes such as `internal:<usecase>-ml:train` and `internal:<usecase>-ml:infer`.
- Training run history, model version metadata and prediction output tables.
- Its own API routes, reason codes, metrics and fallback contract.
- Its own CI gate and Docker image.

## Adding A New Non-Recommendation ML Use Case

1. Define the business decision: prediction target, consumer service, online/offline path and
   fallback behavior.
2. Choose the bounded context owner and name the service, for example `learner-risk-ml-service`.
3. Define service scopes, DB name, API contract and model/version tables.
4. Add a bounded dataset extraction path from the source service or read model. Avoid direct writes
   to another service database.
5. Build a Python service from the standard ML template.
6. Add model quality gates, contract tests, security tests, observability and prod validation.
7. Integrate the consumer service through internal JWT and a timeout/fallback policy.

## Current CourseFlow Decision

`recommendation-ml-service` remains recommendation-only. The phrase "ML platform" in CourseFlow
means shared engineering standards and reusable scaffolding for ML services, not a single runtime
service for every model.

