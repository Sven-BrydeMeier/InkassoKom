"""
Case Management Page (Aktenregister)
Full case management for lawyers
"""
import streamlit as st
from uuid import UUID
from datetime import date
from decimal import Decimal
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.utils.session import init_session, require_role, get_user_id, get_organization_id
from app.utils.formatting import format_currency, format_date, format_datetime, format_status_badge
from app.utils.components import show_balance_card, show_timeline, show_ledger_table, show_document_card
from config.settings import UserRole, CaseStatus, DunningStatus

st.set_page_config(page_title="Aktenregister - NotarFlow", page_icon="📁", layout="wide")

init_session()


@require_role([UserRole.ADMIN, UserRole.RECHTSANWALT])
def main():
    user_id = get_user_id()
    org_id = get_organization_id()

    if not org_id:
        st.warning("Keine Organisation zugeordnet.")
        return

    from db import get_db_session
    from backend.services.case_service import CaseService
    from backend.services.ledger_service import LedgerService
    from backend.services.document_service import DocumentService

    # Check if we're viewing a specific case
    if st.session_state.get('current_case_id'):
        show_case_detail(st.session_state.current_case_id)
        return

    # Case List View
    st.markdown("# 📁 Aktenregister")

    # Search and filter bar
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        search = st.text_input("🔍 Suche", placeholder="Aktennummer, Name, Betreff...")

    with col2:
        status_filter = st.selectbox(
            "Status",
            ["Alle", "Offen", "Mahnverfahren", "Vollstreckung", "Ratenzahlung", "Abgeschlossen"]
        )

    with col3:
        if st.button("➕ Neue Akte", use_container_width=True):
            st.session_state.show_new_case_form = True

    st.divider()

    # New Case Form
    if st.session_state.get('show_new_case_form'):
        show_new_case_form(org_id, user_id)
        return

    # Load and display cases
    with get_db_session() as db:
        case_service = CaseService(db)

        status_map = {
            "Offen": "offen",
            "Mahnverfahren": "mahnverfahren",
            "Vollstreckung": "vollstreckung",
            "Ratenzahlung": "ratenzahlung",
            "Abgeschlossen": "abgeschlossen"
        }

        status = status_map.get(status_filter) if status_filter != "Alle" else None

        cases = case_service.get_cases_for_organization(
            org_id,
            status=status,
            search=search if search else None,
            limit=100
        )

        if not cases:
            st.info("Keine Akten gefunden.")
        else:
            # Display as table-like cards
            for case in cases:
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])

                    with col1:
                        st.markdown(f"**{case.internal_number}**")
                        if case.external_number:
                            st.caption(f"RA-Nr: {case.external_number}")

                    with col2:
                        st.markdown(f"{case.creditor_name}")
                        st.caption(f"./. {case.debtor_name}")

                    with col3:
                        ledger = LedgerService(db)
                        balance = ledger.get_case_balance(case.id)
                        st.markdown(format_currency(balance.get('total_open', 0)))
                        st.caption("offen")

                    with col4:
                        st.markdown(format_status_badge(case.status or 'offen'))
                        if case.dunning_status and case.dunning_status != 'nicht_beantragt':
                            st.caption(case.dunning_status.replace('_', ' ').title())

                    with col5:
                        if st.button("Öffnen", key=f"open_{case.id}"):
                            st.session_state.current_case_id = str(case.id)
                            st.rerun()

                    st.divider()


