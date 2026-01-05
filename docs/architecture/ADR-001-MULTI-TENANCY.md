# ADR-001: Multi-Tenancy und Mandanten-/Mehrbenutzerfähigkeit

**Status:** Akzeptiert
**Datum:** 05.01.2026
**Entscheider:** Sven Bryde-Meier

---

## Kontext

InkassoKom wird von Rechtsanwaltskanzleien genutzt, die:
- Mehrere Mitarbeiter haben (Anwälte, Sekretariat)
- Mandanten (Gläubiger) und Schuldner verwalten
- Strikte Datentrennung zwischen Kanzleien benötigen
- Compliance-Anforderungen (BRAO, DSGVO) erfüllen müssen

## Entscheidung

**Gewählt: Organizations/Workspaces mit Memberships**

### Architektur

```
organizations (Kanzlei/Workspace)
    │
    ├── memberships ← users (n:m)
    │       └── role: admin|lawyer|staff|external
    │
    ├── cases
    │       └── alle Geschäftsdaten
    │
    └── templates, letterheads, settings
```

### Begründung

1. **Datentrennung**: Jede Kanzlei sieht nur ihre Daten
2. **Skalierbarkeit**: Später mehrere Kanzleien pro Instanz möglich
3. **Audit**: `org_id` + `user_id` ermöglicht vollständige Nachvollziehbarkeit
4. **RLS-kompatibel**: Supabase Row Level Security basiert auf `org_id`

### Implementation

```sql
-- Alle Business-Tabellen haben org_id
CREATE TABLE cases (
    id UUID PRIMARY KEY,
    org_id UUID NOT NULL REFERENCES organizations(id),
    -- ...
);

-- RLS Policy
CREATE POLICY "org_isolation" ON cases
    USING (org_id IN (
        SELECT org_id FROM memberships
        WHERE user_id = auth.uid() AND active = true
    ));
```

## Alternativen betrachtet

| Option | Vorteile | Nachteile |
|--------|----------|-----------|
| Single-User | Einfacher | Keine Skalierung, keine Teamarbeit |
| Tenant per Database | Maximale Isolation | Aufwändig, teuer |
| **Shared Database + RLS** | Balance aus Sicherheit und Einfachheit | Komplexere Queries |

## Konsequenzen

- **Positiv**: Zukunftssicher, Compliance-konform, Multi-User ready
- **Negativ**: Alle Queries müssen `org_id` berücksichtigen
- **Migration**: Bestehende Modelle um `org_id` erweitern

## Offene Punkte

- [ ] Entscheidung: Externe Benutzer (Gläubiger/Schuldner) als Users oder Parties?
- [ ] Rollen-Granularität: Reicht admin|lawyer|staff oder feiner?
