import streamlit as st
from datetime import date

from utils import (
    lade_einstellungen,
    speichere_einstellungen,
    berechne_makros,
    lade_tagesdaten,
    lade_caliper_daten,
    speichere_nutrition_target,
    zeige_refresh_button,
)

zeige_refresh_button()

st.title(":material/today: Tagesdaten")
st.caption(
    "Tagesziel und Mahlzeiten werden automatisch mit dem Gewichtsdurchschnitt der aktuellen Woche berechnet und gespeichert."
)

einstellungen = lade_einstellungen()
tagesdaten = lade_tagesdaten()
caliper = lade_caliper_daten()

if not tagesdaten.empty:
    aktuelle_woche = tagesdaten[
        tagesdaten["Datum"].dt.to_period("W") == tagesdaten["Datum"].max().to_period("W")
    ]
    gewicht_kg = float(aktuelle_woche["Gewicht_kg"].mean())
else:
    gewicht_kg = float(einstellungen["gewicht"])

kfa = float(caliper["KFA"].iloc[-1]) if not caliper.empty else 15.0
ziel = einstellungen["ziel"]
faktor = float(einstellungen["faktor"])
makros = berechne_makros(gewicht_kg, faktor, kfa)

with st.container(border=True):
    st.subheader(":material/info: Grundlage")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gewicht Ø aktuelle Woche", f"{gewicht_kg:.1f} kg")
    c2.metric("KFA", f"{kfa:.1f}%")
    c3.metric("Ziel", ziel)
    c4.metric("Kalorien-Faktor", f"{faktor:.2f}")

with st.container(border=True):
    st.subheader(":material/track_changes: Tagesziel")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Kalorien", f"{makros['kalorien']} kcal")
    m2.metric("Eiweiß", f"{makros['eiweiss_g']} g")
    m3.metric("Fett", f"{makros['fett_g']} g")
    m4.metric("Carbs", f"{makros['kohlenhydrate_g']} g")

with st.container(border=True):
    st.subheader(":material/restaurant: Mahlzeiten")

    protein = round(makros["eiweiss_g"] / 6)
    fett = round(makros["fett_g"] / 3)
    carbs_training = round(makros["kohlenhydrate_g"] * 0.40)
    carbs_abend = round(makros["kohlenhydrate_g"] * 0.40)
    carbs_snack = makros["kohlenhydrate_g"] - carbs_training - carbs_abend

    rows = ""
    for name, p, f, c in [
        ("Frühstück",  protein, fett, 0),
        ("Mittagessen", protein, fett, 0),
        ("Snack",       protein, fett, 0),
        ("Training",    protein, 0,    carbs_training),
        ("Abendessen",  protein, 0,    carbs_abend),
        ("Abend-Snack", protein, 0,    carbs_snack),
    ]:
        rows += f"""
        <tr>
            <td>{name}</td>
            <td>{p}</td>
            <td>{f}</td>
            <td>{c}</td>
        </tr>
        """

    st.markdown(
        f"""
        <table class="meal-table">
            <thead>
                <tr>
                    <th>Mahlzeit</th>
                    <th>Protein (g)</th>
                    <th>Fett (g)</th>
                    <th>Carbs (g)</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True
    )

heute = date.today().strftime("%Y-%m-%d")

try:
    speichere_einstellungen(gewicht_kg, ziel, faktor)
    speichere_nutrition_target(
        heute,
        makros["kalorien"],
        makros["eiweiss_g"],
        makros["fett_g"],
        makros["kohlenhydrate_g"],
        faktor,
    )
    st.success("Tagesziel wurde automatisch in Supabase gespeichert.")
except Exception as e:
    st.error(f"Fehler beim automatischen Speichern: {e}")
