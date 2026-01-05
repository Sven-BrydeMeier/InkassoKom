# ADR-004: Asynchrone Jobs und Worker-Strategie

**Status:** Akzeptiert
**Datum:** 05.01.2026
**Entscheider:** Sven Bryde-Meier

---

## Kontext

Bestimmte Operationen sind zu langsam für synchrone Verarbeitung:
- OCR-Extraktion aus PDFs
- Embedding-Generierung für RAG
- KI-Zusammenfassungen
- PDF-Rendering aus Word
- E-Mail-Versand
- Batch-Imports

Anforderungen:
- Nicht-blockierende UI
- Fehlertoleranz und Retry
- Skalierbarkeit
- Status-Tracking

## Entscheidung

**Gewählt: Phasenweise Einführung**

### Phase 1: Synchron mit Feature-Flags
- Alle Operationen synchron (kleine Dateien, wenige User)
- Progress-Indicator in UI
- Feature-Flag für "async_enabled"

### Phase 2: RQ (Redis Queue) Worker
- Separate Worker-Prozesse
- Redis als Message Broker
- Job-Status in PostgreSQL

### Architektur (Phase 2)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Streamlit  │────▶│    Redis    │────▶│  RQ Worker  │
│    App      │     │   Queue     │     │  (OCR/AI)   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                       │
       └───────────────┬───────────────────────┘
                       ▼
              ┌─────────────┐
              │  PostgreSQL │
              │  (job_runs) │
              └─────────────┘
```

### Job-Status Tabelle

```sql
CREATE TABLE job_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    job_type TEXT NOT NULL,  -- 'ocr', 'embedding', 'email', 'pdf_render'
    status TEXT NOT NULL DEFAULT 'pending',  -- pending|running|completed|failed
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    attempts INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
```

### Implementation

```python
# Job erstellen
def enqueue_ocr_job(document_id: str):
    job = JobRun(
        org_id=get_current_org_id(),
        job_type='ocr',
        input_data={'document_id': document_id}
    )
    db.add(job)
    db.commit()

    if settings.ASYNC_ENABLED:
        queue.enqueue(process_ocr, job.id)
    else:
        process_ocr(job.id)  # Synchron

# Worker-Funktion
def process_ocr(job_id: str):
    job = db.get(JobRun, job_id)
    job.status = 'running'
    job.started_at = datetime.now()
    db.commit()

    try:
        # OCR durchführen
        result = run_ocr(job.input_data['document_id'])
        job.output_data = result
        job.status = 'completed'
    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
        job.attempts += 1
    finally:
        job.completed_at = datetime.now()
        db.commit()
```

### Redis Key-Struktur

```
inkassokom:{env}:queue:default        # Standard-Queue
inkassokom:{env}:queue:high           # Prioritäts-Queue
inkassokom:{env}:queue:low            # Hintergrund-Tasks
inkassokom:{env}:lock:job:{job_id}    # Distributed Lock
```

## Alternativen betrachtet

| Option | Vorteile | Nachteile |
|--------|----------|-----------|
| **Nur synchron** | Einfach | Blockiert UI |
| RQ (Redis Queue) | Leichtgewichtig, Python-nativ | Nur Python |
| Celery | Mächtig, bewährt | Komplex, Overhead |
| Supabase Edge Functions | Serverless | Vendor Lock-in, Limits |
| AWS Lambda | Skalierbar | Kosten, Komplexität |

## Konsequenzen

- **Positiv**: Schrittweise Einführung, keine Overengineering
- **Negativ**: Phase 1 kann bei großen Dateien langsam sein
- **Migration**: Job-Logik in eigene Module extrahieren

## Offene Punkte

- [ ] Timeout-Werte pro Job-Typ festlegen
- [ ] Max Retry-Anzahl definieren
- [ ] Dead-Letter-Queue für fehlgeschlagene Jobs?
