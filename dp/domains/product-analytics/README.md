# Product Analytics Data Domain

This domain owns funnel, cohort, retention, feature usage, experimentation and product health data
products across web, mobile, admin and API experiences.

## Business Capability

Product Analytics provides trusted behavioral datasets for product managers, UX researchers,
engineering leaders and growth teams to understand adoption, engagement, conversion, retention,
quality and experiment outcomes.

## First Data Products

| Data product | Purpose | First source or contribution |
|---|---|---|
| `gold.product_usage_daily` | Daily active usage, sessions, feature events and engagement measures. | CourseFlow web, mobile and admin clickstream. |
| `gold.experiment_metrics_daily` | Experiment exposure, conversion, guardrail and segment metrics. | CourseFlow enrollment funnel and recommendation surface experiments. |
| `gold.feature_adoption_daily` | Feature adoption, retention and usage depth by product area. | CourseFlow learning runtime, assessments, reviews and admin workflows. |

## First Consumers

- Product management for roadmap and adoption decisions.
- UX research for journey analysis and behavioral segmentation.
- Growth analytics for funnel, cohort and retention analysis.
- Engineering leads for product health and release impact.

## CourseFlow LMS Contribution

CourseFlow LMS contributes clickstream events, enrollment funnel steps, learning runtime activity,
admin workflows, assessment interactions, review flows and recommendation surface usage.

## Future Product Onboarding

- Mobile apps for app sessions, feature events and release cohorts.
- Admin portals for operational workflow analytics.
- Marketplace products for browse, search, cart and seller journeys.
- Support portals for self-service, deflection and escalation journeys.

## Domain-Specific Rules

- Event taxonomy must separate product area, feature, action, object and surface.
- Experiment metrics require exposure id, variant, assignment time and guardrail definitions.
- Behavioral events must use privacy-safe person and session identifiers.
- Product analytics datasets are not finance-grade unless reconciled by Finance domain rules.
