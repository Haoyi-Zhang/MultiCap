# Final internal gate

Run the fail-closed release gate from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 reviewer/run_final_gate.py --out results/reviewer/final-gate.json
```

The gate runs the independent reviewer scripts, cross-language and mutation checks, end-to-end checks, unit tests, proof kernels, the post-development blind holdout, the fresh structured campaign, a clean reproduction, and package hygiene. A pass is an internal consistency/reproducibility result, not peer review or an acceptance guarantee.
