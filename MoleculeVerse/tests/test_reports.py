import csv
import importlib.util
import io
import json
from datetime import datetime, timezone

from PIL import Image

from modules import reports

RECORD = {
    "input_smiles": "CCO", "name": "Ethanol", "valid": True, "message": "Valid", "warnings": [],
    "canonical_smiles": "CCO", "isomeric_smiles": "CCO", "formula": "C2H6O", "inchikey": None,
    "properties": [
        {"key": "mol_weight", "label": "Molecular weight", "category": "Basic information", "unit": "g/mol", "value": 46.069, "explanation": "Average mass."},
        {"key": "logp", "label": "Calculated logP", "category": "Physicochemical descriptors", "unit": "", "value": -0.0014, "explanation": "Lipophilicity."},
        {"key": "x", "label": "Unavailable thing", "category": "Additional chemical information", "unit": "", "value": None, "explanation": "n/a"},
    ],
    "values": {"mol_weight": 46.069, "logp": -0.0014},
    "composition": [{"element": "C", "count": 2, "mass_percent": 52.14}],
    "fingerprint": {"type": "Morgan", "bits_set": 3, "length": 2048, "first_bits_set": [1, 2, 3]},
}


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (200, 120), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_pdf_is_real_pdf_with_and_without_images():
    when = datetime(2026, 1, 2, tzinfo=timezone.utc)
    plain = reports.build_pdf_report(RECORD, None, None, None, when)
    full = reports.build_pdf_report(RECORD, _png(), None, {"name": "A <b>& B", "registration": "R1"}, when)
    assert plain.startswith(b"%PDF") and full.startswith(b"%PDF")
    assert len(full) > len(plain) > 1000


def test_pdf_handles_invalid_record():
    bad = {"input_smiles": "C(C", "valid": False, "message": "Unbalanced brackets"}
    assert reports.build_pdf_report(bad).startswith(b"%PDF")


def test_csv_export():
    rows = list(csv.reader(io.StringIO(reports.properties_to_csv(RECORD))))
    assert rows[0] == ["Category", "Property", "Value", "Unit", "Description"]
    flat = {r[1]: r[2] for r in rows[1:]}
    assert flat["Molecular weight"] == "46.069" and flat["Unavailable thing"] == ""
    assert flat["Submitted SMILES"] == "CCO"


def test_json_export_has_no_student_data_and_has_disclaimer():
    data = json.loads(reports.record_to_json(RECORD, datetime(2026, 1, 2, tzinfo=timezone.utc)))
    assert data["molecule"]["formula"] == "C2H6O" and data["properties"]["mol_weight"] == 46.069
    assert "not experimental" in data["note"]
    assert "registration" not in json.dumps(data).lower()


def test_exports_from_real_analysis_when_rdkit_available():
    if importlib.util.find_spec("rdkit") is None:
        import pytest

        pytest.skip("RDKit not installed")
    from modules import chemistry

    rec = chemistry.analyze_smiles("CC(=O)Oc1ccccc1C(=O)O", "Aspirin")
    png = chemistry.smiles_to_png("CC(=O)Oc1ccccc1C(=O)O")
    assert reports.build_pdf_report(rec, png).startswith(b"%PDF")
    assert json.loads(reports.record_to_json(rec))["molecule"]["formula"] == "C9H8O4"
    assert "Aspirin" in reports.properties_to_csv(rec)
