"""Add Molecules: the chemistry workspace (SMILES input, validation, 2D/3D, properties, exports, comparison)."""
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

import config
from modules import chemistry, comparison, library, reports, ui, visualization

ui.init_state()
ss = st.session_state
ui.page_header("Add Molecules", "Enter a SMILES string, validate it, explore it in 2D and 3D, calculate properties, export reports, or compare molecules.")

# ------------------------------------------------------------------ one-shot requests from other pages
req_load = ss.pop("mv_req_load", None)
if req_load:
    ss["mv_w_smiles"], ss["mv_w_name"] = req_load["smiles"], req_load.get("name", "")
    ss["mv_ws_smiles"], ss["mv_ws_name"] = ss["mv_w_smiles"], ss["mv_w_name"]
    ss["mv_current_molecule"] = {"smiles": req_load["smiles"], "name": req_load.get("name", "")}
req_section = ss.pop("mv_req_section", None)
if req_section:
    ss["mv_w_section"] = req_section
ss.setdefault("mv_w_section", "Analyze")
if "mv_w_smiles" not in ss:  # widget keys are dropped when leaving the page; restore from the persisted copy
    ss["mv_w_smiles"], ss["mv_w_name"] = ss["mv_ws_smiles"], ss["mv_ws_name"]
for key, default in (("mv_viewer_style", "Ball-and-stick"), ("mv_viewer_colors", visualization.COLOR_NAMES[0]),
                     ("mv_viewer_bg", "Dark navy")):
    ss.setdefault(key, default)

lib = ss["mv_library"]


# ------------------------------------------------------------------ callbacks (safe place to change widget state)
def _analyze() -> None:
    smiles = ss["mv_w_smiles"].strip()
    name = ss["mv_w_name"].strip()
    ss["mv_ws_smiles"], ss["mv_ws_name"] = ss["mv_w_smiles"], ss["mv_w_name"]
    ss["mv_current_molecule"] = {"smiles": smiles, "name": name}
    rec = ui.cached_analysis(smiles, name)
    if rec["valid"]:
        ui.log_activity("Analyzed molecule", f"{name or rec['formula']} ({rec['formula']})", smiles, name)


def _load_example() -> None:
    entry = library.find(lib, ss["mv_w_example"])
    if entry:
        ss["mv_w_smiles"], ss["mv_w_name"] = entry["smiles"], entry["name"]
        _analyze()


def _reset() -> None:
    ss["mv_w_smiles"] = ss["mv_w_name"] = ss["mv_ws_smiles"] = ss["mv_ws_name"] = ""
    ss["mv_current_molecule"] = None
    ss["mv_upload_msg"] = ""


def _use_upload() -> None:
    f = ss.get("mv_w_upload")
    if f is None:
        ss["mv_upload_msg"] = "Choose a file first."
        return
    res = chemistry.parse_structure_bytes(f.getvalue(), f.name)
    if res.ok:
        ss["mv_w_smiles"] = res.smiles
        ss["mv_w_name"] = f.name.rsplit(".", 1)[0][:60]
        ss["mv_upload_msg"] = ""
        _analyze()
    else:
        ss["mv_upload_msg"] = res.message


def _save_to_library() -> None:
    cur = ss["mv_current_molecule"]
    if cur:
        ok, msg, entry = library.add_user_molecule(lib, ss.get("mv_w_save_name", ""), cur["smiles"])
        ss["mv_save_msg"] = (ok, msg)
        if ok:
            ui.log_activity("Added molecule", entry["name"], entry["smiles"], entry["name"])


def _sync_cmp() -> None:
    ss["mv_compare_selection"] = list(ss["mv_w_cmp_ids"])


def _sync_cmp_text() -> None:
    ss["mv_compare_text"] = ss["mv_w_cmp_text"]


def _run_compare() -> None:
    entries: list[tuple[str, str]] = []
    for mid in ss["mv_compare_selection"]:
        e = library.find(lib, mid)
        if e:
            entries.append((e["name"], e["smiles"]))
    for line in ss.get("mv_w_cmp_text", "").splitlines():
        line = line.strip()
        if not line:
            continue
        label, _, smi = line.partition("|") if "|" in line else ("", "", line)
        entries.append((label.strip(), smi.strip()))
    if len(entries) < 2:
        ss["mv_compare_msg"] = "Select or enter at least two molecules to compare."
        ss["mv_compare_request"] = None
        return
    if len(entries) > config.MAX_COMPARE_MOLECULES:
        entries = entries[: config.MAX_COMPARE_MOLECULES]
        ss["mv_compare_msg"] = f"Only the first {config.MAX_COMPARE_MOLECULES} molecules are compared."
    else:
        ss["mv_compare_msg"] = ""
    ss["mv_compare_request"] = entries
    ss["mv_comparisons"] += 1
    ui.log_activity("Comparison", f"Compared {len(entries)} molecules: " + ", ".join(n or s[:12] for n, s in entries[:4]))


