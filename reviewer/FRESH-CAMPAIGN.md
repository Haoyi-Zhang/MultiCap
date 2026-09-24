# Fresh structured-instance campaign

This post-development campaign constructs low-factor-width matrices with a matching exact rational-rank lower bound, validates bilinear schedules on fresh inputs, applies row/column/component permutation metamorphisms, includes zero/identity/repeated-column boundaries, and compares exact cut traffic with a column-decomposition baseline. It is a model-relative semantic/traffic experiment, not a production throughput benchmark and not a statistical train/test study.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 reviewer/fresh_campaign.py --out-dir results/reviewer/fresh-campaign
```
