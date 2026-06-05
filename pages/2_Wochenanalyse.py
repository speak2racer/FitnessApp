from datetime import date, timedelta

import streamlit as st
import plotly.graph_objects as go

from utils import (
    lade_tagesdaten,
    lade_caliper_daten,
    lade_nutrition_logs,
    lade_activity_logs,
    lade_nutrition_targets,
    lade_einstellungen,
    faktor_empfehlung,
    lade_css,
    zeige_refresh_button
)

st.set_page_config(page_title="Wochenanalyse", layout="wide")
lade_css()
zeige_refresh_button()

st.title("📈 Wochenanalyse")
st.caption("Analysiere Gewicht, Ernährung, Aktivität und Körperanalyse.")

heute = date.today()
wochenstart = heute - timedelta(days=heute.weekday())

zeitraum = st.selectbox(
    "Zeitraum",
    ["Diese Woche", "Letzte 14 Tage", "Letzte 30 Tage", "Alle Daten"]
)

if zeitraum == "Diese Woche":
    daten = lade_tagesdaten(wochenstart.strftime("%Y-%m-%d"))
elif zeitraum == "Letzte 14 Tage":
    daten = lade_tagesdaten((heute - timedelta(days=14)).strftime("%Y-%m-%d"))
elif zeitraum == "Letzte 30 Tage":
    daten = lade_tagesdaten((heute - timedelta(days=30)).strftime("%Y-%m-%d"))
else:
    daten = lade_tagesdaten()

nutrition_logs = lade_nutrition_logs()
activity_logs = lade_activity_logs()
nutrition_targets = lade_nutrition_targets()
caliper = lade_caliper_daten()

if daten.empty:
    st.info("Noch keine Gewichtsdaten vorhanden.")
    st.stop()

einstellungen = lade_einstellungen()
ziel = einstellungen["ziel"]
faktor = float(einstellungen["faktor"])


def format_datum(df):
    df = df.copy()
    df["Datum_Anzeige"] = df["Datum"].dt.strftime("%d.%m.%Y")
    return df


def chart_karte(df, x, y, titel, farbe, einheit):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df[x],
            y=df[y],
            mode="lines+markers",
            line=dict(color=farbe, width=4),
            marker=dict(size=9, color=farbe),
            fill="tozeroy",
            fillcolor="rgba(59,130,246,0.12)",
            hovertemplate="%{x}<br>%{y:.2f} " + einheit + "<extra></extra>"
        )
    )

    fig.update_layout(
        title=dict(text=titel, font=dict(size=22, color=farbe), x=0.03),
        height=420,
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#111827",
        font=dict(color="#e5e7eb", size=14),
        margin=dict(l=45, r=25, t=65, b=50),
        xaxis=dict(title="", showgrid=False, type="category"),
        yaxis=dict(
            title=einheit,
            showgrid=True,
            gridcolor="#334155",
            zeroline=False
        )
    )

    return fig


with st.container(border=True):
    st.subheader("📊 Wochenmittel Gewicht")

    wochen = daten.copy()
    wochen["Woche"] = wochen["Datum"].dt.to_period("W").astype(str)

    wochenmittel = (
        wochen.groupby("Woche")
        .agg({"Gewicht_kg": "mean"})
        .reset_index()
        .round(2)
    )

    st.dataframe(
        wochenmittel,
        use_container_width=True,
        hide_index=True
    )


if len(wochenmittel) >= 2:
    aktuelles_gewicht = wochenmittel["Gewicht_kg"].iloc[-1]
    vorheriges_gewicht = wochenmittel["Gewicht_kg"].iloc[-2]
    veraenderung_kg = aktuelles_gewicht - vorheriges_gewicht
    veraenderung_lbs = veraenderung_kg * 2.20462

    empfohlener_faktor = faktor_empfehlung(
        ziel,
        veraenderung_lbs,
        faktor
    )

    with st.container(border=True):
        st.subheader("⚖️ Wochentrend")

        t1, t2, t3, t4 = st.columns(4)

        t1.metric("Diese Woche Ø", f"{aktuelles_gewicht:.2f} kg")
        t2.metric("Vorwoche Ø", f"{vorheriges_gewicht:.2f} kg")
        t3.metric("Veränderung", f"{veraenderung_kg:+.2f} kg")
        t4.metric("Veränderung lbs", f"{veraenderung_lbs:+.2f} lbs")
else:
    st.info("Für den Wochentrend brauchst du mindestens zwei Wochen Daten.")


