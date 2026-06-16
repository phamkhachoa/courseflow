# CourseFlow LMS Product Onboarding

CourseFlow LMS is the first product onboarded into the enterprise data platform. It proves the
repeatable pattern for future products: source systems publish governed events or CDC feeds, the
platform lands immutable Bronze records, domain teams curate Silver/Gold products, and consumers read
only approved serving layers.

## Product Metadata

| Field | Value |
|---|---|
| Product code | `lms-courseflow` |
| Business sponsor | learning-platform-lead |
| Product owner | courseflow-po |
| Technical owner | courseflow-platform-sa |
| Data steward | enterprise-data-steward |
| Primary domains | learning, assessment, recommendation, commerce |
| First platform slice | course publication, enrollment completion, final grade update, recommendation tracking |

## Enterprise Mapping

| CourseFlow concept | Enterprise reusable concept |
|---|---|
| learner/user | person/customer/employee identity |
| organization/section/cohort | account/org/workforce group |
| course/module/content | product/content/learning asset |
| enrollment/progress | subscription/adoption/activity |
| quiz/assignment/gradebook | assessment/outcome/performance |
| certificate | credential/compliance evidence |
| promotion/loyalty/reward | benefit/incentive/liability |
| recommendation tracking | ML interaction/event signal |

## P0 Data Products

| Layer | Data product | Purpose |
|---|---|---|
| Bronze | `bronze.events_course_published` | Raw course publication events. |
| Bronze | `bronze.events_enrollment_completed` | Raw enrollment completion events. |
| Bronze | `bronze.events_gradebook_final_grade_updated` | Raw final grade update events. |
| Bronze | `bronze.events_recommendation_tracking` | Raw recommendation impression/click/enrollment events. |
| Silver | `silver.learner_activity` | Conformed activity timeline for learning and recommendation use cases. |
| Gold | `gold.recsys_interactions` | Versioned ML training snapshot for related-course recommendations. |

## Guardrail

CourseFlow-specific terms may appear under this product folder and in CourseFlow-owned contracts.
Shared `platform/` capabilities must remain reusable for future products such as CRM, HRIS, finance,
commerce, support and other enterprise systems.
