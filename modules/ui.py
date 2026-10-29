"""Shared Streamlit helpers: session state, CSS, navigation, cached chemistry calls."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

import streamlit as st

import config
from . import chemistry, library, reports

ROOT = Path(__file__).resolve().parent.parent
PAGES = {
    "dashboard": "pages/1_Dashboard.py",
    "library": "pages/2_Molecular_Library.py",
    "add": "pages/3_Add_Molecules.py",
    "assessment": "pages/4_Assessment.py",
    "about": "pages/5_About.py",
}

# ------------------------------------------------------------------ session state (all keys prefixed "mv_")
def init_state() -> None:
    """Initialise every session key exactly once (safe to call on every rerun)."""
    ss = st.session_state
    defaults: dict[str, Any] = {
        "mv_student_name": "", "mv_student_reg": "",
        "mv_current_molecule": None,
        "mv_ws_smiles": "", "mv_ws_name": "",
        "mv_compare_selection": [], "mv_compare_text": "", "mv_compare_request": None, "mv_compare_msg": "",
        "mv_comparisons": 0, "mv_questions_answered": 0,
        "mv_assess": None, "mv_assess_history": [],
        "mv_activity": [], "mv_lib_detail": None,
    }
    for key, value in defaults.items():
        if key not in ss:
            ss[key] = value
    if "mv_library" not in ss:
        ss["mv_library"] = library.default_library()


def log_activity(kind: str, label: str, smiles: Optional[str] = None, name: str = "") -> None:
    items = st.session_state.mv_activity
    items.insert(0, {"kind": kind, "label": label, "smiles": smiles, "name": name, "time": time.strftime("%H:%M:%S")})
    del items[25:]


def session_stats() -> dict[str, int]:
    lib = st.session_state.mv_library
    return {
        "library": len(lib),
        "added": len(library.user_molecules(lib)),
        "comparisons": st.session_state.mv_comparisons,
        "answered": st.session_state.mv_questions_answered,
    }


# ------------------------------------------------------------------ navigation
def goto(page: str, **requests: Any) -> None:
    """Switch page, optionally leaving one-shot requests (consumed by the target page)."""
    for k, v in requests.items():
        st.session_state[f"mv_req_{k}"] = v
    st.switch_page(PAGES[page])


def open_molecule(smiles: str, name: str = "") -> None:
    """Open a molecule in the Add Molecules workspace."""
    goto("add", load={"smiles": smiles, "name": name}, section="Analyze")


# ------------------------------------------------------------------ look and feel
def inject_css() -> None:
    css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def sidebar_brand() -> None:
    with st.sidebar:
        st.markdown(
            f"<div class='mv-brand'><div class='mv-brand-name'>{config.APP_NAME}</div>"
            f"<div class='mv-brand-sub'>{config.APP_SUBTITLE}</div></div>",
            unsafe_allow_html=True,
        )


def page_header(title: str, subtitle: str) -> None:
    st.markdown(f"<div class='mv-pagehead'><h1>{title}</h1><p>{subtitle}</p></div>", unsafe_allow_html=True)


def hero_svg() -> str:
    return (ROOT / "assets" / "images" / "hero.svg").read_text(encoding="utf-8")


def plotly_layout(fig, title: str = ""):
    fig.update_layout(
        title=title, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F1F7F4"), colorway=["#72E0AD", "#2FA876", "#8FB8FF", "#E6C36A", "#C792EA"],
        margin=dict(l=10, r=10, t=50, b=10),
    )
    fig.update_xaxes(gridcolor="#1E3A32")
    fig.update_yaxes(gridcolor="#1E3A32")
    return fig


# ------------------------------------------------------------------ cached chemistry calls
@st.cache_data(show_spinner=False, max_entries=512)
def cached_analysis(smiles: str, name: str = "") -> dict[str, Any]:
    return chemistry.analyze_smiles(smiles, name)


@st.cache_data(show_spinner=False, max_entries=256)
def cached_png(smiles: str, width: int = 520, height: int = 400) -> Optional[bytes]:
    return chemistry.smiles_to_png(smiles, (width, height))


@st.cache_data(show_spinner=False, max_entries=64)
def cached_3d(smiles: str) -> dict[str, Any]:
    c = chemistry.smiles_to_3d(smiles)
    return {"ok": c.ok, "molblock": c.molblock, "message": c.message, "method": c.method, "converged": c.converged}


@st.cache_data(show_spinner=False, max_entries=32)
def cached_pdf(smiles: str, name: str, student_name: str, student_reg: str) -> bytes:
    rec = chemistry.analyze_smiles(smiles, name)
    png = chemistry.smiles_to_png(smiles, (720, 520))
    student = {"name": student_name, "registration": student_reg} if (student_name or student_reg) else None
    return reports.build_pdf_report(rec, png, None, student)


@st.cache_data(show_spinner=False, max_entries=64)
def cached_structure_files(smiles: str, name: str) -> dict[str, Optional[str]]:
    """MOL (2D) and SDF (3D if available) text for download."""
    pr = chemistry.parse_smiles(smiles)
    if not pr.ok or pr.mol is None:
        return {"mol": None, "sdf3d": None}
    conf = chemistry.generate_3d(pr.mol)
    return {
        "mol": chemistry.mol_to_molblock(pr.mol),
        "sdf3d": chemistry.molblock_to_sdf(conf.molblock, name, {"SMILES": pr.smiles}) if conf.ok and conf.molblock else None,
    }
