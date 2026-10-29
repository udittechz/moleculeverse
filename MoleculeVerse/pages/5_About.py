"""About: purpose, features, technology, how RDKit helps, SMILES and descriptors, configurable project details."""
import streamlit as st

import config
from modules import ui

ui.init_state()
ui.page_header(config.APP_NAME, config.APP_SUBTITLE)

st.markdown(f"**{config.INSTITUTION}**  \n{config.DEPARTMENT_LINE}")

st.subheader("Purpose and educational objectives")
st.write(
    "MoleculeVerse is an academic project that lets students explore molecules computationally: reading and writing SMILES, "
    "viewing 2D and 3D structures, calculating descriptors, and comparing molecules. It is a teaching tool, not a research or safety tool."
)
st.markdown(
    "- Understand SMILES notation and molecular representations\n- Generate and interpret 2D and 3D structures\n"
    "- Understand and interpret molecular descriptors\n- Examine structure–property relationships and compare molecules"
)

st.subheader("Supported features")
st.markdown(
    "- SMILES input with validation and friendly error messages\n- 2D structure diagrams (PNG download)\n"
    "- Interactive 3D conformers with four display styles\n- Descriptor calculation with explanations\n"
    "- PDF, CSV, JSON and MOL/SDF exports\n- Multi-molecule comparison with charts and Tanimoto similarity\n"
    "- Searchable molecular library and a scored/practice assessment"
)

st.subheader("Technology stack")
st.table({"Component": ["Streamlit", "RDKit", "3Dmol.js", "Plotly", "Pandas", "ReportLab", "pytest"],
          "Role": ["Web application and navigation", "Parsing, validation, descriptors, depiction, conformers, fingerprints",
                   "Interactive 3D viewer in the browser", "Interactive charts", "Tabular data", "PDF reports", "Automated tests"]})

c1, c2 = st.columns(2)
with c1:
    st.subheader("How RDKit supports the calculations")
    st.write(
        "RDKit turns a SMILES string into a molecular graph, checks it (sanitization), and computes descriptors from that graph. "
        "It also draws 2D diagrams, embeds 3D conformers (ETKDG) and optimizes them with force fields (MMFF94 or UFF). "
        "Everything runs locally; no external chemistry service is used."
    )
with c2:
    st.subheader("SMILES and molecular descriptors")
    st.write(
        "SMILES is a line notation for molecules, e.g. CCO for ethanol. A descriptor is a number calculated from the structure, "
        "such as molecular weight, logP or TPSA. Descriptors are calculated values, not experimental measurements, and they do not by "
        "themselves prove stability, activity or safety."
    )

st.subheader("Limitations")
st.markdown(
    "- A valid SMILES is only a parsed structure, not proof that a molecule is stable or can be made.\n"
    "- 3D structures are single computed conformers, not experimental geometries.\n"
    "- The 3D viewer needs a browser able to load 3Dmol.js from a CDN.\n"
    "- Library additions, scores and statistics are session-only; nothing is written to disk."
)

st.subheader("Project details")
st.caption("Edit these in config.py. Empty entries are shown as Not provided; nothing is invented.")
rows = []
for label, value in config.DEVELOPER.items():
    if label == "Registration number" and not config.SHOW_REGISTRATION_ON_ABOUT:
        shown = "Hidden (set SHOW_REGISTRATION_ON_ABOUT = True in config.py to display)" if value else "Not provided"
    else:
        shown = value or "Not provided"
    rows.append({"Item": label, "Value": shown})
st.table(rows)
