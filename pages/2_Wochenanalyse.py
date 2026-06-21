from datetime import date, timedelta

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils import (
    lade_tagesdaten,
    lade_caliper_daten,
    lade_nutrition_logs,
    lade_activity_logs,
    lade_nutrition_targets,
    lade_einstellungen,
    faktor_empfehlung,
    zeige_refresh_button,
)

zeige_refresh_button()

st.title(":material/bar_chart: Wochenanalyse")
st.caption("Analysiere Gewicht, Ernährung, Aktivität und Körperanalyse.")

heute = date.today()
wochenstart = heute - timedelta(days=heute.weekday())

zeitraum = st.selectbox(
    "Zeitraum",
    ["Diese Woche", "Letzte 14 Tage", "Letzte 30 Tage", "Alle Daten"]
)

if zeitraum == "Diese Woche":
    ab_datum = wochenstart.strftime("%Y-%m-%d")
elif zeitraum == "Letzte 14 Tage":
    ab_datum = (heute - timedelta(days=14)).strftime("%Y-%m-%d")
elif zeitraum == "Letzte 30 Tage":
    ab_datum = (heute - timedelta(days=30)).strftime("%Y-%m-%d")
else:
    ab_datum = None

daten = lade_tagesdaten(ab_datum)
nutrition_logs = lade_nutrition_logs(ab_datum)
activity_logs = lade_activity_logs(ab_datum)
nutrition_targets = lade_nutrition_targets(ab_datum)
caliper = lade_caliper_daten()

if daten.empty:
    st.info("Noch keine Gewichtsdaten vorhanden.")
    st.stop()

einstellungen = lade_einstellungen()
ziel = einstellungen["ziel"]
faktor = float(einstellungen["faktor"])


def _hex_to_rgba(hex_color, alpha=0.12):
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"
    except Exception:
        return "rgba(76,155,232,0.12)"


LAYOUT_BASE = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94a3b8", size=12),
    margin=dict(l=50, r=15, t=50, b=40),
    height=290,
)

XAXIS_STYLE = dict(showgrid=False, tickformat="%d.%m", tickangle=-30, color="#64748b")
YAXIS_STYLE = dict(showgrid=True, gridcolor="#1e293b", zeroline=False, color="#64748b")


def chart_linie(df, x_col, y_col, titel, farbe, einheit, zeige_rolling=False):
    werte = df[y_col].dropna()
    if werte.empty:
        return go.Figure()

    y_min = werte.min() * 0.97
    y_max = werte.max() * 1.03
    fill_rgba = _hex_to_rgba(farbe, 0.13)

    fig = go.Figure()

    # unsichtbare Baseline für Flächenfüllung
    fig.add_trace(go.Scatter(
        x=df[x_col], y=[y_min] * len(df),
        mode="lines", line=dict(width=0),
        showlegend=False, hoverinfo="skip"
    ))

    fig.add_trace(go.Scatter(
        x=df[x_col], y=df[y_col],
        mode="lines+markers",
        line=dict(color=farbe, width=2.5),
        marker=dict(size=6, color=farbe, line=dict(width=1.5, color="#0f172a")),
        fill="tonexty", fillcolor=fill_rgba,
        name=titel,
        hovertemplate="%{x|%d.%m.%Y}<br><b>%{y:.1f} " + einheit + "</b><extra></extra>"
    ))

    if zeige_rolling and len(df) >= 7:
        rolling = df.set_index(x_col)[y_col].rolling(7, min_periods=3).mean().reset_index()
        fig.add_trace(go.Scatter(
            x=rolling[x_col], y=rolling[y_col],
            mode="lines", name="7-Tage Ø",
            line=dict(color="#f59e0b", width=2, dash="dot"),
            hovertemplate="%{x|%d.%m.%Y}<br><b>Ø %{y:.1f} " + einheit + "</b><extra></extra>"
        ))

    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text=titel, font=dict(size=15, color=farbe), x=0.01),
        showlegend=zeige_rolling,
        legend=dict(orientation="h", y=1.18, x=0, font=dict(size=11)),
        xaxis=XAXIS_STYLE,
        yaxis=dict(**YAXIS_STYLE, title=einheit, range=[y_min, y_max])
    )
    return fig


