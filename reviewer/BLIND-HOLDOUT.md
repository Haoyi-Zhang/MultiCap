# Independent blind-review robustness suite

`reviewer/blind_holdout.py` is deliberately independent of the project implementation. It uses only the Python standard library and a fixed, newly introduced seed. It re-derives three finite obligations: random finite residual encodings, exhaustive 2x2 nonnegative-integer factor schedules over entries 0--3, and exact two-slot occurrence-cache optima for all 1--4 by 1--4 products. It also scans retained JSON factor certificates and verifies their equations independently.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 reviewer/blind_holdout.py --root . --out results/reviewer/blind_holdout.json
```

This is post-development robustness evidence, not a pre-registered or statistical held-out test set. It targets hand-picked-instance and correlated-implementation risk; it does not replace the general mathematical proofs or establish production-system performance.
