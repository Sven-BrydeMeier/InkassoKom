"""
Streamlit Database Integration
Provides database-backed functions that can replace in-memory demo data
"""
import streamlit as st
from typing import List, Dict, Any, Optional
from datetime import date, datetime

from .connection import (
    DatabaseConfig,
    get_engine,
    get_db_session,
    test_connection,
    get_connection_info,
    ensure_tables_exist
)
from .cache import get_cache, cache_enabled


def is_database_configured() -> bool:
    """Check if database is properly configured via secrets."""
    config = DatabaseConfig.from_streamlit_secrets()
    return config.is_configured


def get_db_status() -> Dict[str, Any]:
    """Get database and cache status for display."""
    db_config = DatabaseConfig.from_streamlit_secrets()
    cache = get_cache()

    # Test database connection
    db_connected, db_message = test_connection() if db_config.is_configured else (False, "Nicht konfiguriert")

    # If connected, ensure tables exist
    if db_connected:
        tables_ok, tables_msg = ensure_tables_exist()
        if not tables_ok:
            db_message = tables_msg

    # Get cache stats (includes error message if not connected)
    cache_stats = cache.get_stats()

    return {
        'database': {
            'configured': db_config.is_configured,
            'connected': db_connected,
            'message': db_message,
            'host': db_config.host if db_config.is_configured else 'SQLite (lokal)',
            'database': db_config.database
        },
        'cache': {
            'configured': cache._url is not None,
            'connected': cache.is_connected,
            'stats': cache_stats,
            'error': cache_stats.get('error') if not cache.is_connected else None
        }
    }


def show_db_status_widget():
    """Display database status in Streamlit sidebar."""
    status = get_db_status()

    with st.sidebar:
        st.markdown("---")
        st.markdown("##### 🔌 Datenbank-Status")

        # Database status
        if status['database']['connected']:
            st.success(f"✅ PostgreSQL: {status['database']['host']}")
        elif status['database']['configured']:
            st.error(f"❌ DB-Fehler: {status['database']['message']}")
        else:
            st.warning("⚠️ SQLite (lokal)")

        # Cache status
        if status['cache']['connected']:
            stats = status['cache']['stats']
            st.success(f"✅ Redis Cache ({stats.get('total_keys', 0)} Keys)")
        elif status['cache']['configured']:
            error_msg = status['cache'].get('error', 'Unbekannter Fehler')
            st.warning(f"⚠️ Redis-Fehler: {error_msg[:50]}..." if error_msg and len(error_msg) > 50 else f"⚠️ Redis-Fehler: {error_msg}")
        else:
            st.info("ℹ️ Kein Cache konfiguriert")


