# Causal Uplift Baseline

Deterministic runtime-library baseline for intervention and experiment review.
It estimates treatment-vs-control lift, flags statistical confidence, enforces
guardrail regression stops and requires human review for high-impact decisions.

This is not a replacement for a full experimentation platform or causal model.
It is the first reusable contract for LMS learning interventions, enterprise
personalization and operations policy experiments.

## Run Tests

```bash
PYTHONPATH=. python -m pytest -q
```
