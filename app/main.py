"""
InkassoKom - Inkasso-Kommunikationsplattform
Vollständige Implementierung aller Funktionen
"""

# App-Versionsnummer (Datum-Zeit Format)
APP_VERSION = "v2026.01.09-1230"

import streamlit as st
from datetime import datetime, date, timedelta
import sys
import os
import base64
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Database Integration (optional - falls Supabase konfiguriert)
try:
    from src.database.streamlit_db import (
        is_database_configured,
        get_db_status,
        show_db_status_widget,
        db_get_all_cases,
        db_get_case,
        db_get_documents,
        db_get_bookings
    )
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# PDF Splitter Integration (intelligente Dokumententrennung)
try:
    from src.pdf_splitter import (
        PDFSplitter,
        split_pdf_intelligent,
        get_splitter_capabilities
    )
    PDF_SPLITTER_AVAILABLE = True
except ImportError:
    PDF_SPLITTER_AVAILABLE = False

# Email Parser Integration (Email-Import)
try:
    from src.email_parser import (
        EmailParser,
        ParsedEmail,
        parse_email_file,
        get_parser_capabilities
    )
    EMAIL_PARSER_AVAILABLE = True
except ImportError:
    EMAIL_PARSER_AVAILABLE = False

# Wiedervorlage Service (intelligente Fristenerkennung)
try:
    from src.services.wiedervorlage_service import (
        WiedervorlageService,
        WVGrund,
        WVBedingung,
        erkenne_fristen_im_text,
        erstelle_wv_vorschlaege,
        get_wv_service
    )
    WV_SERVICE_AVAILABLE = True
except ImportError:
    WV_SERVICE_AVAILABLE = False

