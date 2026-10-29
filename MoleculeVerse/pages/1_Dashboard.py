"""Dashboard: identity, shortcuts, optional student info, features, objectives, real session stats."""
import streamlit as st

import config
from modules import ui

ui.init_state()
ss = st.session_state

# Persist optional student inputs across page changes (widget keys are dropped when a page is left).
if "mv_w_student_name" not in ss:
    ss["mv_w_student_name"] = ss["mv_student_name"]
if "mv_w_student_reg" not in ss:
    ss["mv_w_student_reg"] = ss["mv_student_reg"]


def _sync_student() -> None:
    ss["mv_student_name"] = ss["mv_w_student_name"].strip()[:80]
    ss["mv_student_reg"] = ss["mv_w_student_reg"].strip()[:40]


st.markdown(
    f"""<div class="mv-hero"><div>
    <h1>{config.APP_NAME}</h1><div class="mv-sub">{config.APP_SUBTITLE}</div>
    <p class="mv-inst">{config.INSTITUTION}</p><p class="mv-dept">{config.DEPARTMENT_LINE}</p></div>
    <div>{ui.hero_svg()}</div></div>""",
    unsafe_allow_html=True,
)

st.header("Welcome to the Virtual Laboratory")
st.write(
    "An interactive learning environment for exploring molecular structures, computational chemistry, "
    "molecular properties, and structure–property relationships."
)
c1, c2, c3, c4 = st.columns(4)
if c1.button("Explore Molecular Library", use_container_width=True, type="primary", key="mv_d_lib"):
    ui.goto("library")
if c2.button("Add a Molecule", use_container_width=True, key="mv_d_add"):
    ui.goto("add", section="Analyze")
if c3.button("Compare Molecules", use_container_width=True, key="mv_d_cmp"):
    ui.goto("add", section="Compare")
if c4.button("Start Assessment", use_container_width=True, key="mv_d_asm"):
    ui.goto("assessment")

st.subheader("Student information (optional)")
with st.container(border=True):
    a, b = st.columns(2)
    a.text_input("Student name", key="mv_w_student_name", on_change=_sync_student, max_chars=80)
    b.text_input("Registration number", key="mv_w_student_reg", on_change=_sync_student, max_chars=40)
    st.caption(
        "Optional and kept only in this browser session. These details are never shown publicly and are "
        "included in a PDF report only if you tick the option on the Add Molecules page."
    )

st.subheader("What can students do?")
features = [
    ("Enter any SMILES notation", "Type or load a SMILES string.", "add", "Analyze"),
    ("Validate molecular structures", "Clear, friendly parsing feedback from RDKit.", "add", "Analyze"),
    ("Generate 2D structures", "Publication-style diagrams with PNG download.", "add", "Analyze"),
    ("Generate interactive 3D structures", "Rotate and zoom a computed conformer.", "add", "Analyze"),
    ("Select visualization styles", "Ball-and-stick, stick, space-filling, wireframe.", "add", "Analyze"),
    ("Calculate molecular properties", "Descriptors with plain-language explanations.", "add", "Analyze"),
    ("Download molecular reports", "PDF, CSV, JSON, PNG and MOL/SDF exports.", "add", "Analyze"),
    ("Compare multiple molecules", "Side-by-side tables, charts and similarity.", "add", "Compare"),
]
for row in range(0, len(features), 4):
    cols = st.columns(4)
    for col, (title, text, page, section) in zip(cols, features[row:row + 4]):
        with col:
            st.markdown(f"<div class='mv-card'><h4>{title}</h4><p>{text}</p></div>", unsafe_allow_html=True)
            if st.button("Open tool", key=f"mv_feat_{title}", use_container_width=True):
                ui.goto(page, section=section)

st.subheader("Learning objectives")
objectives = [
    "Understand SMILES notation.", "Interpret molecular representations.", "Generate and understand 2D structures.",
    "Explore molecular geometry in 3D.", "Understand molecular descriptors.", "Examine structure–property relationships.",
    "Compare molecular structures and properties.", "Interpret calculated chemical properties.",
]
oa, ob = st.columns(2)
for col, chunk in ((oa, objectives[:4]), (ob, objectives[4:])):
    col.markdown("<ul class='mv-objectives'>" + "".join(f"<li>{o}</li>" for o in chunk) + "</ul>", unsafe_allow_html=True)

st.subheader("Session statistics")
stats = ui.session_stats()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Molecules in library", stats["library"])
m2.metric("Added this session", stats["added"])
m3.metric("Comparisons performed", stats["comparisons"])
m4.metric("Assessment questions answered", stats["answered"])
st.caption("Counts come from this session only and reset when the session ends.")

st.subheader("Recent activity")
activity = ss["mv_activity"]
history = ss["mv_assess_history"]
if not activity and not history:
    st.markdown("<div class='mv-empty'>No activity yet. Analyze a molecule, run a comparison or take an assessment and it will appear here.</div>", unsafe_allow_html=True)
for i, item in enumerate(activity[:6]):
    c_a, c_b = st.columns([5, 1])
    c_a.markdown(f"**{item['label']}**  \n<span class='mv-muted'>{item['kind']} · {item['time']}</span>", unsafe_allow_html=True)
    if item.get("smiles") and c_b.button("Reopen", key=f"mv_reopen_{i}", use_container_width=True):
        ui.open_molecule(item["smiles"], item.get("name", ""))
for h in history[-3:][::-1]:
    st.markdown(f"**Scored assessment:** {h['score']}/{h['total']} ({h['percent']}%) <span class='mv-muted'>· {h['time']}</span>", unsafe_allow_html=True)