class DatabaseBackedStore:
    """
    A store that uses database when available, falls back to session state.
    This allows gradual migration from demo data to real database.
    """

    def __init__(self):
        self._use_db = is_database_configured()
        self._cache = get_cache()

    @property
    def use_database(self) -> bool:
        """Check if we should use database."""
        return self._use_db and test_connection()[0]

    def get_all_cases(self) -> List[Dict[str, Any]]:
        """Get all cases from database or session state."""
        if self.use_database:
            try:
                from src.services.case_service import CaseService
                return CaseService.get_all_cases()
            except Exception as e:
                st.warning(f"DB-Fehler: {e}. Verwende lokale Daten.")

        # Fallback to session state / demo data
        return self._get_session_cases()

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get single case."""
        if self.use_database:
            try:
                from src.services.case_service import CaseService
                return CaseService.get_case(case_id)
            except Exception:
                pass

        # Fallback
        cases = self._get_session_cases()
        for case in cases:
            if case.get('id') == case_id:
                return case
        return None

    def create_case(self, case_data: Dict[str, Any]) -> Optional[str]:
        """Create a new case."""
        if self.use_database:
            try:
                from src.services.case_service import CaseService
                case = CaseService.create_case(
                    organization_id=case_data.get('organization_id', 'default'),
                    case_number=case_data.get('nr', ''),
                    creditor_name=case_data.get('creditor', ''),
                    debtor_name=case_data.get('debtor', ''),
                    principal_amount=case_data.get('principal', 0),
                    creditor_address=case_data.get('creditor_address', ''),
                    debtor_address=case_data.get('debtor_address', ''),
                    subject=case_data.get('subject', ''),
                    interest_rate=case_data.get('interest', 5.0),
                    due_date=case_data.get('due_date', date.today())
                )
                return str(case.id)
            except Exception as e:
                st.warning(f"DB-Fehler beim Erstellen: {e}")

        # Fallback to session state
        return self._create_session_case(case_data)

    def get_documents(self, case_id: str) -> List[Dict[str, Any]]:
        """Get documents for a case."""
        if self.use_database:
            try:
                from src.services.document_service import DocumentService
                return DocumentService.get_documents_for_case(case_id)
            except Exception:
                pass

        # Fallback
        return self._get_session_documents(case_id)

    def create_documents(self, case_id: str, documents: List[Dict[str, Any]]) -> bool:
        """Create multiple documents."""
        if self.use_database:
            try:
                from src.services.document_service import DocumentService
                DocumentService.bulk_create_documents(case_id, documents)
                return True
            except Exception as e:
                st.warning(f"DB-Fehler: {e}")

        # Fallback
        return self._create_session_documents(case_id, documents)

    def get_bookings(self, case_id: str) -> List[Dict[str, Any]]:
        """Get bookings for a case."""
        if self.use_database:
            try:
                from src.services.case_service import CaseService
                return CaseService.get_bookings(case_id)
            except Exception:
                pass

        # Fallback
        return self._get_session_bookings(case_id)

    # Session state fallback methods

    def _get_session_cases(self) -> List[Dict[str, Any]]:
        """Get cases from session state."""
        cases = []

        # Get from DEMO_CASES if available
        if 'DEMO_CASES' in dir(st.session_state):
            cases.extend(st.session_state.DEMO_CASES)

        # Add imported cases
        if 'imported_cases' in st.session_state:
            cases.extend(st.session_state.imported_cases)

        return cases

    def _create_session_case(self, case_data: Dict[str, Any]) -> str:
        """Create case in session state."""
        if 'imported_cases' not in st.session_state:
            st.session_state.imported_cases = []

        case_id = f"local-{len(st.session_state.imported_cases) + 1:03d}"
        case_data['id'] = case_id
        case_data['created'] = datetime.now()

        st.session_state.imported_cases.append(case_data)
        return case_id

    def _get_session_documents(self, case_id: str) -> List[Dict[str, Any]]:
        """Get documents from session state."""
        if 'imported_documents' in st.session_state:
            return st.session_state.imported_documents.get(case_id, [])
        return []

    def _create_session_documents(self, case_id: str, documents: List[Dict[str, Any]]) -> bool:
        """Create documents in session state."""
        if 'imported_documents' not in st.session_state:
            st.session_state.imported_documents = {}

        st.session_state.imported_documents[case_id] = documents
        return True

    def _get_session_bookings(self, case_id: str) -> List[Dict[str, Any]]:
        """Get bookings from session state."""
        if 'imported_bookings' in st.session_state:
            return st.session_state.imported_bookings.get(case_id, [])
        return []


# Global store instance
_store: Optional[DatabaseBackedStore] = None


def get_store() -> DatabaseBackedStore:
    """Get or create global store instance."""
    global _store
    if _store is None:
        _store = DatabaseBackedStore()
    return _store


# Convenience functions that can be used directly in the app
def db_get_all_cases() -> List[Dict[str, Any]]:
    """Get all cases (database or fallback)."""
    return get_store().get_all_cases()


def db_get_case(case_id: str) -> Optional[Dict[str, Any]]:
    """Get single case."""
    return get_store().get_case(case_id)


def db_create_case(case_data: Dict[str, Any]) -> Optional[str]:
    """Create case."""
    return get_store().create_case(case_data)


def db_get_documents(case_id: str) -> List[Dict[str, Any]]:
    """Get documents for case."""
    return get_store().get_documents(case_id)


def db_create_documents(case_id: str, documents: List[Dict[str, Any]]) -> bool:
    """Create documents."""
    return get_store().create_documents(case_id, documents)


def db_get_bookings(case_id: str) -> List[Dict[str, Any]]:
    """Get bookings for case."""
    return get_store().get_bookings(case_id)
