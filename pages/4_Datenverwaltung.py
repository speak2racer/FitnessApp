import streamlit as st
import pandas as pd

from utils import (
    lade_tagesdaten,
    loesche_supabase_gewicht,
    loesche_alle_supabase_gewichte,
    lade_css
)

st.set_page_config(
    page_title="Datenverwaltung",
    layout="wide"
)

lade_css()

st.title("🗑️ Datenverwaltung")
st.caption("Verwalte deine synchronisierten Gewichtsdaten aus Supabase.")

daten = lade_tagesdaten()

if daten.empty:

    st.warning(
        "Keine Gewichtsdaten vorhanden."
    )

    st.stop()

daten = daten.sort_values(
    "Datum",
    ascending=False
)

anzeigen = daten.copy()

anzeigen["Datum"] = (
    anzeigen["Datum"]
    .dt.strftime("%Y-%m-%d")
)

with st.container(border=True):

    st.subheader(
        "⚖️ Gewichtseinträge"
    )

    auswahl = st.selectbox(

        "Eintrag auswählen",

        anzeigen["Datum"].tolist()
    )

    eintrag = anzeigen[
        anzeigen["Datum"] == auswahl
    ].iloc[0]

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "Datum",
            eintrag["Datum"]
        )

    with c2:

        st.metric(
            "Gewicht",
            f"{eintrag['Gewicht_kg']:.1f} kg"
        )

    if st.button(
        "❌ Diesen Eintrag löschen",
        use_container_width=True
    ):

        try:

            loesche_supabase_gewicht(
                eintrag["Datum"]
            )

            st.success(
                "Eintrag gelöscht."
            )

            st.rerun()

        except Exception as e:

            st.error(
                f"Fehler: {e}"
            )

with st.container(border=True):

    st.subheader(
        "⚠️ Alle Daten löschen"
    )

    st.warning(
        "Dies löscht ALLE Gewichtsdaten aus Supabase."
    )

    if st.button(
        "🔥 Alle Gewichtsdaten löschen",
        use_container_width=True
    ):

        try:

            loesche_alle_supabase_gewichte()

            st.success(
                "Alle Daten gelöscht."
            )

            st.rerun()

        except Exception as e:

            st.error(
                f"Fehler: {e}"
            )

with st.container(border=True):

    st.subheader(
        "📋 Aktuelle Daten"
    )

    st.dataframe(
        anzeigen,
        use_container_width=True,
        hide_index=True
    )