st.set_page_config(
    page_title="InkassoKom - Inkasso-Plattform",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stButton > button { min-height: 44px; }
    @media (max-width: 768px) {
        .main .block-container { padding: 1rem 0.5rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# Session State
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = 'dashboard'
if 'selected_case' not in st.session_state:
    st.session_state.selected_case = None
if 'imported_cases' not in st.session_state:
    st.session_state.imported_cases = []
if 'imported_documents' not in st.session_state:
    st.session_state.imported_documents = {}
if 'imported_bookings' not in st.session_state:
    st.session_state.imported_bookings = {}
if 'pdf_viewer_content' not in st.session_state:
    st.session_state.pdf_viewer_content = None
if 'document_pdfs' not in st.session_state:
    st.session_state.document_pdfs = {}  # {doc_id: pdf_bytes} für einzelne Dokument-PDFs
if 'case_full_pdfs' not in st.session_state:
    st.session_state.case_full_pdfs = {}  # {case_id: pdf_bytes} für Gesamt-PDFs
# Emails
if 'imported_emails' not in st.session_state:
    st.session_state.imported_emails = {}  # {case_id: [ParsedEmail, ...]}
if 'email_attachments' not in st.session_state:
    st.session_state.email_attachments = {}  # {email_id: [attachment_bytes, ...]}
if 'unassigned_emails' not in st.session_state:
    st.session_state.unassigned_emails = []  # Emails ohne Akten-Zuordnung
# Wiedervorlagen
if 'wiedervorlagen' not in st.session_state:
    st.session_state.wiedervorlagen = {}  # {case_id: [WV, ...]}
if 'pending_wv_vorschlaege' not in st.session_state:
    st.session_state.pending_wv_vorschlaege = None  # Temporär nach Nachrichtenversand
if 'wv_notifications' not in st.session_state:
    st.session_state.wv_notifications = []  # Fällige WVs
if 'active_wv_check' not in st.session_state:
    st.session_state.active_wv_check = None  # Aktive WV-Prüfung
if 'wv_neu_terminieren' not in st.session_state:
    st.session_state.wv_neu_terminieren = False  # WV neu terminieren Dialog
if 'compose_prefill' not in st.session_state:
    st.session_state.compose_prefill = None  # Vorbefüllte Nachricht aus WV
# AI & Kommunikation
if 'openai_api_key' not in st.session_state:
    # Zuerst in Streamlit Secrets nachschauen
    api_key_from_secrets = ""
    try:
        if hasattr(st, 'secrets') and 'OPENAI_API_KEY' in st.secrets:
            api_key_from_secrets = st.secrets['OPENAI_API_KEY']
        elif hasattr(st, 'secrets') and 'openai_api_key' in st.secrets:
            api_key_from_secrets = st.secrets['openai_api_key']
        elif hasattr(st, 'secrets') and 'openai' in st.secrets and 'api_key' in st.secrets['openai']:
            api_key_from_secrets = st.secrets['openai']['api_key']
    except Exception:
        pass
    st.session_state.openai_api_key = api_key_from_secrets
    st.session_state.openai_api_key_from_secrets = bool(api_key_from_secrets)
if 'messages' not in st.session_state:
    st.session_state.messages = []  # Globale Nachrichtenliste
if 'notifications' not in st.session_state:
    st.session_state.notifications = []
if 'browser_notifications' not in st.session_state:
    st.session_state.browser_notifications = False
if 'case_events' not in st.session_state:
    st.session_state.case_events = []  # Ereignisprotokoll
# Vorlagen-System
if 'templates' not in st.session_state:
    st.session_state.templates = {
        'briefkopf_docx': None,  # Word-Dokument als Bytes
        'briefkopf_filename': None,  # Dateiname des hochgeladenen Word-Dokuments
        'briefkopf': """Kanzlei Müller & Partner
Rechtsanwälte
Musterstraße 123
10115 Berlin

Tel: +49 30 123456
Fax: +49 30 123457
E-Mail: info@kanzlei-mueller.de
www.kanzlei-mueller.de

Steuernummer: 12/345/67890
USt-IdNr.: DE123456789""",
        'email_signatur': """Mit freundlichen Grüßen

Thomas Müller
Rechtsanwalt

Kanzlei Müller & Partner
Musterstraße 123, 10115 Berlin
Tel: +49 30 123456
E-Mail: ra.mueller@kanzlei-mueller.de

Diese E-Mail kann vertrauliche Informationen enthalten.""",
        'zahlungsaufforderung': """[BRIEFKOPF]

[DATUM]

An
[SCHULDNER_NAME]
[SCHULDNER_ADRESSE]

Unser Zeichen: [AKTENZEICHEN]

Betreff: Zahlungsaufforderung - [BETREFF]

Sehr geehrte/r [ANREDE],

namens und in Vollmacht unserer Mandantschaft, [GLÄUBIGER], fordern wir Sie hiermit auf, den offenen Betrag in Höhe von

[FORDERUNG_GESAMT]

(Hauptforderung: [HAUPTFORDERUNG], zzgl. Zinsen und Kosten)

bis spätestens zum [FRIST] auf das nachfolgende Konto zu überweisen:

[BANKVERBINDUNG]

Sollte die Zahlung nicht fristgerecht erfolgen, werden wir ohne weitere Ankündigung gerichtliche Schritte einleiten.

[SIGNATUR]""",
        'klage_vorlage': """[GERICHT]

Klage

des/der [KLÄGER]
- Kläger/in -

Prozessbevollmächtigte: [KANZLEI]

gegen

[BEKLAGTER]
- Beklagte/r -

wegen: Forderung

Streitwert: [STREITWERT]

[ANTRAG]

[BEGRÜNDUNG]

[BEWEISMITTEL]

[SIGNATUR]""",
        'schriftsatz_vorlage': """An das
[GERICHT]

In Sachen
[KLÄGER] ./. [BEKLAGTER]
Az.: [AKTENZEICHEN]

wird namens und in Vollmacht des Klägers/der Klägerin wie folgt vorgetragen:

[INHALT]

[SIGNATUR]"""
    }
if 'kanzlei_daten' not in st.session_state:
    st.session_state.kanzlei_daten = {
        'name': 'Kanzlei Müller & Partner',
        'adresse': 'Musterstraße 123\n10115 Berlin',
        'telefon': '+49 30 123456',
        'fax': '+49 30 123457',
        'email': 'info@kanzlei-mueller.de',
        'bank': 'Sparkasse Berlin',
        'iban': 'DE89 3704 0044 0532 0130 00',
        'bic': 'COBADEFFXXX'
    }

# =============================================================================
# DEMO-DATEN
# =============================================================================
DEMO_CASES = [
    {
        'id': 'case-001', 'nr': '1/25', 'creditor': 'Mustermann GmbH', 'debtor': 'Max Schmidt',
        'creditor_address': 'Industriestraße 45\n10245 Berlin',
        'debtor_address': 'Hauptstraße 12\n10115 Berlin',
        'subject': 'Offene Rechnung 2024-001', 'status': 'offen', 'dunning': 'nicht_beantragt',
        'enforcement': 'nicht_begonnen', 'principal': 5000.00, 'interest': 5.0,
        'due_date': date.today() - timedelta(days=60), 'created': datetime.now() - timedelta(days=65),
        'contract_type': 'Kaufvertrag', 'contract_date': date.today() - timedelta(days=90),
        'invoice_nr': '2024-001', 'invoice_date': date.today() - timedelta(days=60),
        'leistung': 'Lieferung von Waren gemäß Bestellung vom 01.10.2024',
        'mahnung_dates': [date.today() - timedelta(days=45), date.today() - timedelta(days=30)],
    },
    {
        'id': 'case-002', 'nr': '2/25', 'creditor': 'Mustermann GmbH', 'debtor': 'Hans Meier',
        'creditor_address': 'Industriestraße 45\n10245 Berlin',
        'debtor_address': 'Nebenstraße 34\n10178 Berlin',
        'subject': 'Kaufpreisforderung', 'status': 'mahnverfahren', 'dunning': 'mb_zugestellt',
        'enforcement': 'nicht_begonnen', 'principal': 2500.00, 'interest': 5.0,
        'due_date': date.today() - timedelta(days=90), 'created': datetime.now() - timedelta(days=95),
        'mb_date': date.today() - timedelta(days=30), 'mb_delivered': date.today() - timedelta(days=14),
        'mb_az': '25-1234567-0-8', 'mb_gericht': 'AG Berlin-Wedding',
        'contract_type': 'Kaufvertrag', 'contract_date': date.today() - timedelta(days=120),
        'invoice_nr': '2024-002', 'invoice_date': date.today() - timedelta(days=90),
        'leistung': 'Lieferung von Elektronikartikeln',
        'widerspruch': False, 'einspruch': False, 'abgabe_streitgericht': False,
    },
    {
        'id': 'case-003', 'nr': '3/25', 'creditor': 'Mustermann GmbH', 'debtor': 'Anna Weber',
        'creditor_address': 'Industriestraße 45\n10245 Berlin',
        'debtor_address': 'Parkweg 56\n10999 Berlin',
        'subject': 'Mietrückstand', 'status': 'vollstreckung', 'dunning': 'titel_rechtskraeftig',
        'enforcement': 'pfueb_beantragt', 'principal': 3600.00, 'interest': 5.0,
        'due_date': date.today() - timedelta(days=180), 'created': datetime.now() - timedelta(days=185),
        'vb_date': date.today() - timedelta(days=60),
        'mb_az': '25-9876543-0-2', 'mb_gericht': 'AG Berlin-Wedding',
        'vb_az': '25-9876543-0-2', 'contract_type': 'Mietvertrag',
        'contract_date': date.today() - timedelta(days=365),
        'leistung': 'Überlassung der Mieträume gemäß Mietvertrag',
        'widerspruch': True, 'einspruch': False, 'abgabe_streitgericht': True,
        'streitgericht': 'AG Berlin-Mitte', 'streit_az': '12 C 456/24',
    },
]

DEMO_BOOKINGS = {
    'case-001': [
        {'date': date.today() - timedelta(60), 'type': 'S', 'amount': 5000.00, 'cat': 'Hauptforderung', 'desc': 'Rechnung 2024-001'},
        {'date': date.today() - timedelta(55), 'type': 'S', 'amount': 261.80, 'cat': 'RA-Gebühren', 'desc': '1,3 Geschäftsgebühr'},
        {'date': date.today() - timedelta(30), 'type': 'H', 'amount': 1000.00, 'cat': 'Zahlung', 'desc': 'Teilzahlung'},
        {'date': date.today(), 'type': 'S', 'amount': 125.00, 'cat': 'Zinsen', 'desc': 'Verzugszinsen'},
    ],
    'case-002': [
        {'date': date.today() - timedelta(90), 'type': 'S', 'amount': 2500.00, 'cat': 'Hauptforderung', 'desc': 'Kaufpreis'},
        {'date': date.today() - timedelta(30), 'type': 'S', 'amount': 32.00, 'cat': 'Gerichtskosten', 'desc': 'MB-Kosten'},
    ],
    'case-003': [
        {'date': date.today() - timedelta(180), 'type': 'S', 'amount': 3600.00, 'cat': 'Hauptforderung', 'desc': 'Mietrückstand'},
        {'date': date.today() - timedelta(150), 'type': 'S', 'amount': 311.40, 'cat': 'RA-Gebühren', 'desc': 'RA-Gebühren'},
        {'date': date.today() - timedelta(60), 'type': 'S', 'amount': 32.00, 'cat': 'Gerichtskosten', 'desc': 'VB-Kosten'},
        {'date': date.today() - timedelta(30), 'type': 'H', 'amount': 500.00, 'cat': 'Zahlung', 'desc': 'Teilzahlung'},
    ],
}

def fmt_curr(amt): return f"{amt:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
def fmt_date(d): return d.strftime("%d.%m.%Y") if d else "-"

# =============================================================================
# WORD DOCUMENT HELPER FUNCTIONS
# =============================================================================

def get_case_placeholders(case):
    """Erstellt ein Dictionary mit allen Platzhaltern für eine Akte"""
    if not case:
        return {}

    s, h, o = get_balance(case['id'])

    # Aktenkurzbezeichnung erstellen
    creditor_kurz = case.get('creditor', '').split()[0] if case.get('creditor') else 'Mandant'
    debtor_kurz = case.get('debtor', '').split()[-1] if case.get('debtor') else 'Gegner'
    kurzbezeichnung = f"{creditor_kurz} ./. {debtor_kurz}"

    # Anrede ermitteln
    vorname = case.get('debtor', '').split()[0] if case.get('debtor') else ''
    weibliche_vornamen = ['Anna', 'Maria', 'Lisa', 'Julia', 'Laura', 'Sophie', 'Emma', 'Lena', 'Sarah', 'Claudia', 'Petra', 'Sabine', 'Monika', 'Susanne', 'Martina']
    anrede = 'Frau' if vorname in weibliche_vornamen else 'Herr'
    anrede_brief = 'Sehr geehrte Frau' if vorname in weibliche_vornamen else 'Sehr geehrter Herr'

    return {
        # Akte
        '[AKTENZEICHEN]': case.get('nr', ''),
        '[KURZBEZEICHNUNG]': kurzbezeichnung,
        '[BETREFF]': case.get('subject', ''),
        '[STATUS]': case.get('status', '').title(),

        # Gläubiger/Mandant
        '[MANDANT]': case.get('creditor', ''),
        '[GLÄUBIGER]': case.get('creditor', ''),
        '[MANDANT_ADRESSE]': case.get('creditor_address', ''),
        '[GLÄUBIGER_ADRESSE]': case.get('creditor_address', ''),

        # Schuldner/Gegner
        '[GEGNER]': case.get('debtor', ''),
        '[SCHULDNER]': case.get('debtor', ''),
        '[SCHULDNER_NAME]': case.get('debtor', ''),
        '[GEGNER_ADRESSE]': case.get('debtor_address', ''),
        '[SCHULDNER_ADRESSE]': case.get('debtor_address', ''),
        '[ANREDE]': anrede,
        '[ANREDE_BRIEF]': anrede_brief,
        '[NACHNAME_SCHULDNER]': debtor_kurz,

        # Beträge
        '[HAUPTFORDERUNG]': fmt_curr(case.get('principal', 0)),
        '[FORDERUNG_GESAMT]': fmt_curr(o),
        '[OFFEN]': fmt_curr(o),
        '[GEZAHLT]': fmt_curr(h),
        '[SOLL]': fmt_curr(s),
        '[ZINSSATZ]': f"{case.get('interest', 5.0)}%",

        # Datum/Fristen
        '[DATUM]': fmt_date(date.today()),
        '[HEUTE]': fmt_date(date.today()),
        '[FRIST_7]': fmt_date(date.today() + timedelta(days=7)),
        '[FRIST_14]': fmt_date(date.today() + timedelta(days=14)),
        '[FRIST]': fmt_date(date.today() + timedelta(days=14)),
        '[FÄLLIGKEIT]': fmt_date(case.get('due_date', date.today())),

        # Kanzleidaten
        '[BRIEFKOPF]': st.session_state.templates.get('briefkopf', ''),
        '[SIGNATUR]': st.session_state.templates.get('email_signatur', ''),
        '[KANZLEI]': st.session_state.kanzlei_daten.get('name', ''),
        '[BANKVERBINDUNG]': f"{st.session_state.kanzlei_daten.get('bank', '')}\nIBAN: {st.session_state.kanzlei_daten.get('iban', '')}",
        '[IBAN]': st.session_state.kanzlei_daten.get('iban', ''),
        '[BIC]': st.session_state.kanzlei_daten.get('bic', ''),

        # Mahnverfahren (falls vorhanden)
        '[MB_AZ]': case.get('mb_az', ''),
        '[MB_GERICHT]': case.get('mb_gericht', ''),
        '[VB_AZ]': case.get('vb_az', ''),
    }


def replace_placeholders_in_docx(docx_bytes, placeholders):
    """Ersetzt Platzhalter in einem Word-Dokument"""
    try:
        from docx import Document

        # Dokument aus Bytes laden
        doc = Document(io.BytesIO(docx_bytes))

        def replace_in_paragraph(paragraph, placeholders):
            """Ersetzt Platzhalter in einem Paragraphen - auch wenn über Runs verteilt"""
            # Gesamten Text des Paragraphen holen
            full_text = paragraph.text

            # Prüfen ob überhaupt ein Platzhalter vorhanden ist
            has_placeholder = any(ph in full_text for ph in placeholders.keys())
            if not has_placeholder:
                return

            # Alle Platzhalter ersetzen
            new_text = full_text
            for placeholder, value in placeholders.items():
                if placeholder in new_text:
                    new_text = new_text.replace(placeholder, str(value) if value else '')

            # Wenn Text geändert wurde, Paragraph neu aufbauen
            if new_text != full_text:
                # Formatting des ersten Runs merken (falls vorhanden)
                if paragraph.runs:
                    first_run = paragraph.runs[0]
                    # Alle Runs löschen
                    for run in paragraph.runs:
                        run.text = ''
                    # Neuen Text in ersten Run setzen
                    first_run.text = new_text
                else:
                    # Kein Run vorhanden, neuen erstellen
                    paragraph.add_run(new_text)

        # Durch alle Paragraphen iterieren
        for paragraph in doc.paragraphs:
            replace_in_paragraph(paragraph, placeholders)

        # Durch alle Tabellen iterieren
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_in_paragraph(paragraph, placeholders)

        # Header und Footer
        for section in doc.sections:
            # Header
            for paragraph in section.header.paragraphs:
                replace_in_paragraph(paragraph, placeholders)
            # Footer
            for paragraph in section.footer.paragraphs:
                replace_in_paragraph(paragraph, placeholders)

        # Als Bytes zurückgeben
        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        return output.getvalue()

    except ImportError:
        st.error("❌ python-docx ist nicht installiert. Bitte installieren Sie es mit: pip install python-docx")
        return None
    except Exception as e:
        st.error(f"❌ Fehler beim Verarbeiten des Word-Dokuments: {str(e)}")
        return None


def generate_document_from_template(case, template_key='briefkopf_docx'):
    """Generiert ein Word-Dokument aus der Vorlage mit Platzhalter-Ersetzung"""
    template_bytes = st.session_state.templates.get(template_key)
    if not template_bytes:
        st.error("❌ Keine Word-Vorlage gefunden!")
        return None

    placeholders = get_case_placeholders(case)

    # Debug: Zeige welche Platzhalter verwendet werden
    with st.expander("🔍 Debug: Verwendete Platzhalter"):
        for key, value in placeholders.items():
            if value:  # Nur nicht-leere Werte anzeigen
                st.text(f"{key} → {value}")

    return replace_placeholders_in_docx(template_bytes, placeholders)

def get_all_cases():
    """Gibt alle Akten zurück (Datenbank oder Demo + importierte)"""
    # Versuche zuerst Datenbank
    if DB_AVAILABLE and is_database_configured():
        try:
            db_cases = db_get_all_cases()
            if db_cases:
                return db_cases
        except Exception:
            pass  # Fallback zu Demo-Daten

    # Fallback: Demo + importierte Akten
    all_cases = DEMO_CASES.copy()
    for imp_case in st.session_state.get('imported_cases', []):
        if not any(c['id'] == imp_case['id'] for c in all_cases):
            all_cases.append(imp_case)
    return all_cases

def get_all_documents(case_id):
    """Gibt alle Dokumente einer Akte zurück (Datenbank oder Demo + importierte)"""
    # Versuche zuerst Datenbank
    if DB_AVAILABLE and is_database_configured():
        try:
            db_docs = db_get_documents(case_id)
            if db_docs:
                return db_docs
        except Exception:
            pass

    # Fallback: Demo + importierte Dokumente
    docs = DEMO_DOCUMENTS.get(case_id, []).copy()
    imp_docs = st.session_state.get('imported_documents', {}).get(case_id, [])
    for imp_doc in imp_docs:
        if not any(d['id'] == imp_doc['id'] for d in docs):
            if 'category' not in imp_doc:
                imp_doc['category'] = get_document_category(imp_doc.get('type', ''))
            docs.append(imp_doc)
    return docs

def get_all_bookings(case_id):
    """Gibt alle Buchungen einer Akte zurück (Datenbank oder Demo + importierte)"""
    # Versuche zuerst Datenbank
    if DB_AVAILABLE and is_database_configured():
        try:
            db_bookings = db_get_bookings(case_id)
            if db_bookings:
                return db_bookings
        except Exception:
            pass

    # Fallback: Demo + importierte Buchungen
    bookings = DEMO_BOOKINGS.get(case_id, []).copy()
    imp_bookings = st.session_state.get('imported_bookings', {}).get(case_id, [])
    for imp_b in imp_bookings:
        if imp_b not in bookings:
            bookings.append(imp_b)
    return bookings

# RVG Gebührentabelle (vereinfacht, Stand 2024)
RVG_TABELLE = [
    (500, 49.00),
    (1000, 88.00),
    (1500, 127.00),
    (2000, 166.00),
    (3000, 222.00),
    (4000, 278.00),
    (5000, 334.00),
    (6000, 390.00),
    (7000, 446.00),
    (8000, 502.00),
    (9000, 558.00),
    (10000, 614.00),
    (13000, 666.00),
    (16000, 718.00),
    (19000, 770.00),
    (22000, 822.00),
    (25000, 874.00),
    (30000, 955.00),
    (35000, 1036.00),
    (40000, 1117.00),
    (45000, 1198.00),
    (50000, 1279.00),
    (65000, 1373.00),
    (80000, 1467.00),
    (95000, 1561.00),
    (110000, 1655.00),
    (125000, 1749.00),
    (140000, 1843.00),
    (155000, 1937.00),
    (170000, 2031.00),
    (185000, 2125.00),
    (200000, 2219.00),
]

def calculate_rvg_gebuehr(streitwert: float) -> float:
    """Berechnet die RVG-Gebühr basierend auf dem Streitwert"""
    for grenze, gebuehr in RVG_TABELLE:
        if streitwert <= grenze:
            return gebuehr
    # Für höhere Streitwerte: letzte Gebühr + Zuschlag
    return RVG_TABELLE[-1][1] + ((streitwert - RVG_TABELLE[-1][0]) / 5000) * 94

def calculate_ra_kosten(streitwert: float, gebuehrensatz: float = 1.3) -> dict:
    """
    Berechnet RA-Kosten nach RVG
    gebuehrensatz: z.B. 1.3 für Geschäftsgebühr, 1.5 für erhöhte Gebühr
    """
    grund_gebuehr = calculate_rvg_gebuehr(streitwert)
    geschaefts_gebuehr = round(grund_gebuehr * gebuehrensatz, 2)
    auslagenpauschale = round(min(geschaefts_gebuehr * 0.20, 20.00), 2)  # Max 20€
    ust = round((geschaefts_gebuehr + auslagenpauschale) * 0.19, 2)
    gesamt = round(geschaefts_gebuehr + auslagenpauschale + ust, 2)

    return {
        'streitwert': streitwert,
        'grund_gebuehr': grund_gebuehr,
        'gebuehrensatz': gebuehrensatz,
        'geschaefts_gebuehr': geschaefts_gebuehr,
        'auslagenpauschale': auslagenpauschale,
        'ust': ust,
        'gesamt': gesamt
    }

def get_balance(case_id):
    b = get_all_bookings(case_id)
    s = sum(x['amount'] for x in b if x['type'] == 'S')
    h = sum(x['amount'] for x in b if x['type'] == 'H')
    return s, h, s - h

def parse_date_flexible(date_value):
    """Konvertiert verschiedene Datumsformate in ein date-Objekt."""
    if date_value is None:
        return None
    if isinstance(date_value, date) and not isinstance(date_value, datetime):
        return date_value
    if isinstance(date_value, datetime):
        return date_value.date()
    if isinstance(date_value, str):
        # Versuche verschiedene Formate
        for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y/%m/%d']:
            try:
                return datetime.strptime(date_value, fmt).date()
            except ValueError:
                continue
    return None


def calculate_interest_for_case(case, bookings):
    """
    Berechnet die aktuellen Verzugszinsen für eine Akte.
    Zinsen werden auf die offene Hauptforderung ab Fälligkeitsdatum berechnet.

    Args:
        case: Die Akten-Daten mit 'due_date', 'interest', 'principal'
        bookings: Liste der Buchungen

    Returns:
        float: Berechnete Zinsen bis heute
    """
    if not case:
        return 0.0

    # Zinssatz aus der Akte (Standard: 5% über Basiszins)
    zinssatz = case.get('interest', 5.0)
    if zinssatz is None or zinssatz == 0:
        zinssatz = 5.0  # Gesetzlicher Verzugszins für Verbraucher

    # Fälligkeitsdatum ermitteln
    faellig = parse_date_flexible(case.get('due_date'))

    if not faellig:
        # Falls kein Fälligkeitsdatum, aus Buchungen ermitteln
        soll_buchungen = [b for b in bookings if b.get('type') == 'S']
        if soll_buchungen:
            buchungsdaten = []
            for b in soll_buchungen:
                d = parse_date_flexible(b.get('date'))
                if d:
                    buchungsdaten.append(d)
            if buchungsdaten:
                faellig = min(buchungsdaten)

    if not faellig:
        # Fallback: 60 Tage zurück
        faellig = date.today() - timedelta(days=60)

    # Tage seit Fälligkeit
    heute = date.today()
    if faellig >= heute:
        return 0.0  # Noch nicht fällig

    verzugstage = (heute - faellig).days

    # Hauptforderung ermitteln
    hauptforderung = case.get('principal', 0)
    if hauptforderung is None:
        hauptforderung = 0

    if hauptforderung == 0:
        # Versuche aus Buchungen zu ermitteln
        for b in bookings:
            if b.get('type') == 'S' and b.get('cat') in ['Hauptforderung', 'Rechnung', 'Kaufpreis', 'Mietrückstand']:
                hauptforderung += b.get('amount', 0)

    # Zahlungen abziehen
    zahlungen = sum(b.get('amount', 0) for b in bookings if b.get('type') == 'H')
    offene_forderung = max(0, hauptforderung - zahlungen)

    # Zinsberechnung: Hauptforderung * (Zinssatz/100) * (Tage/365)
    zinsen = offene_forderung * (zinssatz / 100) * (verzugstage / 365)

    return round(zinsen, 2)


def get_interest_details(case, bookings):
    """Gibt detaillierte Zinsinformationen zurück für die Anzeige."""
    zinssatz = case.get('interest', 5.0) or 5.0
    faellig = parse_date_flexible(case.get('due_date'))

    if not faellig:
        soll_buchungen = [b for b in bookings if b.get('type') == 'S']
        if soll_buchungen:
            buchungsdaten = [parse_date_flexible(b.get('date')) for b in soll_buchungen]
            buchungsdaten = [d for d in buchungsdaten if d]
            if buchungsdaten:
                faellig = min(buchungsdaten)

    if not faellig:
        faellig = date.today() - timedelta(days=60)

    heute = date.today()
    verzugstage = max(0, (heute - faellig).days)

    hauptforderung = case.get('principal', 0) or 0
    zahlungen = sum(b.get('amount', 0) for b in bookings if b.get('type') == 'H')
    offene_forderung = max(0, hauptforderung - zahlungen)

    zinsen = calculate_interest_for_case(case, bookings)

    return {
        'zinssatz': zinssatz,
        'faellig_seit': faellig,
        'verzugstage': verzugstage,
        'offene_forderung': offene_forderung,
        'zinsen': zinsen,
        'berechnung': f"{fmt_curr(offene_forderung)} × {zinssatz}% × {verzugstage}/365 = {fmt_curr(zinsen)}"
    }

def logout():
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.page = 'dashboard'

# =============================================================================
# DEMO-NACHRICHTEN & EREIGNISSE
# =============================================================================
DEMO_MESSAGES = [
    {
        'id': 'msg-001',
        'from_role': 'glaeubigerin',
        'from_name': 'Erika Mustermann',
        'to_role': 'rechtsanwalt',
        'to_name': 'Thomas Müller',
        'case_id': 'case-001',
        'subject': 'Anfrage zum Sachstand',
        'content': 'Sehr geehrter Herr Müller,\n\nkönnen Sie mir bitte den aktuellen Sachstand zur Akte 1/25 mitteilen?\n\nMit freundlichen Grüßen\nErika Mustermann',
        'date': datetime.now() - timedelta(hours=2),
        'read': False,
        'type': 'inquiry'
    },
    {
        'id': 'msg-002',
        'from_role': 'schuldner',
        'from_name': 'Max Schmidt',
        'to_role': 'rechtsanwalt',
        'to_name': 'Thomas Müller',
        'case_id': 'case-001',
        'subject': 'Bitte um Ratenzahlung',
        'content': 'Sehr geehrte Damen und Herren,\n\nich kann die Forderung leider nicht auf einmal begleichen. Wäre eine Ratenzahlung möglich?\n\nMit freundlichen Grüßen\nMax Schmidt',
        'date': datetime.now() - timedelta(days=1),
        'read': True,
        'type': 'request'
    },
]

DEMO_EVENTS = [
    {'case_id': 'case-001', 'date': datetime.now() - timedelta(days=30), 'type': 'zahlung', 'desc': 'Teilzahlung 1.000€ eingegangen', 'notified': True},
    {'case_id': 'case-002', 'date': datetime.now() - timedelta(days=14), 'type': 'mahnbescheid', 'desc': 'Mahnbescheid zugestellt', 'notified': True},
    {'case_id': 'case-003', 'date': datetime.now() - timedelta(days=7), 'type': 'pfueb', 'desc': 'PfÜB beantragt', 'notified': False},
]

# =============================================================================
# KI-KOMMUNIKATIONSASSISTENT
# =============================================================================
def generate_ai_response(case, inquiry_type='sachstand'):
    """
    Generiert eine KI-gestützte Antwort basierend auf Akten- und Anfrage-Daten.
    Wenn OpenAI API Key vorhanden, nutze echte KI, sonst Template.
    """
    s, h, o = get_balance(case['id'])

    # Status-Beschreibungen
    status_texts = {
        'offen': 'Die Forderung ist offen und befindet sich in der außergerichtlichen Beitreibung.',
        'mahnverfahren': 'Es wurde ein gerichtliches Mahnverfahren eingeleitet.',
        'vollstreckung': 'Die Forderung befindet sich in der Zwangsvollstreckung.',
        'abgeschlossen': 'Das Verfahren wurde abgeschlossen.'
    }

    dunning_texts = {
        'nicht_beantragt': 'Ein Mahnbescheid wurde noch nicht beantragt.',
        'mb_beantragt': 'Der Mahnbescheid wurde beantragt und ist in Bearbeitung.',
        'mb_zugestellt': 'Der Mahnbescheid wurde dem Schuldner zugestellt. Die Widerspruchsfrist läuft.',
        'vb_beantragt': 'Der Vollstreckungsbescheid wurde beantragt.',
        'vb_erlassen': 'Der Vollstreckungsbescheid wurde erlassen.',
        'titel_rechtskraeftig': 'Der Titel ist rechtskräftig. Vollstreckungsmaßnahmen können eingeleitet werden.'
    }

    next_steps = {
        'offen': 'Als nächsten Schritt empfehlen wir die Beantragung eines Mahnbescheids.',
        'mahnverfahren': 'Wir warten die Widerspruchsfrist ab bzw. beantragen den Vollstreckungsbescheid.',
        'vollstreckung': 'Die Zwangsvollstreckung wird fortgesetzt.',
        'abgeschlossen': 'Keine weiteren Schritte erforderlich.'
    }

    # Prüfen ob OpenAI API verfügbar
    if st.session_state.openai_api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=st.session_state.openai_api_key)

            prompt = f"""Du bist ein Rechtsanwalt für Inkasso. Erstelle eine professionelle Antwort auf eine Sachstandsanfrage.

Aktenzeichen: {case['nr']}
Schuldner: {case['debtor']}
Gläubiger: {case['creditor']}
Hauptforderung: {case['principal']:.2f} €
Offener Betrag: {o:.2f} €
Bezahlt: {h:.2f} €
Status: {case['status']}
Mahnverfahren: {case['dunning']}
Fällig seit: {case['due_date'].strftime('%d.%m.%Y')}

Erstelle ein formelles Schreiben mit aktuellem Sachstand und nächsten Schritten."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            pass  # Fallback auf Template

    # Template-basierte Antwort (ohne API)
    today = date.today().strftime('%d.%m.%Y')
    template = f"""Sehr geehrte Damen und Herren,

bezugnehmend auf Ihre Anfrage zum Sachstand teilen wir Ihnen Folgendes mit:

**Aktenzeichen:** {case['nr']}
**Schuldner:** {case['debtor']}
**Gläubiger:** {case['creditor']}

**Aktueller Sachstand:**
{status_texts.get(case['status'], 'Status unbekannt')}
{dunning_texts.get(case['dunning'], '')}

**Forderungsübersicht:**
- Hauptforderung: {fmt_curr(case['principal'])}
- Gesamtforderung (inkl. Zinsen/Kosten): {fmt_curr(s)}
- Bereits gezahlt: {fmt_curr(h)}
- **Offener Betrag: {fmt_curr(o)}**

**Nächste Schritte:**
{next_steps.get(case['status'], '')}

Für Rückfragen stehen wir Ihnen gerne zur Verfügung.

Mit freundlichen Grüßen
Ihre Kanzlei

---
Stand: {today}"""

    return template

def send_message(from_role, from_name, to_role, to_name, case_id, subject, content, doc_ids=None):
    """Sendet eine Nachricht und erstellt Benachrichtigungen"""
    msg = {
        'id': f'msg-{len(st.session_state.messages) + 100:03d}',
        'from_role': from_role,
        'from_name': from_name,
        'to_role': to_role,
        'to_name': to_name,
        'case_id': case_id,
        'subject': subject,
        'content': content,
        'date': datetime.now(),
        'read': False,
        'type': 'message',
        'attachments': doc_ids or []
    }
    st.session_state.messages.append(msg)

    # Benachrichtigung erstellen
    notification = {
        'id': f'notif-{len(st.session_state.notifications) + 1:03d}',
        'user_role': to_role,
        'type': 'message',
        'title': f'Neue Nachricht: {subject}',
        'content': f'Von {from_name} zu Akte {case_id}',
        'date': datetime.now(),
        'read': False,
        'link': 'inbox'
    }
    st.session_state.notifications.append(notification)
    return msg

def add_case_event(case_id, event_type, description):
    """Fügt ein Ereignis hinzu und benachrichtigt Gläubiger"""
    event = {
        'case_id': case_id,
        'date': datetime.now(),
        'type': event_type,
        'desc': description,
        'notified': False
    }
    st.session_state.case_events.append(event)

    # Benachrichtigung für Gläubiger
    all_cases = get_all_cases()
    case = next((c for c in all_cases if c['id'] == case_id), None)
    if case:
        notification = {
            'id': f'notif-{len(st.session_state.notifications) + 1:03d}',
            'user_role': 'glaeubigerin',
            'type': 'event',
            'title': f'Aktenfortschritt: {case["nr"]}',
            'content': description,
            'date': datetime.now(),
            'read': False,
            'link': 'claims'
        }
        st.session_state.notifications.append(notification)

def get_unread_count(role):
    """Zählt ungelesene Nachrichten für eine Rolle"""
    return sum(1 for m in st.session_state.messages + DEMO_MESSAGES if m['to_role'] == role and not m['read'])

def get_notification_count(role):
    """Zählt ungelesene Benachrichtigungen für eine Rolle"""
    return sum(1 for n in st.session_state.notifications if n['user_role'] == role and not n['read'])

# =============================================================================
# DEMO-DOKUMENTE MIT KATEGORIEN
# =============================================================================
DOCUMENT_CATEGORIES = {
    'aussergerichtlich': {
        'name': 'Außergerichtlich',
        'icon': '📬',
        'types': ['Rechnung', 'Mahnung', 'Zahlungsaufforderung', 'Forderungsaufstellung', 'Vertrag', 'Lieferschein']
    },
    'gerichtlich': {
        'name': 'Gerichtlich',
        'icon': '⚖️',
        'types': ['Mahnbescheid', 'Vollstreckungsbescheid', 'VB', 'PfüB', 'Klage', 'Urteil', 'Beschluss', 'Zustellung', 'EDA']
    },
    'emailverkehr': {
        'name': 'Emailverkehr',
        'icon': '📧',
        'types': ['Email', 'E-Mail', 'Email-Eingang', 'Email-Ausgang', 'Korrespondenz']
    },
    'intern': {
        'name': 'Interne Kommunikation',
        'icon': '🏢',
        'types': ['Notiz', 'Vermerk', 'Aktennotiz', 'Berechnung', 'Intern']
    },
    'mandant': {
        'name': 'Kommunikation mit Mandant',
        'icon': '💼',
        'types': ['Mandantenbrief', 'Sachstandsbericht', 'Abrechnung', 'Vollmacht', 'Mandant']
    },
    'schuldner': {
        'name': 'Kommunikation mit Schuldner',
        'icon': '👤',
        'types': ['Schuldnerbrief', 'Ratenzahlungsvereinbarung', 'Vergleich', 'Schuldner']
    }
}

def get_document_category(doc_type):
    """Ermittelt die Kategorie eines Dokuments anhand des Typs"""
    doc_type_lower = doc_type.lower()
    for cat_id, cat_info in DOCUMENT_CATEGORIES.items():
        for t in cat_info['types']:
            if t.lower() in doc_type_lower or doc_type_lower in t.lower():
                return cat_id
    return 'aussergerichtlich'  # Default

DEMO_DOCUMENTS = {
    'case-001': [
        {'id': 'doc-001', 'name': 'Forderungsaufstellung.pdf', 'date': date.today(), 'type': 'Forderungsaufstellung', 'size': '245 KB', 'category': 'aussergerichtlich'},
        {'id': 'doc-002', 'name': 'Rechnung_2024-001.pdf', 'date': date.today() - timedelta(60), 'type': 'Rechnung', 'size': '128 KB', 'category': 'aussergerichtlich'},
        {'id': 'doc-003', 'name': 'Mahnung_1.pdf', 'date': date.today() - timedelta(45), 'type': 'Mahnung', 'size': '98 KB', 'category': 'aussergerichtlich'},
        {'id': 'doc-004', 'name': 'Sachstandsbericht_Mandant.pdf', 'date': date.today() - timedelta(30), 'type': 'Sachstandsbericht', 'size': '156 KB', 'category': 'mandant'},
        {'id': 'doc-005', 'name': 'Aktennotiz.pdf', 'date': date.today() - timedelta(20), 'type': 'Aktennotiz', 'size': '45 KB', 'category': 'intern'},
    ],
    'case-002': [
        {'id': 'doc-006', 'name': 'Kaufvertrag.pdf', 'date': date.today() - timedelta(120), 'type': 'Vertrag', 'size': '512 KB', 'category': 'aussergerichtlich'},
        {'id': 'doc-007', 'name': 'Mahnbescheid.pdf', 'date': date.today() - timedelta(30), 'type': 'Mahnbescheid', 'size': '156 KB', 'category': 'gerichtlich'},
        {'id': 'doc-008', 'name': 'Zustellnachweis_MB.pdf', 'date': date.today() - timedelta(14), 'type': 'Zustellung', 'size': '89 KB', 'category': 'gerichtlich'},
        {'id': 'doc-009', 'name': 'Brief_an_Schuldner.pdf', 'date': date.today() - timedelta(10), 'type': 'Schuldnerbrief', 'size': '78 KB', 'category': 'schuldner'},
    ],
    'case-003': [
        {'id': 'doc-010', 'name': 'Mietvertrag.pdf', 'date': date.today() - timedelta(365), 'type': 'Vertrag', 'size': '890 KB', 'category': 'aussergerichtlich'},
        {'id': 'doc-011', 'name': 'Vollstreckungsbescheid.pdf', 'date': date.today() - timedelta(60), 'type': 'VB', 'size': '178 KB', 'category': 'gerichtlich'},
        {'id': 'doc-012', 'name': 'PfueB_Antrag.pdf', 'date': date.today() - timedelta(7), 'type': 'PfüB', 'size': '234 KB', 'category': 'gerichtlich'},
        {'id': 'doc-013', 'name': 'Vollmacht.pdf', 'date': date.today() - timedelta(180), 'type': 'Vollmacht', 'size': '120 KB', 'category': 'mandant'},
        {'id': 'doc-014', 'name': 'Ratenzahlungsangebot.pdf', 'date': date.today() - timedelta(45), 'type': 'Ratenzahlungsvereinbarung', 'size': '95 KB', 'category': 'schuldner'},
    ],
}

def generate_demo_pdf(doc_name, case_nr):
    """Generiert ein echtes Demo-PDF mit PyPDF2"""
    try:
        from PyPDF2 import PdfWriter
        from PyPDF2.generic import NameObject, ArrayObject, NumberObject, TextStringObject, DictionaryObject

        # Erstelle ein minimales gültiges PDF
        writer = PdfWriter()

        # Füge eine leere Seite hinzu (A4 Format)
        page = writer.add_blank_page(width=595, height=842)

        # PDF in Bytes konvertieren
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)

        return output.getvalue()
    except Exception as e:
        # Fallback: Minimales gültiges PDF manuell erstellen
        content = f"""Dokument: {doc_name}
Akte: {case_nr}
Datum: {fmt_date(date.today())}

Dies ist ein Demo-Dokument der InkassoKom-Plattform.
"""
        # Minimales PDF mit Text
        pdf_content = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 200 >>
stream
BT
/F1 16 Tf
50 750 Td
(InkassoKom - Demo-Dokument) Tj
0 -30 Td
/F1 12 Tf
(Dokument: {doc_name.replace('(', '').replace(')', '')}) Tj
0 -20 Td
(Akte: {case_nr}) Tj
0 -20 Td
(Datum: {fmt_date(date.today())}) Tj
0 -40 Td
(Dies ist ein Demo-Dokument.) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000518 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
595
%%EOF"""
        return pdf_content.encode('latin-1')

def show_document_viewer(doc, case_nr, key_prefix):
    """Zeigt Dokumentenoptionen: Ansehen, Herunterladen, Teilen"""
    with st.expander(f"📄 {doc['name']} ({doc['size']}) - {fmt_date(doc['date'])}"):
        c1, c2, c3 = st.columns(3)

        # Prüfen ob echtes PDF in Session vorhanden
        has_real_pdf = st.session_state.pdf_viewer_content is not None

        # Demo-Inhalt oder echtes PDF
        if has_real_pdf:
            pdf_content = st.session_state.pdf_viewer_content
        else:
            pdf_content = generate_demo_pdf(doc['name'], case_nr)

        with c1:
            if st.button("👁️ Ansehen", key=f"{key_prefix}_view_{doc['id']}", use_container_width=True):
                st.session_state[f"viewing_{doc['id']}"] = True

        with c2:
            st.download_button(
                "⬇️ Download",
                data=pdf_content,
                file_name=doc['name'],
                mime="application/pdf" if doc['name'].endswith('.pdf') else "application/octet-stream",
                key=f"{key_prefix}_dl_{doc['id']}",
                use_container_width=True
            )

        with c3:
            share_url = f"https://inkassokom.de/dok/{doc['id']}"
            if st.button("🔗 Teilen", key=f"{key_prefix}_share_{doc['id']}", use_container_width=True):
                st.code(share_url, language=None)
                st.info("Link in Zwischenablage kopiert!")

        # PDF-Vorschau anzeigen
        if st.session_state.get(f"viewing_{doc['id']}", False):
            st.divider()
            st.markdown("### 📖 Dokumentvorschau")

            if has_real_pdf and doc['name'].endswith('.pdf'):
                # Echter PDF-Viewer mit iframe
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
                pdf_display = f'''
                <iframe
                    src="data:application/pdf;base64,{pdf_base64}"
                    width="100%"
                    height="500px"
                    type="application/pdf"
                    style="border: 1px solid #ccc; border-radius: 5px;">
                </iframe>
                '''
                st.markdown(pdf_display, unsafe_allow_html=True)
            else:
                # Text-Vorschau für Demo-PDFs
                st.text_area(
                    "Inhalt",
                    value=pdf_content.decode('utf-8') if isinstance(pdf_content, bytes) else str(pdf_content),
                    height=300,
                    disabled=True,
                    key=f"{key_prefix}_preview_{doc['id']}"
                )

            if st.button("❌ Schließen", key=f"{key_prefix}_close_{doc['id']}"):
                st.session_state[f"viewing_{doc['id']}"] = False
                st.rerun()

        # Dokumentinfo
        st.caption(f"📁 Typ: {doc['type']} | 📅 Erstellt: {fmt_date(doc['date'])}")

def show_document_explorer(case_id, case_nr):
    """
    Dokumenten-Explorer mit Baumstruktur nach Kategorien:
    - Außergerichtlich
    - Gerichtlich
    - Interne Kommunikation
    - Kommunikation mit Mandant
    - Kommunikation mit Schuldner
    """
    st.markdown("### 📁 Dokumenten-Explorer")

    # Gesamt-PDF anzeigen Button (für importierte Akten)
    if case_id in st.session_state.case_full_pdfs:
        with st.expander("📖 **Gesamt-PDF der Akte anzeigen**", expanded=False):
            full_pdf = st.session_state.case_full_pdfs[case_id]
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"📄 Original-PDF der importierten Akte ({len(full_pdf) // 1024} KB)")
            with col2:
                st.download_button(
                    "⬇️ Download",
                    data=full_pdf,
                    file_name=f"Akte_{case_nr.replace('/', '_')}_Gesamt.pdf",
                    mime="application/pdf",
                    key=f"full_pdf_dl_{case_id}"
                )

            # PDF-Viewer
            pdf_base64 = base64.b64encode(full_pdf).decode('utf-8')
            st.markdown(f'''
            <iframe src="data:application/pdf;base64,{pdf_base64}" width="100%" height="600px"
                style="border: 1px solid #ccc; border-radius: 5px;"></iframe>
            ''', unsafe_allow_html=True)

        st.divider()

    # Alle Dokumente der Akte abrufen
    all_docs = get_all_documents(case_id)

    if not all_docs:
        st.info("Keine Dokumente in dieser Akte vorhanden")
    else:
        # Statistik - dynamisch basierend auf Kategorien
        num_cats = len(DOCUMENT_CATEGORIES)
        stat_cols = st.columns(num_cats)
        for i, (cat_id, cat_info) in enumerate(DOCUMENT_CATEGORIES.items()):
            cat_count = len([d for d in all_docs if d.get('category', 'aussergerichtlich') == cat_id])
            with stat_cols[i]:
                st.metric(cat_info['icon'], cat_count, help=cat_info['name'])

        st.divider()

        # Filter und Ansicht
        col1, col2 = st.columns([2, 1])
        with col1:
            view_mode = st.radio(
                "Ansicht",
                ["🌳 Baumansicht", "📋 Listenansicht", "📅 Chronologisch"],
                horizontal=True,
                key=f"doc_view_{case_id}"
            )
        with col2:
            search_doc = st.text_input("🔍 Dokument suchen", placeholder="Name oder Typ...", key=f"doc_search_{case_id}")

        # Dokumente filtern
        if search_doc:
            all_docs = [d for d in all_docs if search_doc.lower() in d['name'].lower() or search_doc.lower() in d['type'].lower()]

        st.divider()

        if view_mode == "🌳 Baumansicht":
            # Dokumente nach Kategorien gruppieren
            for cat_id, cat_info in DOCUMENT_CATEGORIES.items():
                cat_docs = [d for d in all_docs if d.get('category', 'aussergerichtlich') == cat_id]

                if cat_docs:
                    with st.expander(f"{cat_info['icon']} **{cat_info['name']}** ({len(cat_docs)} Dokumente)", expanded=(cat_id == 'aussergerichtlich')):
                        for doc in sorted(cat_docs, key=lambda x: x['date'], reverse=True):
                            show_document_item(doc, case_nr, f"exp_{case_id}_{cat_id}")

        elif view_mode == "📋 Listenansicht":
            # Alle Dokumente als Liste
            for doc in sorted(all_docs, key=lambda x: x['name']):
                cat_id = doc.get('category', 'aussergerichtlich')
                cat_info = DOCUMENT_CATEGORIES.get(cat_id, DOCUMENT_CATEGORIES['aussergerichtlich'])
                show_document_item(doc, case_nr, f"list_{case_id}", show_category=True)

        else:  # Chronologisch
            for doc in sorted(all_docs, key=lambda x: x['date'], reverse=True):
                show_document_item(doc, case_nr, f"chron_{case_id}", show_category=True)

    st.divider()

    # Dokument oder Email hinzufügen
    st.markdown("### ➕ Dokument oder Email hinzufügen")

    upload_tab1, upload_tab2, upload_tab3 = st.tabs(["📄 Dokument", "📧 Email", "📦 ZIP-Archiv"])

    with upload_tab1:
        col1, col2 = st.columns(2)

        with col1:
            uploaded = st.file_uploader("Datei hochladen", type=['pdf', 'docx', 'jpg', 'png'], key=f"upload_{case_id}")

        with col2:
            if uploaded:
                doc_type = st.selectbox(
                    "Dokumenttyp",
                    ["Rechnung", "Mahnung", "Vertrag", "Mahnbescheid", "Vollstreckungsbescheid",
                     "Schreiben", "Notiz", "Sachstandsbericht", "Brief an Schuldner", "Sonstiges"],
                    key=f"doc_type_{case_id}"
                )
                doc_category = st.selectbox(
                    "Kategorie",
                    [(k, v['name']) for k, v in DOCUMENT_CATEGORIES.items()],
                    format_func=lambda x: x[1],
                    key=f"doc_cat_{case_id}"
                )[0]

        if uploaded:
            if st.button("📤 Dokument hinzufügen", type="primary", use_container_width=True, key=f"add_doc_{case_id}"):
                # Neues Dokument erstellen
                new_doc = {
                    'id': f'doc-{case_id}-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                    'name': uploaded.name,
                    'date': date.today(),
                    'type': doc_type,
                    'size': f'{len(uploaded.getvalue()) // 1024} KB',
                    'category': doc_category
                }

                # Zu DEMO_DOCUMENTS hinzufügen
                if case_id not in DEMO_DOCUMENTS:
                    DEMO_DOCUMENTS[case_id] = []
                DEMO_DOCUMENTS[case_id].append(new_doc)

                st.success(f"✅ '{uploaded.name}' zur Akte hinzugefügt!")
                st.rerun()

    with upload_tab2:
        # Email Upload
        if EMAIL_PARSER_AVAILABLE:
            email_files = st.file_uploader(
                "Email-Dateien hochladen (.eml, .msg)",
                type=['eml', 'msg'],
                accept_multiple_files=True,
                key=f"email_upload_{case_id}",
                help="Drag & Drop oder Klicken zum Auswählen"
            )

            if email_files:
                st.markdown("#### Erkannte Emails:")
                for email_file in email_files:
                    try:
                        parsed = parse_email_file(email_file.getvalue(), email_file.name)
                        with st.expander(f"📧 {parsed.get_short_subject(40)}", expanded=True):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Von:** {parsed.sender_name} <{parsed.sender_email}>")
                                st.write(f"**An:** {', '.join(parsed.to[:2])}{'...' if len(parsed.to) > 2 else ''}")
                                st.write(f"**Datum:** {parsed.get_display_date()}")
                            with col2:
                                st.write(f"**Anhänge:** {len(parsed.attachments)}")
                                if parsed.case_references:
                                    st.write(f"**Aktenzeichen:** {', '.join(parsed.case_references[:3])}")
                            st.caption(parsed.get_body_preview(150))
                    except Exception as e:
                        st.error(f"Fehler bei {email_file.name}: {str(e)}")

                if st.button("📧 Emails zur Akte hinzufügen", type="primary", use_container_width=True, key=f"add_emails_{case_id}"):
                    added_count = 0
                    for email_file in email_files:
                        try:
                            parsed = parse_email_file(email_file.getvalue(), email_file.name)
                            email_id = f'email-{case_id}-{datetime.now().strftime("%Y%m%d%H%M%S%f")}'

                            # Als Dokument speichern
                            new_doc = {
                                'id': email_id,
                                'name': f"{parsed.get_short_subject(30)}.eml",
                                'date': parsed.date.date() if parsed.date else date.today(),
                                'type': 'Email',
                                'size': f'{len(email_file.getvalue()) // 1024} KB',
                                'category': 'emailverkehr',
                                'email_data': {
                                    'subject': parsed.subject,
                                    'sender': parsed.sender,
                                    'sender_email': parsed.sender_email,
                                    'to': parsed.to,
                                    'cc': parsed.cc,
                                    'body_preview': parsed.get_body_preview(500),
                                    'attachments': len(parsed.attachments),
                                    'message_id': parsed.message_id
                                }
                            }

                            if case_id not in DEMO_DOCUMENTS:
                                DEMO_DOCUMENTS[case_id] = []
                            DEMO_DOCUMENTS[case_id].append(new_doc)

                            # Email-Daten separat speichern
                            if case_id not in st.session_state.imported_emails:
                                st.session_state.imported_emails[case_id] = []
                            st.session_state.imported_emails[case_id].append({
                                'id': email_id,
                                'parsed': parsed,
                                'raw': email_file.getvalue()
                            })

                            added_count += 1
                        except Exception as e:
                            st.error(f"Fehler bei {email_file.name}: {str(e)}")

                    if added_count > 0:
                        st.success(f"✅ {added_count} Email(s) zur Akte hinzugefügt!")
                        st.rerun()
        else:
            st.warning("📧 Email-Parser nicht verfügbar. Bitte src/email_parser installieren.")

    with upload_tab3:
        # ZIP-Archiv Upload
        st.info("📦 Laden Sie ein ZIP-Archiv hoch, um mehrere Dokumente auf einmal zu importieren.")

        zip_file = st.file_uploader(
            "ZIP-Datei hochladen",
            type=['zip'],
            key=f"zip_upload_{case_id}",
            help="ZIP-Archive mit PDFs, Bildern und Dokumenten"
        )

        if zip_file:
            import zipfile
            import io

            try:
                # ZIP entpacken und Inhalt anzeigen
                zip_buffer = io.BytesIO(zip_file.getvalue())
                with zipfile.ZipFile(zip_buffer, 'r') as zf:
                    # Dateien filtern (nur unterstützte Formate)
                    supported_extensions = {'.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.gif', '.tif', '.tiff', '.eml', '.msg'}
                    all_files = []

                    for file_info in zf.infolist():
                        if not file_info.is_dir():
                            file_ext = os.path.splitext(file_info.filename.lower())[1]
                            if file_ext in supported_extensions:
                                all_files.append({
                                    'name': file_info.filename,
                                    'size': file_info.file_size,
                                    'ext': file_ext,
                                    'compress_size': file_info.compress_size
                                })

                    if all_files:
                        st.success(f"📦 **{len(all_files)} Dateien** im Archiv gefunden")

                        # Session State für Auswahl
                        if f'zip_selection_{case_id}' not in st.session_state:
                            st.session_state[f'zip_selection_{case_id}'] = {f['name']: True for f in all_files}

                        # Alle auswählen / Keine auswählen
                        sel_col1, sel_col2 = st.columns(2)
                        with sel_col1:
                            if st.button("✅ Alle auswählen", key=f"zip_sel_all_{case_id}"):
                                st.session_state[f'zip_selection_{case_id}'] = {f['name']: True for f in all_files}
                                st.rerun()
                        with sel_col2:
                            if st.button("❌ Keine auswählen", key=f"zip_sel_none_{case_id}"):
                                st.session_state[f'zip_selection_{case_id}'] = {f['name']: False for f in all_files}
                                st.rerun()

                        st.divider()

                        # Dateien nach Typ gruppieren
                        files_by_type = {}
                        for f in all_files:
                            ext = f['ext'].upper().replace('.', '')
                            if ext not in files_by_type:
                                files_by_type[ext] = []
                            files_by_type[ext].append(f)

                        # Dateien mit Checkboxen anzeigen
                        for file_type, files in sorted(files_by_type.items()):
                            type_icons = {
                                'PDF': '📕', 'DOCX': '📘', 'DOC': '📘',
                                'JPG': '🖼️', 'JPEG': '🖼️', 'PNG': '🖼️', 'GIF': '🖼️', 'TIF': '🖼️', 'TIFF': '🖼️',
                                'EML': '📧', 'MSG': '📧'
                            }
                            icon = type_icons.get(file_type, '📄')

                            with st.expander(f"{icon} **{file_type}** ({len(files)} Dateien)", expanded=True):
                                for f in files:
                                    # Nur Dateiname ohne Pfad anzeigen
                                    display_name = os.path.basename(f['name'])
                                    size_kb = f['size'] / 1024

                                    col1, col2 = st.columns([4, 1])
                                    with col1:
                                        checked = st.checkbox(
                                            f"{display_name}",
                                            value=st.session_state[f'zip_selection_{case_id}'].get(f['name'], True),
                                            key=f"zip_file_{case_id}_{f['name']}"
                                        )
                                        st.session_state[f'zip_selection_{case_id}'][f['name']] = checked
                                    with col2:
                                        st.caption(f"{size_kb:.1f} KB")

                        # Zähle ausgewählte Dateien
                        selected_count = sum(1 for v in st.session_state[f'zip_selection_{case_id}'].values() if v)

                        st.divider()

                        # Dokumenttyp für alle
                        zip_doc_type = st.selectbox(
                            "Dokumenttyp für alle Dateien",
                            ["Automatisch erkennen", "Rechnung", "Mahnung", "Vertrag", "Mahnbescheid",
                             "Vollstreckungsbescheid", "Schreiben", "Notiz", "Sonstiges"],
                            key=f"zip_doc_type_{case_id}"
                        )

                        zip_doc_category = st.selectbox(
                            "Kategorie für alle Dateien",
                            [(k, v['name']) for k, v in DOCUMENT_CATEGORIES.items()],
                            format_func=lambda x: x[1],
                            key=f"zip_doc_cat_{case_id}"
                        )[0]

                        # Import-Button
                        if st.button(
                            f"📥 {selected_count} Dateien importieren",
                            type="primary",
                            use_container_width=True,
                            disabled=selected_count == 0,
                            key=f"zip_import_{case_id}"
                        ):
                            imported_count = 0
                            errors = []

                            # ZIP erneut öffnen für den Import
                            zip_buffer.seek(0)
                            with zipfile.ZipFile(zip_buffer, 'r') as zf:
                                for f in all_files:
                                    if st.session_state[f'zip_selection_{case_id}'].get(f['name'], False):
                                        try:
                                            # Datei aus ZIP extrahieren
                                            file_data = zf.read(f['name'])
                                            display_name = os.path.basename(f['name'])

                                            # Dokumenttyp bestimmen
                                            if zip_doc_type == "Automatisch erkennen":
                                                # Einfache Erkennung basierend auf Dateinamen
                                                name_lower = display_name.lower()
                                                if 'rechnung' in name_lower or 'invoice' in name_lower:
                                                    doc_type = 'Rechnung'
                                                elif 'mahnung' in name_lower:
                                                    doc_type = 'Mahnung'
                                                elif 'vertrag' in name_lower or 'contract' in name_lower:
                                                    doc_type = 'Vertrag'
                                                elif 'mahnbescheid' in name_lower:
                                                    doc_type = 'Mahnbescheid'
                                                elif 'vollstreckung' in name_lower:
                                                    doc_type = 'Vollstreckungsbescheid'
                                                else:
                                                    doc_type = 'Sonstiges'
                                            else:
                                                doc_type = zip_doc_type

                                            # Neues Dokument erstellen
                                            doc_id = f'zip-{case_id}-{datetime.now().strftime("%Y%m%d%H%M%S%f")}'
                                            new_doc = {
                                                'id': doc_id,
                                                'name': display_name,
                                                'date': date.today(),
                                                'type': doc_type,
                                                'size': f'{len(file_data) // 1024} KB',
                                                'category': zip_doc_category
                                            }

                                            # Zu DEMO_DOCUMENTS hinzufügen
                                            if case_id not in DEMO_DOCUMENTS:
                                                DEMO_DOCUMENTS[case_id] = []
                                            DEMO_DOCUMENTS[case_id].append(new_doc)

                                            # PDF-Daten speichern falls PDF
                                            if f['ext'].lower() == '.pdf':
                                                st.session_state.document_pdfs[doc_id] = file_data

                                            imported_count += 1
                                        except Exception as e:
                                            errors.append(f"{f['name']}: {str(e)}")

                            if imported_count > 0:
                                st.success(f"✅ {imported_count} Dateien erfolgreich importiert!")
                            if errors:
                                for err in errors:
                                    st.error(f"❌ {err}")

                            # Auswahl zurücksetzen
                            if f'zip_selection_{case_id}' in st.session_state:
                                del st.session_state[f'zip_selection_{case_id}']

                            st.rerun()
                    else:
                        st.warning("⚠️ Keine unterstützten Dateien im Archiv gefunden.")
                        st.caption("Unterstützte Formate: PDF, DOCX, JPG, PNG, GIF, TIF, EML, MSG")

            except zipfile.BadZipFile:
                st.error("❌ Ungültige ZIP-Datei. Bitte laden Sie ein gültiges ZIP-Archiv hoch.")
            except Exception as e:
                st.error(f"❌ Fehler beim Verarbeiten: {str(e)}")

def get_document_pdf(doc, case_nr):
    """
    Holt die PDF-Bytes für ein Dokument.
    Priorisierung:
    1. Individuelles Dokument-PDF (aufgeteilt aus Gesamt-PDF)
    2. Gesamt-PDF der Akte
    3. Demo-PDF
    """
    doc_id = doc.get('id', '')

    # 1. Prüfen ob individuelles Dokument-PDF vorhanden
    if doc_id in st.session_state.document_pdfs:
        return st.session_state.document_pdfs[doc_id], True

    # 2. Prüfen ob Gesamt-PDF für die Akte vorhanden
    # Akte-ID aus doc_id extrahieren (Format: imp-doc-XXX -> case_id ist in imported_documents)
    for case_id, docs in st.session_state.get('imported_documents', {}).items():
        for d in docs:
            if d.get('id') == doc_id:
                if case_id in st.session_state.case_full_pdfs:
                    # Seite aus Gesamt-PDF extrahieren
                    page_num = doc.get('page', 1) - 1
                    full_pdf = st.session_state.case_full_pdfs[case_id]
                    single_page = extract_pdf_pages(full_pdf, page_num)
                    if single_page:
                        return single_page, True
                    return full_pdf, True

    # 3. Fallback auf alte pdf_viewer_content (Kompatibilität)
    if st.session_state.pdf_viewer_content is not None:
        return st.session_state.pdf_viewer_content, True

    # 4. Demo-PDF generieren
    return generate_demo_pdf(doc['name'], case_nr), False


def show_document_item(doc, case_nr, key_prefix, show_category=False):
    """Zeigt ein einzelnes Dokument in kompakter Form"""
    cat_id = doc.get('category', 'aussergerichtlich')
    cat_info = DOCUMENT_CATEGORIES.get(cat_id, DOCUMENT_CATEGORIES['aussergerichtlich'])

    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

    with col1:
        if show_category:
            st.write(f"{cat_info['icon']} **{doc['name']}**")
        else:
            st.write(f"📄 **{doc['name']}**")
        st.caption(f"{doc['type']} | {doc['size']}")

    with col2:
        st.write(fmt_date(doc['date']))

    with col3:
        # PDF-Inhalt für dieses Dokument holen
        pdf_content, is_real_pdf = get_document_pdf(doc, case_nr)

        st.download_button(
            "⬇️",
            data=pdf_content,
            file_name=doc['name'],
            mime="application/pdf" if doc['name'].endswith('.pdf') else "application/octet-stream",
            key=f"{key_prefix}_dl_{doc['id']}",
            help="Herunterladen"
        )

    with col4:
        if st.button("👁️", key=f"{key_prefix}_view_{doc['id']}", help="Ansehen"):
            st.session_state[f"viewing_{doc['id']}"] = True

    # Vorschau anzeigen wenn aktiviert
    if st.session_state.get(f"viewing_{doc['id']}", False):
        pdf_content, is_real_pdf = get_document_pdf(doc, case_nr)

        with st.container():
            st.divider()
            if is_real_pdf and doc['name'].endswith('.pdf'):
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
                st.markdown(f'''
                <iframe src="data:application/pdf;base64,{pdf_base64}" width="100%" height="400px"
                    style="border: 1px solid #ccc; border-radius: 5px;"></iframe>
                ''', unsafe_allow_html=True)
            else:
                # Versuche Text zu dekodieren, mit Fallback für binäre Inhalte
                if isinstance(pdf_content, bytes):
                    try:
                        text_content = pdf_content.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            text_content = pdf_content.decode('latin-1')
                        except UnicodeDecodeError:
                            text_content = f"[Binärer Inhalt - {len(pdf_content)} Bytes]"
                else:
                    text_content = str(pdf_content)
                st.text_area("Inhalt", value=text_content,
                    height=200, disabled=True, key=f"{key_prefix}_preview_{doc['id']}")

            if st.button("❌ Schließen", key=f"{key_prefix}_close_{doc['id']}"):
                st.session_state[f"viewing_{doc['id']}"] = False
                st.rerun()

    st.divider()

# =============================================================================
# RA-MICRO IMPORT FUNKTIONEN
# =============================================================================

def extract_pdf_pages(pdf_bytes, start_page, end_page=None):
    """
    Extrahiert bestimmte Seiten aus einem PDF.

    Args:
        pdf_bytes: Die PDF als Bytes
        start_page: Startseite (0-indiziert)
        end_page: Endseite (0-indiziert, inklusiv). Wenn None, nur start_page

    Returns:
        bytes: Die extrahierten Seiten als neues PDF
    """
    try:
        from PyPDF2 import PdfReader, PdfWriter

        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()

        if end_page is None:
            end_page = start_page

        # Seitenzahlen begrenzen
        start_page = max(0, min(start_page, len(reader.pages) - 1))
        end_page = max(start_page, min(end_page, len(reader.pages) - 1))

        for page_num in range(start_page, end_page + 1):
            writer.add_page(reader.pages[page_num])

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        return output.getvalue()

    except Exception as e:
        st.error(f"Fehler beim Extrahieren der PDF-Seiten: {str(e)}")
        return None


def split_pdf_by_toc(pdf_bytes, documents):
    """
    Teilt eine PDF basierend auf dem Inhaltsverzeichnis (Dokument-Seitenzuordnungen) auf.

    Args:
        pdf_bytes: Die komplette PDF als Bytes
        documents: Liste der Dokumente mit 'page' (Startseite) und optional 'end_page'

    Returns:
        dict: {doc_id: pdf_bytes} für jedes Dokument
    """
    if not documents or not pdf_bytes:
        return {}

    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        num_pages = len(reader.pages)

        # Dokumente nach Seite sortieren
        sorted_docs = sorted(documents, key=lambda d: d.get('page', 1))

        result = {}
        for i, doc in enumerate(sorted_docs):
            start_page = doc.get('page', 1) - 1  # 0-indiziert
            start_page = max(0, min(start_page, num_pages - 1))

            # Endseite aus Dokument nehmen oder berechnen
            if 'end_page' in doc and doc['end_page']:
                end_page = doc['end_page'] - 1  # 0-indiziert
            elif i + 1 < len(sorted_docs):
                next_page = sorted_docs[i + 1].get('page', num_pages + 1) - 1
                end_page = max(start_page, next_page - 1)
            else:
                end_page = num_pages - 1

            end_page = max(start_page, min(end_page, num_pages - 1))

            # Einzelnes Dokument extrahieren
            doc_pdf = extract_pdf_pages(pdf_bytes, start_page, end_page)
            if doc_pdf:
                result[doc['id']] = doc_pdf
                # Größe aktualisieren
                doc['size'] = f'{len(doc_pdf) // 1024} KB'

        return result

    except Exception as e:
        st.error(f"Fehler beim Aufteilen der PDF: {str(e)}")
        return {}


def render_pdf_page_as_image(pdf_bytes, page_num, width=200):
    """
    Rendert eine PDF-Seite als Base64-Bild für die Vorschau.

    Args:
        pdf_bytes: Die PDF als Bytes
        page_num: Seitennummer (0-indiziert)
        width: Breite des Bildes in Pixel

    Returns:
        str: Base64-kodiertes Bild oder None bei Fehler
    """
    try:
        # Versuche pdf2image zu nutzen (erfordert poppler)
        try:
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(
                pdf_bytes,
                first_page=page_num + 1,
                last_page=page_num + 1,
                size=(width, None)
            )
            if images:
                img_buffer = io.BytesIO()
                images[0].save(img_buffer, format='PNG')
                img_buffer.seek(0)
                return base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        except ImportError:
            pass

        # Fallback: Seite als Mini-PDF anzeigen
        return None

    except Exception:
        return None


def get_pdf_page_count(pdf_bytes):
    """Gibt die Anzahl der Seiten in einer PDF zurück."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return len(reader.pages)
    except Exception:
        return 0


def parse_ra_micro_pdf(pdf_file):
    """
    Parst eine RA-Micro Gesamt-PDF und extrahiert:
    - Aktenzeichen aus dem Inhaltsverzeichnis
    - Einzelne Dokumente mit Seitenbereichen
    - Forderungskonto mit Buchungen
    """
    try:
        from PyPDF2 import PdfReader
        import re

        pdf_reader = PdfReader(pdf_file)
        num_pages = len(pdf_reader.pages)

        # Gesamten Text extrahieren
        full_text = ""
        page_texts = {}
        for i, page in enumerate(pdf_reader.pages):
            text = page.extract_text() or ""
            full_text += text + "\n"
            page_texts[i] = text

        # Aktenzeichen extrahieren (Format: XX/YY oder XXXX/YY)
        az_pattern = r'(?:Aktenzeichen|Az\.?|Akte)[:\s]*(\d{1,4}/\d{2,4})'
        az_match = re.search(az_pattern, full_text, re.IGNORECASE)
        aktenzeichen = az_match.group(1) if az_match else f"IMP/{datetime.now().strftime('%y')}"

        # Parteien extrahieren - speziell für RA-Micro Aktenvorblatt
        # Mandant = Gläubiger (unser Auftraggeber)
        # Gegner = Schuldner (die beklagte Partei)

        creditor = ""
        debtor = ""
        creditor_address = ""
        debtor_address = ""

        # === METHODE 1: Aktenkurzbezeichnung "Mandant ./. Gegner" ===
        # Format: "Gehlsen ./. Berg" oder "Müller ./. Schmidt"
        kurzbezeichnung_match = re.search(
            r'([A-Za-zäöüÄÖÜßé][A-Za-zäöüÄÖÜßé\-\s\.]+?)\s*\./\.\s*([A-Za-zäöüÄÖÜßé][A-Za-zäöüÄÖÜßé\-\s\.]+?)(?:\n|$|\d{1,4}/\d{2})',
            full_text
        )
        mandant_kurz = ""
        gegner_kurz = ""
        if kurzbezeichnung_match:
            mandant_kurz = kurzbezeichnung_match.group(1).strip()
            gegner_kurz = kurzbezeichnung_match.group(2).strip()

        # === METHODE 2: "Forderung der Firma [Name]" oder "Forderung der [Name]" ===
        forderung_match = re.search(
            r'Forderung\s+(?:der\s+)?(?:Firma\s+)?([A-Za-zäöüÄÖÜßé][A-Za-zäöüÄÖÜßé\s\-\.&,]+?(?:GmbH|AG|KG|OHG|UG|e\.K\.|Co\.\s*KG|mbH|& Co\.)[A-Za-zäöüÄÖÜßé\s\-\.&,]*)',
            full_text, re.IGNORECASE
        )
        if forderung_match:
            creditor = forderung_match.group(1).strip()

        # === METHODE 3: RA-Micro Aktenvorblatt - Firma vor Adresse ===
        # Suche Firmenname mit Rechtsform (GmbH, KG, etc.) gefolgt von Straßenadresse
        if not creditor:
            firma_match = re.search(
                r'([A-Za-zäöüÄÖÜßé][A-Za-zäöüÄÖÜßé\s\-\.&,]+?(?:GmbH|AG|KG|OHG|UG|e\.K\.|Co\.\s*KG|mbH|& Co\.)[A-Za-zäöüÄÖÜßé\s\-\.&,]*)\s*\n\s*([A-Za-zäöüÄÖÜß][A-Za-zäöüÄÖÜß\s\-]+(?:straße|str\.?|weg|platz|allee)\s*\d+[a-zA-Z\-\s]*)\s*\n\s*(\d{5})\s+([A-Za-zäöüÄÖÜß\-]+)',
                full_text, re.IGNORECASE
            )
            if firma_match:
                creditor = firma_match.group(1).strip()
                creditor_address = f"{firma_match.group(2).strip()}\n{firma_match.group(3)} {firma_match.group(4)}"

        # === METHODE 4: "Herrn/Frau [Name]" für Schuldner (Privatperson) ===
        herrn_match = re.search(
            r'(?:Herrn|Frau)\s+([A-Za-zäöüÄÖÜßé][A-Za-zäöüÄÖÜßé\s\-\.]+?)(?:\n|$)',
            full_text
        )
        if herrn_match:
            debtor = herrn_match.group(1).strip()
            # Suche Adresse VOR dem Namen (RA-Micro Format: PLZ/Ort, Straße, dann Name)
            herrn_pos = herrn_match.start()
            before_herrn = full_text[max(0, herrn_pos-200):herrn_pos]
            # Suche rückwärts nach PLZ + Ort, dann Straße
            addr_before = re.search(
                r'(\d{5})\s+([A-Za-zäöüÄÖÜß\-]+)\s*\n\s*([A-Za-zäöüÄÖÜß][A-Za-zäöüÄÖÜß\s\-]+(?:straße|str\.?|weg|platz|allee|gasse)\s*\d+[a-zA-Z]?)',
                before_herrn, re.IGNORECASE
            )
            if addr_before:
                debtor_address = f"{addr_before.group(3).strip()}\n{addr_before.group(1)} {addr_before.group(2)}"

        # === METHODE 5: Suche nach internen Adressnummern (RA-Micro spezifisch) ===
        # Nach der zweiten Adressnr: kommt oft der Gegner
        if not debtor:
            # Finde alle "Adressnr:" Einträge und den Text dazwischen
            adressnr_matches = list(re.finditer(r'Adressnr[:\s]*(\d+)?', full_text, re.IGNORECASE))
            if len(adressnr_matches) >= 2:
                # Bereich zwischen zweitem Adressnr und Ende oder nächstem Marker
                second_addr_pos = adressnr_matches[-1].end()
                gegner_section = full_text[second_addr_pos:second_addr_pos+500]
                # Suche nach "Herrn/Frau Name" in diesem Bereich
                name_in_section = re.search(r'(?:Herrn|Frau)\s+([A-Za-zäöüÄÖÜßé][A-Za-zäöüÄÖÜßé\s\-\.]+?)(?:\n|$)', gegner_section)
                if name_in_section:
                    debtor = name_in_section.group(1).strip()

        # === FALLBACK: Nutze Kurzbezeichnung wenn vorhanden ===
        if not creditor and mandant_kurz:
            # Suche vollständigen Namen basierend auf Kurznamen
            vollname_match = re.search(
                rf'([A-Za-zäöüÄÖÜßé][A-Za-zäöüÄÖÜßé\s\-\.&,]*{re.escape(mandant_kurz)}[A-Za-zäöüÄÖÜßé\s\-\.&,]*(?:GmbH|AG|KG|OHG|UG|e\.K\.|Co\.\s*KG|mbH|& Co\.)[A-Za-zäöüÄÖÜßé\s\-\.&,]*)',
                full_text, re.IGNORECASE
            )
            if vollname_match:
                creditor = vollname_match.group(1).strip()
            else:
                creditor = mandant_kurz

        if not debtor and gegner_kurz:
            # Suche vollständigen Namen basierend auf Kurznamen
            vollname_match = re.search(
                rf'(?:Herrn|Frau)?\s*([A-Za-zäöüÄÖÜßé\s\-\.]*{re.escape(gegner_kurz)}[A-Za-zäöüÄÖÜßé\s\-\.]*)',
                full_text, re.IGNORECASE
            )
            if vollname_match:
                debtor = vollname_match.group(1).strip()
            else:
                debtor = gegner_kurz

        # === ADRESSEN EXTRAHIEREN (falls noch nicht gefunden) ===
        if not creditor_address or not debtor_address:
            # Suche nach Straße + PLZ + Ort Pattern (auch mit Hausnummernbereichen wie 106 - 114)
            address_pattern = r'([A-Za-zäöüÄÖÜß][A-Za-zäöüÄÖÜß\s\-]+(?:straße|str\.?|weg|platz|allee|gasse|ring|damm|ufer)\s*\d+[a-zA-Z]?(?:\s*[-–]\s*\d+)?)\s*\n?\s*(\d{5})\s+([A-Za-zäöüÄÖÜß\-]+)'
            addr_matches = re.findall(address_pattern, full_text, re.IGNORECASE)
            if addr_matches:
                if not creditor_address and len(addr_matches) >= 1:
                    cred_addr = addr_matches[0]
                    creditor_address = f"{cred_addr[0].strip()}\n{cred_addr[1]} {cred_addr[2]}"
                if not debtor_address and len(addr_matches) >= 2:
                    deb_addr = addr_matches[-1]
                    debtor_address = f"{deb_addr[0].strip()}\n{deb_addr[1]} {deb_addr[2]}"

        # === BEREINIGUNG ===
        creditor = re.sub(r'\s+', ' ', creditor).strip(',.-:; \n\t')[:80] if creditor else "Unbekannter Gläubiger"
        debtor = re.sub(r'\s+', ' ', debtor).strip(',.-:; \n\t')[:80] if debtor else "Unbekannter Schuldner"
        # Entferne "Herrn" oder "Frau" am Anfang
        debtor = re.sub(r'^(Herrn?|Frau)\s+', '', debtor)

        # Inhaltsverzeichnis parsen - Dokumente identifizieren mit Kategorien
        documents = []

        # Erweiterte Dokumenttypen mit Kategorien
        doc_type_categories = {
            'rechnung': 'aussergerichtlich',
            'mahnung': 'aussergerichtlich',
            'forderungsaufstellung': 'aussergerichtlich',
            'vertrag': 'aussergerichtlich',
            'lieferschein': 'aussergerichtlich',
            'mahnbescheid': 'gerichtlich',
            'vollstreckungsbescheid': 'gerichtlich',
            'pfüb': 'gerichtlich',
            'klage': 'gerichtlich',
            'urteil': 'gerichtlich',
            'beschluss': 'gerichtlich',
            'zustellung': 'gerichtlich',
            'schreiben': 'aussergerichtlich',
            'brief': 'aussergerichtlich',
            'notiz': 'intern',
            'vermerk': 'intern',
            'aktennotiz': 'intern',
            'aktenvorblatt': 'intern',
            'inhaltsverzeichnis': 'intern',
            'sachstandsbericht': 'mandant',
            'vollmacht': 'mandant',
            'mandantenbrief': 'mandant',
            'schuldnerbrief': 'schuldner',
            'ratenzahlung': 'schuldner',
            'vergleich': 'schuldner',
            'forderungskonto': 'intern',
            'kostenrechnung': 'aussergerichtlich',
            'zahlungsaufforderung': 'aussergerichtlich',
            'anschreiben': 'aussergerichtlich',
        }

        # ============================================================
        # VERBESSERTE INHALTSVERZEICHNIS-ERKENNUNG
        # ============================================================

        # Muster für typische RA-Micro Inhaltsverzeichnis-Formate:
        # "Seite 1 - 3: Aktenvorblatt"
        # "Seite 4: Rechnung Nr. 123"
        # "1. Rechnung vom 01.01.2024......Seite 5"
        # "Rechnung                    Seite 5"
        # "- Mahnung vom 15.01.2024    S. 8-10"

        toc_patterns = [
            # Format: "Seite X - Y: Dokumentname" oder "Seite X: Dokumentname"
            r'Seite\s*(\d+)\s*(?:[-–bis]\s*(\d+))?\s*[:\s]+([A-Za-zäöüÄÖÜß][A-Za-zäöüÄÖÜß\s\-\.0-9]+)',

            # Format: "Dokumentname......Seite X" oder "Dokumentname    Seite X-Y"
            r'([A-Za-zäöüÄÖÜß][A-Za-zäöüÄÖÜß\s\-]+?)[\.\s]{2,}(?:Seite|S\.?)\s*(\d+)\s*(?:[-–bis]\s*(\d+))?',

            # Format: "X. Dokumentname" mit optionaler Seitenzahl
            r'(\d+)\.\s+([A-Za-zäöüÄÖÜß][A-Za-zäöüÄÖÜß\s\-\.]+?)(?:\s+(?:Seite|S\.?)\s*(\d+))?(?:\n|$)',

            # Format: "- Dokumentname (Seite X)"
            r'[-•]\s*([A-Za-zäöüÄÖÜß][A-Za-zäöüÄÖÜß\s\-\.0-9]+?)(?:\s*\(?\s*(?:Seite|S\.?)\s*(\d+)\s*(?:[-–bis]\s*(\d+))?\s*\)?)?(?:\n|$)',

            # Format: Einzelne bekannte Dokumenttypen mit Seitenzahlen
            r'(Rechnung|Mahnung|Mahnbescheid|Vollstreckungsbescheid|Vertrag|Schreiben|Vollmacht|Klage|PfÜB|Zustellung|Forderungskonto|Aktenvorblatt)(?:[^\n]*?)(?:Seite|S\.?)\s*(\d+)',
        ]

        doc_id_counter = 1
        found_documents = []  # Liste für alle gefundenen Dokumente

        # Zuerst versuchen wir das Inhaltsverzeichnis auf den ersten Seiten zu finden
        toc_text = "\n".join([page_texts.get(i, "") for i in range(min(3, num_pages))])

        for pattern in toc_patterns:
            for match in re.finditer(pattern, toc_text + "\n" + full_text[:5000], re.IGNORECASE):
                groups = match.groups()
                doc_name = None
                start_page = 1
                end_page = None

                # Pattern-spezifische Extraktion
                for i, g in enumerate(groups):
                    if g:
                        g_stripped = g.strip()
                        # Prüfen ob es eine Seitenzahl ist
                        if g_stripped.isdigit():
                            page_val = int(g_stripped)
                            if page_val <= num_pages:
                                if start_page == 1 or page_val < start_page:
                                    start_page = page_val
                                elif page_val > start_page:
                                    end_page = page_val
                        else:
                            # Dokumentname extrahieren
                            potential_name = g_stripped
                            # Bereinigen
                            potential_name = re.sub(r'^[\d\.\-\s]+', '', potential_name)
                            potential_name = re.sub(r'[\.\s]+$', '', potential_name)
                            if len(potential_name) >= 3 and not potential_name.isdigit():
                                doc_name = potential_name

                if doc_name and start_page > 0:
                    # Prüfen ob ähnliches Dokument bereits existiert
                    is_duplicate = False
                    for existing in found_documents:
                        if existing['start_page'] == start_page and doc_name.lower()[:10] == existing['name'].lower()[:10]:
                            is_duplicate = True
                            break

                    if not is_duplicate:
                        # Kategorie ermitteln
                        category = 'aussergerichtlich'
                        doc_type = doc_name
                        for key, cat in doc_type_categories.items():
                            if key in doc_name.lower():
                                category = cat
                                doc_type = key.title()
                                break

                        found_documents.append({
                            'name': doc_name,
                            'type': doc_type,
                            'category': category,
                            'start_page': min(start_page, num_pages),
                            'end_page': min(end_page, num_pages) if end_page else None,
                        })

        # Dokumente nach Startseite sortieren
        found_documents.sort(key=lambda x: x['start_page'])

        # End-Seiten berechnen falls nicht angegeben
        for i, doc in enumerate(found_documents):
            if doc['end_page'] is None:
                if i + 1 < len(found_documents):
                    # Nächstes Dokument beginnt auf nächster Seite
                    doc['end_page'] = found_documents[i + 1]['start_page'] - 1
                else:
                    # Letztes Dokument geht bis zum Ende
                    doc['end_page'] = num_pages
            # Mindestens eine Seite
            if doc['end_page'] < doc['start_page']:
                doc['end_page'] = doc['start_page']

        # Finale Dokument-Liste erstellen
        for doc in found_documents:
            page_count = doc['end_page'] - doc['start_page'] + 1
            documents.append({
                'id': f'imp-doc-{doc_id_counter:03d}',
                'name': f"{doc['name'][:40]}.pdf",
                'type': doc['type'],
                'category': doc['category'],
                'page': doc['start_page'],
                'end_page': doc['end_page'],
                'page_count': page_count,
                'date': date.today() - timedelta(days=doc_id_counter * 5),
                'size': f'{max(50, page_count * 30)} KB'
            })
            doc_id_counter += 1

        # Fallback: Wenn keine Dokumente gefunden, Standarddokumente mit Kategorien erstellen
        if not documents:
            documents = [
                {'id': 'imp-doc-001', 'name': 'Forderungsaufstellung.pdf', 'type': 'Forderungsaufstellung', 'category': 'aussergerichtlich', 'page': 1, 'date': date.today(), 'size': '150 KB'},
                {'id': 'imp-doc-002', 'name': 'Originalrechnung.pdf', 'type': 'Rechnung', 'category': 'aussergerichtlich', 'page': 2, 'date': date.today() - timedelta(30), 'size': '80 KB'},
                {'id': 'imp-doc-003', 'name': 'Gesamtakte_Import.pdf', 'type': 'Akte', 'category': 'intern', 'page': 1, 'date': date.today(), 'size': f'{num_pages * 50} KB'},
            ]

        # Forderungskonto extrahieren
        bookings = []

        # Hauptforderung suchen
        amount_patterns = [
            r'(?:Hauptforderung|Forderung|Rechnungsbetrag|Kaufpreis)[:\s]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:€|EUR)',
            r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:€|EUR)\s*(?:Hauptforderung|Forderung)',
            r'Summe[:\s]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:€|EUR)',
        ]

        hauptforderung = 0.0
        for pattern in amount_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace('.', '').replace(',', '.')
                try:
                    hauptforderung = float(amount_str)
                    break
                except ValueError:
                    continue

        if hauptforderung == 0:
            hauptforderung = 5000.00  # Demo-Fallback

        bookings.append({
            'date': date.today() - timedelta(60),
            'type': 'S',
            'amount': hauptforderung,
            'cat': 'Hauptforderung',
            'desc': 'Importiert aus RA-Micro'
        })

        # Zinsen suchen
        zinsen_pattern = r'(?:Zinsen|Verzugszinsen)[:\s]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:€|EUR)'
        zinsen_match = re.search(zinsen_pattern, full_text, re.IGNORECASE)
        if zinsen_match:
            zinsen_str = zinsen_match.group(1).replace('.', '').replace(',', '.')
            try:
                zinsen = float(zinsen_str)
                bookings.append({
                    'date': date.today() - timedelta(30),
                    'type': 'S',
                    'amount': zinsen,
                    'cat': 'Zinsen',
                    'desc': 'Verzugszinsen'
                })
            except ValueError:
                pass

        # RA-Gebühren suchen
        gebuehren_pattern = r'(?:RA-Gebühren|Rechtsanwaltsgebühren|Anwaltskosten|Geschäftsgebühr)[:\s]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:€|EUR)'
        gebuehren_match = re.search(gebuehren_pattern, full_text, re.IGNORECASE)
        if gebuehren_match:
            gebuehren_str = gebuehren_match.group(1).replace('.', '').replace(',', '.')
            try:
                gebuehren = float(gebuehren_str)
                bookings.append({
                    'date': date.today() - timedelta(45),
                    'type': 'S',
                    'amount': gebuehren,
                    'cat': 'RA-Gebühren',
                    'desc': '1,3 Geschäftsgebühr Nr. 2300 VV RVG'
                })
            except ValueError:
                pass
        else:
            # Standard RA-Gebühren basierend auf Streitwert
            ra_gebuehr = round(hauptforderung * 0.065, 2)  # Vereinfacht
            bookings.append({
                'date': date.today() - timedelta(45),
                'type': 'S',
                'amount': ra_gebuehr,
                'cat': 'RA-Gebühren',
                'desc': '1,3 Geschäftsgebühr Nr. 2300 VV RVG'
            })

        # Zahlungen suchen
        zahlung_pattern = r'(?:Zahlung|Teilzahlung|Eingang)[:\s]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:€|EUR)'
        for match in re.finditer(zahlung_pattern, full_text, re.IGNORECASE):
            zahlung_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                zahlung = float(zahlung_str)
                if zahlung > 0 and zahlung < hauptforderung:
                    bookings.append({
                        'date': date.today() - timedelta(15),
                        'type': 'H',
                        'amount': zahlung,
                        'cat': 'Zahlung',
                        'desc': 'Teilzahlung'
                    })
                    break
            except ValueError:
                continue

        # Status ermitteln
        status = 'offen'
        dunning = 'nicht_beantragt'
        enforcement = 'nicht_begonnen'

        if re.search(r'vollstreckungsbescheid|VB\s*erlassen', full_text, re.IGNORECASE):
            status = 'vollstreckung'
            dunning = 'titel_rechtskraeftig'
            enforcement = 'gv_auftrag'
        elif re.search(r'mahnbescheid|MB\s*beantragt', full_text, re.IGNORECASE):
            status = 'mahnverfahren'
            dunning = 'mb_zugestellt'

        return {
            'success': True,
            'aktenzeichen': aktenzeichen,
            'creditor': creditor[:50],
            'debtor': debtor[:50],
            'creditor_address': creditor_address,
            'debtor_address': debtor_address,
            'documents': documents,
            'bookings': bookings,
            'status': status,
            'dunning': dunning,
            'enforcement': enforcement,
            'principal': hauptforderung,
            'num_pages': num_pages,
            'raw_text_preview': full_text[:3000] + '...' if len(full_text) > 3000 else full_text
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def show_ra_micro_import():
    """RA-Micro Import Seite"""
    st.markdown("## 📥 RA-Micro Aktenimport")
    st.info("""
    **So funktioniert der Import:**
    1. Exportieren Sie die Akte in RA-Micro als Gesamt-PDF
    2. Die PDF sollte das Inhaltsverzeichnis, alle Schreiben und das Forderungskonto enthalten
    3. Laden Sie die PDF hier hoch
    4. Das System extrahiert automatisch: Aktenzeichen, Dokumente, Forderungen
    """)

    st.divider()

    # PDF Upload
    uploaded_pdf = st.file_uploader(
        "📄 RA-Micro Gesamt-PDF hochladen",
        type=['pdf'],
        help="Laden Sie die aus RA-Micro exportierte Gesamt-PDF hoch"
    )

    if uploaded_pdf:
        st.success(f"✅ Datei geladen: {uploaded_pdf.name} ({uploaded_pdf.size / 1024:.1f} KB)")

        # PDF in Session speichern für Viewer
        pdf_bytes = uploaded_pdf.getvalue()
        st.session_state.pdf_viewer_content = pdf_bytes

        with st.spinner("🔄 PDF wird analysiert..."):
            result = parse_ra_micro_pdf(io.BytesIO(pdf_bytes))

        if result['success']:
            st.markdown("### ✅ Analyse erfolgreich!")

            # Vorschau der extrahierten Daten
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 📋 Akten-Informationen")
                st.write(f"**Aktenzeichen:** {result['aktenzeichen']}")
                st.write(f"**Gläubiger (Mandant):** {result['creditor']}")
                if result.get('creditor_address'):
                    st.caption(f"   {result['creditor_address']}")
                st.write(f"**Schuldner (Gegner):** {result['debtor']}")
                if result.get('debtor_address'):
                    st.caption(f"   {result['debtor_address']}")
                st.write(f"**Status:** {result['status'].title()}")
                st.write(f"**Seiten:** {result['num_pages']}")

            with col2:
                st.markdown("#### 💰 Forderungskonto")
                total_soll = sum(b['amount'] for b in result['bookings'] if b['type'] == 'S')
                total_haben = sum(b['amount'] for b in result['bookings'] if b['type'] == 'H')
                st.metric("Soll (Forderungen)", fmt_curr(total_soll))
                st.metric("Haben (Zahlungen)", fmt_curr(total_haben))
                st.metric("Offener Betrag", fmt_curr(total_soll - total_haben))

            st.divider()

            # Erkannte Dokumente nach Kategorien
            st.markdown("#### 📄 Erkannte Dokumente")

            # Dokumente nach Kategorie gruppieren
            docs_by_cat = {}
            for doc in result['documents']:
                cat = doc.get('category', 'aussergerichtlich')
                if cat not in docs_by_cat:
                    docs_by_cat[cat] = []
                docs_by_cat[cat].append(doc)

            for cat_id, cat_info in DOCUMENT_CATEGORIES.items():
                cat_docs = docs_by_cat.get(cat_id, [])
                if cat_docs:
                    with st.expander(f"{cat_info['icon']} **{cat_info['name']}** ({len(cat_docs)} Dokumente)"):
                        for doc in cat_docs:
                            c1, c2, c3 = st.columns([3, 2, 2])
                            c1.write(f"📄 {doc['name']}")
                            c2.write(doc['type'])
                            c3.write(f"Seite {doc['page']}")

            # Debug: Extrahierter Text anzeigen
            with st.expander("🔍 Extrahierter PDF-Text (Debug)"):
                st.caption("Falls Mandant/Gegner nicht erkannt wurden, suchen Sie hier nach den korrekten Bezeichnungen:")
                st.text_area("PDF-Text (erste 2000 Zeichen)", result.get('raw_text_preview', 'Kein Text extrahiert')[:2000], height=200, disabled=True)
                st.info("💡 Tipp: Suchen Sie nach 'Mandant', 'Gegner', 'Gläubiger', 'Schuldner' im Text")

            st.divider()

            # Buchungen
            st.markdown("#### 📊 Erkannte Buchungen")
            for b in result['bookings']:
                c1, c2, c3, c4 = st.columns([2, 3, 2, 2])
                c1.write(fmt_date(b['date']))
                c2.write(b['desc'])
                c3.write(b['cat'])
                if b['type'] == 'S':
                    c4.write(f"+{fmt_curr(b['amount'])}")
                else:
                    c4.markdown(f"**-{fmt_curr(b['amount'])}**")

            st.divider()

            # PDF Vorschau
            with st.expander("👁️ PDF-Vorschau (Text)"):
                st.text(result['raw_text_preview'])

            # PDF-Viewer mit base64
            with st.expander("📖 PDF-Dokument anzeigen"):
                pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                pdf_display = f'''
                <iframe
                    src="data:application/pdf;base64,{pdf_base64}"
                    width="100%"
                    height="600px"
                    type="application/pdf"
                    style="border: 1px solid #ccc; border-radius: 5px;">
                </iframe>
                '''
                st.markdown(pdf_display, unsafe_allow_html=True)

            st.divider()

            # =====================================================================
            # INTELLIGENTE DOKUMENTENTRENNUNG (OCR + Heuristik)
            # =====================================================================
            st.markdown("#### 🧠 Intelligente Dokumententrennung")

            if PDF_SPLITTER_AVAILABLE:
                capabilities = get_splitter_capabilities()

                cap_cols = st.columns(3)
                with cap_cols[0]:
                    if capabilities['pymupdf']:
                        st.success("✅ PyMuPDF verfügbar")
                    else:
                        st.warning("⚠️ PyMuPDF nicht installiert")
                with cap_cols[1]:
                    if capabilities['ocr']:
                        st.success("✅ OCR verfügbar")
                    else:
                        st.info("ℹ️ OCR nicht verfügbar")
                with cap_cols[2]:
                    if capabilities['full_support']:
                        st.success("✅ Volle Unterstützung")
                    else:
                        st.info("ℹ️ Basis-Modus")

                st.info("""
                **Intelligente Trennung** erkennt Dokumente automatisch anhand von:
                - 📑 PDF-Bookmarks (falls vorhanden)
                - 📝 Textmustern (Mahnbescheid, Rechnung, Vollstreckungsbescheid, etc.)
                - 🔍 OCR für gescannte Dokumente
                - 📄 "Seite 1" Markierungen
                """)

                # Einstellungen für intelligente Trennung
                with st.expander("⚙️ Trennungseinstellungen"):
                    split_mode = st.selectbox(
                        "Trennungsmodus",
                        options=["auto", "heuristic", "bookmarks"],
                        format_func=lambda x: {
                            "auto": "🔄 Automatisch (Bookmarks → Heuristik)",
                            "heuristic": "🧠 Nur Heuristik (Textmuster + OCR)",
                            "bookmarks": "📑 Nur Bookmarks"
                        }.get(x, x),
                        help="Wählen Sie die Methode zur Dokumenttrennung"
                    )

                    use_ocr = st.checkbox(
                        "🔍 OCR für gescannte Seiten verwenden",
                        value=capabilities['ocr'],
                        disabled=not capabilities['ocr'],
                        help="Aktiviert Texterkennung für Seiten ohne eingebetteten Text"
                    )

                # Intelligente Trennung durchführen
                if st.button("🚀 Intelligente Trennung starten", type="primary"):
                    with st.spinner("🔄 Analysiere Dokumente mit KI..."):
                        try:
                            splitter = PDFSplitter(use_ocr=use_ocr)
                            segments = splitter.split(pdf_bytes, mode=split_mode)

                            # In Session State speichern
                            st.session_state.intelligent_segments = segments
                            st.session_state.intelligent_split_done = True
                            st.success(f"✅ {len(segments)} Dokumente erkannt!")

                        except Exception as e:
                            st.error(f"❌ Fehler bei der Analyse: {str(e)}")
                            st.session_state.intelligent_split_done = False

                # Ergebnisse anzeigen
                if st.session_state.get('intelligent_split_done', False):
                    segments = st.session_state.get('intelligent_segments', [])

                    st.markdown("##### 📋 Erkannte Dokumente")

                    # Konfidenz-Legende
                    st.caption("🟢 Hohe Konfidenz | 🟡 Mittlere Konfidenz | 🔴 Niedrige Konfidenz | 🔍 = OCR verwendet")

                    for idx, seg in enumerate(segments):
                        conf_color = "🟢" if seg.confidence >= 0.9 else ("🟡" if seg.confidence >= 0.7 else "🔴")
                        ocr_indicator = " 🔍" if seg.ocr_used else ""

                        with st.expander(f"{conf_color} **{seg.title}**{ocr_indicator} (Seiten {seg.start_page}-{seg.end_page})"):
                            seg_cols = st.columns([2, 2, 1])
                            with seg_cols[0]:
                                st.write(f"**Typ:** {seg.label}")
                                st.write(f"**Kategorie:** {seg.category}")
                            with seg_cols[1]:
                                st.write(f"**Seiten:** {seg.start_page} - {seg.end_page}")
                                st.write(f"**Anzahl:** {seg.pages} Seiten")
                            with seg_cols[2]:
                                st.write(f"**Konfidenz:** {seg.confidence:.0%}")
                                if seg.ocr_used:
                                    st.caption("OCR verwendet")

                            # Titel editieren
                            new_title = st.text_input(
                                "Titel anpassen",
                                value=seg.title,
                                key=f"seg_title_{idx}"
                            )
                            if new_title != seg.title:
                                segments[idx].title = new_title
                                st.session_state.intelligent_segments = segments

                    st.divider()

                    # Import mit intelligenter Trennung
                    if st.button("✅ Mit intelligenter Trennung importieren", type="primary", key="import_intelligent"):
                        try:
                            # Neue Akte erstellen
                            new_case_id = f"imp-{len(st.session_state.imported_cases) + 1:03d}"

                            new_case = {
                                'id': new_case_id,
                                'nr': result['aktenzeichen'],
                                'creditor': result['creditor'],
                                'debtor': result['debtor'],
                                'creditor_address': result.get('creditor_address', ''),
                                'debtor_address': result.get('debtor_address', ''),
                                'subject': f'Import aus RA-Micro - {uploaded_pdf.name}',
                                'status': result['status'],
                                'dunning': result['dunning'],
                                'enforcement': result['enforcement'],
                                'principal': result['principal'],
                                'interest': 5.0,
                                'due_date': date.today() - timedelta(days=60),
                                'created': datetime.now(),
                                'imported': True,
                                'source_pdf': uploaded_pdf.name,
                                'contract_type': 'Importiert',
                                'contract_date': date.today() - timedelta(days=90),
                                'invoice_nr': f'IMP-{new_case_id}',
                                'invoice_date': date.today() - timedelta(days=60),
                                'leistung': 'Aus RA-Micro Import',
                                'mahnung_dates': [],
                            }

                            st.session_state.imported_cases.append(new_case)
                            DEMO_CASES.append(new_case)

                            # Dokumente aus intelligenter Trennung erstellen
                            splitter = PDFSplitter(use_ocr=use_ocr)
                            documents_to_import = []
                            doc_pdfs = {}

                            for idx, seg in enumerate(segments, start=1):
                                doc_id = f"{new_case_id}-doc-{idx:03d}"
                                doc_dict = seg.to_document_dict(doc_id)
                                documents_to_import.append(doc_dict)

                                # PDF extrahieren
                                doc_pdf = splitter.extract_segment(pdf_bytes, seg)
                                doc_pdfs[doc_id] = doc_pdf
                                st.session_state.document_pdfs[doc_id] = doc_pdf

                            st.session_state.imported_documents[new_case_id] = documents_to_import
                            DEMO_DOCUMENTS[new_case_id] = documents_to_import

                            # Gesamt-PDF speichern
                            st.session_state.case_full_pdfs[new_case_id] = pdf_bytes

                            # Buchungen
                            st.session_state.imported_bookings[new_case_id] = result['bookings']
                            DEMO_BOOKINGS[new_case_id] = result['bookings']

                            # Session State bereinigen
                            st.session_state.intelligent_split_done = False
                            st.session_state.intelligent_segments = []

                            st.success(f"✅ Akte {result['aktenzeichen']} mit {len(doc_pdfs)} intelligent getrennten Dokumenten importiert!")
                            st.balloons()

                            st.session_state.page = 'cases'
                            st.rerun()

                        except Exception as e:
                            st.error(f"❌ Import fehlgeschlagen: {str(e)}")

            else:
                st.warning("⚠️ Intelligente PDF-Trennung nicht verfügbar. Bitte installieren Sie `pymupdf` und `pytesseract`.")

            st.divider()

            # =====================================================================
            # MANUELLE DOKUMENTENTRENNUNG
            # =====================================================================
            st.markdown("#### ✂️ Manuelle Dokumententrennung")
            st.info("Falls die automatische Erkennung nicht alle Dokumente korrekt getrennt hat, können Sie hier manuell Trennstellen setzen.")

            # Session State für manuelle Trennungen initialisieren
            if 'manual_splits' not in st.session_state:
                st.session_state.manual_splits = []
            if 'manual_doc_names' not in st.session_state:
                st.session_state.manual_doc_names = {}

            num_pages = result['num_pages']

            # Layout: PDF-Vorschau links, Trennungssteuerung rechts
            preview_col, control_col = st.columns([1, 1])

            with preview_col:
                st.markdown("##### 👁️ PDF-Vorschau")
                # Seitennavigation
                if 'preview_page' not in st.session_state:
                    st.session_state.preview_page = 0

                nav_cols = st.columns([1, 3, 1])
                with nav_cols[0]:
                    if st.button("◀️ Zurück", disabled=st.session_state.preview_page == 0):
                        st.session_state.preview_page -= 1
                        st.rerun()
                with nav_cols[1]:
                    st.session_state.preview_page = st.selectbox(
                        "Seite",
                        range(num_pages),
                        index=st.session_state.preview_page,
                        format_func=lambda x: f"Seite {x + 1} von {num_pages}",
                        label_visibility="collapsed"
                    )
                with nav_cols[2]:
                    if st.button("Weiter ▶️", disabled=st.session_state.preview_page >= num_pages - 1):
                        st.session_state.preview_page += 1
                        st.rerun()

                # Aktuelle Seite als PDF anzeigen
                current_page = st.session_state.preview_page
                is_split_page = current_page in st.session_state.get('manual_splits', []) or current_page == 0

                if is_split_page:
                    st.success(f"📄 **Seite {current_page + 1}** - Dokumentanfang")
                else:
                    st.info(f"📄 Seite {current_page + 1}")

                page_pdf = extract_pdf_pages(pdf_bytes, current_page)
                if page_pdf:
                    page_b64 = base64.b64encode(page_pdf).decode('utf-8')
                    st.markdown(f'''
                    <iframe
                        src="data:application/pdf;base64,{page_b64}#toolbar=0&navpanes=0"
                        width="100%"
                        height="500px"
                        style="border: 2px solid {'#28a745' if is_split_page else '#dee2e6'}; border-radius: 5px;">
                    </iframe>
                    ''', unsafe_allow_html=True)
                else:
                    # Fallback: Ganzes PDF mit Scroll
                    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                    st.markdown(f'''
                    <iframe
                        src="data:application/pdf;base64,{pdf_base64}#page={current_page + 1}"
                        width="100%"
                        height="500px"
                        style="border: 1px solid #ccc; border-radius: 5px;">
                    </iframe>
                    ''', unsafe_allow_html=True)

                # Schnell-Trennung für aktuelle Seite
                if current_page > 0:
                    if current_page in st.session_state.get('manual_splits', []):
                        if st.button(f"✂️ Trennung vor Seite {current_page + 1} entfernen", use_container_width=True):
                            st.session_state.manual_splits.remove(current_page)
                            st.rerun()
                    else:
                        if st.button(f"➕ Trennung vor Seite {current_page + 1} setzen", use_container_width=True, type="primary"):
                            if 'manual_splits' not in st.session_state:
                                st.session_state.manual_splits = []
                            st.session_state.manual_splits.append(current_page)
                            st.session_state.manual_splits.sort()
                            st.rerun()

            with control_col:
                st.markdown("##### ✂️ Trennungssteuerung")
                st.caption("Klicken Sie auf Seitennummern, um zur Vorschau zu springen. Setzen Sie Trennstellen mit den Buttons.")

                # Kompakte Seitenübersicht mit Buttons
                pages_per_row = 8

                for row_start in range(0, num_pages, pages_per_row):
                    row_end = min(row_start + pages_per_row, num_pages)
                    cols = st.columns(pages_per_row)

                    for i, page_num in enumerate(range(row_start, row_end)):
                        with cols[i]:
                            is_split = page_num in st.session_state.manual_splits or page_num == 0
                            is_current = page_num == st.session_state.get('preview_page', 0)

                            # Seite als klickbarer Button
                            btn_type = "primary" if is_current else ("secondary" if not is_split else "secondary")
                            btn_label = f"{'📄' if is_split else ''}{page_num + 1}"

                            if st.button(
                                btn_label,
                                key=f"page_btn_{page_num}",
                                use_container_width=True,
                                type=btn_type,
                                help=f"Seite {page_num + 1} {'(Dokumentanfang)' if is_split else ''}"
                            ):
                                st.session_state.preview_page = page_num
                                st.rerun()

                st.divider()

                # Schnell-Trennungen setzen
                st.markdown("##### ➕ Trennstellen setzen")
                st.caption("Wählen Sie Seiten, vor denen ein neues Dokument beginnt:")

                # Dropdown zur Auswahl einer Seite für Trennung
                available_pages = [p for p in range(1, num_pages) if p not in st.session_state.manual_splits]
                if available_pages:
                    split_page = st.selectbox(
                        "Trennung vor Seite:",
                        available_pages,
                        format_func=lambda x: f"Seite {x + 1}",
                        key="add_split_select"
                    )
                    if st.button("➕ Trennung hinzufügen", use_container_width=True, type="primary"):
                        st.session_state.manual_splits.append(split_page)
                        st.session_state.manual_splits.sort()
                        st.rerun()
                else:
                    st.info("Alle Seiten sind bereits als Dokumentanfang markiert.")

                # Aktuelle Trennstellen anzeigen
                if st.session_state.manual_splits:
                    st.markdown("**Aktuelle Trennstellen:**")
                    split_cols = st.columns(4)
                    for i, split_page in enumerate(st.session_state.manual_splits):
                        with split_cols[i % 4]:
                            if st.button(f"❌ S.{split_page + 1}", key=f"remove_split_{split_page}", help="Trennung entfernen"):
                                st.session_state.manual_splits.remove(split_page)
                                st.rerun()

                st.divider()

                # Zusammenfassung der manuellen Dokumente
                st.markdown("##### 📋 Resultierende Dokumente")

                # Dokumente aus Trennstellen berechnen
                all_splits = sorted(set([0] + st.session_state.manual_splits + [num_pages]))
                manual_docs = []
                for i in range(len(all_splits) - 1):
                    start_page = all_splits[i]
                    end_page = all_splits[i + 1] - 1
                    doc_key = f"manual_doc_{i}"
                    manual_docs.append({
                        'id': doc_key,
                        'start': start_page,
                        'end': end_page,
                        'pages': f"{start_page + 1}" if start_page == end_page else f"{start_page + 1}-{end_page + 1}"
                    })

                st.success(f"📊 {len(manual_docs)} Dokumente werden erstellt")

                # Dokumentnamen bearbeiten
                for doc in manual_docs:
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        st.markdown(f"**Seiten {doc['pages']}**")
                    with c2:
                        default_name = st.session_state.manual_doc_names.get(doc['id'], f"Dokument (Seiten {doc['pages']})")
                        new_name = st.text_input(
                            "Name",
                            value=default_name,
                            key=f"name_{doc['id']}",
                            label_visibility="collapsed"
                        )
                        st.session_state.manual_doc_names[doc['id']] = new_name

                # Zurücksetzen-Button
                if st.session_state.manual_splits:
                    if st.button("🔄 Alle Trennungen zurücksetzen"):
                        st.session_state.manual_splits = []
                        st.session_state.manual_doc_names = {}
                        st.rerun()

            st.divider()

            # Import-Button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("✅ Akte importieren", type="primary", use_container_width=True):
                    # Neue Akte erstellen
                    new_case_id = f"imp-{len(st.session_state.imported_cases) + 1:03d}"

                    new_case = {
                        'id': new_case_id,
                        'nr': result['aktenzeichen'],
                        'creditor': result['creditor'],
                        'debtor': result['debtor'],
                        'creditor_address': result.get('creditor_address', ''),
                        'debtor_address': result.get('debtor_address', ''),
                        'subject': f'Import aus RA-Micro - {uploaded_pdf.name}',
                        'status': result['status'],
                        'dunning': result['dunning'],
                        'enforcement': result['enforcement'],
                        'principal': result['principal'],
                        'interest': 5.0,
                        'due_date': date.today() - timedelta(days=60),
                        'created': datetime.now(),
                        'imported': True,
                        'source_pdf': uploaded_pdf.name,
                        # Zusätzliche Felder für Kompatibilität
                        'contract_type': 'Importiert',
                        'contract_date': date.today() - timedelta(days=90),
                        'invoice_nr': f'IMP-{new_case_id}',
                        'invoice_date': date.today() - timedelta(days=60),
                        'leistung': 'Aus RA-Micro Import',
                        'mahnung_dates': [],
                    }

                    # Zur Liste hinzufügen
                    st.session_state.imported_cases.append(new_case)
                    DEMO_CASES.append(new_case)

                    # Dokumente bestimmen: manuell oder automatisch
                    if use_manual_split and st.session_state.manual_splits:
                        # Manuelle Dokumenttrennung verwenden
                        all_splits = sorted(set([0] + st.session_state.manual_splits + [num_pages]))
                        documents_to_import = []
                        doc_pdfs = {}

                        for i in range(len(all_splits) - 1):
                            start_page = all_splits[i]
                            end_page = all_splits[i + 1] - 1
                            doc_key = f"manual_doc_{i}"
                            doc_id = f"{new_case_id}-doc-{i+1}"
                            doc_name = st.session_state.manual_doc_names.get(doc_key, f"Dokument {i+1}")

                            doc = {
                                'id': doc_id,
                                'name': doc_name,
                                'type': 'Importiert (manuell)',
                                'date': date.today().strftime('%d.%m.%Y'),
                                'page': start_page + 1,
                                'end_page': end_page + 1,
                                'category': 'aussergerichtlich',
                                'size': f"{(end_page - start_page + 1) * 50} KB"
                            }
                            documents_to_import.append(doc)

                            # PDF für dieses Dokument extrahieren
                            doc_pdf = extract_pdf_pages(pdf_bytes, start_page, end_page)
                            if doc_pdf:
                                doc_pdfs[doc_id] = doc_pdf
                                st.session_state.document_pdfs[doc_id] = doc_pdf

                        st.session_state.imported_documents[new_case_id] = documents_to_import
                        DEMO_DOCUMENTS[new_case_id] = documents_to_import

                        # Session State für manuelle Trennung zurücksetzen
                        st.session_state.manual_splits = []
                        st.session_state.manual_doc_names = {}
                    else:
                        # Automatische Dokumenttrennung verwenden
                        for doc in result['documents']:
                            doc['size'] = f"{len(pdf_bytes) // max(1, len(result['documents'])) // 1024} KB"
                        st.session_state.imported_documents[new_case_id] = result['documents']
                        DEMO_DOCUMENTS[new_case_id] = result['documents']

                        # PDF in einzelne Dokumente aufteilen
                        doc_pdfs = split_pdf_by_toc(pdf_bytes, result['documents'])
                        for doc_id, doc_pdf in doc_pdfs.items():
                            st.session_state.document_pdfs[doc_id] = doc_pdf

                        # Falls Dokumente keine eigenen PDFs haben, Gesamt-PDF zuweisen
                        for doc in result['documents']:
                            if doc['id'] not in st.session_state.document_pdfs:
                                # Einzelne Seite extrahieren
                                page_num = doc.get('page', 1) - 1
                                single_page = extract_pdf_pages(pdf_bytes, page_num)
                                if single_page:
                                    st.session_state.document_pdfs[doc['id']] = single_page

                    # Gesamt-PDF für die Akte speichern
                    st.session_state.case_full_pdfs[new_case_id] = pdf_bytes

                    # Buchungen hinzufügen
                    st.session_state.imported_bookings[new_case_id] = result['bookings']
                    DEMO_BOOKINGS[new_case_id] = result['bookings']

                    num_docs = len(doc_pdfs) if doc_pdfs else len(result['documents'])
                    st.success(f"✅ Akte {result['aktenzeichen']} mit {num_docs} Dokumenten erfolgreich importiert!")
                    st.balloons()

                    # Zur Aktenübersicht wechseln
                    st.session_state.page = 'cases'
                    st.rerun()

        else:
            st.error(f"❌ Fehler beim Parsen: {result.get('error', 'Unbekannter Fehler')}")
            st.warning("Bitte stellen Sie sicher, dass die PDF ein gültiges RA-Micro Export-Format hat.")

    # Importierte Akten anzeigen
    if st.session_state.imported_cases:
        st.divider()
        st.markdown("### 📁 Bereits importierte Akten")
        for case in st.session_state.imported_cases:
            with st.expander(f"📁 {case['nr']} - {case['debtor']}"):
                st.write(f"**Gläubiger:** {case['creditor']}")
                st.write(f"**Quelle:** {case.get('source_pdf', 'Unbekannt')}")
                st.write(f"**Importiert:** {case['created'].strftime('%d.%m.%Y %H:%M')}")


# =============================================================================
# ZIP-IMPORT - Dokumente aus ZIP-Archiv importieren
# =============================================================================
def show_zip_import():
    """ZIP-Datei Import Seite - Dokumente aus ZIP-Archiv importieren"""
    st.markdown("## 📦 ZIP-Datei Import")
    st.info("""
    **Importieren Sie Dokumente aus einem ZIP-Archiv:**
    - Laden Sie eine ZIP-Datei mit mehreren Dokumenten hoch
    - Unterstützte Formate: PDF, DOCX, JPG, PNG, GIF, TIF, EML, MSG
    - Wählen Sie die Ziel-Akte aus
    - Alle oder einzelne Dateien importieren
    """)

    st.divider()

    # Ziel-Akte auswählen oder neue Akte anlegen
    all_cases = get_all_cases()

    # Option: Bestehende Akte oder neue Akte
    case_target = st.radio(
        "Ziel für Import",
        ["📁 Bestehende Akte", "➕ Neue Akte anlegen"],
        horizontal=True,
        key="zip_case_target"
    )

    target_case_id = None
    target_case = None

    if case_target == "📁 Bestehende Akte":
        if not all_cases:
            st.warning("⚠️ Keine Akten vorhanden. Bitte wählen Sie 'Neue Akte anlegen'.")
        else:
            case_options = {f"{c['nr']} - {c['debtor']}": c['id'] for c in all_cases}
            selected_case_label = st.selectbox(
                "📁 Ziel-Akte auswählen",
                options=list(case_options.keys()),
                help="Die Dokumente werden dieser Akte zugeordnet"
            )
            target_case_id = case_options[selected_case_label]
            target_case = next((c for c in all_cases if c['id'] == target_case_id), None)

    else:  # Neue Akte anlegen
        st.markdown("##### 📝 Neue Akte anlegen")

        col1, col2 = st.columns(2)
        with col1:
            new_case_nr = st.text_input(
                "Aktenzeichen *",
                placeholder="z.B. 1/25",
                key="zip_new_case_nr"
            )
            new_creditor = st.text_input(
                "Gläubiger (Mandant) *",
                placeholder="z.B. Mustermann GmbH",
                key="zip_new_creditor"
            )
            new_creditor_addr = st.text_area(
                "Adresse Gläubiger",
                placeholder="Straße, PLZ Ort",
                height=80,
                key="zip_new_creditor_addr"
            )

        with col2:
            new_debtor = st.text_input(
                "Schuldner (Gegner) *",
                placeholder="z.B. Max Müller",
                key="zip_new_debtor"
            )
            new_debtor_addr = st.text_area(
                "Adresse Schuldner",
                placeholder="Straße, PLZ Ort",
                height=80,
                key="zip_new_debtor_addr"
            )
            new_principal = st.number_input(
                "Hauptforderung (€)",
                min_value=0.0,
                value=0.0,
                step=100.0,
                key="zip_new_principal"
            )

        new_subject = st.text_input(
            "Betreff / Gegenstand",
            placeholder="z.B. Offene Rechnung 2024-001",
            key="zip_new_subject"
        )

        # Validierung
        if new_case_nr and new_creditor and new_debtor:
            st.success(f"✅ Neue Akte: **{new_case_nr}** - {new_creditor} ./. {new_debtor}")
            # Temporäres Case-Objekt für die Anzeige
            target_case = {
                'nr': new_case_nr,
                'creditor': new_creditor,
                'debtor': new_debtor,
                'id': None  # Wird beim Import erstellt
            }
        else:
            st.warning("⚠️ Bitte füllen Sie mindestens Aktenzeichen, Gläubiger und Schuldner aus.")

    st.divider()

    # ZIP-Datei Upload
    zip_file = st.file_uploader(
        "📦 ZIP-Datei hochladen",
        type=['zip'],
        help="ZIP-Archive mit PDFs, Bildern und Dokumenten (auch passwortgeschützt)"
    )

    if zip_file and (target_case_id or (case_target == "➕ Neue Akte anlegen" and target_case)):
        import zipfile

        st.success(f"✅ Datei geladen: {zip_file.name} ({zip_file.size / 1024:.1f} KB)")

        # Passwort-Eingabe (optional)
        zip_password = None
        zip_buffer = io.BytesIO(zip_file.getvalue())

        # Prüfen ob ZIP passwortgeschützt ist
        try:
            with zipfile.ZipFile(zip_buffer, 'r') as zf_test:
                # Versuche erste Datei zu lesen um zu prüfen ob verschlüsselt
                for file_info in zf_test.infolist():
                    if not file_info.is_dir():
                        try:
                            zf_test.read(file_info.filename)
                            break  # Keine Verschlüsselung
                        except RuntimeError as e:
                            if 'encrypted' in str(e).lower() or 'password' in str(e).lower():
                                st.warning("🔐 Diese ZIP-Datei ist passwortgeschützt.")
                                zip_password = st.text_input(
                                    "Passwort eingeben",
                                    type="password",
                                    key="zip_password",
                                    help="Geben Sie das Passwort für die ZIP-Datei ein"
                                )
                                if not zip_password:
                                    st.info("Bitte geben Sie das Passwort ein, um fortzufahren.")
                                    return
                            break
        except zipfile.BadZipFile:
            st.error("❌ Ungültige ZIP-Datei.")
            return

        try:
            # ZIP entpacken und Inhalt anzeigen
            zip_buffer.seek(0)
            with zipfile.ZipFile(zip_buffer, 'r') as zf:
                # Passwort setzen falls vorhanden
                pwd_bytes = zip_password.encode('utf-8') if zip_password else None

                # Dateien filtern (nur unterstützte Formate)
                supported_extensions = {'.pdf', '.docx', '.doc', '.jpg', '.jpeg', '.png', '.gif', '.tif', '.tiff', '.eml', '.msg'}
                all_files = []

                for file_info in zf.infolist():
                    if not file_info.is_dir():
                        file_ext = os.path.splitext(file_info.filename.lower())[1]
                        if file_ext in supported_extensions:
                            all_files.append({
                                'name': file_info.filename,
                                'size': file_info.file_size,
                                'ext': file_ext,
                                'compress_size': file_info.compress_size
                            })

                if all_files:
                    st.markdown(f"### 📋 Inhalt des Archivs ({len(all_files)} Dateien)")

                    # Session State für Auswahl
                    if 'zip_import_selection' not in st.session_state:
                        st.session_state.zip_import_selection = {f['name']: True for f in all_files}

                    # Alle auswählen / Keine auswählen
                    sel_col1, sel_col2, sel_col3 = st.columns(3)
                    with sel_col1:
                        if st.button("✅ Alle auswählen", key="zip_page_sel_all"):
                            st.session_state.zip_import_selection = {f['name']: True for f in all_files}
                            st.rerun()
                    with sel_col2:
                        if st.button("❌ Keine auswählen", key="zip_page_sel_none"):
                            st.session_state.zip_import_selection = {f['name']: False for f in all_files}
                            st.rerun()
                    with sel_col3:
                        selected_count = sum(1 for f in all_files if st.session_state.zip_import_selection.get(f['name'], True))
                        st.metric("Ausgewählt", f"{selected_count} / {len(all_files)}")

                    st.divider()

                    # Dateien nach Typ gruppieren
                    files_by_type = {}
                    for f in all_files:
                        ext = f['ext'].upper().replace('.', '')
                        if ext not in files_by_type:
                            files_by_type[ext] = []
                        files_by_type[ext].append(f)

                    # Dateien mit Checkboxen anzeigen
                    for file_type, files in sorted(files_by_type.items()):
                        type_icons = {
                            'PDF': '📕', 'DOCX': '📘', 'DOC': '📘',
                            'JPG': '🖼️', 'JPEG': '🖼️', 'PNG': '🖼️', 'GIF': '🖼️', 'TIF': '🖼️', 'TIFF': '🖼️',
                            'EML': '📧', 'MSG': '📧'
                        }
                        icon = type_icons.get(file_type, '📄')

                        with st.expander(f"{icon} **{file_type}** ({len(files)} Dateien)", expanded=True):
                            for f in files:
                                # Nur Dateiname ohne Pfad anzeigen
                                display_name = os.path.basename(f['name'])
                                size_kb = f['size'] / 1024

                                col1, col2 = st.columns([4, 1])
                                with col1:
                                    checked = st.checkbox(
                                        f"{display_name}",
                                        value=st.session_state.zip_import_selection.get(f['name'], True),
                                        key=f"zip_page_file_{f['name']}"
                                    )
                                    st.session_state.zip_import_selection[f['name']] = checked
                                with col2:
                                    st.caption(f"{size_kb:.1f} KB")

                    st.divider()

                    # Import-Optionen
                    st.markdown("### ⚙️ Import-Optionen")

                    col1, col2 = st.columns(2)
                    with col1:
                        zip_doc_type = st.selectbox(
                            "Dokumenttyp für alle Dateien",
                            ["Automatisch erkennen", "Rechnung", "Mahnung", "Vertrag", "Mahnbescheid",
                             "Vollstreckungsbescheid", "Schreiben", "Notiz", "Sonstiges"],
                            key="zip_page_doc_type"
                        )
                    with col2:
                        zip_doc_category = st.selectbox(
                            "Kategorie für alle Dateien",
                            [(k, v['name']) for k, v in DOCUMENT_CATEGORIES.items()],
                            format_func=lambda x: x[1],
                            key="zip_page_doc_cat"
                        )[0]

                    st.divider()

                    # Import-Button
                    selected_count = sum(1 for f in all_files if st.session_state.zip_import_selection.get(f['name'], False))

                    # Button-Text je nach Modus
                    if case_target == "➕ Neue Akte anlegen":
                        btn_text = f"📥 Neue Akte anlegen & {selected_count} Dateien importieren"
                    else:
                        btn_text = f"📥 {selected_count} Dateien in Akte '{target_case.get('nr', '')}' importieren"

                    if st.button(
                        btn_text,
                        type="primary",
                        use_container_width=True,
                        disabled=selected_count == 0
                    ):
                        imported_count = 0
                        errors = []
                        actual_case_id = target_case_id

                        # Falls neue Akte: Erst die Akte anlegen
                        if case_target == "➕ Neue Akte anlegen" and target_case.get('id') is None:
                            try:
                                # Neue Case-ID generieren
                                actual_case_id = f'zip-case-{datetime.now().strftime("%Y%m%d%H%M%S")}'

                                # Neue Akte erstellen
                                new_case = {
                                    'id': actual_case_id,
                                    'nr': st.session_state.get('zip_new_case_nr', ''),
                                    'creditor': st.session_state.get('zip_new_creditor', ''),
                                    'creditor_address': st.session_state.get('zip_new_creditor_addr', ''),
                                    'debtor': st.session_state.get('zip_new_debtor', ''),
                                    'debtor_address': st.session_state.get('zip_new_debtor_addr', ''),
                                    'subject': st.session_state.get('zip_new_subject', ''),
                                    'principal': st.session_state.get('zip_new_principal', 0),
                                    'interest': 5.0,
                                    'status': 'offen',
                                    'dunning': 'nicht_beantragt',
                                    'enforcement': 'nicht_begonnen',
                                    'due_date': date.today(),
                                    'created': datetime.now(),
                                    'source_zip': zip_file.name
                                }

                                # Zu imported_cases hinzufügen
                                if 'imported_cases' not in st.session_state:
                                    st.session_state.imported_cases = []
                                st.session_state.imported_cases.append(new_case)

                                st.info(f"📁 Akte **{new_case['nr']}** wird angelegt...")

                            except Exception as e:
                                st.error(f"❌ Fehler beim Anlegen der Akte: {str(e)}")
                                actual_case_id = None

                        if actual_case_id:
                            # ZIP erneut öffnen für den Import
                            zip_buffer.seek(0)
                            with zipfile.ZipFile(zip_buffer, 'r') as zf:
                                # Passwort für verschlüsselte ZIPs
                                pwd_bytes = zip_password.encode('utf-8') if zip_password else None

                                progress_bar = st.progress(0)
                                status_text = st.empty()

                                for idx, f in enumerate(all_files):
                                    if st.session_state.zip_import_selection.get(f['name'], False):
                                        try:
                                            status_text.text(f"Importiere: {os.path.basename(f['name'])}...")

                                            # Datei aus ZIP extrahieren (mit Passwort falls vorhanden)
                                            file_data = zf.read(f['name'], pwd=pwd_bytes)
                                            display_name = os.path.basename(f['name'])

                                            # Dokumenttyp bestimmen
                                            if zip_doc_type == "Automatisch erkennen":
                                                name_lower = display_name.lower()
                                                if 'rechnung' in name_lower or 'invoice' in name_lower:
                                                    doc_type = 'Rechnung'
                                                elif 'mahnung' in name_lower:
                                                    doc_type = 'Mahnung'
                                                elif 'vertrag' in name_lower or 'contract' in name_lower:
                                                    doc_type = 'Vertrag'
                                                elif 'mahnbescheid' in name_lower:
                                                    doc_type = 'Mahnbescheid'
                                                elif 'vollstreckung' in name_lower:
                                                    doc_type = 'Vollstreckungsbescheid'
                                                else:
                                                    doc_type = 'Sonstiges'
                                            else:
                                                doc_type = zip_doc_type

                                            # Neues Dokument erstellen
                                            doc_id = f'zip-{actual_case_id}-{datetime.now().strftime("%Y%m%d%H%M%S%f")}'
                                            new_doc = {
                                                'id': doc_id,
                                                'name': display_name,
                                                'date': date.today(),
                                                'type': doc_type,
                                                'size': f'{len(file_data) // 1024} KB',
                                                'category': zip_doc_category,
                                                'source': f'ZIP: {zip_file.name}'
                                            }

                                            # Zu DEMO_DOCUMENTS hinzufügen
                                            if actual_case_id not in DEMO_DOCUMENTS:
                                                DEMO_DOCUMENTS[actual_case_id] = []
                                            DEMO_DOCUMENTS[actual_case_id].append(new_doc)

                                            # PDF-Daten speichern falls PDF
                                            if f['ext'].lower() == '.pdf':
                                                st.session_state.document_pdfs[doc_id] = file_data

                                            imported_count += 1
                                        except Exception as e:
                                            errors.append(f"{f['name']}: {str(e)}")

                                    progress_bar.progress((idx + 1) / len(all_files))

                                status_text.empty()
                                progress_bar.empty()

                            if imported_count > 0:
                                st.success(f"✅ **{imported_count} Dateien** erfolgreich in Akte **{target_case.get('nr', '')}** importiert!")
                                st.balloons()

                            if errors:
                                with st.expander(f"⚠️ {len(errors)} Fehler beim Import"):
                                    for err in errors:
                                        st.error(f"❌ {err}")

                            # Auswahl zurücksetzen
                            if 'zip_import_selection' in st.session_state:
                                del st.session_state['zip_import_selection']

                else:
                    st.warning("⚠️ Keine unterstützten Dateien im Archiv gefunden.")
                    st.caption("**Unterstützte Formate:** PDF, DOCX, DOC, JPG, PNG, GIF, TIF, EML, MSG")

        except zipfile.BadZipFile:
            st.error("❌ Ungültige ZIP-Datei. Bitte laden Sie ein gültiges ZIP-Archiv hoch.")
        except Exception as e:
            st.error(f"❌ Fehler beim Verarbeiten: {str(e)}")


# =============================================================================
# EMAILVERKEHR - Intelligenter Ordner für alle Emails
# =============================================================================
def show_emailverkehr():
    """Intelligenter Ordner: Zeigt alle Emails aller Akten mit Suchfunktion"""
    st.markdown("## 📧 Emailverkehr")
    st.caption("Intelligenter Ordner - Alle Emails aller Akten")

    # Alle Emails sammeln
    all_emails = []
    all_cases = get_all_cases()
    case_map = {c['id']: c for c in all_cases}

    # Aus imported_emails
    for case_id, emails in st.session_state.get('imported_emails', {}).items():
        case_info = case_map.get(case_id, {'nr': case_id, 'debtor': 'Unbekannt'})
        for email_data in emails:
            all_emails.append({
                'case_id': case_id,
                'case_nr': case_info.get('nr', case_id),
                'case_debtor': case_info.get('debtor', 'Unbekannt'),
                **email_data
            })

    # Aus DEMO_DOCUMENTS (falls Emails dort gespeichert)
    for case_id, docs in DEMO_DOCUMENTS.items():
        case_info = case_map.get(case_id, {'nr': case_id, 'debtor': 'Unbekannt'})
        for doc in docs:
            if doc.get('category') == 'emailverkehr' and 'email_data' in doc:
                # Prüfen ob bereits in imported_emails
                if not any(e.get('id') == doc['id'] for e in all_emails):
                    all_emails.append({
                        'id': doc['id'],
                        'case_id': case_id,
                        'case_nr': case_info.get('nr', case_id),
                        'case_debtor': case_info.get('debtor', 'Unbekannt'),
                        'parsed': None,  # Keine ParsedEmail-Instanz
                        'doc': doc
                    })

    # Unzugeordnete Emails
    for email_data in st.session_state.get('unassigned_emails', []):
        all_emails.append({
            'case_id': None,
            'case_nr': '⚠️ Nicht zugeordnet',
            'case_debtor': '-',
            **email_data
        })

    # Statistik
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📧 Gesamt", len(all_emails))
    with col2:
        assigned = len([e for e in all_emails if e.get('case_id')])
        st.metric("✅ Zugeordnet", assigned)
    with col3:
        unassigned = len([e for e in all_emails if not e.get('case_id')])
        st.metric("⚠️ Offen", unassigned)
    with col4:
        cases_with_email = len(set(e['case_id'] for e in all_emails if e.get('case_id')))
        st.metric("📁 Akten", cases_with_email)

    st.divider()

    # Filter und Suche
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_term = st.text_input("🔍 Suche", placeholder="Betreff, Absender, Inhalt...", key="email_search")
    with col2:
        case_filter = st.selectbox(
            "Akte",
            ["Alle Akten"] + [f"{c['nr']} - {c['debtor']}" for c in all_cases],
            key="email_case_filter"
        )
    with col3:
        sort_by = st.selectbox("Sortierung", ["Datum (neu)", "Datum (alt)", "Absender", "Betreff"], key="email_sort")

    # Filter anwenden
    filtered_emails = all_emails

    if search_term:
        search_lower = search_term.lower()
        filtered_emails = [
            e for e in filtered_emails
            if (e.get('parsed') and (
                search_lower in e['parsed'].subject.lower() or
                search_lower in e['parsed'].sender.lower() or
                search_lower in e['parsed'].body_plain.lower()
            )) or (e.get('doc') and (
                search_lower in e['doc'].get('email_data', {}).get('subject', '').lower() or
                search_lower in e['doc'].get('email_data', {}).get('sender', '').lower()
            ))
        ]

    if case_filter != "Alle Akten":
        filter_case_nr = case_filter.split(" - ")[0]
        filtered_emails = [e for e in filtered_emails if e.get('case_nr') == filter_case_nr]

    # Sortieren
    def get_sort_key(email_item):
        parsed = email_item.get('parsed')
        doc = email_item.get('doc', {})
        if parsed:
            if sort_by.startswith("Datum"):
                return parsed.date or datetime.min
            elif sort_by == "Absender":
                return parsed.sender_email.lower()
            else:
                return parsed.subject.lower()
        else:
            email_data = doc.get('email_data', {})
            if sort_by.startswith("Datum"):
                return doc.get('date', date.min)
            elif sort_by == "Absender":
                return email_data.get('sender_email', '').lower()
            else:
                return email_data.get('subject', '').lower()

    reverse_sort = sort_by == "Datum (neu)"
    filtered_emails.sort(key=get_sort_key, reverse=reverse_sort)

    st.divider()

    # Email-Liste anzeigen
    if not filtered_emails:
        st.info("Keine Emails gefunden. Importieren Sie Emails über die Aktenansicht oder fügen Sie neue hinzu.")

        # Option zum direkten Email-Import
        st.markdown("### 📥 Emails importieren (automatische Zuordnung)")
        show_email_import_with_matching()
    else:
        st.markdown(f"### 📋 {len(filtered_emails)} Email(s)")

        for i, email_item in enumerate(filtered_emails):
            parsed = email_item.get('parsed')
            doc = email_item.get('doc', {})

            if parsed:
                subject = parsed.subject
                sender = f"{parsed.sender_name} <{parsed.sender_email}>"
                email_date = parsed.get_display_date()
                preview = parsed.get_body_preview(100)
                attachments = len(parsed.attachments)
            else:
                email_data = doc.get('email_data', {})
                subject = email_data.get('subject', doc.get('name', 'Unbekannt'))
                sender = email_data.get('sender', 'Unbekannt')
                email_date = fmt_date(doc.get('date', date.today()))
                preview = email_data.get('body_preview', '')[:100]
                attachments = email_data.get('attachments', 0)

            with st.expander(f"📧 **{subject[:50]}{'...' if len(subject) > 50 else ''}** | {email_item['case_nr']}", expanded=False):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"**Von:** {sender}")
                    st.write(f"**Datum:** {email_date}")
                    st.write(f"**Akte:** {email_item['case_nr']} ({email_item['case_debtor']})")
                    if preview:
                        st.caption(preview)

                with col2:
                    if attachments > 0:
                        st.write(f"📎 {attachments} Anhang/Anhänge")

                    # Aktionen
                    if email_item.get('case_id'):
                        if st.button("📁 Zur Akte", key=f"goto_case_{i}"):
                            st.session_state.selected_case = email_item['case_id']
                            st.session_state.page = 'case_detail'
                            st.rerun()
                    else:
                        # Zuordnung ermöglichen
                        st.warning("Nicht zugeordnet")
                        target_case = st.selectbox(
                            "Zuordnen zu:",
                            ["Auswählen..."] + [f"{c['id']}|{c['nr']}" for c in all_cases],
                            format_func=lambda x: x.split("|")[1] if "|" in x else x,
                            key=f"assign_{i}"
                        )
                        if target_case != "Auswählen..." and st.button("✅ Zuordnen", key=f"do_assign_{i}"):
                            target_id = target_case.split("|")[0]
                            # Email zu Akte zuordnen
                            if target_id not in st.session_state.imported_emails:
                                st.session_state.imported_emails[target_id] = []
                            st.session_state.imported_emails[target_id].append(email_item)

                            # Aus unassigned entfernen
                            if email_item in st.session_state.unassigned_emails:
                                st.session_state.unassigned_emails.remove(email_item)

                            st.success(f"Email zugeordnet zu {target_case.split('|')[1]}")
                            st.rerun()

        st.divider()

        # Neue Emails importieren
        st.markdown("### 📥 Weitere Emails importieren")
        show_email_import_with_matching()


def show_email_import_with_matching():
    """Email-Import mit automatischer Akten-Zuordnung"""
    if not EMAIL_PARSER_AVAILABLE:
        st.warning("📧 Email-Parser nicht verfügbar.")
        return

    email_files = st.file_uploader(
        "Email-Dateien (.eml, .msg) per Drag & Drop",
        type=['eml', 'msg'],
        accept_multiple_files=True,
        key="global_email_upload",
        help="Emails werden automatisch passenden Akten zugeordnet"
    )

    if email_files:
        all_cases = get_all_cases()
        results = []

        st.markdown("#### Erkannte Emails und Zuordnung:")

        for email_file in email_files:
            try:
                parsed = parse_email_file(email_file.getvalue(), email_file.name)

                # Automatische Zuordnung versuchen
                matched_case = parsed.match_to_case(all_cases)

                results.append({
                    'file': email_file,
                    'parsed': parsed,
                    'matched_case': matched_case,
                    'manual_case': None
                })

                with st.container():
                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        st.write(f"📧 **{parsed.get_short_subject(35)}**")
                        st.caption(f"Von: {parsed.sender_email}")

                    with col2:
                        if matched_case:
                            st.success(f"✅ → {matched_case['nr']}")
                        else:
                            # Manuelle Auswahl
                            case_options = ["Nicht zuordnen"] + [f"{c['id']}|{c['nr']} - {c['debtor']}" for c in all_cases]
                            selected = st.selectbox(
                                "Zuordnen:",
                                case_options,
                                key=f"match_{email_file.name}",
                                format_func=lambda x: x.split("|")[1] if "|" in x else x
                            )
                            if selected != "Nicht zuordnen":
                                results[-1]['manual_case'] = selected.split("|")[0]

                    with col3:
                        if parsed.attachments:
                            st.write(f"📎 {len(parsed.attachments)}")

            except Exception as e:
                st.error(f"Fehler: {email_file.name} - {str(e)}")

        if results:
            if st.button("📥 Alle Emails importieren", type="primary", use_container_width=True):
                imported = 0
                unassigned = 0

                for result in results:
                    parsed = result['parsed']
                    case_id = None

                    if result['matched_case']:
                        case_id = result['matched_case']['id']
                    elif result['manual_case']:
                        case_id = result['manual_case']

                    email_id = f'email-{datetime.now().strftime("%Y%m%d%H%M%S%f")}'
                    email_entry = {
                        'id': email_id,
                        'parsed': parsed,
                        'raw': result['file'].getvalue()
                    }

                    if case_id:
                        # Zu Akte hinzufügen
                        if case_id not in st.session_state.imported_emails:
                            st.session_state.imported_emails[case_id] = []
                        st.session_state.imported_emails[case_id].append(email_entry)

                        # Auch als Dokument speichern
                        new_doc = {
                            'id': email_id,
                            'name': f"{parsed.get_short_subject(30)}.eml",
                            'date': parsed.date.date() if parsed.date else date.today(),
                            'type': 'Email',
                            'size': f'{len(result["file"].getvalue()) // 1024} KB',
                            'category': 'emailverkehr',
                            'email_data': {
                                'subject': parsed.subject,
                                'sender': parsed.sender,
                                'sender_email': parsed.sender_email,
                                'to': parsed.to,
                                'body_preview': parsed.get_body_preview(500),
                                'attachments': len(parsed.attachments)
                            }
                        }
                        if case_id not in DEMO_DOCUMENTS:
                            DEMO_DOCUMENTS[case_id] = []
                        DEMO_DOCUMENTS[case_id].append(new_doc)

                        imported += 1
                    else:
                        # Unzugeordnet speichern
                        st.session_state.unassigned_emails.append(email_entry)
                        unassigned += 1

                msg = f"✅ {imported} Email(s) importiert"
                if unassigned > 0:
                    msg += f", {unassigned} nicht zugeordnet"
                st.success(msg)
                st.rerun()


# =============================================================================
# LOGIN
# =============================================================================
def show_login():
    st.markdown("# ⚖️ InkassoKom")
    st.markdown("### Inkasso-Kommunikationsplattform")
    st.caption(f"Version: {APP_VERSION}")
    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("#### 🔓 Demo-Zugang")
        st.info("Wählen Sie eine Rolle:")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("👨‍⚖️ Rechtsanwalt", use_container_width=True, type="primary"):
                st.session_state.authenticated = True
                st.session_state.user = {'id': 'lawyer-1', 'name': 'Thomas Müller', 'role': 'rechtsanwalt'}
                st.rerun()
        with c2:
            if st.button("💼 Gläubigerin", use_container_width=True, type="primary"):
                st.session_state.authenticated = True
                st.session_state.user = {'id': 'creditor-1', 'name': 'Erika Mustermann', 'role': 'glaeubigerin'}
                st.rerun()
        with c3:
            if st.button("👤 Schuldner", use_container_width=True, type="primary"):
                st.session_state.authenticated = True
                st.session_state.user = {'id': 'debtor-1', 'name': 'Max Schmidt', 'role': 'schuldner'}
                st.rerun()

# =============================================================================
# RECHTSANWALT DASHBOARD
# =============================================================================
def lawyer_dashboard():
    # Ungelesene Nachrichten zählen
    unread = get_unread_count('rechtsanwalt')
    notif_count = get_notification_count('rechtsanwalt')

    with st.sidebar:
        st.markdown(f"### ⚖️ InkassoKom")
        st.caption(f"👨‍⚖️ {st.session_state.user['name']}")

        # Benachrichtigungsanzeige
        if unread > 0 or notif_count > 0:
            st.warning(f"📬 {unread} neue Nachrichten | 🔔 {notif_count} Benachrichtigungen")

        st.divider()

        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state.page = 'dashboard'
            st.session_state.selected_case = None
            st.rerun()
        if st.button("📁 Alle Akten", use_container_width=True):
            st.session_state.page = 'cases'
            st.rerun()
        if st.button("➕ Neue Akte", use_container_width=True):
            st.session_state.page = 'new_case'
            st.rerun()

        # Datenimport-Bereich
        with st.expander("📥 **Datenimport**", expanded=False):
            if st.button("📂 RA-Micro Akte", use_container_width=True, key="menu_ra_micro"):
                st.session_state.page = 'ra_micro_import'
                st.rerun()
            if st.button("📦 ZIP-Datei Import", use_container_width=True, key="menu_zip_import"):
                st.session_state.page = 'zip_import'
                st.rerun()

        # Posteingang mit Unread-Badge
        inbox_label = f"📬 Posteingang ({unread})" if unread > 0 else "📬 Posteingang"
        if st.button(inbox_label, use_container_width=True):
            st.session_state.page = 'messages'
            st.rerun()

        # Emailverkehr (intelligenter Ordner)
        email_count = sum(len(emails) for emails in st.session_state.get('imported_emails', {}).values())
        email_label = f"📧 Emailverkehr ({email_count})" if email_count > 0 else "📧 Emailverkehr"
        if st.button(email_label, use_container_width=True):
            st.session_state.page = 'emailverkehr'
            st.rerun()

        if st.button("✉️ Nachricht senden", use_container_width=True):
            st.session_state.page = 'compose'
            st.rerun()

        st.divider()
        if st.button("⚖️ Mahnverfahren", use_container_width=True):
            st.session_state.page = 'dunning'
            st.rerun()
        if st.button("📜 Klage-Entwurf", use_container_width=True):
            st.session_state.page = 'klage'
            st.rerun()
        if st.button("🔨 Vollstreckung", use_container_width=True):
            st.session_state.page = 'enforcement'
            st.rerun()
        if st.button("⏰ Verjährung", use_container_width=True):
            st.session_state.page = 'limitation'
            st.rerun()

        # Wiedervorlagen mit Badge
        wv_count = get_wv_count()
        wv_label = f"📅 Wiedervorlagen ({wv_count})" if wv_count > 0 else "📅 Wiedervorlagen"
        if st.button(wv_label, use_container_width=True, type="primary" if wv_count > 0 else "secondary"):
            st.session_state.page = 'wiedervorlagen'
            st.rerun()

        st.divider()
        if st.button("📋 Vorlagen", use_container_width=True):
            st.session_state.page = 'templates'
            st.rerun()

        # Einstellungen
        if st.button("⚙️ Einstellungen", use_container_width=True):
            st.session_state.page = 'settings'
            st.rerun()
        if st.button("🚪 Abmelden", use_container_width=True):
            logout()
            st.rerun()

        # Datenbank-Status anzeigen
        if DB_AVAILABLE:
            show_db_status_widget()

    page = st.session_state.page
    if page == 'cases': show_cases_list()
    elif page == 'new_case': show_new_case()
    elif page == 'case_detail': show_case_detail()
    elif page == 'inbox': show_inbox()
    elif page == 'messages': show_lawyer_messages()
    elif page == 'compose': show_compose_message()
    elif page == 'settings': show_settings()
    elif page == 'ra_micro_import': show_ra_micro_import()
    elif page == 'zip_import': show_zip_import()
    elif page == 'emailverkehr': show_emailverkehr()
    elif page == 'dunning': show_dunning()
    elif page == 'klage': show_klage_entwurf()
    elif page == 'templates': show_vorlagen()
    elif page == 'enforcement': show_enforcement()
    elif page == 'limitation': show_limitation()
    elif page == 'wiedervorlagen': show_wiedervorlage_dashboard()
    else: show_lawyer_overview()

def show_lawyer_overview():
    st.markdown("## 📊 Kanzlei-Dashboard")

    # API-Key Status anzeigen
    if st.session_state.openai_api_key:
        if st.session_state.get('openai_api_key_from_secrets', False):
            st.success("🤖 **KI aktiviert** - OpenAI API-Key wurde aus Streamlit Secrets geladen")
        else:
            st.success("🤖 **KI aktiviert** - OpenAI API-Key ist konfiguriert")
    else:
        st.info("💡 **Tipp:** Hinterlegen Sie einen OpenAI API-Key in den Einstellungen oder als Streamlit Secret (`OPENAI_API_KEY`) für KI-Funktionen")

    st.divider()

    all_cases = get_all_cases()
    total = len(all_cases)
    offen = sum(1 for c in all_cases if c['status'] == 'offen')
    mahn = sum(1 for c in all_cases if c['status'] == 'mahnverfahren')
    vollstr = sum(1 for c in all_cases if c['status'] == 'vollstreckung')

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📁 Gesamt", total)
    c2.metric("🟡 Offen", offen)
    c3.metric("🟠 Mahnverfahren", mahn)
    c4.metric("🔴 Vollstreckung", vollstr)

    total_claims = sum(c['principal'] for c in all_cases)
    st.metric("💰 Gesamtforderungen", fmt_curr(total_claims))

    st.divider()

    # Sortierung und Filter
    col1, col2 = st.columns([2, 2])
    with col1:
        sort_by = st.selectbox(
            "Sortieren nach",
            ["Status", "Zahlungsstatus (offen→bezahlt)", "Aktenzeichen", "Forderungshöhe", "Schuldner"],
            key="dashboard_sort"
        )
    with col2:
        sort_order = st.radio("Reihenfolge", ["Aufsteigend", "Absteigend"], horizontal=True, key="dashboard_order")

    # Sortierlogik
    status_order = {'offen': 1, 'mahnverfahren': 2, 'vollstreckung': 3, 'abgeschlossen': 4}
    reverse = sort_order == "Absteigend"

    sorted_cases = get_all_cases()
    if sort_by == "Status":
        sorted_cases.sort(key=lambda x: status_order.get(x['status'], 99), reverse=reverse)
    elif sort_by == "Zahlungsstatus (offen→bezahlt)":
        # Sortieren nach offenem Betrag (höchster offen zuerst, bezahlt zuletzt)
        def get_payment_status(case):
            s, h, o = get_balance(case['id'])
            if s == 0:
                return 0  # Keine Forderung
            payment_ratio = h / s  # 0 = nichts bezahlt, 1 = vollständig bezahlt
            return payment_ratio
        sorted_cases.sort(key=get_payment_status, reverse=reverse)
    elif sort_by == "Aktenzeichen":
        sorted_cases.sort(key=lambda x: x['nr'], reverse=reverse)
    elif sort_by == "Forderungshöhe":
        sorted_cases.sort(key=lambda x: x['principal'], reverse=reverse)
    elif sort_by == "Schuldner":
        sorted_cases.sort(key=lambda x: x['debtor'], reverse=reverse)

    st.markdown("### 📁 Aktuelle Akten")

    for case in sorted_cases:
        s, h, o = get_balance(case['id'])
        status_icons = {'offen': '🟡', 'mahnverfahren': '🟠', 'vollstreckung': '🔴', 'abgeschlossen': '🟢'}

        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        with col1:
            st.markdown(f"**{case['nr']}** - {case['debtor']}")
            st.caption(case['subject'])
        with col2:
            st.write(f"{status_icons.get(case['status'], '⚪')} {case['status'].title()}")
        with col3:
            st.write(f"**{fmt_curr(o)}** offen")
        with col4:
            if st.button("📂", key=f"o_{case['id']}"):
                st.session_state.selected_case = case['id']
                st.session_state.page = 'case_detail'
                st.rerun()
        st.divider()

    st.markdown("### ⚠️ Warnungen")
    st.warning("**Verjährung:** Akte 1/25 - Prüfung empfohlen")
    st.info("**Widerspruchsfrist:** Akte 2/25 - läuft in 7 Tagen ab")


# =============================================================================
# WIEDERVORLAGE FUNKTIONEN
# =============================================================================

def get_faellige_wiedervorlagen() -> list:
    """Gibt alle heute oder überfälligen Wiedervorlagen zurück"""
    faellige = []
    heute = date.today()

    for case_id, wvs in st.session_state.get('wiedervorlagen', {}).items():
        for wv in wvs:
            wv_datum = wv.get('datum')
            if isinstance(wv_datum, str):
                try:
                    wv_datum = datetime.strptime(wv_datum, '%Y-%m-%d').date()
                except:
                    continue

            if wv_datum and wv_datum <= heute and not wv.get('erledigt', False):
                # Akte finden
                case = None
                for c in DEMO_CASES + st.session_state.get('imported_cases', []):
                    if c['id'] == case_id:
                        case = c
                        break

                faellige.append({
                    **wv,
                    'case_id': case_id,
                    'case': case,
                    'ueberfaellig': (heute - wv_datum).days
                })

    return sorted(faellige, key=lambda x: x.get('ueberfaellig', 0), reverse=True)


def get_anstehende_wiedervorlagen(tage_voraus: int = 7) -> list:
    """Gibt Wiedervorlagen der nächsten X Tage zurück"""
    anstehende = []
    heute = date.today()
    grenze = heute + timedelta(days=tage_voraus)

    for case_id, wvs in st.session_state.get('wiedervorlagen', {}).items():
        for wv in wvs:
            wv_datum = wv.get('datum')
            if isinstance(wv_datum, str):
                try:
                    wv_datum = datetime.strptime(wv_datum, '%Y-%m-%d').date()
                except:
                    continue

            if wv_datum and heute < wv_datum <= grenze and not wv.get('erledigt', False):
                case = None
                for c in DEMO_CASES + st.session_state.get('imported_cases', []):
                    if c['id'] == case_id:
                        case = c
                        break

                anstehende.append({
                    **wv,
                    'case_id': case_id,
                    'case': case,
                    'tage_bis': (wv_datum - heute).days
                })

    return sorted(anstehende, key=lambda x: x.get('tage_bis', 999))


def get_wv_count() -> int:
    """Zählt fällige Wiedervorlagen für Badge"""
    return len(get_faellige_wiedervorlagen())


def show_wiedervorlage_dashboard():
    """Zeigt das Wiedervorlage-Dashboard"""
    st.markdown("## 📅 Wiedervorlagen")

    faellige = get_faellige_wiedervorlagen()
    anstehende = get_anstehende_wiedervorlagen(14)

    # Übersichtskacheln
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔴 Überfällig", len([w for w in faellige if w.get('ueberfaellig', 0) > 0]))
    with col2:
        st.metric("🟡 Heute fällig", len([w for w in faellige if w.get('ueberfaellig', 0) == 0]))
    with col3:
        st.metric("🔵 Diese Woche", len([w for w in anstehende if w.get('tage_bis', 999) <= 7]))
    with col4:
        total = sum(len(wvs) for wvs in st.session_state.get('wiedervorlagen', {}).values())
        erledigt = sum(
            1 for wvs in st.session_state.get('wiedervorlagen', {}).values()
            for wv in wvs if wv.get('erledigt', False)
        )
        st.metric("✅ Erledigt", f"{erledigt}/{total}")

    st.divider()

    # Fällige WVs
    if faellige:
        st.markdown("### 🔴 Fällige Wiedervorlagen")

        for i, wv in enumerate(faellige):
            case = wv.get('case', {})
            with st.expander(f"⏰ {wv.get('titel', 'WV')} - {case.get('nr', 'Unbekannt')} ({case.get('debtor', 'Unbekannt')})", expanded=True):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"**Datum:** {wv.get('datum')}")
                    st.write(f"**Grund:** {wv.get('grund', 'Nicht angegeben')}")
                    st.write(f"**Bedingung:** {wv.get('bedingung', 'Nicht angegeben')}")
                    if wv.get('beschreibung'):
                        st.caption(wv.get('beschreibung'))

                    if wv.get('ueberfaellig', 0) > 0:
                        st.error(f"⚠️ {wv['ueberfaellig']} Tage überfällig!")

                with col2:
                    # WV prüfen Button
                    if st.button("🔍 Prüfen", key=f"wv_check_{i}", type="primary"):
                        st.session_state.active_wv_check = {
                            'wv': wv,
                            'index': i,
                            'case_id': wv.get('case_id')
                        }
                        st.rerun()

                    if st.button("✅ Erledigt", key=f"wv_done_{i}"):
                        # WV als erledigt markieren
                        case_id = wv.get('case_id')
                        if case_id in st.session_state.wiedervorlagen:
                            for wv_entry in st.session_state.wiedervorlagen[case_id]:
                                if wv_entry.get('datum') == wv.get('datum') and wv_entry.get('titel') == wv.get('titel'):
                                    wv_entry['erledigt'] = True
                                    wv_entry['erledigt_am'] = datetime.now().isoformat()
                                    break
                        st.success("✅ Als erledigt markiert")
                        st.rerun()
    else:
        st.success("✅ Keine fälligen Wiedervorlagen")

    # Anstehende WVs
    if anstehende:
        st.markdown("### 📅 Anstehende Wiedervorlagen")

        for i, wv in enumerate(anstehende):
            case = wv.get('case', {})
            tage = wv.get('tage_bis', 0)
            icon = "🟡" if tage <= 3 else "🔵"

            with st.expander(f"{icon} {wv.get('titel', 'WV')} in {tage} Tagen - {case.get('nr', 'Unbekannt')}"):
                st.write(f"**Datum:** {wv.get('datum')}")
                st.write(f"**Akte:** {case.get('creditor', '')} ./. {case.get('debtor', '')}")
                st.write(f"**Grund:** {wv.get('grund', 'Nicht angegeben')}")

    # WV Prüfungs-Dialog
    if 'active_wv_check' in st.session_state and st.session_state.active_wv_check:
        show_wv_pruefung_dialog()


def show_wv_pruefung_dialog():
    """Zeigt den WV-Prüfungsdialog mit Bedingungsprüfung und Briefgenerierung"""
    wv_data = st.session_state.active_wv_check
    wv = wv_data.get('wv', {})
    case_id = wv_data.get('case_id')

    # Akte laden
    case = wv.get('case', {})

    st.divider()
    st.markdown("### 🔍 Wiedervorlage-Prüfung")
    st.info(f"**{wv.get('titel')}** für Akte {case.get('nr', 'Unbekannt')}")

    # Bedingungsprüfung
    grund = wv.get('grund', 'sonstiges')
    bedingung = wv.get('bedingung', 'sonstiges')

    st.markdown("#### Bedingungsprüfung")

    # Aktendaten für Prüfung sammeln
    saldo, haben, soll = get_balance(case_id) if case_id else (0, 0, 0)

    case_data = {
        'offener_betrag': saldo,
        'ursprungs_betrag': case.get('principal', saldo),
        'schuldner_name': case.get('debtor', 'Unbekannt'),
        'schuldner_anrede': 'Herr/Frau',
        'aktenzeichen': case.get('nr', ''),
        'signatur': f"Mit freundlichen Grüßen\n{st.session_state.get('kanzlei_daten', {}).get('name', 'Kanzlei')}"
    }

    # Ergebnisauswahl
    ergebnis_optionen = {
        "✅ Bedingung erfüllt": "erfuellt",
        "❌ Bedingung nicht erfüllt": "nicht_erfuellt",
        "⚠️ Teilweise erfüllt": "teilweise",
        "❓ Nicht prüfbar": "nicht_pruefbar"
    }

    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Grund:** {grund}")
        st.write(f"**Zu prüfen:** {bedingung}")
        st.write(f"**Offener Betrag:** {fmt_curr(saldo)}")

        ergebnis_label = st.radio(
            "Ergebnis der Prüfung:",
            list(ergebnis_optionen.keys()),
            key="wv_ergebnis_auswahl"
        )
        ergebnis = ergebnis_optionen[ergebnis_label]

    with col2:
        st.write("**Zusätzliche Notizen:**")
        notizen = st.text_area("Notizen zur Prüfung", key="wv_pruefung_notizen", height=100)

    # Brief generieren
    if WV_SERVICE_AVAILABLE:
        st.markdown("#### 📝 Vorgeschlagene Aktion")

        try:
            from src.services.wiedervorlage_service import WVGrund, WVErgebnis

            wv_grund = WVGrund(grund) if grund in [g.value for g in WVGrund] else WVGrund.SONSTIGES
            wv_ergebnis = WVErgebnis(ergebnis) if ergebnis in [e.value for e in WVErgebnis] else WVErgebnis.NICHT_PRUEFBAR

            # Aktionen vorschlagen
            aktionen = {
                ('zahlungsfrist', 'nicht_erfuellt'): "Letzte Mahnung versenden oder gerichtliches Mahnverfahren einleiten",
                ('zahlungsfrist', 'teilweise'): "Restzahlung anmahnen oder Ratenzahlung vereinbaren",
                ('zahlungsfrist', 'erfuellt'): "Akte als erledigt markieren",
                ('vergleichsfrist', 'nicht_erfuellt'): "Volle Forderung geltend machen",
                ('vergleichsfrist', 'erfuellt'): "Vergleichszahlung überwachen",
                ('pruefung', 'nicht_erfuellt'): "Weitere Maßnahmen prüfen oder Akte schließen",
            }

            aktion = aktionen.get((grund, ergebnis), "Manuelle Prüfung und Entscheidung erforderlich")
            st.info(f"**Empfehlung:** {aktion}")

            # Briefentwurf generieren
            wv_service = get_wv_service()
            brief = wv_service.generiere_brief(wv_grund, wv_ergebnis, case_data)

            if brief:
                with st.expander("📄 Briefentwurf anzeigen"):
                    st.text_area("Briefentwurf", brief, height=300, key="wv_brief_entwurf")

                    if st.button("📧 Als Nachricht verwenden"):
                        st.session_state.compose_prefill = {
                            'subject': f"WV: {wv.get('titel')} - {case.get('nr', '')}",
                            'content': brief,
                            'case_id': case_id
                        }
                        st.session_state.page = 'compose'
                        st.session_state.active_wv_check = None
                        st.rerun()

        except Exception as e:
            st.warning(f"Briefgenerierung nicht verfügbar: {e}")

    # Aktionen
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✅ Erledigt markieren", type="primary"):
            if case_id in st.session_state.wiedervorlagen:
                for wv_entry in st.session_state.wiedervorlagen[case_id]:
                    if wv_entry.get('datum') == wv.get('datum') and wv_entry.get('titel') == wv.get('titel'):
                        wv_entry['erledigt'] = True
                        wv_entry['erledigt_am'] = datetime.now().isoformat()
                        wv_entry['ergebnis'] = ergebnis
                        wv_entry['notizen'] = notizen
                        break
            st.session_state.active_wv_check = None
            st.success("✅ Wiedervorlage erledigt")
            st.rerun()

    with col2:
        if st.button("📅 Neu terminieren"):
            st.session_state.wv_neu_terminieren = True

    with col3:
        if st.button("❌ Abbrechen"):
            st.session_state.active_wv_check = None
            st.rerun()

    # Neu terminieren Dialog
    if st.session_state.get('wv_neu_terminieren'):
        st.markdown("#### 📅 Neuer Termin")
        neues_datum = st.date_input("Neues Datum", value=date.today() + timedelta(days=14))
        neuer_titel = st.text_input("Titel", value=wv.get('titel', 'Wiedervorlage'))

        if st.button("💾 Neu anlegen"):
            neue_wv = {
                'titel': neuer_titel,
                'datum': neues_datum.isoformat(),
                'grund': grund,
                'bedingung': bedingung,
                'beschreibung': f"Verlängert von {wv.get('datum')}. {notizen}",
                'erstellt': datetime.now().isoformat()
            }

            if case_id not in st.session_state.wiedervorlagen:
                st.session_state.wiedervorlagen[case_id] = []
            st.session_state.wiedervorlagen[case_id].append(neue_wv)

            # Alte WV als erledigt markieren
            for wv_entry in st.session_state.wiedervorlagen[case_id]:
                if wv_entry.get('datum') == wv.get('datum') and wv_entry.get('titel') == wv.get('titel'):
                    wv_entry['erledigt'] = True
                    wv_entry['ergebnis'] = 'verlängert'
                    break

            st.session_state.wv_neu_terminieren = False
            st.session_state.active_wv_check = None
            st.success(f"✅ Neue Wiedervorlage für {neues_datum.strftime('%d.%m.%Y')} angelegt")
            st.rerun()


def show_cases_list():
    st.markdown("## 📁 Aktenübersicht")

    # Anzahl importierter Akten anzeigen
    imported_count = len(st.session_state.get('imported_cases', []))
    if imported_count > 0:
        st.success(f"📥 {imported_count} importierte Akte(n) vorhanden")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        filter_status = st.selectbox("Status", ["Alle", "Offen", "Mahnverfahren", "Vollstreckung", "Importiert"])
    with col2:
        search = st.text_input("🔍 Suche", placeholder="Name, Aktenzeichen...")
    with col3:
        sort_by = st.selectbox("Sortieren", ["Aktenzeichen", "Schuldner", "Status"])

    st.divider()

    # Alle Akten abrufen (inkl. importierter)
    cases = get_all_cases()

    # Filter anwenden
    if filter_status == "Importiert":
        cases = [c for c in cases if c.get('imported', False)]
    elif filter_status != "Alle":
        cases = [c for c in cases if c['status'] == filter_status.lower()]

    if search:
        cases = [c for c in cases if search.lower() in c['nr'].lower() or search.lower() in c['debtor'].lower() or search.lower() in c['creditor'].lower()]

    # Sortieren
    if sort_by == "Schuldner":
        cases.sort(key=lambda x: x['debtor'])
    elif sort_by == "Status":
        status_order = {'offen': 1, 'mahnverfahren': 2, 'vollstreckung': 3, 'abgeschlossen': 4}
        cases.sort(key=lambda x: status_order.get(x['status'], 99))
    else:
        cases.sort(key=lambda x: x['nr'])

    if not cases:
        st.info("Keine Akten gefunden")
        return

    for case in cases:
        s, h, o = get_balance(case['id'])
        is_imported = case.get('imported', False)

        col1, col2, col3, col4, col5 = st.columns([1.5, 2.5, 2, 2, 1])
        with col1:
            import_badge = "📥 " if is_imported else ""
            st.write(f"**{import_badge}{case['nr']}**")
            if is_imported:
                st.caption(f"Quelle: {case.get('source_pdf', 'Import')[:20]}...")
        with col2:
            st.write(case['debtor'])
            st.caption(case['creditor'])
        with col3:
            status_icons = {'offen': '🟡', 'mahnverfahren': '🟠', 'vollstreckung': '🔴', 'abgeschlossen': '🟢'}
            st.write(f"{status_icons.get(case['status'], '⚪')} {case['status'].title()}")
        with col4:
            st.write(fmt_curr(o))
            if h > 0:
                st.caption(f"Gezahlt: {fmt_curr(h)}")
        with col5:
            if st.button("📂", key=f"l_{case['id']}"):
                st.session_state.selected_case = case['id']
                st.session_state.page = 'case_detail'
                st.rerun()
        st.divider()

def show_new_case():
    st.markdown("## ➕ Neue Akte anlegen")

    with st.form("new_case"):
        st.markdown("### Gläubiger")
        c1, c2 = st.columns(2)
        with c1:
            cred_name = st.text_input("Name/Firma *")
            cred_email = st.text_input("E-Mail")
        with c2:
            cred_street = st.text_input("Straße")
            cred_city = st.text_input("PLZ / Ort")

        st.markdown("### Schuldner")
        c1, c2 = st.columns(2)
        with c1:
            debt_name = st.text_input("Name *", key="dn")
            debt_email = st.text_input("E-Mail", key="de")
        with c2:
            debt_street = st.text_input("Straße", key="ds")
            debt_city = st.text_input("PLZ / Ort", key="dc")

        st.markdown("### Forderung")
        c1, c2, c3 = st.columns(3)
        with c1:
            principal = st.number_input("Hauptforderung (€) *", min_value=0.0, step=100.0)
            interest = st.number_input("Zinssatz (%)", value=5.0)
        with c2:
            due = st.date_input("Fälligkeitsdatum *")
            invoice = st.text_input("Rechnungsnummer")
        with c3:
            claim_type = st.selectbox("Art", ["Kaufpreis", "Miete", "Darlehen", "Sonstiges"])

        subject = st.text_area("Betreff *")

        if st.form_submit_button("💾 Akte anlegen", type="primary", use_container_width=True):
            if cred_name and debt_name and principal > 0 and subject:
                st.success("✅ Akte erfolgreich angelegt!")
                st.balloons()
            else:
                st.error("Bitte alle Pflichtfelder (*) ausfüllen.")

def show_case_detail():
    case_id = st.session_state.selected_case
    # Alle Akten durchsuchen (inkl. importierter)
    all_cases = get_all_cases()
    case = next((c for c in all_cases if c['id'] == case_id), None)
    if not case:
        st.error("Akte nicht gefunden")
        return

    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"## 📁 Akte {case['nr']}")
        st.caption(case['subject'])
    with col2:
        if st.button("← Zurück"):
            st.session_state.page = 'cases'
            st.rerun()

    s, h, o = get_balance(case_id)
    c1, c2, c3 = st.columns(3)
    c1.metric("Status", case['status'].title())
    c2.metric("Offen", fmt_curr(o))
    c3.metric("Verjährung", fmt_date(case['due_date'] + timedelta(days=3*365)))

    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Übersicht", "💰 Konto", "📄 Dokumente", "⚖️ Mahnverfahren", "📜 Verlauf"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Gläubiger")
            st.write(f"**{case['creditor']}**")
            st.markdown("### Schuldner")
            st.write(f"**{case['debtor']}**")
        with c2:
            st.markdown("### Forderung")
            st.write(f"Hauptforderung: **{fmt_curr(case['principal'])}**")
            st.write(f"Zinssatz: {case['interest']}% p.a.")
            st.write(f"Fällig seit: {fmt_date(case['due_date'])}")

        st.divider()
        st.markdown("### ⚡ Aktionen")

        # Session State für Dialoge
        if f'show_mahnung_{case_id}' not in st.session_state:
            st.session_state[f'show_mahnung_{case_id}'] = False
        if f'show_mb_{case_id}' not in st.session_state:
            st.session_state[f'show_mb_{case_id}'] = False
        if f'show_zahlung_{case_id}' not in st.session_state:
            st.session_state[f'show_zahlung_{case_id}'] = False
        if f'show_ra_calc_{case_id}' not in st.session_state:
            st.session_state[f'show_ra_calc_{case_id}'] = False
        if f'show_schreiben_{case_id}' not in st.session_state:
            st.session_state[f'show_schreiben_{case_id}'] = False

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        if c1.button("📝 Mahnung", use_container_width=True, key=f"btn_mahn_{case_id}"):
            st.session_state[f'show_mahnung_{case_id}'] = True
        if c2.button("⚖️ MB beantragen", use_container_width=True, key=f"btn_mb_{case_id}"):
            st.session_state[f'show_mb_{case_id}'] = True
        if c3.button("💳 Zahlung", use_container_width=True, key=f"btn_zahl_{case_id}"):
            st.session_state[f'show_zahlung_{case_id}'] = True
        if c4.button("💶 RA-Gebühren", use_container_width=True, key=f"btn_rag_{case_id}"):
            st.session_state[f'show_ra_calc_{case_id}'] = True
        if c5.button("📄 Word", use_container_width=True, key=f"btn_word_{case_id}"):
            st.session_state[f'show_schreiben_{case_id}'] = True
        if c6.button("📤 Upload", use_container_width=True, key=f"btn_upl_{case_id}"):
            st.session_state.page = 'case_detail'  # Scroll to documents tab

        # Word-Schreiben generieren Dialog
        if st.session_state.get(f'show_schreiben_{case_id}', False):
            with st.expander("📄 Schreiben aus Word-Vorlage generieren", expanded=True):
                if st.session_state.templates.get('briefkopf_docx'):
                    st.markdown("#### Word-Dokument mit Aktendaten erstellen")

                    # Zeige Platzhalter-Vorschau
                    placeholders = get_case_placeholders(case)
                    with st.expander("📋 Platzhalter-Werte (Vorschau)"):
                        preview_items = [
                            ('[AKTENZEICHEN]', placeholders.get('[AKTENZEICHEN]', '')),
                            ('[KURZBEZEICHNUNG]', placeholders.get('[KURZBEZEICHNUNG]', '')),
                            ('[GEGNER]', placeholders.get('[GEGNER]', '')),
                            ('[GEGNER_ADRESSE]', placeholders.get('[GEGNER_ADRESSE]', '')),
                            ('[MANDANT]', placeholders.get('[MANDANT]', '')),
                            ('[FORDERUNG_GESAMT]', placeholders.get('[FORDERUNG_GESAMT]', '')),
                        ]
                        for key, val in preview_items:
                            st.text(f"{key}: {val}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Dokument generieren", type="primary", key=f"gen_word_{case_id}"):
                            result = generate_document_from_template(case)
                            if result:
                                st.session_state[f'generated_doc_{case_id}'] = result
                                st.success("✅ Dokument wurde generiert!")
                                st.rerun()
                    with col2:
                        if st.button("❌ Schließen", key=f"close_word_{case_id}"):
                            st.session_state[f'show_schreiben_{case_id}'] = False
                            st.rerun()

                    # Download-Button wenn Dokument generiert
                    if st.session_state.get(f'generated_doc_{case_id}'):
                        debtor_name = case['debtor'].split()[-1] if case.get('debtor') else 'Schuldner'
                        st.download_button(
                            "⬇️ Word-Dokument herunterladen",
                            data=st.session_state[f'generated_doc_{case_id}'],
                            file_name=f"Schreiben_{case['nr'].replace('/', '-')}_{debtor_name}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            type="primary",
                            key=f"dl_word_{case_id}"
                        )
                else:
                    st.warning("⚠️ Keine Word-Vorlage hochgeladen!")
                    st.info("Gehen Sie zu **Vorlagen** → **Briefkopf & Signatur** und laden Sie Ihren Kanzlei-Briefkopf als Word-Dokument hoch.")
                    if st.button("📋 Zu den Vorlagen", key=f"goto_tpl_{case_id}"):
                        st.session_state.page = 'templates'
                        st.rerun()

        # Mahnung Dialog
        if st.session_state.get(f'show_mahnung_{case_id}', False):
            with st.expander("📝 Mahnung erstellen", expanded=True):
                st.markdown("#### Mahnschreiben generieren")
                mahn_nr = st.selectbox("Mahnung Nr.", [1, 2, 3], key=f"mahn_nr_{case_id}")
                mahn_frist = st.number_input("Zahlungsfrist (Tage)", min_value=7, max_value=30, value=14, key=f"mahn_frist_{case_id}")
                mahn_text = st.text_area("Zusätzlicher Text", placeholder="Optional: Individueller Text für die Mahnung...", key=f"mahn_text_{case_id}")

                col1, col2 = st.columns(2)
                if col1.button("✅ Mahnung erstellen", type="primary", key=f"mahn_create_{case_id}"):
                    st.success(f"✅ {mahn_nr}. Mahnung für {case['debtor']} erstellt! Frist: {mahn_frist} Tage")
                    st.session_state[f'show_mahnung_{case_id}'] = False
                    st.rerun()
                if col2.button("❌ Abbrechen", key=f"mahn_cancel_{case_id}"):
                    st.session_state[f'show_mahnung_{case_id}'] = False
                    st.rerun()

        # MB beantragen Dialog
        if st.session_state.get(f'show_mb_{case_id}', False):
            with st.expander("⚖️ Mahnbescheid beantragen", expanded=True):
                st.markdown("#### Antrag auf Erlass eines Mahnbescheids")
                st.info(f"**Schuldner:** {case['debtor']}\n**Hauptforderung:** {fmt_curr(case['principal'])}")

                # Gerichtskosten berechnen
                gk = 32.00 if case['principal'] <= 1000 else 36.00 if case['principal'] <= 2000 else 43.00
                st.write(f"**Gerichtskosten (ca.):** {fmt_curr(gk)}")

                mb_mahngericht = st.selectbox("Mahngericht", ["Berlin-Wedding", "Coburg", "Stuttgart", "Hagen", "Hamburg"], key=f"mb_gericht_{case_id}")
                mb_zinsen = st.checkbox("Verzugszinsen geltend machen", value=True, key=f"mb_zinsen_{case_id}")

                col1, col2 = st.columns(2)
                if col1.button("📤 MB beantragen", type="primary", key=f"mb_create_{case_id}"):
                    st.success(f"✅ Mahnbescheid beim AG {mb_mahngericht} beantragt!")
                    st.session_state[f'show_mb_{case_id}'] = False
                    st.rerun()
                if col2.button("❌ Abbrechen", key=f"mb_cancel_{case_id}"):
                    st.session_state[f'show_mb_{case_id}'] = False
                    st.rerun()

        # Zahlung buchen Dialog
        if st.session_state.get(f'show_zahlung_{case_id}', False):
            with st.expander("💳 Zahlung buchen", expanded=True):
                st.markdown("#### Zahlungseingang verbuchen")

                z_col1, z_col2 = st.columns(2)
                with z_col1:
                    z_betrag = st.number_input("Betrag (€)", min_value=0.01, value=100.00, key=f"z_betrag_{case_id}")
                    z_datum = st.date_input("Eingangsdatum", value=date.today(), key=f"z_datum_{case_id}")
                with z_col2:
                    z_art = st.selectbox("Zahlungsart", ["Überweisung", "Bar", "Scheck", "Ratenzahlung"], key=f"z_art_{case_id}")
                    z_ref = st.text_input("Referenz/Verwendungszweck", key=f"z_ref_{case_id}")

                col1, col2 = st.columns(2)
                if col1.button("💾 Zahlung buchen", type="primary", key=f"z_create_{case_id}"):
                    # Buchung hinzufügen
                    new_booking = {
                        'date': z_datum,
                        'type': 'H',
                        'amount': z_betrag,
                        'cat': 'Zahlung',
                        'desc': f'{z_art}: {z_ref}' if z_ref else z_art
                    }
                    if case_id not in DEMO_BOOKINGS:
                        DEMO_BOOKINGS[case_id] = []
                    DEMO_BOOKINGS[case_id].append(new_booking)
                    st.success(f"✅ Zahlung über {fmt_curr(z_betrag)} verbucht!")
                    st.session_state[f'show_zahlung_{case_id}'] = False
                    st.rerun()
                if col2.button("❌ Abbrechen", key=f"z_cancel_{case_id}"):
                    st.session_state[f'show_zahlung_{case_id}'] = False
                    st.rerun()

        # RA-Gebühren Rechner Dialog
        if st.session_state.get(f'show_ra_calc_{case_id}', False):
            with st.expander("💶 RA-Gebühren berechnen (RVG)", expanded=True):
                st.markdown("#### Rechtsanwaltsgebühren nach RVG")

                ra_col1, ra_col2 = st.columns(2)
                with ra_col1:
                    streitwert = st.number_input(
                        "Streitwert (€)",
                        min_value=0.01,
                        value=float(case['principal']),
                        key=f"ra_sw_{case_id}"
                    )
                with ra_col2:
                    gebuehrensatz = st.selectbox(
                        "Gebührensatz",
                        [
                            ("0,5 - Einfache Schreiben", 0.5),
                            ("1,0 - Verfahrensgebühr", 1.0),
                            ("1,3 - Geschäftsgebühr", 1.3),
                            ("1,5 - Erhöhte Gebühr", 1.5),
                            ("2,0 - Terminsgebühr", 2.0),
                        ],
                        index=2,
                        format_func=lambda x: x[0],
                        key=f"ra_gs_{case_id}"
                    )[1]

                # Berechnung
                ra_kosten = calculate_ra_kosten(streitwert, gebuehrensatz)

                st.divider()
                st.markdown("##### Berechnungsergebnis")

                r_col1, r_col2 = st.columns(2)
                with r_col1:
                    st.write(f"**Streitwert:** {fmt_curr(ra_kosten['streitwert'])}")
                    st.write(f"**Grundgebühr (RVG):** {fmt_curr(ra_kosten['grund_gebuehr'])}")
                    st.write(f"**Gebührensatz:** {ra_kosten['gebuehrensatz']}")
                with r_col2:
                    st.write(f"**Geschäftsgebühr:** {fmt_curr(ra_kosten['geschaefts_gebuehr'])}")
                    st.write(f"**Auslagenpauschale:** {fmt_curr(ra_kosten['auslagenpauschale'])}")
                    st.write(f"**USt. (19%):** {fmt_curr(ra_kosten['ust'])}")

                st.metric("**Gesamt (brutto)**", fmt_curr(ra_kosten['gesamt']))

                col1, col2, col3 = st.columns(3)
                if col1.button("💾 Als Buchung übernehmen", type="primary", key=f"ra_book_{case_id}"):
                    new_booking = {
                        'date': date.today(),
                        'type': 'S',
                        'amount': ra_kosten['gesamt'],
                        'cat': 'RA-Gebühren',
                        'desc': f'{ra_kosten["gebuehrensatz"]} Gebühr Nr. 2300 VV RVG'
                    }
                    if case_id not in DEMO_BOOKINGS:
                        DEMO_BOOKINGS[case_id] = []
                    DEMO_BOOKINGS[case_id].append(new_booking)
                    st.success(f"✅ RA-Gebühren {fmt_curr(ra_kosten['gesamt'])} verbucht!")
                    st.session_state[f'show_ra_calc_{case_id}'] = False
                    st.rerun()
                if col2.button("📋 Kopieren", key=f"ra_copy_{case_id}"):
                    st.code(f"RA-Gebühren: {fmt_curr(ra_kosten['gesamt'])}")
                if col3.button("❌ Schließen", key=f"ra_close_{case_id}"):
                    st.session_state[f'show_ra_calc_{case_id}'] = False
                    st.rerun()

    with tab2:
        st.markdown("### 💰 Forderungskonto")

        # Alle Buchungen holen (inkl. importierte)
        bookings = get_all_bookings(case_id)

        # Wenn keine Buchungen vorhanden, Standard-Buchungen erstellen
        if not bookings:
            st.warning("⚠️ Kein Forderungskonto vorhanden. Erstelle Standard-Buchungen...")
            # Standard-Buchung basierend auf Hauptforderung erstellen
            default_bookings = [
                {
                    'date': case.get('due_date', date.today() - timedelta(days=60)),
                    'type': 'S',
                    'amount': case.get('principal', 0),
                    'cat': 'Hauptforderung',
                    'desc': case.get('leistung', 'Hauptforderung aus Vertrag')
                }
            ]
            # Zu session state hinzufügen
            if case_id not in st.session_state.imported_bookings:
                st.session_state.imported_bookings[case_id] = []
            st.session_state.imported_bookings[case_id].extend(default_bookings)
            bookings = default_bookings

        # Zinsen berechnen mit Details
        zinsen_details = get_interest_details(case, bookings)
        zinsen_berechnet = zinsen_details['zinsen']

        # Übersicht mit aktualisierten Werten
        total_soll = sum(b.get('amount', 0) for b in bookings if b.get('type') == 'S')
        total_haben = sum(b.get('amount', 0) for b in bookings if b.get('type') == 'H')
        total_offen = total_soll + zinsen_berechnet - total_haben

        # Metriken in 4 Spalten
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 Hauptforderung", fmt_curr(case.get('principal', 0) or 0))
        c2.metric("📈 Zinsen (aktuell)", fmt_curr(zinsen_berechnet))
        c3.metric("💳 Zahlungen", fmt_curr(total_haben))
        c4.metric("💰 Offen gesamt", fmt_curr(total_offen))

        # Zinsdetails anzeigen
        with st.expander("📈 Zinsberechnung Details", expanded=zinsen_berechnet > 0):
            zi_c1, zi_c2 = st.columns(2)
            with zi_c1:
                st.write(f"**Zinssatz:** {zinsen_details['zinssatz']}% p.a.")
                st.write(f"**Fällig seit:** {fmt_date(zinsen_details['faellig_seit'])}")
                st.write(f"**Verzugstage:** {zinsen_details['verzugstage']} Tage")
            with zi_c2:
                st.write(f"**Offene Forderung:** {fmt_curr(zinsen_details['offene_forderung'])}")
                st.write(f"**Berechnete Zinsen:** {fmt_curr(zinsen_berechnet)}")

            st.info(f"📐 Berechnung: {zinsen_details['berechnung']}")

            if zinsen_berechnet == 0:
                st.warning("⚠️ Keine Zinsen berechnet. Mögliche Gründe: Forderung noch nicht fällig, vollständig bezahlt, oder kein Fälligkeitsdatum gesetzt.")

        st.divider()

        # Forderungskonto-Tabelle mit laufender Summe
        st.markdown("#### 📋 Kontobewegungen")

        # Tabellenkopf
        col_date, col_desc, col_cat, col_soll, col_haben, col_saldo = st.columns([1.5, 3, 2, 1.5, 1.5, 1.5])
        col_date.markdown("**Datum**")
        col_desc.markdown("**Beschreibung**")
        col_cat.markdown("**Kategorie**")
        col_soll.markdown("**Soll (+)**")
        col_haben.markdown("**Haben (-)**")
        col_saldo.markdown("**Saldo**")

        st.divider()

        # Buchungen chronologisch sortieren und mit laufendem Saldo anzeigen
        laufender_saldo = 0.0
        for b in sorted(bookings, key=lambda x: x['date']):
            if b['type'] == 'S':
                laufender_saldo += b['amount']
                soll_text = f"+{fmt_curr(b['amount'])}"
                haben_text = ""
            else:
                laufender_saldo -= b['amount']
                soll_text = ""
                haben_text = f"-{fmt_curr(b['amount'])}"

            col_date, col_desc, col_cat, col_soll, col_haben, col_saldo = st.columns([1.5, 3, 2, 1.5, 1.5, 1.5])
            col_date.write(fmt_date(b['date']))
            col_desc.write(b.get('desc', '-'))
            col_cat.write(b.get('cat', '-'))

            if b['type'] == 'S':
                col_soll.markdown(f"<span style='color: #d9534f'>{soll_text}</span>", unsafe_allow_html=True)
            else:
                col_soll.write("")

            if b['type'] == 'H':
                col_haben.markdown(f"<span style='color: #5cb85c'>{haben_text}</span>", unsafe_allow_html=True)
            else:
                col_haben.write("")

            col_saldo.write(fmt_curr(laufender_saldo))

        # Zinsen als separate Zeile (immer aktuell)
        if zinsen_berechnet > 0:
            st.divider()
            col_date, col_desc, col_cat, col_soll, col_haben, col_saldo = st.columns([1.5, 3, 2, 1.5, 1.5, 1.5])
            col_date.write(fmt_date(date.today()))
            col_desc.write(f"Verzugszinsen ({case.get('interest', 5.0)}% p.a.)")
            col_cat.write("Zinsen")
            col_soll.markdown(f"<span style='color: #d9534f'>+{fmt_curr(zinsen_berechnet)}</span>", unsafe_allow_html=True)
            col_haben.write("")
            col_saldo.markdown(f"**{fmt_curr(laufender_saldo + zinsen_berechnet)}**")

        # Endsumme
        st.divider()
        col_date, col_desc, col_cat, col_soll, col_haben, col_saldo = st.columns([1.5, 3, 2, 1.5, 1.5, 1.5])
        col_date.write("")
        col_desc.markdown("**GESAMT**")
        col_cat.write("")
        col_soll.markdown(f"**{fmt_curr(total_soll + zinsen_berechnet)}**")
        col_haben.markdown(f"**{fmt_curr(total_haben)}**")
        col_saldo.markdown(f"**{fmt_curr(total_offen)}**")

        st.divider()

        # Buchung hinzufügen
        with st.expander("➕ Buchung hinzufügen"):
            c1, c2 = st.columns(2)
            with c1:
                b_type = st.selectbox("Art", ["Zahlung (Haben)", "Kosten (Soll)"], key=f"b_type_{case_id}")
                b_amt = st.number_input("Betrag", min_value=0.0, key=f"b_amt_{case_id}")
            with c2:
                b_date = st.date_input("Datum", value=date.today(), key=f"b_date_{case_id}")
                b_cat = st.selectbox("Kategorie",
                    ["Zahlung", "Teilzahlung", "Hauptforderung", "Zinsen", "RA-Gebühren",
                     "Gerichtskosten", "Mahnkosten", "Inkassokosten", "Auslagen", "Sonstiges"],
                    key=f"b_cat_{case_id}")
            b_desc = st.text_input("Beschreibung", key=f"b_desc_{case_id}")

            if st.button("💾 Buchung speichern", type="primary", key=f"save_booking_{case_id}"):
                new_booking = {
                    'date': b_date,
                    'type': 'H' if 'Haben' in b_type else 'S',
                    'amount': b_amt,
                    'cat': b_cat,
                    'desc': b_desc if b_desc else b_cat
                }
                # Zu Session State hinzufügen
                if case_id not in st.session_state.imported_bookings:
                    st.session_state.imported_bookings[case_id] = []
                st.session_state.imported_bookings[case_id].append(new_booking)
                st.success(f"✅ Buchung ({b_cat}: {fmt_curr(b_amt)}) gespeichert!")
                st.rerun()

    with tab3:
        show_document_explorer(case_id, case['nr'])

    with tab4:
        st.markdown("### ⚖️ Mahnverfahren")

        steps = ['Nicht beantragt', 'MB beantragt', 'MB zugestellt', 'VB beantragt', 'VB erlassen', 'Titel rechtskräftig']
        status_map = {'nicht_beantragt': 0, 'mb_beantragt': 1, 'mb_zugestellt': 2, 'vb_beantragt': 3, 'vb_erlassen': 4, 'titel_rechtskraeftig': 5}
        current = status_map.get(case['dunning'], 0)

        st.progress((current + 1) / len(steps))
        cols = st.columns(len(steps))
        for i, step in enumerate(steps):
            with cols[i]:
                if i <= current:
                    st.markdown(f"**✓ {step}**")
                else:
                    st.caption(step)

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**MB beantragt:** {fmt_date(case.get('mb_date'))}")
            st.write(f"**MB zugestellt:** {fmt_date(case.get('mb_delivered'))}")
        with c2:
            st.write(f"**VB erlassen:** {fmt_date(case.get('vb_date'))}")
            if case.get('mb_delivered'):
                frist = case['mb_delivered'] + timedelta(14)
                if date.today() <= frist:
                    st.warning(f"⏰ Widerspruchsfrist bis: {fmt_date(frist)}")

        st.divider()
        c1, c2, c3 = st.columns(3)
        if case['dunning'] == 'nicht_beantragt':
            if c1.button("📤 Mahnbescheid beantragen", type="primary", use_container_width=True, key=f"tab_mb_{case_id}"):
                st.session_state[f'show_mb_{case_id}'] = True
                st.rerun()
        if case['dunning'] == 'mb_zugestellt':
            if c2.button("📤 VB beantragen", type="primary", use_container_width=True, key=f"tab_vb_{case_id}"):
                st.success("✅ Vollstreckungsbescheid wird beantragt...")
        if c3.button("📋 EDA-Datei erstellen", use_container_width=True, key=f"tab_eda_{case_id}"):
            st.info("📋 EDA-Datei wird generiert...")
            st.code(f"""EDA-DATENSATZ
Aktenzeichen: {case['nr']}
Schuldner: {case['debtor']}
Gläubiger: {case['creditor']}
Hauptforderung: {fmt_curr(case['principal'])}
Status: {case['dunning']}
---
Format: EDA 4.0 (Mahnbescheid)""", language=None)

    with tab5:
        st.markdown("### 📜 Verlauf")
        events = [
            (datetime.now() - timedelta(1), "Zinsen berechnet", "system"),
            (datetime.now() - timedelta(14), "MB zugestellt", "dunning"),
            (datetime.now() - timedelta(30), "MB beantragt", "dunning"),
            (datetime.now() - timedelta(35), "Teilzahlung 1.000€", "payment"),
            (datetime.now() - timedelta(65), "Akte angelegt", "system"),
        ]
        for dt, title, cat in events:
            icons = {'system': '⚙️', 'dunning': '⚖️', 'payment': '💳'}
            st.markdown(f"**{icons.get(cat, '📌')} {title}**")
            st.caption(dt.strftime("%d.%m.%Y %H:%M"))
            st.divider()

def show_inbox():
    st.markdown("## 📬 Posteingang")
    st.info("Eingehende Dokumente zur Zuordnung")

    # Session state für Zuordnungs-Dialog
    if 'inbox_assign' not in st.session_state:
        st.session_state.inbox_assign = None

    items = [
        ("Brief_2024-12-30.pdf", datetime.now() - timedelta(hours=2), "neu"),
        ("Email_Anlage.pdf", datetime.now() - timedelta(days=1), "zugeordnet"),
    ]
    for name, dt, status in items:
        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
        c1.write(f"📄 {name}")
        c2.write(dt.strftime("%d.%m.%Y %H:%M"))
        c3.write("🔴 Neu" if status == "neu" else "✅ Zugeordnet")
        if c4.button("Zuordnen", key=f"i_{name}"):
            st.session_state.inbox_assign = name
        st.divider()

    # Zuordnungs-Dialog
    if st.session_state.inbox_assign:
        with st.expander(f"📁 Dokument zuordnen: {st.session_state.inbox_assign}", expanded=True):
            case_options = [f"{c['nr']} - {c['debtor']}" for c in DEMO_CASES]
            selected_case = st.selectbox("Akte auswählen", case_options, key="inbox_case_select")
            doc_type = st.selectbox("Dokumenttyp", ["Schreiben", "Rechnung", "Mahnung", "Sonstiges"], key="inbox_doc_type")

            col1, col2 = st.columns(2)
            if col1.button("✅ Zuordnen", type="primary", key="inbox_confirm"):
                st.success(f"✅ '{st.session_state.inbox_assign}' wurde {selected_case} zugeordnet!")
                st.session_state.inbox_assign = None
                st.rerun()
            if col2.button("❌ Abbrechen", key="inbox_cancel"):
                st.session_state.inbox_assign = None
                st.rerun()

# =============================================================================
# NACHRICHTEN & KI-KOMMUNIKATION
# =============================================================================
def show_lawyer_messages():
    """Posteingang für Anwalt mit KI-Unterstützung"""
    st.markdown("## 📬 Posteingang")

    # Tabs für Nachrichten
    tab1, tab2, tab3 = st.tabs(["📥 Eingang", "📤 Gesendet", "🔔 Benachrichtigungen"])

    with tab1:
        # Alle Nachrichten an Anwalt
        all_messages = [m for m in st.session_state.messages + DEMO_MESSAGES if m['to_role'] == 'rechtsanwalt']
        all_messages.sort(key=lambda x: x['date'], reverse=True)

        if not all_messages:
            st.info("Keine Nachrichten vorhanden")
        else:
            for msg in all_messages:
                case = next((c for c in DEMO_CASES if c['id'] == msg.get('case_id')), None)
                case_nr = case['nr'] if case else 'Unbekannt'

                status_icon = "🔴" if not msg['read'] else "✅"
                with st.expander(f"{status_icon} **{msg['subject']}** - Von: {msg['from_name']} (Akte {case_nr}) - {msg['date'].strftime('%d.%m.%Y %H:%M')}"):
                    st.write(msg['content'])

                    st.divider()
                    st.markdown("### 🤖 KI-Antwort generieren")

                    if case:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            response_type = st.selectbox(
                                "Antworttyp",
                                ["Sachstandsmitteilung", "Zahlungsaufforderung", "Ratenzahlungsangebot", "Allgemeine Antwort"],
                                key=f"resp_type_{msg['id']}"
                            )

                        if st.button("🤖 Antwort generieren", key=f"gen_{msg['id']}", type="primary"):
                            with st.spinner("KI generiert Antwort..."):
                                response = generate_ai_response(case, response_type)
                                st.session_state[f"draft_{msg['id']}"] = response

                        # Draft anzeigen/bearbeiten
                        if f"draft_{msg['id']}" in st.session_state:
                            draft = st.text_area(
                                "Antwort (bearbeiten)",
                                value=st.session_state[f"draft_{msg['id']}"],
                                height=300,
                                key=f"edit_{msg['id']}"
                            )

                            st.markdown("### 📤 Versandoptionen")
                            col1, col2, col3, col4 = st.columns(4)

                            with col1:
                                if st.button("📬 In Postfach legen", key=f"inbox_{msg['id']}", use_container_width=True):
                                    send_message(
                                        'rechtsanwalt', st.session_state.user['name'],
                                        msg['from_role'], msg['from_name'],
                                        msg.get('case_id', ''), f"Re: {msg['subject']}", draft
                                    )
                                    add_case_event(msg.get('case_id', ''), 'kommunikation', f"Antwort an {msg['from_name']} gesendet")
                                    st.success("✅ Nachricht in Postfach gelegt!")
                                    st.rerun()

                            with col2:
                                st.download_button(
                                    "📄 Als Word",
                                    data=draft.encode('utf-8'),
                                    file_name=f"Antwort_{case_nr}_{date.today().strftime('%Y%m%d')}.txt",
                                    mime="text/plain",
                                    key=f"word_{msg['id']}",
                                    use_container_width=True
                                )

                            with col3:
                                if st.button("📧 Per E-Mail", key=f"email_{msg['id']}", use_container_width=True):
                                    st.info("E-Mail-Versand würde hier erfolgen (Demo)")

                            with col4:
                                if st.button("📁 Zur Akte", key=f"tocase_{msg['id']}", use_container_width=True):
                                    st.success("✅ Dokument zur Akte hinzugefügt!")
                    else:
                        st.warning("Keine Akte zugeordnet - KI-Antwort nicht möglich")

    with tab2:
        # Gesendete Nachrichten
        sent = [m for m in st.session_state.messages if m.get('from_role') == 'rechtsanwalt']
        sent.sort(key=lambda x: x['date'], reverse=True)

        if not sent:
            st.info("Keine gesendeten Nachrichten")
        else:
            for msg in sent:
                with st.expander(f"📤 **{msg['subject']}** - An: {msg['to_name']} - {msg['date'].strftime('%d.%m.%Y %H:%M')}"):
                    st.write(msg['content'])

    with tab3:
        # Benachrichtigungen
        notifs = [n for n in st.session_state.notifications if n['user_role'] == 'rechtsanwalt']
        notifs.sort(key=lambda x: x['date'], reverse=True)

        if not notifs:
            st.info("Keine Benachrichtigungen")
        else:
            for notif in notifs:
                icon = "🔔" if not notif['read'] else "✓"
                st.write(f"{icon} **{notif['title']}** - {notif['content']} ({notif['date'].strftime('%d.%m.%Y %H:%M')})")
                st.divider()

def show_compose_message():
    """Nachricht verfassen"""
    st.markdown("## ✉️ Nachricht verfassen")

    # Prefill aus WV-Briefentwurf laden
    prefill = st.session_state.get('compose_prefill')
    prefill_subject = ""
    prefill_content = ""
    prefill_case_id = None

    if prefill:
        prefill_subject = prefill.get('subject', '')
        prefill_content = prefill.get('content', '')
        prefill_case_id = prefill.get('case_id')
        st.session_state.compose_prefill = None  # Reset nach Verwendung
        st.info("📝 Nachricht aus Wiedervorlage vorbefüllt")

    # Empfänger auswählen
    recipient_type = st.radio("Empfänger", ["Gläubigerin", "Schuldner"], horizontal=True)

    # Akte auswählen
    all_cases = DEMO_CASES + st.session_state.get('imported_cases', [])
    case_options = ["Ohne Aktenbezug"] + [f"{c['nr']} - {c['debtor']}" for c in all_cases]

    # Vorauswahl falls aus WV
    default_idx = 0
    if prefill_case_id:
        for i, c in enumerate(all_cases):
            if c['id'] == prefill_case_id:
                default_idx = i + 1
                break

    selected_case = st.selectbox("Akte", case_options, index=default_idx)

    case = None
    if selected_case != "Ohne Aktenbezug":
        case_nr = selected_case.split(" - ")[0]
        case = next((c for c in all_cases if c['nr'] == case_nr), None)

    subject = st.text_input("Betreff", value=prefill_subject)

    # KI-Unterstützung
    if case:
        st.markdown("### 🤖 KI-Unterstützung")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📊 Sachstand generieren", use_container_width=True):
                st.session_state.compose_draft = generate_ai_response(case, 'sachstand')
        with col2:
            if st.button("💰 Zahlungsaufforderung", use_container_width=True):
                s, h, o = get_balance(case['id'])
                st.session_state.compose_draft = f"""Sehr geehrte Damen und Herren,

wir erlauben uns, Sie an die offene Forderung in Höhe von {fmt_curr(o)} zu erinnern.

Bitte überweisen Sie den Betrag innerhalb von 14 Tagen auf unser Kanzleikonto.

Mit freundlichen Grüßen"""
        with col3:
            if st.button("📅 Ratenzahlung anbieten", use_container_width=True):
                s, h, o = get_balance(case['id'])
                monthly = round(o / 6, 2)
                st.session_state.compose_draft = f"""Sehr geehrte Damen und Herren,

wir bieten Ihnen die Möglichkeit einer Ratenzahlung an.

Offener Betrag: {fmt_curr(o)}
Vorgeschlagene Monatsrate: {fmt_curr(monthly)}
Laufzeit: 6 Monate

Bei Interesse melden Sie sich bitte.

Mit freundlichen Grüßen"""

    # Nachrichtentext
    default_content = prefill_content or st.session_state.get('compose_draft', '')
    content = st.text_area(
        "Nachricht",
        value=default_content,
        height=300
    )

    # Dokumente anhängen
    attach_docs = st.checkbox("Dokumente anhängen")
    selected_docs = []
    if attach_docs and case:
        docs = DEMO_DOCUMENTS.get(case['id'], [])
        for doc in docs:
            if st.checkbox(f"📄 {doc['name']}", key=f"attach_{doc['id']}"):
                selected_docs.append(doc['id'])

    st.divider()

    # WV-Vorschläge anzeigen wenn vorhanden
    if st.session_state.pending_wv_vorschlaege and case:
        st.markdown("---")
        st.markdown("### 📅 Wiedervorlage erkannt")
        st.info("Im Text wurden Fristen erkannt. Möchten Sie eine Wiedervorlage anlegen?")

        for i, vorschlag in enumerate(st.session_state.pending_wv_vorschlaege):
            with st.expander(f"📅 {vorschlag.titel} - {vorschlag.datum.strftime('%d.%m.%Y')}", expanded=True):
                st.write(f"**Erkannter Text:** _{vorschlag.original_text}_")
                st.write(f"**Grund:** {vorschlag.grund.value}")
                st.write(f"**Zu prüfen:** {vorschlag.bedingung.value}")

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button(f"✅ WV anlegen", key=f"wv_create_{i}", type="primary"):
                        # WV speichern
                        wv_entry = {
                            'id': f"wv-{case['id']}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                            'titel': vorschlag.titel,
                            'datum': vorschlag.datum,
                            'grund': vorschlag.grund.value,
                            'bedingung': vorschlag.bedingung.value,
                            'prioritaet': vorschlag.prioritaet,
                            'erstellt': datetime.now(),
                            'status': 'offen',
                            'original_text': vorschlag.original_text
                        }
                        if case['id'] not in st.session_state.wiedervorlagen:
                            st.session_state.wiedervorlagen[case['id']] = []
                        st.session_state.wiedervorlagen[case['id']].append(wv_entry)
                        st.success(f"✅ Wiedervorlage für {vorschlag.datum.strftime('%d.%m.%Y')} angelegt!")
                        st.session_state.pending_wv_vorschlaege = None
                        st.rerun()
                with col_b:
                    if st.button(f"❌ Überspringen", key=f"wv_skip_{i}"):
                        st.session_state.pending_wv_vorschlaege = None
                        st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📬 In Postfach senden", type="primary", use_container_width=True):
            if subject and content:
                to_role = 'glaeubigerin' if recipient_type == "Gläubigerin" else 'schuldner'
                to_name = case['creditor'] if to_role == 'glaeubigerin' else case['debtor'] if case else "Empfänger"

                send_message(
                    'rechtsanwalt', st.session_state.user['name'],
                    to_role, to_name,
                    case['id'] if case else '', subject, content, selected_docs
                )

                if case:
                    add_case_event(case['id'], 'kommunikation', f"Nachricht an {to_name} gesendet: {subject}")

                # WV-Vorschläge erkennen
                if WV_SERVICE_AVAILABLE and case:
                    vorschlaege = erstelle_wv_vorschlaege(f"{subject}\n{content}")
                    if vorschlaege:
                        st.session_state.pending_wv_vorschlaege = vorschlaege
                        st.success("✅ Nachricht gesendet! Fristen erkannt - siehe unten.")
                        st.session_state.compose_draft = ''
                        st.rerun()

                st.success("✅ Nachricht gesendet!")
                st.session_state.compose_draft = ''
                st.rerun()
            else:
                st.error("Bitte Betreff und Nachricht eingeben")

    with col2:
        st.download_button(
            "📄 Als Dokument speichern",
            data=content.encode('utf-8'),
            file_name=f"Schreiben_{date.today().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )

    with col3:
        if st.button("❌ Abbrechen", use_container_width=True):
            st.session_state.compose_draft = ''
            st.session_state.pending_wv_vorschlaege = None
            st.session_state.page = 'dashboard'
            st.rerun()

def show_settings():
    """Einstellungen für API-Keys und Benachrichtigungen"""
    st.markdown("## ⚙️ Einstellungen")

    tab1, tab2, tab3, tab4 = st.tabs(["🤖 KI-Integration", "🔔 Benachrichtigungen", "👤 Profil", "🔧 Debug"])

    with tab1:
        st.markdown("### OpenAI API-Schlüssel")

        # Prüfen ob Key aus Secrets geladen wurde
        if st.session_state.get('openai_api_key_from_secrets', False):
            st.success("✅ **API-Key aus Streamlit Secrets geladen**")
            st.info("""
            Der OpenAI API-Schlüssel wurde automatisch aus den Streamlit Secrets geladen.

            Unterstützte Secret-Namen:
            - `OPENAI_API_KEY`
            - `openai_api_key`
            - `openai.api_key`
            """)
            # Maskierten Key anzeigen
            masked_key = st.session_state.openai_api_key[:7] + "..." + st.session_state.openai_api_key[-4:] if len(st.session_state.openai_api_key) > 15 else "***"
            st.text_input("Geladener API-Schlüssel", value=masked_key, disabled=True)
        else:
            st.info("""
            Für die KI-gestützte Kommunikation benötigen Sie einen OpenAI API-Schlüssel.

            **Option 1:** Hier manuell eingeben
            **Option 2:** In Streamlit Secrets hinterlegen als `OPENAI_API_KEY`

            API-Schlüssel erhalten Sie unter: https://platform.openai.com/api-keys
            """)

            api_key = st.text_input(
                "API-Schlüssel",
                value=st.session_state.openai_api_key,
                type="password",
                placeholder="sk-..."
            )

            if st.button("💾 API-Schlüssel speichern", type="primary"):
                st.session_state.openai_api_key = api_key
                st.session_state.openai_api_key_from_secrets = False
                if api_key:
                    st.success("✅ API-Schlüssel gespeichert!")
                else:
                    st.info("API-Schlüssel entfernt. KI nutzt jetzt Template-basierte Antworten.")

        st.divider()
        st.markdown("### KI-Status")
        if st.session_state.openai_api_key:
            source = "aus Secrets" if st.session_state.get('openai_api_key_from_secrets', False) else "manuell konfiguriert"
            st.success(f"✅ KI-Integration aktiv (OpenAI GPT-4) - {source}")
        else:
            st.warning("⚠️ Keine API - Template-basierte Antworten werden verwendet")

    with tab2:
        st.markdown("### Browser-Benachrichtigungen")
        browser_notif = st.checkbox(
            "Browser-Benachrichtigungen aktivieren",
            value=st.session_state.browser_notifications
        )
        if browser_notif != st.session_state.browser_notifications:
            st.session_state.browser_notifications = browser_notif
            st.success("Einstellung gespeichert!")

        st.markdown("### E-Mail-Benachrichtigungen")
        email_notif = st.checkbox("E-Mail bei neuen Nachrichten", value=True)
        event_notif = st.checkbox("E-Mail bei Aktenfortschritt", value=True)

        st.markdown("### Benachrichtigungstypen")
        st.checkbox("Neue Nachrichten von Gläubigern", value=True)
        st.checkbox("Neue Nachrichten von Schuldnern", value=True)
        st.checkbox("Zahlungseingänge", value=True)
        st.checkbox("Mahnverfahren-Updates", value=True)
        st.checkbox("Fristen-Warnungen", value=True)

    with tab3:
        st.markdown("### Profil")
        st.text_input("Name", value=st.session_state.user['name'], disabled=True)
        st.text_input("E-Mail", value="ra.mueller@kanzlei.de")
        st.text_input("Telefon", value="+49 30 123456")

        st.markdown("### Kanzlei")
        st.text_input("Kanzleiname", value="Kanzlei Müller & Partner")
        st.text_area("Adresse", value="Musterstraße 123\n10115 Berlin")

    with tab4:
        st.markdown("### 🔧 Debug & System-Status")
        st.caption("Diese Seite zeigt den Status aller Systemkomponenten und hilft bei der Fehlersuche.")

        # ============= DATENBANK STATUS =============
        st.markdown("#### 🗄️ Datenbank")

        if DB_AVAILABLE:
            try:
                db_status = get_db_status()

                if db_status['database']['connected']:
                    st.success(f"✅ PostgreSQL verbunden")
                    db_col1, db_col2 = st.columns(2)
                    with db_col1:
                        st.write(f"**Host:** {db_status['database']['host']}")
                        st.write(f"**Datenbank:** {db_status['database']['database']}")
                    with db_col2:
                        st.write(f"**Modus:** {db_status['database'].get('mode', 'Verbunden')}")

                elif db_status['database']['configured']:
                    st.error(f"❌ Verbindungsfehler")
                    st.write(f"**Fehler:** {db_status['database']['message']}")

                    # Hilfestellung bei häufigen Fehlern
                    error_msg = db_status['database']['message'].lower()

                    if "tenant or user not found" in error_msg:
                        st.warning("""
                        **Häufige Ursache:** Bei Supabase Pooler (Port 6543) muss der Benutzername
                        das Format `postgres.[PROJECT-REF]` haben.

                        **Lösung:** Verwenden Sie die vollständige Database URL aus dem Supabase Dashboard:
                        1. Supabase Dashboard → Project Settings → Database
                        2. Connection string → URI kopieren
                        3. In Streamlit Secrets einfügen als:
                        """)
                        st.code("""[supabase]
url = "postgresql://postgres.abcdef123456:IhrPasswort@aws-0-eu-west-2.pooler.supabase.com:6543/postgres" """, language="toml")

                    elif "password authentication failed" in error_msg:
                        st.warning("**Häufige Ursache:** Falsches Passwort oder Sonderzeichen nicht URL-kodiert.")

                    elif "could not connect" in error_msg or "connection refused" in error_msg:
                        st.warning("**Häufige Ursache:** Host oder Port falsch, oder Firewall blockiert.")

                else:
                    st.warning("⚠️ Supabase nicht konfiguriert")
                    st.write("**Modus:** SQLite (lokal)")
                    st.caption("Konfigurieren Sie Supabase in den Streamlit Secrets")

                # Konfigurationshinweis
                with st.expander("📖 Supabase Konfiguration"):
                    st.markdown("""
                    **Empfohlene Methode: Vollständige URL**

                    1. Öffnen Sie das Supabase Dashboard
                    2. Gehen Sie zu **Project Settings** → **Database**
                    3. Kopieren Sie den **Connection string** (URI)
                    4. Fügen Sie ihn in Ihre Streamlit Secrets ein:
                    """)
                    st.code("""[supabase]
url = "postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres" """, language="toml")

                    st.markdown("""
                    **Wichtige Hinweise:**
                    - Ersetzen Sie `[YOUR-PASSWORD]` mit Ihrem tatsächlichen Passwort
                    - Bei Sonderzeichen im Passwort: URL-kodieren (z.B. `@` → `%40`)
                    - Port 6543 = Transaction Pooler (empfohlen)
                    - Port 5432 = Session Pooler
                    """)

            except Exception as e:
                st.error(f"❌ Datenbankfehler: {str(e)}")
        else:
            st.warning("⚠️ Datenbank-Modul nicht geladen")
            st.caption("Die Datenbank-Integration ist nicht verfügbar.")

        st.divider()

        # ============= REDIS CACHE STATUS =============
        st.markdown("#### ⚡ Redis Cache")

        if DB_AVAILABLE:
            try:
                from src.database.cache import get_cache, cache_enabled

                cache = get_cache()
                if cache.is_connected:
                    stats = cache.get_stats()
                    st.success("✅ Redis Cache verbunden")

                    cache_col1, cache_col2, cache_col3 = st.columns(3)
                    cache_col1.metric("Keys", stats.get('total_keys', 0))
                    cache_col2.metric("Speicher", stats.get('used_memory', 'N/A'))
                    cache_col3.metric("Clients", stats.get('connected_clients', 0))
                else:
                    st.warning("⚠️ Redis nicht verbunden")
                    st.caption("Cache ist deaktiviert. Die App funktioniert, aber langsamer.")

                    st.write("**Erforderliche Secrets:**")
                    st.code("""[redis]
url = "redis://default:password@host:6379" """, language="toml")

            except Exception as e:
                st.error(f"❌ Cache-Fehler: {str(e)}")
        else:
            st.info("ℹ️ Cache-Modul nicht geladen")

        st.divider()

        # ============= OPENAI STATUS =============
        st.markdown("#### 🤖 OpenAI API")

        if st.session_state.openai_api_key:
            st.success("✅ API-Key konfiguriert")

            source = "Streamlit Secrets" if st.session_state.get('openai_api_key_from_secrets', False) else "Manuell eingegeben"
            st.write(f"**Quelle:** {source}")

            masked_key = st.session_state.openai_api_key[:7] + "..." + st.session_state.openai_api_key[-4:] if len(st.session_state.openai_api_key) > 15 else "***"
            st.write(f"**Key:** {masked_key}")

            # Test-Button
            if st.button("🧪 API testen"):
                with st.spinner("Teste OpenAI API..."):
                    try:
                        from openai import OpenAI
                        client = OpenAI(api_key=st.session_state.openai_api_key)
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": "Sag nur 'OK'"}],
                            max_tokens=5
                        )
                        st.success(f"✅ API funktioniert! Antwort: {response.choices[0].message.content}")
                    except Exception as e:
                        st.error(f"❌ API-Fehler: {str(e)}")
        else:
            st.warning("⚠️ Kein OpenAI API-Key")
            st.caption("KI-Funktionen nutzen Template-basierte Antworten.")

        st.divider()

        # ============= SESSION STATE DEBUG =============
        st.markdown("#### 📦 Session State")

        with st.expander("Session State anzeigen"):
            debug_state = {
                'authenticated': st.session_state.get('authenticated', False),
                'user': st.session_state.get('user'),
                'page': st.session_state.get('page'),
                'selected_case': st.session_state.get('selected_case'),
                'imported_cases_count': len(st.session_state.get('imported_cases', [])),
                'imported_documents_count': len(st.session_state.get('imported_documents', {})),
                'document_pdfs_count': len(st.session_state.get('document_pdfs', {})),
                'case_full_pdfs_count': len(st.session_state.get('case_full_pdfs', {})),
                'openai_api_key_set': bool(st.session_state.get('openai_api_key')),
            }
            st.json(debug_state)

        st.divider()

        # ============= SYSTEM INFO =============
        st.markdown("#### ℹ️ System-Information")

        import sys
        import platform

        sys_col1, sys_col2 = st.columns(2)
        with sys_col1:
            st.write(f"**App-Version:** {APP_VERSION}")
            st.write(f"**Python:** {sys.version.split()[0]}")
            st.write(f"**Plattform:** {platform.system()} {platform.release()}")
        with sys_col2:
            st.write(f"**Streamlit:** {st.__version__}")
            st.write(f"**DB-Modul:** {'Geladen' if DB_AVAILABLE else 'Nicht verfügbar'}")

        st.divider()

        # ============= FEHLER-LOG =============
        st.markdown("#### 📋 Letzte Fehler")

        if 'error_log' not in st.session_state:
            st.session_state.error_log = []

        if st.session_state.error_log:
            for err in st.session_state.error_log[-10:]:  # Letzte 10 Fehler
                st.error(f"{err['time']}: {err['message']}")
            if st.button("🗑️ Fehler-Log löschen"):
                st.session_state.error_log = []
                st.rerun()
        else:
            st.info("✅ Keine Fehler protokolliert")

        # Button zum Testen
        st.divider()
        if st.button("🔄 Status aktualisieren"):
            st.rerun()

def show_dunning():
    st.markdown("## ⚖️ Mahnverfahren")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("MB beantragt", 0)
    c2.metric("MB zugestellt", 1)
    c3.metric("VB beantragt", 0)
    c4.metric("Titel", 1)

    st.divider()
    st.markdown("### Akten im Verfahren")

    dunning_cases = [c for c in DEMO_CASES if c['dunning'] != 'nicht_beantragt']
    for case in dunning_cases:
        c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
        c1.write(f"**{case['nr']}**")
        c1.caption(case['debtor'])
        c2.write(case['dunning'].replace('_', ' ').title())
        if case.get('mb_delivered'):
            frist = case['mb_delivered'] + timedelta(14)
            if date.today() <= frist:
                c3.warning(f"Frist: {fmt_date(frist)}")
        if st.button("Öffnen", key=f"d_{case['id']}"):
            st.session_state.selected_case = case['id']
            st.session_state.page = 'case_detail'
            st.rerun()
        st.divider()

def show_enforcement():
    st.markdown("## 🔨 Vollstreckung")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("GV-Aufträge", 0)
    c2.metric("PfÜB", 1)
    c3.metric("VV erhalten", 0)
    c4.metric("Abgeschlossen", 0)

    st.divider()
    st.markdown("### Akten in Vollstreckung")

    enf_cases = [c for c in DEMO_CASES if c['status'] == 'vollstreckung']
    for case in enf_cases:
        s, h, o = get_balance(case['id'])
        c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
        c1.write(f"**{case['nr']}** - {case['debtor']}")
        c2.write(case['enforcement'].replace('_', ' ').title())
        c3.write(f"**{fmt_curr(o)}** offen")
        if st.button("Öffnen", key=f"e_{case['id']}"):
            st.session_state.selected_case = case['id']
            st.session_state.page = 'case_detail'
            st.rerun()
        st.divider()

    st.markdown("### ⚡ Aktionen")

    # Session state für Dialoge
    if 'show_gv' not in st.session_state:
        st.session_state.show_gv = False
    if 'show_pfueb' not in st.session_state:
        st.session_state.show_pfueb = False
    if 'show_vv' not in st.session_state:
        st.session_state.show_vv = False

    c1, c2, c3 = st.columns(3)
    if c1.button("👮 GV-Auftrag", use_container_width=True):
        st.session_state.show_gv = True
    if c2.button("📋 PfÜB beantragen", use_container_width=True):
        st.session_state.show_pfueb = True
    if c3.button("📊 VV-Analyse", use_container_width=True):
        st.session_state.show_vv = True

    # GV-Auftrag Dialog
    if st.session_state.show_gv:
        with st.expander("👮 Gerichtsvollzieher-Auftrag erstellen", expanded=True):
            gv_case = st.selectbox("Akte", [f"{c['nr']} - {c['debtor']}" for c in enf_cases], key="gv_case")
            gv_type = st.selectbox("Auftragsart", [
                "Mobiliarvollstreckung",
                "Abnahme Vermögensauskunft",
                "Haftbefehl beantragen",
                "Taschenpfändung"
            ], key="gv_type")
            gv_notes = st.text_area("Hinweise für GV", placeholder="Besonderheiten...", key="gv_notes")

            col1, col2 = st.columns(2)
            if col1.button("📤 Auftrag erstellen", type="primary", key="gv_create"):
                st.success(f"✅ GV-Auftrag ({gv_type}) für {gv_case} erstellt!")
                st.session_state.show_gv = False
                st.rerun()
            if col2.button("❌ Abbrechen", key="gv_cancel"):
                st.session_state.show_gv = False
                st.rerun()

    # PfÜB Dialog
    if st.session_state.show_pfueb:
        with st.expander("📋 Pfändungs- und Überweisungsbeschluss", expanded=True):
            pf_case = st.selectbox("Akte", [f"{c['nr']} - {c['debtor']}" for c in enf_cases], key="pf_case")
            pf_drittschuldner = st.text_input("Drittschuldner (z.B. Arbeitgeber, Bank)", key="pf_ds")
            pf_type = st.selectbox("Pfändungsart", [
                "Arbeitseinkommen",
                "Bankkonto (P-Konto)",
                "Sonstige Forderungen"
            ], key="pf_type")

            col1, col2 = st.columns(2)
            if col1.button("📤 PfÜB beantragen", type="primary", key="pf_create"):
                st.success(f"✅ PfÜB gegen {pf_drittschuldner} für {pf_case} beantragt!")
                st.session_state.show_pfueb = False
                st.rerun()
            if col2.button("❌ Abbrechen", key="pf_cancel"):
                st.session_state.show_pfueb = False
                st.rerun()

    # VV-Analyse Dialog
    if st.session_state.show_vv:
        with st.expander("📊 Vermögensverzeichnis-Analyse", expanded=True):
            st.info("Analyse des Vermögensverzeichnisses zur Identifikation von Vollstreckungsmöglichkeiten")
            vv_case = st.selectbox("Akte", [f"{c['nr']} - {c['debtor']}" for c in enf_cases], key="vv_case")

            st.markdown("#### Erkannte Vermögenswerte (Demo)")
            st.write("💼 **Arbeitgeber:** Musterfirma GmbH, Musterstr. 1, 10115 Berlin")
            st.write("🏦 **Bankverbindung:** Sparkasse Berlin, IBAN: DE89...")
            st.write("🚗 **Fahrzeug:** VW Golf, Bj. 2019 (Finanziert)")
            st.write("🏠 **Immobilie:** Keine")

            st.markdown("#### Empfehlung")
            st.success("✅ Lohnpfändung empfohlen (Arbeitseinkommen vorhanden)")

            if st.button("❌ Schließen", key="vv_close"):
                st.session_state.show_vv = False
                st.rerun()

def show_limitation():
    st.markdown("## ⏰ Verjährung")

    st.info("**Fristen:** Regulär 3 Jahre (Jahresende), Tituliert 30 Jahre")
    st.divider()

    for case in DEMO_CASES:
        titled = case['dunning'] == 'titel_rechtskraeftig'
        if titled:
            lim = case['due_date'] + timedelta(days=30*365)
        else:
            lim = date(case['due_date'].year + 4, 12, 31)
        days = (lim - date.today()).days

        c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
        c1.write(f"**{case['nr']}** - {case['debtor']}")
        c2.write("🏆 Tituliert" if titled else "📋 Nicht tituliert")
        c3.write(f"Verjährt: {fmt_date(lim)}")
        if days < 90:
            c4.error(f"⚠️ {days} Tage!")
        elif days < 365:
            c4.warning(f"⚡ {days} Tage")
        else:
            c4.success(f"✅ {days} Tage")
        st.divider()

# =============================================================================
# KLAGE-ENTWURF SYSTEM
# =============================================================================
def get_zustaendiges_gericht(case):
    """
    Ermittelt das zuständige Gericht nach ZPO.
    Sachliche Zuständigkeit: Streitwert > 5000€ = Landgericht, sonst Amtsgericht
    Örtliche Zuständigkeit: Wohnsitz des Beklagten (allgemeiner Gerichtsstand)
    """
    streitwert = case['principal']
    debtor_address = case.get('debtor_address', '')

    # Sachliche Zuständigkeit
    if streitwert > 5000:
        gericht_art = "Landgericht"
    else:
        gericht_art = "Amtsgericht"

    # Örtliche Zuständigkeit aus Adresse ableiten
    if 'Berlin' in debtor_address:
        if gericht_art == "Landgericht":
            gericht = "Landgericht Berlin"
        else:
            # Bezirk aus PLZ ermitteln
            if '10115' in debtor_address or '10178' in debtor_address:
                gericht = "Amtsgericht Berlin-Mitte"
            elif '10245' in debtor_address:
                gericht = "Amtsgericht Berlin-Kreuzberg"
            elif '10999' in debtor_address:
                gericht = "Amtsgericht Berlin-Kreuzberg"
            else:
                gericht = "Amtsgericht Berlin-Mitte"
    else:
        gericht = f"{gericht_art} [Ort einsetzen]"

    return {
        'art': gericht_art,
        'name': gericht,
        'streitwert': streitwert,
        'ist_landgericht': streitwert > 5000
    }

def generate_klage_entwurf(case, use_ai=False):
    """
    Generiert einen vollständigen Klage-Entwurf nach ZPO.
    """
    s, h, o = get_balance(case['id'])
    gericht_info = get_zustaendiges_gericht(case)
    kanzlei = st.session_state.kanzlei_daten

    # Prüfen ob Mahnverfahren durchgeführt wurde
    hat_mahnverfahren = case.get('mb_az') is not None
    hat_widerspruch = case.get('widerspruch', False)
    hat_einspruch = case.get('einspruch', False)
    abgabe_erfolgt = case.get('abgabe_streitgericht', False)

    # Zahlungen ermitteln
    bookings = DEMO_BOOKINGS.get(case['id'], [])
    zahlungen = [b for b in bookings if b['type'] == 'H']

    # Gericht und Rubrum bestimmen
    if hat_mahnverfahren and not abgabe_erfolgt:
        # Noch beim Mahngericht - Abgabeantrag
        gericht_header = f"""An das
{case.get('mb_gericht', 'Amtsgericht [Mahngericht]')}
- Mahnabteilung -

Geschäftszeichen: {case.get('mb_az', '[Aktenzeichen Mahnverfahren]')}

In dem Mahnverfahren

{case['creditor']}
{case.get('creditor_address', '[Adresse Gläubiger]')}
- Antragsteller/Kläger -

Prozessbevollmächtigte: {kanzlei['name']}, {kanzlei['adresse'].replace(chr(10), ', ')}

gegen

{case['debtor']}
{case.get('debtor_address', '[Adresse Schuldner]')}
- Antragsgegner/Beklagter -

wird aufgrund des {'Widerspruchs gegen den Mahnbescheid' if hat_widerspruch else 'Einspruchs gegen den Vollstreckungsbescheid' if hat_einspruch else 'gerichtlichen Mahnverfahrens'} die

**Abgabe an das zuständige Streitgericht**

beantragt.

Zuständiges Streitgericht: {gericht_info['name']}

---

"""
    else:
        gericht_header = ""

    # Hauptteil der Klage
    if abgabe_erfolgt:
        streitgericht = case.get('streitgericht', gericht_info['name'])
        streit_az = case.get('streit_az', '[Aktenzeichen Streitgericht]')
        klage_header = f"""An das
{streitgericht}

Geschäftszeichen: {streit_az}

"""
    else:
        klage_header = f"""An das
{gericht_info['name']}

"""

    # Rubrum
    rubrum = f"""
K L A G E

des/der {case['creditor']}
{case.get('creditor_address', '[Adresse Gläubiger]')}
- Kläger/in -

Prozessbevollmächtigte: {kanzlei['name']}
{kanzlei['adresse']}
Tel: {kanzlei['telefon']}, Fax: {kanzlei['fax']}

gegen

{case['debtor']}
{case.get('debtor_address', '[Adresse Schuldner]')}
- Beklagte/r -

wegen: Forderung aus {case.get('contract_type', 'Vertrag')}

**Streitwert: {fmt_curr(case['principal'])}**
(Gegenstandswert: Hauptforderung ohne Zinsen)

"""

    # Antrag
    due_date_str = fmt_date(case['due_date'])
    antrag = f"""
I. ANTRAG

Es wird beantragt,

den Beklagten/die Beklagte zu verurteilen, an den Kläger/die Klägerin

**{fmt_curr(case['principal'])}**
(in Worten: {betrag_in_worten(case['principal'])})

zuzüglich Zinsen in Höhe von 5 Prozentpunkten über dem jeweiligen Basiszinssatz der EZB seit dem {due_date_str} zu zahlen.

"""

    # Zusätzlich vorgerichtliche Kosten wenn vorhanden
    ra_kosten = sum(b['amount'] for b in bookings if b['cat'] == 'RA-Gebühren')
    if ra_kosten > 0:
        antrag += f"""
Ferner wird beantragt, den Beklagten/die Beklagte zu verurteilen, an den Kläger/die Klägerin vorgerichtliche Rechtsanwaltskosten in Höhe von {fmt_curr(ra_kosten)} nebst Zinsen in Höhe von 5 Prozentpunkten über dem jeweiligen Basiszinssatz seit Rechtshängigkeit zu zahlen.

"""

    # Begründung
    begruendung = f"""
II. BEGRÜNDUNG

1. Sachverhalt

Die Parteien schlossen am {fmt_date(case.get('contract_date', case['due_date']))} einen {case.get('contract_type', 'Vertrag')}.

**Beweis:** {case.get('contract_type', 'Vertrag')} vom {fmt_date(case.get('contract_date', case['due_date']))} (Anlage K1)

Der Kläger/Die Klägerin hat die vertraglich geschuldete Leistung vollständig erbracht:
{case.get('leistung', 'Die Leistung wurde ordnungsgemäß erbracht.')}

**Beweis:** Lieferschein/Leistungsnachweis (Anlage K2)

Für die erbrachte Leistung stellte der Kläger/die Klägerin am {fmt_date(case.get('invoice_date', case['due_date']))} die Rechnung Nr. {case.get('invoice_nr', '[Rechnungsnummer]')} über einen Betrag von {fmt_curr(case['principal'])}.

**Beweis:** Rechnung Nr. {case.get('invoice_nr', '[Rechnungsnummer]')} (Anlage K3)

Die Forderung war am {due_date_str} zur Zahlung fällig.

"""

    # Außergerichtliche Mahnungen
    mahnung_dates = case.get('mahnung_dates', [])
    if mahnung_dates:
        begruendung += f"""
2. Außergerichtliche Beitreibung

Der Beklagte/Die Beklagte wurde außergerichtlich zur Zahlung aufgefordert:
"""
        for i, md in enumerate(mahnung_dates, 1):
            begruendung += f"""
- {i}. Mahnung vom {fmt_date(md)}
"""
        begruendung += """
**Beweis:** Mahnschreiben (Anlagen K4 ff.)

Trotz dieser Aufforderungen blieb die Zahlung aus.

"""

    # Mahnverfahren
    if hat_mahnverfahren:
        begruendung += f"""
3. Gerichtliches Mahnverfahren

Der Kläger/Die Klägerin hat am {fmt_date(case.get('mb_date', date.today()))} beim {case.get('mb_gericht', 'zuständigen Mahngericht')} einen Mahnbescheid beantragt.

Aktenzeichen Mahnverfahren: {case.get('mb_az', '[Aktenzeichen]')}

"""
        if case.get('mb_delivered'):
            begruendung += f"""Der Mahnbescheid wurde dem Beklagten/der Beklagten am {fmt_date(case.get('mb_delivered'))} zugestellt.

"""
        if hat_widerspruch:
            begruendung += """Der Beklagte/Die Beklagte hat gegen den Mahnbescheid Widerspruch eingelegt.

"""
        if hat_einspruch:
            begruendung += """Der Beklagte/Die Beklagte hat gegen den Vollstreckungsbescheid Einspruch eingelegt.

"""
        if case.get('vb_date'):
            begruendung += f"""Am {fmt_date(case.get('vb_date'))} wurde der Vollstreckungsbescheid erlassen.

"""

    # Zahlungen
    if zahlungen:
        begruendung += f"""
4. Zahlungen

Folgende Zahlungen sind eingegangen:
"""
        for z in zahlungen:
            begruendung += f"""
- {fmt_date(z['date'])}: {fmt_curr(z['amount'])} ({z['desc']})
"""
        begruendung += f"""
Diese Zahlungen wurden auf die Forderung verrechnet. Es verbleibt ein offener Betrag von {fmt_curr(o)}.

"""

    # Anspruchsgrundlage
    begruendung += f"""
5. Rechtliche Würdigung / Anspruchsgrundlage

Der Kläger/Die Klägerin hat gegen den Beklagten/die Beklagte einen Anspruch auf Zahlung von {fmt_curr(case['principal'])} aus dem {case.get('contract_type', 'Vertrag')} vom {fmt_date(case.get('contract_date', case['due_date']))}.

Die Anspruchsgrundlage ergibt sich aus:
- § 433 Abs. 2 BGB (Kaufpreisanspruch) bei Kaufverträgen
- § 535 Abs. 2 BGB (Mietzinsanspruch) bei Mietverträgen
- § 631 Abs. 1 BGB (Vergütungsanspruch) bei Werkverträgen

Der Vertrag zwischen den Parteien ist wirksam zustande gekommen. Der Kläger/Die Klägerin hat die geschuldete Leistung vollständig und ordnungsgemäß erbracht. Der Beklagte/Die Beklagte ist daher zur Zahlung des vereinbarten Entgelts verpflichtet.

Der Zinsanspruch ergibt sich aus §§ 286, 288 BGB. Mit Fälligkeit am {due_date_str} befand sich der Beklagte/die Beklagte in Verzug.

"""

    # Beweismittel
    beweismittel = """
III. BEWEISMITTEL

Zum Beweis des klägerischen Vortrags werden folgende Beweismittel angeboten:

1. Anlage K1 - Vertrag vom [Datum]
2. Anlage K2 - Leistungsnachweis/Lieferschein
3. Anlage K3 - Rechnung
4. Anlage K4 ff. - Mahnschreiben
"""
    if hat_mahnverfahren:
        beweismittel += """5. Mahnbescheid/Vollstreckungsbescheid
"""

    beweismittel += """
Zeugenbeweis: [Falls Zeugen vorhanden]

Sachverständigenbeweis: [Falls erforderlich]

Parteivernehmung des Klägers/der Klägerin

"""

    # Unterschrift
    unterschrift = f"""
{kanzlei['adresse'].split(chr(10))[1] if chr(10) in kanzlei['adresse'] else 'Berlin'}, den {fmt_date(date.today())}

{kanzlei['name']}

_______________________
Rechtsanwalt/Rechtsanwältin
"""

    # Zusammenfügen
    klage = gericht_header + klage_header + rubrum + antrag + begruendung + beweismittel + unterschrift

    return klage

def betrag_in_worten(betrag):
    """Wandelt einen Betrag in Worte um (vereinfacht)"""
    euro = int(betrag)
    cent = int((betrag - euro) * 100)

    einer = ['', 'ein', 'zwei', 'drei', 'vier', 'fünf', 'sechs', 'sieben', 'acht', 'neun']
    zehner = ['', 'zehn', 'zwanzig', 'dreißig', 'vierzig', 'fünfzig', 'sechzig', 'siebzig', 'achtzig', 'neunzig']

    if euro < 10:
        euro_wort = einer[euro]
    elif euro < 20:
        euro_wort = ['zehn', 'elf', 'zwölf', 'dreizehn', 'vierzehn', 'fünfzehn', 'sechzehn', 'siebzehn', 'achtzehn', 'neunzehn'][euro-10]
    elif euro < 100:
        euro_wort = einer[euro % 10] + ('und' if euro % 10 > 0 else '') + zehner[euro // 10]
    elif euro < 1000:
        rest = euro % 100
        if rest == 0:
            euro_wort = einer[euro // 100] + 'hundert'
        elif rest < 10:
            euro_wort = einer[euro // 100] + 'hundert' + einer[rest]
        elif rest < 20:
            euro_wort = einer[euro // 100] + 'hundert' + ['zehn', 'elf', 'zwölf', 'dreizehn', 'vierzehn', 'fünfzehn', 'sechzehn', 'siebzehn', 'achtzehn', 'neunzehn'][rest-10]
        else:
            euro_wort = einer[euro // 100] + 'hundert' + einer[rest % 10] + ('und' if rest % 10 > 0 else '') + zehner[rest // 10]
    else:
        tausend = euro // 1000
        rest = euro % 1000
        if tausend == 1:
            euro_wort = 'eintausend'
        else:
            euro_wort = einer[tausend] + 'tausend'
        if rest > 0:
            if rest < 100:
                euro_wort += betrag_in_worten(rest).replace(' Euro', '')
            else:
                euro_wort += einer[rest // 100] + 'hundert'
                if rest % 100 > 0:
                    euro_wort += betrag_in_worten(rest % 100).replace(' Euro', '')

    return f"{euro_wort} Euro" + (f" und {cent} Cent" if cent > 0 else "")

def generate_klage_with_ai(case, klage_entwurf):
    """Verbessert den Klage-Entwurf mit KI"""
    if not st.session_state.openai_api_key:
        return klage_entwurf

    try:
        import openai
        client = openai.OpenAI(api_key=st.session_state.openai_api_key)

        prompt = f"""Du bist ein erfahrener Rechtsanwalt für Zivilrecht.
Bitte überarbeite und verbessere den folgenden Klage-Entwurf:
- Verbessere die juristische Sprache
- Stelle sicher, dass alle formalen Anforderungen der ZPO erfüllt sind
- Ergänze wo sinnvoll rechtliche Ausführungen
- Behalte alle faktischen Angaben bei

Klage-Entwurf:
{klage_entwurf}

Bitte gib den verbesserten Klage-Entwurf zurück."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.warning(f"KI-Verbesserung fehlgeschlagen: {str(e)}")
        return klage_entwurf

def show_klage_entwurf():
    """Hauptseite für Klage-Entwurf"""
    st.markdown("## 📜 Klage-Entwurf")

    st.info("""
    **Klage-Entwurf nach ZPO**

    Dieses Tool erstellt einen vollständigen Klage-Entwurf basierend auf den Aktendaten:
    - Automatische Bestimmung der sachlichen und örtlichen Zuständigkeit
    - Berücksichtigung von Mahnverfahren (Widerspruch/Einspruch)
    - Integration aller Zahlungen und Kosten
    - ZPO-konforme Struktur mit Antrag, Begründung und Beweismitteln
    """)

    st.divider()

    # Akte auswählen
    case_options = [f"{c['nr']} - {c['debtor']} ({fmt_curr(c['principal'])})" for c in DEMO_CASES]
    selected_case_str = st.selectbox("📁 Akte auswählen", case_options)

    case_nr = selected_case_str.split(" - ")[0]
    case = next((c for c in DEMO_CASES if c['nr'] == case_nr), None)

    if not case:
        st.error("Akte nicht gefunden")
        return

    # Akten-Info anzeigen
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### Kläger (Gläubiger)")
        st.write(f"**{case['creditor']}**")
        st.caption(case.get('creditor_address', 'Keine Adresse'))
    with col2:
        st.markdown("### Beklagter (Schuldner)")
        st.write(f"**{case['debtor']}**")
        st.caption(case.get('debtor_address', 'Keine Adresse'))
    with col3:
        s, h, o = get_balance(case['id'])
        st.markdown("### Forderung")
        st.metric("Streitwert", fmt_curr(case['principal']))
        st.caption(f"Offen: {fmt_curr(o)}")

    st.divider()

    # Gerichtszuständigkeit
    gericht_info = get_zustaendiges_gericht(case)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ⚖️ Sachliche Zuständigkeit")
        if gericht_info['ist_landgericht']:
            st.warning(f"**{gericht_info['art']}** (Streitwert > 5.000 €)")
        else:
            st.success(f"**{gericht_info['art']}** (Streitwert ≤ 5.000 €)")
    with col2:
        st.markdown("### 📍 Örtliche Zuständigkeit")
        st.info(f"**{gericht_info['name']}**")
        st.caption("(Allgemeiner Gerichtsstand: Wohnsitz des Beklagten)")

    # Mahnverfahren-Status
    if case.get('mb_az'):
        st.divider()
        st.markdown("### ⚖️ Mahnverfahren")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Mahngericht:** {case.get('mb_gericht', '-')}")
            st.write(f"**Az.:** {case.get('mb_az', '-')}")
        with col2:
            st.write(f"**MB zugestellt:** {fmt_date(case.get('mb_delivered'))}")
            st.write(f"**Widerspruch:** {'Ja' if case.get('widerspruch') else 'Nein'}")
        with col3:
            st.write(f"**VB erlassen:** {fmt_date(case.get('vb_date'))}")
            st.write(f"**Abgabe erfolgt:** {'Ja' if case.get('abgabe_streitgericht') else 'Nein'}")

    st.divider()

    # Optionen
    st.markdown("### ⚙️ Optionen")
    col1, col2 = st.columns(2)
    with col1:
        use_ai = st.checkbox("🤖 KI-Optimierung verwenden", value=bool(st.session_state.openai_api_key))
        if use_ai and not st.session_state.openai_api_key:
            st.warning("Bitte API-Schlüssel in Einstellungen hinterlegen")
    with col2:
        include_costs = st.checkbox("💶 Vorgerichtliche Kosten einbeziehen", value=True)

    st.divider()

    # Klage generieren
    if st.button("📜 Klage-Entwurf erstellen", type="primary", use_container_width=True):
        with st.spinner("Klage wird erstellt..."):
            klage = generate_klage_entwurf(case)

            if use_ai and st.session_state.openai_api_key:
                with st.spinner("KI optimiert den Entwurf..."):
                    klage = generate_klage_with_ai(case, klage)

            st.session_state.current_klage = klage
            st.session_state.current_klage_case = case['id']

    # Klage anzeigen
    if 'current_klage' in st.session_state and st.session_state.get('current_klage_case') == case['id']:
        st.divider()
        st.markdown("### 📄 Klage-Entwurf")

        # Bearbeitbares Textfeld
        edited_klage = st.text_area(
            "Klage (bearbeitbar)",
            value=st.session_state.current_klage,
            height=600,
            key="klage_editor"
        )

        st.divider()

        # Aktionen
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.download_button(
                "📄 Als Word/TXT",
                data=edited_klage.encode('utf-8'),
                file_name=f"Klage_{case['nr'].replace('/', '-')}_{date.today().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True
            )

        with col2:
            if st.button("📋 In Zwischenablage", use_container_width=True):
                st.code(edited_klage[:500] + "...", language=None)
                st.success("Text kopiert!")

        with col3:
            if st.button("📁 Zur Akte speichern", use_container_width=True):
                # Dokument zur Akte hinzufügen
                new_doc = {
                    'id': f'klage-{case["id"]}-{date.today().strftime("%Y%m%d")}',
                    'name': f'Klage_{case["nr"].replace("/", "-")}_{date.today().strftime("%Y%m%d")}.pdf',
                    'date': date.today(),
                    'type': 'Klage',
                    'size': f'{len(edited_klage) // 100} KB'
                }
                if case['id'] not in DEMO_DOCUMENTS:
                    DEMO_DOCUMENTS[case['id']] = []
                DEMO_DOCUMENTS[case['id']].append(new_doc)
                st.success("✅ Klage zur Akte hinzugefügt!")

        with col4:
            if st.button("🤖 Mit KI verbessern", use_container_width=True):
                if st.session_state.openai_api_key:
                    with st.spinner("KI optimiert..."):
                        st.session_state.current_klage = generate_klage_with_ai(case, edited_klage)
                        st.rerun()
                else:
                    st.error("Bitte API-Schlüssel in Einstellungen hinterlegen")

def show_vorlagen():
    """Vorlagen-Verwaltung"""
    st.markdown("## 📋 Vorlagen-Verwaltung")

    st.info("""
    **Vorlagen für Schriftsätze und Dokumente**

    Erstellen und verwalten Sie Vorlagen für:
    - Briefkopf und Kanzleidaten
    - E-Mail-Signatur
    - Zahlungsaufforderungen
    - Klagen
    - Schriftsätze

    Die Vorlagen können mit KI automatisch in fertige Dokumente umgewandelt werden.
    """)

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["📝 Briefkopf & Signatur", "📬 Schreiben", "⚖️ Klagen & Schriftsätze", "🏢 Kanzleidaten"])

    with tab1:
        st.markdown("### 📄 Word-Briefkopf (Empfohlen)")
        st.info("""
        **Laden Sie Ihren Kanzlei-Briefkopf als Word-Dokument (.docx) hoch.**

        Verwenden Sie folgende Platzhalter in Ihrem Dokument:

        | Platzhalter | Wird ersetzt durch |
        |-------------|-------------------|
        | `[AKTENZEICHEN]` | Aktenzeichen (z.B. 975/25) |
        | `[KURZBEZEICHNUNG]` | Mandant ./. Gegner |
        | `[DATUM]` | Aktuelles Datum |
        | `[GEGNER]` / `[SCHULDNER]` | Name des Schuldners |
        | `[GEGNER_ADRESSE]` | Adresse des Schuldners |
        | `[MANDANT]` / `[GLÄUBIGER]` | Name des Mandanten |
        | `[HAUPTFORDERUNG]` | Hauptforderungsbetrag |
        | `[FORDERUNG_GESAMT]` | Gesamtforderung |
        | `[ANREDE_BRIEF]` | "Sehr geehrter Herr" / "Sehr geehrte Frau" |
        | `[FRIST]` | Zahlungsfrist (14 Tage) |
        | `[BANKVERBINDUNG]` | Kanzlei-Bankverbindung |
        """)

        # Aktuell hochgeladene Vorlage anzeigen
        if st.session_state.templates.get('briefkopf_docx'):
            filename = st.session_state.templates.get('briefkopf_filename', 'Briefkopf.docx')
            st.success(f"✅ **Aktive Vorlage:** {filename}")

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "⬇️ Vorlage herunterladen",
                    data=st.session_state.templates['briefkopf_docx'],
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            with col2:
                if st.button("🗑️ Vorlage entfernen", key="remove_docx"):
                    st.session_state.templates['briefkopf_docx'] = None
                    st.session_state.templates['briefkopf_filename'] = None
                    st.rerun()

        # Upload neuer Vorlage
        uploaded_docx = st.file_uploader(
            "Word-Dokument hochladen (.docx)",
            type=['docx'],
            key="upload_briefkopf"
        )

        if uploaded_docx:
            if st.button("✅ Als Briefkopf-Vorlage speichern", type="primary", key="save_docx"):
                docx_bytes = uploaded_docx.getvalue()
                st.session_state.templates['briefkopf_docx'] = docx_bytes
                st.session_state.templates['briefkopf_filename'] = uploaded_docx.name
                st.success(f"✅ '{uploaded_docx.name}' wurde als Briefkopf-Vorlage gespeichert!")
                st.rerun()

        # Test-Bereich für Word-Vorlage
        if st.session_state.templates.get('briefkopf_docx'):
            st.divider()
            st.markdown("### 🧪 Word-Vorlage testen")

            all_cases = get_all_cases()
            if all_cases:
                case_options = [f"{c['nr']} - {c['debtor']}" for c in all_cases]
                test_case_docx = st.selectbox("Akte für Test wählen", case_options, key="test_case_docx")

                if st.button("📄 Word-Dokument generieren", type="primary", key="gen_docx"):
                    case_nr = test_case_docx.split(" - ")[0]
                    case = next((c for c in all_cases if c['nr'] == case_nr), None)
                    if case:
                        # Debug: Zeige Akten-Daten
                        with st.expander("📋 Debug: Akte-Daten"):
                            st.json({
                                'nr': case.get('nr'),
                                'creditor': case.get('creditor'),
                                'debtor': case.get('debtor'),
                                'creditor_address': case.get('creditor_address'),
                                'debtor_address': case.get('debtor_address'),
                                'principal': case.get('principal'),
                            })

                        result = generate_document_from_template(case)
                        if result:
                            debtor_name = case.get('debtor', 'Schuldner').split()[-1] if case.get('debtor') else 'Schuldner'
                            st.download_button(
                                "⬇️ Generiertes Dokument herunterladen",
                                data=result,
                                file_name=f"Schreiben_{case['nr'].replace('/', '-')}_{debtor_name}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                type="primary"
                            )
                            st.success("✅ Dokument wurde mit Aktendaten befüllt!")
                        else:
                            st.error("❌ Dokument konnte nicht generiert werden!")
                    else:
                        st.error(f"❌ Akte '{case_nr}' nicht gefunden!")

        st.divider()

        st.markdown("### 📝 Text-Briefkopf (Fallback)")
        st.caption("Wird verwendet wenn kein Word-Dokument hochgeladen wurde")
        briefkopf = st.text_area(
            "Briefkopf-Vorlage (Text)",
            value=st.session_state.templates.get('briefkopf', ''),
            height=150,
            key="tpl_briefkopf"
        )
        if st.button("💾 Text-Briefkopf speichern", key="save_briefkopf"):
            st.session_state.templates['briefkopf'] = briefkopf
            st.success("✅ Gespeichert!")

        st.divider()

        st.markdown("### E-Mail-Signatur")
        email_sig = st.text_area(
            "E-Mail-Signatur",
            value=st.session_state.templates.get('email_signatur', ''),
            height=150,
            key="tpl_email"
        )
        if st.button("💾 Signatur speichern", key="save_email"):
            st.session_state.templates['email_signatur'] = email_sig
            st.success("✅ Gespeichert!")

    with tab2:
        st.markdown("### Zahlungsaufforderung")
        st.caption("Platzhalter: [BRIEFKOPF], [DATUM], [SCHULDNER_NAME], [GLÄUBIGER], [FORDERUNG_GESAMT], etc.")

        zahlungsauff = st.text_area(
            "Vorlage Zahlungsaufforderung",
            value=st.session_state.templates.get('zahlungsaufforderung', ''),
            height=400,
            key="tpl_zahlung"
        )
        if st.button("💾 Vorlage speichern", key="save_zahlung"):
            st.session_state.templates['zahlungsaufforderung'] = zahlungsauff
            st.success("✅ Gespeichert!")

        st.divider()

        # Test mit Akte
        st.markdown("### 🧪 Vorlage testen")
        case_options = [f"{c['nr']} - {c['debtor']}" for c in DEMO_CASES]
        test_case_str = st.selectbox("Akte für Test", case_options, key="test_case")

        if st.button("📄 Dokument generieren", key="gen_zahlung"):
            case_nr = test_case_str.split(" - ")[0]
            case = next((c for c in DEMO_CASES if c['nr'] == case_nr), None)
            if case:
                s, h, o = get_balance(case['id'])
                doc = zahlungsauff
                doc = doc.replace('[BRIEFKOPF]', st.session_state.templates.get('briefkopf', ''))
                doc = doc.replace('[DATUM]', fmt_date(date.today()))
                doc = doc.replace('[SCHULDNER_NAME]', case['debtor'])
                doc = doc.replace('[SCHULDNER_ADRESSE]', case.get('debtor_address', ''))
                doc = doc.replace('[AKTENZEICHEN]', case['nr'])
                doc = doc.replace('[BETREFF]', case['subject'])
                doc = doc.replace('[GLÄUBIGER]', case['creditor'])
                doc = doc.replace('[FORDERUNG_GESAMT]', fmt_curr(o))
                doc = doc.replace('[HAUPTFORDERUNG]', fmt_curr(case['principal']))
                doc = doc.replace('[SIGNATUR]', st.session_state.templates.get('email_signatur', ''))
                doc = doc.replace('[BANKVERBINDUNG]', f"{st.session_state.kanzlei_daten['bank']}\nIBAN: {st.session_state.kanzlei_daten['iban']}")
                doc = doc.replace('[FRIST]', fmt_date(date.today() + timedelta(days=14)))
                doc = doc.replace('[ANREDE]', 'Frau' if case['debtor'].split()[0] in ['Anna', 'Maria', 'Lisa'] else 'Herr')

                st.text_area("Generiertes Dokument", value=doc, height=400)
                st.download_button(
                    "⬇️ Herunterladen",
                    data=doc.encode('utf-8'),
                    file_name=f"Zahlungsaufforderung_{case['nr'].replace('/', '-')}.txt",
                    mime="text/plain"
                )

    with tab3:
        st.markdown("### Klage-Vorlage")
        klage_vorlage = st.text_area(
            "Vorlage für Klagen",
            value=st.session_state.templates.get('klage_vorlage', ''),
            height=300,
            key="tpl_klage"
        )
        if st.button("💾 Klage-Vorlage speichern", key="save_klage"):
            st.session_state.templates['klage_vorlage'] = klage_vorlage
            st.success("✅ Gespeichert!")

        st.divider()

        st.markdown("### Schriftsatz-Vorlage")
        schriftsatz = st.text_area(
            "Vorlage für Schriftsätze",
            value=st.session_state.templates.get('schriftsatz_vorlage', ''),
            height=200,
            key="tpl_schrift"
        )
        if st.button("💾 Schriftsatz-Vorlage speichern", key="save_schrift"):
            st.session_state.templates['schriftsatz_vorlage'] = schriftsatz
            st.success("✅ Gespeichert!")

    with tab4:
        st.markdown("### 🏢 Kanzleidaten")

        col1, col2 = st.columns(2)
        with col1:
            kanzlei_name = st.text_input("Kanzleiname", value=st.session_state.kanzlei_daten.get('name', ''))
            kanzlei_adresse = st.text_area("Adresse", value=st.session_state.kanzlei_daten.get('adresse', ''), height=100)
            kanzlei_telefon = st.text_input("Telefon", value=st.session_state.kanzlei_daten.get('telefon', ''))
            kanzlei_fax = st.text_input("Fax", value=st.session_state.kanzlei_daten.get('fax', ''))
        with col2:
            kanzlei_email = st.text_input("E-Mail", value=st.session_state.kanzlei_daten.get('email', ''))
            kanzlei_bank = st.text_input("Bank", value=st.session_state.kanzlei_daten.get('bank', ''))
            kanzlei_iban = st.text_input("IBAN", value=st.session_state.kanzlei_daten.get('iban', ''))
            kanzlei_bic = st.text_input("BIC", value=st.session_state.kanzlei_daten.get('bic', ''))

        if st.button("💾 Kanzleidaten speichern", type="primary"):
            st.session_state.kanzlei_daten = {
                'name': kanzlei_name,
                'adresse': kanzlei_adresse,
                'telefon': kanzlei_telefon,
                'fax': kanzlei_fax,
                'email': kanzlei_email,
                'bank': kanzlei_bank,
                'iban': kanzlei_iban,
                'bic': kanzlei_bic
            }
            st.success("✅ Kanzleidaten gespeichert!")

