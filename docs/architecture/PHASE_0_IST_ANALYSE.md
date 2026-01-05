# Phase 0: Ist-Analyse InkassoKom

**Datum:** 05.01.2026
**Status:** Abgeschlossen

---

## 1. Zusammenfassung

Die aktuelle InkassoKom-Anwendung nutzt **zwei parallele Datenhaltungskonzepte**, die nicht miteinander verbunden sind:

1. **SQLAlchemy-Modelle** (`db/models.py`) - vorbereitet aber nicht aktiv genutzt
2. **In-Memory Demo-Daten** (`app/main.py`) - aktuell im Einsatz

Die Streamlit-App verwendet ausschließlich die Demo-Daten und Session-State, NICHT die SQLAlchemy-Modelle.

---

## 2. Bestehende SQLAlchemy-Modelle (db/models.py)

| Tabelle | Felder (Auszug) | Status |
|---------|----------------|--------|
| `organizations` | id, name, slug, address, email, phone | Definiert, nicht genutzt |
| `users` | id, org_id, email, password_hash, name, role | Definiert, nicht genutzt |
| `cases` | id, org_id, internal_number, creditor/debtor, status | Definiert, nicht genutzt |
| `claims` | id, case_id, principal_amount, interest_rate, due_date | Definiert, nicht genutzt |
| `ledger_bookings` | id, case_id, claim_id, debit_credit, amount, category | Definiert, nicht genutzt |
| `documents` | id, case_id, filename, storage_path, ocr_text | Definiert, nicht genutzt |
| `timeline_events` | id, case_id, event_type, title, actor_id | Definiert, nicht genutzt |
| `payment_plans` | id, case_id, status, total_amount, installments | Definiert, nicht genutzt |
| `inbox_items` | id, org_id, document_id, source, status | Definiert, nicht genutzt |
| `notifications` | id, user_id, title, message, is_read | Definiert, nicht genutzt |
| `limitation_events` | id, case_id, claim_id, event_type, event_date | Definiert, nicht genutzt |

**Fehlend im aktuellen Schema (für Zielarchitektur erforderlich):**
- `parties` (n:m Beteiligte)
- `case_parties` (Zuordnung)
- `communications` (Threads)
- `messages` (Ein-/Ausgang)
- `templates` (Vorlagen)
- `letterheads` (Briefköpfe)
- `generated_documents` (erzeugte Schreiben)
- `audit_log` (Änderungshistorie)
- `memberships` (User↔Org)

---

## 3. Aktive In-Memory Datenstrukturen (app/main.py)

### 3.1 Globale Demo-Daten (hardcoded)

```python
DEMO_CASES = [
    {
        'id': 'case-001',
        'nr': '1/25',
        'creditor': 'Mustermann GmbH',
        'debtor': 'Max Schmidt',
        'creditor_address': '...',
        'debtor_address': '...',
        'subject': '...',
        'status': 'offen',  # offen|mahnverfahren|vollstreckung
        'dunning': 'nicht_beantragt',
        'enforcement': 'nicht_begonnen',
        'principal': 5000.00,
        'interest': 5.0,
        'due_date': date,
        'created': datetime,
        # ... weitere Felder
    }
]

DEMO_BOOKINGS = {
    'case-001': [
        {'date': date, 'type': 'S', 'amount': 5000.00, 'cat': 'Hauptforderung', 'desc': '...'}
    ]
}

DEMO_DOCUMENTS = {
    'case-001': [
        {'id': '...', 'name': '...', 'type': '...', 'category': '...', 'page': 1, 'date': date}
    ]
}

DEMO_MESSAGES = [...]
DEMO_EVENTS = [...]
```

### 3.2 Session State Variablen

| Variable | Typ | Zweck |
|----------|-----|-------|
| `authenticated` | bool | Login-Status |
| `user` | dict | Aktueller Benutzer (id, name, role) |
| `page` | str | Aktuelle Seite |
| `selected_case` | str | Ausgewählte Akte ID |
| `imported_cases` | list | Importierte Akten (RA-Micro) |
| `imported_documents` | dict | Dokumente importierter Akten |
| `imported_bookings` | dict | Buchungen importierter Akten |
| `pdf_viewer_content` | bytes | Aktuelle PDF im Viewer |
| `document_pdfs` | dict | Einzelne Dokument-PDFs |
| `case_full_pdfs` | dict | Gesamt-PDFs pro Akte |
| `openai_api_key` | str | OpenAI API Key |
| `openai_api_key_from_secrets` | bool | Key aus Secrets geladen? |
| `templates` | dict | Vorlagen (briefkopf_docx, email_signatur, etc.) |
| `kanzlei_daten` | dict | Kanzleiinformationen |
| `messages` | list | Nachrichten |
| `notifications` | list | Benachrichtigungen |
| `case_events` | list | Ereignisprotokoll |

---

## 4. UI-Flows und Datenoperationen

