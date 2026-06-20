# CourseFlow Retrieval Service

Canonical location: `ai/services/retrieval-service`.

This is the independent runtime shell for AI Platform retrieval and RAG search. It exposes the
registered course-content and support-knowledge vector artifacts through a policy-enforced service
boundary. LMS is one consumer; Support Platform is another, proving retrieval is a platform product
capability rather than an LMS-only feature.

## Responsibilities

- Expose retrieval routes:
  - `GET /v1/retrieval/collections`
  - `POST /v1/retrieval/search`
  - `GET /v1/retrieval/health`
  - `GET /v1/retrieval/metrics`
- Support `lexical`, `vector` and `hybrid` retrieval modes.
- Enforce principal, scope, tenant and collection allowlists from
  `platform/governance/policies/retrieval-access-policy.yaml`.
- Keep tenant-private chunks from crossing tenant boundaries.
- Reuse AI Platform vector-index artifacts and collection schemas.

## Local Development

```bash
cd ai/services/retrieval-service
make test
make health
```

Run a support search through the service boundary:

```bash
PYTHONPATH=../../platform/src:src python -m courseflow_retrieval_service.cli \
  --ai-root ../.. \
  --principal-id service:support-platform-retrieval \
  search \
  --body-json '{"collectionId":"support_knowledge_articles","tenantId":"tenant-a","query":"MFA timeout admin login","mode":"hybrid","topK":3}'
```

Run the lightweight HTTP wrapper:

```bash
PYTHONPATH=../../platform/src:src python -m courseflow_retrieval_service.cli \
  --ai-root ../.. \
  serve \
  --host 127.0.0.1 \
  --port 8092
```

The HTTP wrapper expects `X-CourseFlow-Principal-Id`; optional
`X-CourseFlow-Scopes` can narrow the requested scopes.
