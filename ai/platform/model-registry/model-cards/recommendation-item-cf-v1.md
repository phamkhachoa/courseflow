# Model Card: Recommendation Item-CF V1

## Identity

| Field | Value |
|---|---|
| Model ID | `recommendation-item-cf-v1` |
| Algorithm | `IMPLICIT_ITEM_CF_V1` |
| Use case | `lms-related-course-recommendation` |
| Product | `lms-courseflow` |
| Owner | `ai-platform` |
| Status | active baseline |

## Intended Use

Generate related-course recommendations from implicit learner-course interactions. This model is the baseline recommendation algorithm for future recommender upgrades such as ALS/BPR, two-tower retrieval and SASRec.

## Not Intended For

- Personalized tutoring.
- Skill mastery estimation.
- Learner risk prediction.
- Cross-tenant recommendation.
- Final ranking for paid commerce offers.

## Inputs

| Input | Description |
|---|---|
| principal hash | Pseudonymous learner identifier |
| course ID | Course interaction target |
| event type | `ENROLLMENT`, `CLICK`, `IMPRESSION` |
| weight | Optional bounded interaction weight |

## Outputs

| Output | Description |
|---|---|
| course ID | Source course |
| related course ID | Recommended related course |
| rank | Rank within source course |
| score | Combined similarity and confidence score |
| similarity | Cosine similarity component |
| support count | Number of co-interaction supports |
| reason code | `ML_CO_ENROLLMENT` or `ML_SIMILAR_LEARNER` |

## Training Method

The trainer builds learner-course vectors from implicit events, computes item-item cosine similarity, blends similarity with support confidence and emits top-N related courses per course.

This is classical memory-based collaborative filtering, not deep learning.

## Governance

- Active activation uses recommendation service model registry and maker-checker governance when auto-activation is disabled.
- Recommendation quality gates prevent candidates from replacing an active model when minimum data and quality thresholds are not met.
- This baseline must remain available for future model comparisons.

## Known Limitations

- Does not learn model parameters.
- Does not use sequence order.
- Has cold-start weakness for new courses.
- Does not use course text, skill taxonomy or learner goals.
- Current production training path still accepts bounded interaction payloads; target enterprise path is DP Gold/offline feature snapshot.

## Monitoring

Current service metrics cover HTTP requests, training runs, active model age, stale active model state, migration readiness, pending approvals and fallback signals through analytics integration.

Future platform metrics should add Recall@K/NDCG eval tracking, drift, feature freshness, catalog coverage and tenant leakage checks.

