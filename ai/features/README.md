# AI Features

`features/` chuẩn hóa offline/online features cho AI models. Source of truth cho dữ liệu phân tích vẫn là `dp/`; folder này mô tả cách AI platform tiêu thụ feature để train và serve.

## Structure

```text
features/
  contracts/       Local mirrors or derived views of contracts/features/
  offline/         Batch snapshots for training and evaluation
  online/          Low-latency features for serving
```

## Feature Store Direction

Phase 1 có thể đọc batch snapshots hoặc synthetic fixtures. Phase enterprise cần:

- Offline store cho training/evaluation reproducibility.
- Online store cho low-latency serving.
- Materialization jobs từ `dp` gold datasets.
- Training-serving parity checks.
- Feature freshness and drift monitoring.

Use `contracts/features/lms-learning-features.v1.yaml` as the current canonical feature contract.

