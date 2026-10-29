import pytest

pytest.importorskip("rdkit")

from modules import comparison  # noqa: E402


def test_compare_valid_molecules_and_highlights():
    res = comparison.run_comparison([("Ethanol", "CCO"), ("Benzene", "c1ccccc1"), ("Aspirin", "CC(=O)Oc1ccccc1C(=O)O")])
    assert len(res.valid) == 3 and not res.invalid
    assert list(res.table["Molecule"]) == ["Ethanol", "Benzene", "Aspirin"]
    assert res.table.loc[res.table["Molecule"] == "Aspirin", "Formula"].iloc[0] == "C9H8O4"
    mw = next(h for h in res.highlights if h["key"] == "mol_weight")
    assert mw["highest"][0] == "Aspirin" and mw["lowest"][0] == "Ethanol" and mw["meaningful"]
    assert res.similarity.shape == (3, 3)
    assert all(res.similarity.iloc[i, i] == 1.0 for i in range(3))


def test_invalid_entries_do_not_block_comparison():
    res = comparison.run_comparison([("Good", "CCO"), ("Bad", "C(C"), ("Empty", ""), ("Other", "CCCO")])
    assert [r["label"] for r in res.valid] == ["Good", "Other"]
    assert {i["label"] for i in res.invalid} == {"Bad", "Empty"}
    assert all(i["message"] for i in res.invalid)
    assert res.similarity is not None


def test_single_valid_molecule_has_no_similarity():
    res = comparison.run_comparison([("A", "CCO"), ("B", "nonsense!")])
    assert len(res.valid) == 1 and res.similarity is None and res.highlights == []


def test_duplicate_labels_are_made_unique():
    res = comparison.run_comparison([("X", "CCO"), ("X", "CCC")])
    assert [r["label"] for r in res.valid] == ["X", "X (2)"]
