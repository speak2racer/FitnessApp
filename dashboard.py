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
    zeige_refresh_button,
)

zeige_refresh_button()

st.title(":material/dashboard: Fitness Dashboard")

einstellungen = lade_einstellungen()
daten = lade_tagesdaten()
caliper = lade_caliper_daten()
nutrition_logs = lade_nutrition_logs()
activity_logs = lade_activity_logs()

if not daten.empty:
    aktuelle_woche_daten = daten[
        daten["Datum"].dt.to_period("W") == daten["Datum"].max().to_period("W")
    ]
    gewicht = float(aktuelle_woche_daten["Gewicht_kg"].mean())
else:
    gewicht = float(einstellungen["gewicht"])

ziel = einstellungen["ziel"]
faktor = float(einstellungen["faktor"])
kfa = float(caliper["KFA"].iloc[-1]) if not caliper.empty else 15.0
makros = berechne_makros(gewicht, faktor, kfa)
heute = pd.Timestamp.today().normalize()

nutrition_heute = (
    nutrition_logs[nutrition_logs["Datum"].dt.normalize() == heute]
    if not nutrition_logs.empty else pd.DataFrame()
)
activity_heute = (
    activity_logs[activity_logs["Datum"].dt.normalize() == heute]
    if not activity_logs.empty else pd.DataFrame()
)

gegessen = float(nutrition_heute["Kalorien_gegessen"].iloc[-1]) if not nutrition_heute.empty else 0
aktiv = float(activity_heute["Aktivkalorien"].iloc[-1]) if not activity_heute.empty else 0
gesamtverbrauch = float(activity_heute["Gesamtverbrauch"].iloc[-1]) if not activity_heute.empty else 0
schritte = int(activity_heute["Schritte"].iloc[-1]) if not activity_heute.empty else 0

if not daten.empty:
    vorwoche = daten[
        daten["Datum"].dt.to_period("W")
        == (daten["Datum"].max() - pd.Timedelta(weeks=1)).to_period("W")
    ]
    if not vorwoche.empty:
        gewicht_trend = gewicht - float(vorwoche["Gewicht_kg"].mean())
        symbol = "↘" if gewicht_trend < -0.1 else "↗" if gewicht_trend > 0.1 else "→"
        st.success(f"Letzter Sync: {daten['Datum'].max().strftime('%d.%m.%Y')}  |  {symbol} {gewicht_trend:+.2f} kg zur Vorwoche")
    else:
        st.success(f"Letzter Sync: {daten['Datum'].max().strftime('%d.%m.%Y')}")
else:
    st.warning("Noch keine Gewichtsdaten vorhanden.")

hinweise = []
if daten.empty or daten[daten["Datum"].dt.normalize() == heute].empty:
    hinweise.append("Kein Gewicht heute")
if nutrition_heute.empty:
    hinweise.append("Keine Ernährung heute")
if hinweise:
    st.warning("  |  ".join(hinweise))

tab_heute, tab_woche, tab_koerper = st.tabs([
    ":material/today: Heute",
    ":material/bar_chart: Woche",
    ":material/fitness_center: Körper",
])