# =============================================================================
# GLÄUBIGER DASHBOARD
# =============================================================================
def creditor_dashboard():
    # Ungelesene Nachrichten zählen
    unread = get_unread_count('glaeubigerin')
    notif_count = get_notification_count('glaeubigerin')

    with st.sidebar:
        st.markdown(f"### 💼 InkassoKom")
        st.caption(f"💼 {st.session_state.user['name']}")

        # Benachrichtigungsanzeige
        if unread > 0 or notif_count > 0:
            st.warning(f"📬 {unread} neue Nachrichten | 🔔 {notif_count} Benachrichtigungen")

        st.divider()
        if st.button("📊 Übersicht", use_container_width=True):
            st.session_state.page = 'dashboard'
            st.rerun()
        if st.button("💰 Forderungen", use_container_width=True):
            st.session_state.page = 'claims'
            st.rerun()

        # Posteingang mit Unread-Badge
        inbox_label = f"📬 Posteingang ({unread})" if unread > 0 else "📬 Posteingang"
        if st.button(inbox_label, use_container_width=True):
            st.session_state.page = 'messages'
            st.rerun()

        if st.button("✉️ Nachricht an Anwalt", use_container_width=True):
            st.session_state.page = 'compose'
            st.rerun()

        if st.button("💳 Zahlung melden", use_container_width=True):
            st.session_state.page = 'payment'
            st.rerun()
        if st.button("📄 Dokumente", use_container_width=True):
            st.session_state.page = 'docs'
            st.rerun()
        st.divider()
        if st.button("🚪 Abmelden", use_container_width=True):
            logout()
            st.rerun()

    page = st.session_state.page
    if page == 'claims': creditor_claims()
    elif page == 'messages': show_creditor_messages()
    elif page == 'compose': show_creditor_compose()
    elif page == 'payment': creditor_payment()
    elif page == 'docs': creditor_docs()
    else: creditor_overview()

