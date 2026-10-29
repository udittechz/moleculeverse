"""Core cheminformatics helpers for MoleculeVerse (all calculations use RDKit locally).

Nothing here depends on Streamlit, so every function can be unit-tested.
All values are *calculated descriptors*, not experimental measurements.
"""
from __future__ import annotations

import re
import string
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Optional

from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import (
    AllChem,
    Crippen,
    Descriptors,
    Draw,
    Lipinski,
    rdDepictor,
    rdFingerprintGenerator,
    rdMolDescriptors,
)
from rdkit.Chem.Draw import rdMolDraw2D

RDLogger.DisableLog("rdApp.*")  # keep RDKit warnings out of server logs / UI

MAX_SMILES_LENGTH = 500
MAX_HEAVY_ATOMS = 200
MAX_3D_HEAVY_ATOMS = 100
MAX_FILE_BYTES = 1_000_000
ALLOWED_FILE_EXTENSIONS = (".mol", ".sdf", ".smi", ".txt")

DISCLAIMER = (
    "All values in this report are calculated descriptors or computational predictions "
    "produced with RDKit from the molecular graph. They are not experimental measurements, "
    "and they do not by themselves establish stability, synthesizability, biological activity, "
    "toxicity, drug suitability or safety."
)

_ALLOWED_CHARS = set(string.ascii_letters + string.digits + "()[]=#$:/\\@+-%.*~")


# --------------------------------------------------------------------------- parsing
@dataclass
class ParseResult:
    """Outcome of parsing/validating a SMILES string."""

    ok: bool
    mol: Optional[Chem.Mol]
    smiles: str
    message: str
    warnings: list[str] = field(default_factory=list)
    detail: str = ""


def _explain_syntax_error(s: str) -> str:
    hints: list[str] = []
    if s.count("(") != s.count(")"):
        hints.append("The round brackets ( ) are not balanced; every branch that opens must close.")
    if s.count("[") != s.count("]"):
        hints.append("The square brackets [ ] are not balanced; every bracket atom must be closed.")
    outside = re.sub(r"\[[^\]]*\]", "", s)
    counts = Counter(re.findall(r"%\d\d|\d", outside))
    odd = sorted(k for k, v in counts.items() if v % 2)
    if odd:
        hints.append(
            "Ring-closure number(s) " + ", ".join(odd) + " appear an odd number of times; "
            "every ring that is opened with a digit must be closed with the same digit."
        )
    if not hints:
        hints.append(
            "RDKit could not read this text as SMILES. Check element symbols (for example Cl and Br "
            "start with a capital letter), bond symbols, and brackets."
        )
    return "This is not a valid SMILES string. " + " ".join(hints)


def _explain_sanitize_error(exc: Exception) -> tuple[str, str]:
    text = str(exc)
    low = text.lower()
    detail = text.strip().splitlines()[0][:200] if text.strip() else ""
    if "valence" in low:
        return (
            "The SMILES is readable, but an atom has more bonds than its normal valence allows "
            "(for example a carbon with five bonds). Check bond orders, charges, and hydrogen counts.",
            detail,
        )
    if "kekul" in low:
        return (
            "The SMILES is readable, but the aromatic (lowercase) atoms cannot form a consistent "
            "aromatic ring. Check ring atoms; for example pyrrole needs an explicit [nH].",
            detail,
        )
    return (
        "The SMILES is readable, but the atoms and bonds are not chemically consistent "
        "(RDKit sanitization failed).",
        detail,
    )


