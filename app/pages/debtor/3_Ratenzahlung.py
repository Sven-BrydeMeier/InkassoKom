"""
Debtor Payment Plan Page
Request and manage payment plans
"""
import streamlit as st
from uuid import UUID
from datetime import date, timedelta
from decimal import Decimal
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.utils.session import init_session, require_role, get_user_id
from app.utils.formatting import format_currency, format_date, format_datetime, format_status_badge
from config.settings import UserRole

st.set_page_config(page_title="Ratenzahlung - NotarFlow", page_icon="📅", layout="wide")

init_session()


@require_role([UserRole.SCHULDNER])
def main():
    user_id = get_user_id()

    st.markdown("# 📅 Ratenzahlung")
    st.caption("Verwalten Sie Ihre Ratenzahlungsvereinbarungen")

    from db import get_db_session
    from backend.services.case_service import CaseService
    from backend.services.ledger_service import LedgerService
    from db.models import PaymentPlan, PaymentPlanInstallment

    with get_db_session() as db:
        case_service = CaseService(db)
        ledger = LedgerService(db)

        # Get debtor's cases
        cases = case_service.get_cases_for_debtor(user_id)

        if not cases:
            st.info("Keine Forderungen vorhanden.")
            return

        # Check for active payment plans
        active_plans = []
        cases_without_plans = []

        for case in cases:
            balance = ledger.get_case_balance(case.id)
            if balance.get('total_open', 0) <= 0:
                continue  # Skip paid cases

            plans = db.query(PaymentPlan).filter(
                PaymentPlan.case_id == case.id,
                PaymentPlan.status.in_(['aktiv', 'angefragt', 'entwurf', 'geprueft', 'freigegeben'])
            ).all()

            if plans:
                for plan in plans:
                    active_plans.append((case, plan))
            else:
                cases_without_plans.append(case)

        # Tabs
        tab1, tab2 = st.tabs(["📋 Aktive Ratenzahlungen", "➕ Ratenzahlung anfragen"])

        # Tab 1: Active payment plans
        with tab1:
            if not active_plans:
                st.info("Sie haben keine aktiven Ratenzahlungsvereinbarungen.")
            else:
                for case, plan in active_plans:
                    with st.container():
                        st.markdown(f"### Akte {case.internal_number}")
                        st.caption(f"Gläubiger: {case.creditor_name}")

                        # Plan status
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.markdown("**Status**")
                            status = plan.status
                            if status == 'angefragt':
                                st.warning("⏳ Anfrage eingereicht")
                            elif status == 'entwurf':
                                st.info("📝 Entwurf wird erstellt")
                            elif status == 'geprueft':
                                st.info("🔍 In Prüfung")
                            elif status == 'freigegeben':
                                st.success("✅ Freigegeben - warte auf Start")
                            elif status == 'aktiv':
                                st.success("✅ Aktiv")
                            elif status == 'verzoegert':
                                st.error("⚠️ Verzögert")

                        with col2:
                            st.markdown("**Gesamtbetrag**")
                            st.markdown(format_currency(plan.total_amount))

                        with col3:
                            st.markdown("**Monatliche Rate**")
                            st.markdown(format_currency(plan.installment_amount))

                        st.divider()

                        # Show installments if plan is active
                        if plan.status in ['aktiv', 'verzoegert', 'freigegeben']:
                            st.markdown("#### Ratenplan")

                            installments = db.query(PaymentPlanInstallment).filter(
                                PaymentPlanInstallment.payment_plan_id == plan.id
                            ).order_by(PaymentPlanInstallment.installment_number).all()

                            for inst in installments:
                                col1, col2, col3 = st.columns([2, 3, 2])

                                with col1:
                                    status_icon = "⏳"
                                    if inst.status == 'paid':
                                        status_icon = "✅"
                                    elif inst.status == 'overdue':
                                        status_icon = "❌"

                                    st.markdown(f"{status_icon} **Rate {inst.installment_number}**")

                                with col2:
                                    st.markdown(f"Fällig: {format_date(inst.due_date)}")
                                    st.markdown(format_currency(inst.amount))

                                with col3:
                                    if inst.status == 'pending':
                                        days_until = (inst.due_date - date.today()).days
                                        if days_until < 0:
                                            st.error(f"Überfällig seit {abs(days_until)} Tagen!")
                                        elif days_until <= 7:
                                            st.warning(f"Fällig in {days_until} Tagen")
                                        else:
                                            st.info(f"In {days_until} Tagen")
                                    elif inst.status == 'paid':
                                        st.success("Bezahlt")
                                        if inst.paid_at:
                                            st.caption(format_date(inst.paid_at))
                                    elif inst.status == 'overdue':
                                        st.error("Überfällig!")

                                st.markdown("---")

                            # Progress visualization
                            paid_count = sum(1 for i in installments if i.status == 'paid')
                            total_count = len(installments)

                            if total_count > 0:
                                st.progress(paid_count / total_count)
                                st.caption(f"{paid_count} von {total_count} Raten bezahlt")

                                # Estimated completion
                                remaining = total_count - paid_count
                                if remaining > 0 and plan.interval_days:
                                    est_end = date.today() + timedelta(days=remaining * plan.interval_days)
                                    st.info(f"📅 Voraussichtliches Ende: {format_date(est_end)}")

                        st.markdown("---")
                        st.markdown("---")

        # Tab 2: Request new payment plan
        with tab2:
            st.markdown("### Ratenzahlung anfragen")

            if not cases_without_plans:
                st.success("Für alle Ihre offenen Forderungen existiert bereits eine Ratenzahlungsvereinbarung.")
            else:
                st.info(
                    "Hier können Sie eine Ratenzahlung für Ihre offenen Forderungen anfragen. "
                    "Der Rechtsanwalt wird Ihren Vorschlag prüfen und Ihnen eine Vereinbarung zusenden."
                )

                with st.form("payment_plan_request"):
                    # Select case
                    case_options = {}
                    for c in cases_without_plans:
                        balance = ledger.get_case_balance(c.id)
                        total_open = balance.get('total_open', 0)
                        case_options[str(c.id)] = f"{c.internal_number} - {c.creditor_name} ({format_currency(total_open)})"

                    selected_case_id = st.selectbox(
                        "Forderung auswählen",
                        options=list(case_options.keys()),
                        format_func=lambda x: case_options[x]
                    )

                    if selected_case_id:
                        selected_case = next(c for c in cases_without_plans if str(c.id) == selected_case_id)
                        balance = ledger.get_case_balance(selected_case.id)
                        total_open = balance.get('total_open', 0)

                        st.info(f"Offener Betrag: **{format_currency(total_open)}**")

                    st.divider()

                    col1, col2 = st.columns(2)

                    with col1:
                        monthly_rate = st.number_input(
                            "Gewünschte monatliche Rate (€)",
                            min_value=10.0,
                            step=10.0,
                            format="%.2f",
                            help="Wie viel können Sie monatlich zahlen?"
                        )

                    with col2:
                        first_payment = st.date_input(
                            "Erste Rate ab",
                            value=date.today() + timedelta(days=14),
                            min_value=date.today() + timedelta(days=7),
                            help="Wann können Sie die erste Rate zahlen?"
                        )

                    # Calculate estimated number of installments
                    if selected_case_id and monthly_rate > 0:
                        num_installments = int(total_open / monthly_rate) + 1
                        est_end = first_payment + timedelta(days=30 * num_installments)

                        st.markdown("#### Voraussichtlicher Plan")
                        st.markdown(f"- Anzahl Raten: **{num_installments}**")
                        st.markdown(f"- Letzte Rate ca.: **{format_date(est_end)}**")
                        st.markdown(f"- Monatliche Belastung: **{format_currency(monthly_rate)}**")

                    notes = st.text_area(
                        "Begründung / Anmerkungen",
                        placeholder="Bitte erläutern Sie kurz Ihre finanzielle Situation...",
                        help="Warum können Sie nicht den vollen Betrag zahlen?"
                    )

                    st.divider()

                    st.warning(
                        "⚠️ **Wichtig:** Mit dem Absenden dieser Anfrage erkennen Sie die Forderung grundsätzlich an. "
                        "Der Rechtsanwalt wird Ihren Vorschlag prüfen. Sie erhalten eine verbindliche Vereinbarung, "
                        "sobald der Gläubiger zugestimmt hat."
                    )

                    submitted = st.form_submit_button("Ratenzahlung anfragen", use_container_width=True)

                    if submitted:
                        if not selected_case_id or monthly_rate <= 0:
                            st.error("Bitte füllen Sie alle Felder aus.")
                        else:
                            # Create payment plan request
                            plan = PaymentPlan(
                                case_id=UUID(selected_case_id),
                                status='angefragt',
                                total_amount=Decimal(str(total_open)),
                                installment_amount=Decimal(str(monthly_rate)),
                                number_of_installments=num_installments,
                                first_installment_date=first_payment,
                                interval_days=30,
                                requested_at=datetime.utcnow(),
                                requested_by=user_id,
                                request_notes=notes,
                                created_by=user_id
                            )

                            db.add(plan)
                            db.commit()

                            st.success("✅ Ihre Anfrage wurde erfolgreich eingereicht!")
                            st.info("Der Rechtsanwalt wird Ihren Vorschlag prüfen und sich bei Ihnen melden.")
                            st.rerun()


# Import datetime at module level
from datetime import datetime

if __name__ == "__main__":
    main()
