# CourseFlow RAG Answer Service

Canonical location: `ai/services/rag-answer-service`.

This service is the policy-enforced grounded-answer boundary for the AI Platform. It composes
retrieval, citation enforcement and prompt gateway safety gates so LMS and non-LMS products can ask
questions over approved knowledge collections without bypassing tenant, product or human-review
controls.

## Responsibilities

- Expose RAG answer routes:
  - `POST /v1/rag-answer/answer`
  - `GET /v1/rag-answer/health`
  - `GET /v1/rag-answer/metrics`
- Retrieve evidence through the registered retrieval runtime.
- Refuse answers when no trusted citation meets the configured grounding threshold.
- Enforce principal, scope, tenant, product, use-case and collection allowlists from
  `platform/governance/policies/rag-answer-access-policy.yaml`.
- Require human review and block external auto-send for baseline RAG answers.

## Local Development

```bash
cd ai/services/rag-answer-service
make test
make health
```

Run an LMS tutor answer through the service boundary:

```bash
PYTHONPATH=../../platform/src:src python -m courseflow_rag_answer_service.cli \
  --ai-root ../.. \
  --principal-id service:lms-courseflow-rag-answer \
  answer \
  --body-json '{"tenantId":"tenant-a","product":"lms-courseflow","useCaseId":"lms-rag-tutor","collectionId":"course_content_chunks","question":"Explain Python for loops, while loops, break and continue.","topK":3}'
```

Run the lightweight HTTP wrapper:

```bash
PYTHONPATH=../../platform/src:src python -m courseflow_rag_answer_service.cli \
  --ai-root ../.. \
  serve \
  --host 127.0.0.1 \
  --port 8101
```

The HTTP wrapper expects `X-CourseFlow-Principal-Id`; optional `X-CourseFlow-Scopes` can narrow the
requested scopes.