def parse_smiles(smiles: Optional[str]) -> ParseResult:
    """Parse and sanitize a SMILES string without ever raising to the caller."""
    if smiles is None or not str(smiles).strip():
        return ParseResult(False, None, "", "Please enter a SMILES string, for example CCO for ethanol.")
    s = str(smiles).strip()
    if len(s) > MAX_SMILES_LENGTH:
        return ParseResult(False, None, s[:50] + "...", f"The input is longer than {MAX_SMILES_LENGTH} characters.")
    if any(ch.isspace() for ch in s):
        return ParseResult(
            False, None, s,
            "SMILES strings cannot contain spaces or line breaks. Enter one molecule at a time.",
        )
    bad = sorted({c for c in s if c not in _ALLOWED_CHARS})
    if bad:
        shown = " ".join(repr(c) for c in bad[:6])
        return ParseResult(False, None, s, f"The input contains characters that are not used in SMILES: {shown}.")
    try:
        mol = Chem.MolFromSmiles(s, sanitize=False)
    except Exception:  # pragma: no cover - defensive
        mol = None
    if mol is None or mol.GetNumAtoms() == 0:
        return ParseResult(False, None, s, _explain_syntax_error(s))
    try:
        Chem.SanitizeMol(mol)
    except Exception as exc:
        msg, detail = _explain_sanitize_error(exc)
        return ParseResult(False, None, s, msg, detail=detail)
    if mol.GetNumHeavyAtoms() > MAX_HEAVY_ATOMS:
        return ParseResult(False, None, s, f"This molecule has more than {MAX_HEAVY_ATOMS} heavy atoms, which is above the limit of this teaching tool.")
    Chem.AssignStereochemistry(mol, cleanIt=True, force=True)
    warnings: list[str] = []
    if len(Chem.GetMolFrags(mol)) > 1:
        warnings.append("The structure contains more than one disconnected fragment (for example a salt or mixture).")
    return ParseResult(True, mol, s, "Valid structure: RDKit parsed and sanitized this SMILES.", warnings)


def canonical_smiles(mol: Chem.Mol) -> str:
    """Canonical SMILES without stereochemistry."""
    return Chem.MolToSmiles(mol, isomericSmiles=False)


def isomeric_smiles(mol: Chem.Mol) -> str:
    """Canonical SMILES including stereochemistry and isotopes."""
    return Chem.MolToSmiles(mol, isomericSmiles=True)


def molecular_formula(mol: Chem.Mol) -> str:
    """Molecular formula in Hill order, e.g. C2H6O (charge appended if non-zero)."""
    return rdMolDescriptors.CalcMolFormula(mol)


def isomeric_key(smiles: str) -> Optional[str]:
    """Canonical isomeric SMILES used as an identity key (None if invalid)."""
    res = parse_smiles(smiles)
    return isomeric_smiles(res.mol) if res.ok and res.mol is not None else None


# --------------------------------------------------------------------------- descriptors
def _chiral_centers(mol: Chem.Mol):
    return Chem.FindMolChiralCenters(mol, includeUnassigned=True, useLegacyImplementation=False)