section = st.radio("Workspace", ["Analyze", "Compare"], horizontal=True, key="mv_w_section", label_visibility="collapsed")

# =================================================================== ANALYZE
if section == "Analyze":
    left, right = st.columns([5, 7], gap="large")
    with left, st.container(border=True):
        st.subheader("1. Molecular input")
        options = [e["id"] for e in lib]
        st.selectbox("Example molecules", options, key="mv_w_example",
                     format_func=lambda i: f"{library.find(lib, i)['name']}  ({library.find(lib, i)['smiles']})")
        st.button("Load selected example", on_click=_load_example, key="mv_b_load", use_container_width=True)
        st.text_input("SMILES notation", key="mv_w_smiles", on_change=_analyze, max_chars=chemistry.MAX_SMILES_LENGTH,
                      placeholder="e.g. CC(=O)Oc1ccccc1C(=O)O", help="Press Enter or use the button below. One molecule per entry, no spaces.")
        st.text_input("Molecule name (optional)", key="mv_w_name", max_chars=config.MAX_MOLECULE_NAME_LENGTH)
        b1, b2 = st.columns(2)
        b1.button("Validate and analyze", type="primary", on_click=_analyze, key="mv_b_an", use_container_width=True)
        b2.button("Clear / reset", on_click=_reset, key="mv_b_reset", use_container_width=True)
        with st.expander("SMILES quick guide"):
            st.markdown(
                "- Atoms are written as element symbols: `C`, `N`, `O`, `Cl`.\n"
                "- `=` double bond, `#` triple bond; parentheses `( )` open a branch.\n"
                "- Digits close rings: `C1CCCCC1` is cyclohexane; lowercase letters are aromatic: `c1ccccc1`.\n"
                "- Charges and explicit hydrogens go in brackets: `[NH4+]`, `CC(=O)[O-]`.\n"
                "- `@` / `@@` mark tetrahedral stereochemistry; `/` and `\\` mark double-bond geometry.\n\n"
                "Examples: water `O`, ethanol `CCO`, benzene `c1ccccc1`, aspirin `CC(=O)Oc1ccccc1C(=O)O`, caffeine `Cn1c(=O)c2c(ncn2C)n(C)c1=O`."
            )
        with st.expander("Upload a structure file (.mol, .sdf, .smi)"):
            st.file_uploader("Structure file (max 1 MB)", type=["mol", "sdf", "smi", "txt"], key="mv_w_upload")
            st.button("Use uploaded file", on_click=_use_upload, key="mv_b_up")
            if ss.get("mv_upload_msg"):
                st.error(ss["mv_upload_msg"])

    with right:
        cur = ss["mv_current_molecule"]
        if not cur:
            st.markdown("<div class='mv-empty'><b>No molecule loaded yet.</b><br>Enter a SMILES string, load an example, or upload a file to see structures and properties.</div>", unsafe_allow_html=True)
        else:
            with st.spinner("Validating and calculating..."):
                rec = ui.cached_analysis(cur["smiles"], cur["name"])
            if not rec["valid"]:
                st.markdown(f"<div class='mv-err'><b>Not a valid structure.</b> {rec['message']}</div>", unsafe_allow_html=True)
                if rec.get("detail"):
                    st.caption(f"RDKit detail: {rec['detail']}")
            else:
                st.markdown(f"<div class='mv-ok'><b>Valid structure.</b> RDKit parsed and sanitized this SMILES. "
                            "This does not mean the molecule is stable, synthesizable or experimentally confirmed.</div>", unsafe_allow_html=True)
                for w in rec["warnings"]:
                    st.warning(w)
                title = cur["name"] or rec["formula"]
                st.subheader(f"{title}  ·  {rec['formula']}")
                tab2d, tab3d, tabprops, tabexp = st.tabs(["2D structure", "3D viewer", "Properties", "Export and save"])
                smiles = rec["input_smiles"]

                with tab2d:
                    png = ui.cached_png(smiles, 720, 520)
                    if png:
                        st.image(png, use_container_width=True)
                        st.caption("2D depiction computed by RDKit from the same parsed molecule used for the descriptors. Heteroatoms are labelled; stereochemistry is annotated where defined.")
                        st.download_button("Download 2D structure (PNG)", png, chemistry.safe_filename(title, "png"), "image/png", key="mv_dl_png2d")
                    else:
                        st.error("The 2D diagram could not be drawn for this molecule.")

                with tab3d:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.selectbox("Style", visualization.STYLE_NAMES, key="mv_viewer_style")
                    c2.selectbox("Atom colours", visualization.COLOR_NAMES, key="mv_viewer_colors")
                    c3.selectbox("Background", visualization.BACKGROUND_NAMES, key="mv_viewer_bg")
                   spin = c4.checkbox(
    "Auto-rotate 360°",
    value=True,
    key="mv_viewer_spin",
    help="Automatically rotate the molecule. Uncheck to stop."
)
                    with st.spinner("Generating a 3D conformer (RDKit ETKDG + force field)..."):
                        conf = ui.cached_3d(smiles)
                    if conf["ok"]:
                        components.html(visualization.build_viewer_html(conf["molblock"], ss["mv_viewer_style"], ss["mv_viewer_colors"],
                                                                         ss["mv_viewer_bg"], spin, 460), height=480)
                        st.caption(f"Computational conformer ({conf['method']}). {conf['message']} Drag to rotate, scroll to zoom, right-drag or Shift-drag to pan; use Reset view to recentre. "
                                   "The viewer loads 3Dmol.js from a CDN, so it needs an internet connection in your browser.")
                    else:
                        st.warning(conf["message"])

                with tabprops:
                    v = rec["values"]
                    m = st.columns(4)
                    m[0].metric("Molecular weight", f"{v['mol_weight']} g/mol")
                    m[1].metric("Calculated logP", v["logp"])
                    m[2].metric("TPSA", f"{v['tpsa']} Å²")
                    m[3].metric("Heavy atoms", v["heavy_atoms"])
                    m = st.columns(4)
                    m[0].metric("H-bond donors", v["hbd"])
                    m[1].metric("H-bond acceptors", v["hba"])
                    m[2].metric("Rotatable bonds", v["rotatable_bonds"])
                    m[3].metric("Rings", v["ring_count"])
                    for category in chemistry.CATEGORY_ORDER:
                        with st.expander(category, expanded=category == chemistry.CATEGORY_ORDER[0]):
                            df = pd.DataFrame([{"Property": p["label"], "Value": "Not available" if p["value"] is None else str(p["value"]),
                                                "Unit": p["unit"], "What it measures": p["explanation"]}
                                               for p in rec["properties"] if p["category"] == category])
                            st.dataframe(df, hide_index=True, use_container_width=True)
                    with st.expander("Element composition and fingerprint"):
                        st.dataframe(pd.DataFrame(rec["composition"]).rename(columns={"element": "Element", "count": "Atoms", "mass_percent": "Mass %"}),
                                     hide_index=True, use_container_width=True)
                        fp = rec["fingerprint"]
                        st.write(f"{fp['type']}: {fp['bits_set']} of {fp['length']} bits set. First set bits: {fp['first_bits_set']}")
                        if rec.get("inchikey"):
                            st.write(f"InChIKey: {rec['inchikey']}")
                    if rec["descriptor_errors"]:
                        st.warning("Some descriptors could not be calculated: " + ", ".join(rec["descriptor_errors"]))
                    st.caption(chemistry.DISCLAIMER)

                with tabexp:
                    include = st.checkbox("Include my name / registration number in the PDF report", key="mv_w_incl_student", value=False,
                                          help="Off by default. Student details are never added to CSV, JSON or structure files.")
                    s_name = ss["mv_student_name"] if include else ""
                    s_reg = ss["mv_student_reg"] if include else ""
                    if include and not (s_name or s_reg):
                        st.info("No student details entered yet. You can add them on the Dashboard.")
                    d1, d2, d3 = st.columns(3)
                    try:
                        pdf = ui.cached_pdf(smiles, cur["name"], s_name, s_reg)
                        d1.download_button("PDF report", pdf, chemistry.safe_filename(title, "pdf"), "application/pdf", key="mv_dl_pdf", use_container_width=True)
                    except Exception:
                        d1.error("The PDF report could not be generated.")
                    d2.download_button("Properties (CSV)", reports.properties_to_csv(rec), chemistry.safe_filename(title, "csv"), "text/csv", key="mv_dl_csv", use_container_width=True)
                    d3.download_button("Molecule data (JSON)", reports.record_to_json(rec), chemistry.safe_filename(title, "json"), "application/json", key="mv_dl_json", use_container_width=True)
                    files = ui.cached_structure_files(smiles, cur["name"])
                    e1, e2 = st.columns(2)
                    if files["mol"]:
                        e1.download_button("Structure (MOL, 2D)", files["mol"], chemistry.safe_filename(title, "mol"), "chemical/x-mdl-molfile", key="mv_dl_mol", use_container_width=True)
                    if files["sdf3d"]:
                        e2.download_button("Structure (SDF, 3D conformer)", files["sdf3d"], chemistry.safe_filename(title, "sdf"), "chemical/x-mdl-sdfile", key="mv_dl_sdf", use_container_width=True)
                    st.caption("The PDF contains the 2D structure. A 3D image is not included because the browser viewer cannot send a snapshot back to the server; the 3D conformer is available as an SDF file instead.")
                    st.divider()
                    st.markdown("**Save to library** (this session only)")
                    st.text_input("Library name", value=cur["name"], key="mv_w_save_name", max_chars=config.MAX_MOLECULE_NAME_LENGTH)
                    st.button("Save valid molecule to library", on_click=_save_to_library, key="mv_b_save", type="primary")
                    saved = ss.pop("mv_save_msg", None)
                    if saved:
                        (st.success if saved[0] else st.warning)(saved[1])

