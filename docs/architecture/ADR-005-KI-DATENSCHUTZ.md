# ADR-005: KI-Provider und Datenschutz

**Status:** Akzeptiert
**Datum:** 05.01.2026
**Entscheider:** Sven Bryde-Meier

---

## Kontext

InkassoKom plant KI-Funktionen:
- **Akten-Chat (RAG)**: Fragen zu Akteninhalten beantworten
- **KI-Schreiben**: Entwürfe basierend auf Musterschreiben generieren
- **Zusammenfassungen**: Dokumente automatisch zusammenfassen

Besondere Anforderungen:
- DSGVO-Konformität
- Anwaltliche Verschwiegenheitspflicht (§ 43a BRAO)
- Mandantengeheimnis
- Nachvollziehbarkeit

## Entscheidung

**Gewählt: OpenAI mit Datenschutz-Maßnahmen**

### Provider-Auswahl

| Kriterium | OpenAI | Anthropic | Azure OpenAI |
|-----------|--------|-----------|--------------|
| API-Qualität | ★★★★★ | ★★★★★ | ★★★★☆ |
| DSGVO (EU-Server) | ❌ (US) | ❌ (US) | ✅ (EU möglich) |
| Daten-Training | Opt-out möglich | Kein Training | Kein Training |
| Kosten | ★★★☆☆ | ★★★☆☆ | ★★★★☆ |

**Empfehlung Phase 1**: OpenAI mit API-Opt-out (keine Daten für Training)
**Empfehlung Phase 2**: Migration zu Azure OpenAI (EU) für volle Compliance

### Datenschutz-Maßnahmen

#### 1. Datenklassifikation

| Kategorie | Beispiele | An KI senden? |
|-----------|-----------|---------------|
| Öffentlich | Gesetzestexte, Formulare | ✅ Ja |
| Intern | Aktenzeichen, Betreff | ✅ Mit Vorsicht |
| Sensibel | Namen, Adressen | ⚠️ Pseudonymisiert |
| Hochsensibel | IBAN, Personalausweis, Gesundheitsdaten | ❌ Niemals |

#### 2. Pseudonymisierung vor Prompt

```python
def prepare_for_ai(text: str, case: Case) -> tuple[str, dict]:
    """Ersetzt sensible Daten durch Platzhalter"""
    replacements = {}

    # Namen ersetzen
    if case.debtor_name:
        placeholder = f"[SCHULDNER_{hash(case.id)[:6]}]"
        text = text.replace(case.debtor_name, placeholder)
        replacements[placeholder] = case.debtor_name

    # IBAN ersetzen
    iban_pattern = r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b'
    text = re.sub(iban_pattern, '[IBAN_MASKIERT]', text)

    return text, replacements

def restore_after_ai(text: str, replacements: dict) -> str:
    """Stellt Originaldaten wieder her"""
    for placeholder, original in replacements.items():
        text = text.replace(placeholder, original)
    return text
```

#### 3. Audit-Trail für KI-Nutzung

```sql
CREATE TABLE ai_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    case_id UUID REFERENCES cases(id),
    request_type TEXT NOT NULL,  -- 'chat', 'draft', 'summary'
    model TEXT NOT NULL,
    prompt_hash TEXT NOT NULL,  -- SHA-256 des Prompts (ohne Klartext!)
    input_tokens INT,
    output_tokens INT,
    latency_ms INT,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
-- KEIN Klartext von Prompts/Responses speichern!
```

#### 4. Einwilligung und Transparenz

- Mandanten-Einwilligung für KI-Nutzung einholen
- KI-generierte Texte als solche kennzeichnen
- Opt-out auf Akten-Ebene ermöglichen

### RAG-Architektur

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Dokumente  │────▶│  Chunking   │────▶│  Embeddings │
│  (Storage)  │     │  (500 Wörter)│     │  (pgvector) │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
       ┌───────────────────────────────────────┘
       ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  User Query │────▶│  Retrieval  │────▶│    LLM      │
│             │     │  (Top-K)    │     │  (Antwort)  │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Datenbank-Schema für RAG

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id),
    case_id UUID NOT NULL REFERENCES cases(id),
    org_id UUID NOT NULL REFERENCES organizations(id),
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    content_length INT NOT NULL,
    page_number INT,
    metadata JSONB,
    embedding vector(1536),  -- OpenAI ada-002
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_embedding ON document_chunks
    USING ivfflat (embedding vector_cosine_ops);
```

## Implementierungs-Roadmap

| Phase | Feature | Datenschutz-Level |
|-------|---------|-------------------|
| 1 | KI-Schreibentwurf (einzelne Akte) | Pseudonymisierung |
| 2 | Akten-Chat (RAG) | Pseudonymisierung + Scope-Filter |
| 3 | Kanzlei-weites RAG | Strikte RLS + Audit |

## Alternativen betrachtet

| Option | Vorteile | Nachteile |
|--------|----------|-----------|
| Kein KI | Kein Risiko | Keine Produktivitätsgewinne |
| Nur lokale LLMs | Volle Kontrolle | Qualität, Kosten |
| **Cloud-KI mit Schutz** | Beste Qualität | Sorgfaltspflichten |

## Konsequenzen

- **Positiv**: KI-Features mit vertretbarem Risiko
- **Negativ**: Zusätzlicher Aufwand für Datenschutz
- **Migration**: Embedding-Infrastruktur muss aufgebaut werden

## Offene Punkte

- [ ] Mandanten-Einwilligungsformular entwerfen
- [ ] Azure OpenAI EU-Setup evaluieren
- [ ] Lokale LLM-Option (Ollama) für sensitive Fälle?
