"""
Formatting utilities for display
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Union


def format_currency(
    amount: Union[float, Decimal, int, None],
    symbol: str = "€",
    decimal_places: int = 2
) -> str:
    """Format a number as currency."""
    if amount is None:
        return f"0,00 {symbol}"

    # Convert to float if needed
    if isinstance(amount, Decimal):
        amount = float(amount)

    # Format with German number format
    formatted = f"{amount:,.{decimal_places}f}"
    # Convert to German format (. for thousands, , for decimal)
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")

    return f"{formatted} {symbol}"


def format_date(
    d: Union[datetime, date, str, None],
    format_str: str = "%d.%m.%Y"
) -> str:
    """Format a date for display."""
    if d is None:
        return "-"

    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d)
        except ValueError:
            return d

    if isinstance(d, datetime):
        return d.strftime(format_str)

    if isinstance(d, date):
        return d.strftime(format_str)

    return str(d)


def format_datetime(
    dt: Union[datetime, str, None],
    format_str: str = "%d.%m.%Y %H:%M"
) -> str:
    """Format a datetime for display."""
    if dt is None:
        return "-"

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt

    if isinstance(dt, datetime):
        return dt.strftime(format_str)

    return str(dt)


def format_status_badge(status: str, status_type: str = "case") -> str:
    """
    Return HTML for a status badge.
    Uses Streamlit's markdown with HTML support.
    """
    status_colors = {
        # Case status
        "offen": ("#FFA500", "Offen"),
        "mahnverfahren": ("#2196F3", "Mahnverfahren"),
        "vollstreckung": ("#9C27B0", "Vollstreckung"),
        "ratenzahlung": ("#4CAF50", "Ratenzahlung"),
        "abgeschlossen": ("#8BC34A", "Abgeschlossen"),
        "uneinbringlich": ("#F44336", "Uneinbringlich"),

        # Dunning status
        "nicht_beantragt": ("#9E9E9E", "Nicht beantragt"),
        "mb_beantragt": ("#2196F3", "MB beantragt"),
        "mb_zugestellt": ("#4CAF50", "MB zugestellt"),
        "widerspruch": ("#FF9800", "Widerspruch"),
        "vb_beantragt": ("#2196F3", "VB beantragt"),
        "vb_erlassen": ("#4CAF50", "VB erlassen"),
        "titel_rechtskraeftig": ("#8BC34A", "Titel rechtskräftig"),

        # Payment status
        "gemeldet": ("#FFC107", "Gemeldet"),
        "akzeptiert": ("#2196F3", "Akzeptiert"),
        "abgelehnt": ("#F44336", "Abgelehnt"),
        "verbucht": ("#4CAF50", "Verbucht"),

        # Payment plan status
        "angefragt": ("#FFC107", "Angefragt"),
        "entwurf": ("#9E9E9E", "Entwurf"),
        "geprueft": ("#2196F3", "Geprüft"),
        "freigegeben": ("#4CAF50", "Freigegeben"),
        "aktiv": ("#4CAF50", "Aktiv"),
        "verzoegert": ("#FF9800", "Verzögert"),
        "gekuendigt": ("#F44336", "Gekündigt"),

        # Enforcement status
        "nicht_begonnen": ("#9E9E9E", "Nicht begonnen"),
        "gv_auftrag": ("#2196F3", "GV beauftragt"),
        "vv_erhalten": ("#4CAF50", "VV erhalten"),
        "pfueb_beantragt": ("#2196F3", "PfüB beantragt"),
        "pfueb_erlassen": ("#4CAF50", "PfüB erlassen"),
        "pfueb_zugestellt": ("#8BC34A", "PfüB zugestellt"),
        "teilzahlung": ("#FFC107", "Teilzahlung"),
        "vollstaendig": ("#4CAF50", "Vollständig"),

        # Approval status
        "ausstehend": ("#FFC107", "Ausstehend"),
        "genehmigt": ("#4CAF50", "Genehmigt"),

        # Measure status
        "vorgeschlagen": ("#9E9E9E", "Vorgeschlagen"),
        "ausgewaehlt": ("#2196F3", "Ausgewählt"),
        "freigabe_ausstehend": ("#FFC107", "Freigabe ausstehend"),
        "ausgefuehrt": ("#4CAF50", "Ausgeführt"),
        "ruecklaefer": ("#8BC34A", "Rückläufer"),

        # General
        "pending": ("#FFC107", "Ausstehend"),
        "paid": ("#4CAF50", "Bezahlt"),
        "overdue": ("#F44336", "Überfällig"),
        "cancelled": ("#9E9E9E", "Storniert"),
    }

    color, display_name = status_colors.get(
        status.lower(),
        ("#9E9E9E", status.replace("_", " ").title())
    )

    return f":{color[1:]}[{display_name}]"


def get_status_icon(status: str) -> str:
    """Get an emoji icon for a status."""
    icons = {
        # Payment plan indicators
        "aktiv": "🟢",
        "verzoegert": "🟠",
        "gekuendigt": "🔴",
        "pending": "⏳",
        "paid": "✅",
        "overdue": "❗",

        # General
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "info": "ℹ️",

        # Dunning
        "mb_zugestellt": "📬",
        "vb_erlassen": "📜",
        "widerspruch": "⚠️",

        # Enforcement
        "gv_auftrag": "👮",
        "pfueb_erlassen": "🏛️",
    }

    return icons.get(status.lower(), "•")


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """Format a percentage value."""
    return f"{value:.{decimal_places}f}%"


def format_days(days: int) -> str:
    """Format number of days in German."""
    if days == 0:
        return "heute"
    elif days == 1:
        return "1 Tag"
    elif days == -1:
        return "gestern"
    elif days > 0:
        return f"{days} Tagen"
    else:
        return f"vor {abs(days)} Tagen"


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate text to a maximum length."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
