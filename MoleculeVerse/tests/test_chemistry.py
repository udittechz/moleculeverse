import pytest

pytest.importorskip("rdkit")

from modules import chemistry as c  # noqa: E402
from modules import library  # noqa: E402


def test_valid_invalid_and_empty_input():
    assert c.parse_smiles("CCO").ok
    for bad in ("", "   ", None):
        r = c.parse_smiles(bad)
        assert not r.ok and "enter" in r.message.lower()
    for bad in ("C(C", "c1ccc", "CC(C)(C)(C)(C)C", "Xyz", "C C", "C1CC1C1"):
        r = c.parse_smiles(bad)
        assert not r.ok and r.mol is None and r.message
        assert "Traceback" not in r.message


def test_friendly_messages():
    assert "round brackets" in c.parse_smiles("C(C").message
    assert "valence" in c.parse_smiles("CC(C)(C)(C)C").message.lower()
    assert "aromatic" in c.parse_smiles("c1cccc1").message.lower()


def test_input_limit():
    assert not c.parse_smiles("C" * (c.MAX_SMILES_LENGTH + 1)).ok


def test_formula_weight_and_exact_mass():
    rec = c.analyze_smiles("CCO")
    assert rec["formula"] == "C2H6O"
    assert abs(rec["values"]["mol_weight"] - 46.069) < 0.01
    assert abs(rec["values"]["exact_mass"] - 46.0419) < 0.001
    assert c.analyze_smiles("O")["formula"] == "H2O"
    assert abs(c.analyze_smiles("O")["values"]["mol_weight"] - 18.015) < 0.01


def test_aromatic_molecule():
    v = c.analyze_smiles("c1ccccc1")["values"]
    assert v["aromatic_rings"] == 1 and v["ring_count"] == 1 and v["fsp3"] == 0.0
    assert v["formula"] == "C6H6" and v["heavy_atoms"] == 6 and v["atom_count"] == 12


def test_charged_molecule():
    rec = c.analyze_smiles("CC(=O)[O-]")
    assert rec["valid"] and rec["values"]["formal_charge"] == -1
    assert c.analyze_smiles("C[NH3+]")["values"]["formal_charge"] == 1


def test_stereochemistry():
    l_ala = c.analyze_smiles("N[C@@H](C)C(=O)O")["values"]
    d_ala = c.analyze_smiles("N[C@H](C)C(=O)O")["values"]
    assert l_ala["stereocenters"] == 1 and l_ala["defined_stereocenters"] == 1
    assert c.analyze_smiles("CC(N)C(=O)O")["values"]["defined_stereocenters"] == 0
    assert l_ala["isomeric_smiles"] != d_ala["isomeric_smiles"]
    assert c.analyze_smiles("C/C=C/C")["values"]["stereo_double_bonds"] == 1


def test_descriptors_are_complete_and_plausible():
    rec = c.analyze_smiles("CC(=O)Oc1ccccc1C(=O)O", "Aspirin")
    v = rec["values"]
    assert v["formula"] == "C9H8O4" and abs(v["mol_weight"] - 180.159) < 0.01
    assert abs(v["tpsa"] - 63.6) < 0.5 and v["hbd"] == 1 and v["hba"] >= 3
    assert not rec["descriptor_errors"]
    assert all(p["explanation"] for p in rec["properties"])
    for key in ("canonical_smiles", "isomeric_smiles", "logp", "rotatable_bonds", "heteroatoms", "formal_charge"):
        assert key in v
    assert abs(sum(x["mass_percent"] for x in rec["composition"]) - 100) < 0.1
    assert rec["fingerprint"]["bits_set"] > 0


def test_2d_png_generation():
    png = c.smiles_to_png("CC(=O)Oc1ccccc1C(=O)O")
    assert png and png[:8] == b"\x89PNG\r\n\x1a\n"
    assert c.smiles_to_png("not-a-smiles") is None


def test_3d_conformer_generation():
    conf = c.smiles_to_3d("CCO")
    assert conf.ok and "M  END" in conf.molblock and conf.method
    assert len(conf.molblock.splitlines()) > 12
    assert not c.smiles_to_3d("C(C").ok


def test_file_conversion_and_filenames():
    mol = c.parse_smiles("CCO").mol
    block = c.mol_to_molblock(mol)
    sdf = c.molblock_to_sdf(block, "My ethanol", {"SMILES": "CCO"})
    assert sdf.rstrip().endswith("$$$$") and "> <SMILES>" in sdf
    assert c.safe_filename("Ethanol / test!", "pdf") == "Ethanol_test.pdf"
    assert c.safe_filename("", "csv") == "molecule.csv"


def test_upload_validation():
    mol = c.parse_smiles("CCO").mol
    block = c.mol_to_molblock(mol)
    assert c.parse_structure_bytes(block.encode(), "x.mol").ok
    assert c.parse_structure_bytes(b"CCO ethanol\n", "x.smi").ok
    assert not c.parse_structure_bytes(b"data", "x.exe").ok
    assert not c.parse_structure_bytes(b"x" * (c.MAX_FILE_BYTES + 1), "x.smi").ok
    assert not c.parse_structure_bytes(b"\xff\xfe\x00", "x.smi").ok
    assert not c.parse_structure_bytes(b"garbage", "x.mol").ok


def test_fingerprint_similarity():
    a, b = c.parse_smiles("CCO").mol, c.parse_smiles("CCCO").mol
    assert c.tanimoto_similarity(a, a) == 1.0
    assert 0.0 < c.tanimoto_similarity(a, b) < 1.0
    assert c.tanimoto_similarity(a, c.parse_smiles("c1ccccc1").mol) < c.tanimoto_similarity(a, b)


def test_builtin_library_examples_are_valid_and_match_formulas():
    lib = library.default_library()
    assert len(lib) == len(library.BUILTIN_MOLECULES)
    for entry, spec in zip(lib, library.BUILTIN_MOLECULES):
        assert c.analyze_smiles(entry["smiles"])["formula"] == spec["formula"], spec["name"]
    names = {e["name"] for e in lib}
    for needed in ("Water", "Methane", "Ethanol", "Benzene", "Aspirin", "Caffeine", "Acetic acid"):
        assert needed in names
    assert any(e["name"].startswith("Glucose") for e in lib)