def show_new_case_form(org_id, user_id):
    """Display form to create a new case."""
    st.markdown("## ➕ Neue Akte anlegen")

    with st.form("new_case_form"):
        st.markdown("### Parteien")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Gläubigerin**")
            creditor_name = st.text_input("Name*", key="creditor_name")
            creditor_street = st.text_input("Straße", key="creditor_street")

            c_col1, c_col2 = st.columns([1, 2])
            with c_col1:
                creditor_plz = st.text_input("PLZ", key="creditor_plz")
            with c_col2:
                creditor_city = st.text_input("Ort", key="creditor_city")

            creditor_email = st.text_input("E-Mail", key="creditor_email")

        with col2:
            st.markdown("**Schuldner**")
            debtor_name = st.text_input("Name*", key="debtor_name")
            debtor_street = st.text_input("Straße", key="debtor_street")

            d_col1, d_col2 = st.columns([1, 2])
            with d_col1:
                debtor_plz = st.text_input("PLZ", key="debtor_plz")
            with d_col2:
                debtor_city = st.text_input("Ort", key="debtor_city")

            debtor_email = st.text_input("E-Mail", key="debtor_email")

        st.divider()

        st.markdown("### Forderung")

        subject = st.text_input("Betreff / Forderungsgrund*")

        f_col1, f_col2, f_col3 = st.columns(3)

        with f_col1:
            principal = st.number_input("Hauptforderung (€)*", min_value=0.0, step=0.01)

        with f_col2:
            due_date = st.date_input("Fälligkeitsdatum*", value=date.today())

        with f_col3:
            interest_rate = st.number_input("Zinssatz (%)", min_value=0.0, max_value=100.0, step=0.1)

        description = st.text_area("Beschreibung")

        external_number = st.text_input("RA-Aktennummer (optional)")

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("Akte anlegen", use_container_width=True)

        with col2:
            cancelled = st.form_submit_button("Abbrechen", use_container_width=True)

        if cancelled:
            st.session_state.show_new_case_form = False
            st.rerun()

        if submitted:
            if not creditor_name or not debtor_name or not subject or principal <= 0:
                st.error("Bitte füllen Sie alle Pflichtfelder (*) aus.")
            else:
                from db import get_db_session
                from backend.services.case_service import CaseService

                with get_db_session() as db:
                    case_service = CaseService(db)

                    case = case_service.create_case(
                        organization_id=org_id,
                        creditor_name=creditor_name,
                        debtor_name=debtor_name,
                        created_by=user_id,
                        subject=subject,
                        description=description,
                        external_number=external_number,
                        creditor_street=creditor_street,
                        creditor_postal_code=creditor_plz,
                        creditor_city=creditor_city,
                        creditor_email=creditor_email,
                        debtor_street=debtor_street,
                        debtor_postal_code=debtor_plz,
                        debtor_city=debtor_city,
                        debtor_email=debtor_email
                    )

                    # Add initial claim
                    case_service.add_claim(
                        case_id=case.id,
                        description=subject,
                        principal_amount=Decimal(str(principal)),
                        due_date=due_date,
                        created_by=user_id,
                        interest_rate=Decimal(str(interest_rate)) if interest_rate else None,
                        interest_start_date=due_date
                    )

                    st.success(f"Akte {case.internal_number} wurde angelegt!")
                    st.session_state.show_new_case_form = False
                    st.session_state.current_case_id = str(case.id)
                    st.rerun()


def show_case_detail(case_id: str):
    """Display detailed case view."""
    from db import get_db_session
    from backend.services.case_service import CaseService
    from backend.services.ledger_service import LedgerService
    from backend.services.document_service import DocumentService
    from backend.services.limitation_service import LimitationService
    from backend.services.eda_service import EDAService

    user_id = get_user_id()

    with get_db_session() as db:
        case_service = CaseService(db)
        ledger = LedgerService(db)
        doc_service = DocumentService(db)
        limitation = LimitationService(db)

        case = case_service.get_case(UUID(case_id))

        if not case:
            st.error("Akte nicht gefunden.")
            if st.button("Zurück"):
                st.session_state.current_case_id = None
                st.rerun()
            return

        # Header
        col1, col2 = st.columns([4, 1])

        with col1:
            st.markdown(f"# Akte {case.internal_number}")
            st.markdown(f"**{case.creditor_name}** ./. **{case.debtor_name}**")
            if case.subject:
                st.caption(case.subject)

        with col2:
            if st.button("← Zurück zur Liste"):
                st.session_state.current_case_id = None
                st.rerun()

        st.divider()

        # Status Row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("**Status**")
            st.markdown(format_status_badge(case.status or 'offen'))

        with col2:
            st.markdown("**Mahnverfahren**")
            st.markdown(format_status_badge(case.dunning_status or 'nicht_beantragt'))

        with col3:
            st.markdown("**Vollstreckung**")
            st.markdown(format_status_badge(case.enforcement_status or 'nicht_begonnen'))

        with col4:
            # Limitation info
            lim_result = limitation.calculate_limitation_date(case.id)
            if lim_result.get('earliest_limitation'):
                days = lim_result.get('days_until_limitation', 0)
                if days <= 30:
                    st.markdown("**⚠️ Verjährung**")
                    st.error(f"{days} Tage")
                elif days <= 180:
                    st.markdown("**Verjährung**")
                    st.warning(f"{days} Tage")
                else:
                    st.markdown("**Verjährung**")
                    st.info(f"{days} Tage")

        st.divider()

        # Balance Card
        balance = ledger.get_case_balance(case.id)
        show_balance_card(balance)

        st.divider()

        # Tabs for different sections
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Übersicht",
            "💰 Forderungskonto",
            "📄 Dokumente",
            "⚖️ Mahnverfahren",
            "🏛️ Vollstreckung",
            "📅 Timeline"
        ])

        # Tab 1: Overview
        with tab1:
            show_case_overview(case, case_service, user_id, db)

        # Tab 2: Ledger
        with tab2:
            show_case_ledger(case, ledger, user_id)

        # Tab 3: Documents
        with tab3:
            show_case_documents(case, doc_service, user_id)

        # Tab 4: Dunning
        with tab4:
            show_case_dunning(case, user_id, db)

        # Tab 5: Enforcement
        with tab5:
            show_case_enforcement(case, user_id, db)

        # Tab 6: Timeline
        with tab6:
            events = case_service.get_timeline_events(case.id, 'rechtsanwalt', limit=50)
            if events:
                for event in events:
                    event_dict = {
                        'id': str(event.id),
                        'title': event.title,
                        'description': event.description,
                        'timestamp': event.event_date.isoformat() if event.event_date else None,
                        'severity': event.severity,
                        'actor_name': event.actor_name,
                        'category': event.category
                    }
                    with st.container():
                        severity = event.severity or 'info'
                        icons = {'success': '✅', 'warning': '⚠️', 'error': '❌', 'info': 'ℹ️'}
                        icon = icons.get(severity, '•')

                        st.markdown(f"**{icon} {event.title}**")
                        if event.description:
                            st.caption(event.description)

                        meta = []
                        if event.actor_name:
                            meta.append(event.actor_name)
                        if event.event_date:
                            meta.append(format_datetime(event.event_date))
                        if meta:
                            st.caption(" | ".join(meta))

                        st.divider()
            else:
                st.info("Keine Timeline-Einträge vorhanden.")


