import streamlit as st
import pandas as pd

from utils import (
    lade_tagesdaten,
    aktualisiere_supabase_gewicht,
    loesche_supabase_gewicht,
    loesche_alle_supabase_gewichte,
    lade_css,
    zeige_refresh_button
)

st.set_page_config(page_title="Datenverwaltung", layout="wide")
lade_css()
zeige_refresh_button()

st.title("🗃️ Datenverwaltung")
st.caption("Gewichtsdaten aus Supabase anzeigen, bearbeiten und löschen.")

daten = lade_tagesdaten()

if daten.empty:
    st.warning("Keine Gewichtsdaten vorhanden.")
    st.stop()

daten = daten.sort_values("Datum", ascending=False)
anzeigen = daten.copy()
anzeigen["Datum"] = anzeigen["Datum"].dt.strftime("%Y-%m-%d")

with st.container(border=True):
    st.subheader("✏️ Eintrag bearbeiten")

    auswahl = st.selectbox("Eintrag auswählen", anzeigen["Datum"].tolist())

    eintrag = anzeigen[anzeigen["Datum"] == auswahl].iloc[0]

    c1, c2 = st.columns(2)

    with c1:
        st.metric("Datum", eintrag["Datum"])

    with c2:
        neues_gewicht = st.number_input(
            "Gewicht (kg)",
            min_value=30.0,
            max_value=300.0,
            value=float(eintrag["Gewicht_kg"]),
            step=0.1,
            format="%.2f"
        )

    b1, b2 = st.columns(2)

    with b1:
        if st.button("💾 Gewicht speichern", use_container_width=True):
            try:
                aktualisiere_supabase_gewicht(eintrag["Datum"], neues_gewicht)
                st.cache_data.clear()
                st.success(f"Gewicht für {eintrag['Datum']} auf {neues_gewicht:.2f} kg aktualisiert.")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler: {e}")

    with b2:
        if st.button("❌ Eintrag löschen", use_container_width=True):
            try:
                loesche_supabase_gewicht(eintrag["Datum"])
                st.cache_data.clear()
                st.success("Eintrag gelöscht.")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler: {e}")


with st.container(border=True):
    st.subheader("📋 Alle Einträge")

    st.dataframe(
        anzeigen[["Datum", "Gewicht_kg"]].rename(columns={"Gewicht_kg": "Gewicht (kg)"}),
        use_container_width=True,
        hide_index=True
    )


with st.container(border=True):
    st.subheader("⚠️ Alle Daten löschen")
    st.warning("Dies löscht ALLE Gewichtsdaten aus Supabase unwiderruflich.")

    if st.button("🔥 Alle Gewichtsdaten löschen", use_container_width=True):
        try:
            loesche_alle_supabase_gewichte()
            st.cache_data.clear()
            st.success("Alle Daten gelöscht.")
            st.rerun()
        except Exception as e:
            st.error(f"Fehler: {e}")
