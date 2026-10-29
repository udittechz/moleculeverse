# MoleculeVerse — Chemoinformatics Virtual Laboratory

An educational Streamlit web app for SRM Institute of Science and Technology, Tiruchirappalli (Division of Chemistry).
Enter SMILES, validate structures, view 2D and interactive 3D structures, calculate RDKit descriptors, download reports,
compare molecules, browse a library and take an assessment. All chemistry runs locally with RDKit.

> **Honest status:** this project was generated in an environment with **no network access**, so RDKit, Streamlit, Plotly and
> pytest could not be installed there. Only the pure-Python parts were executed (see "Verification status"). Run the test suite
> on your machine before submitting or deploying.

## Features
Dashboard · Molecular Library · Add Molecules (SMILES input, validation, 2D PNG, 3D viewer with 4 styles, properties,
PDF/CSV/JSON/PNG/MOL/SDF exports, save to library, comparison) · Assessment (practice + scored) · About.

## Project layout
```
app.py                 entry point (st.navigation)
config.py              institution text, developer details, limits  <-- edit here
pages/                 1_Dashboard … 5_About
modules/               chemistry, visualization, comparison, reports, library, assessment, ui
assets/styles.css      dark green + navy theme (plus .streamlit/config.toml)
tests/                 pytest suite
```

## Run locally on Windows
1. Install Python **3.11** (https://www.python.org/downloads/) and tick "Add python.exe to PATH".
2. Open PowerShell in the project folder and create a virtual environment:
   ```
   py -3.11 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
   (If scripts are blocked: `Set-ExecutionPolicy -Scope Process RemoteSigned`, or use `.venv\Scripts\activate.bat` in cmd.)
3. Install dependencies: `python -m pip install --upgrade pip` then `pip install -r requirements.txt`
4. Launch: `streamlit run app.py` (opens http://localhost:8501).
5. Run tests: `pytest -v`

macOS/Linux: `python3.11 -m venv .venv && source .venv/bin/activate`, then the same pip/streamlit/pytest commands.

## Deploy to Streamlit Community Cloud
1. Create a GitHub repository, then in the project folder: `git init`, `git add .`, `git commit -m "MoleculeVerse"`,
   `git branch -M main`, `git remote add origin <your-repo-url>`, `git push -u origin main`.
2. At https://share.streamlit.io choose **New app**, pick the repo, branch `main`, main file `app.py`.
3. Under **Advanced settings** choose **Python 3.11**.
4. `packages.txt` installs `libxrender1` and `libxext6`, which RDKit's drawing code can need on Linux.
5. Deploy and open every page once to check it.

## Where data lives
Library additions, student fields, comparison selections, scores and statistics are in `st.session_state` only. Nothing is written to disk
and everything disappears when the browser session ends (clear it sooner with "Remove all user-added molecules" or by refreshing).
Use the export buttons to keep results.

## Limitations
- A valid SMILES is only a parsed structure, not proof of stability or synthesizability.
- 3D structures are single computed conformers (ETKDG + MMFF94/UFF), not experimental geometries.
- The 3D viewer loads 3Dmol.js from a CDN (3dmol.org, then jsDelivr), so the browser needs internet access.
- PDF reports contain the 2D image; a 3D snapshot cannot be returned from the browser component, so it is omitted. The 3D conformer is exported as SDF.
- Heavy-atom limits: 200 for analysis, 100 for 3D generation. SMILES length limit 500. Uploads: .mol/.sdf/.smi/.txt up to 1 MB.
- Library SMILES (including glucose stereochemistry) are checked by the tests for validity and formula only; confirm stereochemistry against a reference if it matters.

## Manual verification checklist (browser features)
1. Add Molecules → load Aspirin → 3D tab: rotate, zoom, press Reset view and Spin.
2. Switch Style through all four options and Atom colours/Background; the molecule must visibly change each time.
3. Enter `C(C` → a plain-language error appears, no traceback.
4. Export tab: open the PDF, CSV, JSON, PNG and MOL/SDF downloads.
5. Compare Ethanol, Benzene and a typed invalid SMILES → valid ones still compare.
6. Navigate between pages; typed SMILES and student fields should persist.

## Troubleshooting
- `ImportError: libXrender.so.1` → install `libxrender1` (already in `packages.txt` for Streamlit Cloud).
- `No matching distribution for rdkit` → use Python 3.10–3.12 (64-bit). On unusual platforms use conda: `conda install -c conda-forge rdkit`.
- 3D panel stays on "Loading" → the browser cannot reach the CDN; check connection, ad-blockers or firewalls.
- Pinned versions in `requirements.txt` were not tested together here; if pip reports a conflict, relax the pins and re-run `pytest`.
