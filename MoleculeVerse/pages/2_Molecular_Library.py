"""Molecular Library: searchable, filterable cards for built-in and user-added molecules."""
import math

import pandas as pd
import streamlit as st

from modules import chemistry, library, reports, ui

ui.init_state()
ss = st.session_state
ui.page_header("Molecular Library", "Curated examples plus the molecules you add. Every property is calculated by RDKit.")

lib = ss["mv_library"]
records = {e["id"]: ui.cached_analysis(e["smiles"], e["name"]) for e in lib}
valid_ids = [i for i, r in records.items() if r["valid"]]

# ------------------------------------------------------------------ detail panel
detail_id = ss["mv_lib_detail"]
entry = library.find(lib, detail_id) if detail_id else None
if entry and records.get(entry["id"], {}).get("valid"):
    rec = records[entry["id"]]
    with st.container(border=True):
        top = st.columns([6, 1])
        top[0].subheader(f"{entry['name']}  ·  {rec['formula']}")
        if top[1].button("Close", key="mv_lib_close"):
            ss["mv_lib_detail"] = None
            st.rerun()
        d1, d2 = st.columns([2, 3], gap="large")
        with d1:
            png = ui.cached_png(entry["smiles"], 520, 400)
            if png:
                st.image(png, use_container_width=True)
            st.caption(f"SMILES: {rec['canonical_smiles']}")
            st.markdown(f"<span class='mv-badge {'user' if not entry['builtin'] else ''}'>{'Built-in example' if entry['builtin'] else 'User-added'}</span>", unsafe_allow_html=True)
        with d2:
            df = pd.DataFrame([{"Property": p["label"], "Value": "Not available" if p["value"] is None else str(p["value"]),
                                "Unit": p["unit"], "What it measures": p["explanation"]} for p in rec["properties"]])
            st.dataframe(df, hide_index=True, use_container_width=True, height=300)
        b = st.columns(5)
        if b[0].button("Visualize / analyze", key="mv_det_an", use_container_width=True, type="primary"):
            ui.open_molecule(entry["smiles"], entry["name"])
        if b[1].button("Add to comparison", key="mv_det_cmp", use_container_width=True):
            if entry["id"] not in ss["mv_compare_selection"]:
                ss["mv_compare_selection"].append(entry["id"])
            st.toast("Added to the comparison list.")
        b[2].download_button("Export CSV", reports.properties_to_csv(rec), chemistry.safe_filename(entry["name"], "csv"), "text/csv", key="mv_det_csv", use_container_width=True)
        b[3].download_button("Export JSON", reports.record_to_json(rec), chemistry.safe_filename(entry["name"], "json"), "application/json", key="mv_det_json", use_container_width=True)
        if png:
            b[4].download_button("Export PNG", png, chemistry.safe_filename(entry["name"], "png"), "image/png", key="mv_det_png", use_container_width=True)
        if not entry["builtin"]:
            r1, r2 = st.columns([4, 1])
            new_name = r1.text_input("Rename (the structure stays the same)", value=entry["name"], max_chars=60, key=f"mv_rename_{entry['id']}")
            r2.write("")
            r2.write("")
            if r2.button("Rename", key="mv_rename_btn", use_container_width=True):
                ok, msg = library.rename_molecule(lib, entry["id"], new_name)
                (st.success if ok else st.error)(msg)
                if ok:
                    st.rerun()

# ------------------------------------------------------------------ filters
st.subheader("Browse and filter")
f1, f2 = st.columns([3, 2])
query = f1.text_input("Search by name, formula or SMILES", key="mv_lib_q", placeholder="e.g. aspirin, C9H8O4, c1ccccc1")
source = f2.radio("Source", ["All", "Built-in", "User-added"], horizontal=True, key="mv_lib_src")
cats = sorted({e["category"] for e in lib})
sel_cats = st.multiselect("Molecule category", cats, key="mv_lib_cats", placeholder="All categories")

mws = [records[i]["values"]["mol_weight"] for i in valid_ids]
lps = [records[i]["values"]["logp"] for i in valid_ids]
mw_range = lp_range = None
if len(mws) >= 2:
    s1, s2 = st.columns(2)
    lo, hi = math.floor(min(mws)), math.ceil(max(mws))
    if lo < hi:
        mw_range = s1.slider("Molecular weight (g/mol)", float(lo), float(hi), (float(lo), float(hi)), key=f"mv_lib_mw_{lo}_{hi}")
    llo, lhi = math.floor(min(lps)), math.ceil(max(lps))
    if llo < lhi:
        lp_range = s2.slider("Calculated logP", float(llo), float(lhi), (float(llo), float(lhi)), key=f"mv_lib_lp_{llo}_{lhi}")