wochen = daten.copy()
wochen["Woche"] = wochen["Datum"].dt.to_period("W").astype(str)
wochenmittel = (
    wochen.groupby("Woche").agg({"Gewicht_kg": "mean"}).reset_index().round(2)
)

tab_uebersicht, tab_charts = st.tabs([":material/assignment: Übersicht", ":material/show_chart: Charts"])

# ══════════════════════════════════════════════════════════════════════════════
with tab_uebersicht:
    with st.container(border=True):
        st.subheader("📊 Wochenmittel Gewicht")
        st.dataframe(wochenmittel, use_container_width=True, hide_index=True)

if len(wochenmittel) >= 2:
    aktuelles_gewicht = wochenmittel["Gewicht_kg"].iloc[-1]
    vorheriges_gewicht = wochenmittel["Gewicht_kg"].iloc[-2]
    veraenderung_kg = aktuelles_gewicht - vorheriges_gewicht
    veraenderung_lbs = veraenderung_kg * 2.20462

    empfohlener_faktor = faktor_empfehlung(ziel, veraenderung_lbs, faktor)

    with tab_uebersicht:
        with st.container(border=True):
            st.subheader("⚖️ Wochentrend")
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("Diese Woche Ø", f"{aktuelles_gewicht:.2f} kg")
            t2.metric("Vorwoche Ø", f"{vorheriges_gewicht:.2f} kg")
            t3.metric("Veränderung", f"{veraenderung_kg:+.2f} kg")
            t4.metric("Veränderung lbs", f"{veraenderung_lbs:+.2f} lbs")
else:
    with tab_uebersicht:
        st.info("Für den Wochentrend brauchst du mindestens zwei Wochen Daten.")