def show_case_overview(case, case_service, user_id, db):
    """Show case overview tab."""
    st.markdown("### Parteien")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Gläubigerin**")
        st.text(case.creditor_name)
        if case.creditor_street:
            st.text(case.creditor_street)
        if case.creditor_postal_code or case.creditor_city:
            st.text(f"{case.creditor_postal_code or ''} {case.creditor_city or ''}")
        if case.creditor_email:
            st.text(f"E-Mail: {case.creditor_email}")

    with col2:
        st.markdown("**Schuldner**")
        st.text(case.debtor_name)
        if case.debtor_street:
            st.text(case.debtor_street)
        if case.debtor_postal_code or case.debtor_city:
            st.text(f"{case.debtor_postal_code or ''} {case.debtor_city or ''}")
        if case.debtor_email:
            st.text(f"E-Mail: {case.debtor_email}")
        if case.debtor_birth_date:
            st.text(f"Geb.: {format_date(case.debtor_birth_date)}")

    st.divider()

    st.markdown("### Forderungen")

    claims = case_service.get_claims_for_case(case.id)

    if claims:
        for claim in claims:
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 2])

                with col1:
                    st.markdown(f"**{claim.description}**")
                    st.caption(f"Fällig seit: {format_date(claim.due_date)}")

                with col2:
                    st.markdown(format_currency(claim.principal_amount))
                    if claim.interest_rate:
                        st.caption(f"Zinsen: {claim.interest_rate}% p.a.")

                with col3:
                    if claim.is_titled:
                        st.success("Tituliert")
                        st.caption(f"Titel vom {format_date(claim.title_date)}")

                st.divider()
    else:
        st.info("Keine Forderungen angelegt.")