# key, label, category, unit, explanation, function(mol, mol_with_Hs)
PROPERTY_SPECS: list[tuple[str, str, str, str, str, Any]] = [
    ("formula", "Molecular formula", "Basic information", "", "Counts of each element in the molecule (Hill order).", lambda m, h: molecular_formula(m)),
    ("canonical_smiles", "Canonical SMILES", "Basic information", "", "A unique, standardised SMILES for this structure without stereochemistry.", lambda m, h: canonical_smiles(m)),
    ("isomeric_smiles", "Isomeric SMILES", "Basic information", "", "Canonical SMILES that also records stereochemistry (wedges, E/Z) where defined.", lambda m, h: isomeric_smiles(m)),
    ("mol_weight", "Molecular weight", "Basic information", "g/mol", "Sum of average atomic masses (natural isotope abundance), including hydrogens.", lambda m, h: Descriptors.MolWt(m)),
    ("exact_mass", "Exact (monoisotopic) mass", "Basic information", "Da", "Mass using the most abundant isotope of each element; relevant to mass spectrometry.", lambda m, h: Descriptors.ExactMolWt(m)),
    ("atom_count", "Atom count (with H)", "Basic information", "", "Total atoms including hydrogens.", lambda m, h: h.GetNumAtoms()),
    ("heavy_atoms", "Heavy-atom count", "Basic information", "", "Number of non-hydrogen atoms.", lambda m, h: m.GetNumHeavyAtoms()),
    ("bond_count", "Bond count (with H)", "Basic information", "", "Total bonds including bonds to hydrogen.", lambda m, h: h.GetNumBonds()),
    ("logp", "Calculated logP (Crippen)", "Physicochemical descriptors", "", "Estimated lipophilicity: octanol/water partition tendency from an atom-contribution model.", lambda m, h: Crippen.MolLogP(m)),
    ("tpsa", "Topological polar surface area (TPSA)", "Physicochemical descriptors", "Å²", "Surface contributed by polar atoms (mainly N and O with attached H), a rough polarity measure.", lambda m, h: rdMolDescriptors.CalcTPSA(m)),
    ("hbd", "Hydrogen-bond donors", "Physicochemical descriptors", "", "Count of N-H / O-H type groups able to donate a hydrogen bond (RDKit Lipinski-style rule).", lambda m, h: Lipinski.NumHDonors(m)),
    ("hba", "Hydrogen-bond acceptors", "Physicochemical descriptors", "", "Count of N / O atoms able to accept a hydrogen bond (RDKit Lipinski-style rule).", lambda m, h: Lipinski.NumHAcceptors(m)),
    ("rotatable_bonds", "Rotatable bonds", "Physicochemical descriptors", "", "Single, non-ring bonds between non-terminal heavy atoms; a rough flexibility measure.", lambda m, h: rdMolDescriptors.CalcNumRotatableBonds(m)),
    ("ring_count", "Ring count", "Physicochemical descriptors", "", "Number of rings in the smallest set of smallest rings.", lambda m, h: rdMolDescriptors.CalcNumRings(m)),
    ("aromatic_rings", "Aromatic ring count", "Physicochemical descriptors", "", "Number of rings perceived as aromatic.", lambda m, h: rdMolDescriptors.CalcNumAromaticRings(m)),
    ("fsp3", "Fraction sp3 carbon (Fsp3)", "Physicochemical descriptors", "", "Share of carbons that are sp3 hybridised; 0 = fully flat/unsaturated, 1 = fully saturated.", lambda m, h: rdMolDescriptors.CalcFractionCSP3(m)),
    ("molar_refractivity", "Molar refractivity (Crippen)", "Physicochemical descriptors", "", "Calculated polarizability-related quantity from atom contributions.", lambda m, h: Crippen.MolMR(m)),
    ("formal_charge", "Formal charge", "Additional chemical information", "", "Sum of formal atomic charges.", lambda m, h: Chem.GetFormalCharge(m)),
    ("heteroatoms", "Heteroatom count", "Additional chemical information", "", "Atoms other than carbon and hydrogen.", lambda m, h: rdMolDescriptors.CalcNumHeteroatoms(m)),
    ("stereocenters", "Stereocenters (total)", "Additional chemical information", "", "Potential tetrahedral stereocenters, defined or not.", lambda m, h: len(_chiral_centers(m))),
    ("defined_stereocenters", "Stereocenters (defined)", "Additional chemical information", "", "Stereocenters whose configuration (R/S) is specified in the SMILES.", lambda m, h: sum(1 for _, lab in _chiral_centers(m) if lab in ("R", "S"))),
    ("stereo_double_bonds", "Double bonds with E/Z defined", "Additional chemical information", "", "Double bonds with specified cis/trans (E/Z) geometry.", lambda m, h: sum(1 for b in m.GetBonds() if b.GetStereo() != Chem.BondStereo.STEREONONE)),
    ("fragments", "Disconnected fragments", "Additional chemical information", "", "Number of separate components (more than 1 for salts or mixtures).", lambda m, h: len(Chem.GetMolFrags(m))),
]

CATEGORY_ORDER = ["Basic information", "Physicochemical descriptors", "Additional chemical information"]


def element_composition(mol: Chem.Mol) -> list[dict[str, Any]]:
    """Element counts and mass percentages (hydrogens included)."""
    mh = Chem.AddHs(mol)
    table = Chem.GetPeriodicTable()
    counts = Counter(a.GetSymbol() for a in mh.GetAtoms())
    masses = {sym: n * table.GetAtomicWeight(table.GetAtomicNumber(sym)) for sym, n in counts.items()}
    total = sum(masses.values()) or 1.0
    order = sorted(counts)
    if "C" in counts:
        order = ["C"] + (["H"] if "H" in counts else []) + [s for s in order if s not in ("C", "H")]
    return [
        {"element": s, "count": counts[s], "mass_percent": round(100.0 * masses[s] / total, 2)}
        for s in order
    ]