with tab_uebersicht:
    with st.container(border=True):
        st.subheader("🔥 Ernährung & Aktivität pro Woche")

    if (
        not nutrition_logs.empty
        and not activity_logs.empty
        and not nutrition_targets.empty
    ):
        heute_norm = pd.Timestamp.today().normalize()
        nutrition = nutrition_logs[nutrition_logs["Datum"].dt.normalize() < heute_norm].copy()
        activity = activity_logs[
            (activity_logs["Datum"].dt.normalize() < heute_norm) &
            (activity_logs["Gesamtverbrauch"] > 0)
        ].copy()
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
            weekly_full["Kalorien_gegessen"] - weekly_full["Gesamtverbrauch"]
        )
        weekly_full["Bilanz_vs_Ziel"] = (
            weekly_full["Kalorien_gegessen"] - weekly_full["Kalorienziel"]
        )
        weekly_full["Kalorien_Compliance"] = (
            100 - (abs(weekly_full["Kalorien_gegessen"] - weekly_full["Kalorienziel"])
                   / weekly_full["Kalorienziel"] * 100)
        ).clip(lower=0)
        weekly_full["Protein_Compliance"] = (
            100 - (abs(weekly_full["Protein_gegessen"] - weekly_full["Eiweiss_g"])
                   / weekly_full["Eiweiss_g"] * 100)
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
        k4.metric("Bilanz vs Verbrauch", f"{aktuell['Bilanz_vs_Verbrauch']:+.0f} kcal")

        if aktuell["Bilanz_vs_Verbrauch"] < -300:
            st.success("Du befindest dich aktuell in einem deutlichen Kaloriendefizit.")
        elif aktuell["Bilanz_vs_Verbrauch"] > 300:
            st.warning("Du befindest dich aktuell in einem deutlichen Kalorienüberschuss.")
        else:
            st.info("Du befindest dich aktuell ungefähr auf Erhaltung.")

        st.dataframe(weekly_full.tail(8), use_container_width=True, hide_index=True)

    else:
        st.info("Noch nicht genug Nutrition-, Activity- oder Ziel-Daten vorhanden.")

# ══════════════════════════════════════════════════════════════════════════════
with tab_charts:

    heute_norm = pd.Timestamp.today().normalize()

    # ── Körperanalyse ────────────────────────────────────────────────────────
    st.markdown("### 🏋️ Körperanalyse")

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(
            chart_linie(daten, "Datum", "Gewicht_kg", "Gewicht", "#3b82f6", "kg", zeige_rolling=True),
            use_container_width=True
        )

    if not caliper.empty:
        with c2:
            st.plotly_chart(
                chart_linie(caliper, "Datum", "KFA", "Körperfett", "#ef4444", "%"),
                use_container_width=True
            )
        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(
                chart_linie(caliper, "Datum", "FFM", "Fettfreie Masse", "#22c55e", "kg"),
                use_container_width=True
            )
        with c4:
            st.plotly_chart(
                chart_linie(caliper, "Datum", "Fettmasse", "Fettmasse", "#f97316", "kg"),
                use_container_width=True
            )
    else:
        st.info("Noch keine Caliper-Daten vorhanden.")

    # ── Ernährung ────────────────────────────────────────────────────────────
    if not nutrition_logs.empty:
        nutr = nutrition_logs[nutrition_logs["Datum"].dt.normalize() < heute_norm].copy()

        if not nutr.empty:
            st.markdown("### 🍽️ Ernährung")

            # Makros täglich — gestapeltes Balkendiagramm
            nutr["Tag"] = nutr["Datum"].dt.normalize()
            makro_daily = nutr.groupby("Tag").agg({
                "Protein_gegessen": "sum",
                "Fett_gegessen": "sum",
                "Carbs_gegessen": "sum"
            }).reset_index().rename(columns={"Tag": "Datum"})

            fig_makro = go.Figure()
            fig_makro.add_trace(go.Bar(
                x=makro_daily["Datum"], y=makro_daily["Protein_gegessen"],
                name="Protein", marker_color="#22c55e",
                hovertemplate="%{x|%d.%m.%Y}<br>Protein: <b>%{y:.0f} g</b><extra></extra>"
            ))
            fig_makro.add_trace(go.Bar(
                x=makro_daily["Datum"], y=makro_daily["Fett_gegessen"],
                name="Fett", marker_color="#f97316",
                hovertemplate="%{x|%d.%m.%Y}<br>Fett: <b>%{y:.0f} g</b><extra></extra>"
            ))
            fig_makro.add_trace(go.Bar(
                x=makro_daily["Datum"], y=makro_daily["Carbs_gegessen"],
                name="Carbs", marker_color="#a855f7",
                hovertemplate="%{x|%d.%m.%Y}<br>Carbs: <b>%{y:.0f} g</b><extra></extra>"
            ))
            fig_makro.update_layout(
                **LAYOUT_BASE,
                barmode="stack",
                title=dict(text="Makros täglich", font=dict(size=15, color="#e5e7eb"), x=0.01),
                legend=dict(orientation="h", y=1.18, x=0, font=dict(size=11)),
                xaxis=XAXIS_STYLE,
                yaxis=dict(**YAXIS_STYLE, title="g")
            )
            st.plotly_chart(fig_makro, use_container_width=True)

    # ── Kalorienbilanz ───────────────────────────────────────────────────────
    if not nutrition_logs.empty and not activity_logs.empty:
        nutr_b = nutrition_logs[nutrition_logs["Datum"].dt.normalize() < heute_norm].copy()
        act_b = activity_logs[
            (activity_logs["Datum"].dt.normalize() < heute_norm) &
            (activity_logs["Gesamtverbrauch"] > 0)
        ].copy()

        if not nutr_b.empty and not act_b.empty:
            nutr_b["Tag"] = nutr_b["Datum"].dt.normalize()
            act_b["Tag"] = act_b["Datum"].dt.normalize()

            nd = nutr_b.groupby("Tag")["Kalorien_gegessen"].sum().reset_index()
            ad = act_b.groupby("Tag")["Gesamtverbrauch"].mean().reset_index()
            bilanz_df = nd.merge(ad, on="Tag", how="inner")
            bilanz_df["Bilanz_Verbrauch"] = bilanz_df["Kalorien_gegessen"] - bilanz_df["Gesamtverbrauch"]
            bilanz_df = bilanz_df.rename(columns={"Tag": "Datum"})

            if not nutrition_targets.empty:
                tgt_b = nutrition_targets.copy()
                tgt_b["Tag"] = tgt_b["Datum"].dt.normalize()
                tgt_d = tgt_b.groupby("Tag")["Kalorienziel"].mean().reset_index().rename(columns={"Tag": "Datum"})
                bilanz_df = bilanz_df.merge(tgt_d, on="Datum", how="left")
                bilanz_df["Bilanz_Ziel"] = bilanz_df["Kalorien_gegessen"] - bilanz_df["Kalorienziel"]

            if not bilanz_df.empty:
                st.markdown("### ⚖️ Kalorienbilanz")

                TOLERANZ = 0.10  # ±10 % = grün (nur für Ziel-Chart)

                def bilanz_bar(df, col, titel, mit_toleranz=False, referenz_col=None):
                    if mit_toleranz and referenz_col and referenz_col in df.columns:
                        farben = [
                            "#22c55e" if (not pd.isna(r) and r != 0 and abs(b) / abs(r) <= TOLERANZ) else "#ef4444"
                            for b, r in zip(df[col], df[referenz_col])
                        ]
                        tol_val = (df[referenz_col] * TOLERANZ).mean()
                    else:
                        farben = ["#22c55e" if v <= 0 else "#ef4444" for v in df[col]]
                        tol_val = None

                    y_abs = df[col].abs().max() * 1.15
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=df["Datum"], y=df[col],
                        marker_color=farben,
                        hovertemplate="%{x|%d.%m.%Y}<br><b>%{y:+.0f} kcal</b><extra></extra>"
                    ))
                    fig.add_hline(y=0, line_color="#475569", line_width=1.5)
                    if tol_val:
                        fig.add_hrect(
                            y0=-tol_val, y1=tol_val,
                            fillcolor="rgba(34,197,94,0.07)", line_width=0,
                            annotation_text="±10%", annotation_position="top right",
                            annotation_font=dict(size=10, color="#22c55e")
                        )
                    fig.update_layout(
                        **{**LAYOUT_BASE, "height": 260},
                        title=dict(text=titel, font=dict(size=15, color="#e5e7eb"), x=0.01),
                        showlegend=False,
                        xaxis=XAXIS_STYLE,
                        yaxis=dict(
                            showgrid=True, gridcolor="#1e293b", color="#64748b",
                            title="kcal", zeroline=True, zerolinecolor="#475569",
                            range=[-y_abs, y_abs]
                        )
                    )
                    return fig

                if "Bilanz_Ziel" in bilanz_df.columns and bilanz_df["Bilanz_Ziel"].notna().any():
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        st.plotly_chart(
                            bilanz_bar(bilanz_df, "Bilanz_Verbrauch", "Gegessen − Verbrauch"),
                            use_container_width=True
                        )
                    with bc2:
                        st.plotly_chart(
                            bilanz_bar(bilanz_df, "Bilanz_Ziel", "Gegessen − Ziel",
                                       mit_toleranz=True, referenz_col="Kalorienziel"),
                            use_container_width=True
                        )
                else:
                    st.plotly_chart(
                        bilanz_bar(bilanz_df, "Bilanz_Verbrauch", "Kalorienbilanz (Gegessen − Verbrauch)"),
                        use_container_width=True
                    )
