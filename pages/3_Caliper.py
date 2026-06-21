import streamlit as st
from datetime import date

from utils import (
    lade_einstellungen,
    speichere_einstellungen,
    berechne_kfa,
    lade_tagesdaten,
    speichere_caliper_supabase,
    lade_css,
    zeige_refresh_button
)

st.set_page_config(page_title="Caliper", layout="wide")
lade_css()
zeige_refresh_button()

st.title("📏 Caliper Messung")
st.caption("Speichert KFA, FFM und Fettmasse direkt in Supabase.")

einstellungen = lade_einstellungen()
tagesdaten = lade_tagesdaten()

gewicht_kg = (
    float(tagesdaten["Gewicht_kg"].iloc[-1])
    if not tagesdaten.empty
    else float(einstellungen["gewicht"])
)

for key, value in {
    "alter": int(einstellungen["alter"]),
    "brust": float(einstellungen["brust"]),
    "bauch": float(einstellungen["bauch"]),
    "oberschenkel": float(einstellungen["oberschenkel"])
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

with st.container(border=True):
    st.subheader("📝 Eingabe")

    st.metric("Gewicht", f"{gewicht_kg:.1f} kg")

    r1c1, r1c2 = st.columns(2)
    with r1c1:
        alter = st.number_input("Alter", min_value=10, max_value=100, key="alter")
    with r1c2:
        brust = st.number_input("Brustfalte mm", min_value=1.0, max_value=80.0, step=0.5, key="brust")

    r2c1, r2c2 = st.columns(2)
    with r2c1:
        bauch = st.number_input("Bauchfalte mm", min_value=1.0, max_value=80.0, step=0.5, key="bauch")
    with r2c2:
        oberschenkel = st.number_input("Oberschenkel mm", min_value=1.0, max_value=80.0, step=0.5, key="oberschenkel")

kfa_daten = berechne_kfa(
    gewicht_kg,
    alter,
    brust,
    bauch,
    oberschenkel
)

with st.container(border=True):
    st.subheader("📊 Ergebnis")

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("KFA", f"{kfa_daten['kfa']}%")
    m2.metric("FFM", f"{kfa_daten['ffm']} kg")
    m3.metric("Fettmasse", f"{kfa_daten['fettmasse']} kg")
    m4.metric("Faltensumme", f"{kfa_daten['falten_summe']:.1f} mm")

if st.button("💾 Caliper speichern", use_container_width=True):
    heute = date.today().strftime("%Y-%m-%d")

    try:
        speichere_caliper_supabase(
            heute,
            gewicht_kg,
            alter,
            brust,
            bauch,
            oberschenkel,
            kfa_daten["falten_summe"],
            kfa_daten["kfa"],
            kfa_daten["ffm"],
            kfa_daten["fettmasse"]
        )

        speichere_einstellungen(
            gewicht_kg,
            einstellungen["ziel"],
            einstellungen["faktor"],
            alter,
            brust,
            bauch,
            oberschenkel
        )

        st.success("Caliper-Daten in Supabase gespeichert!")

    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")