def creditor_overview():
    st.markdown("## 💼 Gläubiger-Dashboard")
    st.write(f"Willkommen, {st.session_state.user['name']}!")

    total_claims = sum(c['principal'] for c in DEMO_CASES)
    total_open = sum(get_balance(c['id'])[2] for c in DEMO_CASES)

    c1, c2, c3 = st.columns(3)
    c1.metric("📁 Akten", len(DEMO_CASES))
    c2.metric("💰 Forderungen", fmt_curr(total_claims))
    c3.metric("📊 Offen", fmt_curr(total_open))

    st.divider()
    st.markdown("### 📁 Ihre Forderungen")

    for case in DEMO_CASES:
        s, h, o = get_balance(case['id'])
        with st.expander(f"**{case['nr']}** - {case['debtor']} ({fmt_curr(o)} offen)"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"Status: {case['status'].title()}")
                st.write(f"Mahnverfahren: {case['dunning'].replace('_', ' ').title()}")
            with c2:
                st.write(f"Hauptforderung: {fmt_curr(case['principal'])}")
                st.write(f"Bezahlt: {fmt_curr(h)}")
            if s > 0:
                st.progress(min(h/s, 1.0), text=f"{h/s*100:.1f}% bezahlt")

def creditor_claims():
    st.markdown("## 💰 Meine Forderungen")

    for case in DEMO_CASES:
        s, h, o = get_balance(case['id'])
        st.markdown(f"### {case['nr']} - {case['debtor']}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Hauptforderung", fmt_curr(case['principal']))
        c2.metric("Zinsen/Kosten", fmt_curr(s - case['principal']))
        c3.metric("Gezahlt", fmt_curr(h))
        c4.metric("Offen", fmt_curr(o))

        st.write(f"Status: {case['status'].title()} | Fällig seit: {fmt_date(case['due_date'])}")
        st.divider()

