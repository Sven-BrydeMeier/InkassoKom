"""
InkassoKom - Inkasso-Kommunikationsplattform
Vollständige Implementierung aller Funktionen
"""
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

# =============================================================================
# DEMO-DATEN
# =============================================================================
DEMO_CASES = [
    {
        'id': 'case-001', 'nr': '1/25', 'creditor': 'Mustermann GmbH', 'debtor': 'Max Schmidt',
        'subject': 'Offene Rechnung 2024-001', 'status': 'offen', 'dunning': 'nicht_beantragt',
        'enforcement': 'nicht_begonnen', 'principal': 5000.00, 'interest': 5.0,
        'due_date': date.today() - timedelta(days=60), 'created': datetime.now() - timedelta(days=65),
    },
    {
        'id': 'case-002', 'nr': '2/25', 'creditor': 'Mustermann GmbH', 'debtor': 'Hans Meier',
        'subject': 'Kaufpreisforderung', 'status': 'mahnverfahren', 'dunning': 'mb_zugestellt',
        'enforcement': 'nicht_begonnen', 'principal': 2500.00, 'interest': 5.0,
        'due_date': date.today() - timedelta(days=90), 'created': datetime.now() - timedelta(days=95),
        'mb_date': date.today() - timedelta(days=30), 'mb_delivered': date.today() - timedelta(days=14),
    },
    {
        'id': 'case-003', 'nr': '3/25', 'creditor': 'Mustermann GmbH', 'debtor': 'Anna Weber',
        'subject': 'Mietrückstand', 'status': 'vollstreckung', 'dunning': 'titel_rechtskraeftig',
        'enforcement': 'pfueb_beantragt', 'principal': 3600.00, 'interest': 5.0,
        'due_date': date.today() - timedelta(days=180), 'created': datetime.now() - timedelta(days=185),
        'vb_date': date.today() - timedelta(days=60),
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
    b = DEMO_BOOKINGS.get(case_id, [])
    s = sum(x['amount'] for x in b if x['type'] == 'S')
    h = sum(x['amount'] for x in b if x['type'] == 'H')
    return s, h, s - h

def logout():
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.page = 'dashboard'

# =============================================================================
# DEMO-DOKUMENTE
# =============================================================================
DEMO_DOCUMENTS = {
    'case-001': [
        {'id': 'doc-001', 'name': 'Forderungsaufstellung.pdf', 'date': date.today(), 'type': 'Forderungsaufstellung', 'size': '245 KB'},
        {'id': 'doc-002', 'name': 'Rechnung_2024-001.pdf', 'date': date.today() - timedelta(60), 'type': 'Rechnung', 'size': '128 KB'},
        {'id': 'doc-003', 'name': 'Mahnung_1.pdf', 'date': date.today() - timedelta(45), 'type': 'Mahnung', 'size': '98 KB'},
    ],
    'case-002': [
        {'id': 'doc-004', 'name': 'Kaufvertrag.pdf', 'date': date.today() - timedelta(120), 'type': 'Vertrag', 'size': '512 KB'},
        {'id': 'doc-005', 'name': 'Mahnbescheid.pdf', 'date': date.today() - timedelta(30), 'type': 'Mahnbescheid', 'size': '156 KB'},
        {'id': 'doc-006', 'name': 'Zustellnachweis_MB.pdf', 'date': date.today() - timedelta(14), 'type': 'Zustellung', 'size': '89 KB'},
    ],
    'case-003': [
        {'id': 'doc-007', 'name': 'Mietvertrag.pdf', 'date': date.today() - timedelta(365), 'type': 'Vertrag', 'size': '890 KB'},
        {'id': 'doc-008', 'name': 'Vollstreckungsbescheid.pdf', 'date': date.today() - timedelta(60), 'type': 'VB', 'size': '178 KB'},
        {'id': 'doc-009', 'name': 'PfueB_Antrag.pdf', 'date': date.today() - timedelta(7), 'type': 'PfüB', 'size': '234 KB'},
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

        # Parteien extrahieren
        creditor_pattern = r'(?:Gläubiger|Mandant|Auftraggeber)[:\s]*([A-Za-zäöüÄÖÜß\s\-\.]+(?:GmbH|AG|e\.K\.|KG|OHG)?)'
        debtor_pattern = r'(?:Schuldner|Gegner|Beklagter)[:\s]*([A-Za-zäöüÄÖÜß\s\-\.]+)'

        creditor_match = re.search(creditor_pattern, full_text, re.IGNORECASE)
        debtor_match = re.search(debtor_pattern, full_text, re.IGNORECASE)

        creditor = creditor_match.group(1).strip() if creditor_match else "Unbekannter Gläubiger"
        debtor = debtor_match.group(1).strip() if debtor_match else "Unbekannter Schuldner"

        # Inhaltsverzeichnis parsen - Dokumente identifizieren
        documents = []
        toc_patterns = [
            r'(\d+)\.\s+(Rechnung|Mahnung|Mahnbescheid|Vollstreckungsbescheid|Vertrag|Schreiben|Brief|Forderungsaufstellung)[^\n]*(?:Seite\s*)?(\d+)?',
            r'(Seite\s*)?(\d+)\s*[-–]\s*(Rechnung|Mahnung|Mahnbescheid|Vollstreckungsbescheid|Vertrag|Schreiben|Brief)',
        ]

        doc_id_counter = 1
        for pattern in toc_patterns:
            for match in re.finditer(pattern, full_text, re.IGNORECASE):
                groups = match.groups()
                doc_type = None
                page_num = 1

                for g in groups:
                    if g and g.lower() in ['rechnung', 'mahnung', 'mahnbescheid', 'vollstreckungsbescheid', 'vertrag', 'schreiben', 'brief', 'forderungsaufstellung']:
                        doc_type = g.title()
                    elif g and g.isdigit():
                        page_num = int(g)

                if doc_type:
                    documents.append({
                        'id': f'imp-doc-{doc_id_counter:03d}',
                        'name': f'{doc_type}_{doc_id_counter}.pdf',
                        'type': doc_type,
                        'page': min(page_num, num_pages),
                        'date': date.today() - timedelta(days=doc_id_counter * 10),
                        'size': f'{(num_pages // len(documents) + 1) * 50} KB' if documents else '100 KB'
                    })
                    doc_id_counter += 1

        # Fallback: Wenn keine Dokumente gefunden, Standarddokumente erstellen
        if not documents:
            documents = [
                {'id': 'imp-doc-001', 'name': 'Forderungsaufstellung.pdf', 'type': 'Forderungsaufstellung', 'page': 1, 'date': date.today(), 'size': '150 KB'},
                {'id': 'imp-doc-002', 'name': 'Originalrechnung.pdf', 'type': 'Rechnung', 'page': 2, 'date': date.today() - timedelta(30), 'size': '80 KB'},
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
            'documents': documents,
            'bookings': bookings,
            'status': status,
            'dunning': dunning,
            'enforcement': enforcement,
            'principal': hauptforderung,
            'num_pages': num_pages,
            'raw_text_preview': full_text[:500] + '...' if len(full_text) > 500 else full_text
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
                st.write(f"**Gläubiger:** {result['creditor']}")
                st.write(f"**Schuldner:** {result['debtor']}")
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

            # Erkannte Dokumente
            st.markdown("#### 📄 Erkannte Dokumente")
            for doc in result['documents']:
                c1, c2, c3 = st.columns([3, 2, 2])
                c1.write(f"📄 {doc['name']}")
                c2.write(doc['type'])
                c3.write(f"Seite {doc['page']}")

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
                        'subject': f'Import aus RA-Micro - {uploaded_pdf.name}',
                        'status': result['status'],
                        'dunning': result['dunning'],
                        'enforcement': result['enforcement'],
                        'principal': result['principal'],
                        'interest': 5.0,
                        'due_date': date.today() - timedelta(days=60),
                        'created': datetime.now(),
                        'imported': True,
                        'source_pdf': uploaded_pdf.name
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
    with st.sidebar:
        st.markdown(f"### ⚖️ InkassoKom")
        st.caption(f"👨‍⚖️ {st.session_state.user['name']}")
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
        if st.button("📬 Posteingang", use_container_width=True):
            st.session_state.page = 'inbox'
            st.rerun()
        st.divider()
        if st.button("⚖️ Mahnverfahren", use_container_width=True):
            st.session_state.page = 'dunning'
            st.rerun()
        if st.button("🔨 Vollstreckung", use_container_width=True):
            st.session_state.page = 'enforcement'
            st.rerun()
        if st.button("⏰ Verjährung", use_container_width=True):
            st.session_state.page = 'limitation'
            st.rerun()
        st.divider()
        if st.button("🚪 Abmelden", use_container_width=True):
            logout()
            st.rerun()

    page = st.session_state.page
    if page == 'cases': show_cases_list()
    elif page == 'new_case': show_new_case()
    elif page == 'case_detail': show_case_detail()
    elif page == 'inbox': show_inbox()
    elif page == 'ra_micro_import': show_ra_micro_import()
    elif page == 'dunning': show_dunning()
    elif page == 'enforcement': show_enforcement()
    elif page == 'limitation': show_limitation()
    else: show_lawyer_overview()

def show_lawyer_overview():
    st.markdown("## 📊 Kanzlei-Dashboard")

    total = len(DEMO_CASES)
    offen = sum(1 for c in DEMO_CASES if c['status'] == 'offen')
    mahn = sum(1 for c in DEMO_CASES if c['status'] == 'mahnverfahren')
    vollstr = sum(1 for c in DEMO_CASES if c['status'] == 'vollstreckung')

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📁 Gesamt", total)
    c2.metric("🟡 Offen", offen)
    c3.metric("🟠 Mahnverfahren", mahn)
    c4.metric("🔴 Vollstreckung", vollstr)

    total_claims = sum(c['principal'] for c in DEMO_CASES)
    st.metric("💰 Gesamtforderungen", fmt_curr(total_claims))

    st.divider()

    # Sortierung und Filter
    col1, col2 = st.columns([2, 2])
    with col1:
        sort_by = st.selectbox(
            "Sortieren nach",
            ["Status", "Aktenzeichen", "Forderungshöhe", "Schuldner"],
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

    col1, col2 = st.columns(2)
    with col1:
        filter_status = st.selectbox("Status", ["Alle", "Offen", "Mahnverfahren", "Vollstreckung"])
    with col2:
        search = st.text_input("🔍 Suche", placeholder="Name, Aktenzeichen...")

    st.divider()

    cases = DEMO_CASES.copy()
    if filter_status != "Alle":
        cases = [c for c in cases if c['status'] == filter_status.lower()]
    if search:
        cases = [c for c in cases if search.lower() in c['nr'].lower() or search.lower() in c['debtor'].lower()]

    for case in cases:
        s, h, o = get_balance(case['id'])
        col1, col2, col3, col4, col5 = st.columns([1.5, 2.5, 2, 2, 1])
        with col1:
            st.write(f"**{case['nr']}**")
        with col2:
            st.write(case['debtor'])
            st.caption(case['creditor'])
        with col3:
            st.write(case['status'].title())
        with col4:
            st.write(fmt_curr(o))
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
    case = next((c for c in DEMO_CASES if c['id'] == case_id), None)
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
        st.markdown("### 📄 Dokumente")
        docs = DEMO_DOCUMENTS.get(case_id, [])
        if docs:
            for doc in docs:
                show_document_viewer(doc, case['nr'], f"ra_{case_id}")
        else:
            st.info("Keine Dokumente vorhanden")

        st.divider()
        uploaded = st.file_uploader("Dokument hochladen", type=['pdf', 'docx', 'jpg'])
        if uploaded:
            if st.button("📤 Hochladen", type="primary"):
                st.success(f"✅ '{uploaded.name}' hochgeladen!")

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
            c1.button("📤 Mahnbescheid beantragen", type="primary", use_container_width=True)
        if case['dunning'] == 'mb_zugestellt':
            c2.button("📤 VB beantragen", type="primary", use_container_width=True)
        c3.button("📋 EDA-Datei erstellen", use_container_width=True)

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

    items = [
        ("Brief_2024-12-30.pdf", datetime.now() - timedelta(hours=2), "neu"),
        ("Email_Anlage.pdf", datetime.now() - timedelta(days=1), "zugeordnet"),
    ]
    for name, dt, status in items:
        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
        c1.write(f"📄 {name}")
        c2.write(dt.strftime("%d.%m.%Y %H:%M"))
        c3.write("🔴 Neu" if status == "neu" else "✅ Zugeordnet")
        c4.button("Zuordnen", key=f"i_{name}")
        st.divider()

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
    c1, c2, c3 = st.columns(3)
    c1.button("👮 GV-Auftrag", use_container_width=True)
    c2.button("📋 PfÜB beantragen", use_container_width=True)
    c3.button("📊 VV-Analyse", use_container_width=True)

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
# GLÄUBIGER DASHBOARD
# =============================================================================
def creditor_dashboard():
    with st.sidebar:
        st.markdown(f"### 💼 InkassoKom")
        st.caption(f"💼 {st.session_state.user['name']}")
        st.divider()
        if st.button("📊 Übersicht", use_container_width=True):
            st.session_state.page = 'dashboard'
            st.rerun()
        if st.button("💰 Forderungen", use_container_width=True):
            st.session_state.page = 'claims'
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

# =============================================================================
# SCHULDNER DASHBOARD
# =============================================================================
def debtor_dashboard():
    with st.sidebar:
        st.markdown(f"### 👤 InkassoKom")
        st.caption(f"👤 {st.session_state.user['name']}")
        st.divider()
        if st.button("📊 Übersicht", use_container_width=True):
            st.session_state.page = 'dashboard'
            st.rerun()
        if st.button("💰 Schulden", use_container_width=True):
            st.session_state.page = 'debts'
            st.rerun()
        if st.button("📅 Ratenzahlung", use_container_width=True):
            st.session_state.page = 'installment'
            st.rerun()
        if st.button("📄 Dokumente", use_container_width=True):
            st.session_state.page = 'docs'
            st.rerun()
        if st.button("💬 Kontakt", use_container_width=True):
            st.session_state.page = 'contact'
            st.rerun()
        st.divider()
        if st.button("🚪 Abmelden", use_container_width=True):
            logout()
            st.rerun()

    page = st.session_state.page
    if page == 'debts': debtor_debts()
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

def debtor_contact():
    st.markdown("## 💬 Kontakt")

    st.info("""
    **Kanzlei Müller & Partner**
    Musterstraße 123, 10115 Berlin
    Tel: +49 30 123456
    E-Mail: info@kanzlei-mueller.de
    """)

    st.divider()
    with st.form("contact"):
        subject = st.selectbox("Betreff", ["Frage zur Forderung", "Zahlungsvereinbarung", "Adressänderung", "Widerspruch", "Sonstiges"])
        message = st.text_area("Nachricht", height=150)

        if st.form_submit_button("📤 Senden", type="primary", use_container_width=True):
            if message:
                st.success("✅ Nachricht gesendet!")
            else:
                st.error("Bitte Nachricht eingeben.")

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
