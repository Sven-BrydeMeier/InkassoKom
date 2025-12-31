"""
Reusable Streamlit components
"""
import streamlit as st
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal

from .formatting import (
    format_currency, format_date, format_datetime,
    format_status_badge, get_status_icon, truncate_text
)


def show_case_card(
    case: Dict[str, Any],
    show_balance: bool = True,
    on_click: Optional[callable] = None
):
    """Display a case summary card."""
    with st.container():
        col1, col2, col3 = st.columns([3, 2, 2])

        with col1:
            st.markdown(f"### {case.get('internal_number', 'N/A')}")
            st.markdown(f"**{case.get('creditor_name', 'Gläubiger')}** ./. **{case.get('debtor_name', 'Schuldner')}**")
            if case.get('subject'):
                st.caption(truncate_text(case['subject'], 100))

        with col2:
            status = case.get('status', 'offen')
            st.markdown(format_status_badge(status))

            dunning = case.get('dunning_status')
            if dunning and dunning != 'nicht_beantragt':
                st.markdown(format_status_badge(dunning))

        with col3:
            if show_balance:
                balance = case.get('balance', {})
                total_open = balance.get('total_open', 0)
                st.metric(
                    "Offener Betrag",
                    format_currency(total_open),
                    delta=None
                )

        if on_click:
            if st.button("Akte öffnen", key=f"open_{case.get('id')}"):
                on_click(case.get('id'))

        st.divider()


def show_timeline(
    events: List[Dict[str, Any]],
    show_date: bool = True,
    max_items: Optional[int] = None
):
    """Display a timeline of events."""
    if max_items:
        events = events[:max_items]

    for event in events:
        severity = event.get('severity', 'info')
        icon = get_status_icon(severity)

        timestamp = event.get('timestamp') or event.get('event_date')
        date_str = format_datetime(timestamp) if timestamp else ""

        with st.container():
            col1, col2 = st.columns([1, 10])

            with col1:
                st.markdown(f"### {icon}")

            with col2:
                title = event.get('title', 'Event')
                st.markdown(f"**{title}**")

                if event.get('description'):
                    st.caption(event['description'])

                meta_parts = []
                if show_date and date_str:
                    meta_parts.append(date_str)
                if event.get('actor_name'):
                    meta_parts.append(f"von {event['actor_name']}")
                if event.get('case_number'):
                    meta_parts.append(f"Akte {event['case_number']}")

                if meta_parts:
                    st.caption(" | ".join(meta_parts))

        st.markdown("---")


def show_ledger_table(
    bookings: List[Dict[str, Any]],
    show_status: bool = False
):
    """Display a ledger/booking table."""
    if not bookings:
        st.info("Keine Buchungen vorhanden.")
        return

    # Prepare data for table
    table_data = []
    for b in bookings:
        row = {
            "Datum": format_date(b.get('booking_date')),
            "S/H": b.get('debit_credit', '-'),
            "Betrag": format_currency(b.get('amount', 0)),
            "Kategorie": b.get('category', '-').replace('_', ' ').title(),
            "Beschreibung": truncate_text(b.get('description', ''), 50),
        }
        if show_status:
            row["Status"] = b.get('status', '-')

        table_data.append(row)

    st.table(table_data)