def morgan_fingerprint(mol: Chem.Mol, radius: int = 2, n_bits: int = 2048):
    """Morgan (circular, ECFP-like) bit-vector fingerprint."""
    return rdFingerprintGenerator.GetMorganGenerator(radius=radius, fpSize=n_bits).GetFingerprint(mol)


def fingerprint_summary(mol: Chem.Mol) -> dict[str, Any]:
    fp = morgan_fingerprint(mol)
    on = list(fp.GetOnBits())
    return {
        "type": "Morgan fingerprint (radius 2, 2048 bits)",
        "bits_set": len(on),
        "length": fp.GetNumBits(),
        "first_bits_set": on[:20],
    }


def tanimoto_similarity(mol_a: Chem.Mol, mol_b: Chem.Mol) -> float:
    """Tanimoto coefficient (0-1) of Morgan fingerprints. Not proof of similar behaviour."""
    try:
        return float(DataStructs.TanimotoSimilarity(morgan_fingerprint(mol_a), morgan_fingerprint(mol_b)))
    except Exception:  # pragma: no cover - defensive
        return 0.0


def _round(value: Any) -> Any:
    return round(value, 4) if isinstance(value, float) else value


def analyze_smiles(smiles: Optional[str], name: str = "") -> dict[str, Any]:
    """Validate a SMILES string and compute every descriptor. Returns a plain dict.

    The same parsed molecule object is reused for every calculation.
    """
    pr = parse_smiles(smiles)
    rec: dict[str, Any] = {
        "input_smiles": pr.smiles,
        "name": (name or "").strip()[:60],
        "valid": pr.ok,
        "message": pr.message,
        "warnings": pr.warnings,
        "detail": pr.detail,
    }
    if not pr.ok or pr.mol is None:
        return rec
    mol = pr.mol
    mh = Chem.AddHs(mol)
    props: list[dict[str, Any]] = []
    values: dict[str, Any] = {}
    errors: list[str] = []
    for key, label, category, unit, expl, fn in PROPERTY_SPECS:
        try:
            val = _round(fn(mol, mh))
        except Exception:
            val = None
            errors.append(label)
        values[key] = val
        props.append({"key": key, "label": label, "category": category, "unit": unit, "value": val, "explanation": expl})
    try:
        from rdkit.Chem import inchi

        rec["inchikey"] = inchi.MolToInchiKey(mol) or None
    except Exception:
        rec["inchikey"] = None
    rec.update(
        canonical_smiles=values.get("canonical_smiles"),
        isomeric_smiles=values.get("isomeric_smiles"),
        formula=values.get("formula"),
        properties=props,
        values=values,
        composition=element_composition(mol),
        fingerprint=fingerprint_summary(mol),
        descriptor_errors=errors,
    )
    return rec


# --------------------------------------------------------------------------- 2D depiction
def draw_2d_png(mol: Chem.Mol, size: tuple[int, int] = (520, 400), legend: str = "") -> Optional[bytes]:
    """Render a 2D structure diagram as PNG bytes (None if rendering fails)."""
    try:
        m = Chem.Mol(mol)
        try:
            rdDepictor.SetPreferCoordGen(True)
        except Exception:
            pass
        rdDepictor.Compute2DCoords(m)
        drawer = rdMolDraw2D.MolDraw2DCairo(size[0], size[1])
        opts = drawer.drawOptions()
        opts.addStereoAnnotation = True
        opts.bondLineWidth = 2
        opts.padding = 0.12
        rdMolDraw2D.PrepareAndDrawMolecule(drawer, m, legend=legend)
        drawer.FinishDrawing()
        return drawer.GetDrawingText()
    except Exception:
        try:
            import io

            img = Draw.MolToImage(mol, size=size)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            return None


def smiles_to_png(smiles: str, size: tuple[int, int] = (520, 400), legend: str = "") -> Optional[bytes]:
    pr = parse_smiles(smiles)
    return draw_2d_png(pr.mol, size, legend) if pr.ok and pr.mol is not None else None


# --------------------------------------------------------------------------- 3D conformers
@dataclass
class Conformer3D:
    ok: bool
    molblock: Optional[str]
    message: str
    method: str = ""
    converged: Optional[bool] = None


