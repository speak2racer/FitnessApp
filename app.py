import streamlit as st
from utils import lade_css

st.set_page_config(
    page_title="Fitness Dashboard",
    page_icon=":material/fitness_center:",
    layout="wide",
    initial_sidebar_state="expanded"
)
lade_css()

pg = st.navigation([
    st.Page("dashboard.py",                   title="Dashboard",      icon=":material/dashboard:"),
    st.Page("pages/1_Tagesdaten.py",          title="Tagesdaten",     icon=":material/today:"),
    st.Page("pages/2_Wochenanalyse.py",       title="Wochenanalyse",  icon=":material/bar_chart:"),
    st.Page("pages/3_Caliper.py",             title="Caliper",        icon=":material/straighten:"),
    st.Page("pages/4_Datenverwaltung.py",     title="Datenverwaltung",icon=":material/edit_note:"),
    st.Page("pages/5_Zielsteuerung.py",       title="Zielsteuerung",  icon=":material/track_changes:"),
])
pg.run()
