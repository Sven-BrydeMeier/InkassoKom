"""
NotarFlow - Inkasso-Kommunikationsplattform
Vollständige Implementierung aller Funktionen
"""
import streamlit as st
from datetime import datetime, date, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(
    page_title="NotarFlow - Inkasso-Plattform",
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

# =============================================================================
# DEMO-DATEN
# =============================================================================
DEMO_CASES = [
    {
        'id': 'case-001', 'nr': '1-25', 'creditor': 'Mustermann GmbH', 'debtor': 'Max Schmidt',
        'subject': 'Offene Rechnung 2024-001', 'status': 'offen', 'dunning': 'nicht_beantragt',
        'enforcement': 'nicht_begonnen', 'principal': 5000.00, 'interest': 5.0,
        'due_date': date.today() - timedelta(days=60), 'created': datetime.now() - timedelta(days=65),
    },
    {
        'id': 'case-002', 'nr': '2-25', 'creditor': 'Mustermann GmbH', 'debtor': 'Hans Meier',
        'subject': 'Kaufpreisforderung', 'status': 'mahnverfahren', 'dunning': 'mb_zugestellt',
        'enforcement': 'nicht_begonnen', 'principal': 2500.00, 'interest': 5.0,
        'due_date': date.today() - timedelta(days=90), 'created': datetime.now() - timedelta(days=95),
        'mb_date': date.today() - timedelta(days=30), 'mb_delivered': date.today() - timedelta(days=14),
    },
    {
        'id': 'case-003', 'nr': '3-25', 'creditor': 'Mustermann GmbH', 'debtor': 'Anna Weber',
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
# LOGIN
# =============================================================================
def show_login():
    st.markdown("# ⚖️ NotarFlow")
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
        st.markdown(f"### ⚖️ NotarFlow")
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
    st.markdown("### 📁 Aktuelle Akten")

    for case in DEMO_CASES:
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
    st.warning("**Verjährung:** Akte 1-25 - Prüfung empfohlen")
    st.info("**Widerspruchsfrist:** Akte 2-25 - läuft in 7 Tagen ab")

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
        c1, c2, c3, c4 = st.columns(4)
        c1.button("📝 Mahnung", use_container_width=True)
        c2.button("⚖️ MB beantragen", use_container_width=True)
        c3.button("💳 Zahlung buchen", use_container_width=True)
        c4.button("📄 Upload", use_container_width=True)

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
        docs = [
            ("Rechnung_2024.pdf", "Rechnung", date.today() - timedelta(60)),
            ("Mahnung_1.pdf", "Mahnung", date.today() - timedelta(45)),
        ]
        for name, typ, d in docs:
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            c1.write(f"📄 {name}")
            c2.write(typ)
            c3.write(fmt_date(d))
            c4.button("⬇️", key=f"d_{name}")
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
        st.markdown(f"### 💼 NotarFlow")
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

    docs = [
        ("1-25", "Forderungsaufstellung.pdf", date.today()),
        ("1-25", "Mahnbescheid.pdf", date.today() - timedelta(14)),
        ("2-25", "Rechnung.pdf", date.today() - timedelta(90)),
    ]
    for case, name, d in docs:
        c1, c2, c3, c4 = st.columns([1.5, 3, 2, 1])
        c1.write(f"📁 {case}")
        c2.write(f"📄 {name}")
        c3.write(fmt_date(d))
        c4.button("⬇️", key=f"cd_{name}")
        st.divider()

# =============================================================================
# SCHULDNER DASHBOARD
# =============================================================================
def debtor_dashboard():
    with st.sidebar:
        st.markdown(f"### 👤 NotarFlow")
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

    docs = [
        ("Forderungsaufstellung.pdf", date.today()),
        ("Mahnbescheid.pdf", date.today() - timedelta(14)),
        ("Rechnung.pdf", date.today() - timedelta(60)),
    ]
    for name, d in docs:
        c1, c2, c3 = st.columns([4, 2, 1])
        c1.write(f"📄 {name}")
        c2.write(fmt_date(d))
        c3.button("⬇️", key=f"dd_{name}")
        st.divider()

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