def generate_3d(mol: Chem.Mol, seed: int = 42) -> Conformer3D:
    """Embed a 3D conformer (ETKDGv3) and optimise it (MMFF94, else UFF)."""
    try:
        if mol.GetNumHeavyAtoms() > MAX_3D_HEAVY_ATOMS:
            return Conformer3D(False, None, f"3D generation is limited to {MAX_3D_HEAVY_ATOMS} heavy atoms in this tool.")
        mh = Chem.AddHs(mol)
        params = AllChem.ETKDGv3()
        params.randomSeed = seed
        if hasattr(params, "maxIterations"):
            params.maxIterations = 500
        cid = AllChem.EmbedMolecule(mh, params)
        if cid < 0:
            params.useRandomCoords = True
            cid = AllChem.EmbedMolecule(mh, params)
        if cid < 0:
            return Conformer3D(False, None, "RDKit could not generate a 3D conformer for this molecule.")
        method, converged = "ETKDGv3 embedding only (no force-field optimisation available)", None
        try:
            if AllChem.MMFFHasAllMoleculeParams(mh):
                converged = AllChem.MMFFOptimizeMolecule(mh, maxIters=2000) == 0
                method = "ETKDGv3 embedding, MMFF94 optimisation"
            elif AllChem.UFFHasAllMoleculeParams(mh):
                converged = AllChem.UFFOptimizeMolecule(mh, maxIters=2000) == 0
                method = "ETKDGv3 embedding, UFF optimisation"
        except Exception:
            method = "ETKDGv3 embedding (optimisation failed)"
        msg = "Computational conformer generated. It is one model geometry, not an experimentally determined structure."
        if converged is False:
            msg += " The force-field optimisation did not fully converge."
        return Conformer3D(True, Chem.MolToMolBlock(mh), msg, method, converged)
    except Exception:
        return Conformer3D(False, None, "3D conformer generation failed for this molecule.")


def smiles_to_3d(smiles: str) -> Conformer3D:
    pr = parse_smiles(smiles)
    if not pr.ok or pr.mol is None:
        return Conformer3D(False, None, pr.message)
    return generate_3d(pr.mol)


# --------------------------------------------------------------------------- file formats
def mol_to_molblock(mol: Chem.Mol) -> str:
    """MOL block with 2D coordinates (computed if missing)."""
    m = Chem.Mol(mol)
    rdDepictor.Compute2DCoords(m)
    return Chem.MolToMolBlock(m)


def molblock_to_sdf(molblock: str, name: str = "", props: Optional[dict[str, Any]] = None) -> str:
    """Wrap a MOL block as a one-record SDF with optional data fields."""
    lines = molblock.rstrip("\n").split("\n")
    if name:
        lines[0] = re.sub(r"[\r\n]", " ", name)[:80]
    body = "\n".join(lines) + "\n"
    for k, v in (props or {}).items():
        body += f"> <{re.sub(r'[^A-Za-z0-9_]', '_', str(k))}>\n{v}\n\n"
    return body + "$$$$\n"


def safe_filename(name: str, ext: str, default: str = "molecule") -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "_", (name or "").strip()).strip("_")[:40] or default
    return f"{base}.{ext.lstrip('.')}"


def parse_structure_bytes(data: bytes, filename: str) -> ParseResult:
    """Validate and read an uploaded .mol/.sdf/.smi/.txt file (untrusted input)."""
    fname = (filename or "").lower()
    if not fname.endswith(ALLOWED_FILE_EXTENSIONS):
        return ParseResult(False, None, "", "Unsupported file type. Use .mol, .sdf, .smi or .txt.")
    if len(data) > MAX_FILE_BYTES:
        return ParseResult(False, None, "", "The file is larger than 1 MB.")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return ParseResult(False, None, "", "The file is not plain UTF-8 text.")
    if fname.endswith((".mol", ".sdf")):
        block = text.split("$$$$")[0]
        try:
            mol = Chem.MolFromMolBlock(block, sanitize=True, removeHs=True)
        except Exception:
            mol = None
        if mol is None:
            return ParseResult(False, None, "", "RDKit could not read a molecule from this file.")
        return parse_smiles(Chem.MolToSmiles(mol))
    for line in text.splitlines():
        if line.strip():
            return parse_smiles(line.split()[0])
    return ParseResult(False, None, "", "The file is empty.")
