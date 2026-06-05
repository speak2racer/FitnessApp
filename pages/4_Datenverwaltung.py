import streamlit as st
import pandas as pd
from datetime import date

from utils import (
    lade_tagesdaten,
    lade_caliper_daten,
    lade_nutrition_targets,
    aktualisiere_supabase_gewicht,
    loesche_supabase_gewicht,
    loesche_alle_supabase_gewichte,
    loesche_caliper_supabase,
    loesche_nutrition_target,
    speichere_caliper_supabase,
    speichere_nutrition_target,
    berechne_kfa,
    lade_css,
    zeige_refresh_button
)

st.set_page_config(page_title="Datenverwaltung", layout="wide")
lade_css()
zeige_refresh_button()

st.title("🗃️ Datenverwaltung")

tab_gewicht, tab_caliper, tab_nutrition = st.tabs([
    "⚖️ Gewicht", "📏 Caliper", "🎯 Nutrition Targets"
])

# ══════════════════════════════════════════════════════════════════════════════
with tab_gewicht:
    daten = lade_tagesdaten()

    if daten.empty:
        st.warning("Keine Gewichtsdaten vorhanden.")
    else:
        daten_sorted = daten.sort_values("Datum", ascending=False).copy()
        daten_sorted["Datum"] = daten_sorted["Datum"].dt.strftime("%Y-%m-%d")

        with st.container(border=True):
            st.subheader("✏️ Eintrag bearbeiten")
            auswahl = st.selectbox("Datum auswählen", daten_sorted["Datum"].tolist(), key="gew_auswahl")
            eintrag = daten_sorted[daten_sorted["Datum"] == auswahl].iloc[0]

            c1, c2 = st.columns(2)
            with c1:
                st.metric("Datum", eintrag["Datum"])
            with c2:
                neues_gewicht = st.number_input(
                    "Gewicht (kg)", min_value=30.0, max_value=300.0,
                    value=float(eintrag["Gewicht_kg"]), step=0.1, format="%.2f", key="gew_input"
                )

            b1, b2 = st.columns(2)
            with b1:
                if st.button("💾 Speichern", use_container_width=True, key="gew_save"):
                    try:
                        aktualisiere_supabase_gewicht(eintrag["Datum"], neues_gewicht)
                        st.cache_data.clear()
                        st.success(f"Gewicht für {eintrag['Datum']} auf {neues_gewicht:.2f} kg aktualisiert.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler: {e}")
            with b2:
                if st.button("❌ Löschen", use_container_width=True, key="gew_del"):
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
                daten_sorted[["Datum", "Gewicht_kg"]].rename(columns={"Gewicht_kg": "Gewicht (kg)"}),
                use_container_width=True, hide_index=True
            )

        with st.container(border=True):
            st.subheader("⚠️ Alle Gewichtsdaten löschen")
            st.warning("Dies löscht ALLE Gewichtsdaten aus Supabase unwiderruflich.")
            if st.button("🔥 Alle löschen", use_container_width=True, key="gew_del_all"):
                try:
                    loesche_alle_supabase_gewichte()
                    st.cache_data.clear()
                    st.success("Alle Daten gelöscht.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {e}")