def _matches(e: dict) -> bool:
    r = records[e["id"]]
    if not r["valid"]:
        return False
    if source == "Built-in" and not e["builtin"]:
        return False
    if source == "User-added" and e["builtin"]:
        return False
    if sel_cats and e["category"] not in sel_cats:
        return False
    q = query.strip().lower()
    if q and q not in e["name"].lower() and q not in (r["formula"] or "").lower() and q not in e["smiles"].lower():
        return False
    if mw_range and not (mw_range[0] <= r["values"]["mol_weight"] <= mw_range[1]):
        return False
    if lp_range and not (lp_range[0] <= r["values"]["logp"] <= lp_range[1]):
        return False
    return True


shown = [e for e in lib if _matches(e)]
st.caption(f"Showing {len(shown)} of {len(lib)} molecules. Built-in examples are fixed; user-added molecules live in this session only (nothing is stored on disk).")

if shown:
    table = pd.DataFrame([{"Name": e["name"], "Formula": records[e["id"]]["formula"], "Category": e["category"],
                           "MW (g/mol)": records[e["id"]]["values"]["mol_weight"], "logP": records[e["id"]]["values"]["logp"],
                           "TPSA (Å²)": records[e["id"]]["values"]["tpsa"], "SMILES": e["smiles"]} for e in shown])
    st.download_button("Download filtered list (CSV)", table.to_csv(index=False), "molecule_library.csv", "text/csv", key="mv_lib_dl")

# ------------------------------------------------------------------ cards
if not shown:
    st.markdown("<div class='mv-empty'>No molecules match these filters. Clear the search or widen the ranges, or add a new molecule on the Add Molecules page.</div>", unsafe_allow_html=True)
for start in range(0, len(shown), 3):
    cols = st.columns(3, gap="medium")
    for col, e in zip(cols, shown[start:start + 3]):
        r = records[e["id"]]
        with col, st.container(border=True):
            png = ui.cached_png(e["smiles"], 360, 260)
            if png:
                st.image(png, use_container_width=True)
            badge = "<span class='mv-badge'>Built-in</span>" if e["builtin"] else "<span class='mv-badge user'>User-added</span>"
            st.markdown(f"**{e['name']}** {badge}", unsafe_allow_html=True)
            st.markdown(f"<span class='mv-muted'>{r['formula']} · {e['category']}</span>", unsafe_allow_html=True)
            st.caption(f"MW {r['values']['mol_weight']} g/mol · logP {r['values']['logp']} · TPSA {r['values']['tpsa']} Å²")
            a, b = st.columns(2)
            if a.button("Details", key=f"mv_det_{e['id']}", use_container_width=True):
                ss["mv_lib_detail"] = e["id"]
                st.rerun()
            if b.button("Visualize", key=f"mv_vis_{e['id']}", use_container_width=True):
                ui.open_molecule(e["smiles"], e["name"])
            c, d = st.columns(2)
            in_cmp = e["id"] in ss["mv_compare_selection"]
            if c.button("Remove from compare" if in_cmp else "Compare", key=f"mv_cmpb_{e['id']}", use_container_width=True):
                if in_cmp:
                    ss["mv_compare_selection"].remove(e["id"])
                else:
                    ss["mv_compare_selection"].append(e["id"])
                st.rerun()
            if not e["builtin"]:
                if d.button("Remove", key=f"mv_rm_{e['id']}", use_container_width=True):
                    library.remove_molecule(lib, e["id"])
                    ss["mv_compare_selection"] = [i for i in ss["mv_compare_selection"] if i != e["id"]]
                    if ss["mv_lib_detail"] == e["id"]:
                        ss["mv_lib_detail"] = None
                    st.rerun()

sel = ss["mv_compare_selection"]
if sel:
    names = [library.find(lib, i)["name"] for i in sel if library.find(lib, i)]
    st.info("Selected for comparison: " + ", ".join(names))
    if st.button("Go to comparison", key="mv_lib_gocmp", type="primary"):
        ui.goto("add", section="Compare")

user = library.user_molecules(lib)
if user:
    with st.expander("Manage user-added molecules"):
        st.write(f"{len(user)} user-added molecule(s) are stored in this browser session only.")
        if st.button("Remove all user-added molecules", key="mv_clear_user"):
            library.clear_user_molecules(lib)
            ss["mv_compare_selection"] = [i for i in ss["mv_compare_selection"] if library.find(lib, i)]
            ss["mv_lib_detail"] = None
            st.rerun()