def creditor_payment():
    st.markdown("## 💳 Zahlung melden")
    st.info("Melden Sie Zahlungen, die Sie direkt erhalten haben.")

    with st.form("payment"):
        case_opts = [f"{c['nr']} - {c['debtor']}" for c in DEMO_CASES]
        selected = st.selectbox("Akte", case_opts)

        c1, c2 = st.columns(2)
        with c1:
            amount = st.number_input("Betrag (€)", min_value=0.0, step=10.0)
            p_date = st.date_input("Datum", value=date.today())
        with c2:
            method = st.selectbox("Zahlungsart", ["Überweisung", "Bar", "PayPal"])
            ref = st.text_input("Referenz")

        notes = st.text_area("Bemerkungen")

        if st.form_submit_button("📤 Zahlung melden", type="primary", use_container_width=True):
            if amount > 0:
                st.success(f"✅ Zahlung über {fmt_curr(amount)} gemeldet!")
                st.balloons()
            else:
                st.error("Bitte Betrag eingeben.")

def creditor_docs():
    st.markdown("## 📄 Dokumente")

    # Filter für Akten
    case_filter = st.selectbox(
        "Akte filtern",
        ["Alle Akten"] + [c['nr'] for c in DEMO_CASES],
        key="cred_doc_filter"
    )

    # Dokumente nach Akte gruppieren
    for case in DEMO_CASES:
        if case_filter != "Alle Akten" and case['nr'] != case_filter:
            continue

        docs = DEMO_DOCUMENTS.get(case['id'], [])
        if docs:
            st.markdown(f"### 📁 Akte {case['nr']} - {case['debtor']}")
            for doc in docs:
                show_document_viewer(doc, case['nr'], f"cred_{case['id']}")
            st.divider()

