# ADR-003: Dokumenten-Storage Strategie

**Status:** Akzeptiert
**Datum:** 05.01.2026
**Entscheider:** Sven Bryde-Meier

---

## Kontext

InkassoKom verarbeitet verschiedene Dokumente:
- Eingehende PDFs (RA-Micro Import, Uploads)
- Erzeugte Schreiben (Word → PDF)
- Briefköpfe und Vorlagen
- Große Dateien (bis 50 MB pro Dokument)

Anforderungen:
- Streamlit Cloud-kompatibel (kein persistenter lokaler Speicher)
- Sichere Zugriffskontrolle
- Versionierung optional
- Skalierbar

## Entscheidung

**Gewählt: Supabase Storage (ausschließlich)**

### Bucket-Struktur

```
supabase-storage/
├── case-documents/
│   └── {org_id}/{case_id}/{yyyy}/{mm}/{doc_id}_{filename}
├── generated-letters/
│   └── {org_id}/{case_id}/{yyyy}/{mm}/{gen_id}_{type}.pdf
├── templates/
│   ├── {org_id}/letterheads/{letterhead_id}/briefkopf.docx
│   └── {org_id}/letters/{template_id}/template.docx
└── inbox/
    └── {org_id}/{yyyy}/{mm}/{upload_id}_{filename}
```

### Implementation

```python
from supabase import create_client

def upload_document(case_id: str, file_bytes: bytes, filename: str) -> str:
    org_id = get_current_org_id()
    now = datetime.now()
    doc_id = str(uuid.uuid4())
    path = f"{org_id}/{case_id}/{now.year}/{now.month:02d}/{doc_id}_{sanitize(filename)}"

    supabase.storage.from_("case-documents").upload(
        path,
        file_bytes,
        {"content-type": get_mime_type(filename)}
    )
    return path

def get_document_url(path: str, expires_in: int = 3600) -> str:
    return supabase.storage.from_("case-documents").create_signed_url(
        path, expires_in
    )["signedURL"]
```

### Zugriffskontrolle (RLS)

```sql
-- Bucket-Policy: Nur Org-Mitglieder können auf ihre Dokumente zugreifen
CREATE POLICY "org_documents" ON storage.objects
    FOR ALL
    USING (
        bucket_id = 'case-documents' AND
        (storage.foldername(name))[1] IN (
            SELECT org_id::text FROM memberships
            WHERE user_id = auth.uid() AND active = true
        )
    );
```

## Alternativen betrachtet

| Option | Vorteile | Nachteile |
|--------|----------|-----------|
| Lokaler Speicher | Schnell, einfach | Nicht Cloud-fähig |
| S3 direkt | Flexibel | Zusätzlicher Service |
| **Supabase Storage** | RLS-Integration, einfach | Vendor Lock-in |
| Cloudinary | Bildoptimierung | Für PDFs ungeeignet |

## Konsequenzen

- **Positiv**: Einheitliche Lösung, RLS-geschützt, Cloud-ready
- **Negativ**: Abhängigkeit von Supabase; Latenz bei großen Dateien
- **Migration**: Session-State PDFs → Supabase Storage

## Zusätzliche Features

### Duplikaterkennung (SHA-256)
```python
def upload_with_dedup(file_bytes: bytes, ...):
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    existing = db.query(Document).filter_by(hash=file_hash).first()
    if existing:
        return existing.storage_path  # Kein erneuter Upload
    # ... upload
```

### Temporäre Downloads
- Signed URLs mit kurzer TTL (1h) für Viewer
- Längere TTL für Downloads

## Offene Punkte

- [ ] Maximale Dateigröße festlegen (50 MB?)
- [ ] Backup-Strategie für Storage
- [ ] CDN für häufig abgerufene Dokumente?