def show_case_ledger(case, ledger, user_id):
    """Show case ledger tab."""
    st.markdown("### Forderungskonto")

    bookings = ledger.get_bookings_for_case(case.id)

    if bookings:
        # Convert to display format
        booking_data = []
        for b in bookings:
            booking_data.append({
                'booking_date': b.booking_date,
                'debit_credit': b.debit_credit,
                'amount': float(b.amount),
                'category': b.category,
                'description': b.description,
                'status': b.status
            })

        show_ledger_table(booking_data, show_status=True)
    else:
        st.info("Keine Buchungen vorhanden.")

    st.divider()

    # Add booking form
    with st.expander("➕ Neue Buchung hinzufügen"):
        with st.form("add_booking"):
            col1, col2 = st.columns(2)

            with col1:
                booking_date = st.date_input("Datum", value=date.today())
                category = st.selectbox(
                    "Kategorie",
                    ["hauptforderung", "zinsen", "ra_gebuehren", "nebenkosten", "gerichtskosten"]
                )

            with col2:
                debit_credit = st.selectbox("Buchungsart", [("S", "Soll (Forderung)"), ("H", "Haben (Zahlung)")], format_func=lambda x: x[1])
                amount = st.number_input("Betrag (€)", min_value=0.01, step=0.01)

            description = st.text_input("Beschreibung")

            if st.form_submit_button("Buchen"):
                ledger.create_booking(
                    case_id=case.id,
                    booking_date=booking_date,
                    debit_credit=debit_credit[0],
                    amount=Decimal(str(amount)),
                    category=category,
                    description=description,
                    source='rechtsanwalt',
                    created_by=user_id
                )
                st.success("Buchung hinzugefügt!")
                st.rerun()


def show_case_documents(case, doc_service, user_id):
    """Show case documents tab."""
    st.markdown("### Dokumente")

    documents = doc_service.get_documents_for_case(case.id)

    if documents:
        for doc in documents:
            doc_dict = {
                'id': str(doc.id),
                'title': doc.title,
                'original_filename': doc.original_filename,
                'file_type': doc.file_type,
                'document_type': doc.document_type,
                'created_at': doc.created_at
            }
            show_document_card(doc_dict)
    else:
        st.info("Keine Dokumente vorhanden.")

    st.divider()

    # Upload new document
    st.markdown("### 📤 Dokument hochladen")

    uploaded_file = st.file_uploader(
        "Datei auswählen",
        type=['pdf', 'docx', 'doc', 'xlsx', 'xls', 'png', 'jpg', 'jpeg', 'eml', 'msg'],
        key="doc_upload"
    )

    if uploaded_file:
        col1, col2 = st.columns(2)

        with col1:
            doc_type = st.selectbox(
                "Dokumenttyp",
                ["rechnung", "vertrag", "mahnung", "schreiben_ra", "schreiben_schuldner", "sonstiges"]
            )

        with col2:
            visible_creditor = st.checkbox("Für Gläubigerin sichtbar", value=True)
            visible_debtor = st.checkbox("Für Schuldner sichtbar", value=False)

        if st.button("Hochladen"):
            from db import get_db_session
            from backend.services.document_service import DocumentService as DS

            with get_db_session() as db:
                ds = DS(db)
                ds.upload_document(
                    file_content=uploaded_file.read(),
                    filename=uploaded_file.name,
                    uploaded_by=user_id,
                    organization_id=case.organization_id,
                    case_id=case.id,
                    document_type=doc_type,
                    visible_to_creditor=visible_creditor,
                    visible_to_debtor=visible_debtor
                )

            st.success("Dokument hochgeladen!")
            st.rerun()


def show_case_dunning(case, user_id, db):
    """Show dunning procedure tab."""
    from backend.services.eda_service import EDAService

    st.markdown("### Mahnverfahren")

    eda = EDAService(db)

    # Current status
    st.markdown(f"**Aktueller Status:** {format_status_badge(case.dunning_status or 'nicht_beantragt')}")

    if case.mb_application_date:
        st.info(f"MB beantragt am: {format_date(case.mb_application_date)}")
    if case.mb_delivery_date:
        st.success(f"MB zugestellt am: {format_date(case.mb_delivery_date)}")
    if case.vb_issue_date:
        st.success(f"VB erlassen am: {format_date(case.vb_issue_date)}")
    if case.objection_date:
        st.warning(f"Widerspruch am: {format_date(case.objection_date)}")

    st.divider()

    # Actions based on status
    if case.dunning_status in [None, 'nicht_beantragt']:
        st.markdown("### Mahnbescheid beantragen")

        if st.button("📝 MB-Antrag erstellen", use_container_width=True):
            try:
                application = eda.create_mb_application(case.id, user_id)
                st.success(f"MB-Antrag erstellt!")
                st.session_state.current_dunning_app = str(application.id)
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    elif case.dunning_status == 'mb_zugestellt' and not case.objection_date:
        st.markdown("### Vollstreckungsbescheid beantragen")

        if st.button("📝 VB-Antrag erstellen", use_container_width=True):
            try:
                application = eda.create_vb_application(case.id, user_id)
                st.success(f"VB-Antrag erstellt!")
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    # Record delivery/objection
    with st.expander("📬 Zustellung/Ereignis eintragen"):
        event_type = st.selectbox(
            "Ereignis",
            ["MB zugestellt", "Widerspruch eingegangen", "VB erlassen"]
        )
        event_date = st.date_input("Datum")
        court_az = st.text_input("Aktenzeichen (optional)")

        if st.button("Eintragen"):
            from backend.services.case_service import CaseService

            cs = CaseService(db)

            if event_type == "MB zugestellt":
                cs.update_case(
                    case.id, user_id,
                    dunning_status=DunningStatus.MB_ZUGESTELLT,
                    mb_delivery_date=event_date,
                    court_file_number=court_az or case.court_file_number
                )
            elif event_type == "Widerspruch eingegangen":
                cs.update_case(
                    case.id, user_id,
                    dunning_status=DunningStatus.WIDERSPRUCH,
                    objection_date=event_date
                )
            elif event_type == "VB erlassen":
                cs.update_case(
                    case.id, user_id,
                    dunning_status=DunningStatus.VB_ERLASSEN,
                    vb_issue_date=event_date
                )

            st.success("Ereignis eingetragen!")
            st.rerun()