def show_creditor_messages():
    """Posteingang für Gläubiger mit Ereignis-Benachrichtigungen"""
    st.markdown("## 📬 Posteingang")

    tab1, tab2, tab3 = st.tabs(["📥 Nachrichten", "🔔 Aktenfortschritt", "📤 Gesendet"])

    with tab1:
        # Alle Nachrichten an Gläubiger
        all_messages = [m for m in st.session_state.messages + DEMO_MESSAGES if m['to_role'] == 'glaeubigerin']
        all_messages.sort(key=lambda x: x['date'], reverse=True)

        if not all_messages:
            st.info("Keine Nachrichten vorhanden")
        else:
            for msg in all_messages:
                case = next((c for c in DEMO_CASES if c['id'] == msg.get('case_id')), None)
                case_nr = case['nr'] if case else 'Allgemein'

                status_icon = "🔴" if not msg['read'] else "✅"
                with st.expander(f"{status_icon} **{msg['subject']}** - Von: {msg['from_name']} (Akte {case_nr}) - {msg['date'].strftime('%d.%m.%Y %H:%M')}"):
                    st.write(msg['content'])

                    # Anhänge anzeigen
                    if msg.get('attachments'):
                        st.markdown("### 📎 Anhänge")
                        for att_id in msg['attachments']:
                            st.write(f"📄 Dokument {att_id}")

                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💬 Antworten", key=f"cred_reply_{msg['id']}"):
                            st.session_state.cred_reply_to = msg
                            st.session_state.page = 'compose'
                            st.rerun()
                    with col2:
                        if st.button("✓ Als gelesen markieren", key=f"cred_read_{msg['id']}"):
                            msg['read'] = True
                            st.success("Als gelesen markiert")
                            st.rerun()

    with tab2:
        # Aktenfortschritt / Ereignisse für Gläubiger
        st.markdown("### 📋 Aktuelle Ereignisse zu Ihren Forderungen")

        all_events = st.session_state.case_events + DEMO_EVENTS
        all_events.sort(key=lambda x: x['date'], reverse=True)

        if not all_events:
            st.info("Keine Ereignisse vorhanden")
        else:
            for event in all_events:
                case = next((c for c in DEMO_CASES if c['id'] == event['case_id']), None)
                if case:
                    icon = "🔔" if not event.get('notified') else "✓"
                    event_icons = {
                        'zahlung': '💰',
                        'mahnbescheid': '⚖️',
                        'vb': '📋',
                        'pfueb': '📋',
                        'kommunikation': '💬',
                    }
                    e_icon = event_icons.get(event['type'], '📌')

                    st.markdown(f"{icon} {e_icon} **{case['nr']} - {case['debtor']}**")
                    st.write(event['desc'])
                    st.caption(event['date'].strftime('%d.%m.%Y %H:%M') if isinstance(event['date'], datetime) else str(event['date']))
                    st.divider()

    with tab3:
        # Gesendete Nachrichten
        sent = [m for m in st.session_state.messages if m.get('from_role') == 'glaeubigerin']
        sent.sort(key=lambda x: x['date'], reverse=True)

        if not sent:
            st.info("Keine gesendeten Nachrichten")
        else:
            for msg in sent:
                with st.expander(f"📤 **{msg['subject']}** - {msg['date'].strftime('%d.%m.%Y %H:%M')}"):
                    st.write(msg['content'])

