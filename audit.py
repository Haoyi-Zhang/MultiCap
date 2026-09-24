#!/usr/bin/env python3
"""Cross-file integrity audit for the standalone evidence repository.

This command is intentionally independent of the experiment runner.  It checks
that retained inputs, certificates, tabular results, summary counts, evidence
ledgers, and reference-audit records describe the same packet.  It does not
prove the mathematical theorems; the proof documents and certificate checkers
have separate responsibilities.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


class AuditError(ValueError):
    pass


def load_json(relative: str) -> Any:
    path = ROOT / relative
    if not path.is_file():
        raise AuditError(f"missing JSON file: {relative}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AuditError(f"invalid JSON in {relative}: {exc}") from exc


def load_csv(relative: str) -> list[dict[str, str]]:
    path = ROOT / relative
    if not path.is_file():
        raise AuditError(f"missing CSV file: {relative}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise AuditError(f"CSV has no header: {relative}")
        rows = list(reader)
    if not rows:
        raise AuditError(f"CSV has no data rows: {relative}")
    return rows


def unique(rows: list[dict[str, str]], field: str, label: str) -> set[str]:
    values = [row.get(field, "").strip() for row in rows]
    if any(not value for value in values):
        raise AuditError(f"{label}: blank {field}")
    if len(values) != len(set(values)):
        raise AuditError(f"{label}: duplicate {field}")
    return set(values)


def input_ids(relative: str, expected: int) -> tuple[list[dict[str, Any]], set[str]]:
    rows = load_json(relative)
    if not isinstance(rows, list) or len(rows) != expected:
        raise AuditError(f"{relative}: expected {expected} cases")
    ids = [row.get("id") for row in rows]
    if any(not isinstance(value, str) or not value for value in ids):
        raise AuditError(f"{relative}: invalid case id")
    if len(ids) != len(set(ids)):
        raise AuditError(f"{relative}: duplicate case id")
    return rows, set(ids)


def certificate_names(prefix: str, expected_ids: set[str]) -> set[str]:
    paths = sorted((ROOT / "results/certificates").glob(f"{prefix}-*.json"))
    names = {path.stem for path in paths}
    if names != expected_ids:
        missing = sorted(expected_ids - names)
        extra = sorted(names - expected_ids)
        raise AuditError(f"{prefix} certificates mismatch: missing={missing}, extra={extra}")
    for path in paths:
        try:
            packet = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AuditError(f"invalid certificate JSON: {path.name}") from exc
        if prefix in {"rank", "residual"} and packet.get("id") != path.stem:
            raise AuditError(f"certificate id mismatch: {path.name}")
    return names


def verify_evidence_paths(claims: list[dict[str, str]]) -> int:
    pattern = re.compile(r"(?:proofs|src|formal|tests|results|inputs)/[A-Za-z0-9_.\-/]+")
    checked: set[str] = set()
    for row in claims:
        for field in ("proof_or_checker", "source_or_test", "raw_result"):
            for match in pattern.findall(row.get(field, "")):
                relative = match.rstrip(".,;:")
                if not (ROOT / relative).exists():
                    raise AuditError(f"claim {row['claim_id']}: missing evidence path {relative}")
                checked.add(relative)
    return len(checked)


def audit(package_clean: bool = False) -> dict[str, Any]:
    required = [
        "README.md", "readme.txt", "LICENSE", "run.py", "audit.py",
        "claim_evidence_ledger.csv", "external_resources.csv",
        "reference-audit.csv", "literature-notes.md",
        "proofs/capability.md", "proofs/replay.md", "proofs/residual.md",
        "proofs/integer-rank.md", "proofs/cache.md", "formal/check.py",
        "results/summary.json",
    ]
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        raise AuditError(f"required files missing: {missing}")

    semantic, semantic_ids = input_ids("inputs/semantic_cases.json", 896)
    cache, cache_ids = input_ids("inputs/cache_cases.json", 9)
    rank, rank_ids = input_ids("inputs/rank_cases.json", 64)
    residual, residual_ids = input_ids("inputs/residual_cases.json", 16)

    certificate_names("cache", cache_ids)
    certificate_names("rank", rank_ids)
    certificate_names("residual", residual_ids)

    summary = load_json("results/summary.json")
    expected_summary = {
        "semantic_cases": len(semantic),
        "cache_instances": len(cache),
        "integer_rank_instances": len(rank),
        "residual_function_instances": len(residual),
        "declared_program_or_certificate_instances": len(semantic) + len(cache) + len(rank) + len(residual),
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            raise AuditError(f"summary {key}: expected {expected}, found {summary.get(key)!r}")

    result_rows = {
        "semantic": load_csv("results/semantic.csv"),
        "cache": load_csv("results/cache.csv"),
        "rank": load_csv("results/integer_rank.csv"),
        "residual": load_csv("results/residual.csv"),
    }
    expected_result_ids = {
        "semantic": semantic_ids,
        "cache": cache_ids,
        "rank": rank_ids,
        "residual": residual_ids,
    }
    for label, rows in result_rows.items():
        ids = unique(rows, "id", f"results/{label}")
        if ids != expected_result_ids[label]:
            raise AuditError(f"results/{label}: row ids do not match retained inputs")

    if any(row.get("equivalent") != "True" for row in result_rows["semantic"]):
        raise AuditError("semantic.csv contains a non-equivalent row")
    modeled_reads = sum(int(row["base_reads"]) for row in result_rows["semantic"])
    if modeled_reads != summary.get("total_modeled_base_reads"):
        raise AuditError("semantic modeled-read total does not reconcile with summary")

    negatives = load_json("results/negative_controls.json")
    cache_negatives = negatives.get("cache", [])
    positive_negatives = negatives.get("positive_source", [])
    if len(cache_negatives) != summary.get("cache_negative_controls"):
        raise AuditError("cache negative-control count mismatch")
    if len(positive_negatives) != summary.get("positive_source_negative_controls"):
        raise AuditError("positive-source negative-control count mismatch")
    if summary.get("negative_control_failures") != 0:
        raise AuditError("summary reports a negative-control failure")

    references = load_csv("reference-audit.csv")
    reference_keys = unique(references, "key", "reference audit")
    persistent = unique(references, "persistent_id", "reference audit")
    if len(references) < 60:
        raise AuditError("reference audit must contain at least 60 sources")
    for row in references:
        if not row["persistent_id"].startswith(("doi:", "arXiv:", "https://doi.org/", "https://arxiv.org/", "https://")):
            raise AuditError(f"reference {row['key']}: unsupported persistent identifier")
        if not row.get("verification_basis", "").strip() or not row.get("technical_role", "").strip():
            raise AuditError(f"reference {row['key']}: incomplete audit metadata")
        if not row.get("cited_in", "").strip():
            raise AuditError(f"reference {row['key']}: no manuscript citation location")

    claims = load_csv("claim_evidence_ledger.csv")
    claim_ids = unique(claims, "claim_id", "claim evidence ledger")
    for row in claims:
        for field in ("claim", "maturity", "boundary", "fresh_recheck"):
            if not row.get(field, "").strip():
                raise AuditError(f"claim {row['claim_id']}: blank {field}")
    evidence_paths = verify_evidence_paths(claims)

    resources = load_csv("external_resources.csv")
    resource_ids = unique(resources, "id", "external resources")
    for row in resources:
        url = row.get("scholarly_or_official_url", "")
        if not url.startswith("https://"):
            raise AuditError(f"external resource {row['id']}: non-HTTPS scholarly URL")
        if row.get("internals_modified") not in {"yes", "no"}:
            raise AuditError(f"external resource {row['id']}: invalid internals_modified value")

    archives = sorted(str(path.relative_to(ROOT)) for path in ROOT.rglob("*")
                      if path.is_file() and path.suffix.lower() in {".zip", ".tar", ".gz", ".7z"})
    if archives:
        raise AuditError(f"nested archives are not allowed: {archives}")
    cache_dirs = sorted(str(path.relative_to(ROOT)) for path in ROOT.rglob("__pycache__") if path.is_dir())
    bytecode = sorted(str(path.relative_to(ROOT)) for path in ROOT.rglob("*.pyc"))
    if package_clean and (cache_dirs or bytecode):
        raise AuditError(f"generated Python cache files present: dirs={cache_dirs}, files={bytecode[:5]}")

    report = {
        "status": "pass",
        "declared_instances": expected_summary["declared_program_or_certificate_instances"],
        "input_cases": {"semantic": 896, "cache": 9, "integer_rank": 64, "residual": 16},
        "certificate_files": 9 + 64 + 16,
        "result_rows": {key: len(value) for key, value in result_rows.items()},
        "negative_controls": len(cache_negatives) + len(positive_negatives),
        "reference_records": len(reference_keys),
        "persistent_reference_ids": len(persistent),
        "claim_records": len(claim_ids),
        "evidence_paths_checked": evidence_paths,
        "external_resource_records": len(resource_ids),
        "package_clean_mode": package_clean,
        "python_cache_directories": len(cache_dirs),
        "python_bytecode_files": len(bytecode),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-clean", action="store_true",
                        help="also reject generated __pycache__ directories and .pyc files")
    args = parser.parse_args()
    try:
        report = audit(package_clean=args.package_clean)
    except (AuditError, KeyError, TypeError, ValueError) as exc:
        print(f"AUDIT FAILED: {exc}")
        raise SystemExit(1)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
