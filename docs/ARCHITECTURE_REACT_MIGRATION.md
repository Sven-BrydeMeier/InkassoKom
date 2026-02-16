# InkassoKom - React/FastAPI Architektur

## Inhaltsverzeichnis

1. [Übersicht](#1-übersicht)
2. [Systemarchitektur](#2-systemarchitektur)
3. [Backend (FastAPI)](#3-backend-fastapi)
4. [Frontend (React)](#4-frontend-react)
5. [API-Spezifikation](#5-api-spezifikation)
6. [Datenmodelle](#6-datenmodelle)
7. [Authentifizierung & Autorisierung](#7-authentifizierung--autorisierung)
8. [Datei-Storage](#8-datei-storage)
9. [Migrationsplan](#9-migrationsplan)

---

## 1. Übersicht

### 1.1 Aktuelle Architektur (Streamlit)

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit App                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │  main.py (~4000 Zeilen)                          │   │
│  │  - UI-Logik                                      │   │
│  │  - Business-Logik                                │   │
│  │  - Session State                                 │   │
│  │  - PDF-Parsing                                   │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                              │
│  ┌───────────────────────┼───────────────────────────┐ │
│  │                       ▼                           │ │
│  │   src/models/    src/services/    src/database/   │ │
│  │   (SQLAlchemy)   (Business)       (Connection)    │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   PostgreSQL    │
                  │   (Supabase)    │
                  └─────────────────┘
```

**Probleme:**
- Monolithische main.py mit UI + Business-Logik vermischt
- Session State als "Pseudo-Datenbank"
- Keine echte API-Schicht
- Schwer testbar
- Limitierte UI-Möglichkeiten

### 1.2 Ziel-Architektur (React + FastAPI)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐│
│  │   Pages     │  │ Components  │  │   Hooks     │  │   State (Zustand)   ││
│  │  - Dashboard│  │ - CaseCard  │  │ - useCase   │  │ - cases             ││
│  │  - Cases    │  │ - DocViewer │  │ - useDocs   │  │ - documents         ││
│  │  - Import   │  │ - PDFViewer │  │ - useAuth   │  │ - auth              ││
│  │  - Messages │  │ - Forms     │  │ - useApi    │  │ - ui                ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘│
│                                    │                                        │
│                         ┌──────────┴──────────┐                             │
│                         │   API Client        │                             │
│                         │   (React Query +    │                             │
│                         │    Axios/Fetch)     │                             │
│                         └──────────┬──────────┘                             │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │ HTTPS / REST
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (FastAPI)                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         API Routes                                   │   │
│  │  /api/v1/cases      /api/v1/documents    /api/v1/auth               │   │
│  │  /api/v1/bookings   /api/v1/import       /api/v1/messages           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐ │
│  │                     Services Layer                                    │ │
│  │  CaseService    DocumentService    ImportService    MessageService    │ │
│  └─────────────────────────────────┼─────────────────────────────────────┘ │
│                                    │                                        │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐ │
│  │                     Domain Layer                                      │ │
│  │  parser_akten.py   pdf_splitter.py   email_parser.py                  │ │
│  └─────────────────────────────────┼─────────────────────────────────────┘ │
│                                    │                                        │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐ │
│  │                  Data Access Layer (SQLAlchemy)                       │ │
│  │  models/case.py   models/document.py   models/claim.py                │ │
│  └─────────────────────────────────┼─────────────────────────────────────┘ │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
           ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
           │ PostgreSQL  │   │  Supabase   │   │   Redis     │
           │ (Supabase)  │   │  Storage    │   │  (Cache)    │
           └─────────────┘   └─────────────┘   └─────────────┘
```

---

## 2. Systemarchitektur

### 2.1 Verzeichnisstruktur

```
inkassokom/
├── backend/                          # FastAPI Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI App Entry
│   │   ├── config.py                 # Settings (Pydantic)
│   │   │
│   │   ├── api/                      # API Layer
│   │   │   ├── __init__.py
│   │   │   ├── deps.py               # Dependencies (Auth, DB)
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py         # Main Router
│   │   │       ├── cases.py          # /cases Endpoints
│   │   │       ├── documents.py      # /documents Endpoints
│   │   │       ├── import_.py        # /import Endpoints
│   │   │       ├── bookings.py       # /bookings Endpoints
│   │   │       ├── messages.py       # /messages Endpoints
│   │   │       ├── auth.py           # /auth Endpoints
│   │   │       └── templates.py      # /templates Endpoints
│   │   │
│   │   ├── core/                     # Core Utilities
│   │   │   ├── __init__.py
│   │   │   ├── security.py           # JWT, Hashing
│   │   │   ├── exceptions.py         # Custom Exceptions
│   │   │   └── logging.py            # Logging Config
│   │   │
│   │   ├── services/                 # Business Logic
│   │   │   ├── __init__.py
│   │   │   ├── case_service.py
│   │   │   ├── document_service.py
│   │   │   ├── import_service.py
│   │   │   ├── booking_service.py
│   │   │   ├── message_service.py
│   │   │   └── wiedervorlage_service.py
│   │   │
│   │   ├── domain/                   # Domain Logic (Parser etc.)
│   │   │   ├── __init__.py
│   │   │   ├── parser_akten.py       # RA-Micro Parser
│   │   │   ├── pdf_splitter.py       # PDF Splitting
│   │   │   ├── email_parser.py       # Email Parsing
│   │   │   └── rvg_calculator.py     # Gebührenrechner
│   │   │
│   │   ├── models/                   # SQLAlchemy Models
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── case.py
│   │   │   ├── document.py
│   │   │   ├── claim.py
│   │   │   ├── communication.py
│   │   │   ├── user.py
│   │   │   └── organization.py
│   │   │
│   │   ├── schemas/                  # Pydantic Schemas
│   │   │   ├── __init__.py
│   │   │   ├── case.py
│   │   │   ├── document.py
│   │   │   ├── import_.py
│   │   │   ├── booking.py
│   │   │   └── auth.py
│   │   │
│   │   └── db/                       # Database
│   │       ├── __init__.py
│   │       ├── session.py
│   │       └── init_db.py
│   │
│   ├── tests/                        # Backend Tests
│   │   ├── conftest.py
│   │   ├── test_cases.py
│   │   ├── test_import.py
│   │   └── test_parser.py
│   │
│   ├── alembic/                      # Migrations
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/                         # React Frontend
│   ├── src/
│   │   ├── main.tsx                  # Entry Point
│   │   ├── App.tsx                   # Root Component
│   │   ├── vite-env.d.ts
│   │   │
│   │   ├── api/                      # API Client
│   │   │   ├── client.ts             # Axios Instance
│   │   │   ├── cases.ts              # Case API
│   │   │   ├── documents.ts          # Document API
│   │   │   ├── import.ts             # Import API
│   │   │   └── auth.ts               # Auth API
│   │   │
│   │   ├── components/               # UI Components
│   │   │   ├── common/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── DataTable.tsx
│   │   │   │   └── LoadingSpinner.tsx
│   │   │   ├── cases/
│   │   │   │   ├── CaseCard.tsx
│   │   │   │   ├── CaseList.tsx
│   │   │   │   ├── CaseDetail.tsx
│   │   │   │   └── CaseForm.tsx
│   │   │   ├── documents/
│   │   │   │   ├── DocumentList.tsx
│   │   │   │   ├── DocumentViewer.tsx
│   │   │   │   ├── PDFViewer.tsx
│   │   │   │   └── DocumentUpload.tsx
│   │   │   ├── import/
│   │   │   │   ├── RAMicroImport.tsx
│   │   │   │   ├── PDFPreview.tsx
│   │   │   │   └── ImportForm.tsx
│   │   │   ├── bookings/
│   │   │   │   ├── BookingTable.tsx
│   │   │   │   └── BookingForm.tsx
│   │   │   └── layout/
│   │   │       ├── Sidebar.tsx
│   │   │       ├── Header.tsx
│   │   │       └── Layout.tsx
│   │   │
│   │   ├── pages/                    # Page Components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── CasesPage.tsx
│   │   │   ├── CaseDetailPage.tsx
│   │   │   ├── ImportPage.tsx
│   │   │   ├── MessagesPage.tsx
│   │   │   ├── DunningPage.tsx
│   │   │   ├── EnforcementPage.tsx
│   │   │   ├── TemplatesPage.tsx
│   │   │   ├── SettingsPage.tsx
│   │   │   └── LoginPage.tsx
│   │   │
│   │   ├── hooks/                    # Custom Hooks
│   │   │   ├── useCase.ts
│   │   │   ├── useCases.ts
│   │   │   ├── useDocuments.ts
│   │   │   ├── useImport.ts
│   │   │   ├── useBookings.ts
│   │   │   └── useAuth.ts
│   │   │
│   │   ├── store/                    # Zustand State
│   │   │   ├── index.ts
│   │   │   ├── authStore.ts
│   │   │   ├── caseStore.ts
│   │   │   ├── uiStore.ts
│   │   │   └── notificationStore.ts
│   │   │
│   │   ├── types/                    # TypeScript Types
│   │   │   ├── index.ts
│   │   │   ├── case.ts
│   │   │   ├── document.ts
│   │   │   ├── booking.ts
│   │   │   └── api.ts
│   │   │
│   │   ├── utils/                    # Utilities
│   │   │   ├── format.ts             # Date/Currency Formatting
│   │   │   ├── validation.ts
│   │   │   └── constants.ts
│   │   │
│   │   └── styles/                   # Global Styles
│   │       └── globals.css
│   │
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── Dockerfile
│
├── docker-compose.yml
├── docker-compose.dev.yml
└── README.md
```

### 2.2 Technologie-Stack

| Komponente | Technologie | Begründung |
|------------|-------------|------------|
| **Frontend Framework** | React 18 | Komponenten-basiert, großes Ökosystem |
| **Build Tool** | Vite | Schnelle Entwicklung, ESM-native |
| **Styling** | Tailwind CSS | Utility-first, konsistentes Design |
| **UI Components** | shadcn/ui | Kopierbare, anpassbare Komponenten |
| **State Management** | Zustand | Einfach, leichtgewichtig, TypeScript |
| **Data Fetching** | TanStack Query | Caching, Refetching, Optimistic Updates |
| **Routing** | React Router v6 | Standard für React SPAs |
| **Forms** | React Hook Form | Performance, Validation |
| **PDF Viewer** | react-pdf | PDF.js Wrapper |
| **Backend Framework** | FastAPI | Async, Auto-Docs, Pydantic |
| **ORM** | SQLAlchemy 2.0 | Bestehende Models weiterverwenden |
| **Database** | PostgreSQL (Supabase) | Bereits vorhanden |
| **File Storage** | Supabase Storage | S3-kompatibel, RLS |
| **Auth** | Supabase Auth | JWT, Row Level Security |
| **Cache** | Redis | Session, API Cache |

---

## 3. Backend (FastAPI)

### 3.1 Hauptdatei (main.py)

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.api.v1.router import api_router
from app.db.session import engine
from app.models.base import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(
    title="InkassoKom API",
    description="Inkasso-Plattform für Rechtsanwälte",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### 3.2 Konfiguration

```python
# backend/app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_NAME: str = "InkassoKom"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Storage
    STORAGE_BUCKET: str = "case-documents"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

### 3.3 API Router

```python
# backend/app/api/v1/router.py
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    cases,
    documents,
    bookings,
    import_,
    messages,
    templates,
    wiedervorlagen,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(import_.router, prefix="/import", tags=["import"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(wiedervorlagen.router, prefix="/wiedervorlagen", tags=["wiedervorlagen"])
```

### 3.4 Beispiel: Cases Router

```python
# backend/app/api/v1/cases.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.schemas.case import (
    CaseCreate,
    CaseUpdate,
    CaseResponse,
    CaseListResponse,
    CaseStatistics,
)
from app.services.case_service import CaseService
from app.models.user import User

router = APIRouter()

@router.get("", response_model=CaseListResponse)
async def list_cases(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in case number/subject"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all cases for the current organization."""
    service = CaseService(db)
    cases, total = await service.get_cases(
        organization_id=current_user.organization_id,
        status=status,
        search=search,
        skip=skip,
        limit=limit,
    )
    return CaseListResponse(
        items=cases,
        total=total,
        skip=skip,
        limit=limit,
    )

@router.get("/statistics", response_model=CaseStatistics)
async def get_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get case statistics for dashboard."""
    service = CaseService(db)
    return await service.get_statistics(current_user.organization_id)

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single case by ID."""
    service = CaseService(db)
    case = await service.get_case(case_id, current_user.organization_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.post("", response_model=CaseResponse, status_code=201)
async def create_case(
    data: CaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new case."""
    service = CaseService(db)
    return await service.create_case(
        data=data,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
    )

@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: UUID,
    data: CaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update case fields."""
    service = CaseService(db)
    case = await service.update_case(case_id, data, current_user.organization_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.delete("/{case_id}", status_code=204)
async def delete_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a case."""
    service = CaseService(db)
    success = await service.delete_case(case_id, current_user.organization_id)
    if not success:
        raise HTTPException(status_code=404, detail="Case not found")
```

### 3.5 Beispiel: Import Router

```python
# backend/app/api/v1/import_.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.api.deps import get_db, get_current_user
from app.schemas.import_ import (
    ImportPreviewResponse,
    ImportConfirmRequest,
    ImportResultResponse,
)
from app.services.import_service import ImportService
from app.models.user import User

router = APIRouter()

@router.post("/ra-micro/preview", response_model=ImportPreviewResponse)
async def preview_ra_micro_import(
    file: UploadFile = File(..., description="RA-Micro PDF file"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Preview RA-Micro PDF import.

    Parses the PDF and returns extracted data for review before import.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()
    service = ImportService(db)

    try:
        preview = await service.preview_ra_micro_import(
            pdf_bytes=content,
            filename=file.filename,
        )
        return preview
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse PDF: {str(e)}")

@router.post("/ra-micro/confirm", response_model=ImportResultResponse)
async def confirm_ra_micro_import(
    request: ImportConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Confirm and execute RA-Micro import.

    Uses the edited data from preview to create the case.
    """
    service = ImportService(db)

    result = await service.execute_import(
        preview_id=request.preview_id,
        edited_data=request.edited_data,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
    )

    return result

@router.post("/zip/preview")
async def preview_zip_import(
    file: UploadFile = File(...),
    case_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preview ZIP archive contents before import."""
    # Implementation...
    pass
```

### 3.6 Pydantic Schemas

```python
# backend/app/schemas/case.py
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum

class CaseStatus(str, Enum):
    OFFEN = "offen"
    MAHNVERFAHREN = "mahnverfahren"
    VOLLSTRECKUNG = "vollstreckung"
    RATENZAHLUNG = "ratenzahlung"
    ABGESCHLOSSEN = "abgeschlossen"
    UNEINBRINGLICH = "uneinbringlich"

class DunningStatus(str, Enum):
    NICHT_BEANTRAGT = "nicht_beantragt"
    MB_BEANTRAGT = "mb_beantragt"
    MB_ZUGESTELLT = "mb_zugestellt"
    WIDERSPRUCH = "widerspruch"
    VB_BEANTRAGT = "vb_beantragt"
    VB_ERLASSEN = "vb_erlassen"
    TITEL_RECHTSKRAEFTIG = "titel_rechtskraeftig"

class PartyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class PartyResponse(PartyBase):
    id: UUID
    party_type: str

    class Config:
        from_attributes = True

class CaseBase(BaseModel):
    case_no: str = Field(..., min_length=1, max_length=50, description="Aktenzeichen")
    subject: Optional[str] = Field(None, max_length=500)
    principal: float = Field(..., ge=0, description="Hauptforderung in EUR")
    interest_rate: float = Field(5.0, ge=0, le=100)
    due_date: Optional[date] = None

class CaseCreate(CaseBase):
    creditor_name: str
    creditor_address: Optional[str] = None
    debtor_name: str
    debtor_address: Optional[str] = None

class CaseUpdate(BaseModel):
    case_no: Optional[str] = None
    subject: Optional[str] = None
    status: Optional[CaseStatus] = None
    dunning_status: Optional[DunningStatus] = None
    principal: Optional[float] = None
    interest_rate: Optional[float] = None

class CaseResponse(CaseBase):
    id: UUID
    status: CaseStatus
    dunning_status: DunningStatus
    enforcement_status: str
    creditor: PartyResponse
    debtor: PartyResponse
    total_soll: float
    total_haben: float
    open_balance: float
    document_count: int
    created_at: datetime

    class Config:
        from_attributes = True

class CaseListResponse(BaseModel):
    items: List[CaseResponse]
    total: int
    skip: int
    limit: int

class CaseStatistics(BaseModel):
    total_cases: int
    by_status: dict[str, int]
    total_principal: float
    total_collected: float
    open_balance: float
```

```python
# backend/app/schemas/import_.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date

class ExtractedParty(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class ExtractedDocument(BaseModel):
    id: str
    name: str
    type: str
    category: str
    page: int
    end_page: int
    page_count: int

class ExtractedBooking(BaseModel):
    date: date
    type: str  # 'S' or 'H'
    amount: float
    category: str
    description: str

class ImportPreviewResponse(BaseModel):
    preview_id: str  # Temporary ID to reference this preview
    success: bool
    aktenzeichen: Optional[str]
    creditor: ExtractedParty
    debtor: ExtractedParty
    principal: float
    documents: List[ExtractedDocument]
    bookings: List[ExtractedBooking]
    status: str
    dunning_status: str
    num_pages: int
    raw_text_preview: str
    pdf_preview_url: Optional[str] = None  # Temporary URL for PDF preview

class EditedImportData(BaseModel):
    aktenzeichen: str
    creditor_name: str
    creditor_address: Optional[str]
    debtor_name: str
    debtor_address: Optional[str]
    principal: float
    documents: List[ExtractedDocument]
    bookings: List[ExtractedBooking]

class ImportConfirmRequest(BaseModel):
    preview_id: str
    edited_data: EditedImportData

class ImportResultResponse(BaseModel):
    success: bool
    case_id: str
    case_no: str
    document_count: int
    message: str
```

### 3.7 Services

```python
# backend/app/services/import_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID, uuid4
import tempfile
import os

from app.domain.parser_akten import extract_case_data
from app.domain.pdf_splitter import split_pdf_by_pages
from app.services.case_service import CaseService
from app.services.document_service import DocumentService
from app.schemas.import_ import (
    ImportPreviewResponse,
    ExtractedParty,
    ExtractedDocument,
    ExtractedBooking,
    EditedImportData,
    ImportResultResponse,
)

# Temporary storage for preview data (use Redis in production)
_preview_cache: dict = {}

class ImportService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.case_service = CaseService(db)
        self.document_service = DocumentService(db)

    async def preview_ra_micro_import(
        self,
        pdf_bytes: bytes,
        filename: str,
    ) -> ImportPreviewResponse:
        """Parse RA-Micro PDF and return preview data."""

        # Extract data using existing parser
        case_data = extract_case_data(pdf_bytes, filename=filename)

        # Generate preview ID
        preview_id = str(uuid4())

        # Store PDF bytes temporarily
        _preview_cache[preview_id] = {
            'pdf_bytes': pdf_bytes,
            'filename': filename,
            'case_data': case_data,
        }

        # Extract parties
        cover = case_data.get('cover', {})
        claimant = cover.get('claimant', {})
        defendant = cover.get('defendant', {})

        creditor = ExtractedParty(
            name=claimant.get('name'),
            address=self._format_address(claimant),
            email=claimant.get('email', [None])[0] if claimant.get('email') else None,
            phone=claimant.get('telefon', [None])[0] if claimant.get('telefon') else None,
        )

        debtor = ExtractedParty(
            name=defendant.get('name'),
            address=self._format_address(defendant),
            email=defendant.get('email', [None])[0] if defendant.get('email') else None,
            phone=defendant.get('telefon', [None])[0] if defendant.get('telefon') else None,
        )

        # Extract principal from money data
        money = case_data.get('money', {})
        principal_data = money.get('principal', {})
        principal = principal_data.get('betrag', 0.0) if isinstance(principal_data, dict) else 0.0

        # Build response
        return ImportPreviewResponse(
            preview_id=preview_id,
            success=True,
            aktenzeichen=cover.get('aktenzeichen'),
            creditor=creditor,
            debtor=debtor,
            principal=principal,
            documents=[],  # Extract from TOC
            bookings=[],   # Extract from ledger
            status='offen',
            dunning_status='nicht_beantragt',
            num_pages=len(case_data.get('pages', [])),
            raw_text_preview=case_data.get('full_text', '')[:3000],
        )

    async def execute_import(
        self,
        preview_id: str,
        edited_data: EditedImportData,
        organization_id: UUID,
        created_by: UUID,
    ) -> ImportResultResponse:
        """Execute the import with edited data."""

        # Get cached preview data
        preview = _preview_cache.get(preview_id)
        if not preview:
            raise ValueError("Preview expired or not found")

        pdf_bytes = preview['pdf_bytes']

        # Create case
        case = await self.case_service.create_case(
            organization_id=organization_id,
            case_no=edited_data.aktenzeichen,
            creditor_name=edited_data.creditor_name,
            creditor_address=edited_data.creditor_address,
            debtor_name=edited_data.debtor_name,
            debtor_address=edited_data.debtor_address,
            principal=edited_data.principal,
            imported=True,
            import_source='ra-micro',
            import_filename=preview['filename'],
        )

        # Split and upload documents
        doc_count = 0
        for doc in edited_data.documents:
            doc_pdf = split_pdf_by_pages(
                pdf_bytes,
                doc.page - 1,
                doc.end_page - 1,
            )
            if doc_pdf:
                await self.document_service.upload_document(
                    case_id=case.id,
                    organization_id=organization_id,
                    filename=f"{doc.name}.pdf",
                    content=doc_pdf,
                    document_type=doc.type,
                    category=doc.category,
                )
                doc_count += 1

        # Add bookings
        for booking in edited_data.bookings:
            await self.case_service.add_booking(
                case_id=case.id,
                booking_date=booking.date,
                booking_type=booking.type,
                amount=booking.amount,
                category=booking.category,
                description=booking.description,
            )

        # Clean up preview cache
        del _preview_cache[preview_id]

        return ImportResultResponse(
            success=True,
            case_id=str(case.id),
            case_no=edited_data.aktenzeichen,
            document_count=doc_count,
            message=f"Akte {edited_data.aktenzeichen} erfolgreich importiert",
        )

    def _format_address(self, party: dict) -> Optional[str]:
        parts = []
        if party.get('street'):
            parts.append(party['street'])
        if party.get('plz') and party.get('ort'):
            parts.append(f"{party['plz']} {party['ort']}")
        return '\n'.join(parts) if parts else None
```

---

## 4. Frontend (React)

### 4.1 Entry Point

```tsx
// frontend/src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './styles/globals.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
```

### 4.2 App Component

```tsx
// frontend/src/App.tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/layout/Layout'
import LoginPage from './pages/LoginPage'
import Dashboard from './pages/Dashboard'
import CasesPage from './pages/CasesPage'
import CaseDetailPage from './pages/CaseDetailPage'
import ImportPage from './pages/ImportPage'
import MessagesPage from './pages/MessagesPage'
import DunningPage from './pages/DunningPage'
import EnforcementPage from './pages/EnforcementPage'
import TemplatesPage from './pages/TemplatesPage'
import SettingsPage from './pages/SettingsPage'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/*"
        element={
          <PrivateRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/cases" element={<CasesPage />} />
                <Route path="/cases/:id" element={<CaseDetailPage />} />
                <Route path="/import" element={<ImportPage />} />
                <Route path="/messages" element={<MessagesPage />} />
                <Route path="/dunning" element={<DunningPage />} />
                <Route path="/enforcement" element={<EnforcementPage />} />
                <Route path="/templates" element={<TemplatesPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </Layout>
          </PrivateRoute>
        }
      />
    </Routes>
  )
}
```

### 4.3 API Client

```typescript
// frontend/src/api/client.ts
import axios, { AxiosError, AxiosInstance } from 'axios'
import { useAuthStore } from '../store/authStore'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for auth
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor for errors
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
```

```typescript
// frontend/src/api/cases.ts
import { apiClient } from './client'
import type {
  Case,
  CaseCreate,
  CaseUpdate,
  CaseListResponse,
  CaseStatistics
} from '../types/case'

export const casesApi = {
  list: async (params?: {
    status?: string
    search?: string
    skip?: number
    limit?: number
  }): Promise<CaseListResponse> => {
    const { data } = await apiClient.get('/cases', { params })
    return data
  },

  get: async (id: string): Promise<Case> => {
    const { data } = await apiClient.get(`/cases/${id}`)
    return data
  },

  create: async (caseData: CaseCreate): Promise<Case> => {
    const { data } = await apiClient.post('/cases', caseData)
    return data
  },

  update: async (id: string, updates: CaseUpdate): Promise<Case> => {
    const { data } = await apiClient.patch(`/cases/${id}`, updates)
    return data
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/cases/${id}`)
  },

  getStatistics: async (): Promise<CaseStatistics> => {
    const { data } = await apiClient.get('/cases/statistics')
    return data
  },
}
```

```typescript
// frontend/src/api/import.ts
import { apiClient } from './client'
import type { ImportPreview, ImportConfirm, ImportResult } from '../types/import'

export const importApi = {
  previewRAMicro: async (file: File): Promise<ImportPreview> => {
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await apiClient.post('/import/ra-micro/preview', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  confirmRAMicro: async (request: ImportConfirm): Promise<ImportResult> => {
    const { data } = await apiClient.post('/import/ra-micro/confirm', request)
    return data
  },
}
```

### 4.4 Hooks

```typescript
// frontend/src/hooks/useCases.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { casesApi } from '../api/cases'
import type { CaseCreate, CaseUpdate } from '../types/case'

export function useCases(params?: {
  status?: string
  search?: string
  skip?: number
  limit?: number
}) {
  return useQuery({
    queryKey: ['cases', params],
    queryFn: () => casesApi.list(params),
  })
}

export function useCase(id: string) {
  return useQuery({
    queryKey: ['case', id],
    queryFn: () => casesApi.get(id),
    enabled: !!id,
  })
}

export function useCaseStatistics() {
  return useQuery({
    queryKey: ['caseStatistics'],
    queryFn: () => casesApi.getStatistics(),
  })
}

export function useCreateCase() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CaseCreate) => casesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['caseStatistics'] })
    },
  })
}

export function useUpdateCase() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CaseUpdate }) =>
      casesApi.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['case', id] })
    },
  })
}
```

```typescript
// frontend/src/hooks/useImport.ts
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { importApi } from '../api/import'
import type { ImportPreview, EditedImportData } from '../types/import'

export function useRAMicroImport() {
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [editedData, setEditedData] = useState<EditedImportData | null>(null)

  const previewMutation = useMutation({
    mutationFn: importApi.previewRAMicro,
    onSuccess: (data) => {
      setPreview(data)
      // Initialize edited data with preview values
      setEditedData({
        aktenzeichen: data.aktenzeichen || '',
        creditor_name: data.creditor.name || '',
        creditor_address: data.creditor.address || '',
        debtor_name: data.debtor.name || '',
        debtor_address: data.debtor.address || '',
        principal: data.principal,
        documents: data.documents,
        bookings: data.bookings,
      })
    },
  })

  const confirmMutation = useMutation({
    mutationFn: () => {
      if (!preview || !editedData) {
        throw new Error('No preview data')
      }
      return importApi.confirmRAMicro({
        preview_id: preview.preview_id,
        edited_data: editedData,
      })
    },
  })

  const updateField = <K extends keyof EditedImportData>(
    field: K,
    value: EditedImportData[K]
  ) => {
    setEditedData((prev) => prev ? { ...prev, [field]: value } : null)
  }

  const reset = () => {
    setPreview(null)
    setEditedData(null)
  }

  return {
    preview,
    editedData,
    updateField,
    reset,
    uploadFile: previewMutation.mutate,
    isUploading: previewMutation.isPending,
    uploadError: previewMutation.error,
    confirmImport: confirmMutation.mutate,
    isConfirming: confirmMutation.isPending,
    confirmError: confirmMutation.error,
    importResult: confirmMutation.data,
  }
}
```

### 4.5 Store (Zustand)

```typescript
// frontend/src/store/authStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  email: string
  name: string
  role: string
  organization_id: string
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
  login: (token: string, user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      login: (token, user) =>
        set({ token, user, isAuthenticated: true }),
      logout: () =>
        set({ token: null, user: null, isAuthenticated: false }),
    }),
    {
      name: 'auth-storage',
    }
  )
)
```

```typescript
// frontend/src/store/uiStore.ts
import { create } from 'zustand'

interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration?: number
}

interface UIState {
  sidebarOpen: boolean
  toggleSidebar: () => void
  notifications: Notification[]
  addNotification: (notification: Omit<Notification, 'id'>) => void
  removeNotification: (id: string) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  notifications: [],
  addNotification: (notification) =>
    set((state) => ({
      notifications: [
        ...state.notifications,
        { ...notification, id: crypto.randomUUID() },
      ],
    })),
  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),
}))
```

### 4.6 TypeScript Types

```typescript
// frontend/src/types/case.ts
export type CaseStatus =
  | 'offen'
  | 'mahnverfahren'
  | 'vollstreckung'
  | 'ratenzahlung'
  | 'abgeschlossen'
  | 'uneinbringlich'

export type DunningStatus =
  | 'nicht_beantragt'
  | 'mb_beantragt'
  | 'mb_zugestellt'
  | 'widerspruch'
  | 'vb_beantragt'
  | 'vb_erlassen'
  | 'titel_rechtskraeftig'

export interface Party {
  id: string
  name: string
  address?: string
  email?: string
  phone?: string
  party_type: 'natural_person' | 'legal_entity'
}

export interface Case {
  id: string
  case_no: string
  subject?: string
  status: CaseStatus
  dunning_status: DunningStatus
  enforcement_status: string
  creditor: Party
  debtor: Party
  principal: number
  interest_rate: number
  due_date?: string
  total_soll: number
  total_haben: number
  open_balance: number
  document_count: number
  created_at: string
}

export interface CaseCreate {
  case_no: string
  subject?: string
  principal: number
  interest_rate?: number
  due_date?: string
  creditor_name: string
  creditor_address?: string
  debtor_name: string
  debtor_address?: string
}

export interface CaseUpdate {
  case_no?: string
  subject?: string
  status?: CaseStatus
  dunning_status?: DunningStatus
  principal?: number
  interest_rate?: number
}

export interface CaseListResponse {
  items: Case[]
  total: number
  skip: number
  limit: number
}

export interface CaseStatistics {
  total_cases: number
  by_status: Record<string, number>
  total_principal: number
  total_collected: number
  open_balance: number
}
```

```typescript
// frontend/src/types/import.ts
export interface ExtractedParty {
  name?: string
  address?: string
  email?: string
  phone?: string
}

export interface ExtractedDocument {
  id: string
  name: string
  type: string
  category: string
  page: number
  end_page: number
  page_count: number
}

export interface ExtractedBooking {
  date: string
  type: 'S' | 'H'
  amount: number
  category: string
  description: string
}

export interface ImportPreview {
  preview_id: string
  success: boolean
  aktenzeichen?: string
  creditor: ExtractedParty
  debtor: ExtractedParty
  principal: number
  documents: ExtractedDocument[]
  bookings: ExtractedBooking[]
  status: string
  dunning_status: string
  num_pages: number
  raw_text_preview: string
  pdf_preview_url?: string
}

export interface EditedImportData {
  aktenzeichen: string
  creditor_name: string
  creditor_address?: string
  debtor_name: string
  debtor_address?: string
  principal: number
  documents: ExtractedDocument[]
  bookings: ExtractedBooking[]
}

export interface ImportConfirm {
  preview_id: string
  edited_data: EditedImportData
}

export interface ImportResult {
  success: boolean
  case_id: string
  case_no: string
  document_count: number
  message: string
}
```

### 4.7 Beispiel: Import Page

```tsx
// frontend/src/pages/ImportPage.tsx
import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { useRAMicroImport } from '../hooks/useImport'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Input } from '../components/common/Input'
import { TextArea } from '../components/common/TextArea'
import { PDFViewer } from '../components/documents/PDFViewer'
import { formatCurrency } from '../utils/format'
import { useUIStore } from '../store/uiStore'

export default function ImportPage() {
  const navigate = useNavigate()
  const addNotification = useUIStore((state) => state.addNotification)

  const {
    preview,
    editedData,
    updateField,
    reset,
    uploadFile,
    isUploading,
    confirmImport,
    isConfirming,
    importResult,
  } = useRAMicroImport()

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        uploadFile(acceptedFiles[0])
      }
    },
    [uploadFile]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
  })

  const handleConfirm = () => {
    confirmImport(undefined, {
      onSuccess: (result) => {
        addNotification({
          type: 'success',
          message: `Akte ${result.case_no} erfolgreich importiert`,
        })
        navigate(`/cases/${result.case_id}`)
      },
      onError: (error) => {
        addNotification({
          type: 'error',
          message: `Import fehlgeschlagen: ${error.message}`,
        })
      },
    })
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">RA-Micro Aktenimport</h1>

      {!preview ? (
        // Upload Area
        <Card>
          <div
            {...getRootProps()}
            className={`
              border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
              transition-colors duration-200
              ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
              ${isUploading ? 'opacity-50 pointer-events-none' : ''}
            `}
          >
            <input {...getInputProps()} />
            {isUploading ? (
              <div className="flex flex-col items-center">
                <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" />
                <p className="mt-4 text-gray-600">PDF wird analysiert...</p>
              </div>
            ) : (
              <>
                <p className="text-lg text-gray-600">
                  {isDragActive
                    ? 'PDF hier ablegen...'
                    : 'PDF-Datei hierher ziehen oder klicken zum Auswählen'}
                </p>
                <p className="mt-2 text-sm text-gray-400">
                  Unterstützt: RA-Micro Gesamt-PDF Export
                </p>
              </>
            )}
          </div>
        </Card>
      ) : (
        // Preview & Edit Form
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Edit Form */}
          <div className="space-y-6">
            <Card title="Akten-Informationen">
              <div className="space-y-4">
                <Input
                  label="Aktenzeichen"
                  value={editedData?.aktenzeichen || ''}
                  onChange={(e) => updateField('aktenzeichen', e.target.value)}
                />

                <div className="border-t pt-4">
                  <h4 className="font-medium mb-3">Gläubiger (Mandant)</h4>
                  <Input
                    label="Name"
                    value={editedData?.creditor_name || ''}
                    onChange={(e) => updateField('creditor_name', e.target.value)}
                  />
                  <TextArea
                    label="Adresse"
                    value={editedData?.creditor_address || ''}
                    onChange={(e) => updateField('creditor_address', e.target.value)}
                    rows={2}
                    className="mt-3"
                  />
                </div>

                <div className="border-t pt-4">
                  <h4 className="font-medium mb-3">Schuldner (Gegner)</h4>
                  <Input
                    label="Name"
                    value={editedData?.debtor_name || ''}
                    onChange={(e) => updateField('debtor_name', e.target.value)}
                  />
                  <TextArea
                    label="Adresse"
                    value={editedData?.debtor_address || ''}
                    onChange={(e) => updateField('debtor_address', e.target.value)}
                    rows={2}
                    className="mt-3"
                  />
                </div>

                <div className="border-t pt-4">
                  <h4 className="font-medium mb-3">Forderung</h4>
                  <Input
                    label="Hauptforderung (€)"
                    type="number"
                    step="0.01"
                    min="0"
                    value={editedData?.principal || 0}
                    onChange={(e) => updateField('principal', parseFloat(e.target.value) || 0)}
                  />
                </div>
              </div>
            </Card>

            {/* Summary */}
            <Card title="Zusammenfassung">
              <div className="space-y-2 text-sm">
                <p>
                  <span className="text-gray-500">Aktenzeichen:</span>{' '}
                  <strong>{editedData?.aktenzeichen}</strong>
                </p>
                <p>
                  <span className="text-gray-500">Gläubiger:</span>{' '}
                  <strong>{editedData?.creditor_name}</strong>
                </p>
                <p>
                  <span className="text-gray-500">Schuldner:</span>{' '}
                  <strong>{editedData?.debtor_name}</strong>
                </p>
                <p>
                  <span className="text-gray-500">Hauptforderung:</span>{' '}
                  <strong>{formatCurrency(editedData?.principal || 0)}</strong>
                </p>
                <p>
                  <span className="text-gray-500">Dokumente:</span>{' '}
                  <strong>{preview.documents.length}</strong>
                </p>
                <p>
                  <span className="text-gray-500">Seiten:</span>{' '}
                  <strong>{preview.num_pages}</strong>
                </p>
              </div>
            </Card>

            {/* Actions */}
            <div className="flex gap-4">
              <Button
                variant="outline"
                onClick={reset}
                disabled={isConfirming}
              >
                Abbrechen
              </Button>
              <Button
                variant="primary"
                onClick={handleConfirm}
                disabled={isConfirming || !editedData?.aktenzeichen}
                className="flex-1"
              >
                {isConfirming ? 'Importiere...' : 'Akte importieren'}
              </Button>
            </div>
          </div>

          {/* Right: PDF Preview */}
          <Card title="PDF-Vorschau">
            {preview.pdf_preview_url ? (
              <PDFViewer url={preview.pdf_preview_url} />
            ) : (
              <div className="bg-gray-100 rounded p-4 text-sm text-gray-600 max-h-96 overflow-auto">
                <pre className="whitespace-pre-wrap">
                  {preview.raw_text_preview}
                </pre>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  )
}
```

### 4.8 Layout Component

```tsx
// frontend/src/components/layout/Layout.tsx
import { ReactNode } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import { useUIStore } from '../../store/uiStore'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const sidebarOpen = useUIStore((state) => state.sidebarOpen)

  return (
    <div className="min-h-screen bg-gray-50">
      <Sidebar />

      <div
        className={`
          transition-all duration-300
          ${sidebarOpen ? 'ml-64' : 'ml-20'}
        `}
      >
        <Header />
        <main className="p-6">{children}</main>
      </div>
    </div>
  )
}
```

```tsx
// frontend/src/components/layout/Sidebar.tsx
import { NavLink } from 'react-router-dom'
import { useUIStore } from '../../store/uiStore'
import {
  HomeIcon,
  FolderIcon,
  ArrowDownTrayIcon,
  EnvelopeIcon,
  DocumentTextIcon,
  ScaleIcon,
  BoltIcon,
  Cog6ToothIcon,
  ChevronLeftIcon,
} from '@heroicons/react/24/outline'

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Akten', href: '/cases', icon: FolderIcon },
  { name: 'Import', href: '/import', icon: ArrowDownTrayIcon },
  { name: 'Posteingang', href: '/messages', icon: EnvelopeIcon },
  { name: 'Mahnverfahren', href: '/dunning', icon: DocumentTextIcon },
  { name: 'Vollstreckung', href: '/enforcement', icon: BoltIcon },
  { name: 'Vorlagen', href: '/templates', icon: ScaleIcon },
  { name: 'Einstellungen', href: '/settings', icon: Cog6ToothIcon },
]

export default function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useUIStore()

  return (
    <aside
      className={`
        fixed left-0 top-0 h-screen bg-gray-900 text-white
        transition-all duration-300 z-40
        ${sidebarOpen ? 'w-64' : 'w-20'}
      `}
    >
      {/* Logo */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-gray-800">
        {sidebarOpen && (
          <span className="text-xl font-bold">InkassoKom</span>
        )}
        <button
          onClick={toggleSidebar}
          className="p-2 rounded hover:bg-gray-800"
        >
          <ChevronLeftIcon
            className={`h-5 w-5 transition-transform ${!sidebarOpen && 'rotate-180'}`}
          />
        </button>
      </div>

      {/* Navigation */}
      <nav className="mt-4 px-2">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) => `
              flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1
              transition-colors
              ${isActive
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }
            `}
          >
            <item.icon className="h-5 w-5 flex-shrink-0" />
            {sidebarOpen && <span>{item.name}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
```

---

## 5. API-Spezifikation

### 5.1 Endpunkt-Übersicht

| Methode | Endpunkt | Beschreibung |
|---------|----------|--------------|
| **Auth** | | |
| POST | `/auth/login` | Login mit Email/Passwort |
| POST | `/auth/logout` | Logout (Token invalidieren) |
| GET | `/auth/me` | Aktueller User |
| **Cases** | | |
| GET | `/cases` | Liste aller Akten |
| GET | `/cases/statistics` | Statistiken für Dashboard |
| GET | `/cases/{id}` | Einzelne Akte |
| POST | `/cases` | Neue Akte erstellen |
| PATCH | `/cases/{id}` | Akte aktualisieren |
| DELETE | `/cases/{id}` | Akte löschen (soft) |
| **Documents** | | |
| GET | `/cases/{id}/documents` | Dokumente einer Akte |
| POST | `/cases/{id}/documents` | Dokument hochladen |
| GET | `/documents/{id}` | Dokument herunterladen |
| DELETE | `/documents/{id}` | Dokument löschen |
| **Bookings** | | |
| GET | `/cases/{id}/bookings` | Buchungen einer Akte |
| POST | `/cases/{id}/bookings` | Buchung hinzufügen |
| **Import** | | |
| POST | `/import/ra-micro/preview` | PDF analysieren |
| POST | `/import/ra-micro/confirm` | Import bestätigen |
| POST | `/import/zip/preview` | ZIP analysieren |
| POST | `/import/zip/confirm` | ZIP-Import bestätigen |
| **Messages** | | |
| GET | `/messages` | Nachrichten-Liste |
| GET | `/messages/{id}` | Einzelne Nachricht |
| POST | `/messages` | Nachricht senden |
| PATCH | `/messages/{id}/read` | Als gelesen markieren |
| **Wiedervorlagen** | | |
| GET | `/wiedervorlagen` | Alle Wiedervorlagen |
| GET | `/wiedervorlagen/due` | Fällige Wiedervorlagen |
| POST | `/cases/{id}/wiedervorlagen` | WV anlegen |
| PATCH | `/wiedervorlagen/{id}` | WV aktualisieren |
| DELETE | `/wiedervorlagen/{id}` | WV löschen |
| **Templates** | | |
| GET | `/templates` | Vorlagen-Liste |
| GET | `/templates/{id}` | Vorlage herunterladen |
| POST | `/templates` | Vorlage hochladen |
| POST | `/templates/{id}/generate` | Dokument generieren |

### 5.2 OpenAPI Schema

FastAPI generiert automatisch OpenAPI-Dokumentation unter:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

---

## 6. Datenmodelle

### 6.1 ER-Diagramm

```
┌─────────────────┐       ┌─────────────────┐
│  organizations  │───────│     users       │
│  (Kanzleien)    │       │  (Benutzer)     │
└────────┬────────┘       └────────┬────────┘
         │                         │
         │ 1:n                     │ 1:n
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│     cases       │◄──────│   case_parties  │──────►┌─────────────┐
│    (Akten)      │       │ (Zuordnung)     │       │   parties   │
└────────┬────────┘       └─────────────────┘       │ (Beteiligte)│
         │                                          └─────────────┘
         │ 1:n
         ├─────────────────┬─────────────────┬─────────────────┐
         ▼                 ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────┐
│    claims       │ │   documents     │ │ communications  │ │  deadlines  │
│  (Forderungen)  │ │   (Dokumente)   │ │  (Nachrichten)  │ │  (Fristen)  │
└────────┬────────┘ └─────────────────┘ └─────────────────┘ └─────────────┘
         │
         │ 1:n
         ▼
┌─────────────────┐
│ ledger_bookings │
│   (Buchungen)   │
└─────────────────┘
```

### 6.2 Bestehende SQLAlchemy Models

Die bestehenden Models unter `/src/models/` können **direkt wiederverwendet** werden:

- `base.py` - Base Model mit UUID, Timestamps, Soft Delete
- `case.py` - Case, Party, CaseParty
- `claim.py` - Claim, LedgerBooking
- `document.py` - Document, DocumentChunk, GeneratedDocument
- `communication.py` - Message, Attachment
- `deadline.py` - Deadline (Wiedervorlagen)
- `user.py` - User, Session
- `organization.py` - Organization, OrganizationSettings
- `template.py` - Template, Letterhead

---

## 7. Authentifizierung & Autorisierung

### 7.1 Auth Flow

```
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│  React   │      │  FastAPI │      │ Supabase │      │ Database │
│ Frontend │      │  Backend │      │   Auth   │      │          │
└────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘
     │                 │                 │                 │
     │ 1. Login        │                 │                 │
     │ (email/pass)    │                 │                 │
     │────────────────►│                 │                 │
     │                 │ 2. Verify       │                 │
     │                 │────────────────►│                 │
     │                 │                 │ 3. Check user   │
     │                 │                 │────────────────►│
     │                 │                 │◄────────────────│
     │                 │ 4. JWT Token    │                 │
     │                 │◄────────────────│                 │
     │ 5. Token +      │                 │                 │
     │    User Info    │                 │                 │
     │◄────────────────│                 │                 │
     │                 │                 │                 │
     │ 6. API Request  │                 │                 │
     │ (Bearer Token)  │                 │                 │
     │────────────────►│                 │                 │
     │                 │ 7. Verify JWT   │                 │
     │                 │────────────────►│                 │
     │                 │◄────────────────│                 │
     │                 │ 8. Query with   │                 │
     │                 │    org_id       │                 │
     │                 │─────────────────────────────────►│
     │ 9. Response     │◄─────────────────────────────────│
     │◄────────────────│                 │                 │
```

### 7.2 Dependency Injection

```python
# backend/app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.config import settings
from app.db.session import get_async_session
from app.models.user import User

security = HTTPBearer()

async def get_db() -> AsyncSession:
    async with get_async_session() as session:
        yield session

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate JWT and return current user."""
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
```

### 7.3 Row Level Security (RLS)

Supabase RLS-Policies für Multi-Tenancy:

```sql
-- Cases: Users can only see cases from their organization
CREATE POLICY "cases_org_isolation" ON cases
    FOR ALL
    USING (organization_id = auth.jwt() ->> 'organization_id');

-- Documents: Same organization isolation
CREATE POLICY "documents_org_isolation" ON documents
    FOR ALL
    USING (
        organization_id = auth.jwt() ->> 'organization_id'
        OR case_id IN (
            SELECT id FROM cases
            WHERE organization_id = auth.jwt() ->> 'organization_id'
        )
    );
```

---

## 8. Datei-Storage

### 8.1 Supabase Storage Struktur

```
buckets/
├── case-documents/           # Akten-Dokumente
│   └── {org_id}/
│       └── {case_id}/
│           ├── {doc_id}.pdf
│           └── {doc_id}.pdf
│
├── generated-letters/        # Generierte Schreiben
│   └── {org_id}/
│       └── {case_id}/
│           └── {generated_doc_id}.pdf
│
├── templates/                # Dokumentvorlagen
│   └── {org_id}/
│       ├── briefkopf.docx
│       └── mahnung.docx
│
└── temp-imports/             # Temporäre Import-Dateien
    └── {preview_id}/
        └── original.pdf
```

### 8.2 Storage Service

```python
# backend/app/services/storage_service.py
from supabase import create_client
from app.config import settings

class StorageService:
    def __init__(self):
        self.client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
        )

    async def upload_document(
        self,
        bucket: str,
        path: str,
        content: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        """Upload file to Supabase Storage."""
        response = self.client.storage.from_(bucket).upload(
            path,
            content,
            {"content-type": content_type},
        )
        return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"

    async def get_signed_url(
        self,
        bucket: str,
        path: str,
        expires_in: int = 3600,
    ) -> str:
        """Get temporary signed URL for private files."""
        response = self.client.storage.from_(bucket).create_signed_url(
            path,
            expires_in,
        )
        return response["signedURL"]

    async def delete_file(self, bucket: str, path: str) -> bool:
        """Delete file from storage."""
        self.client.storage.from_(bucket).remove([path])
        return True
```

---

## 9. Migrationsplan

### Phase 1: Vorbereitung (1-2 Wochen)

1. **Projekt-Setup**
   - [ ] Monorepo erstellen (backend/ + frontend/)
   - [ ] Docker Compose für lokale Entwicklung
   - [ ] CI/CD Pipeline (GitHub Actions)
   - [ ] Umgebungsvariablen (.env.example)

2. **Backend Basis**
   - [ ] FastAPI Projekt initialisieren
   - [ ] Bestehende Models kopieren/anpassen
   - [ ] Database Connection (async SQLAlchemy)
   - [ ] Auth Middleware (Supabase JWT)
   - [ ] CORS konfigurieren

3. **Frontend Basis**
   - [ ] Vite + React + TypeScript Setup
   - [ ] Tailwind + shadcn/ui
   - [ ] React Router
   - [ ] Zustand Store
   - [ ] API Client (Axios)

### Phase 2: Core Features (2-3 Wochen)

1. **API Endpoints**
   - [ ] `/auth` - Login/Logout/Me
   - [ ] `/cases` - CRUD
   - [ ] `/cases/{id}/documents` - Upload/Download
   - [ ] `/cases/{id}/bookings` - CRUD

2. **Frontend Pages**
   - [ ] Login Page
   - [ ] Dashboard mit Statistiken
   - [ ] Akten-Liste (Suche, Filter, Pagination)
   - [ ] Akten-Detail (Dokumente, Buchungen)

### Phase 3: Import Feature (1-2 Wochen)

1. **Backend**
   - [ ] `parser_akten.py` integrieren
   - [ ] `/import/ra-micro/preview`
   - [ ] `/import/ra-micro/confirm`
   - [ ] PDF Split + Upload

2. **Frontend**
   - [ ] Import Page mit Drag & Drop
   - [ ] Preview mit editierbaren Feldern
   - [ ] PDF Viewer
   - [ ] Bestätigungs-Flow

### Phase 4: Erweiterte Features (2-3 Wochen)

1. **Nachrichten**
   - [ ] Messages API
   - [ ] Posteingang UI
   - [ ] Nachricht verfassen

2. **Wiedervorlagen**
   - [ ] Wiedervorlagen API
   - [ ] Kalender-Ansicht
   - [ ] Benachrichtigungen

3. **Vorlagen**
   - [ ] Template Upload/Download
   - [ ] Dokument generieren
   - [ ] Platzhalter ersetzen

### Phase 5: Finalisierung (1-2 Wochen)

1. **Testing**
   - [ ] Backend Unit Tests (pytest)
   - [ ] Frontend Component Tests (Vitest)
   - [ ] E2E Tests (Playwright)

2. **Deployment**
   - [ ] Staging Environment
   - [ ] Production Deployment
   - [ ] Monitoring (Sentry)

3. **Migration**
   - [ ] Daten-Migration von Streamlit Session State
   - [ ] Parallelbetrieb
   - [ ] Umstellung

### Zeitplan Übersicht

```
Woche 1-2:   ████████░░░░░░░░░░░░  Vorbereitung
Woche 3-5:   ░░░░░░░░████████████░  Core Features
Woche 6-7:   ░░░░░░░░░░░░░░░░████░  Import
Woche 8-10:  ░░░░░░░░░░░░░░░░░░██████  Erweiterte Features
Woche 11-12: ░░░░░░░░░░░░░░░░░░░░████  Finalisierung
```

**Geschätzte Gesamtdauer: 10-12 Wochen**

---

## Anhang: Technische Entscheidungen

### Warum Zustand statt Redux?

- Einfacher: Kein Boilerplate (actions, reducers, selectors)
- TypeScript-native
- Kleiner Bundle-Size (1.5KB vs 7KB)
- Für diese App-Größe ausreichend

### Warum TanStack Query statt SWR?

- Bessere DevTools
- Optimistic Updates eingebaut
- Mutation Lifecycle Hooks
- Query Invalidation

### Warum shadcn/ui statt Chakra/MUI?

- Kopierbar, nicht als Dependency
- Vollständig anpassbar
- Tailwind-native
- Keine Runtime-Dependencies

### Warum Vite statt Next.js?

- SPA ist ausreichend (keine SEO nötig)
- Einfacher (kein SSR-Komplexität)
- Schnellerer Build
- Backend ist separat (FastAPI)
