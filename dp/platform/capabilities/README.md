# Enterprise Capability Maturity

`platform/capabilities/` is the architecture-as-code view of the enterprise data platform. It
translates the reference architecture into measurable capabilities, target maturity, evidence
artifacts, production gates and known gaps.

Maturity levels:

| Level | Meaning |
|---|---|
| `L0` | Documented only. |
| `L1` | Validated as code with local checks and metadata. |
| `L2` | Integrated runtime exists in staging or an equivalent production-like environment. |
| `L3` | Production-enforced release gates and runtime controls. |
| `L4` | Optimized with SLO/error budgets, cost controls and continuous improvement. |

Use the report CLI to inspect readiness:

```bash
PYTHONPATH=src python -m enterprise_dp.cli capability-maturity-report \
  --root . \
  --phase P0 \
  --output build/capabilities/p0-maturity.json
```

The report is expected to be `not_ready` until the live data plane and enforcement runtime catch up
with the control-plane manifests.
