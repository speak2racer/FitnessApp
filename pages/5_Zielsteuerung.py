import streamlit as st
import pandas as pd

from datetime import date

from utils import (
    lade_einstellungen,
    speichere_einstellungen,
    lade_tagesdaten,
    lade_caliper_daten,
    lade_nutrition_logs,
    berechne_makros,
    speichere_nutrition_target,
    lade_css,
    zeige_refresh_button,
    STANDARD_FAKTOR
)

st.set_page_config(page_title="Zielsteuerung", layout="wide")
lade_css()
zeige_refresh_button()

st.title("🎯 Zielsteuerung")
st.caption("Passe Ziel, Faktor und TDEE-basierte Empfehlungen zentral an.")

einstellungen = lade_einstellungen()
daten = lade_tagesdaten()
nutrition_logs = lade_nutrition_logs()

if not daten.empty:
    aktuelle_woche = daten[
        daten["Datum"].dt.to_period("W")
        == daten["Datum"].max().to_period("W")
    ]
    gewicht = float(aktuelle_woche["Gewicht_kg"].mean())
else:
    gewicht = float(einstellungen["gewicht"])


if "ziel" not in st.session_state:
    st.session_state.ziel = einstellungen["ziel"]

if "faktor" not in st.session_state:
    st.session_state.faktor = float(einstellungen["faktor"])


def ziel_geaendert():
    st.session_state.faktor = float(
        STANDARD_FAKTOR[st.session_state.ziel]
    )


with st.container(border=True):
    st.subheader("⚙️ Einstellung")

    c1, c2 = st.columns(2)

    with c1:
        ziel = st.selectbox(
            "Ziel",
            ["Diät", "Erhalt", "Aufbau"],
            key="ziel",
            on_change=ziel_geaendert
        )

    with c2:
        faktor = st.number_input(
            "Kalorien-Faktor",
            min_value=8.0,
            max_value=25.0,
            step=0.25,
            key="faktor"
        )

gewicht_lbs = gewicht * 2.20462
kalorien = round(gewicht_lbs * faktor)

with st.container(border=True):
    st.subheader("📊 Aktuelles Ziel")

    z1, z2, z3, z4 = st.columns(4)

    z1.metric("Gewicht Ø Woche", f"{gewicht:.2f} kg")
    z2.metric("Ziel", ziel)
    z3.metric("Faktor", f"{faktor:.2f}")
    z4.metric("Kalorienziel", f"{kalorien} kcal")


with st.container(border=True):
    st.subheader("🧮 Empfehlung aus echtem TDEE")

    if not daten.empty and not nutrition_logs.empty:
        heute_norm = pd.Timestamp.today().normalize()

        gewicht_woche = daten[daten["Datum"].dt.normalize() < heute_norm].copy()
        kcal_woche = nutrition_logs[
            (nutrition_logs["Datum"].dt.normalize() < heute_norm) &
            (nutrition_logs["Kalorien_gegessen"] > 0)
        ].copy()

        gewicht_woche["Woche"] = gewicht_woche["Datum"].dt.to_period("W").astype(str)
        kcal_woche["Woche"] = kcal_woche["Datum"].dt.to_period("W").astype(str)

        gewicht_weekly = (
            gewicht_woche.groupby("Woche")["Gewicht_kg"]
            .mean()
            .reset_index()
            .round(2)
        )

        # Nur Wochen mit mindestens 5 Tagen Kaloriendaten
        kcal_counts = kcal_woche.groupby("Woche")["Kalorien_gegessen"].count()
        kcal_weekly = (
            kcal_woche.groupby("Woche")["Kalorien_gegessen"]
            .mean()
            .reset_index()
            .round(0)
        )
        kcal_weekly = kcal_weekly[kcal_weekly["Woche"].isin(
            kcal_counts[kcal_counts >= 5].index
        )]

        tdee_data = (
            gewicht_weekly.merge(kcal_weekly, on="Woche", how="inner")
            .sort_values("Woche")
        )

        tdee_data["Periode"] = tdee_data["Woche"].apply(lambda w: pd.Period(w, freq="W"))
        tdee_data = tdee_data.sort_values("Woche").reset_index(drop=True)

        paar = None
        for i in range(len(tdee_data) - 1, 0, -1):
            if (tdee_data.loc[i, "Periode"] - tdee_data.loc[i-1, "Periode"]) == 1:
                paar = (tdee_data.iloc[i-1], tdee_data.iloc[i])
                break

        if paar:
            vorherige, aktuelle = paar

            gewicht_delta = aktuelle["Gewicht_kg"] - vorherige["Gewicht_kg"]
            kcal_delta_pro_tag = (gewicht_delta * 7700) / 7
            echter_tdee = aktuelle["Kalorien_gegessen"] - kcal_delta_pro_tag

            gewicht_lbs_tdee = aktuelle["Gewicht_kg"] * 2.20462
            erhalt_faktor = echter_tdee / gewicht_lbs_tdee

            diaet_faktor = erhalt_faktor - 2
            aufbau_faktor = erhalt_faktor + 1

            e1, e2, e3, e4 = st.columns(4)

            e1.metric("Echter TDEE", f"{echter_tdee:.0f} kcal")
            e2.metric("Erhalt-Faktor", f"{erhalt_faktor:.2f}")
            e3.metric("Diät-Faktor", f"{diaet_faktor:.2f}")
            e4.metric("Aufbau-Faktor", f"{aufbau_faktor:.2f}")

            if ziel == "Diät":
                empfohlener_faktor = diaet_faktor
            elif ziel == "Aufbau":
                empfohlener_faktor = aufbau_faktor
            else:
                empfohlener_faktor = erhalt_faktor

            st.info(
                f"Für dein aktuelles Ziel **{ziel}** wäre der empfohlene Faktor "
                f"**{empfohlener_faktor:.2f}**."
            )

            if st.button(
                "Empfohlenen Faktor übernehmen",
                use_container_width=True
            ):
                st.session_state.faktor = round(empfohlener_faktor, 2)

                speichere_einstellungen(
                    gewicht,
                    ziel,
                    round(empfohlener_faktor, 2),
                    einstellungen["carb_anteil"]
                )

                st.success(
                    f"Empfohlener Faktor gespeichert: {empfohlener_faktor:.2f}"
                )

                st.rerun()

        else:
            st.info("Keine zwei aufeinanderfolgenden vollständigen Wochen gefunden.")
    else:
        st.info("Noch nicht genug Gewicht- oder Kaloriendaten vorhanden.")


if st.button("💾 Ziel speichern", use_container_width=True):
    try:
        speichere_einstellungen(
            gewicht,
            ziel,
            faktor,
            einstellungen["carb_anteil"]
        )

        caliper = lade_caliper_daten()
        kfa = float(caliper["KFA"].iloc[-1]) if not caliper.empty else 15.0
        makros = berechne_makros(gewicht, faktor, kfa)

        speichere_nutrition_target(
            date.today().strftime("%Y-%m-%d"),
            makros["kalorien"],
            makros["eiweiss_g"],
            makros["fett_g"],
            makros["kohlenhydrate_g"],
            faktor,
            makros["carb_anteil"]
        )

        st.cache_data.clear()
        st.success("Zielsteuerung gespeichert und Supabase aktualisiert.")

    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")

    st.rerun()