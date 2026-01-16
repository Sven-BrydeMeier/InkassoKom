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
    cover_text = _normalize_spaces(cover_text)

    # Aktenzeichen (Aktennr) + Kurzbezeichnung
    aktenzeichen = None
    m = re.search(r"Aktennr\.?:\s*([0-9]{3,5}/[0-9]{2})", cover_text)
    if m:
        aktenzeichen = m.group(1)
    if aktenzeichen is None:
        m2 = AZ_RE.search(cover_text)
        aktenzeichen = m2.group(1) if m2 else None

    # Kurzbezeichnung: häufig "X ./. Y"
    kurz = None
    m3 = re.search(r"([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\s\-\.]+?)\s*\./\.\s*([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\s\-\.]+?)(?:\s|\n|$)", cover_text)
    if m3:
        kurz = f"{m3.group(1).strip()} ./. {m3.group(2).strip()}"

    # Parteienblöcke
    auftraggeber_block = _extract_block(
        cover_text,
        "AUFTRAGGEBER",
        end_labels=["GEGNERVERTRETER", "GEGNER"],
    ) or ""

    gegner_block = _extract_block(
        cover_text,
        "GEGNER",
        end_labels=["GEGNERVERTRETER", "GEGENSTANDSWERT", "RECHTSSCHUTZ", "TERMINE", "FRISTEN", "Aktennr", "Aktenzeichen"],
    ) or ""

    # Auftraggeber (Mandant/Gläubiger)
    ag_name = _pick_name(auftraggeber_block, prefer=["GmbH", "mbH", "AG", "KG", "UG", "Reno", "Gesellschaft"])
    ag_street, ag_plz, ag_ort = _extract_address(auftraggeber_block)
    ag_contacts = _extract_contacts(auftraggeber_block)

    claimant = Party(
        rolle="Mandantin/Gläubigerin",
        name=ag_name,
        street=ag_street,
        plz=ag_plz,
        ort=ag_ort,
        telefon=ag_contacts["telefon"],
        mobil=ag_contacts["mobil"],
        fax=ag_contacts["fax"],
        email=ag_contacts["email"],
        raw=auftraggeber_block.strip() or None,
    )

    # Gegner (Schuldner)
    g_name = _pick_name(gegner_block, prefer=["Eheleute", "Herrn", "Frau", "Nikusch"])
    g_street, g_plz, g_ort = _extract_address(gegner_block)
    g_contacts = _extract_contacts(gegner_block)

    defendant = Party(
        rolle="Gegner/Schuldner",
        name=g_name,
        street=g_street,
        plz=g_plz,
        ort=g_ort,
        telefon=g_contacts["telefon"],
        mobil=g_contacts["mobil"],
        fax=g_contacts["fax"],
        email=g_contacts["email"],
        raw=gegner_block.strip() or None,
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
