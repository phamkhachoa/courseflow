# Sequence Risk Service

Policy-enforced service package for recurrent sequence risk scoring. It wraps
`sequence-risk-baseline-v1` as an AI Platform service boundary so LMS risk and
knowledge-tracing workflows do not call model libraries directly.

## Routes

| Route | Scope | Purpose |
|---|---|---|
| `POST /v1/sequence-risk/score` | `internal:ai-platform:sequence-risk:score` | Score a bounded pseudonymous event sequence. |
| `GET /v1/sequence-risk/health` | `internal:ai-platform:sequence-risk:ops` | Report model and route readiness. |
| `GET /v1/sequence-risk/metrics` | `internal:ai-platform:sequence-risk:ops` | Report tenant-safe score, error, identifier rejection and HITL counters. |

## Boundary

The service accepts pseudonymous subject hashes and bounded event sequences. It
rejects direct learner, student, user or email identifiers. Medium and high risk
results set `requiresHumanReview=true` because interventions cannot be automated
as adverse learner actions.

## Local Commands

```bash
make test
make lint
make manifest
make health
```
