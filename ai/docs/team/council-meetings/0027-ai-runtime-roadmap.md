# 0027 AI Runtime Roadmap

Date: 2026-06-17

## Decision

Add a validated runtime roadmap report on top of AI Business Capability
Coverage. The report converts `runtime_status` into prioritized work so the
platform can move from registry coverage toward real runtime artifacts.

## Why

The platform covers the full AI spectrum requested by stakeholders. The current
coverage modules are now service-integrated, so the roadmap report is kept as a
control-plane check that proves whether new registry/tooling/shadow modules
create runtime gaps.

## Artifacts

| Artifact | Path |
| --- | --- |
| Runtime roadmap projection | `platform/src/courseflow_ai_platform/runtime_roadmap.py` |
| Runtime roadmap report | `platform/coverage/reports/runtime-roadmap-v1.yaml` |
| Tests | `platform/tests/test_runtime_roadmap.py`, `platform/tests/test_cli.py` |
| CLI output | `runtimeRoadmap` top-level key and optional report writer |

## Current Runtime Roadmap

| Scope | Value |
| --- | ---: |
| AI coverage modules | 14 |
| Runtime-ready modules | 14 |
| Runtime gaps | 0 |
| P1 runtime candidates | 0 |
| P2 runtime candidates | 0 |
| Runtime-library modules | 0 |
| Registry-only modules | 0 |
| Production-ready modules | 0 |

## First Runtime Candidates

| Candidate | Why first | Owner |
| --- | --- | --- |
| None | Current roadmap has no P1/P2 runtime candidate after governance evaluation was service-integrated | SA AI Platform |

## Product Impact

| Role | Outcome |
| --- | --- |
| PO/BA | Can explain which AI families are covered versus runtime-ready |
| SA AI Platform | Can sequence runtime platform investments beyond LMS |
| SA AI Engineer | Can pick the next artifact, evaluation and serving slice |
| Governance Reviewer | Can keep privacy/simulator modules from premature activation |
| Admin/Ops | Can track runtime maturity as a control-plane report |

## Next Moves

1. Keep document/audio raw-media controls in the media privacy review loop before raw OCR/layout, ASR or diarization adapters are enabled.
2. Surface governance evaluation service metrics in Admin/Ops dashboard and release health projections.
3. Add online-policy learning only after logged-policy data, counterfactual evaluation and safety constraints are accepted.
