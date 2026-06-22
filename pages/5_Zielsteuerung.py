import streamlit as st
import pandas as pd
import numpy as np

from datetime import date

from utils import (
    lade_einstellungen,
    speichere_einstellungen,
    lade_tagesdaten,
    lade_caliper_daten,
    lade_nutrition_logs,
    berechne_makros,
    speichere_nutrition_target,
    zeige_refresh_button,
    STANDARD_FAKTOR,
)

zeige_refresh_button()

st.title(":material/track_changes: Zielsteuerung")
st.caption("Passe Ziel, Faktor und TDEE-basierte Empfehlungen zentral an.")

tab_faktor, tab_aragon = st.tabs([
    ":material/calculate: Faktor-Methode",
    ":material/restaurant_menu: Aragon Flexible Dieting",
])

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


# ── Tab 1: Faktor-Methode ─────────────────────────────────────────────────────
with tab_faktor:
    if "ziel" not in st.session_state:
        st.session_state.ziel = einstellungen["ziel"]

    if "faktor" not in st.session_state:
        st.session_state.faktor = float(einstellungen["faktor"])

    def ziel_geaendert():
        st.session_state.faktor = float(STANDARD_FAKTOR[st.session_state.ziel])

    with st.container(border=True):
        st.subheader(":material/settings: Einstellung")

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
        st.subheader(":material/bar_chart: Aktuelles Ziel")

        z1, z2, z3, z4 = st.columns(4)
        z1.metric("Gewicht Ø Woche", f"{gewicht:.2f} kg")
        z2.metric("Ziel", ziel)
        z3.metric("Faktor", f"{faktor:.2f}")
        z4.metric("Kalorienziel", f"{kalorien} kcal")

    with st.container(border=True):
        st.subheader(":material/insights: Empfehlung aus echtem TDEE")

        off1, off2 = st.columns(2)
        diaet_offset = off1.number_input(
            "Diät-Offset (Faktor unter Erhalt)", min_value=0.5, max_value=5.0,
            value=2.0, step=0.25,
            help="Wie viele Faktor-Punkte unter dem Erhalt-Faktor für Diät"
        )
        aufbau_offset = off2.number_input(
            "Aufbau-Offset (Faktor über Erhalt)", min_value=0.25, max_value=3.0,
            value=1.0, step=0.25,
            help="Wie viele Faktor-Punkte über dem Erhalt-Faktor für Aufbau"
        )

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
                .mean().reset_index().round(2)
            )

            kcal_counts = kcal_woche.groupby("Woche")["Kalorien_gegessen"].count()
            kcal_weekly = (
                kcal_woche.groupby("Woche")["Kalorien_gegessen"]
                .mean().reset_index().round(0)
            )
            kcal_weekly = kcal_weekly[kcal_weekly["Woche"].isin(
                kcal_counts[kcal_counts >= 3].index
            )]

            tdee_data = (
                gewicht_weekly.merge(kcal_weekly, on="Woche", how="inner")
                .sort_values("Woche").reset_index(drop=True)
            )
            tdee_data["Periode"] = tdee_data["Woche"].apply(lambda w: pd.Period(w, freq="W"))

            paare = []
            for i in range(1, len(tdee_data)):
                diff = tdee_data.loc[i, "Periode"] - tdee_data.loc[i - 1, "Periode"]
                diff_n = diff.n if hasattr(diff, "n") else int(diff)
                if diff_n == 1:
                    vor = tdee_data.iloc[i - 1]
                    akt = tdee_data.iloc[i]
                    delta_kg = akt["Gewicht_kg"] - vor["Gewicht_kg"]
                    kcal_delta = (delta_kg * 7700) / 7
                    tdee_est = akt["Kalorien_gegessen"] - kcal_delta
                    paare.append({
                        "Woche": f"{vor['Woche']} → {akt['Woche']}",
                        "Δ Gewicht": delta_kg,
                        "TDEE-Schätzung": tdee_est,
                        "Gewicht_kg": akt["Gewicht_kg"],
                    })

            paare = paare[-4:]

            if paare:
                echter_tdee = float(np.mean([p["TDEE-Schätzung"] for p in paare]))
                max_delta = max(abs(p["Δ Gewicht"]) for p in paare)
                letztes_gewicht = paare[-1]["Gewicht_kg"]
                gewicht_lbs_tdee = letztes_gewicht * 2.20462
                erhalt_faktor = echter_tdee / gewicht_lbs_tdee
                diaet_faktor = erhalt_faktor - diaet_offset
                aufbau_faktor = erhalt_faktor + aufbau_offset

                if max_delta > 1.0:
                    st.warning(
                        f":material/warning: Hohe Gewichtsschwankung ({max_delta:+.2f} kg) — "
                        "Schätzung kann durch Wassereinlagerungen verfälscht sein."
                    )
                elif len(paare) == 1:
                    st.info(":material/info: Nur ein Wochenpaar — mehr Daten erhöhen die Genauigkeit.")
                else:
                    st.success(f":material/check_circle: TDEE aus {len(paare)} Wochenpaaren gemittelt.")

                e1, e2, e3, e4 = st.columns(4)
                e1.metric("Echter TDEE (Ø)", f"{echter_tdee:.0f} kcal")
                e2.metric("Erhalt-Faktor", f"{erhalt_faktor:.2f}")
                e3.metric("Diät-Faktor", f"{diaet_faktor:.2f}")
                e4.metric("Aufbau-Faktor", f"{aufbau_faktor:.2f}")

                with st.expander(":material/table_rows: Einzelne Wochenpaare", expanded=False):
                    st.dataframe(
                        pd.DataFrame(paare)[["Woche", "Δ Gewicht", "TDEE-Schätzung"]]
                        .rename(columns={"Δ Gewicht": "Δ Gewicht (kg)", "TDEE-Schätzung": "TDEE (kcal)"})
                        .round({"Δ Gewicht (kg)": 2, "TDEE (kcal)": 0}),
                        use_container_width=True, hide_index=True
                    )

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

                if st.button(":material/check: Empfohlenen Faktor übernehmen", use_container_width=True):
                    st.session_state.faktor = round(empfohlener_faktor, 2)
                    speichere_einstellungen(gewicht, ziel, round(empfohlener_faktor, 2))
                    st.success(f"Empfohlener Faktor gespeichert: {empfohlener_faktor:.2f}")
                    st.rerun()

            else:
                st.info("Keine zwei aufeinanderfolgenden vollständigen Wochen gefunden.")
        else:
            st.info("Noch nicht genug Gewicht- oder Kaloriendaten vorhanden.")

    if st.button(":material/save: Ziel speichern", use_container_width=True, key="save_faktor"):
        try:
            speichere_einstellungen(gewicht, ziel, faktor)

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
            )

            st.cache_data.clear()
            st.success("Zielsteuerung gespeichert und Supabase aktualisiert.")
        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")
        st.rerun()


