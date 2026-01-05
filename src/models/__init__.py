"""
InkassoKom Database Models

SQLAlchemy models for Supabase/PostgreSQL.
All models follow the architecture defined in ADR-001 (Multi-Tenancy).
"""

from src.models.base import Base, generate_uuid
from src.models.organization import Organization, Membership
from src.models.user import User
from src.models.case import Case, Party, CaseParty
from src.models.claim import Claim, LedgerBooking, Payment, PaymentAllocation
from src.models.document import Document, DocumentChunk, GeneratedDocument
from src.models.communication import Communication, Message
from src.models.template import Template, Letterhead
from src.models.deadline import Deadline
from src.models.audit import AuditLog

__all__ = [
    'Base',
    'generate_uuid',
    'Organization',
    'Membership',
    'User',
    'Case',
    'Party',
    'CaseParty',
    'Claim',
    'LedgerBooking',
    'Payment',
    'PaymentAllocation',
    'Document',
    'DocumentChunk',
    'GeneratedDocument',
    'Communication',
    'Message',
    'Template',
    'Letterhead',
    'Deadline',
    'AuditLog',
]
