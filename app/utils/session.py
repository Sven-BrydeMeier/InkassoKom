"""
Session management utilities for Streamlit
"""
import streamlit as st
from typing import Optional, List
from uuid import UUID
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db import get_db_session
from db.models import User, Organization
from backend.services.auth_service import AuthService
from config.settings import UserRole


def init_session():
    """Initialize session state variables."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'token' not in st.session_state:
        st.session_state.token = None
    if 'organization' not in st.session_state:
        st.session_state.organization = None
    if 'current_case_id' not in st.session_state:
        st.session_state.current_case_id = None


def get_current_user() -> Optional[dict]:
    """Get the current authenticated user."""
    if st.session_state.authenticated and st.session_state.user:
        return st.session_state.user
    return None


def get_user_id() -> Optional[UUID]:
    """Get the current user's ID."""
    user = get_current_user()
    if user:
        return UUID(user['id'])
    return None


def get_organization_id() -> Optional[UUID]:
    """Get the current user's organization ID."""
    user = get_current_user()
    if user and user.get('organization_id'):
        return UUID(user['organization_id'])
    return None


def require_auth(func):
    """Decorator to require authentication for a page."""
    def wrapper(*args, **kwargs):
        if not st.session_state.get('authenticated'):
            st.warning("Bitte melden Sie sich an.")
            st.stop()
        return func(*args, **kwargs)
    return wrapper


def require_role(allowed_roles: List[str]):
    """Decorator to require specific roles for a page."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                st.warning("Bitte melden Sie sich an.")
                st.stop()
            if user.get('role') not in allowed_roles:
                st.error("Sie haben keine Berechtigung für diese Seite.")
                st.stop()
            return func(*args, **kwargs)
        return wrapper
    return decorator


def login(email: str, password: str) -> bool:
    """Attempt to log in a user."""
    with get_db_session() as db:
        auth_service = AuthService(db)
        result = auth_service.login(email, password)

        if result:
            st.session_state.authenticated = True
            st.session_state.user = result['user']
            st.session_state.token = result['token']

            # Load organization info
            if result['user'].get('organization_id'):
                org = db.query(Organization).filter(
                    Organization.id == UUID(result['user']['organization_id'])
                ).first()
                if org:
                    st.session_state.organization = {
                        'id': str(org.id),
                        'name': org.name,
                        'slug': org.slug
                    }

            return True

    return False


def logout():
    """Log out the current user."""
    if st.session_state.token:
        with get_db_session() as db:
            auth_service = AuthService(db)
            auth_service.logout(st.session_state.token)

    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.token = None
    st.session_state.organization = None
    st.session_state.current_case_id = None


def get_user_display_name() -> str:
    """Get a display name for the current user."""
    user = get_current_user()
    if user:
        parts = []
        if user.get('title'):
            parts.append(user['title'])
        parts.append(user.get('first_name', ''))
        parts.append(user.get('last_name', ''))
        return ' '.join(p for p in parts if p)
    return "Gast"


def get_role_display_name(role: str) -> str:
    """Get a display name for a role."""
    role_names = {
        UserRole.ADMIN: "Administrator",
        UserRole.RECHTSANWALT: "Rechtsanwalt",
        UserRole.GLAEUBIGERIN: "Gläubigerin",
        UserRole.SCHULDNER: "Schuldner"
    }
    return role_names.get(role, role)


def is_lawyer() -> bool:
    """Check if current user is a lawyer."""
    user = get_current_user()
    return user and user.get('role') in [UserRole.ADMIN, UserRole.RECHTSANWALT]


def is_creditor() -> bool:
    """Check if current user is a creditor."""
    user = get_current_user()
    return user and user.get('role') == UserRole.GLAEUBIGERIN


def is_debtor() -> bool:
    """Check if current user is a debtor."""
    user = get_current_user()
    return user and user.get('role') == UserRole.SCHULDNER