# ── Heute ─────────────────────────────────────────────────────────────────────
with tab_heute:

    with st.container(border=True):
        st.subheader(":material/settings: Aktueller Stand")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Gewicht Ø Woche", f"{gewicht:.2f} kg")
        c2.metric("Ziel", ziel)
        c3.metric("Faktor", f"{faktor:.2f}")
        c4.metric("Kalorienziel", f"{makros['kalorien']} kcal")

    with st.container(border=True):
        st.subheader(":material/local_fire_department: Kalorienbilanz heute")

        ziel_kalorien = makros["kalorien"]
        differenz_ziel = gegessen - ziel_kalorien
        netto_gesamt = gegessen - gesamtverbrauch

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Kalorienziel", f"{ziel_kalorien:.0f} kcal")
        k2.metric("Gegessen", f"{gegessen:.0f} kcal", f"{differenz_ziel:+.0f} kcal")
        k3.metric("Verbrauch gesamt", f"{gesamtverbrauch:.0f} kcal")
        k4.metric("Schritte", f"{schritte:,}".replace(",", "."))

        k5, k6 = st.columns(2)
        k5.metric("Aktiv verbrannt", f"{aktiv:.0f} kcal")
        k6.metric("Bilanz vs Verbrauch", f"{netto_gesamt:+.0f} kcal")

        if gegessen > 0:
            fortschritt = min(gegessen / ziel_kalorien, 1.0)
            st.progress(fortschritt, text=f"{gegessen:.0f} / {ziel_kalorien:.0f} kcal gegessen")

    with st.container(border=True):
        st.subheader(":material/check_circle: Compliance gestern")

        gestern = pd.Timestamp.today().date() - pd.Timedelta(days=1)
        nutrition_gestern = (
            nutrition_logs[nutrition_logs["Datum"].dt.date == gestern]
            if not nutrition_logs.empty else pd.DataFrame()
        )

        if nutrition_gestern.empty:
            st.info(f"Keine Daten für gestern ({gestern}).")
        else:
            row = nutrition_gestern.iloc[-1]

            def trefferquote(ist, z):
                if z <= 0:
                    return 0
                return round(max(0, 100 - abs(ist - z) / z * 100), 1)

            k_score = trefferquote(float(row["Kalorien_gegessen"]), makros["kalorien"])
            p_score = trefferquote(float(row["Protein_gegessen"]), makros["eiweiss_g"])
            f_score = trefferquote(float(row["Fett_gegessen"]), makros["fett_g"])
            c_score = trefferquote(float(row["Carbs_gegessen"]), makros["kohlenhydrate_g"])
            gesamt = round(k_score * 0.4 + p_score * 0.3 + f_score * 0.15 + c_score * 0.15, 1)

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Gesamt", f"{gesamt:.1f}%")
            c2.metric("Kalorien", f"{k_score:.1f}%", f"{float(row['Kalorien_gegessen']) - makros['kalorien']:+.0f} kcal")
            c3.metric("Protein", f"{p_score:.1f}%", f"{float(row['Protein_gegessen']) - makros['eiweiss_g']:+.0f} g")
            c4.metric("Fett", f"{f_score:.1f}%", f"{float(row['Fett_gegessen']) - makros['fett_g']:+.0f} g")
            c5.metric("Carbs", f"{c_score:.1f}%", f"{float(row['Carbs_gegessen']) - makros['kohlenhydrate_g']:+.0f} g")

# ── Woche ─────────────────────────────────────────────────────────────────────
with tab_woche:

    if not nutrition_logs.empty:
        with st.container(border=True):
            st.subheader(":material/track_changes: Wochenziel-Fortschritt")

            diese_woche = nutrition_logs[
                nutrition_logs["Datum"].dt.to_period("W") == pd.Timestamp.today().to_period("W")
            ]

            if not diese_woche.empty:
                ziel_kcal = makros["kalorien"]
                tage_im_ziel = int((
                    (diese_woche["Kalorien_gegessen"] >= ziel_kcal * 0.9) &
                    (diese_woche["Kalorien_gegessen"] <= ziel_kcal * 1.1)
                ).sum())
                tage_gesamt = len(diese_woche)

                p1, p2 = st.columns(2)
                p1.metric("Tage im Zielbereich", f"{tage_im_ziel} / {tage_gesamt}")
                p2.metric("Tage mit Daten", f"{tage_gesamt} / 7")
                st.progress(tage_im_ziel / 7, text=f"{tage_im_ziel} von 7 Tagen im Kalorienbereich (±10%)")
            else:
                st.info("Noch keine Ernährungsdaten diese Woche.")

    with st.container(border=True):
        st.subheader(":material/bar_chart: Wochenübersicht")

        if not nutrition_logs.empty and not activity_logs.empty:
            n = nutrition_logs[nutrition_logs["Datum"].dt.normalize() < heute].copy()
            a = activity_logs[
                (activity_logs["Datum"].dt.normalize() < heute) &
                (activity_logs["Gesamtverbrauch"] > 0)
            ].copy()
            n["Woche"] = n["Datum"].dt.to_period("W").astype(str)
            a["Woche"] = a["Datum"].dt.to_period("W").astype(str)

            nw = n.groupby("Woche").agg({"Kalorien_gegessen": "mean", "Protein_gegessen": "mean"}).reset_index().round(0)
            aw = a.groupby("Woche").agg({"Gesamtverbrauch": "mean", "Schritte": "mean"}).reset_index().round(0)
            weekly = nw.merge(aw, on="Woche", how="outer").sort_values("Woche")
            weekly["Bilanz"] = weekly["Kalorien_gegessen"] - weekly["Gesamtverbrauch"]

            aktuell = weekly.iloc[-1]
            w1, w2, w3, w4 = st.columns(4)
            w1.metric("Kalorien Ø", f"{aktuell['Kalorien_gegessen']:.0f} kcal")
            w2.metric("Bilanz Ø", f"{aktuell['Bilanz']:+.0f} kcal")
            w3.metric("Verbrauch Ø", f"{aktuell['Gesamtverbrauch']:.0f} kcal")
            w4.metric("Schritte Ø", f"{aktuell['Schritte']:.0f}")
        else:
            st.info("Noch nicht genug Daten vorhanden.")

    with st.container(border=True):
        st.subheader(":material/calculate: Geschätzter TDEE")

        if not daten.empty and not nutrition_logs.empty:
            gw = daten[daten["Datum"].dt.normalize() < heute].copy()
            kw = nutrition_logs[
                (nutrition_logs["Datum"].dt.normalize() < heute) &
                (nutrition_logs["Kalorien_gegessen"] > 0)
            ].copy()
            gw["Woche"] = gw["Datum"].dt.to_period("W").astype(str)
            kw["Woche"] = kw["Datum"].dt.to_period("W").astype(str)

            g_weekly = gw.groupby("Woche")["Gewicht_kg"].mean().reset_index().round(2)
            kcal_counts = kw.groupby("Woche")["Kalorien_gegessen"].count()
            k_weekly = kw.groupby("Woche")["Kalorien_gegessen"].mean().reset_index().round(0)
            k_weekly = k_weekly[k_weekly["Woche"].isin(kcal_counts[kcal_counts >= 3].index)]
            tdee_data = g_weekly.merge(k_weekly, on="Woche").sort_values("Woche").reset_index(drop=True)
            tdee_data["Periode"] = tdee_data["Woche"].apply(lambda w: pd.Period(w, freq="W"))

            paar = None
            for i in range(len(tdee_data) - 1, 0, -1):
                diff = tdee_data.loc[i, "Periode"] - tdee_data.loc[i-1, "Periode"]
                diff_n = diff.n if hasattr(diff, "n") else int(diff)
                if diff_n == 1:
                    paar = (tdee_data.iloc[i-1], tdee_data.iloc[i])
                    break

            if paar:
                vor, akt = paar
                delta_kg = akt["Gewicht_kg"] - vor["Gewicht_kg"]
                echter_tdee = akt["Kalorien_gegessen"] - (delta_kg * 7700 / 7)

                t1, t2, t3, t4 = st.columns(4)
                t1.metric(f"Gewicht {akt['Woche']}", f"{akt['Gewicht_kg']:.2f} kg")
                t2.metric(f"Gewicht {vor['Woche']}", f"{vor['Gewicht_kg']:.2f} kg")
                t3.metric("Trend", f"{delta_kg:+.2f} kg/Woche")
                t4.metric("Geschätzter TDEE", f"{echter_tdee:.0f} kcal")
                st.caption("Berechnet aus zwei aufeinanderfolgenden Wochen mit je ≥3 Kalorieneinträgen.")
            else:
                st.info("Mindestens zwei Wochen Daten nötig.")
        else:
            st.info("Noch nicht genug Daten vorhanden.")

