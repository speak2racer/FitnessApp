import streamlit as st
import pandas as pd
import json
import os
import requests

DATEI = "daten.csv"
CALIPER_DATEI = "caliper.csv"
EINSTELLUNGEN_DATEI = "einstellungen.json"

try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
except Exception:
    import os
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

STANDARD_FAKTOR = {
    "Diät": 12.0,
    "Erhalt": 15.0,
    "Aufbau": 16.0
}

CARB_OPTIONEN = [40, 50, 60]


def lade_css():
    if os.path.exists("style.css"):
        with open("style.css", "r", encoding="utf-8") as f:
            st.markdown(
                f"<style>{f.read()}</style>",
                unsafe_allow_html=True
            )


def zeige_refresh_button():
    import datetime
    with st.sidebar:
        st.divider()
        if "letzter_refresh" not in st.session_state:
            st.session_state.letzter_refresh = datetime.datetime.now()
        st.caption(f"🕐 Stand: {st.session_state.letzter_refresh.strftime('%H:%M:%S')}")
        if st.button("🔄 Daten aktualisieren", use_container_width=True):
            st.cache_data.clear()
            st.session_state.letzter_refresh = datetime.datetime.now()
            st.rerun()


def lade_einstellungen():
    standard = {
        "gewicht": 90.0,
        "ziel": "Erhalt",
        "faktor": 15.0,
        "alter": 40,
        "brust": 10.0,
        "bauch": 20.0,
        "oberschenkel": 15.0
    }

    if os.path.exists(EINSTELLUNGEN_DATEI):
        with open(EINSTELLUNGEN_DATEI, "r", encoding="utf-8") as f:
            daten = json.load(f)
            standard.update(daten)

    # Faktor und Carb-Anteil aus Supabase nutrition_targets überschreiben
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/nutrition_targets",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
            },
            params={"select": "faktor", "order": "datum.desc", "limit": "1"}
        )
        response.raise_for_status()
        daten = response.json()
        if daten:
            faktor = float(daten[0]["faktor"])
            standard["faktor"] = faktor
            # Ziel aus Faktor ableiten
            if faktor <= 13.5:
                standard["ziel"] = "Diät"
            elif faktor >= 15.5:
                standard["ziel"] = "Aufbau"
            else:
                standard["ziel"] = "Erhalt"
    except Exception:
        pass

    # Alter und Caliper-Falten aus letztem Supabase-Caliper-Eintrag laden
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/caliper",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
            },
            params={"select": "alter,brust_mm,bauch_mm,oberschenkel_mm", "order": "datum.desc", "limit": "1"}
        )
        response.raise_for_status()
        daten = response.json()
        if daten:
            standard["alter"] = int(daten[0]["alter"])
            standard["brust"] = float(daten[0]["brust_mm"])
            standard["bauch"] = float(daten[0]["bauch_mm"])
            standard["oberschenkel"] = float(daten[0]["oberschenkel_mm"])
    except Exception:
        pass

    return standard

@st.cache_data(ttl=300)
def lade_nutrition_targets(ab_datum=None):
    try:
        url = f"{SUPABASE_URL}/rest/v1/nutrition_targets"

        params = {
            "select": "*",
            "order": "datum.asc"
        }

        if ab_datum:
            params["datum"] = f"gte.{ab_datum}"

        response = requests.get(
            url,
            headers=supabase_headers(),
            params=params
        )

        response.raise_for_status()
        daten = response.json()

        if len(daten) > 0:
            df = pd.DataFrame(daten)

            df = df.rename(
                columns={
                    "datum": "Datum",
                    "kalorien": "Kalorienziel",
                    "eiweiss": "Eiweiss_g",
                    "fett": "Fett_g",
                    "kohlenhydrate": "Kohlenhydrate_g",
                    "faktor": "Faktor"
                }
            )

            df["Datum"] = pd.to_datetime(df["Datum"])

            return df.sort_values("Datum")

    except Exception as e:
        print("Supabase Nutrition Targets Fehler:", e)

    return pd.DataFrame()


def speichere_einstellungen(
    gewicht,
    ziel,
    faktor,
    alter=None,
    brust=None,
    bauch=None,
    oberschenkel=None
):
    alte = lade_einstellungen()

    daten = {
        "gewicht": gewicht,
        "ziel": ziel,
        "faktor": faktor,
        "alter": alter if alter is not None else alte["alter"],
        "brust": brust if brust is not None else alte["brust"],
        "bauch": bauch if bauch is not None else alte["bauch"],
        "oberschenkel": (
            oberschenkel
            if oberschenkel is not None
            else alte["oberschenkel"]
        )
    }

    with open(EINSTELLUNGEN_DATEI, "w", encoding="utf-8") as f:
        json.dump(daten, f, indent=4)


