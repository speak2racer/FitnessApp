# Fitness Dashboard

Ein persönliches Fitness-Dashboard gebaut mit [Streamlit](https://streamlit.io).

## Features

- Überblick über Gewicht, Kalorien und Aktivität
- Makro-Tracking und TDEE-Berechnung
- Compliance-Auswertung
- Körperfett-Messung via Caliper-Daten

## Voraussetzungen

- Python 3.8+
- Abhängigkeiten aus `requirements.txt`

## Installation

```bash
pip install -r requirements.txt
```

## Starten

```bash
streamlit run app.py
```

## Projektstruktur

```
FitnessApp/
├── app.py              # Haupt-Dashboard
├── utils.py            # Hilfsfunktionen
├── style.css           # Styling
├── pages/              # Unterseiten (Tagesdaten, Wochenanalyse, Caliper, ...)
├── requirements.txt    # Python-Abhängigkeiten
└── app/                # Android HealthConnect Export App
```
