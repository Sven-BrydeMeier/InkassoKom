# Datenbank-Migrationen

## Supabase Security Alert: Row Level Security (RLS)

### Problem
Supabase meldet: "RLS has not been enabled on tables exposed to PostgREST"

Ohne RLS können **alle authentifizierten Benutzer alle Daten sehen** - ein kritisches Sicherheitsproblem!

### Lösung

#### Schritt 1: Quick Fix (Sofort ausführen!)

Öffnen Sie den **Supabase SQL Editor** und führen Sie aus:

```sql
-- Kopieren Sie den Inhalt von: 000_enable_rls_quick.sql
```

Dieser Script:
- Aktiviert RLS auf allen 19 Tabellen
- Fügt eine einfache "nur authentifizierte Benutzer" Policy hinzu

#### Schritt 2: Vollständige Multi-Tenancy (Empfohlen)

Für echte Datenisolierung zwischen Organisationen:

```sql
-- Kopieren Sie den Inhalt von: 001_enable_rls_all_tables.sql
```

Dieser Script:
- Erstellt Helper-Funktionen für Organisationszugehörigkeit
- Definiert detaillierte Policies für jede Tabelle
- Stellt sicher, dass Benutzer nur Daten ihrer Organisation sehen

### Verifizierung

Nach der Migration, führen Sie diese Query aus:

```sql
SELECT
  schemaname,
  tablename,
  rowsecurity as "RLS Enabled"
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

Alle Tabellen sollten `rowsecurity = true` zeigen.

### Betroffene Tabellen

| Tabelle | Beschreibung |
|---------|--------------|
| organizations | Kanzleien/Workspaces |
| users | Benutzerprofile |
| memberships | Benutzer-Organisation Zuordnung |
| cases | Akten |
| parties | Beteiligte (Gläubiger, Schuldner) |
| case_parties | Akten-Beteiligte Zuordnung |
| claims | Forderungen |
| ledger_bookings | Kontobuchungen |
| payments | Zahlungen |
| payment_allocations | Zahlungszuordnungen |
| documents | Dokumente |
| document_chunks | Dokument-Chunks (RAG) |
| generated_documents | Generierte Dokumente |
| templates | Vorlagen |
| letterheads | Briefköpfe |
| deadlines | Fristen/Termine |
| communications | Kommunikations-Threads |
| messages | Nachrichten |
| audit_logs | Audit-Protokoll |

### Service Role

Für Backend-Operationen (z.B. über Python/SQLAlchemy) verwenden Sie den **Service Role Key**. Dieser umgeht RLS und hat vollen Zugriff.

⚠️ **WICHTIG**: Speichern Sie den Service Role Key niemals im Frontend-Code!