# ── Körper ────────────────────────────────────────────────────────────────────
with tab_koerper:

    if not daten.empty:
        with st.container(border=True):
            st.subheader(":material/show_chart: Gewichtsverlauf")
            try:
                y_min = daten["Gewicht_kg"].min() * 0.98
                y_max = daten["Gewicht_kg"].max() * 1.02

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=daten["Datum"], y=daten["Gewicht_kg"],
                    mode="lines+markers", name="Gewicht",
                    line=dict(color="#4C9BE8", width=2), marker=dict(size=4)
                ))
                if len(daten) >= 7:
                    g7d = daten.set_index("Datum")["Gewicht_kg"].rolling("7D").mean().reset_index()
                    fig.add_trace(go.Scatter(
                        x=g7d["Datum"], y=g7d["Gewicht_kg"],
                        mode="lines", name="7-Tage Ø",
                        line=dict(color="#F4A623", width=2, dash="dash")
                    ))
                fig.update_layout(
                    height=300, margin=dict(l=0, r=0, t=10, b=0),
                    legend=dict(orientation="h", y=1.1),
                    xaxis_title=None, yaxis_title="kg",
                    yaxis=dict(range=[y_min, y_max]),
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Chart konnte nicht geladen werden: {e}")

    if not caliper.empty:
        with st.container(border=True):
            st.subheader(":material/monitor_weight: Körperanalyse")

            letzter = caliper.iloc[-1]
            vorher = caliper.iloc[-2] if len(caliper) >= 2 else None

            kfa_delta = letzter["KFA"] - vorher["KFA"] if vorher is not None else 0
            ffm_delta = letzter["FFM"] - vorher["FFM"] if vorher is not None else 0
            fett_delta = letzter["Fettmasse"] - vorher["Fettmasse"] if vorher is not None else 0

            k1, k2, k3 = st.columns(3)
            k1.metric("KFA", f"{letzter['KFA']:.1f}%", f"{kfa_delta:+.1f}%")
            k2.metric("FFM", f"{letzter['FFM']:.1f} kg", f"{ffm_delta:+.1f} kg")
            k3.metric("Fettmasse", f"{letzter['Fettmasse']:.1f} kg", f"{fett_delta:+.1f} kg")
    else:
        st.info("Noch keine Caliper-Daten vorhanden. Gehe zur Caliper-Seite.")
