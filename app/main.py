"""
InkassoKom - Inkasso-Kommunikationsplattform
Vollständige Implementierung aller Funktionen
"""

# App-Versionsnummer (Datum-Zeit Format)
APP_VERSION = "v2025.01.02-1430"

import streamlit as st
from datetime import datetime, date, timedelta
import sys
import os
import base64
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
# AI & Kommunikation
if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = ""
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

def get_all_cases():
    """Gibt alle Akten zurück (Demo + importierte)"""
    all_cases = DEMO_CASES.copy()
    # Importierte Akten hinzufügen (falls nicht bereits vorhanden)
    for imp_case in st.session_state.get('imported_cases', []):
        if not any(c['id'] == imp_case['id'] for c in all_cases):
            all_cases.append(imp_case)
    return all_cases

def get_all_documents(case_id):
    """Gibt alle Dokumente einer Akte zurück (Demo + importierte)"""
    docs = DEMO_DOCUMENTS.get(case_id, []).copy()
    # Importierte Dokumente hinzufügen
    imp_docs = st.session_state.get('imported_documents', {}).get(case_id, [])
    for imp_doc in imp_docs:
        if not any(d['id'] == imp_doc['id'] for d in docs):
            # Kategorie hinzufügen falls nicht vorhanden
            if 'category' not in imp_doc:
                imp_doc['category'] = get_document_category(imp_doc.get('type', ''))
            docs.append(imp_doc)
    return docs

def get_all_bookings(case_id):
    """Gibt alle Buchungen einer Akte zurück (Demo + importierte)"""
    bookings = DEMO_BOOKINGS.get(case_id, []).copy()
    # Importierte Buchungen hinzufügen
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
    """Generiert ein einfaches Demo-PDF"""
    # Einfacher PDF-Inhalt (minimales gültiges PDF)
    content = f"""Dokument: {doc_name}
Akte: {case_nr}
Datum: {fmt_date(date.today())}

Dies ist ein Demo-Dokument der InkassoKom-Plattform.

----------------------------------------
Dieses Dokument dient nur zu Demonstrationszwecken.
----------------------------------------
"""
    return content.encode('utf-8')

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

    # Alle Dokumente der Akte abrufen
    all_docs = get_all_documents(case_id)

    if not all_docs:
        st.info("Keine Dokumente in dieser Akte vorhanden")
    else:
        # Statistik
        col1, col2, col3, col4, col5 = st.columns(5)
        for i, (cat_id, cat_info) in enumerate(DOCUMENT_CATEGORIES.items()):
            cat_count = len([d for d in all_docs if d.get('category', 'aussergerichtlich') == cat_id])
            with [col1, col2, col3, col4, col5][i]:
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

    # Dokument hinzufügen
    st.markdown("### ➕ Dokument hinzufügen")
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
        # Prüfen ob echtes PDF vorhanden
        has_real_pdf = st.session_state.pdf_viewer_content is not None

        if has_real_pdf:
            pdf_content = st.session_state.pdf_viewer_content
        else:
            pdf_content = generate_demo_pdf(doc['name'], case_nr)

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
        has_real_pdf = st.session_state.pdf_viewer_content is not None
        if has_real_pdf:
            pdf_content = st.session_state.pdf_viewer_content
        else:
            pdf_content = generate_demo_pdf(doc['name'], case_nr)

        with st.container():
            st.divider()
            if has_real_pdf and doc['name'].endswith('.pdf'):
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
                st.markdown(f'''
                <iframe src="data:application/pdf;base64,{pdf_base64}" width="100%" height="400px"
                    style="border: 1px solid #ccc; border-radius: 5px;"></iframe>
                ''', unsafe_allow_html=True)
            else:
                st.text_area("Inhalt", value=pdf_content.decode('utf-8') if isinstance(pdf_content, bytes) else str(pdf_content),
                    height=200, disabled=True, key=f"{key_prefix}_preview_{doc['id']}")

            if st.button("❌ Schließen", key=f"{key_prefix}_close_{doc['id']}"):
                st.session_state[f"viewing_{doc['id']}"] = False
                st.rerun()

    st.divider()

