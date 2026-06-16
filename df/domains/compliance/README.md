# Compliance Data Domain

This domain owns audit evidence, privacy, consent, retention, residency, access governance and
regulatory compliance datasets. It is separate from Risk and Compliance Controls, which owns fraud,
abuse and operational risk signals.

## Business Capability

Compliance provides defensible evidence that data is collected, accessed, retained, deleted,
transferred and shared according to policy, law, contract and enterprise control requirements.

## First Data Products

| Data product | Purpose | First source or contribution |
|---|---|---|
| `silver.audit_access_events` | Conformed access, entitlement and administrative audit events. | CourseFlow access-control, entitlement and admin activity. |
| `gold.compliance_retention_status` | Dataset, record-class and product retention compliance status. | CourseFlow learner PII, course, organization and activity retention classes. |
| `gold.privacy_subject_request_status` | Data subject request inventory, SLA and fulfillment status. | CourseFlow learner and organization-scoped privacy requests when available. |

## First Consumers

- Compliance office for policy evidence and regulatory reporting.
- Privacy office for data subject rights and consent governance.
- Security for access review, audit and incident investigation.
- Internal audit for control testing and evidence sampling.

## CourseFlow LMS Contribution

CourseFlow LMS contributes access-control events, entitlement changes, learner PII classification,
tenant and organization scope, administrative audit trails and retention requirements for learning
records.

## Future Product Onboarding

- Identity and access management for authentication, authorization and access review events.
- Legal case management for holds, regulatory matters and privacy requests.
- Customer data platforms for consent, preference and marketing permission data.
- Document management for records, policy attestations and retention evidence.

## Domain-Specific Rules

- Compliance datasets must retain policy version, control owner, evidence timestamp and source
  lineage.
- PII, sensitive and regulated attributes must have classification, masking and retention metadata.
- Access evidence must preserve actor, subject, action, resource, decision and correlation id.
- Deletion or anonymization evidence must be immutable and queryable by product and subject scope.