def show_case_enforcement(case, user_id, db):
    """Show enforcement tab."""
    from backend.services.enforcement_service import EnforcementService

    st.markdown("### Zwangsvollstreckung")

    enforcement = EnforcementService(db)

    # Check if case has title
    if case.dunning_status not in ['vb_erlassen', 'titel_rechtskraeftig']:
        st.warning("Zwangsvollstreckung erfordert einen Titel (VB oder Urteil).")
        return

    # Current status
    st.markdown(f"**Status:** {format_status_badge(case.enforcement_status or 'nicht_begonnen')}")

    st.divider()

    # Get existing measures
    measures = enforcement.get_measures_for_case(case.id)

    if measures:
        st.markdown("### Laufende Maßnahmen")

        for measure in measures:
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 2])

                with col1:
                    st.markdown(f"**{enforcement.MEASURE_TYPES.get(measure.measure_type, measure.measure_type)}**")
                    if measure.target_name:
                        st.caption(f"Ziel: {measure.target_name}")

                with col2:
                    st.markdown(format_status_badge(measure.status))

                with col3:
                    if measure.result_amount:
                        st.metric("Ergebnis", format_currency(measure.result_amount))

                st.divider()

    # New measures
    st.markdown("### Neue Maßnahme")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("👮 GV-Auftrag", use_container_width=True):
            measure = enforcement.create_gv_auftrag(case.id, user_id)
            st.success("GV-Auftrag angelegt!")
            st.rerun()

    with col2:
        if st.button("🏦 PfüB Bank", use_container_width=True):
            st.session_state.show_pfueb_form = True

    # PfüB Form
    if st.session_state.get('show_pfueb_form'):
        with st.form("pfueb_form"):
            st.markdown("### PfüB - Bankpfändung")

            bank_name = st.text_input("Bank/Drittschuldner")
            iban = st.text_input("IBAN")
            address = st.text_area("Adresse")

            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Anlegen"):
                    measure = enforcement.create_measure(
                        case_id=case.id,
                        measure_type='pfueb_bank',
                        created_by=user_id,
                        target_name=bank_name,
                        target_iban=iban,
                        target_address=address
                    )
                    st.session_state.show_pfueb_form = False
                    st.success("PfüB angelegt!")
                    st.rerun()

            with col2:
                if st.form_submit_button("Abbrechen"):
                    st.session_state.show_pfueb_form = False
                    st.rerun()

    # VV Upload
    st.divider()
    st.markdown("### 📋 Vermögensverzeichnis importieren")

    vv_file = st.file_uploader("VV-PDF hochladen", type=['pdf'], key="vv_upload")

    if vv_file:
        if st.button("VV analysieren"):
            from backend.services.document_service import DocumentService

            ds = DocumentService(db)

            # Upload document
            doc = ds.upload_document(
                file_content=vv_file.read(),
                filename=vv_file.name,
                uploaded_by=user_id,
                organization_id=case.organization_id,
                case_id=case.id,
                document_type='vermoegensverzeichnis'
            )

            # Process VV
            assets = enforcement.process_vermoegensverzeichnis(
                case.id, doc.id, user_id
            )

            st.success(f"VV analysiert! {len(assets)} Vermögenspositionen gefunden.")
            st.rerun()


if __name__ == "__main__":
    main()