# ══════════════════════════════════════════════════════════════════════════════
with tab_caliper:
    caliper = lade_caliper_daten()

    if caliper.empty:
        st.info("Noch keine Caliper-Daten vorhanden.")
    else:
        caliper_sorted = caliper.sort_values("Datum", ascending=False).copy()
        caliper_sorted["Datum"] = caliper_sorted["Datum"].dt.strftime("%Y-%m-%d")

        with st.container(border=True):
            st.subheader("✏️ Eintrag bearbeiten")
            auswahl = st.selectbox("Datum auswählen", caliper_sorted["Datum"].tolist(), key="cal_auswahl")
            row = caliper_sorted[caliper_sorted["Datum"] == auswahl].iloc[0]

            c1, c2 = st.columns(2)
            with c1:
                gewicht_val = st.number_input("Gewicht (kg)", min_value=30.0, max_value=300.0,
                    value=float(row["Gewicht_kg"]), step=0.1, format="%.1f", key="cal_gew")
                brust_val = st.number_input("Brustfalte (mm)", min_value=1.0, max_value=80.0,
                    value=float(row["Brust_mm"]), step=0.5, key="cal_brust")
                bauch_val = st.number_input("Bauchfalte (mm)", min_value=1.0, max_value=80.0,
                    value=float(row["Bauch_mm"]), step=0.5, key="cal_bauch")
            with c2:
                alter_val = st.number_input("Alter", min_value=10, max_value=100,
                    value=int(row["alter"]) if "alter" in row and pd.notna(row["alter"]) else 30,
                    key="cal_alter")
                ober_val = st.number_input("Oberschenkel (mm)", min_value=1.0, max_value=80.0,
                    value=float(row["Oberschenkel_mm"]), step=0.5, key="cal_ober")

            kfa_preview = berechne_kfa(gewicht_val, alter_val, brust_val, bauch_val, ober_val)
            m1, m2, m3 = st.columns(3)
            m1.metric("KFA", f"{kfa_preview['kfa']}%")
            m2.metric("FFM", f"{kfa_preview['ffm']} kg")
            m3.metric("Fettmasse", f"{kfa_preview['fettmasse']} kg")

            b1, b2 = st.columns(2)
            with b1:
                if st.button("💾 Speichern", use_container_width=True, key="cal_save"):
                    try:
                        speichere_caliper_supabase(
                            auswahl, gewicht_val, alter_val, brust_val, bauch_val, ober_val,
                            kfa_preview["falten_summe"], kfa_preview["kfa"],
                            kfa_preview["ffm"], kfa_preview["fettmasse"]
                        )
                        st.cache_data.clear()
                        st.success(f"Caliper-Daten für {auswahl} aktualisiert.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler: {e}")
            with b2:
                if st.button("❌ Löschen", use_container_width=True, key="cal_del"):
                    try:
                        loesche_caliper_supabase(auswahl)
                        st.cache_data.clear()
                        st.success("Eintrag gelöscht.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler: {e}")

        with st.container(border=True):
            st.subheader("📋 Alle Einträge")
            anzeige_cols = ["Datum", "Gewicht_kg", "KFA", "FFM", "Fettmasse"]
            st.dataframe(
                caliper_sorted[[c for c in anzeige_cols if c in caliper_sorted.columns]],
                use_container_width=True, hide_index=True
            )

# ══════════════════════════════════════════════════════════════════════════════
with tab_nutrition:
    targets = lade_nutrition_targets()

    if targets.empty:
        st.info("Noch keine Nutrition Targets vorhanden.")
    else:
        targets_sorted = targets.sort_values("Datum", ascending=False).copy()
        targets_sorted["Datum"] = targets_sorted["Datum"].dt.strftime("%Y-%m-%d")

        with st.container(border=True):
            st.subheader("✏️ Eintrag bearbeiten")
            auswahl = st.selectbox("Datum auswählen", targets_sorted["Datum"].tolist(), key="nt_auswahl")
            row = targets_sorted[targets_sorted["Datum"] == auswahl].iloc[0]

            c1, c2 = st.columns(2)
            with c1:
                kal_val = st.number_input("Kalorien (kcal)", min_value=500, max_value=6000,
                    value=int(row["Kalorienziel"]), step=10, key="nt_kal")
                eiw_val = st.number_input("Eiweiß (g)", min_value=50, max_value=500,
                    value=int(row["Eiweiss_g"]), step=1, key="nt_eiw")
                fett_val = st.number_input("Fett (g)", min_value=20, max_value=300,
                    value=int(row["Fett_g"]), step=1, key="nt_fett")
            with c2:
                carbs_val = st.number_input("Kohlenhydrate (g)", min_value=0, max_value=800,
                    value=int(row["Kohlenhydrate_g"]), step=1, key="nt_carbs")
                faktor_val = st.number_input("Faktor", min_value=8.0, max_value=25.0,
                    value=float(row["Faktor"]), step=0.25, format="%.2f", key="nt_faktor")
                carb_anteil_val = st.number_input("Carb-Anteil (%)", min_value=0, max_value=100,
                    value=int(row["Carb_Anteil"]) if "Carb_Anteil" in row else 40, step=5, key="nt_ca")

            b1, b2 = st.columns(2)
            with b1:
                if st.button("💾 Speichern", use_container_width=True, key="nt_save"):
                    try:
                        speichere_nutrition_target(
                            auswahl, kal_val, eiw_val, fett_val, carbs_val, faktor_val, carb_anteil_val
                        )
                        st.cache_data.clear()
                        st.success(f"Nutrition Target für {auswahl} aktualisiert.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler: {e}")
            with b2:
                if st.button("❌ Löschen", use_container_width=True, key="nt_del"):
                    try:
                        loesche_nutrition_target(auswahl)
                        st.cache_data.clear()
                        st.success("Eintrag gelöscht.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler: {e}")

        with st.container(border=True):
            st.subheader("📋 Alle Einträge")
            anzeige = ["Datum", "Kalorienziel", "Eiweiss_g", "Fett_g", "Kohlenhydrate_g", "Faktor"]
            st.dataframe(
                targets_sorted[[c for c in anzeige if c in targets_sorted.columns]],
                use_container_width=True, hide_index=True
            )