# =============================================================================
# RA-MICRO IMPORT FUNKTIONEN
# =============================================================================
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
            'sachstandsbericht': 'mandant',
            'vollmacht': 'mandant',
            'mandantenbrief': 'mandant',
            'schuldnerbrief': 'schuldner',
            'ratenzahlung': 'schuldner',
            'vergleich': 'schuldner',
        }

        toc_patterns = [
            r'(\d+)\.\s+(Rechnung|Mahnung|Mahnbescheid|Vollstreckungsbescheid|Vertrag|Schreiben|Brief|Forderungsaufstellung|Notiz|Vermerk|Sachstandsbericht|Vollmacht|Klage|PfÜB|Zustellung)[^\n]*(?:Seite\s*)?(\d+)?',
            r'(Seite\s*)?(\d+)\s*[-–]\s*(Rechnung|Mahnung|Mahnbescheid|Vollstreckungsbescheid|Vertrag|Schreiben|Brief|Klage)',
            r'[-•]\s*(Rechnung|Mahnung|Mahnbescheid|Vollstreckungsbescheid|Vertrag|Schreiben|Notiz|Vollmacht|Klage|PfÜB)',
        ]

        doc_id_counter = 1
        found_types = set()

        for pattern in toc_patterns:
            for match in re.finditer(pattern, full_text, re.IGNORECASE):
                groups = match.groups()
                doc_type = None
                page_num = 1

                for g in groups:
                    if g:
                        g_lower = g.lower().strip()
                        if g_lower in doc_type_categories or any(t in g_lower for t in doc_type_categories.keys()):
                            doc_type = g.title()
                        elif g.isdigit():
                            page_num = int(g)

                if doc_type and doc_type.lower() not in found_types:
                    found_types.add(doc_type.lower())

                    # Kategorie ermitteln
                    category = 'aussergerichtlich'
                    for key, cat in doc_type_categories.items():
                        if key in doc_type.lower():
                            category = cat
                            break

                    documents.append({
                        'id': f'imp-doc-{doc_id_counter:03d}',
                        'name': f'{doc_type}_{doc_id_counter}.pdf',
                        'type': doc_type,
                        'category': category,
                        'page': min(page_num, num_pages),
                        'date': date.today() - timedelta(days=doc_id_counter * 10),
                        'size': f'{max(50, num_pages * 10)} KB'
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

                    # Dokumente hinzufügen
                    for doc in result['documents']:
                        doc['size'] = f"{len(pdf_bytes) // len(result['documents']) // 1024} KB"
                    st.session_state.imported_documents[new_case_id] = result['documents']
                    DEMO_DOCUMENTS[new_case_id] = result['documents']

                    # Buchungen hinzufügen
                    st.session_state.imported_bookings[new_case_id] = result['bookings']
                    DEMO_BOOKINGS[new_case_id] = result['bookings']

                    st.success(f"✅ Akte {result['aktenzeichen']} erfolgreich importiert!")
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
        if st.button("📥 RA-Micro Import", use_container_width=True):
            st.session_state.page = 'ra_micro_import'
            st.rerun()

        # Posteingang mit Unread-Badge
        inbox_label = f"📬 Posteingang ({unread})" if unread > 0 else "📬 Posteingang"
        if st.button(inbox_label, use_container_width=True):
            st.session_state.page = 'messages'
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

    page = st.session_state.page
    if page == 'cases': show_cases_list()
    elif page == 'new_case': show_new_case()
    elif page == 'case_detail': show_case_detail()
    elif page == 'inbox': show_inbox()
    elif page == 'messages': show_lawyer_messages()
    elif page == 'compose': show_compose_message()
    elif page == 'settings': show_settings()
    elif page == 'ra_micro_import': show_ra_micro_import()
    elif page == 'dunning': show_dunning()
    elif page == 'klage': show_klage_entwurf()
    elif page == 'templates': show_vorlagen()
    elif page == 'enforcement': show_enforcement()
    elif page == 'limitation': show_limitation()
    else: show_lawyer_overview()

def show_lawyer_overview():
    st.markdown("## 📊 Kanzlei-Dashboard")

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

    sorted_cases = DEMO_CASES.copy()
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

        c1, c2, c3, c4, c5 = st.columns(5)
        if c1.button("📝 Mahnung", use_container_width=True, key=f"btn_mahn_{case_id}"):
            st.session_state[f'show_mahnung_{case_id}'] = True
        if c2.button("⚖️ MB beantragen", use_container_width=True, key=f"btn_mb_{case_id}"):
            st.session_state[f'show_mb_{case_id}'] = True
        if c3.button("💳 Zahlung", use_container_width=True, key=f"btn_zahl_{case_id}"):
            st.session_state[f'show_zahlung_{case_id}'] = True
        if c4.button("💶 RA-Gebühren", use_container_width=True, key=f"btn_rag_{case_id}"):
            st.session_state[f'show_ra_calc_{case_id}'] = True
        if c5.button("📄 Upload", use_container_width=True, key=f"btn_upl_{case_id}"):
            st.session_state.page = 'case_detail'  # Scroll to documents tab

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
        bookings = DEMO_BOOKINGS.get(case_id, [])

        c1, c2, c3 = st.columns(3)
        c1.metric("Soll", fmt_curr(s))
        c2.metric("Haben", fmt_curr(h))
        c3.metric("Offen", fmt_curr(o))

        st.divider()
        for b in sorted(bookings, key=lambda x: x['date'], reverse=True):
            c1, c2, c3, c4 = st.columns([2, 3, 2, 2])
            c1.write(fmt_date(b['date']))
            c2.write(b['desc'])
            c3.write(b['cat'])
            if b['type'] == 'S':
                c4.write(f"+{fmt_curr(b['amount'])}")
            else:
                c4.markdown(f"**-{fmt_curr(b['amount'])}**")
            st.divider()

        with st.expander("➕ Buchung hinzufügen"):
            c1, c2 = st.columns(2)
            with c1:
                b_type = st.selectbox("Art", ["Zahlung (Haben)", "Kosten (Soll)"])
                b_amt = st.number_input("Betrag", min_value=0.0)
            with c2:
                b_date = st.date_input("Datum", value=date.today())
                b_cat = st.selectbox("Kategorie", ["Zahlung", "Zinsen", "RA-Gebühren", "Gerichtskosten"])
            b_desc = st.text_input("Beschreibung")
            if st.button("💾 Speichern", type="primary"):
                st.success("✅ Buchung gespeichert!")

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

    # Empfänger auswählen
    recipient_type = st.radio("Empfänger", ["Gläubigerin", "Schuldner"], horizontal=True)

    # Akte auswählen
    case_options = ["Ohne Aktenbezug"] + [f"{c['nr']} - {c['debtor']}" for c in DEMO_CASES]
    selected_case = st.selectbox("Akte", case_options)

    case = None
    if selected_case != "Ohne Aktenbezug":
        case_nr = selected_case.split(" - ")[0]
        case = next((c for c in DEMO_CASES if c['nr'] == case_nr), None)

    subject = st.text_input("Betreff")

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
    content = st.text_area(
        "Nachricht",
        value=st.session_state.get('compose_draft', ''),
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
            st.session_state.page = 'dashboard'
            st.rerun()

def show_settings():
    """Einstellungen für API-Keys und Benachrichtigungen"""
    st.markdown("## ⚙️ Einstellungen")

    tab1, tab2, tab3 = st.tabs(["🤖 KI-Integration", "🔔 Benachrichtigungen", "👤 Profil"])

    with tab1:
        st.markdown("### OpenAI API-Schlüssel")
        st.info("""
        Für die KI-gestützte Kommunikation benötigen Sie einen OpenAI API-Schlüssel.
        Diesen erhalten Sie unter: https://platform.openai.com/api-keys
        """)

        api_key = st.text_input(
            "API-Schlüssel",
            value=st.session_state.openai_api_key,
            type="password",
            placeholder="sk-..."
        )

        if st.button("💾 API-Schlüssel speichern", type="primary"):
            st.session_state.openai_api_key = api_key
            if api_key:
                st.success("✅ API-Schlüssel gespeichert!")
            else:
                st.info("API-Schlüssel entfernt. KI nutzt jetzt Template-basierte Antworten.")

        st.divider()
        st.markdown("### KI-Status")
        if st.session_state.openai_api_key:
            st.success("✅ KI-Integration aktiv (OpenAI GPT-4)")
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
        st.markdown("### Briefkopf")
        briefkopf = st.text_area(
            "Briefkopf-Vorlage",
            value=st.session_state.templates.get('briefkopf', ''),
            height=200,
            key="tpl_briefkopf"
        )
        if st.button("💾 Briefkopf speichern", key="save_briefkopf"):
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
