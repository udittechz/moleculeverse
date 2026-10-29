"""Molecule library logic (pure Python; the Streamlit session holds the list).

Storage: the library lives in ``st.session_state`` only. It is NOT saved to disk, so
user-added molecules disappear when the browser session ends. Use the export buttons to keep them.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from . import chemistry

# Verified-by-test examples: tests/test_chemistry.py parses each SMILES and checks its formula.
BUILTIN_MOLECULES: list[dict[str, str]] = [
    {"name": "Water", "smiles": "O", "category": "Inorganic / small molecule", "formula": "H2O"},
    {"name": "Methane", "smiles": "C", "category": "Alkane", "formula": "CH4"},
    {"name": "Ammonia", "smiles": "N", "category": "Inorganic / small molecule", "formula": "H3N"},
    {"name": "Carbon dioxide", "smiles": "O=C=O", "category": "Inorganic / small molecule", "formula": "CO2"},
    {"name": "Ethanol", "smiles": "CCO", "category": "Alcohol", "formula": "C2H6O"},
    {"name": "Dimethyl ether", "smiles": "COC", "category": "Ether", "formula": "C2H6O"},
    {"name": "Acetone", "smiles": "CC(C)=O", "category": "Ketone", "formula": "C3H6O"},
    {"name": "Acetic acid", "smiles": "CC(=O)O", "category": "Carboxylic acid", "formula": "C2H4O2"},
    {"name": "Acetate ion", "smiles": "CC(=O)[O-]", "category": "Ion", "formula": "C2H3O2-"},
    {"name": "Ethene", "smiles": "C=C", "category": "Alkene", "formula": "C2H4"},
    {"name": "Benzene", "smiles": "c1ccccc1", "category": "Aromatic", "formula": "C6H6"},
    {"name": "Toluene", "smiles": "Cc1ccccc1", "category": "Aromatic", "formula": "C7H8"},
    {"name": "Phenol", "smiles": "Oc1ccccc1", "category": "Aromatic", "formula": "C6H6O"},
    {"name": "L-Alanine", "smiles": "N[C@@H](C)C(=O)O", "category": "Amino acid", "formula": "C3H7NO2"},
    {"name": "Glucose (beta-D-glucopyranose)", "smiles": "C([C@@H]1[C@H]([C@@H]([C@H]([C@@H](O1)O)O)O)O)O", "category": "Carbohydrate", "formula": "C6H12O6"},
    {"name": "Aspirin", "smiles": "CC(=O)Oc1ccccc1C(=O)O", "category": "Pharmaceutical (educational example)", "formula": "C9H8O4"},
    {"name": "Paracetamol", "smiles": "CC(=O)Nc1ccc(O)cc1", "category": "Pharmaceutical (educational example)", "formula": "C8H9NO2"},
    {"name": "Ibuprofen", "smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O", "category": "Pharmaceutical (educational example)", "formula": "C13H18O2"},
    {"name": "Caffeine", "smiles": "Cn1c(=O)c2c(ncn2C)n(C)c1=O", "category": "Alkaloid", "formula": "C8H10N4O2"},
]

USER_CATEGORY = "User-added"


def default_library() -> list[dict[str, Any]]:
    """Built-in entries with a canonical identity key computed by RDKit."""
    out = []
    for i, m in enumerate(BUILTIN_MOLECULES):
        key = chemistry.isomeric_key(m["smiles"])
        if key is None:
            continue
        out.append({"id": f"builtin-{i}", "name": m["name"], "smiles": m["smiles"],
                    "category": m["category"], "builtin": True, "key": key})
    return out


def find(library: list[dict[str, Any]], mol_id: str) -> Optional[dict[str, Any]]:
    return next((e for e in library if e["id"] == mol_id), None)


def _unique_name(library: list[dict[str, Any]], name: str) -> str:
    names = {e["name"].lower() for e in library}
    if name.lower() not in names:
        return name
    n = 2
    while f"{name} ({n})".lower() in names:
        n += 1
    return f"{name} ({n})"


def add_user_molecule(library: list[dict[str, Any]], name: str, smiles: str) -> tuple[bool, str, Optional[dict[str, Any]]]:
    """Add a valid molecule. Duplicates (same canonical isomeric SMILES) are rejected."""
    pr = chemistry.parse_smiles(smiles)
    if not pr.ok or pr.mol is None:
        return False, pr.message, None
    key = chemistry.isomeric_smiles(pr.mol)
    for e in library:
        if e.get("key") == key:
            return False, f"This structure is already in the library as '{e['name']}'.", None
    clean = (name or "").strip()[:60] or f"Molecule {chemistry.molecular_formula(pr.mol)}"
    entry = {"id": f"user-{uuid.uuid4().hex[:8]}", "name": _unique_name(library, clean), "smiles": pr.smiles,
             "category": USER_CATEGORY, "builtin": False, "key": key}
    library.append(entry)
    return True, f"Saved '{entry['name']}' to the library for this session.", entry


def rename_molecule(library: list[dict[str, Any]], mol_id: str, new_name: str) -> tuple[bool, str]:
    """Rename a user-added molecule; the structure (SMILES) is never changed."""
    e = find(library, mol_id)
    if e is None:
        return False, "Molecule not found."
    if e["builtin"]:
        return False, "Built-in example molecules cannot be renamed."
    clean = (new_name or "").strip()[:60]
    if not clean:
        return False, "The name cannot be empty."
    others = [x for x in library if x["id"] != mol_id]
    e["name"] = _unique_name(others, clean)
    return True, f"Renamed to '{e['name']}'."


def remove_molecule(library: list[dict[str, Any]], mol_id: str) -> tuple[bool, str]:
    e = find(library, mol_id)
    if e is None:
        return False, "Molecule not found."
    if e["builtin"]:
        return False, "Built-in example molecules cannot be removed."
    library.remove(e)
    return True, f"Removed '{e['name']}'."


def clear_user_molecules(library: list[dict[str, Any]]) -> int:
    before = len(library)
    library[:] = [e for e in library if e["builtin"]]
    return before - len(library)


def user_molecules(library: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in library if not e["builtin"]]
