# Recommendation Data Domain

This domain owns data products that support recommendation signals, next-action models and
recommendation analytics across enterprise products. CourseFlow LMS is the first product slice.

## Business Capability

Recommendation turns cross-product behavioral, content and eligibility signals into governed data
products for personalization, next-best-action, ranking, experimentation and recommendation quality
measurement.

## First Data Products

| Data product | Purpose | First source or contribution |
|---|---|---|
| `gold.recsys_interactions` | ML-ready interaction rows with event weights and snapshot id. | CourseFlow related-course impressions, clicks and enrollments. |
| `gold.recommendation_quality_daily` | Daily quality, freshness, coverage and outcome metrics for recommendation surfaces. | CourseFlow recommendation tracking and enrollment conversion. |
| `feature.recommendation_candidate_features` | Candidate item, user and context features for serving and training. | Course graph, learner activity and content metadata. |

## First Consumers

- ML services for training, evaluation and online feature lookup.
- Product analytics for surface-level funnel and conversion reporting.
- Reverse ETL for audited updates to application recommendation read models.
- Enterprise reporting for adoption, quality and business outcome KPIs.

## CourseFlow LMS Contribution

CourseFlow LMS contributes the pilot recommendation event stream, learner activity, course graph,
content metadata, enrollment outcomes and model handoff requirements.

## Future Product Onboarding

- Content marketplace recommendation surfaces.
- Ecommerce bundles and next-best-offer use cases.
- Support knowledge-base article recommendations.
- Employee learning and role-based content recommendations.

## Initial Product Slice

```text
recommendation.tracking.v1 topic
  -> bronze.events_recommendation_tracking
  -> silver.learner_activity
  -> gold.recsys_interactions
  -> recommendation ML training handoff
```

## Domain Ownership

| Role | Owner |
|---|---|
| Business owner | enterprise-growth-and-experience-po |
| Technical owner | senior-data-platform |
| Primary consumers | ML services, BI, reverse ETL, product analytics |

## Domain-Specific Rules

- Event types are restricted to `IMPRESSION`, `CLICK` and `ENROLLMENT`.
- Learner and session identifiers must be hashed or tokenized before entering the platform.
- Gold ML datasets must include snapshot id, row count and quality result in the training handoff.
- Reverse ETL back to application read models must be idempotent and auditable.
