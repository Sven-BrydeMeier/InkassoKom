"""
Creditor Payment Reporting
Page for creditors to report incoming payments
"""
import streamlit as st
from uuid import UUID
from datetime import date
from decimal import Decimal
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.utils.session import init_session, require_role, get_user_id
from app.utils.formatting import format_currency, format_date, format_datetime, format_status_badge
from config.settings import UserRole

st.set_page_config(page_title="Zahlungseingänge - NotarFlow", page_icon="💳", layout="wide")

init_session()


@require_role([UserRole.GLAEUBIGERIN])
def main():
    user_id = get_user_id()

    st.markdown("# 💳 Zahlungseingänge melden")
    st.caption("Melden Sie eingegangene Zahlungen zur Verbuchung")

    from db import get_db_session
    from backend.services.case_service import CaseService
    from backend.services.ledger_service import LedgerService

    with get_db_session() as db:
        case_service = CaseService(db)
        ledger = LedgerService(db)

        # Get creditor's cases
        cases = case_service.get_cases_for_creditor(user_id)

        if not cases:
            st.info("Sie haben keine aktiven Forderungen.")
            return

        # Tabs
        tab1, tab2 = st.tabs(["➕ Neue Meldung", "📋 Gemeldete Zahlungen"])

        # Tab 1: New payment report
        with tab1:
            st.markdown("### Zahlungseingang melden")

            with st.form("payment_report"):
                # Select case
                case_options = {str(c.id): f"{c.internal_number} - {c.debtor_name}" for c in cases}
                selected_case = st.selectbox(
                    "Forderung auswählen",
                    options=list(case_options.keys()),
                    format_func=lambda x: case_options[x]
                )

                if selected_case:
                    # Show current balance
                    balance = ledger.get_case_balance(UUID(selected_case))
                    st.info(f"Offener Betrag: {format_currency(balance.get('total_open', 0))}")

                col1, col2 = st.columns(2)

                with col1:
                    payment_date = st.date_input("Zahlungsdatum", value=date.today())

                with col2:
                    amount = st.number_input(
                        "Betrag (€)",
                        min_value=0.01,
                        step=0.01,
                        format="%.2f"
                    )

                reference = st.text_input(
                    "Referenz / Verwendungszweck",
                    help="Zahlungsreferenz, Überweisungsbetreff o.ä."
                )

                notes = st.text_area(
                    "Anmerkungen (optional)",
                    help="Zusätzliche Informationen zur Zahlung"
                )

                st.divider()

                st.warning(
                    "⚠️ **Hinweis:** Die gemeldete Zahlung wird erst nach Prüfung und "
                    "Freigabe durch den Rechtsanwalt im Forderungskonto verbucht."
                )

                submitted = st.form_submit_button("Zahlung melden", use_container_width=True)

                if submitted:
                    if not selected_case or amount <= 0 or not reference:
                        st.error("Bitte füllen Sie alle Pflichtfelder aus.")
                    else:
                        ledger.report_payment(
                            case_id=UUID(selected_case),
                            payment_date=payment_date,
                            amount=Decimal(str(amount)),
                            reference=reference,
                            reported_by=user_id,
                            description=notes
                        )
                        st.success("✅ Zahlungseingang erfolgreich gemeldet!")
                        st.info("Der Rechtsanwalt wird die Zahlung prüfen und freigeben.")
                        st.rerun()

        # Tab 2: Reported payments
        with tab2:
            st.markdown("### Gemeldete Zahlungen")

            # Get all bookings for creditor's cases
            all_bookings = []

            for case in cases:
                bookings = ledger.get_bookings_for_case(case.id)
                for b in bookings:
                    if b.source == 'glaeubiger':
                        all_bookings.append({
                            'id': str(b.id),
                            'case_number': case.internal_number,
                            'debtor': case.debtor_name,
                            'amount': b.amount,
                            'date': b.booking_date,
                            'reference': b.reference,
                            'status': b.status,
                            'reported_at': b.reported_at,
                            'accepted_at': b.accepted_at,
                            'rejection_reason': b.rejection_reason
                        })

            # Sort by reported date
            all_bookings.sort(key=lambda x: x.get('reported_at') or '', reverse=True)

            if not all_bookings:
                st.info("Sie haben noch keine Zahlungen gemeldet.")
            else:
                for booking in all_bookings:
                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 2])

                        with col1:
                            st.markdown(f"**{format_currency(booking['amount'])}**")
                            st.caption(f"Akte {booking['case_number']} - {booking['debtor']}")
                            st.caption(f"Referenz: {booking['reference'] or '-'}")

                        with col2:
                            st.caption(f"Gemeldet: {format_datetime(booking['reported_at'])}")
                            st.caption(f"Zahlungsdatum: {format_date(booking['date'])}")

                        with col3:
                            status = booking['status']
                            if status == 'gemeldet':
                                st.warning("⏳ Prüfung ausstehend")
                            elif status == 'akzeptiert' or status == 'verbucht':
                                st.success("✅ Verbucht")
                                if booking['accepted_at']:
                                    st.caption(f"am {format_datetime(booking['accepted_at'])}")
                            elif status == 'abgelehnt':
                                st.error("❌ Abgelehnt")
                                if booking['rejection_reason']:
                                    st.caption(f"Grund: {booking['rejection_reason']}")

                        st.divider()


if __name__ == "__main__":
    main()
