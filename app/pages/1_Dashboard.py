"""
Lawyer Dashboard Page
Main dashboard for Rechtsanwalt role
"""
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.utils.session import init_session, require_role, get_user_id, get_organization_id
from app.utils.formatting import format_currency, format_date, format_datetime
from app.utils.components import show_timeline, show_limitation_warning
from config.settings import UserRole

# Page config
st.set_page_config(page_title="Dashboard - NotarFlow", page_icon="📊", layout="wide")

init_session()

# Require lawyer role
@require_role([UserRole.ADMIN, UserRole.RECHTSANWALT])
def main():
    st.markdown("# 📊 Dashboard")

    user_id = get_user_id()
    org_id = get_organization_id()

    if not org_id:
        st.warning("Keine Organisation zugeordnet.")
        return

    # Import services
    from db import get_db_session
    from backend.services.case_service import CaseService
    from backend.services.notification_service import NotificationService
    from backend.services.limitation_service import LimitationService
    from backend.services.document_service import DocumentService
    from backend.services.ledger_service import LedgerService

    with get_db_session() as db:
        case_service = CaseService(db)
        notification_service = NotificationService(db)
        limitation_service = LimitationService(db)
        doc_service = DocumentService(db)

        # Quick Stats Row
        stats = case_service.get_organization_statistics(org_id)
        inbox_items = doc_service.get_inbox_items(org_id, status='new')
        notifications = notification_service.get_unread_notifications(user_id)
        warnings = limitation_service.check_all_cases_limitation(org_id, warning_months=3)

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                "Aktive Akten",
                stats.get('total_cases', 0),
                help="Gesamtzahl aller aktiven Inkasso-Akten"
            )

        with col2:
            st.metric(
                "Gesamtforderungen",
                format_currency(stats.get('total_open', 0)),
                help="Summe aller offenen Forderungen"
            )

        with col3:
            st.metric(
                "Posteingang",
                len(inbox_items),
                delta=f"{len(inbox_items)} neu" if inbox_items else None,
                delta_color="normal" if inbox_items else "off"
            )

        with col4:
            st.metric(
                "Verjährungswarnungen",
                len(warnings),
                delta="Kritisch!" if any(w['severity'] == 'critical' for w in warnings) else None,
                delta_color="inverse"
            )

        with col5:
            st.metric(
                "Benachrichtigungen",
                len(notifications)
            )

        st.divider()

        # Main Content Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📌 Aktuelles",
            "⚠️ Verjährungen",
            "📬 Posteingang",
            "💰 Zahlungen"
        ])

        # Tab 1: Activity Feed
        with tab1:
            st.markdown("### Aktuelle Ereignisse")

            feed = notification_service.get_activity_feed(
                user_id=user_id,
                organization_id=org_id,
                limit=20
            )

            if not feed:
                st.info("Keine aktuellen Ereignisse vorhanden.")
            else:
                for event in feed[:15]:
                    with st.container():
                        col1, col2 = st.columns([5, 1])

                        with col1:
                            severity = event.get('severity', 'info')
                            icons = {'success': '✅', 'warning': '⚠️', 'error': '❌', 'info': 'ℹ️'}
                            icon = icons.get(severity, '•')

                            st.markdown(f"**{icon} {event.get('title', '')}**")

                            if event.get('description'):
                                st.caption(event['description'])

                            meta = []
                            if event.get('case_number'):
                                meta.append(f"Akte {event['case_number']}")
                            if event.get('actor_name'):
                                meta.append(event['actor_name'])
                            if event.get('timestamp'):
                                meta.append(format_datetime(event['timestamp']))

                            if meta:
                                st.caption(" | ".join(meta))

                        with col2:
                            if event.get('case_id'):
                                if st.button("→", key=f"goto_{event.get('id')}"):
                                    st.session_state.current_case_id = event['case_id']

                        st.divider()

        # Tab 2: Limitation Warnings
        with tab2:
            st.markdown("### Verjährungswarnungen")

            if not warnings:
                st.success("✅ Keine drohenden Verjährungen in den nächsten 3 Monaten.")
            else:
                for warning in warnings:
                    days = warning['days_remaining']
                    severity = warning['severity']

                    if severity == 'critical':
                        st.error(
                            f"⚠️ **KRITISCH:** Akte {warning['internal_number']} - "
                            f"Verjährung in **{days} Tagen** ({warning['limitation_date']})\n\n"
                            f"Schuldner: {warning['debtor_name']}"
                        )
                    else:
                        st.warning(
                            f"⏰ Akte {warning['internal_number']} - "
                            f"Verjährung in {days} Tagen ({warning['limitation_date']})\n\n"
                            f"Schuldner: {warning['debtor_name']}"
                        )

                    if st.button(f"Akte öffnen", key=f"open_lim_{warning['case_id']}"):
                        st.session_state.current_case_id = warning['case_id']

                    st.divider()

        # Tab 3: Inbox Preview
        with tab3:
            st.markdown("### Posteingang")

            if not inbox_items:
                st.success("📭 Posteingang ist leer.")
            else:
                for item in inbox_items[:10]:
                    doc = doc_service.get_document(item.document_id)
                    if doc:
                        with st.container():
                            col1, col2, col3 = st.columns([3, 2, 1])

                            with col1:
                                st.markdown(f"📄 **{doc.original_filename}**")
                                st.caption(f"Eingegangen: {format_datetime(item.received_at)}")
                                st.caption(f"Quelle: {item.source}")

                            with col2:
                                if item.ai_analysis:
                                    doc_type = item.ai_analysis.get('document_type', 'Unbekannt')
                                    st.caption(f"Erkannt als: {doc_type}")

                            with col3:
                                if st.button("Bearbeiten", key=f"process_{item.id}"):
                                    st.session_state.current_inbox_item = str(item.id)

                            st.divider()

                if len(inbox_items) > 10:
                    st.info(f"... und {len(inbox_items) - 10} weitere Dokumente")

        # Tab 4: Pending Payments
        with tab4:
            st.markdown("### Gemeldete Zahlungseingänge")

            ledger = LedgerService(db)
            pending = ledger.get_pending_payments(org_id)

            if not pending:
                st.success("✅ Keine ausstehenden Zahlungsbestätigungen.")
            else:
                for booking in pending:
                    case = case_service.get_case(booking.case_id)

                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 2])

                        with col1:
                            st.markdown(f"**{format_currency(booking.amount)}**")
                            st.caption(f"Akte: {case.internal_number if case else 'N/A'}")
                            st.caption(f"Gemeldet: {format_datetime(booking.reported_at)}")

                        with col2:
                            st.caption(f"Referenz: {booking.reference or '-'}")
                            st.caption(f"Datum: {format_date(booking.booking_date)}")

                        with col3:
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button("✓", key=f"approve_{booking.id}", help="Akzeptieren"):
                                    ledger.approve_payment(booking.id, user_id)
                                    st.success("Zahlung akzeptiert!")
                                    st.rerun()
                            with col_b:
                                if st.button("✗", key=f"reject_{booking.id}", help="Ablehnen"):
                                    st.session_state.reject_booking = str(booking.id)

                        st.divider()

        # Rejection Modal
        if 'reject_booking' in st.session_state:
            with st.form("reject_form"):
                st.markdown("### Zahlung ablehnen")
                reason = st.text_area("Ablehnungsgrund")

                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Ablehnen"):
                        ledger = LedgerService(db)
                        ledger.reject_payment(
                            UUID(st.session_state.reject_booking),
                            user_id,
                            reason
                        )
                        del st.session_state.reject_booking
                        st.success("Zahlung abgelehnt.")
                        st.rerun()

                with col2:
                    if st.form_submit_button("Abbrechen"):
                        del st.session_state.reject_booking
                        st.rerun()


if __name__ == "__main__":
    main()