def berechne_makros(gewicht_kg, faktor, kfa):
    gewicht_lbs = round(gewicht_kg * 2.20462, 2)
    kalorien = round(gewicht_lbs * faktor)

    eiweiss_g = round(gewicht_kg * 2)
    eiweiss_kcal = eiweiss_g * 4

    fett_g = round(gewicht_kg * 0.7)
    fett_kcal = fett_g * 9

    kohlenhydrate_kcal = max(0, kalorien - eiweiss_kcal - fett_kcal)
    kohlenhydrate_g = round(kohlenhydrate_kcal / 4)

    return {
        "gewicht_lbs": gewicht_lbs,
        "kalorien": kalorien,
        "eiweiss_g": eiweiss_g,
        "fett_g": fett_g,
        "kohlenhydrate_g": kohlenhydrate_g,
    }


def berechne_kfa(gewicht_kg, alter, brust, bauch, oberschenkel):
    summe_falten = brust + bauch + oberschenkel

    koerperdichte = (
        1.10938
        - 0.0008267 * summe_falten
        + 0.0000016 * (summe_falten ** 2)
        - 0.0002574 * alter
    )

    kfa = round((495 / koerperdichte) - 450, 1)
    ffm = round(gewicht_kg * (1 - kfa / 100), 1)
    fettmasse = round(gewicht_kg - ffm, 1)

    return {
        "kfa": kfa,
        "ffm": ffm,
        "fettmasse": fettmasse,
        "falten_summe": summe_falten
    }


def faktor_empfehlung(ziel, veraenderung_lbs, faktor):
    neuer_faktor = faktor

    if ziel == "Diät":
        if veraenderung_lbs <= -2:
            neuer_faktor = faktor
        elif -1.9 <= veraenderung_lbs <= -1:
            neuer_faktor = faktor - 0.5
        elif -1 < veraenderung_lbs <= 0.5:
            neuer_faktor = faktor - 1
        else:
            neuer_faktor = faktor - 1.5

    elif ziel == "Aufbau":
        if veraenderung_lbs >= 2:
            neuer_faktor = faktor - 0.5
        elif 1 <= veraenderung_lbs < 2:
            neuer_faktor = faktor - 0.25
        elif 0 <= veraenderung_lbs < 1:
            neuer_faktor = faktor
        else:
            neuer_faktor = faktor + 1.5

    return round(max(8.0, min(25.0, neuer_faktor)), 2)


def supabase_headers():
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json"
    }


@st.cache_data(ttl=300)
def lade_tagesdaten(ab_datum=None):
    try:
        url = f"{SUPABASE_URL}/rest/v1/weights"

        params = {
            "select": "*",
            "order": "datum.asc"
        }

        if ab_datum:
            params["datum"] = f"gte.{ab_datum}"

        response = requests.get(
            url,
            headers=supabase_headers(),
            params=params
        )

        response.raise_for_status()
        daten = response.json()

        if len(daten) > 0:
            df = pd.DataFrame(daten)

            df = df.rename(
                columns={
                    "datum": "Datum",
                    "gewicht": "Gewicht_kg"
                }
            )

            df["Datum"] = pd.to_datetime(df["Datum"])

            df["Kalorienziel"] = 0
            df["Faktor"] = 0
            df["Eiweiss_g"] = 0
            df["Fett_g"] = 0
            df["Kohlenhydrate_g"] = 0

            return df[[
                "Datum",
                "Gewicht_kg",
                "Kalorienziel",
                "Faktor",
                "Eiweiss_g",
                "Fett_g",
                "Kohlenhydrate_g"
            ]].sort_values("Datum")

    except Exception as e:
        print("Supabase Gewicht Fehler:", e)

    if os.path.exists(DATEI):
        df = pd.read_csv(DATEI)
        df["Datum"] = pd.to_datetime(df["Datum"])

        if ab_datum:
            df = df[df["Datum"] >= pd.to_datetime(ab_datum)]

        return df.sort_values("Datum")

    return pd.DataFrame()


@st.cache_data(ttl=300)
def lade_caliper_daten():
    try:
        url = f"{SUPABASE_URL}/rest/v1/caliper"

        params = {
            "select": "*",
            "order": "datum.asc"
        }

        response = requests.get(
            url,
            headers=supabase_headers(),
            params=params
        )

        response.raise_for_status()
        daten = response.json()

        if len(daten) > 0:
            df = pd.DataFrame(daten)

            df = df.rename(
                columns={
                    "datum": "Datum",
                    "gewicht_kg": "Gewicht_kg",
                    "brust_mm": "Brust_mm",
                    "bauch_mm": "Bauch_mm",
                    "oberschenkel_mm": "Oberschenkel_mm",
                    "falten_summe_mm": "Falten_Summe_mm",
                    "kfa": "KFA",
                    "ffm": "FFM",
                    "fettmasse": "Fettmasse"
                }
            )

            df["Datum"] = pd.to_datetime(df["Datum"])

            return df.sort_values("Datum")

    except Exception as e:
        print("Supabase Caliper Fehler:", e)

    if os.path.exists(CALIPER_DATEI):
        df = pd.read_csv(CALIPER_DATEI)
        df["Datum"] = pd.to_datetime(df["Datum"])
        return df.sort_values("Datum")

    return pd.DataFrame()


