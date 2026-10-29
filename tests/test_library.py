import pytest

pytest.importorskip("rdkit")

from modules import library  # noqa: E402


def test_add_duplicate_rename_remove():
    lib = library.default_library()
    n = len(lib)
    ok, msg, entry = library.add_user_molecule(lib, "My propanol", "CCCO")
    assert ok and entry and not entry["builtin"] and len(lib) == n + 1
    ok, msg, _ = library.add_user_molecule(lib, "again", "OCCC")  # same structure, different SMILES text
    assert not ok and "already" in msg.lower() and len(lib) == n + 1
    ok, msg, _ = library.add_user_molecule(lib, "dup of built-in", "OCC")
    assert not ok and "Ethanol" in msg
    ok, _ = library.rename_molecule(lib, entry["id"], "Propan-1-ol")
    assert ok and library.find(lib, entry["id"])["name"] == "Propan-1-ol"
    assert library.find(lib, entry["id"])["smiles"] == "CCCO"  # structure unchanged
    assert not library.rename_molecule(lib, entry["id"], "   ")[0]
    builtin = lib[0]
    assert not library.rename_molecule(lib, builtin["id"], "x")[0]
    assert not library.remove_molecule(lib, builtin["id"])[0]
    assert library.remove_molecule(lib, entry["id"])[0] and len(lib) == n


def test_invalid_input_and_default_name_and_clear():
    lib = library.default_library()
    ok, msg, entry = library.add_user_molecule(lib, "bad", "C(C")
    assert not ok and entry is None and msg
    ok, _, e = library.add_user_molecule(lib, "", "CCCC")
    assert ok and "C4H10" in e["name"]
    ok, _, e2 = library.add_user_molecule(lib, e["name"], "CCCCC")
    assert ok and e2["name"] != e["name"]
    assert library.clear_user_molecules(lib) == 2
    assert all(x["builtin"] for x in lib)
