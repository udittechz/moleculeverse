"""MoleculeVerse entry point (run with:  streamlit run app.py).

Uses Streamlit's st.navigation so the five pages in ./pages are registered explicitly.
"""
import streamlit as st

import config
from modules import ui

st.set_page_config(
    page_title=f"{config.APP_NAME} | {config.APP_SUBTITLE}",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui.init_state()
ui.inject_css()
ui.sidebar_brand()

navigation = st.navigation(
    [
        st.Page(ui.PAGES["dashboard"], title="Dashboard", default=True),
        st.Page(ui.PAGES["library"], title="Molecular Library"),
        st.Page(ui.PAGES["add"], title="Add Molecules"),
        st.Page(ui.PAGES["assessment"], title="Assessment"),
        st.Page(ui.PAGES["about"], title="About"),
    ]
)
navigation.run()