def show_balance_card(balance: Dict[str, Any]):
    """Display a balance summary card."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Hauptforderung",
            format_currency(balance.get('total_principal', 0))
        )

    with col2:
        st.metric(
            "Zinsen",
            format_currency(balance.get('total_interest', 0))
        )

    with col3:
        st.metric(
            "Kosten",
            format_currency(balance.get('total_costs', 0) + balance.get('total_lawyer_fees', 0))
        )

    with col4:
        total = balance.get('total_open', 0)
        is_paid = balance.get('is_paid', False)
        st.metric(
            "Gesamtforderung",
            format_currency(total),
            delta="Bezahlt" if is_paid else None,
            delta_color="normal" if is_paid else "off"
        )


def show_payment_progress(
    total_amount: float,
    paid_amount: float,
    installments: Optional[List[Dict]] = None
):
    """Display payment progress visualization."""
    if total_amount <= 0:
        st.info("Keine Forderung vorhanden.")
        return

    # Calculate percentages
    paid_percent = min((paid_amount / total_amount) * 100, 100)
    remaining_percent = 100 - paid_percent

    # Create progress bar
    st.progress(paid_percent / 100)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Bezahlt", format_currency(paid_amount))
    with col2:
        st.metric("Offen", format_currency(total_amount - paid_amount))
    with col3:
        st.metric("Fortschritt", f"{paid_percent:.1f}%")

    # Show installments if provided
    if installments:
        st.subheader("Ratenplan")
        for inst in installments:
            status = inst.get('status', 'pending')
            icon = get_status_icon(status)
            due_date = format_date(inst.get('due_date'))
            amount = format_currency(inst.get('amount', 0))

            col1, col2, col3 = st.columns([1, 2, 2])
            with col1:
                st.markdown(f"{icon} Rate {inst.get('installment_number', '?')}")
            with col2:
                st.text(f"Fällig: {due_date}")
            with col3:
                st.text(amount)


def show_document_card(
    document: Dict[str, Any],
    on_download: Optional[callable] = None,
    on_view: Optional[callable] = None
):
    """Display a document card."""
    col1, col2, col3 = st.columns([4, 2, 2])

    with col1:
        icon = "📄"
        file_type = document.get('file_type', '').lower()
        if file_type == 'pdf':
            icon = "📕"
        elif file_type in ['doc', 'docx']:
            icon = "📘"
        elif file_type in ['xls', 'xlsx']:
            icon = "📗"
        elif file_type in ['jpg', 'jpeg', 'png']:
            icon = "🖼️"

        st.markdown(f"{icon} **{document.get('title') or document.get('original_filename', 'Dokument')}**")
        st.caption(f"{document.get('document_type', 'Sonstiges')} | {format_date(document.get('created_at'))}")

    with col2:
        if on_view:
            if st.button("Ansehen", key=f"view_{document.get('id')}"):
                on_view(document.get('id'))

    with col3:
        if on_download:
            if st.button("Download", key=f"dl_{document.get('id')}"):
                on_download(document.get('id'))


def show_notification_badge(count: int):
    """Display a notification count badge."""
    if count > 0:
        return f"🔔 ({count})"
    return "🔕"


def show_warning_banner(message: str, icon: str = "⚠️"):
    """Display a warning banner."""
    st.warning(f"{icon} {message}")


def show_success_banner(message: str, icon: str = "✅"):
    """Display a success banner."""
    st.success(f"{icon} {message}")


def show_info_banner(message: str, icon: str = "ℹ️"):
    """Display an info banner."""
    st.info(f"{icon} {message}")


def show_limitation_warning(days_remaining: int, case_number: str):
    """Display a limitation warning."""
    if days_remaining <= 30:
        st.error(f"⚠️ **DRINGEND:** Akte {case_number} - Verjährung in {days_remaining} Tagen!")
    elif days_remaining <= 90:
        st.warning(f"⏰ Akte {case_number} - Verjährung in {days_remaining} Tagen")
    elif days_remaining <= 180:
        st.info(f"📅 Akte {case_number} - Verjährung in {days_remaining} Tagen")


def create_sidebar_nav(role: str):
    """Create sidebar navigation based on role."""
    with st.sidebar:
        st.markdown("## Navigation")

        if role in ['admin', 'rechtsanwalt']:
            st.page_link("pages/1_Dashboard.py", label="📊 Dashboard", icon="📊")
            st.page_link("pages/2_Akten.py", label="📁 Aktenregister", icon="📁")
            st.page_link("pages/3_Posteingang.py", label="📬 Posteingang", icon="📬")
            st.page_link("pages/4_Mahnverfahren.py", label="⚖️ Mahnverfahren", icon="⚖️")
            st.page_link("pages/5_Vollstreckung.py", label="🏛️ Vollstreckung", icon="🏛️")
            st.page_link("pages/6_Einstellungen.py", label="⚙️ Einstellungen", icon="⚙️")

        elif role == 'glaeubigerin':
            st.page_link("pages/creditor/1_Aktuelles.py", label="📊 Aktuelles", icon="📊")
            st.page_link("pages/creditor/2_Forderungen.py", label="💰 Forderungen", icon="💰")
            st.page_link("pages/creditor/3_Zahlungen.py", label="💳 Zahlungseingänge", icon="💳")

        elif role == 'schuldner':
            st.page_link("pages/debtor/1_Uebersicht.py", label="📊 Übersicht", icon="📊")
            st.page_link("pages/debtor/2_Dokumente.py", label="📄 Dokumente", icon="📄")
            st.page_link("pages/debtor/3_Ratenzahlung.py", label="📅 Ratenzahlung", icon="📅")

        st.divider()
        st.page_link("pages/0_Profil.py", label="👤 Profil", icon="👤")


def show_empty_state(
    message: str,
    icon: str = "📭",
    action_label: Optional[str] = None,
    on_action: Optional[callable] = None
):
    """Display an empty state message."""
    st.markdown(f"### {icon}")
    st.markdown(f"**{message}**")

    if action_label and on_action:
        if st.button(action_label):
            on_action()


def show_loading():
    """Display a loading spinner."""
    with st.spinner("Laden..."):
        pass
