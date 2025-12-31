"""
Creditor Dashboard - Aktuelles
Dashboard for Gläubigerin showing latest updates
"""
import streamlit as st
from uuid import UUID
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.utils.session import init_session, require_role, get_user_id
from app.utils.formatting import format_currency, format_date, format_datetime, format_status_badge
from app.utils.components import show_balance_card, show_timeline
from config.settings import UserRole

st.set_page_config(page_title="Aktuelles - NotarFlow", page_icon="📊", layout="wide")

init_session()


@require_role([UserRole.GLAEUBIGERIN])
def main():
    user_id = get_user_id()

    st.markdown("# 📊 Aktuelles")
    st.caption("Übersicht über Ihre Inkasso-Forderungen")

    from db import get_db_session
    from backend.services.case_service import CaseService
    from backend.services.ledger_service import LedgerService
    from backend.services.notification_service import NotificationService

    with get_db_session() as db:
        case_service = CaseService(db)
        ledger = LedgerService(db)
        notification_service = NotificationService(db)

        # Get creditor's cases
        cases = case_service.get_cases_for_creditor(user_id)

        if not cases:
            st.info("Sie haben keine aktiven Forderungen.")
            return

        # Summary metrics
        total_cases = len(cases)
        total_open = 0
        total_paid = 0

        for case in cases:
            balance = ledger.get_case_balance(case.id)
            total_open += balance.get('total_open', 0)
            total_paid += balance.get('total_haben', 0)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Aktive Forderungen", total_cases)

        with col2:
            st.metric("Gesamtforderung", format_currency(total_open + total_paid))

        with col3:
            st.metric("Offen", format_currency(total_open))

        with col4:
            st.metric("Eingegangen", format_currency(total_paid))

        st.divider()

        # Top case card (first case)
        if cases:
            top_case = cases[0]
            balance = ledger.get_case_balance(top_case.id)

            st.markdown("### 📌 Aktuelle Forderung")

            with st.container():
                col1, col2 = st.columns([3, 2])

                with col1:
                    st.markdown(f"**Akte {top_case.internal_number}**")
                    st.markdown(f"Schuldner: **{top_case.debtor_name}**")
                    if top_case.subject:
                        st.caption(top_case.subject)

                with col2:
                    st.metric("Offener Betrag", format_currency(balance.get('total_open', 0)))

                # Status
                st.markdown(f"Status: {format_status_badge(top_case.status or 'offen')}")

                if st.button("Forderung anzeigen", key="view_top"):
                    st.session_state.current_case_id = str(top_case.id)

        st.divider()

        # Activity feed
        st.markdown("### 📋 Letzte Aktivitäten")

        # Get timeline events for all creditor cases
        all_events = []
        for case in cases[:5]:  # Limit to first 5 cases
            events = case_service.get_timeline_events(case.id, 'glaeubigerin', limit=10)
            for event in events:
                all_events.append({
                    'id': str(event.id),
                    'title': event.title,
                    'description': event.description,
                    'timestamp': event.event_date.isoformat() if event.event_date else None,
                    'severity': event.severity,
                    'case_number': case.internal_number,
                    'case_id': str(case.id)
                })

        # Sort by timestamp
        all_events.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        if all_events:
            for event in all_events[:15]:
                with st.container():
                    severity = event.get('severity', 'info')
                    icons = {'success': '✅', 'warning': '⚠️', 'error': '❌', 'info': 'ℹ️'}
                    icon = icons.get(severity, '•')

                    col1, col2 = st.columns([5, 1])

                    with col1:
                        st.markdown(f"**{icon} {event.get('title', '')}**")
                        if event.get('description'):
                            st.caption(event['description'])
                        st.caption(f"Akte {event.get('case_number', '')} | {format_datetime(event.get('timestamp'))}")

                    with col2:
                        if st.button("→", key=f"goto_{event.get('id')}"):
                            st.session_state.current_case_id = event.get('case_id')

                    st.divider()
        else:
            st.info("Keine Aktivitäten vorhanden.")

        # Notifications
        notifications = notification_service.get_unread_notifications(user_id, limit=5)

        if notifications:
            st.divider()
            st.markdown("### 🔔 Benachrichtigungen")

            for notif in notifications:
                with st.container():
                    notif_icons = {'info': 'ℹ️', 'warning': '⚠️', 'error': '❌', 'success': '✅'}
                    icon = notif_icons.get(notif.notification_type, 'ℹ️')

                    col1, col2 = st.columns([5, 1])

                    with col1:
                        st.markdown(f"**{icon} {notif.title}**")
                        st.caption(notif.message)
                        st.caption(format_datetime(notif.created_at))

                    with col2:
                        if st.button("✓", key=f"read_{notif.id}"):
                            notification_service.mark_as_read(notif.id)
                            st.rerun()

                    st.divider()


if __name__ == "__main__":
    main()