### 4.1 Akte anlegen/importieren
- **Import:** `show_ra_micro_import()` → `parse_ra_micro_pdf()` → Append zu `DEMO_CASES` + `session_state.imported_cases`
- **Manuell:** Nicht implementiert (nur Demo-Daten)

### 4.2 Forderungskonto
- Buchungen aus `get_all_bookings(case_id)` → kombiniert `DEMO_BOOKINGS` + `session_state.imported_bookings`
- Zinsen: `calculate_interest_for_case()` berechnet live

### 4.3 Dokumente
- `get_all_documents(case_id)` → kombiniert `DEMO_DOCUMENTS` + `session_state.imported_documents`
- PDF-Aufteilung via `split_pdf_by_toc()` → `session_state.document_pdfs`

### 4.4 Vorlagen/Briefkopf
- Word-Upload in `session_state.templates['briefkopf_docx']`
- Platzhalter-Ersetzung: `replace_placeholders_in_docx()`
- Syntax: `[AKTENZEICHEN]`, `[DATUM]`, `[SCHULDNER]`, etc.

### 4.5 Nachrichten
- KI-Entwurf via OpenAI (wenn API Key vorhanden)
- Speicherung nur in Session State

---

## 5. Konfiguration (config/settings.py)

### 5.1 Bestehende Enum-Klassen

| Klasse | Werte |
|--------|-------|
| `UserRole` | ADMIN, RECHTSANWALT, GLAEUBIGERIN, SCHULDNER |
| `DocumentType` | RECHNUNG, VERTRAG, MAHNUNG, MAHNBESCHEID, VOLLSTRECKUNGSBESCHEID, ... |
| `CaseStatus` | OFFEN, MAHNVERFAHREN, VOLLSTRECKUNG, RATENZAHLUNG, ABGESCHLOSSEN, UNEINBRINGLICH |
| `PaymentStatus` | GEMELDET, AKZEPTIERT, ABGELEHNT, VERBUCHT |
| `BookingCategory` | HAUPTFORDERUNG, ZINSEN, RA_GEBUEHREN, NEBENKOSTEN, GERICHTSKOSTEN, VOLLSTRECKUNGSKOSTEN |
| `DunningStatus` | NICHT_BEANTRAGT, MB_BEANTRAGT, MB_ZUGESTELLT, WIDERSPRUCH, VB_BEANTRAGT, VB_ERLASSEN, TITEL_RECHTSKRAEFTIG |
| `EnforcementStatus` | NICHT_BEGONNEN, GV_AUFTRAG, VV_ERHALTEN, PFUEB_BEANTRAGT, ... |
| `PaymentPlanStatus` | ANGEFRAGT, ENTWURF, GEPRUEFT, FREIGEGEBEN, AKTIV, ... |
| `ApprovalStatus` | AUSSTEHEND, GENEHMIGT, ABGELEHNT |

### 5.2 Settings

```python
DATABASE_URL = "sqlite:///./inkassokom.db"  # Nicht genutzt in main.py
STORAGE_TYPE = "local"
STORAGE_PATH = "./storage"
OPENAI_API_KEY = None  # Wird aus st.secrets geladen
```

---

## 6. Identifizierte Lücken und Risiken

### 6.1 Kritische Lücken

| Problem | Auswirkung | Priorität |
|---------|------------|-----------|
| Keine Persistenz | Daten gehen bei Reload verloren | KRITISCH |
| Keine echte Auth | Nur Demo-Buttons, kein Login | HOCH |
| Keine Multi-Tenancy | Alle sehen alles | HOCH |
| Keine Audit-Trail | Keine Nachvollziehbarkeit | MITTEL |
| Lokale Datei-Speicherung | Funktioniert nicht in Streamlit Cloud | HOCH |

### 6.2 Technische Schulden

- SQLAlchemy-Modelle existieren aber werden nicht verwendet
- Doppelte Datenstrukturen (DB-Modelle vs. DEMO_* Dicts)
- Inkonsistente Statusfelder (lowercase in DB, mixed case in UI)
- Platzhalter-Syntax `[...]` vs. empfohlenes `{{...}}`

---

## 7. Empfehlungen für Phase 1

1. **Supabase als Source of Truth** - SQLAlchemy-Modelle für PostgreSQL anpassen
2. **Service-Layer einführen** - Kein direkter DB-Zugriff aus UI
3. **Enums zentralisieren** - Eine Quelle für Status-Werte (Python + DB)
4. **Session State minimieren** - Nur UI-State, keine Business-Daten
5. **Supabase Storage** - Für alle Dokumente und PDFs

---

## 8. Nächste Schritte

- [x] Ist-Analyse abgeschlossen
- [ ] ADR-001: Multi-Tenancy Entscheidung
- [ ] ADR-002: Auth-Strategie
- [ ] ADR-003: Storage-Strategie
- [ ] ADR-004: Job/Worker-Strategie
- [ ] ADR-005: KI-Provider & Datenschutz