# =================================================================== COMPARE
else:
    st.subheader("Compare molecules")
    id_to_entry = {e["id"]: e for e in lib}
    ss["mv_w_cmp_ids"] = [i for i in ss["mv_compare_selection"] if i in id_to_entry]
    if "mv_w_cmp_text" not in ss:
        ss["mv_w_cmp_text"] = ss["mv_compare_text"]
    with st.container(border=True):
        st.multiselect("Select molecules from the library", list(id_to_entry), key="mv_w_cmp_ids", on_change=_sync_cmp,
                       format_func=lambda i: f"{id_to_entry[i]['name']} ({'built-in' if id_to_entry[i]['builtin'] else 'user-added'})",
                       placeholder="Choose two or more")
        st.text_area("Or enter more SMILES (one per line; optionally `Name | SMILES`)", key="mv_w_cmp_text", on_change=_sync_cmp_text, height=110,
                     placeholder="Propanol | CCCO\nc1ccncc1", max_chars=2000)
        st.button("Compare molecules", type="primary", on_click=_run_compare, key="mv_b_cmp")
    if ss["mv_compare_msg"]:
        st.warning(ss["mv_compare_msg"])
    request = ss["mv_compare_request"]
    if not request:
        st.markdown("<div class='mv-empty'>Choose at least two molecules (or type SMILES) and press <b>Compare molecules</b>.</div>", unsafe_allow_html=True)
    else:
        res = comparison.run_comparison(request, analyzer=ui.cached_analysis)
        for bad in res.invalid:
            st.markdown(f"<div class='mv-err'><b>{bad['label']}</b> could not be compared: {bad['message']}</div>", unsafe_allow_html=True)
        if len(res.valid) < 2:
            st.warning("At least two valid molecules are needed for a comparison. Fix or replace the invalid entries above.")
        if res.valid:
            st.markdown("#### Structures")
            for start in range(0, len(res.valid), 4):
                cols = st.columns(4)
                for col, rec in zip(cols, res.valid[start:start + 4]):
                    png = ui.cached_png(rec["input_smiles"], 360, 280)
                    with col:
                        if png:
                            st.image(png, use_container_width=True)
                        st.markdown(f"**{rec['label']}**  \n<span class='mv-muted'>{rec['formula']}</span>", unsafe_allow_html=True)
            st.markdown("#### Property comparison")
            st.dataframe(res.table, hide_index=True, use_container_width=True)
            st.download_button("Download comparison (CSV)", res.table.to_csv(index=False), "molecule_comparison.csv", "text/csv", key="mv_dl_cmp")
        if res.highlights:
            st.markdown("#### Highlighted differences")
            for h in res.highlights:
                unit = f" {h['unit']}" if h["unit"] else ""
                tag = "Notable difference" if h["meaningful"] else "Similar"
                st.markdown(f"- **{h['label']}** · {tag}: highest {h['highest'][0]} ({h['highest'][1]}{unit}), lowest {h['lowest'][0]} ({h['lowest'][1]}{unit}); spread {h['spread']}{unit}.")
            st.caption("'Notable' means the spread reaches a teaching threshold (about 10 g/mol, 0.5 logP units, 10 Å², or at least 1 for counts); it is a rule of thumb, not a scientific cut-off.")
            cols = [c for c in res.table.columns if c not in ("Molecule", "Formula")]
            pick = st.selectbox("Chart a descriptor", cols, key="mv_w_cmp_chart")
            fig = px.bar(res.table, x="Molecule", y=pick, text_auto=True)
            st.plotly_chart(ui.plotly_layout(fig, pick), use_container_width=True)
        if res.similarity is not None:
            st.markdown("#### Structural similarity (Tanimoto, Morgan fingerprints)")
            fig = px.imshow(res.similarity, text_auto=".2f", zmin=0, zmax=1, color_continuous_scale=[[0, "#0C211C"], [1, "#72E0AD"]])
            st.plotly_chart(ui.plotly_layout(fig), use_container_width=True)
            st.caption("Tanimoto = shared fingerprint bits / total distinct bits (Morgan radius 2, 2048 bits); 1 means identical fingerprints.")
        st.info(comparison.CAUTION)
