# Operations Demand Forecast Baseline

Deterministic time-series and planning baseline for
`operations-demand-forecasting`. It forecasts near-term workload, estimates
capacity gap, emits reason codes and recommends staffing/scenario actions.

This is a runtime library baseline, not a production forecasting service. It is
intended to prove the model IO, feature contract, evaluation and governance path
before replacing the deterministic logic with a trained forecasting model or a
causal scenario simulator.

## Runtime

- Model ID: `operations-demand-forecast-baseline-v1`
- Entry point: `demand_forecast_baseline:DemandForecastBaseline`
- Input contract: `contracts/features/operations-demand-features.v1.yaml`
- Model IO contract: `contracts/models/operations-demand-forecast-model-io.v1.yaml`
- Evaluation gate: `platform/evaluation/datasets/operations-demand-forecast-golden.yaml`

## Governance

- Tenant ID is required.
- High capacity shortfall, high demand band or active incident requires human
  review before staffing or SLA-impacting action.
- This baseline emits transparent reason codes for planning review.
