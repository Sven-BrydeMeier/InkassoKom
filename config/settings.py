"""
Application Settings - NotarFlow Inkasso-Kommunikationsplattform
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application configuration using Pydantic Settings."""

    # Application
    APP_NAME: str = "NotarFlow - Inkasso-Kommunikationsplattform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-in-production-32-chars-min"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/notarflow"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage
    STORAGE_TYPE: str = "local"  # local, s3
    STORAGE_PATH: str = "./storage"
    S3_BUCKET: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_ENDPOINT: Optional[str] = None
    S3_REGION: str = "eu-central-1"

    # Encryption
    ENCRYPTION_KEY: Optional[str] = None

    # OpenAI (optional AI Copilot)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo-preview"

    # Email
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@notarflow.de"
    SMTP_TLS: bool = True

    # beA Connector (optional)
    BEA_CONNECTOR_ENABLED: bool = False
    BEA_CONNECTOR_URL: Optional[str] = None
    BEA_CONNECTOR_API_KEY: Optional[str] = None

    # Session
    SESSION_EXPIRY_HOURS: int = 24

    # Limits
    MAX_UPLOAD_SIZE_MB: int = 50
    OCR_ENABLED: bool = True

    # Paths
    TEMPLATE_DIR: str = "./templates"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()


# Role definitions
class UserRole:
    ADMIN = "admin"
    RECHTSANWALT = "rechtsanwalt"
    GLAEUBIGERIN = "glaeubigerin"
    SCHULDNER = "schuldner"


# Document types
class DocumentType:
    RECHNUNG = "rechnung"
    VERTRAG = "vertrag"
    MAHNUNG = "mahnung"
    MAHNBESCHEID = "mahnbescheid"
    VOLLSTRECKUNGSBESCHEID = "vollstreckungsbescheid"
    SCHREIBEN_RA = "schreiben_ra"
    SCHREIBEN_GLAEUBIGER = "schreiben_glaeubiger"
    SCHREIBEN_SCHULDNER = "schreiben_schuldner"
    VERMOEGENSVERZEICHNIS = "vermoegensverzeichnis"
    PFUEB = "pfueb"
    SONSTIGES = "sonstiges"


# Case status
class CaseStatus:
    OFFEN = "offen"
    MAHNVERFAHREN = "mahnverfahren"
    VOLLSTRECKUNG = "vollstreckung"
    RATENZAHLUNG = "ratenzahlung"
    ABGESCHLOSSEN = "abgeschlossen"
    UNEINBRINGLICH = "uneinbringlich"


# Payment status
class PaymentStatus:
    GEMELDET = "gemeldet"
    AKZEPTIERT = "akzeptiert"
    ABGELEHNT = "abgelehnt"
    VERBUCHT = "verbucht"


# Booking categories
class BookingCategory:
    HAUPTFORDERUNG = "hauptforderung"
    ZINSEN = "zinsen"
    RA_GEBUEHREN = "ra_gebuehren"
    NEBENKOSTEN = "nebenkosten"
    GERICHTSKOSTEN = "gerichtskosten"
    VOLLSTRECKUNGSKOSTEN = "vollstreckungskosten"


# Dunning procedure status
class DunningStatus:
    NICHT_BEANTRAGT = "nicht_beantragt"
    MB_BEANTRAGT = "mb_beantragt"
    MB_ZUGESTELLT = "mb_zugestellt"
    WIDERSPRUCH = "widerspruch"
    VB_BEANTRAGT = "vb_beantragt"
    VB_ERLASSEN = "vb_erlassen"
    TITEL_RECHTSKRAEFTIG = "titel_rechtskraeftig"


# Enforcement status
class EnforcementStatus:
    NICHT_BEGONNEN = "nicht_begonnen"
    GV_AUFTRAG = "gv_auftrag"
    VV_ERHALTEN = "vv_erhalten"
    PFUEB_BEANTRAGT = "pfueb_beantragt"
    PFUEB_ERLASSEN = "pfueb_erlassen"
    PFUEB_ZUGESTELLT = "pfueb_zugestellt"
    TEILZAHLUNG = "teilzahlung"
    VOLLSTAENDIG = "vollstaendig"


# Payment plan status
class PaymentPlanStatus:
    ANGEFRAGT = "angefragt"
    ENTWURF = "entwurf"
    GEPRUEFT = "geprueft"
    FREIGEGEBEN = "freigegeben"
    AKTIV = "aktiv"
    VERZOEGERT = "verzoegert"
    ABGESCHLOSSEN = "abgeschlossen"
    GEKUENDIGT = "gekuendigt"


# Approval status
class ApprovalStatus:
    AUSSTEHEND = "ausstehend"
    GENEHMIGT = "genehmigt"
    ABGELEHNT = "abgelehnt"
