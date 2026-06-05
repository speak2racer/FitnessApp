import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils import (
    lade_einstellungen,
    lade_nutrition_logs,
    lade_activity_logs,
    berechne_makros,
    lade_tagesdaten,
    lade_caliper_daten,
    lade_css,
    zeige_refresh_button
)

st.set_page_config(
    page_title="Fitness Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)
lade_css()
zeige_refresh_button()

st.title("🏠 Fitness Dashboard")
st.caption("Kompakter Überblick über Gewicht, Kalorien, Aktivität, Compliance und TDEE.")

einstellungen = lade_einstellungen()

daten = lade_tagesdaten()
caliper = lade_caliper_daten()
nutrition_logs = lade_nutrition_logs()
activity_logs = lade_activity_logs()

if not daten.empty:
    letzter_sync = daten["Datum"].max().strftime("%d.%m.%Y")

    vorwoche = daten[
        daten["Datum"].dt.to_period("W")
        == (daten["Datum"].max() - pd.Timedelta(weeks=1)).to_period("W")
    ]
    aktuelle_woche_daten = daten[
        daten["Datum"].dt.to_period("W")
        == daten["Datum"].max().to_period("W")
    ]

    if not vorwoche.empty and not aktuelle_woche_daten.empty:
        gewicht_trend = float(aktuelle_woche_daten["Gewicht_kg"].mean()) - float(vorwoche["Gewicht_kg"].mean())
        trend_symbol = "📉" if gewicht_trend < -0.1 else "📈" if gewicht_trend > 0.1 else "➡️"
        st.success(f"✅ Letzter Sync: {letzter_sync}  |  Gewichtstrend: {trend_symbol} {gewicht_trend:+.2f} kg zur Vorwoche")
    else:
        st.success(f"✅ Letztes synchronisiertes Gewicht: {letzter_sync}")
else:
    st.warning("⚠️ Noch keine Supabase-Gewichtsdaten vorhanden.")

if not daten.empty:
    aktuelle_woche = daten[
        daten["Datum"].dt.to_period("W")
        == daten["Datum"].max().to_period("W")
    ]
    gewicht = float(aktuelle_woche["Gewicht_kg"].mean())
else:
    gewicht = float(einstellungen["gewicht"])

ziel = einstellungen["ziel"]
faktor = float(einstellungen["faktor"])

if not caliper.empty:
    kfa = float(caliper["KFA"].iloc[-1])
else:
    kfa = 15.0

makros = berechne_makros(
    gewicht,
    faktor,
    kfa
)

with st.container(border=True):
    st.subheader("⚙️ Aktueller Stand")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Gewicht Ø Woche", f"{gewicht:.2f} kg")
    c2.metric("Ziel", ziel)
    c3.metric("Faktor", f"{faktor:.2f}")
    c4.metric("Kalorienziel", f"{makros['kalorien']} kcal")


with st.container(border=True):
    st.subheader("🔥 Kalorienbilanz heute")

    heute = pd.Timestamp.today().normalize()

    nutrition_heute = (
        nutrition_logs[
            nutrition_logs["Datum"].dt.normalize() == heute
        ]
        if not nutrition_logs.empty
        else pd.DataFrame()
    )

    activity_heute = (
        activity_logs[
            activity_logs["Datum"].dt.normalize() == heute
        ]
        if not activity_logs.empty
        else pd.DataFrame()
    )

    gegessen = (
        float(nutrition_heute["Kalorien_gegessen"].iloc[-1])
        if not nutrition_heute.empty
        else 0
    )

    aktiv = (
        float(activity_heute["Aktivkalorien"].iloc[-1])
        if not activity_heute.empty
        else 0
    )

    gesamtverbrauch = (
        float(activity_heute["Gesamtverbrauch"].iloc[-1])
        if not activity_heute.empty
        else 0
    )

    schritte = (
        int(activity_heute["Schritte"].iloc[-1])
        if not activity_heute.empty
        else 0
    )

    ziel_kalorien = makros["kalorien"]
    differenz_ziel = gegessen - ziel_kalorien
    netto_gesamt = gegessen - gesamtverbrauch

    k1, k2, k3, k4 = st.columns(4)

    k1.metric("Kalorienziel", f"{ziel_kalorien:.0f} kcal")
    k2.metric("Gegessen", f"{gegessen:.0f} kcal", f"{differenz_ziel:+.0f} kcal")
    k3.metric("Gesamtverbrauch", f"{gesamtverbrauch:.0f} kcal")
    k4.metric("Schritte", f"{schritte:,}".replace(",", "."))

    k5, k6 = st.columns(2)

    k5.metric("Aktiv verbrannt", f"{aktiv:.0f} kcal")
    k6.metric("Bilanz vs Verbrauch", f"{netto_gesamt:+.0f} kcal")


with st.container(border=True):
    st.subheader("✅ Compliance gestern")

    gestern = (
        pd.Timestamp.today().date()
        - pd.Timedelta(days=1)
    )

    nutrition_gestern = (
        nutrition_logs[
            nutrition_logs["Datum"].dt.date == gestern
        ]
        if not nutrition_logs.empty
        else pd.DataFrame()
    )

    if nutrition_gestern.empty:
        st.warning(
            f"Keine Nutrition-Daten für gestern ({gestern}) gefunden."
        )
    else:
        letzter_gestern = nutrition_gestern.iloc[-1]

        kalorien_ist = float(letzter_gestern["Kalorien_gegessen"])
        protein_ist = float(letzter_gestern["Protein_gegessen"])
        fett_ist = float(letzter_gestern["Fett_gegessen"])
        carbs_ist = float(letzter_gestern["Carbs_gegessen"])

        kalorien_ziel = makros["kalorien"]
        protein_ziel = makros["eiweiss_g"]
        fett_ziel = makros["fett_g"]
        carbs_ziel = makros["kohlenhydrate_g"]

        def trefferquote(ist, ziel):
            if ziel <= 0:
                return 0

            abweichung = abs(ist - ziel) / ziel

            return round(
                max(0, 100 - abweichung * 100),
                1
            )

        kalorien_score = trefferquote(kalorien_ist, kalorien_ziel)
        protein_score = trefferquote(protein_ist, protein_ziel)
        fett_score = trefferquote(fett_ist, fett_ziel)
        carbs_score = trefferquote(carbs_ist, carbs_ziel)

        compliance_score = round(
            (
                kalorien_score * 0.4
                + protein_score * 0.3
                + fett_score * 0.15
                + carbs_score * 0.15
            ),
            1
        )

        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric("Gesamt", f"{compliance_score:.1f}%")
        c2.metric("Kalorien", f"{kalorien_score:.1f}%", f"{kalorien_ist - kalorien_ziel:+.0f} kcal")
        c3.metric("Protein", f"{protein_score:.1f}%", f"{protein_ist - protein_ziel:+.0f} g")
        c4.metric("Fett", f"{fett_score:.1f}%", f"{fett_ist - fett_ziel:+.0f} g")
        c5.metric("Carbs", f"{carbs_score:.1f}%", f"{carbs_ist - carbs_ziel:+.0f} g")


with st.container(border=True):
    st.subheader("📊 Wochenübersicht Ernährung & Aktivität")

    if not nutrition_logs.empty and not activity_logs.empty:
        nutrition_woche = nutrition_logs.copy()
        activity_woche = activity_logs.copy()

        nutrition_woche["Woche"] = nutrition_woche["Datum"].dt.to_period("W").astype(str)
        activity_woche["Woche"] = activity_woche["Datum"].dt.to_period("W").astype(str)

        nutrition_weekly = (
            nutrition_woche.groupby("Woche")
            .agg({
                "Kalorien_gegessen": "mean",
                "Protein_gegessen": "mean",
                "Carbs_gegessen": "mean",
                "Fett_gegessen": "mean"
            })
            .reset_index()
            .round(0)
        )

        activity_weekly = (
            activity_woche.groupby("Woche")
            .agg({
                "Aktivkalorien": "mean",
                "Gesamtverbrauch": "mean",
                "Schritte": "mean"
            })
            .reset_index()
            .round(0)
        )

        weekly = (
            nutrition_weekly.merge(
                activity_weekly,
                on="Woche",
                how="outer"
            )
            .sort_values("Woche")
        )

        weekly["Bilanz_vs_Verbrauch"] = (
            weekly["Kalorien_gegessen"]
            - weekly["Gesamtverbrauch"]
        )

        weekly["Bilanz_vs_Ziel"] = (
            weekly["Kalorien_gegessen"]
            - makros["kalorien"]
        )

        aktuelle_woche = weekly.iloc[-1]

        w1, w2, w3, w4 = st.columns(4)

        w1.metric(
            "Kalorien Ø Woche",
            f"{aktuelle_woche['Kalorien_gegessen']:.0f} kcal"
        )

        w2.metric(
            "Bilanz vs Verbrauch Ø",
            f"{aktuelle_woche['Bilanz_vs_Verbrauch']:+.0f} kcal"
        )

        w3.metric(
            "Aktivkalorien Ø",
            f"{aktuelle_woche['Aktivkalorien']:.0f} kcal"
        )

        w4.metric(
            "Schritte Ø",
            f"{aktuelle_woche['Schritte']:.0f}"
        )

    else:
        st.info("Noch nicht genug Nutrition- oder Aktivitätsdaten vorhanden.")


with st.container(border=True):
    st.subheader("🧮 Echter TDEE aus Gewichtstrend")

    if not daten.empty and not nutrition_logs.empty:
        gewicht_woche = daten.copy()
        kcal_woche = nutrition_logs.copy()

        gewicht_woche["Woche"] = (
            gewicht_woche["Datum"]
            .dt.to_period("W")
            .astype(str)
        )

        kcal_woche["Woche"] = (
            kcal_woche["Datum"]
            .dt.to_period("W")
            .astype(str)
        )

        gewicht_weekly = (
            gewicht_woche.groupby("Woche")["Gewicht_kg"]
            .mean()
            .reset_index()
            .round(2)
        )

        kcal_weekly = (
            kcal_woche.groupby("Woche")["Kalorien_gegessen"]
            .mean()
            .reset_index()
            .round(0)
        )

        tdee_data = (
            gewicht_weekly.merge(
                kcal_weekly,
                on="Woche",
                how="inner"
            )
            .sort_values("Woche")
        )

        if len(tdee_data) >= 2:
            aktuelle = tdee_data.iloc[-1]
            vorherige = tdee_data.iloc[-2]

            gewicht_delta = (
                aktuelle["Gewicht_kg"]
                - vorherige["Gewicht_kg"]
            )

            kcal_delta_pro_tag = (
                gewicht_delta * 7700
            ) / 7

            echter_tdee = (
                aktuelle["Kalorien_gegessen"]
                - kcal_delta_pro_tag
            )

            t1, t2, t3, t4 = st.columns(4)

            t1.metric(
                "Gewicht Ø aktuelle Woche",
                f"{aktuelle['Gewicht_kg']:.2f} kg"
            )

            t2.metric(
                "Gewicht Ø Vorwoche",
                f"{vorherige['Gewicht_kg']:.2f} kg"
            )

            t3.metric(
                "Trend",
                f"{gewicht_delta:+.2f} kg/Woche"
            )

            t4.metric(
                "Geschätzter TDEE",
                f"{echter_tdee:.0f} kcal"
            )

            st.caption(
                "Berechnet aus Gewichtsänderung und tatsächlicher Kalorienaufnahme."
            )

        else:
            st.info("Für den TDEE brauchst du mindestens zwei Wochen mit Gewicht und Kalorien.")
    else:
        st.info("Noch nicht genug Gewicht- oder Kaloriendaten vorhanden.")


if not nutrition_logs.empty:
    with st.container(border=True):
        st.subheader("🎯 Wochenziel-Fortschritt")

        diese_woche = nutrition_logs[
            nutrition_logs["Datum"].dt.to_period("W")
            == pd.Timestamp.today().to_period("W")
        ]

        if not diese_woche.empty:
            ziel_kcal = makros["kalorien"]
            tage_im_ziel = (
                (diese_woche["Kalorien_gegessen"] >= ziel_kcal * 0.9) &
                (diese_woche["Kalorien_gegessen"] <= ziel_kcal * 1.1)
            ).sum()
            tage_gesamt = len(diese_woche)
            tage_woche = 7

            p1, p2 = st.columns(2)
            p1.metric("Tage im Zielbereich", f"{tage_im_ziel} / {tage_gesamt}")
            p2.metric("Wochenfortschritt", f"{tage_gesamt} / {tage_woche} Tage")

            st.progress(tage_im_ziel / tage_woche, text=f"{tage_im_ziel} von 7 Tagen im Kalorienbereich (±10%)")
        else:
            st.info("Noch keine Ernährungsdaten diese Woche.")

if not caliper.empty:
    with st.container(border=True):
        st.subheader("📊 Körperanalyse")

        letzter = caliper.iloc[-1]

        if len(caliper) >= 2:
            vorher = caliper.iloc[-2]

            kfa_delta = letzter["KFA"] - vorher["KFA"]
            ffm_delta = letzter["FFM"] - vorher["FFM"]
            fett_delta = letzter["Fettmasse"] - vorher["Fettmasse"]
        else:
            kfa_delta = 0
            ffm_delta = 0
            fett_delta = 0

        k1, k2, k3 = st.columns(3)

        k1.metric(
            "KFA",
            f"{letzter['KFA']:.1f}%",
            f"{kfa_delta:+.1f}%"
        )

        k2.metric(
            "FFM",
            f"{letzter['FFM']:.1f} kg",
            f"{ffm_delta:+.1f} kg"
        )

        k3.metric(
            "Fettmasse",
            f"{letzter['Fettmasse']:.1f} kg",
            f"{fett_delta:+.1f} kg"
        )

if not daten.empty:
    with st.container(border=True):
        st.subheader("📈 Gewichtsverlauf")

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=daten["Datum"],
            y=daten["Gewicht_kg"],
            mode="lines+markers",
            name="Gewicht",
            line=dict(color="#4C9BE8", width=2),
            marker=dict(size=4)
        ))

        gewicht_7d = daten.set_index("Datum")["Gewicht_kg"].rolling("7D").mean().reset_index()
        fig.add_trace(go.Scatter(
            x=gewicht_7d["Datum"],
            y=gewicht_7d["Gewicht_kg"],
            mode="lines",
            name="7-Tage Ø",
            line=dict(color="#F4A623", width=2, dash="dash")
        ))

        fig.update_layout(
            height=300,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", y=1.1),
            xaxis_title=None,
            yaxis_title="kg"
        )

        st.plotly_chart(fig, use_container_width=True)

st.caption("Nutze links die Seiten Tagesdaten, Wochenanalyse, Caliper, Datenverwaltung und Zielsteuerung.")