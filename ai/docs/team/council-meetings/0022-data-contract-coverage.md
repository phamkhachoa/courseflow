# 0022 Data Contract Coverage

Date: 2026-06-17

## Decision

Promote feature/data contracts from a proposed pattern into a validated AI
Platform control-plane capability. Every solution blueprint data domain must map
to a registered contract, and the platform must distinguish design-ready,
production-ready, privacy-gated and simulator-gated contracts.

## Why

The operating cockpit showed data contracts as a delivery blocker. Without a
data contract coverage report, PO/BA, SA AI Platform and SA AI Engineer cannot
tell whether a use case is missing data, blocked by privacy, blocked by
simulator requirements or merely using a draft contract that needs hardening.

## Artifacts

| Artifact | Path |
| --- | --- |
| Data contract registry | `platform/data-contracts/registry.yaml` |
| Data contract coverage report | `platform/data-contracts/reports/data-contract-coverage-v1.yaml` |
| Coverage validator | `platform/src/courseflow_ai_platform/data_contracts.py` |
| Tests | `platform/tests/test_data_contracts.py`, `platform/tests/test_cli.py` |
| CLI output | `dataContractCoverage` top-level key and optional report writer |

## Current Coverage

| Scope | Value |
| --- | --- |
| Contracts | 7 total |
| Active contracts | 2 |
| Draft contracts | 4 |
| Privacy-gated contracts | 1 |
| Simulator-gated contracts | 0 |
| Solution blueprint requests | 6 |
| Design-ready requests | 5 |
| Production-ready requests | 2 |
| Missing data domains | 0 of 16 |
| Non-LMS requests covered | 5 |

## Newly Registered Contracts

| Contract | Product | Status |
| --- | --- | --- |
| `enterprise-knowledge-documents-v1` | AI Platform | draft |
| `finance-payment-risk-features-v1` | Billing/Finance | draft |
| `finance-document-intelligence-features-v1` | Billing/Finance | privacy-gated |
| `operations-routing-features-v1` | Enterprise Operations | draft |
| `operations-demand-features-v1` | Enterprise Operations | draft |

Existing LMS and Support contracts remain active and now participate in the same
coverage report.

## Product Impact

| Role | Outcome |
| --- | --- |
| PO/BA | Can see whether a requested AI use case has data-domain coverage |
| SA AI Platform | Can separate platform build gaps from data contract gaps |
| SA AI Engineer | Can start design from draft contracts without pretending they are production-ready |
| Governance Reviewer | Can see privacy-gated document/media contracts clearly |
| Data Platform | Can harden draft contracts into production-ready contracts |

## Next Moves

1. Add contract freshness/parity checks against real DP manifests.
2. Add contract-to-training-run binding for model artifact evidence.
3. Surface data contract coverage in the rendered Admin/Ops dashboard.
