# Capability-indexed materialization bounds for multiset programs

This standalone repository supports the internal article **Capability-Indexed
Materialization Bounds for Multiset Programs**.  It contains exact inputs,
source/interpreters, proof-producing compilers, independent certificate
checkers, handwritten proofs, a small purpose-built proof kernel, negative
controls, and retained results.  It does not require the paper directory.

## Scientific contents

- `proofs/capability.md` defines capability signatures, simulation monotonicity,
  strict same-denotation separations, and the no-denotation-only-bound result.
- `proofs/replay.md` proves typing, multiplicity preservation, termination, and
  a sufficient zero-derived-store replay budget for the declared pure bag
  fragment.
- `proofs/residual.md` proves the exact finite one-way bit-barrier theorem and
  describes the residual-class compiler.
- `proofs/integer-rank.md` proves the positive substitution lemma and exact
  count-word barrier theorem, with a factorization compiler.
- `proofs/cache.md` proves the occurrence-record product results.
- `formal/` kernel-checks the residual semantic core and 64 polynomial factor
  identities.  Its README states the exact non-claims.

The mathematical measures are model-specific.  Residual classes and
nonnegative integer rank are established concepts; the article's contribution
is the capability-indexed semantics, strict separations, and their integration
with typed bag compilation—not a claim to have invented those measures.

## Reproduction

Use POSIX/Linux with Python 3.10 or newer and the standard library.  Do not use
Python's `-O` flag.  From the repository root:

```sh
python audit.py --package-clean
python run.py check
python run.py reproduce --out /tmp/resource-semantics-reproduction
python -m unittest discover -s tests -v
python formal/check.py
python src/generate_inputs.py --out /tmp/resource-semantics-inputs
python src/pilot.py
```

The two output directories must be absent or empty.  The independent `audit.py`
command cross-checks input IDs, certificate names, result rows, summary counts,
negative controls, claim-evidence paths, reference-audit records, external
resource records, and package cleanliness.  Compare generated input files with
`inputs/`; the main `check` command validates retained packets and reconciles
row counts, while `reproduce` reruns the entire bounded campaign.  The pilot is
a retained early diagnostic and is intentionally separate.

Expected main logical counts are:

- 985 declared program/certificate instances;
- 896 replay semantic cases;
- nine occurrence-cache certificates;
- 64 exact integer-rank packets;
- all 16 Boolean two-by-two residual functions and 44 capacity variants;
- 33 negative controls;
- 30,083 counted validation/transition obligations;
- 41 focused unit/mutation/integrity tests;
- 81 audited scholarly references, each cited and carrying a persistent
  identifier; and
- one first-order theorem plus 64 semiring identities checked by the
  purpose-built kernels.

CPU time, wall time, RSS, PDF bytes, and temporary paths are measurements rather
than deterministic outputs.  Logical inputs, CSVs, JSON certificates, reference-audit records, and
checker judgments are deterministic.

## Evidence interpretation

The source-language oracle intentionally materializes bags; the replay
interpreter is separate.  The exact rank and cache synthesizers are separate
from their checkers.  Rank packets include both a factor witness and a Bellman
potential over every bounded residual state.  Residual packets include the
reconstructed equivalence classes and shortest fixed-width codes.  Negative
controls mutate dimensions, partitions, costs, witnesses, potentials, types,
and semantic operators.

Finite checks do not prove the general theorems.  Conversely, successful
commands do not verify CPython, the operating system, or physical performance.
The paper and proof documents state which results are handwritten, kernel
checked, finite checked, or measured.

## Machine boundaries

The bit-barrier theorem forbids uncharged input-dependent addresses or trace
lengths, permits output only after the barrier, and charges bit stores and
loads.  The positive-word theorem permits only static positive natural
arithmetic and forbids subtraction, division, bit extraction, branches on
packed values, and readable output.  The occurrence model charges identity
records and does not allow multiplicity compression.  Changing any of these
features changes the capability signature and may change the optimum.

## Provenance and external use

An AI assistant contributed research formulation, proof drafts, code, generated
input definitions, execution, analysis, manuscript drafting, and self-audit.
The evidence is not independently blind-reviewed.  Human authors must inspect
and take responsibility for all content and recheck current venue policies
before any external use.  No email, account action, external model API,
private data, GPU, institutional compute, or human-subject evidence was used.


## Independent blind-review robustness check

```sh
PYTHONDONTWRITEBYTECODE=1 python3 reviewer/blind_holdout.py --root . --out results/reviewer/blind_holdout.json
```

This post-development suite is independent of the implementation and is not described as a statistical held-out set. See `reviewer/BLIND-HOLDOUT.md`.


## Fresh structured-instance campaign

```sh
PYTHONDONTWRITEBYTECODE=1 python3 reviewer/fresh_campaign.py --out-dir results/reviewer/fresh-campaign
```

The campaign provides exact model-relative robustness evidence, not a production throughput benchmark.


## Fail-closed final internal gate

```sh
PYTHONDONTWRITEBYTECODE=1 python3 reviewer/run_final_gate.py --out results/reviewer/final-gate.json
```
