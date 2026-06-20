# CourseFlow NLP Understanding Service

Canonical location: `ai/services/nlp-understanding-service`.

This service is the shared NLP/transformer-upgrade boundary for the AI Platform. It provides a
baseline runtime for intent classification, semantic tags, retrieval-query shaping and rubric
feedback while preserving the future transformer adapter path behind the same policy controls.

## Responsibilities

- Expose NLP understanding routes:
  - `POST /v1/nlp-understanding/analyze`
  - `GET /v1/nlp-understanding/health`
  - `GET /v1/nlp-understanding/metrics`
- Serve LMS semantic search, LMS auto-grading, support agent assist, support speech QA and
  enterprise knowledge assistant through one boundary.
- Enforce principal, scope, tenant, product and use-case allowlists from
  `platform/governance/policies/nlp-understanding-access-policy.yaml`.
- Reject direct learner, customer, contact, account, user, email and phone identifiers.
- Require human review for rubric feedback, support assist and speech QA outputs.

## Local Development

```bash
cd ai/services/nlp-understanding-service
make test
make health
```

Run a support case analysis through the service boundary:

```bash
PYTHONPATH=../../platform/src:src python -m courseflow_nlp_understanding_service.cli \
  --ai-root ../.. \
  --principal-id service:support-platform-nlp \
  analyze \
  --body-json '{"tenantId":"tenant-a","product":"support-platform","useCaseId":"support-agent-assist","subject":"Urgent login outage","latestMessage":"All admins are blocked by MFA timeout errors.","productArea":"identity","priority":"urgent","taskType":"case_triage"}'
```

The HTTP wrapper expects `X-CourseFlow-Principal-Id`; optional `X-CourseFlow-Scopes` can narrow the
requested scopes.
