# parser_akten.py
"""
Parser für RA-Micro Aktenvorblätter und Inkasso-Akten.
Extrahiert Parteien, Verfahrensarten, Fristen, Beträge und Timeline.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


DATE_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
AZ_RE = re.compile(r"\b(\d{3,5}/\d{2})\b")
EUR_RE = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)(?:\s?€|\s*EUR)\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# sehr tolerant (DE-Festnetz + Mobil, mit Leerzeichen/Slash)
PHONE_RE = re.compile(r"\b0\d{1,5}(?:[ /-]?\d{2,}){2,}\b")
MOBILE_RE = re.compile(r"\b01\d{1,4}(?:[ /-]?\d{2,}){2,}\b")
PLZ_CITY_RE = re.compile(r"\b(\d{5})\s+([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß .-]+)\b")
STREET_RE = re.compile(
    r"\b([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß .-]+(?:straße|str\.|weg|platz|allee|ring|damm|gasse|berg|ufer))\s+(\d+[A-Za-z]?)\b",
    re.IGNORECASE,
)

COVER_KEYWORDS_ALL = ["GEGNER", "AUFTRAGGEBER"]
# zusätzliche Marker, um das Vorblatt sicher zu erkennen
COVER_KEYWORDS_ANY = ["Aktennr", "Aktenzeichen", "GEGENSTANDSWERT", "FRISTEN"]


@dataclass
class Party:
    rolle: str
    name: Optional[str] = None
    street: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    telefon: List[str] = None
    mobil: List[str] = None
    fax: List[str] = None
    email: List[str] = None
    raw: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # None -> [] für Listenfelder
        for k in ("telefon", "mobil", "fax", "email"):
            if d.get(k) is None:
                d[k] = []
        return d


def _parse_date(d: str) -> Optional[date]:
    m = DATE_RE.search(d)
    if not m:
        return None
    day, month, year = map(int, m.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _eur_to_float(s: str) -> float:
    # "13.469,00" -> 13469.0 ; "13.469" -> 13469.0 ; "14.861,34" -> 14861.34
    s = s.strip()
    s = s.replace(".", "").replace(" ", "")
    s = s.replace(",", ".")
    return float(s)


def _normalize_spaces(text: str) -> str:
    text = text.replace("\u00a0", " ")
    # mehrfachspaces reduzieren, aber Zeilen erhalten
    text = "\n".join(" ".join(line.split()) for line in text.splitlines())
    return text.strip()


def extract_pdf_text_pages(
    pdf_bytes: bytes,
    ocr: bool = False,
    ocr_dpi: int = 300,
    max_pages: Optional[int] = None,
) -> List[str]:
    """
    Extrahiert Text seitenweise. OCR ist optional und wird nur genutzt,
    wenn Tesseract verfügbar ist.
    """
    pages: List[str] = []

    # OCR optional vorbereiten
    do_ocr = False
    pytesseract = None
    if ocr:
        try:
            import pytesseract as _pyt
            pytesseract = _pyt
            do_ocr = True
        except Exception:
            do_ocr = False

    # Primär: pdfplumber verwenden
    if PDFPLUMBER_AVAILABLE:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                if max_pages is not None and i >= max_pages:
                    break

                txt = page.extract_text() or ""
                txt = _normalize_spaces(txt)

                # OCR-Fallback: wenn praktisch leer
                if do_ocr and len(txt) < 40:
                    try:
                        pil_img = page.to_image(resolution=ocr_dpi).original
                        ocr_txt = pytesseract.image_to_string(pil_img, lang="deu")
                        txt = _normalize_spaces(ocr_txt or "")
                    except Exception:
                        pass

                pages.append(txt)
    # Fallback: PyPDF2 verwenden
    elif PYPDF2_AVAILABLE:
        pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
        for i, page in enumerate(pdf_reader.pages):
            if max_pages is not None and i >= max_pages:
                break
            txt = page.extract_text() or ""
            txt = _normalize_spaces(txt)
            pages.append(txt)
    else:
        raise ImportError("Weder pdfplumber noch PyPDF2 ist installiert.")

    return pages


def find_cover_page_index(pages: List[str]) -> Optional[int]:
    # Suche zuerst am Ende (häufig dort)
    for idx in range(len(pages) - 1, -1, -1):
        t = pages[idx]
        if all(k in t for k in COVER_KEYWORDS_ALL) and any(k in t for k in COVER_KEYWORDS_ANY):
            return idx
    # Fallback: irgendwo im Dokument
    for idx, t in enumerate(pages):
        if all(k in t for k in COVER_KEYWORDS_ALL) and any(k in t for k in COVER_KEYWORDS_ANY):
            return idx
    return None


def _extract_block(text: str, start_label: str, end_labels: List[str]) -> Optional[str]:
    # sucht ab "start_label:" bis zum ersten end_label:
    # tolerant: Labels können in derselben Zeile stehen
    start = text.find(start_label)
    if start < 0:
        return None
    sub = text[start:]
    end_positions = []
    for el in end_labels:
        p = sub.find(el)
        if p > 0:
            end_positions.append(p)
    end = min(end_positions) if end_positions else len(sub)
    return sub[:end].strip()


def _pick_name(block: str, prefer: List[str]) -> Optional[str]:
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    # 1) bevorzugte Zeile
    for kw in prefer:
        for l in lines:
            if kw.lower() in l.lower():
                # oft steht rechts noch Tel/Fax -> abschneiden
                return l.split(" Tel")[0].split(" Mobil")[0].strip(" :")
    # 2) erste sinnvolle Zeile
    for l in lines:
        if len(l) >= 4 and not l.lower().startswith(("adressnr", "tel", "fax", "e-mail", "email")):
            return l.split(" Tel")[0].split(" Mobil")[0].strip(" :")
    return None


def _extract_address(block: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    street = None
    plz = None
    ort = None
    for line in block.splitlines():
        if street is None:
            m = STREET_RE.search(line)
            if m:
                street = f"{m.group(1)} {m.group(2)}"
        if plz is None:
            m2 = PLZ_CITY_RE.search(line)
            if m2:
                plz, ort = m2.group(1), m2.group(2).strip()
    return street, plz, ort


def _extract_contacts(block: str) -> Dict[str, List[str]]:
    emails = sorted(set(EMAIL_RE.findall(block)))
    phones = sorted(set(PHONE_RE.findall(block)))
    mobiles = sorted(set(MOBILE_RE.findall(block)))
    # Fax ist im Vorblatt oft nicht sauber erkennbar; heuristisch: Zeilen mit "Fax"
    fax = []
    for line in block.splitlines():
        if "fax" in line.lower():
            fax.extend(PHONE_RE.findall(line))
    fax = sorted(set(fax))
    # Mobilnummern aus phones entfernen (sonst doppelt)
    phones = [p for p in phones if p not in mobiles]
    return {"email": emails, "telefon": phones, "mobil": mobiles, "fax": fax}


def parse_cover_page(cover_text: str) -> Dict[str, Any]:
    """
    Parst ein RA-Micro Aktenvorblatt und extrahiert Parteien.

    RA-Micro Struktur:
    - AUFTRAGGEBER: ... Mandant-Daten (Firma, Adresse, Kontakt) ... GEGNERVERTRETER:
    - GEGNERVERTRETER: ... Gegner-Daten (Firma, Adresse, Kontakt) ...

    Der Mandant ist der Gläubiger, der Gegner ist der Schuldner.
    """
    cover_text = _normalize_spaces(cover_text)

    # Aktenzeichen (Aktennr) + Kurzbezeichnung
    aktenzeichen = None
    m = re.search(r"Aktennr\.?:\s*([0-9]{1,5}/[0-9]{2})", cover_text)
    if m:
        aktenzeichen = m.group(1)
    if aktenzeichen is None:
        m2 = AZ_RE.search(cover_text)
        aktenzeichen = m2.group(1) if m2 else None

    # Kurzbezeichnung: häufig "X ./. Y"
    kurz = None
    kurz_mandant = None
    kurz_gegner = None
    m3 = re.search(r"([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\s\-\.]+?)\s*\./\.\s*([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\s\-\.]+?)(?:\s|\n|$)", cover_text)
    if m3:
        kurz_mandant = m3.group(1).strip()
        kurz_gegner = m3.group(2).strip()
        kurz = f"{kurz_mandant} ./. {kurz_gegner}"

    # ============================================================
    # RA-MICRO STRUKTUR: Teile Text bei GEGNERVERTRETER
    # ============================================================
    # Alles VOR "GEGNERVERTRETER:" gehört zum MANDANT (Gläubiger)
    # Alles NACH "GEGNERVERTRETER:" gehört zum GEGNER (Schuldner)

    mandant_section = ""
    gegner_section = ""

    # Finde GEGNERVERTRETER Position
    gegnervertreter_pos = cover_text.find("GEGNERVERTRETER")
    if gegnervertreter_pos == -1:
        # Fallback: Suche nach "GEGNER:" (ohne VERTRETER)
        gegner_match = re.search(r'\bGEGNER\s*:', cover_text)
        if gegner_match:
            gegnervertreter_pos = gegner_match.start()

    if gegnervertreter_pos > 0:
        mandant_section = cover_text[:gegnervertreter_pos]
        gegner_section = cover_text[gegnervertreter_pos:]
    else:
        # Kein GEGNERVERTRETER gefunden - alles ist Mandant-Sektion
        mandant_section = cover_text

    # ============================================================
    # MANDANT/GLÄUBIGER EXTRAHIEREN
    # ============================================================
    # Suche Firma mit Rechtsform (GmbH, KG, etc.) in Mandant-Sektion
    legal_forms = r'(?:GmbH|mbH|AG|KG|OHG|UG|e\.?K\.?|Co\.\s*KG|& Co\.|Inc\.|Ltd\.|oHG|SE|eG)'

    # Pattern: Firmenname mit Rechtsform - nur innerhalb einer Zeile (keine Zeilenumbrüche)
    # [^\n] statt \s um Zeilenumbrüche auszuschließen
    firma_pattern = rf'([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß \t\-\.\&\,\"\']+\s*{legal_forms})'

    mandant_name = None
    mandant_firmen = re.findall(firma_pattern, mandant_section, re.IGNORECASE | re.MULTILINE)

    # Filtere ungültige Matches
    valid_firmen = []
    for firma in mandant_firmen:
        firma_clean = firma.strip()
        # Ignoriere wenn es ein Label ist (AUFTRAGGEBER matcht fälschlicherweise wegen "AG")
        firma_upper = firma_clean.upper()
        if any(label in firma_upper for label in ['AUFTRAGGEBER', 'GEGNER', 'RECHTSSCHUTZ', 'VERTRETER']):
            continue
        # Ignoriere wenn es "AUFTRAG" ist (Teil von AUFTRAGGEBER durch "AG"-Match)
        if firma_upper in ['AUFTRAG', 'AUFTRA', 'GEGNERVERT']:
            continue
        # Ignoriere wenn es Teil der Kurzbezeichnung ist (enthält ./.)
        if './.' in firma_clean:
            continue
        # Ignoriere zu kurze Namen (weniger als 5 Zeichen vor Rechtsform)
        name_part = re.sub(rf'\s*{legal_forms}.*$', '', firma_clean, flags=re.IGNORECASE).strip()
        if len(name_part) < 5:
            continue
        # Ignoriere wenn der Name aus der Kurzbezeichnung stammt (kurz_gegner am Anfang)
        if kurz_gegner and firma_clean.startswith(kurz_gegner):
            continue
        valid_firmen.append(firma_clean)

    if valid_firmen:
        # Nimm die erste gültige Firma (typischerweise der Mandant)
        mandant_name = valid_firmen[0].strip()
        # Bereinige: Entferne führende Sonderzeichen
        mandant_name = re.sub(r'^[\s\-\.\,\:]+', '', mandant_name)
        # Entferne Email-Domains die versehentlich mitgematcht wurden
        mandant_name = re.sub(r'^[a-zA-Z0-9\.\-\_]+@[a-zA-Z0-9\.\-]+\s*\n?\s*', '', mandant_name)
        mandant_name = re.sub(r'^[a-zA-Z0-9\.\-]+\.[a-z]{2,4}\s*\n?\s*', '', mandant_name)
        mandant_name = mandant_name.strip()

    # Fallback: Nutze Kurzbezeichnung
    if not mandant_name and kurz_mandant:
        # Suche vollständigen Namen basierend auf Kurzbezeichnung
        for firma in mandant_firmen if mandant_firmen else []:
            if kurz_mandant.lower() in firma.lower():
                mandant_name = firma.strip()
                break
        if not mandant_name:
            mandant_name = kurz_mandant

    # Extrahiere Adresse und Kontakte aus Mandant-Sektion
    mandant_street, mandant_plz, mandant_ort = _extract_address(mandant_section)
    mandant_contacts = _extract_contacts(mandant_section)

    claimant = Party(
        rolle="Mandantin/Gläubigerin",
        name=mandant_name,
        street=mandant_street,
        plz=mandant_plz,
        ort=mandant_ort,
        telefon=mandant_contacts["telefon"],
        mobil=mandant_contacts["mobil"],
        fax=mandant_contacts["fax"],
        email=mandant_contacts["email"],
        raw=mandant_section.strip() or None,
    )

    # ============================================================
    # GEGNER/SCHULDNER EXTRAHIEREN
    # ============================================================
    # Erweitertes Pattern für Firmen mit "& Co. KG" etc. (nur innerhalb einer Zeile)
    firma_pattern_full = rf'([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß \t\-\.\&\,\"\']+\s*{legal_forms}(?:\s*\&\s*Co\.?\s*KG)?)'

    gegner_name = None
    gegner_firmen = re.findall(firma_pattern_full, gegner_section, re.IGNORECASE | re.MULTILINE)

    # Filtere ungültige Matches
    valid_gegner_firmen = []
    for firma in gegner_firmen:
        firma_clean = firma.strip()
        # Ignoriere wenn es ein Label ist
        if any(label in firma_clean.upper() for label in ['AUFTRAGGEBER', 'GEGNERVERTRETER', 'RECHTSSCHUTZ']):
            continue
        # Ignoriere zu kurze Namen
        name_part = re.sub(rf'\s*{legal_forms}.*$', '', firma_clean, flags=re.IGNORECASE).strip()
        if len(name_part) < 3:
            continue
        valid_gegner_firmen.append(firma_clean)

    if valid_gegner_firmen:
        gegner_name = valid_gegner_firmen[0].strip()
        gegner_name = re.sub(r'^[\s\-\.\,\:]+', '', gegner_name)

    # Fallback: Suche nach Personennamen (Eheleute, Herrn, Frau)
    if not gegner_name:
        person_match = re.search(
            r'((?:Eheleute|Herrn|Frau)\s+[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\s\-\.]+?)(?:\n|$|geb\.|Tel|\d{5})',
            gegner_section, re.IGNORECASE
        )
        if person_match:
            gegner_name = person_match.group(1).strip()

    # Fallback: Nutze Kurzbezeichnung
    if not gegner_name and kurz_gegner:
        for firma in valid_gegner_firmen if valid_gegner_firmen else []:
            if kurz_gegner.lower() in firma.lower():
                gegner_name = firma.strip()
                break
        if not gegner_name:
            gegner_name = kurz_gegner

    # Extrahiere Adresse und Kontakte aus Gegner-Sektion
    gegner_street, gegner_plz, gegner_ort = _extract_address(gegner_section)
    gegner_contacts = _extract_contacts(gegner_section)

    defendant = Party(
        rolle="Gegner/Schuldner",
        name=gegner_name,
        street=gegner_street,
        plz=gegner_plz,
        ort=gegner_ort,
        telefon=gegner_contacts["telefon"],
        mobil=gegner_contacts["mobil"],
        fax=gegner_contacts["fax"],
        email=gegner_contacts["email"],
        raw=gegner_section.strip() or None,
    )

    return {
        "aktenzeichen": aktenzeichen,
        "aktenkurzbezeichnung": kurz,
        "claimant": claimant.to_dict(),
        "defendant": defendant.to_dict(),
    }


def detect_procedures(full_text: str) -> Dict[str, Any]:
    t = full_text.lower()
    found = {
        "aussergerichtlich": any(k in t for k in ["außergericht", "aussergericht", "letzte frist", "vergleichsangebot"]),
        "mahnverfahren": any(k in t for k in ["mahnverfahren", "mahnbescheid", "widerspruch"]),
        "vollstreckungsbescheid": "vollstreckungsbescheid" in t,
        "gerichtsverfahren": any(k in t for k in ["klage", "landgericht", "amtsgericht", "streitiges verfahren"]),
        "zwangsvollstreckung": any(k in t for k in ["zwangsvollstreck", "pfänd", "pfaend", "gerichtsvollzieher", "schuldnerverzeichnis"]),
    }

    unterverfahren = []
    if "pfänd" in t or "pfaend" in t:
        if "konto" in t:
            unterverfahren.append("Kontopfändung")
        if "drittschuldner" in t:
            unterverfahren.append("Drittschuldnerpfändung")
        if "sach" in t:
            unterverfahren.append("Sachpfändung")

    return {"arten": found, "unterverfahren": sorted(set(unterverfahren))}


def extract_timeline_and_deadlines(pages: List[str]) -> Dict[str, Any]:
    events = []
    deadlines = []
    interest_candidates = []

    for page_no, text in enumerate(pages, start=1):
        for line in text.splitlines():
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # Events: Zeilen beginnen oft mit Datum
            m = re.match(r"^(\d{1,2}\.\d{1,2}\.\d{4})\s*(.*)$", line_stripped)
            if m:
                d = _parse_date(m.group(1))
                if d:
                    events.append(
                        {
                            "datum": d.isoformat(),
                            "beschreibung": m.group(2).strip(" –-"),
                            "seite": page_no,
                        }
                    )

            # Fristen
            m2 = re.search(r"\bFrist\b.*?\b(?:bis|zum)\b\s*(\d{1,2}\.\d{1,2}\.\d{4})", line_stripped, re.IGNORECASE)
            if m2:
                d = _parse_date(m2.group(1))
                if d:
                    deadlines.append({"datum": d.isoformat(), "kontext": line_stripped, "seite": page_no})

            # Zins-Kandidaten (z. B. "15.06.2022/11.07.2022/20.07.2022")
            if "verzugszinsen" in line_stripped.lower() or "§ 288" in line_stripped:
                for dm in DATE_RE.finditer(line_stripped):
                    d = _parse_date(dm.group(0))
                    if d:
                        interest_candidates.append({"datum": d.isoformat(), "kontext": line_stripped, "seite": page_no})

    # Duplikate entfernen
    def _dedupe(items, key):
        seen = set()
        out = []
        for it in items:
            k = it[key]
            if k in seen:
                continue
            seen.add(k)
            out.append(it)
        return out

    return {
        "events": events,
        "deadlines": deadlines,
        "interest_candidates": _dedupe(interest_candidates, "datum"),
    }


def extract_amounts(full_text: str) -> Dict[str, Any]:
    """
    Sammelt Beträge mit Kontext und versucht Hauptforderung / Zahlungen zu klassifizieren.
    """
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]

    amounts = []
    for line in lines:
        for m in EUR_RE.finditer(line):
            amounts.append({"betrag": _eur_to_float(m.group(1)), "raw": m.group(0), "kontext": line})

    def pick_principal() -> Optional[Dict[str, Any]]:
        preferred_markers = ["gefordert", "klage über", "schadensersatz nach", "hauptforderung", "forderung"]
        for marker in preferred_markers:
            for a in amounts:
                if marker in a["kontext"].lower():
                    return a
        # fallback: größter Betrag, der nicht „Auftragswert" ist
        candidates = [a for a in amounts if "auftragswert" not in a["kontext"].lower()]
        if not candidates:
            return None
        return max(candidates, key=lambda x: x["betrag"])

    principal = pick_principal()

    payments = []
    for a in amounts:
        ctx = a["kontext"].lower()
        if any(k in ctx for k in ["zahlung", "gezahlt", "zahlbetrag", "bezahlt", "eingang"]):
            payments.append(a)
        if "anzahlung" in ctx:
            payments.append({**a, "hinweis": "Anzahlung (ggf. nur vereinbart)"})

    # grobe Fälligkeit-Kandidaten: Fristen + ggf. "Zahlung bis ..."
    due_candidates = []
    for a in amounts:
        if "bis" in a["kontext"].lower() and "€" in a["kontext"]:
            # Suche Datum in derselben Zeile
            dm = DATE_RE.search(a["kontext"])
            if dm:
                d = _parse_date(dm.group(0))
                if d:
                    due_candidates.append({"datum": d.isoformat(), "kontext": a["kontext"]})

    return {
        "principal": principal,
        "amounts": amounts,
        "payments": payments,
        "due_candidates": due_candidates,
    }


def calculate_simple_interest(
    principal_eur: float,
    start: date,
    end: date,
    annual_rate_percent: float,
) -> Dict[str, Any]:
    if end < start:
        start, end = end, start
    days = (end - start).days
    interest = principal_eur * (annual_rate_percent / 100.0) * (days / 365.0)
    return {"tage": days, "zinsbetrag": round(interest, 2), "zinssatz_pro_jahr": annual_rate_percent}


def extract_case_data(
    pdf_bytes: bytes,
    filename: Optional[str] = None,
    enable_ocr: bool = False,
) -> Dict[str, Any]:
    """
    Hauptfunktion: Extrahiert alle relevanten Daten aus einer Akten-PDF.

    Returns:
        Dict mit meta, cover, procedures, timeline, money
    """
    pages = extract_pdf_text_pages(pdf_bytes, ocr=enable_ocr)
    full_text = "\n".join(pages)

    cover_idx = find_cover_page_index(pages)
    cover_data = {}
    if cover_idx is not None:
        cover_data = parse_cover_page(pages[cover_idx])

    # optional: AZ aus Dateiname (z.B. "1299-25 ...")
    az_from_filename = None
    if filename:
        m = re.search(r"\b(\d{3,5})[-_/](\d{2})\b", filename)
        if m:
            az_from_filename = f"{m.group(1)}/{m.group(2)}"

    procedures = detect_procedures(full_text)
    timeline = extract_timeline_and_deadlines(pages)
    money = extract_amounts(full_text)

    return {
        "meta": {
            "filename": filename,
            "cover_page_index_0based": cover_idx,
            "aktenzeichen_from_filename": az_from_filename,
            "num_pages": len(pages),
        },
        "cover": cover_data,
        "procedures": procedures,
        "timeline": timeline,
        "money": money,
        "full_text": full_text,
        "pages": pages,
    }