def show_creditor_compose():
    """Nachricht an Anwalt verfassen (Gläubiger-Sicht)"""
    st.markdown("## ✉️ Nachricht an Anwalt")

    # Prüfen ob Antwort auf bestehende Nachricht
    reply_to = st.session_state.get('cred_reply_to')
    if reply_to:
        st.info(f"Antwort auf: {reply_to['subject']}")
        default_subject = f"Re: {reply_to['subject']}"
        default_case_id = reply_to.get('case_id', '')
    else:
        default_subject = ""
        default_case_id = ""

    # Akte auswählen
    case_options = [f"{c['nr']} - {c['debtor']}" for c in DEMO_CASES]
    if default_case_id:
        case = next((c for c in DEMO_CASES if c['id'] == default_case_id), None)
        default_idx = case_options.index(f"{case['nr']} - {case['debtor']}") if case else 0
    else:
        default_idx = 0

    selected_case = st.selectbox("Zu Akte", case_options, index=default_idx)
    case_nr = selected_case.split(" - ")[0]
    case = next((c for c in DEMO_CASES if c['nr'] == case_nr), None)

    subject = st.text_input("Betreff", value=default_subject)

    # Vorlagen für häufige Anfragen
    st.markdown("### 📝 Schnellauswahl")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📊 Sachstand anfragen", use_container_width=True):
            st.session_state.cred_compose_draft = f"""Sehr geehrte Damen und Herren,

ich bitte um Mitteilung des aktuellen Sachstands zur Akte {case['nr']} gegen {case['debtor']}.

Mit freundlichen Grüßen
{st.session_state.user['name']}"""
    with col2:
        if st.button("💰 Zahlung melden", use_container_width=True):
            st.session_state.cred_compose_draft = f"""Sehr geehrte Damen und Herren,

ich möchte mitteilen, dass ich eine Zahlung erhalten habe:

Akte: {case['nr']}
Schuldner: {case['debtor']}
Betrag: [Bitte eintragen]
Datum: {date.today().strftime('%d.%m.%Y')}

Mit freundlichen Grüßen
{st.session_state.user['name']}"""
    with col3:
        if st.button("❓ Allgemeine Frage", use_container_width=True):
            st.session_state.cred_compose_draft = f"""Sehr geehrte Damen und Herren,

ich habe eine Frage zu Akte {case['nr']}:

[Ihre Frage hier]

Mit freundlichen Grüßen
{st.session_state.user['name']}"""

    content = st.text_area(
        "Nachricht",
        value=st.session_state.get('cred_compose_draft', ''),
        height=300
    )

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 Nachricht senden", type="primary", use_container_width=True):
            if subject and content:
                send_message(
                    'glaeubigerin', st.session_state.user['name'],
                    'rechtsanwalt', 'Thomas Müller',
                    case['id'] if case else '', subject, content
                )
                st.success("✅ Nachricht gesendet!")
                st.session_state.cred_compose_draft = ''
                st.session_state.cred_reply_to = None
                st.rerun()
            else:
                st.error("Bitte Betreff und Nachricht eingeben")
    with col2:
        if st.button("❌ Abbrechen", use_container_width=True):
            st.session_state.cred_compose_draft = ''
            st.session_state.cred_reply_to = None
            st.session_state.page = 'dashboard'
            st.rerun()

