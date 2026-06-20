# 0021 Platform Operating Cockpit

Date: 2026-06-17

## Decision

Add an AI Platform operating cockpit that combines solution blueprint intake,
data contract coverage, promotion request intake, promotion readiness, coverage,
evidence, evaluation health and serving runtime health into one Admin/Ops
projection.

## Why

The platform now has several real control-plane reports. Product and operations
owners need one place to answer:

- Is the platform release-ready?
- Which business requests are ready for solution design?
- Which candidate artifacts need approval, artifact, evaluation, privacy or
  simulator work?
- Which active, approved or shadow artifacts need monitoring or activation?
- Is the platform broader than LMS?

## Artifacts

| Artifact | Path |
| --- | --- |
| Cockpit projection | `platform/src/courseflow_ai_platform/operating_cockpit.py` |
| Cockpit report | `platform/operations/reports/operating-cockpit-v1.yaml` |
| Tests | `platform/tests/test_operating_cockpit.py`, `platform/tests/test_cli.py` |
| CLI output | `operatingCockpit` top-level key and optional report writer |

## Current Health

| Dimension | Status |
| --- | --- |
| Platform status | `attention_required` |
| Delivery status | `ready_work_available` |
| Release status | `release_ready` |
| Evaluations | 20 required, 20 passed |
| Coverage | 14 modules, no missing required AI areas |
| Data contracts | 7 contracts, 16 mapped domains, 0 missing domains |
| Solution blueprint intake | 6 requests, 5 ready, 1 waiting, 5 non-LMS |
| Promotion intake | 5 requests, 2 ready, 3 waiting |
| Promotion readiness | 4 promotions, 4 ready, 0 blocked |
| Serving health | `healthy`, runtime metrics export connected |

## Operating Meaning

`release_ready` means existing promoted artifacts and gates are clean.
`attention_required` means the enterprise delivery queue still needs PO/BA,
SA AI Platform, SA AI Engineer, Governance or Data Platform work before the
next wave can move.

## Role Actions

| Role | Cockpit action |
| --- | --- |
| PO/BA | Confirm business acceptance metrics and product ownership |
| SA AI Platform | Publish solution architecture and plan runtime platform gaps |
| SA AI Engineer | Build evaluation, artifact, simulator and shadow evidence |
| Governance Reviewer | Complete privacy and promotion approvals |
| Admin/Ops | Activate approved artifacts and monitor active/shadow releases |

## Next Moves

1. Add a rendered Admin/Ops dashboard view backed by the cockpit snapshot.
2. Add backlog state transitions and SLA ownership.
3. Add freshness/parity checks so draft contracts can move toward production-ready.