with st.container(border=True):
    st.subheader("🔥 Ernährung & Aktivität pro Woche")

    if (
        not nutrition_logs.empty
        and not activity_logs.empty
        and not nutrition_targets.empty
    ):
        nutrition = nutrition_logs.copy()
        activity = activity_logs.copy()
        targets = nutrition_targets.copy()

        nutrition["Woche"] = nutrition["Datum"].dt.to_period("W").astype(str)
        activity["Woche"] = activity["Datum"].dt.to_period("W").astype(str)
        targets["Woche"] = targets["Datum"].dt.to_period("W").astype(str)

        nutrition_weekly = (
            nutrition.groupby("Woche")
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
            activity.groupby("Woche")
            .agg({
                "Aktivkalorien": "mean",
                "Gesamtverbrauch": "mean",
                "Schritte": "mean"
            })
            .reset_index()
            .round(0)
        )

        targets_weekly = (
            targets.groupby("Woche")
            .agg({
                "Kalorienziel": "mean",
                "Eiweiss_g": "mean",
                "Fett_g": "mean",
                "Kohlenhydrate_g": "mean",
                "Faktor": "mean"
            })
            .reset_index()
            .round(0)
        )

        weekly_full = (
            wochenmittel
            .merge(targets_weekly, on="Woche", how="outer")
            .merge(nutrition_weekly, on="Woche", how="outer")
            .merge(activity_weekly, on="Woche", how="outer")
            .sort_values("Woche")
        )

        weekly_full["Bilanz_vs_Verbrauch"] = (
            weekly_full["Kalorien_gegessen"]
            - weekly_full["Gesamtverbrauch"]
        )

        weekly_full["Bilanz_vs_Ziel"] = (
            weekly_full["Kalorien_gegessen"]
            - weekly_full["Kalorienziel"]
        )

        weekly_full["Kalorien_Compliance"] = (
            100
            - (
                abs(
                    weekly_full["Kalorien_gegessen"]
                    - weekly_full["Kalorienziel"]
                )
                / weekly_full["Kalorienziel"]
                * 100
            )
        ).clip(lower=0)

        weekly_full["Protein_Compliance"] = (
            100
            - (
                abs(
                    weekly_full["Protein_gegessen"]
                    - weekly_full["Eiweiss_g"]
                )
                / weekly_full["Eiweiss_g"]
                * 100
            )
        ).clip(lower=0)

        weekly_full["Compliance"] = (
            weekly_full["Kalorien_Compliance"] * 0.6
            + weekly_full["Protein_Compliance"] * 0.4
        ).round(1)

        aktuell = weekly_full.iloc[-1]

        s1, s2, s3, s4, s5 = st.columns(5)

        s1.metric("Gewicht Ø", f"{aktuell['Gewicht_kg']:.2f} kg")
        s2.metric("Kalorien Ø", f"{aktuell['Kalorien_gegessen']:.0f} kcal")
        s3.metric("Protein Ø", f"{aktuell['Protein_gegessen']:.0f} g")
        s4.metric("Schritte Ø", f"{aktuell['Schritte']:.0f}")
        s5.metric("Compliance", f"{aktuell['Compliance']:.1f}%")

        k1, k2, k3, k4 = st.columns(4)

        k1.metric("Ziel Ø", f"{aktuell['Kalorienziel']:.0f} kcal")
        k2.metric("Verbrauch Ø", f"{aktuell['Gesamtverbrauch']:.0f} kcal")
        k3.metric("Bilanz vs Ziel", f"{aktuell['Bilanz_vs_Ziel']:+.0f} kcal")
        k4.metric(
            "Bilanz vs Verbrauch",
            f"{aktuell['Bilanz_vs_Verbrauch']:+.0f} kcal"
        )

        if aktuell["Bilanz_vs_Verbrauch"] < -300:
            st.success("Du befindest dich aktuell in einem deutlichen Kaloriendefizit.")
        elif aktuell["Bilanz_vs_Verbrauch"] > 300:
            st.warning("Du befindest dich aktuell in einem deutlichen Kalorienüberschuss.")
        else:
            st.info("Du befindest dich aktuell ungefähr auf Erhaltung.")

        st.dataframe(
            weekly_full.tail(8),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info(
            "Noch nicht genug Nutrition-, Activity- oder Ziel-Daten vorhanden."
        )


with st.container(border=True):
    st.subheader("📉 Körperanalyse Dashboard")

    daten_plot = format_datum(daten)

    fig_gewicht = chart_karte(
        daten_plot,
        "Datum_Anzeige",
        "Gewicht_kg",
        "Gewicht",
        "#3b82f6",
        "kg"
    )

    if not caliper.empty:
        caliper_plot = format_datum(caliper)

        fig_kfa = chart_karte(
            caliper_plot,
            "Datum_Anzeige",
            "KFA",
            "Körperfett",
            "#ef4444",
            "%"
        )

        fig_ffm = chart_karte(
            caliper_plot,
            "Datum_Anzeige",
            "FFM",
            "Fettfreie Masse",
            "#22c55e",
            "kg"
        )

        fig_fettmasse = chart_karte(
            caliper_plot,
            "Datum_Anzeige",
            "Fettmasse",
            "Fettmasse",
            "#f97316",
            "kg"
        )

        c1, c2 = st.columns(2)

        with c1:
            st.plotly_chart(fig_gewicht, use_container_width=True)

        with c2:
            st.plotly_chart(fig_kfa, use_container_width=True)

        c3, c4 = st.columns(2)

        with c3:
            st.plotly_chart(fig_ffm, use_container_width=True)

        with c4:
            st.plotly_chart(fig_fettmasse, use_container_width=True)

    else:
        st.plotly_chart(fig_gewicht, use_container_width=True)
        st.info("Noch keine Caliper-Daten vorhanden.")