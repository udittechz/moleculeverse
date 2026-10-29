"""Molecule comparison: side-by-side descriptors, highlighted differences, Tanimoto similarity."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import pandas as pd

from . import chemistry

# key, column label, unit, difference threshold considered "meaningful" (teaching heuristic)
KEY_DESCRIPTORS = [
    ("mol_weight", "Molecular weight (g/mol)", "g/mol", 10.0),
    ("logp", "logP", "", 0.5),
    ("tpsa", "TPSA (Å²)", "Å²", 10.0),
    ("hbd", "H-bond donors", "", 1),
    ("hba", "H-bond acceptors", "", 1),
    ("rotatable_bonds", "Rotatable bonds", "", 1),
    ("ring_count", "Rings", "", 1),
]
TABLE_COLUMNS = KEY_DESCRIPTORS + [
    ("exact_mass", "Exact mass (Da)", "Da", 0),
    ("aromatic_rings", "Aromatic rings", "", 1),
    ("fsp3", "Fsp3", "", 0.1),
    ("formal_charge", "Formal charge", "", 1),
    ("heavy_atoms", "Heavy atoms", "", 1),
]

CAUTION = (
    "Differences in calculated descriptors do not automatically mean differences in biological "
    "efficacy, toxicity or safety. Fingerprint similarity is a structural-pattern measure and "
    "does not prove that two molecules behave the same way."
)


@dataclass
class ComparisonResult:
    valid: list[dict[str, Any]] = field(default_factory=list)
    invalid: list[dict[str, str]] = field(default_factory=list)
    table: pd.DataFrame = field(default_factory=pd.DataFrame)
    similarity: Optional[pd.DataFrame] = None
    highlights: list[dict[str, Any]] = field(default_factory=list)


def _unique_labels(entries: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: dict[str, int] = {}
    out = []
    for label, smi in entries:
        base = (label or "").strip() or (smi or "").strip()[:20] or "Molecule"
        seen[base] = seen.get(base, 0) + 1
        out.append((base if seen[base] == 1 else f"{base} ({seen[base]})", smi))
    return out


def run_comparison(
    entries: list[tuple[str, str]],
    analyzer: Callable[..., dict[str, Any]] = chemistry.analyze_smiles,
) -> ComparisonResult:
    """Validate each entry independently, so invalid ones never block the rest."""
    res = ComparisonResult()
    for label, smi in _unique_labels(entries):
        rec = analyzer(smi, label)
        if rec.get("valid"):
            rec = dict(rec, label=label)
            res.valid.append(rec)
        else:
            res.invalid.append({"label": label, "smiles": smi or "", "message": rec.get("message", "Invalid structure.")})
    rows = []
    for rec in res.valid:
        row: dict[str, Any] = {"Molecule": rec["label"], "Formula": rec["formula"]}
        for key, col, _unit, _thr in TABLE_COLUMNS:
            row[col] = rec["values"].get(key)
        rows.append(row)
    res.table = pd.DataFrame(rows)
    if len(res.valid) >= 2:
        res.similarity = similarity_matrix(res.valid)
        res.highlights = highlight_differences(res.valid)
    return res


def similarity_matrix(valid: list[dict[str, Any]]) -> pd.DataFrame:
    """Pairwise Tanimoto similarity (Morgan radius 2, 2048 bits)."""
    mols = [chemistry.parse_smiles(r["input_smiles"]).mol for r in valid]
    labels = [r["label"] for r in valid]
    data = [[1.0 if i == j else round(chemistry.tanimoto_similarity(a, b), 3) for j, b in enumerate(mols)] for i, a in enumerate(mols)]
    return pd.DataFrame(data, index=labels, columns=labels)


def highlight_differences(valid: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """For each key descriptor report the highest/lowest molecule and whether the spread is meaningful."""
    out = []
    for key, col, unit, thr in KEY_DESCRIPTORS:
        pairs = [(r["label"], r["values"].get(key)) for r in valid if r["values"].get(key) is not None]
        if len(pairs) < 2:
            continue
        hi = max(pairs, key=lambda p: p[1])
        lo = min(pairs, key=lambda p: p[1])
        spread = round(hi[1] - lo[1], 3)
        out.append({
            "key": key, "label": col, "unit": unit, "highest": hi, "lowest": lo,
            "spread": spread, "meaningful": spread >= thr and spread > 0, "threshold": thr,
        })
    return out
