"""
NotarFlow - Inkasso-Kommunikationsplattform
Main Streamlit Application Entry Point
"""
import streamlit as st
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Page configuration
st.set_page_config(
    page_title="NotarFlow - Inkasso-Plattform",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize database
from db import init_db, get_db_session
from db.models import User, Case, LedgerBooking
init_db()

# Custom CSS
st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: bold; margin-bottom: 1rem; }
    .metric-card { background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; }
    .status-badge { padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.875rem; }
    .case-card { border: 1px solid #ddd; padding: 1rem; border-radius: 0.5rem; margin-bottom: 0.5rem; }

    /* Mobile styles */
    @media (max-width: 768px) {
        .main .block-container { padding: 1rem 0.5rem !important; }
        .stButton > button { min-height: 48px !important; width: 100% !important; }
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None


def login(email: str, password: str) -> bool:
    """Authenticate user."""
    from passlib.hash import bcrypt

    with get_db_session() as db:
        user = db.query(User).filter(
            User.email == email,
            User.is_active == True,
            User.is_deleted == False
        ).first()

        if user and bcrypt.verify(password, user.password_hash):
            st.session_state.authenticated = True
            st.session_state.user = {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'organization_id': user.organization_id
            }
            return True
    return False


def logout():
    """Log out user."""
    st.session_state.authenticated = False
    st.session_state.user = None


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

        # Demo accounts info
        with st.expander("Demo-Zugänge"):
            st.markdown("""
            **Rechtsanwalt:** ra@kanzlei-mueller.de / demo123
            **Gläubigerin:** erika@mustermann-gmbh.de / demo123
            **Schuldner:** max@example.de / demo123
            """)

        st.caption("© 2024 NotarFlow - DSGVO-konform")


def show_dashboard():
    """Show main dashboard based on user role."""
    user = st.session_state.user
    role = user.get('role', '')

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚖️ NotarFlow")
        st.caption(f"**{user.get('first_name')} {user.get('last_name')}**")
        st.caption(f"Rolle: {role.replace('_', ' ').title()}")
        st.divider()

        if st.button("🚪 Abmelden", use_container_width=True):
            logout()
            st.rerun()

    # Main content
    st.markdown(f"# Willkommen, {user.get('first_name')}!")

    if role in ['admin', 'rechtsanwalt']:
        show_lawyer_dashboard()
    elif role == 'glaeubigerin':
        show_creditor_dashboard()
    elif role == 'schuldner':
        show_debtor_dashboard()
    else:
        st.info("Keine Dashboard-Ansicht für diese Rolle.")


def show_lawyer_dashboard():
    """Dashboard for lawyers."""
    org_id = st.session_state.user.get('organization_id')

    st.markdown("## 📊 Kanzlei-Dashboard")

    with get_db_session() as db:
        cases = db.query(Case).filter(
            Case.organization_id == org_id,
            Case.is_deleted == False
        ).order_by(Case.created_at.desc()).limit(10).all()

        total_cases = len(cases)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Aktive Akten", total_cases)
        col2.metric("Mahnverfahren", sum(1 for c in cases if c.dunning_status != 'nicht_beantragt'))
        col3.metric("Vollstreckung", sum(1 for c in cases if c.enforcement_status != 'nicht_begonnen'))
        col4.metric("Neu heute", sum(1 for c in cases if c.created_at and c.created_at.date() == datetime.now().date()))

    st.divider()
    st.markdown("### 📁 Aktuelle Akten")

    if not cases:
        st.info("Keine Akten vorhanden.")
        if st.button("➕ Neue Akte erstellen"):
            st.session_state.page = 'new_case'
    else:
        for case in cases[:5]:
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.markdown(f"**{case.internal_number}** - {case.debtor_name or 'Unbekannt'}")
                    st.caption(f"Gläubiger: {case.creditor_name or '-'}")
                with col2:
                    status_color = {'offen': '🟡', 'mahnverfahren': '🟠', 'vollstreckung': '🔴', 'abgeschlossen': '🟢'}.get(case.status, '⚪')
                    st.markdown(f"{status_color} {(case.status or 'offen').replace('_', ' ').title()}")
                with col3:
                    st.button("Öffnen", key=f"case_{case.id}")
                st.divider()


def show_creditor_dashboard():
    """Dashboard for creditors."""
    user_id = st.session_state.user.get('id')

    st.markdown("## 💼 Gläubiger-Dashboard")

    with get_db_session() as db:
        cases = db.query(Case).filter(
            Case.creditor_user_id == user_id,
            Case.is_deleted == False
        ).all()

        if not cases:
            st.info("Sie haben keine aktiven Forderungen.")
            return

        total_open = 0
        for case in cases:
            bookings = db.query(LedgerBooking).filter(LedgerBooking.case_id == case.id).all()
            soll = sum(b.amount for b in bookings if b.debit_credit == 'S')
            haben = sum(b.amount for b in bookings if b.debit_credit == 'H')
            total_open += (soll - haben)

        st.metric("Offene Gesamtforderung", f"{total_open:,.2f} €")
        st.divider()

        st.markdown("### 💰 Ihre Forderungen")
        for case in cases:
            with st.expander(f"Akte {case.internal_number} - {case.debtor_name}"):
                st.write(f"Status: {case.status}")
                st.write(f"Mahnverfahren: {case.dunning_status}")


def show_debtor_dashboard():
    """Dashboard for debtors."""
    user_id = st.session_state.user.get('id')

    st.markdown("## 📋 Schuldner-Übersicht")

    with get_db_session() as db:
        cases = db.query(Case).filter(
            Case.debtor_user_id == user_id,
            Case.is_deleted == False
        ).all()

        if not cases:
            st.success("Keine offenen Forderungen.")
            return

        for case in cases:
            st.markdown(f"### Akte {case.internal_number}")
            st.caption(f"Gläubiger: {case.creditor_name}")

            bookings = db.query(LedgerBooking).filter(LedgerBooking.case_id == case.id).all()
            soll = sum(b.amount for b in bookings if b.debit_credit == 'S')
            haben = sum(b.amount for b in bookings if b.debit_credit == 'H')
            open_amount = soll - haben

            col1, col2 = st.columns(2)
            col1.metric("Gesamtforderung", f"{soll:,.2f} €")
            col2.metric("Offener Betrag", f"{open_amount:,.2f} €")

            if soll > 0:
                progress = haben / soll
                st.progress(min(progress, 1.0), text=f"{progress*100:.1f}% bezahlt")

            st.divider()


# Main entry point
if st.session_state.authenticated:
    show_dashboard()
else:
    show_login_page()
