"""
NotarFlow - Inkasso-Kommunikationsplattform
Main Streamlit Application Entry Point

Mobile-optimized for Phone and iPad access
"""
import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.session import init_session, login, logout, get_current_user, get_user_display_name
from app.utils.formatting import format_status_badge
from app.utils.mobile_styles import inject_mobile_styles, inject_mobile_nav
from config.settings import settings, UserRole

# Page configuration - mobile optimized
st.set_page_config(
    page_title="NotarFlow - Inkasso-Plattform",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"  # Collapsed by default for mobile
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .status-badge {
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
    }
    .timeline-item {
        border-left: 2px solid #ddd;
        padding-left: 1rem;
        margin-left: 0.5rem;
    }
    .case-card {
        border: 1px solid #ddd;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .case-card:hover {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# Inject mobile-optimized styles
inject_mobile_styles()

# Initialize session
init_session()


def show_login_page():
    """Display the login page."""
    st.markdown("# ⚖️ NotarFlow")
    st.markdown("### Inkasso-Kommunikationsplattform")

    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("#### Anmeldung")

        with st.form("login_form"):
            email = st.text_input("E-Mail", placeholder="ihre@email.de")
            password = st.text_input("Passwort", type="password")

            submitted = st.form_submit_button("Anmelden", use_container_width=True)

            if submitted:
                if email and password:
                    if login(email, password):
                        st.success("Erfolgreich angemeldet!")
                        st.rerun()
                    else:
                        st.error("Ungültige Anmeldedaten.")
                else:
                    st.warning("Bitte E-Mail und Passwort eingeben.")

        st.divider()

        st.caption("© 2024 NotarFlow - Alle Rechte vorbehalten")
        st.caption("DSGVO-konform | Kanzlei-Standard Sicherheit")


def show_main_app():
    """Display the main application based on user role."""
    user = get_current_user()

    if not user:
        show_login_page()
        return

    role = user.get('role', '')

    # Sidebar
    with st.sidebar:
        st.markdown(f"### ⚖️ NotarFlow")
        st.caption(f"Angemeldet als: **{get_user_display_name()}**")
        st.caption(f"Rolle: {role.replace('_', ' ').title()}")

        st.divider()

        # Navigation based on role
        if role in [UserRole.ADMIN, UserRole.RECHTSANWALT]:
            show_lawyer_navigation()
        elif role == UserRole.GLAEUBIGERIN:
            show_creditor_navigation()
        elif role == UserRole.SCHULDNER:
            show_debtor_navigation()

        st.divider()

        if st.button("🚪 Abmelden", use_container_width=True):
            logout()
            st.rerun()

    # Main content
    st.markdown(f"# Willkommen, {get_user_display_name()}")

    if role in [UserRole.ADMIN, UserRole.RECHTSANWALT]:
        show_lawyer_dashboard()
    elif role == UserRole.GLAEUBIGERIN:
        show_creditor_dashboard()
    elif role == UserRole.SCHULDNER:
        show_debtor_dashboard()

    # Inject mobile bottom navigation
    inject_mobile_nav(role)


def show_lawyer_navigation():
    """Show navigation for lawyers."""
    st.markdown("### 📋 Navigation")

    if st.button("📊 Dashboard", use_container_width=True):
        st.session_state.page = 'dashboard'
        st.rerun()

    if st.button("📁 Aktenregister", use_container_width=True):
        st.session_state.page = 'cases'
        st.rerun()

    if st.button("📬 Posteingang", use_container_width=True):
        st.session_state.page = 'inbox'
        st.rerun()

    if st.button("⚖️ Mahnverfahren", use_container_width=True):
        st.session_state.page = 'dunning'
        st.rerun()

    if st.button("🏛️ Vollstreckung", use_container_width=True):
        st.session_state.page = 'enforcement'
        st.rerun()

    if st.button("⚙️ Einstellungen", use_container_width=True):
        st.session_state.page = 'settings'
        st.rerun()


def show_creditor_navigation():
    """Show navigation for creditors."""
    st.markdown("### 📋 Navigation")

    if st.button("📊 Aktuelles", use_container_width=True):
        st.session_state.page = 'dashboard'
        st.rerun()

    if st.button("💰 Forderungen", use_container_width=True):
        st.session_state.page = 'claims'
        st.rerun()

    if st.button("💳 Zahlungseingänge", use_container_width=True):
        st.session_state.page = 'payments'
        st.rerun()


def show_debtor_navigation():
    """Show navigation for debtors."""
    st.markdown("### 📋 Navigation")

    if st.button("📊 Übersicht", use_container_width=True):
        st.session_state.page = 'dashboard'
        st.rerun()

    if st.button("📄 Dokumente", use_container_width=True):
        st.session_state.page = 'documents'
        st.rerun()

    if st.button("📅 Ratenzahlung", use_container_width=True):
        st.session_state.page = 'payment_plan'
        st.rerun()


def show_lawyer_dashboard():
    """Show dashboard for lawyers."""
    from db import get_db_session
    from backend.services.case_service import CaseService
    from backend.services.notification_service import NotificationService
    from backend.services.limitation_service import LimitationService
    from app.utils.session import get_organization_id, get_user_id

    org_id = get_organization_id()
    user_id = get_user_id()

    if not org_id:
        st.warning("Keine Organisation zugeordnet.")
        return

    # Quick stats
    st.markdown("## 📊 Dashboard")

    with get_db_session() as db:
        case_service = CaseService(db)
        notification_service = NotificationService(db)
        limitation_service = LimitationService(db)

        # Get statistics
        stats = case_service.get_organization_statistics(org_id)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Aktive Akten", stats.get('total_cases', 0))

        with col2:
            from app.utils.formatting import format_currency
            st.metric("Gesamtforderungen", format_currency(stats.get('total_open', 0)))

        with col3:
            # Get pending inbox items
            from backend.services.document_service import DocumentService
            doc_service = DocumentService(db)
            inbox_items = doc_service.get_inbox_items(org_id, status='new')
            st.metric("Posteingang", len(inbox_items))

        with col4:
            notifications = notification_service.get_unread_notifications(user_id)
            st.metric("Benachrichtigungen", len(notifications))

    st.divider()

    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["📌 Aktuelles", "⚠️ Verjährungswarnungen", "📬 Posteingang", "📊 Statistiken"])

    with tab1:
        show_activity_feed(org_id, user_id)

    with tab2:
        show_limitation_warnings(org_id)

    with tab3:
        show_inbox_preview(org_id)

    with tab4:
        show_statistics(org_id)


def show_activity_feed(org_id, user_id):
    """Show recent activity feed."""
    from db import get_db_session
    from backend.services.notification_service import NotificationService

    st.markdown("### 📌 Aktuelle Ereignisse")

    with get_db_session() as db:
        notification_service = NotificationService(db)
        feed = notification_service.get_activity_feed(
            user_id=user_id,
            organization_id=org_id,
            limit=20
        )

        if not feed:
            st.info("Keine aktuellen Ereignisse.")
        else:
            from app.utils.components import show_timeline
            show_timeline(feed, max_items=10)


def show_limitation_warnings(org_id):
    """Show limitation warnings."""
    from db import get_db_session
    from backend.services.limitation_service import LimitationService
    from app.utils.components import show_limitation_warning

    st.markdown("### ⚠️ Verjährungswarnungen")

    with get_db_session() as db:
        limitation_service = LimitationService(db)
        warnings = limitation_service.check_all_cases_limitation(org_id, warning_months=6)

        if not warnings:
            st.success("Keine drohenden Verjährungen in den nächsten 6 Monaten.")
        else:
            for warning in warnings[:10]:
                show_limitation_warning(
                    warning['days_remaining'],
                    warning['internal_number']
                )


def show_inbox_preview(org_id):
    """Show inbox preview."""
    from db import get_db_session
    from backend.services.document_service import DocumentService
    from app.utils.formatting import format_datetime

    st.markdown("### 📬 Neuer Posteingang")

    with get_db_session() as db:
        doc_service = DocumentService(db)
        inbox_items = doc_service.get_inbox_items(org_id, status='new')

        if not inbox_items:
            st.success("Posteingang ist leer.")
        else:
            for item in inbox_items[:5]:
                doc = doc_service.get_document(item.document_id)
                if doc:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"📄 **{doc.original_filename}**")
                        st.caption(f"Eingegangen: {format_datetime(item.received_at)}")
                    with col2:
                        if st.button("Bearbeiten", key=f"inbox_{item.id}"):
                            st.session_state.current_inbox_item = str(item.id)
                            st.session_state.page = 'inbox'
                            st.rerun()
                    st.divider()


