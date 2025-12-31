# NotarFlow - Inkasso-Kommunikationsplattform

Eine mehrrollenfähige Streamlit-Anwendung für die digitale Inkasso-Verwaltung mit drei Benutzerrollen:
- **Rechtsanwalt**: Vollständige Aktenverwaltung, Mahnverfahren, Zwangsvollstreckung
- **Gläubigerin**: Forderungsübersicht, Zahlungseingänge melden, Freigaben erteilen
- **Schuldner**: Forderungsstatus, Dokumente, Ratenzahlung anfragen

## Features

### Kern-Funktionen
- **Forderungskonto (Ledger)**: Vollständige Buchführung mit Zahlungsallokation (Zinsen → RA-Gebühren → Nebenkosten → Hauptforderung)
- **Dokumentenmanagement**: Upload, OCR, AI-gestützte Klassifikation
- **Verjährungsprüfung**: Automatische Event-basierte Berechnung mit Warnungen
- **Mahnverfahren**: EDA-Datei-Generierung für MB/VB-Anträge
- **Zwangsvollstreckung**: GV-Aufträge, PfüB, Vermögensverzeichnis-Auswertung

### Technische Features
- **Multi-Tenant**: Mandantentrennung auf Datenbankebene
- **RBAC**: Rollenbasierte Zugriffskontrolle
- **Audit Trail**: Vollständige Nachverfolgbarkeit aller Aktionen
- **AI Copilot**: Optional mit OpenAI-Integration

## Installation

### Voraussetzungen
- Python 3.10+
- PostgreSQL 14+
- Redis (für Background Jobs)

### Setup

```bash
# Repository klonen
git clone <repository-url>
cd NotarFlow

# Virtual environment erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Abhängigkeiten installieren
pip install -r requirements.txt

# .env Datei erstellen
cp .env.example .env
# Anpassen: DATABASE_URL, SECRET_KEY, etc.

# Datenbank initialisieren
python -c "from db import init_db; init_db()"

# Seed-Daten erstellen (Demo)
python db/seed_data.py

# Anwendung starten
streamlit run app/main.py
```

### Umgebungsvariablen

```env
# Datenbank
DATABASE_URL=postgresql://user:pass@localhost:5432/notarflow

# Sicherheit
SECRET_KEY=your-secret-key-min-32-chars

# Redis (für Celery)
REDIS_URL=redis://localhost:6379/0

# Optionale AI-Integration
OPENAI_API_KEY=sk-...

# E-Mail
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user
SMTP_PASSWORD=pass
```

## Demo-Zugangsdaten

Nach Ausführung von `seed_data.py`:

| Rolle | E-Mail | Passwort |
|-------|--------|----------|
| Rechtsanwalt | ra.schmidt@kanzlei.de | Demo123! |
| Gläubigerin | glaeubiger@firma.de | Demo123! |
| Schuldner | schuldner@beispiel.de | Demo123! |

## Projektstruktur

```
NotarFlow/
├── app/                    # Streamlit UI
│   ├── main.py            # Haupteinstiegspunkt
│   ├── pages/             # Seiten nach Rolle
│   │   ├── 1_Dashboard.py
│   │   ├── 2_Akten.py
│   │   ├── creditor/      # Gläubiger-Seiten
│   │   └── debtor/        # Schuldner-Seiten
│   └── utils/             # UI-Hilfsfunktionen
├── backend/               # Backend-Services
│   └── services/
│       ├── auth_service.py
│       ├── case_service.py
│       ├── ledger_service.py
│       ├── document_service.py
│       ├── limitation_service.py
│       ├── eda_service.py
│       ├── enforcement_service.py
│       ├── ai_service.py
│       └── notification_service.py
├── db/                    # Datenbank
│   ├── models.py          # SQLAlchemy-Modelle
│   └── seed_data.py       # Demo-Daten
├── config/                # Konfiguration
│   └── settings.py
├── tests/                 # Tests
│   └── unit/
└── requirements.txt
```

## Sicherheit

- **DSGVO-konform**: Mandantentrennung, Audit-Trail, Zugriffsrechte
- **Kanzlei-Standard**: Verschlüsselung, sichere Sessions, RBAC
- **Revisionssicher**: Versionierung von Dokumenten, Hash-Prüfung

## Mahnverfahren (EDA)

Die Anwendung generiert EDA-Datensätze gemäß den Spezifikationen der deutschen Mahngerichte:
- Format 4.0 für Mahnbescheid-Anträge
- Format 4.1 für Vollstreckungsbescheid-Anträge

Versand erfolgt über:
1. **MVP-Modus**: Download der EDA-Datei, manueller Versand via beA
2. **Pro-Modus**: Lokaler Connector-Agent für automatisierten beA-Versand

## Tests

```bash
# Unit-Tests ausführen
pytest tests/unit/ -v

# Mit Coverage
pytest --cov=backend tests/
```

## Lizenz

Proprietär - Alle Rechte vorbehalten

## Support

Bei Fragen oder Problemen: support@notarflow.de
