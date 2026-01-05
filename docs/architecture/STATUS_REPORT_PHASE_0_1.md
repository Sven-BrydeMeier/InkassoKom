# Status Report: Phase 0 & Phase 1 (Beginn)

**Datum:** 05.01.2026
**Version:** v2026.01.05

---

## Zusammenfassung

Phase 0 (Ist-Analyse) ist abgeschlossen. Phase 1 (Supabase Schema) ist begonnen.

### Was ist fertig?

#### Phase 0: Ist-Analyse
- [x] Analyse der bestehenden Datenstrukturen
- [x] Dokumentation der In-Memory Demo-Daten
- [x] Mapping: Bestehende SQLAlchemy-Modelle vs. aktive Nutzung
- [x] Identifizierung von Lücken und technischen Schulden

#### Phase 0: Architecture Decision Records (ADRs)
- [x] ADR-001: Multi-Tenancy (Organizations/Workspaces)
- [x] ADR-002: Auth (Supabase Auth mit Custom Claims)
- [x] ADR-003: Storage (Supabase Storage ausschließlich)
- [x] ADR-004: Jobs/Workers (Phasenweise: synchron → RQ)
- [x] ADR-005: KI/Datenschutz (OpenAI mit Pseudonymisierung)

#### Phase 1: Supabase Schema (begonnen)
- [x] Neue Projektstruktur erstellt (`src/models/`, `migrations/`)
- [x] SQLAlchemy-Modelle für PostgreSQL/Supabase
- [x] Alembic-Konfiguration
- [x] Initial-Migration mit komplettem Schema

### Was ist offen?

#### Phase 1: Verbleibende Aufgaben
- [ ] Supabase-Projekt erstellen und konfigurieren
- [ ] Migration gegen echte Supabase-DB testen
- [ ] RLS-Policies implementieren
- [ ] Service-Layer implementieren
- [ ] Repository-Pattern für Datenzugriff

#### Phase 2-4: Zukünftige Phasen
- [ ] Storage-Umstellung auf Supabase Storage
- [ ] Redis Cache-Integration
- [ ] Audit-Log Implementation
- [ ] KI/RAG-Vorbereitung

---

## Neue Dateien

```
docs/architecture/
├── PHASE_0_IST_ANALYSE.md
├── ADR-001-MULTI-TENANCY.md
├── ADR-002-AUTH.md
├── ADR-003-STORAGE.md
├── ADR-004-JOBS-WORKERS.md
├── ADR-005-KI-DATENSCHUTZ.md
└── STATUS_REPORT_PHASE_0_1.md

src/
├── __init__.py
└── models/
    ├── __init__.py
    ├── base.py
    ├── organization.py
    ├── user.py
    ├── case.py
    ├── claim.py
    ├── document.py
    ├── communication.py
    ├── template.py
    ├── deadline.py
    └── audit.py

migrations/
├── env.py
├── script.py.mako
└── versions/
    └── 20260105_0001_initial_schema.py

alembic.ini
```

---

## Datenbank-Schema

### Kern-Tabellen (implementiert)

| Tabelle | Status | Beschreibung |
|---------|--------|--------------|
| `organizations` | ✅ | Multi-Tenancy Basis |
| `users` | ✅ | Benutzerprofile (Supabase Auth) |
| `memberships` | ✅ | User ↔ Org Zuordnung |
| `parties` | ✅ | Gläubiger, Schuldner, Dritte |
| `cases` | ✅ | Akten/Mandate |
| `case_parties` | ✅ | Akte ↔ Beteiligte |
| `claims` | ✅ | Forderungen |
| `ledger_bookings` | ✅ | Forderungskonto-Buchungen |
| `payments` | ✅ | Zahlungseingänge |
| `payment_allocations` | ✅ | Zahlungszuordnung (§ 367 BGB) |
| `documents` | ✅ | Dokument-Metadaten |
| `document_chunks` | ✅ | RAG-Vorbereitung |
| `templates` | ✅ | Vorlagen |
| `letterheads` | ✅ | Briefköpfe |
| `communications` | ✅ | Kommunikations-Threads |
| `messages` | ✅ | Ein-/Ausgangsnachrichten |
| `generated_documents` | ✅ | Erzeugte Schreiben |
| `deadlines` | ✅ | Fristen/Termine |
| `audit_logs` | ✅ | Änderungshistorie |

---

## Risiken

| Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|--------|-------------------|------------|------------|
| Supabase-Limits (Free Tier) | Mittel | Mittel | Auf Pro-Plan upgraden bei Bedarf |
| Migration der bestehenden Demo-Daten | Niedrig | Niedrig | Seed-Script anpassen |
| RLS-Komplexität | Mittel | Hoch | Schrittweise testen |
| Streamlit Cloud + Supabase Latenz | Niedrig | Mittel | Redis Cache |

---

## Nächste Schritte

1. **Supabase-Projekt erstellen**
   - Projekt in Supabase Dashboard anlegen
   - Connection-Strings in Streamlit Secrets

2. **Migration testen**
   ```bash
   alembic upgrade head
   ```

3. **RLS-Policies definieren**
   - Separate Migration für RLS
   - Policies pro Tabelle

4. **Service-Layer implementieren**
   - `src/services/case_service.py`
   - `src/services/document_service.py`
   - etc.

---

## Empfehlung

Phase 1 kann mit dem aktuellen Stand fortgesetzt werden. Die Modelle und Migration sind bereit für den Test gegen eine echte Supabase-Instanz.

**Priorität:** Supabase-Projekt erstellen und Connection testen.