# =============================================================================
# SCHULDNER DASHBOARD
# =============================================================================
def debtor_dashboard():
    # Ungelesene Nachrichten zählen
    unread = get_unread_count('schuldner')
    notif_count = get_notification_count('schuldner')

    with st.sidebar:
        st.markdown(f"### 👤 InkassoKom")
        st.caption(f"👤 {st.session_state.user['name']}")

        # Benachrichtigungsanzeige
        if unread > 0 or notif_count > 0:
            st.warning(f"📬 {unread} neue Nachrichten")

        st.divider()
        if st.button("📊 Übersicht", use_container_width=True):
            st.session_state.page = 'dashboard'
            st.rerun()
        if st.button("💰 Schulden", use_container_width=True):
            st.session_state.page = 'debts'
            st.rerun()

        # Posteingang mit Unread-Badge
        inbox_label = f"📬 Posteingang ({unread})" if unread > 0 else "📬 Posteingang"
        if st.button(inbox_label, use_container_width=True):
            st.session_state.page = 'messages'
            st.rerun()

        if st.button("📅 Ratenzahlung", use_container_width=True):
            st.session_state.page = 'installment'
            st.rerun()
        if st.button("📄 Dokumente", use_container_width=True):
            st.session_state.page = 'docs'
            st.rerun()
        if st.button("💬 Kontakt/Nachricht", use_container_width=True):
            st.session_state.page = 'contact'
            st.rerun()
        st.divider()
        if st.button("🚪 Abmelden", use_container_width=True):
            logout()
            st.rerun()

    page = st.session_state.page
    if page == 'debts': debtor_debts()
    elif page == 'messages': show_debtor_messages()
    elif page == 'installment': debtor_installment()
    elif page == 'docs': debtor_docs()
    elif page == 'contact': debtor_contact()
    else: debtor_overview()

def debtor_overview():
    st.markdown("## 📋 Schuldner-Übersicht")
    st.write(f"Guten Tag, {st.session_state.user['name']}.")

    case = DEMO_CASES[0]  # Demo: erster Fall
    s, h, o = get_balance(case['id'])

    st.metric("💰 Offener Betrag", fmt_curr(o))

    st.divider()
    st.markdown(f"### Akte {case['nr']}")
    st.write(f"**Gläubiger:** {case['creditor']}")
    st.write(f"**Betreff:** {case['subject']}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Gesamt", fmt_curr(s))
    c2.metric("Bezahlt", fmt_curr(h))
    c3.metric("Offen", fmt_curr(o))

    if s > 0:
        st.progress(min(h/s, 1.0), text=f"{h/s*100:.1f}% bezahlt")

    st.divider()
    st.info("**Hinweis:** Zahlen Sie nur auf das Kanzleikonto. Bei Fragen kontaktieren Sie uns.")

def debtor_debts():
    st.markdown("## 💰 Forderungsaufstellung")

    case = DEMO_CASES[0]
    s, h, o = get_balance(case['id'])
    bookings = DEMO_BOOKINGS.get(case['id'], [])

    st.markdown("### Forderungen (Soll)")
    for b in [x for x in bookings if x['type'] == 'S']:
        c1, c2, c3 = st.columns([2, 4, 2])
        c1.write(fmt_date(b['date']))
        c2.write(b['desc'])
        c3.write(f"**{fmt_curr(b['amount'])}**")

    st.markdown("### Zahlungen (Haben)")
    for b in [x for x in bookings if x['type'] == 'H']:
        c1, c2, c3 = st.columns([2, 4, 2])
        c1.write(fmt_date(b['date']))
        c2.write(b['desc'])
        c3.write(f"**-{fmt_curr(b['amount'])}**")

    st.divider()
    st.markdown(f"### Offener Betrag: {fmt_curr(o)}")

def debtor_installment():
    st.markdown("## 📅 Ratenzahlung beantragen")

    case = DEMO_CASES[0]
    s, h, o = get_balance(case['id'])
    st.info(f"Offener Betrag: **{fmt_curr(o)}**")

    with st.form("installment"):
        c1, c2 = st.columns(2)
        with c1:
            monthly = st.number_input("Monatliche Rate (€)", min_value=50.0, value=min(250.0, o), step=50.0)
            start = st.date_input("Erste Rate", value=date.today() + timedelta(14))
        with c2:
            num = int(o / monthly) + 1
            st.write(f"**Anzahl Raten:** {num}")
            st.write(f"**Letzte Rate:** {fmt_date(start + timedelta(days=30*num))}")

        reason = st.text_area("Begründung", placeholder="Ihre finanzielle Situation...")

        st.markdown("### Finanzielle Angaben")
        c1, c2 = st.columns(2)
        with c1:
            income = st.number_input("Nettoeinkommen (€)", min_value=0.0)
            job = st.selectbox("Status", ["Angestellt", "Selbstständig", "Arbeitslos", "Rentner"])
        with c2:
            expenses = st.number_input("Fixkosten (€)", min_value=0.0)
            dependents = st.number_input("Unterhaltsberechtigte", min_value=0)

        agree = st.checkbox("Angaben sind wahrheitsgemäß")

        if st.form_submit_button("📤 Antrag senden", type="primary", use_container_width=True):
            if agree and reason and monthly > 0:
                st.success("✅ Antrag eingereicht! Sie erhalten Nachricht.")
                st.balloons()
            else:
                st.error("Bitte alle Felder ausfüllen und bestätigen.")

def debtor_docs():
    st.markdown("## 📄 Dokumente")
    st.info("Hier finden Sie alle Dokumente zu Ihrer Forderung. Sie können diese ansehen, herunterladen oder teilen.")

    # Demo: Dokumente für case-001 (Schuldner-Sicht)
    case = DEMO_CASES[0]
    docs = DEMO_DOCUMENTS.get(case['id'], [])

    if docs:
        for doc in docs:
            show_document_viewer(doc, case['nr'], "debtor")
    else:
        st.info("Keine Dokumente vorhanden")

def show_debtor_messages():
    """Posteingang für Schuldner"""
    st.markdown("## 📬 Posteingang")

    tab1, tab2 = st.tabs(["📥 Nachrichten", "📤 Gesendet"])

    with tab1:
        # Alle Nachrichten an Schuldner
        all_messages = [m for m in st.session_state.messages + DEMO_MESSAGES if m['to_role'] == 'schuldner']
        all_messages.sort(key=lambda x: x['date'], reverse=True)

        if not all_messages:
            st.info("Keine Nachrichten vorhanden")
        else:
            for msg in all_messages:
                case = next((c for c in DEMO_CASES if c['id'] == msg.get('case_id')), None)
                case_nr = case['nr'] if case else 'Allgemein'

                status_icon = "🔴" if not msg['read'] else "✅"
                with st.expander(f"{status_icon} **{msg['subject']}** - Von: Kanzlei (Akte {case_nr}) - {msg['date'].strftime('%d.%m.%Y %H:%M')}"):
                    st.write(msg['content'])

                    # Anhänge anzeigen
                    if msg.get('attachments'):
                        st.markdown("### 📎 Anhänge")
                        for att_id in msg['attachments']:
                            # Dokument suchen und anzeigen
                            for c_id, docs in DEMO_DOCUMENTS.items():
                                for doc in docs:
                                    if doc['id'] == att_id:
                                        show_document_viewer(doc, case_nr, f"debt_att_{msg['id']}")

                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💬 Antworten", key=f"debt_reply_{msg['id']}"):
                            st.session_state.debt_reply_to = msg
                            st.session_state.page = 'contact'
                            st.rerun()
                    with col2:
                        if st.button("✓ Als gelesen markieren", key=f"debt_read_{msg['id']}"):
                            msg['read'] = True
                            st.success("Als gelesen markiert")
                            st.rerun()

    with tab2:
        # Gesendete Nachrichten
        sent = [m for m in st.session_state.messages if m.get('from_role') == 'schuldner']
        sent.sort(key=lambda x: x['date'], reverse=True)

        if not sent:
            st.info("Keine gesendeten Nachrichten")
        else:
            for msg in sent:
                with st.expander(f"📤 **{msg['subject']}** - {msg['date'].strftime('%d.%m.%Y %H:%M')}"):
                    st.write(msg['content'])

def debtor_contact():
    st.markdown("## 💬 Kontakt & Nachricht")

    st.info("""
    **Kanzlei Müller & Partner**
    Musterstraße 123, 10115 Berlin
    Tel: +49 30 123456
    E-Mail: info@kanzlei-mueller.de
    """)

    st.divider()

    # Prüfen ob Antwort auf bestehende Nachricht
    reply_to = st.session_state.get('debt_reply_to')
    if reply_to:
        st.info(f"Antwort auf: {reply_to['subject']}")
        default_subject = f"Re: {reply_to['subject']}"
    else:
        default_subject = ""

    # Demo: erster Fall gehört dem Schuldner
    case = DEMO_CASES[0]

    st.markdown("### ✉️ Nachricht an die Kanzlei")

    # Schnellvorlagen
    st.markdown("**Schnellauswahl:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📅 Ratenzahlung anfragen", use_container_width=True, key="debt_tpl_rate"):
            s, h, o = get_balance(case['id'])
            st.session_state.debt_compose_draft = f"""Sehr geehrte Damen und Herren,

ich möchte eine Ratenzahlung für die Forderung vereinbaren.

Akte: {case['nr']}
Offener Betrag: {fmt_curr(o)}
Gewünschte monatliche Rate: [Bitte angeben]

Meine finanzielle Situation erlaubt derzeit keine Einmalzahlung.

Mit freundlichen Grüßen
{st.session_state.user['name']}"""
    with col2:
        if st.button("❓ Frage zur Forderung", use_container_width=True, key="debt_tpl_frage"):
            st.session_state.debt_compose_draft = f"""Sehr geehrte Damen und Herren,

ich habe eine Frage zu meiner Forderung:

[Ihre Frage hier]

Mit freundlichen Grüßen
{st.session_state.user['name']}"""
    with col3:
        if st.button("🏠 Adressänderung", use_container_width=True, key="debt_tpl_addr"):
            st.session_state.debt_compose_draft = f"""Sehr geehrte Damen und Herren,

hiermit teile ich Ihnen meine neue Adresse mit:

Alte Adresse: [Bitte angeben]
Neue Adresse: [Bitte angeben]

Mit freundlichen Grüßen
{st.session_state.user['name']}"""

    st.divider()

    subject_options = ["Frage zur Forderung", "Zahlungsvereinbarung", "Ratenzahlungsantrag", "Adressänderung", "Widerspruch", "Sonstiges"]
    if reply_to:
        subject = st.text_input("Betreff", value=default_subject)
    else:
        subject = st.selectbox("Betreff", subject_options)

    message = st.text_area(
        "Nachricht",
        value=st.session_state.get('debt_compose_draft', ''),
        height=200
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 Nachricht senden", type="primary", use_container_width=True):
            if message:
                # Nachricht über das System senden
                send_message(
                    'schuldner', st.session_state.user['name'],
                    'rechtsanwalt', 'Thomas Müller',
                    case['id'], subject, message
                )
                st.success("✅ Nachricht gesendet! Sie erhalten eine Antwort in Ihrem Posteingang.")
                st.session_state.debt_compose_draft = ''
                st.session_state.debt_reply_to = None
                st.balloons()
            else:
                st.error("Bitte Nachricht eingeben.")
    with col2:
        if reply_to:
            if st.button("❌ Abbrechen", use_container_width=True):
                st.session_state.debt_reply_to = None
                st.session_state.debt_compose_draft = ''
                st.rerun()

# =============================================================================
# MAIN
# =============================================================================
if st.session_state.authenticated:
    role = st.session_state.user.get('role', '')
    if role == 'rechtsanwalt':
        lawyer_dashboard()
    elif role == 'glaeubigerin':
        creditor_dashboard()
    elif role == 'schuldner':
        debtor_dashboard()
    else:
        st.error("Unbekannte Rolle")
else:
    show_login()
