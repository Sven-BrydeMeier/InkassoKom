"""
Debtor Overview Page
Main overview for debtors showing their cases and payment progress
"""
import streamlit as st
from uuid import UUID
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.utils.session import init_session, require_role, get_user_id
from app.utils.formatting import format_currency, format_date, format_datetime, format_status_badge
from app.utils.components import show_payment_progress
from config.settings import UserRole

st.set_page_config(page_title="Übersicht - NotarFlow", page_icon="📊", layout="wide")

init_session()


@require_role([UserRole.SCHULDNER])
def main():
    user_id = get_user_id()

    st.markdown("# 📊 Übersicht")
    st.caption("Ihre offenen Forderungen und Zahlungsfortschritt")

    from db import get_db_session
    from backend.services.case_service import CaseService
    from backend.services.ledger_service import LedgerService

    with get_db_session() as db:
        case_service = CaseService(db)
        ledger = LedgerService(db)

        # Get debtor's cases
        cases = case_service.get_cases_for_debtor(user_id)

        if not cases:
            st.success("✅ Keine offenen Forderungen.")
            return

        # Show each case
        for case in cases:
            balance = ledger.get_case_balance(case.id)

            total_soll = balance.get('total_soll', 0)
            total_haben = balance.get('total_haben', 0)
            total_open = balance.get('total_open', 0)

            with st.container():
                st.markdown(f"## Akte {case.internal_number}")
                st.caption(f"Gläubiger: **{case.creditor_name}**")

                if case.subject:
                    st.info(f"Betreff: {case.subject}")

                st.divider()

                # Payment progress visualization
                st.markdown("### 📊 Zahlungsfortschritt")

                if total_soll > 0:
                    paid_percent = min((total_haben / total_soll) * 100, 100)

                    # Progress bar with colors
                    progress_color = "normal" if paid_percent < 100 else "off"

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric(
                            "Gesamtforderung",
                            format_currency(total_soll),
                            help="Ursprünglicher Gesamtbetrag inkl. Zinsen und Kosten"
                        )

                    with col2:
                        st.metric(
                            "Bereits gezahlt",
                            format_currency(total_haben),
                            delta=f"{paid_percent:.1f}%",
                            delta_color="normal"
                        )

                    with col3:
                        if total_open <= 0:
                            st.metric(
                                "Noch offen",
                                format_currency(0),
                                delta="Vollständig bezahlt!",
                                delta_color="normal"
                            )
                        else:
                            st.metric(
                                "Noch offen",
                                format_currency(total_open)
                            )

                    # Visual progress bar
                    st.markdown("#### Fortschritt")

                    # Create colored progress representation
                    if paid_percent >= 100:
                        st.progress(1.0)
                        st.success("🎉 Diese Forderung ist vollständig beglichen!")
                    else:
                        st.progress(paid_percent / 100)

                        # Show remaining amount prominently
                        st.warning(f"💰 Noch zu zahlen: **{format_currency(total_open)}**")

                st.divider()

                # Show status
                st.markdown("### 📋 Status")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Verfahrensstatus**")
                    st.markdown(format_status_badge(case.status or 'offen'))

                with col2:
                    if case.payment_plan_status:
                        st.markdown("**Ratenzahlung**")
                        st.markdown(format_status_badge(case.payment_plan_status))

                # Dunning/Enforcement info (visible to debtor)
                if case.dunning_status and case.dunning_status != 'nicht_beantragt':
                    st.divider()
                    st.markdown("### ⚖️ Mahnverfahren")

                    if case.dunning_status == 'mb_zugestellt':
                        st.warning("📬 Mahnbescheid zugestellt")
                        if case.mb_delivery_date:
                            st.caption(f"Zustellungsdatum: {format_date(case.mb_delivery_date)}")

                    elif case.dunning_status == 'vb_erlassen':
                        st.error("📜 Vollstreckungsbescheid erlassen")
                        if case.vb_issue_date:
                            st.caption(f"Datum: {format_date(case.vb_issue_date)}")

                    elif case.dunning_status == 'titel_rechtskraeftig':
                        st.error("⚠️ Titel ist rechtskräftig")

                st.divider()

                # Recent timeline events
                st.markdown("### 📅 Letzte Ereignisse")

                events = case_service.get_timeline_events(case.id, 'schuldner', limit=5)

                if events:
                    for event in events:
                        severity = event.severity or 'info'
                        icons = {'success': '✅', 'warning': '⚠️', 'error': '❌', 'info': 'ℹ️'}
                        icon = icons.get(severity, '•')

                        st.markdown(f"**{icon} {event.title}**")
                        if event.description:
                            st.caption(event.description)
                        st.caption(format_datetime(event.event_date))
                        st.markdown("---")
                else:
                    st.info("Keine Ereignisse vorhanden.")

                st.divider()

                # Actions
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("📄 Dokumente anzeigen", key=f"docs_{case.id}", use_container_width=True):
                        st.session_state.current_case_id = str(case.id)
                        st.session_state.show_documents = True

                with col2:
                    if total_open > 0 and not case.payment_plan_status:
                        if st.button("📅 Ratenzahlung anfragen", key=f"rate_{case.id}", use_container_width=True):
                            st.session_state.current_case_id = str(case.id)
                            st.session_state.show_payment_plan_request = True

            st.markdown("---")
            st.markdown("---")


if __name__ == "__main__":
    main()