def aktualisiere_supabase_gewicht(datum, neues_gewicht):
    url = f"{SUPABASE_URL}/rest/v1/weights"

    headers = supabase_headers()
    headers["Prefer"] = "return=minimal"

    response = requests.patch(
        url,
        headers=headers,
        params={"datum": f"eq.{datum}"},
        json={"gewicht": round(float(neues_gewicht), 2)}
    )

    response.raise_for_status()


def loesche_supabase_gewicht(datum):
    url = f"{SUPABASE_URL}/rest/v1/weights"

    params = {
        "datum": f"eq.{datum}"
    }

    response = requests.delete(
        url,
        headers=supabase_headers(),
        params=params
    )

    response.raise_for_status()


def loesche_alle_supabase_gewichte():
    url = f"{SUPABASE_URL}/rest/v1/weights"

    params = {
        "datum": "not.is.null"
    }

    response = requests.delete(
        url,
        headers=supabase_headers(),
        params=params
    )

    response.raise_for_status()


def loesche_caliper_supabase(datum):
    response = requests.delete(
        f"{SUPABASE_URL}/rest/v1/caliper",
        headers=supabase_headers(),
        params={"datum": f"eq.{datum}"}
    )
    response.raise_for_status()


def loesche_nutrition_target(datum):
    response = requests.delete(
        f"{SUPABASE_URL}/rest/v1/nutrition_targets",
        headers=supabase_headers(),
        params={"datum": f"eq.{datum}"}
    )
    response.raise_for_status()


def speichere_nutrition_target(
    datum,
    kalorien,
    eiweiss,
    fett,
    kohlenhydrate,
    faktor,
):
    url = f"{SUPABASE_URL}/rest/v1/nutrition_targets"

    headers = supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"

    daten = {
        "datum": datum,
        "kalorien": int(kalorien),
        "eiweiss": int(eiweiss),
        "fett": int(fett),
        "kohlenhydrate": int(kohlenhydrate),
        "faktor": float(faktor),
    }

    response = requests.post(
        f"{url}?on_conflict=datum",
        headers=headers,
        json=daten
    )

    response.raise_for_status()


def speichere_caliper_supabase(
    datum,
    gewicht_kg,
    alter,
    brust_mm,
    bauch_mm,
    oberschenkel_mm,
    falten_summe_mm,
    kfa,
    ffm,
    fettmasse
):
    url = f"{SUPABASE_URL}/rest/v1/caliper"

    headers = supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"

    daten = {
        "datum": datum,
        "gewicht_kg": float(gewicht_kg),
        "alter": int(alter),
        "brust_mm": float(brust_mm),
        "bauch_mm": float(bauch_mm),
        "oberschenkel_mm": float(oberschenkel_mm),
        "falten_summe_mm": float(falten_summe_mm),
        "kfa": float(kfa),
        "ffm": float(ffm),
        "fettmasse": float(fettmasse)
    }

    response = requests.post(
        f"{url}?on_conflict=datum",
        headers=headers,
        json=daten
    )

    response.raise_for_status()

@st.cache_data(ttl=300)
def lade_nutrition_logs(ab_datum=None):
    try:
        url = f"{SUPABASE_URL}/rest/v1/nutrition_daily_logs"

        params = {
            "select": "*",
            "order": "log_date.asc"
        }

        if ab_datum:
            params["log_date"] = f"gte.{ab_datum}"

        response = requests.get(
            url,
            headers=supabase_headers(),
            params=params
        )

        response.raise_for_status()
        daten = response.json()

        if len(daten) > 0:
            df = pd.DataFrame(daten)

            df = df.rename(
                columns={
                    "log_date": "Datum",
                    "calories": "Kalorien_gegessen",
                    "protein": "Protein_gegessen",
                    "carbs": "Carbs_gegessen",
                    "fat": "Fett_gegessen"
                }
            )

            df["Datum"] = pd.to_datetime(df["Datum"])

            return df.sort_values("Datum")

    except Exception as e:
        print("Supabase Nutrition Log Fehler:", e)

    return pd.DataFrame()


@st.cache_data(ttl=300)
def lade_activity_logs(ab_datum=None):
    try:
        url = f"{SUPABASE_URL}/rest/v1/activity_daily_logs"

        params = {
            "select": "*",
            "order": "log_date.asc"
        }

        if ab_datum:
            params["log_date"] = f"gte.{ab_datum}"

        response = requests.get(
            url,
            headers=supabase_headers(),
            params=params
        )

        response.raise_for_status()
        daten = response.json()

        if len(daten) > 0:
            df = pd.DataFrame(daten)

            df = df.rename(
                columns={
                    "log_date": "Datum",
                    "active_calories": "Aktivkalorien",
                    "total_calories": "Gesamtverbrauch",
                    "steps": "Schritte"
                }
            )

            df["Datum"] = pd.to_datetime(df["Datum"])

            return df.sort_values("Datum")

    except Exception as e:
        print("Supabase Activity Log Fehler:", e)

    return pd.DataFrame()