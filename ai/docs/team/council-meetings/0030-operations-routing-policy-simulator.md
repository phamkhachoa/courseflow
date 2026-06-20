# 0030 Operations Routing Policy Simulator

Date: 2026-06-17

## Decision

Promote `rl-bandit-decisioning` from simulator-required roadmap coverage to an
executable runtime-library baseline through
`operations-routing-policy-simulator-v1`.

## Why

The AI Platform must cover decision optimization and RL/bandit use cases without
allowing unsafe online exploration. The operations-routing baseline gives PO/BA,
SA AI Platform and SA AI Engineer a deterministic simulator, constrained policy
contract and offline evaluation gate before any shadow or live routing policy is
considered.

## Evidence

| Artifact | Path |
| --- | --- |
| Runtime library | `models/bandit_rl/routing_policy_simulator/routing_policy_simulator.py` |
| Model IO contract | `contracts/models/operations-routing-policy-model-io.v1.yaml` |
| Golden dataset | `platform/evaluation/datasets/operations-routing-policy-golden.yaml` |
| Evaluation report | `platform/evaluation/reports/operations-routing-policy-v1-eval.yaml` |
| Model card | `platform/model-registry/model-cards/operations-routing-policy-simulator-v1.md` |
| Artifact manifest | `platform/artifacts/manifests/operations-routing-policy-simulator-v1.yaml` |

## Current Baseline

| Scope | Value |
| --- | --- |
| Model ID | `operations-routing-policy-simulator-v1` |
| Product | `enterprise-operations` |
| Use case | `operations-routing-optimization` |
| Runtime status | `runtime_library` |
| Coverage status | `executable_gate` |
| Required eval status | passed |
| Promotion request | `operations-routing-rl-simulator-request` ready for approval |

## Guardrail

This is a deterministic constrained routing simulator and offline policy
baseline. It is not an online RL learner and it does not perform live
exploration. Any live or shadow policy must first prove logged-policy data,
counterfactual evaluation, capacity constraints, fairness checks and human
override paths.

## Product Impact

| Role | Outcome |
| --- | --- |
| PO/BA | Can move operations routing into solution design with measurable constraints |
| SA AI Platform | Can keep decision optimization gated by offline evidence before live serving |
| SA AI Engineer | Has a tested baseline to beat with future contextual bandit or RL learners |
| Governance Reviewer | Can review simulator promotion separately from online exploration risk |
| Admin/Ops | Can track the simulator promotion request in the same release cockpit |

## Next Moves

1. Publish solution architecture for `operations-routing-optimization-simulator`.
2. Harden `operations-routing-features-v1` from draft to production-ready.
3. Host or service-integrate the simulator only after product serving SLA and
   override workflow are accepted.
4. Add online-policy learning later only after governed logged-policy data and
   counterfactual evaluation are available.
