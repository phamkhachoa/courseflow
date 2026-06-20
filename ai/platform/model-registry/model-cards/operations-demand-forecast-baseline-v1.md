# Model Card: Operations Demand Forecast Baseline V1

## Identity

| Field | Value |
|---|---|
| Model ID | `operations-demand-forecast-baseline-v1` |
| Algorithm | deterministic weighted moving average capacity planner |
| Use case | `operations-demand-forecasting` |
| Product | `enterprise-operations` |
| Owner | `ai-platform` |
| Status | runtime library baseline |

## Intended Use

Forecast short-horizon operations workload, estimate capacity gap and provide
explainable staffing/scenario recommendations for planning review.

## Not Intended For

- Fully automated workforce changes.
- Production demand forecasting without governed workload snapshots.
- Causal intervention lift estimation.
- Long-range financial planning.

## Inputs

| Input | Description |
|---|---|
| tenant ID | Tenant boundary |
| forecast ID | Forecast request identifier |
| queue ID | Operations queue or workload lane |
| historical demand | Recent workload observations |
| planned capacity | Planned work units for the forecast horizon |
| backlog and handle time | Backlog pressure and work complexity signals |
| seasonal/event/incident signals | Calendar, surge and incident context |
| service-level target | Policy target used to flag planning risk |

## Outputs

| Output | Description |
|---|---|
| forecast units | Predicted workload units for the horizon |
| demand band | Low, normal, elevated or high |
| capacity gap | Forecast minus planned capacity |
| utilization ratio | Forecast divided by planned capacity |
| staffing recommendation | Maintain, add, reallocate or trigger plan |
| reason codes | Explainable planning reasons |
| scenario actions | What-if or operational follow-up actions |
| human-review flag | Required for high demand, shortfall or incident |

## Runtime Method

The baseline uses recent weighted demand, bounded trend adjustment, backlog
pressure and seasonal/event/incident multipliers. It converts forecast-to-
capacity ratio into a demand band and maps shortfall/surplus signals to
staffing actions.

This is a deterministic runtime library. It proves the model IO, data contract,
evaluation and governance path for forecasting and planning; it is not a
production-grade trained time-series model.

## Governance

- Tenant ID is required.
- High demand, large capacity shortfall or open incident requires human review.
- Automated staffing or SLA-impacting actions are not allowed from this
  baseline.
- Future trained models must backtest against this deterministic gate.

## Known Limitations

- No probabilistic prediction intervals.
- No calendar feature learning.
- No causal intervention estimator.
- No live staffing feedback loop.

## Monitoring

Track forecast error by queue, capacity gap override rate, service-level miss
rate, staffing recommendation acceptance, incident surge misses, model age and
data freshness before promotion to service runtime.