def show_statistics(org_id):
    """Show case statistics."""
    from db import get_db_session
    from backend.services.case_service import CaseService

    st.markdown("### 📊 Statistiken")

    with get_db_session() as db:
        case_service = CaseService(db)
        stats = case_service.get_organization_statistics(org_id)

        status_counts = stats.get('status_counts', {})

        if status_counts:
            import pandas as pd

            df = pd.DataFrame([
                {"Status": k.replace('_', ' ').title(), "Anzahl": v}
                for k, v in status_counts.items()
            ])

            st.bar_chart(df.set_index('Status'))


def show_creditor_dashboard():
    """Show dashboard for creditors."""
    from db import get_db_session
    from backend.services.case_service import CaseService
    from app.utils.session import get_user_id
    from app.utils.components import show_case_card, show_balance_card
    from app.utils.formatting import format_currency

    user_id = get_user_id()

    st.markdown("## 📊 Aktuelles")

    with get_db_session() as db:
        case_service = CaseService(db)
        cases = case_service.get_cases_for_creditor(user_id)

        if not cases:
            st.info("Sie haben keine aktiven Forderungen.")
            return

        # Summary
        total_open = 0
        for case in cases:
            summary = case_service.get_case_summary(case.id)
            balance = summary.get('balance', {})
            total_open += balance.get('total_open', 0)

        st.metric("Gesamtforderungen", format_currency(total_open))

        st.divider()

        # Cases list
        st.markdown("### 💰 Ihre Forderungen")

        for case in cases:
            summary = case_service.get_case_summary(case.id)
            show_case_card(summary)


def show_debtor_dashboard():
    """Show dashboard for debtors."""
    from db import get_db_session
    from backend.services.case_service import CaseService
    from backend.services.ledger_service import LedgerService
    from app.utils.session import get_user_id
    from app.utils.components import show_payment_progress, show_balance_card
    from app.utils.formatting import format_currency

    user_id = get_user_id()

    st.markdown("## 📊 Übersicht")

    with get_db_session() as db:
        case_service = CaseService(db)
        ledger_service = LedgerService(db)

        cases = case_service.get_cases_for_debtor(user_id)

        if not cases:
            st.success("Keine offenen Forderungen.")
            return

        for case in cases:
            st.markdown(f"### Akte {case.internal_number}")
            st.caption(f"Gläubiger: {case.creditor_name}")

            balance = ledger_service.get_case_balance(case.id)

            total_soll = balance.get('total_soll', 0)
            total_haben = balance.get('total_haben', 0)
            total_open = balance.get('total_open', 0)

            # Show progress
            show_payment_progress(
                total_amount=total_soll,
                paid_amount=total_haben
            )

            st.divider()


# Main entry point
if __name__ == "__main__":
    if st.session_state.get('authenticated'):
        show_main_app()
    else:
        show_login_page()
