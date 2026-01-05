# ADR-002: Authentifizierung und Autorisierung

**Status:** Akzeptiert
**Datum:** 05.01.2026
**Entscheider:** Sven Bryde-Meier

---

## Kontext

Die Anwendung benötigt:
- Sichere Benutzerauthentifizierung
- Rollenbasierte Zugriffssteuerung
- Integration mit Supabase
- Session-Management in Streamlit

## Entscheidung

**Gewählt: Supabase Auth mit Custom Claims**

### Phase 1 (Sofort)
- Supabase Auth für Login/Registration
- JWT-Tokens mit `org_id` und `role` in Custom Claims
- Session via Streamlit + Supabase Client

### Phase 2 (Später)
- Optional: SSO/SAML für Enterprise-Kanzleien
- 2FA für erhöhte Sicherheit

### Architektur

```
┌─────────────┐      ┌───────────────┐      ┌─────────────┐
│  Streamlit  │──────│ Supabase Auth │──────│  PostgreSQL │
│    App      │ JWT  │   (GoTrue)    │ RLS  │   + RLS     │
└─────────────┘      └───────────────┘      └─────────────┘
```

### Implementation

```python
# Streamlit Login
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def login(email: str, password: str):
    response = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })
    st.session_state.user = response.user
    st.session_state.access_token = response.session.access_token

# RLS nutzt auth.uid() und auth.jwt()
```

### Rollen-Matrix

| Rolle | Beschreibung | Berechtigungen |
|-------|--------------|----------------|
| `admin` | Kanzlei-Admin | Alles in der Org |
| `lawyer` | Rechtsanwalt | Akten, Schreiben, Vollstreckung |
| `staff` | Sekretariat | Akten lesen, Termine, Fristen |
| `external_creditor` | Externer Gläubiger | Nur eigene Fälle (lesend) |
| `external_debtor` | Externer Schuldner | Nur eigener Fall (eingeschränkt) |

## Alternativen betrachtet

| Option | Vorteile | Nachteile |
|--------|----------|-----------|
| Eigenes Auth (bcrypt) | Volle Kontrolle | Sicherheitsrisiko, Wartung |
| **Supabase Auth** | Sicher, OOTB, RLS-Integration | Vendor Lock-in |
| Auth0/Clerk | Enterprise Features | Kosten, Komplexität |

## Konsequenzen

- **Positiv**: Sichere, bewährte Auth-Lösung; RLS-Integration
- **Negativ**: Abhängigkeit von Supabase
- **Migration**: Bestehende User-Tabelle wird zu `auth.users` Referenz

## Offene Punkte

- [ ] Magic Link oder Passwort für erste Version?
- [ ] Externe Benutzer: Invite-System oder Self-Registration?