# ── Tab 2: Aragon Flexible Dieting ───────────────────────────────────────────
with tab_aragon:
    st.markdown(
        "Basiert auf Alan Aragons **Flexible Dieting** — "
        "TBW (Target Bodyweight) als Grundlage für TDEE und Makros."
    )

    NEAT_FAKTOREN = {
        "Low NEAT (hauptsächlich sitzend)":        1.0,
        "Moderate NEAT (leicht aktiv)":            1.1,
        "High NEAT (stehender/aktiver Job)":       1.2,
        "Very High NEAT (körperliche Arbeit)":     1.4,
    }

    caliper = lade_caliper_daten()
    kfa_aktuell = float(caliper["KFA"].iloc[-1]) if not caliper.empty else 15.0

    # ── Schritt 1: TBW berechnen ──────────────────────────────────────────────
    with st.container(border=True):
        st.subheader(":material/person: Schritt 1 — Target Bodyweight (TBW)")

        lbm_aktuell = round(gewicht * (1 - kfa_aktuell / 100), 1)

        s1c1, s1c2, s1c3 = st.columns(3)
        s1c1.metric("Aktuelles Gewicht", f"{gewicht:.1f} kg")
        s1c2.metric("Aktueller KFA", f"{kfa_aktuell:.1f}%")
        s1c3.metric("Aktuelle LBM", f"{lbm_aktuell:.1f} kg")

        st.divider()

        t1, t2 = st.columns(2)
        with t1:
            ziel_lbm = st.number_input(
                "Ziel-LBM (kg)", min_value=30.0, max_value=150.0,
                value=round(lbm_aktuell, 1), step=0.5,
                help=f"Aktuelle LBM: {lbm_aktuell} kg — passe an dein Ziel an"
            )
        with t2:
            ziel_kfa = st.number_input(
                "Ziel-KFA (%)", min_value=4.0, max_value=40.0,
                value=float(round(kfa_aktuell)),
                step=0.5,
                help="Angestrebter Körperfettanteil"
            )

        tbw_kg = ziel_lbm / ((100 - ziel_kfa) / 100)
        tbw_lbs = tbw_kg * 2.20462

        r1, r2, r3 = st.columns(3)
        r1.metric("Ziel-LBM", f"{ziel_lbm:.1f} kg")
        r2.metric("Ziel-KFA", f"{ziel_kfa:.1f}%")
        r3.metric("TBW", f"{tbw_kg:.1f} kg / {tbw_lbs:.1f} lbs")

    # ── Schritt 2: TDEE berechnen ─────────────────────────────────────────────
    with st.container(border=True):
        st.subheader(":material/local_fire_department: Schritt 2 — TDEE")

        d1, d2 = st.columns(2)
        with d1:
            trainingstunden = st.number_input(
                "Wöchentliche Trainingsstunden", min_value=0.0, max_value=30.0,
                value=4.0, step=0.5,
                help="Gesamte Trainingsstunden pro Woche"
            )
        with d2:
            neat_label = st.selectbox(
                "NEAT-Level", list(NEAT_FAKTOREN.keys()), index=1
            )

        neat_faktor = NEAT_FAKTOREN[neat_label]
        tdee_basis = tbw_lbs * (10 + trainingstunden)
        tdee_neat  = tdee_basis * neat_faktor

        fudge_pct = st.select_slider(
            "Fudge Factor",
            options=[-30, -20, -10, 0, 10, 20, 30],
            value=0,
            format_func=lambda x: f"{x:+d}%" if x != 0 else "0% (kein Anpassung)",
            help="Wenn du dich über- oder unterschätzt, passe hier in 10%-Schritten an"
        )

        tdee_final = round(tdee_neat * (1 + fudge_pct / 100))

        t1, t2, t3 = st.columns(3)
        t1.metric("TDEE Basis", f"{tdee_basis:.0f} kcal")
        t2.metric("× NEAT-Faktor", f"{tdee_neat:.0f} kcal")
        t3.metric("TDEE (mit Fudge)", f"{tdee_final} kcal")

    # ── Schritt 3: Makros ─────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader(":material/nutrition: Schritt 3 — Makros")

        protein_a = round(tbw_lbs * 1.0)
        fett_a    = round(tbw_lbs * 0.6)
        carbs_a   = max(0, round((tdee_final - protein_a * 4 - fett_a * 9) / 4))
        kcal_check = protein_a * 4 + fett_a * 9 + carbs_a * 4

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Kalorien", f"{tdee_final} kcal")
        m2.metric("Protein", f"{protein_a} g", help="TBW (lbs) × 1")
        m3.metric("Fett", f"{fett_a} g", help="TBW (lbs) × 0.6")
        m4.metric("Carbs", f"{carbs_a} g", help="Verbleibende Kalorien")

        if carbs_a == 0:
            st.warning(
                ":material/warning: Carbs = 0 — Protein + Fett übersteigen bereits das Kalorienziel. "
                "Ziel-KFA erhöhen oder Fudge Factor anpassen."
            )

        anteil_p = round(protein_a * 4 / tdee_final * 100) if tdee_final > 0 else 0
        anteil_f = round(fett_a * 9 / tdee_final * 100) if tdee_final > 0 else 0
        anteil_c = 100 - anteil_p - anteil_f
        st.caption(f"Kalorienverteilung: Protein {anteil_p}% · Fett {anteil_f}% · Carbs {anteil_c}%")

    if st.button(":material/save: Aragon-Ziel übernehmen & speichern", use_container_width=True, key="save_aragon"):
        try:
            gewicht_lbs_a = gewicht * 2.20462
            faktor_aragon = tdee_final / gewicht_lbs_a if gewicht_lbs_a > 0 else 15.0

            speichere_einstellungen(
                gewicht, einstellungen["ziel"], round(faktor_aragon, 2)
            )
            speichere_nutrition_target(
                date.today().strftime("%Y-%m-%d"),
                tdee_final,
                protein_a,
                fett_a,
                carbs_a,
                round(faktor_aragon, 2),
            )
            st.cache_data.clear()
            st.success(
                f"Aragon-Ziel gespeichert: {tdee_final} kcal · "
                f"P {protein_a} g · F {fett_a} g · C {carbs_a} g"
            )
        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")
        st.rerun()
