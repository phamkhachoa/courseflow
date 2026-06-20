# AI Platform Product Council 0033

Date: 2026-06-17

## Topic

Operations demand forecast runtime baseline.

## Participants

- SA AI Platform: Platform architecture, registry and evidence owner
- SA AI Engineer: Runtime baseline and evaluation owner
- PO/BA: Enterprise operations use-case owner

## Decision

Promote `operations-demand-forecasting` from proposed roadmap coverage to a
runtime-library baseline backed by feature contract, model IO contract, golden
evaluation, model card and source artifact manifest.

This converts the `forecasting-planning` capability into an executable gate for
enterprise operations while keeping it reusable for LMS cohort demand planning.

## Evidence

| Artifact | Path |
|---|---|
| Runtime source | `models/forecasting/demand_forecast_baseline/demand_forecast_baseline.py` |
| Feature contract | `contracts/features/operations-demand-features.v1.yaml` |
| Model IO contract | `contracts/models/operations-demand-forecast-model-io.v1.yaml` |
| Golden dataset | `platform/evaluation/datasets/operations-demand-forecast-golden.yaml` |
| Evaluation report | `platform/evaluation/reports/operations-demand-forecast-v1-eval.yaml` |
| Model card | `platform/model-registry/model-cards/operations-demand-forecast-baseline-v1.md` |
| Artifact manifest | `platform/artifacts/manifests/operations-demand-forecast-baseline-v1.yaml` |

## Baseline Behavior

The baseline uses recent weighted demand, bounded trend adjustment, backlog
pressure and calendar/incident multipliers to produce forecast units, demand
band, capacity gap, reason codes and staffing scenario actions.

## Gate

| Metric | Threshold | Status |
|---|---:|---|
| Demand band accuracy | 1.00 | passed |
| Staffing recommendation accuracy | 1.00 | passed |
| Reason code recall | 0.85 | passed |
| Forecast threshold pass rate | 1.00 | passed |
| Human review policy pass rate | 1.00 | passed |
| Forecast ordering pass rate | 1.00 | passed |

## Governance

- High demand, large capacity shortfall or open incident requires human review.
- Automated capacity changes are not allowed from the baseline.
- Future trained forecasting models must backtest against this gate before
  service activation.

## Next Steps

1. Bind the baseline to a governed operations workload snapshot.
2. Add time-split backtesting with prediction interval metrics.
3. Compare against a trained forecasting model.
4. Host the runtime library behind the shared model-serving facade.
