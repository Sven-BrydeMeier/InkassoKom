"""
PDF in Einzeldokumente zerlegen (heuristisch + optional OCR)

Strategie-Reihenfolge:
1) Bookmarks/Outline (wenn vorhanden)
2) Explizite Trenn-/Startsignale im Text (z.B. "Seite: 1", "Seite - 1 -")
3) Start-Muster (Regex) auf Text / OCR-Text
4) Manuelle Overrides

Angepasst für InkassoKom / RA-Micro Import.
"""

from __future__ import annotations

import io
import json
import os
import re
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Tuple, Dict, Any, Union

# PDF Processing
try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

from PyPDF2 import PdfReader, PdfWriter

# OCR Support (optional)
try:
    from PIL import Image
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


# =============================================================================
# DEFAULT PATTERNS für Inkasso/RA-Micro Dokumente
# =============================================================================
DEFAULT_PATTERNS = [
    # (label, regex, category)
    ("Mahnbescheid-Antrag", r"antrag\s+auf\s+erlass\s+eines\s+mahnbescheids", "gerichtlich"),
    ("Mahngericht-Mitteilung", r"mitteilung\s+des\s+mahngerichts", "gerichtlich"),
    ("Vollstreckungsbescheid-Antrag", r"antrag\s+auf\s+erlass\s+eines\s+vollstreckungsbescheides", "gerichtlich"),
    ("Vollstreckungsbescheid", r"vollstreckungsbescheid|\bamtsgericht\b.*\bbescheid\b", "gerichtlich"),
    ("Mahnbescheid", r"\bmahnbescheid\b", "gerichtlich"),
    ("PfÜB", r"pfändungs.*überweisungsbeschluss|pf[uü]b", "gerichtlich"),
    ("Zustellungsurkunde", r"zustellungsurkunde|zustellung.*urkunde", "gerichtlich"),
    ("Anwaltsschreiben", r"rechtsanw[aä]lt|kanzlei|radtke.*heigener|anwaltskanzlei", "aussergerichtlich"),
    ("Mahnung", r"\bmahnung\b|\d\.\s*mahnung|zahlungserinnerung", "aussergerichtlich"),
    ("Rechnung", r"\b(rechnungs[-\s]?nr|rechnung\s+nummer|rechnungsdatum)\b", "aussergerichtlich"),
    ("Lieferschein", r"\blieferschein\b", "aussergerichtlich"),
    ("Vertrag", r"\bvertrag\b|\bvereinbarung\b", "aussergerichtlich"),
    ("Vollmacht", r"\bvollmacht\b", "mandant"),
    ("Forderungskonto", r"forderungskonto|forderungsaufstellung", "intern"),
    ("Aktenvorblatt", r"aktenvorblatt|deckblatt|aktendeckblatt", "intern"),
    ("Inhaltsverzeichnis", r"inhaltsverzeichnis|inhalt\s*:", "intern"),
    ("Aktenblatt", r"^\s*gegner:|^\s*mandant:", "intern"),
    ("E-Mail", r"^von:\s|^from:\s|betreff:\s", "schuldner"),
    ("Schuldnerschreiben", r"sehr\s+geehrte.*herr|ratenzahlung|zahlungsvorschlag", "schuldner"),
]

# Indikator für "Seite: 1" bzw. "Seite - 1 -" (häufig: Start/Deckblatt)
DEFAULT_PAGE1_PATTERN = r"(?:^|\n)\s*(seite\s*-\s*1\s*-|seite\s*[:\-]\s*1\b)"

# Priorität für Label-Auswahl (stärkste zuerst)
LABEL_PRIORITY = [
    "Mahnbescheid-Antrag", "Mahngericht-Mitteilung", "Vollstreckungsbescheid-Antrag",
    "Vollstreckungsbescheid", "Mahnbescheid", "PfÜB", "Zustellungsurkunde",
    "Anwaltsschreiben", "E-Mail", "Rechnung", "Mahnung", "Lieferschein",
    "Vertrag", "Vollmacht", "Forderungskonto", "Aktenvorblatt", "Aktenblatt"
]

# Starke Start-Signale (erzwingen immer einen neuen Dokumentstart)
STRONG_START_LABELS = {
    "Mahnbescheid-Antrag", "Mahngericht-Mitteilung", "Vollstreckungsbescheid-Antrag",
    "Vollstreckungsbescheid", "Mahnbescheid", "PfÜB", "Zustellungsurkunde",
    "Anwaltsschreiben", "E-Mail", "Aktenblatt", "Aktenvorblatt", "Inhaltsverzeichnis"
}


@dataclass
class Segment:
    """Repräsentiert ein erkanntes Dokument-Segment."""
    start_page: int  # 1-basiert
    end_page: int    # 1-basiert, inklusiv
    pages: int
    title: str
    label: str
    category: str = "aussergerichtlich"
    confidence: float = 1.0
    ocr_used: bool = False
    file: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_document_dict(self, doc_id: str) -> Dict[str, Any]:
        """Konvertiert zu InkassoKom Dokument-Format."""
        from datetime import date
        return {
            'id': doc_id,
            'name': f"{self.title}.pdf",
            'type': self.label,
            'date': date.today().strftime('%d.%m.%Y'),
            'page': self.start_page,
            'end_page': self.end_page,
            'category': self.category,
            'size': f"{self.pages * 50} KB",  # Schätzung
            'confidence': self.confidence,
            'ocr_used': self.ocr_used,
        }


def sanitize_filename(name: str, maxlen: int = 90) -> str:
    """Bereinigt einen String für Dateinamen."""
    name = re.sub(r"[^\w\s\-\.,äöüÄÖÜß]+", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.replace(" ", "_")
    if len(name) > maxlen:
        name = name[:maxlen]
    return name or "Dokument"


class PDFSplitter:
    """
    Intelligenter PDF-Splitter mit OCR-Unterstützung.
    """

    def __init__(
        self,
        patterns: Optional[List[Tuple[str, str, str]]] = None,
        use_ocr: bool = True,
        ocr_dpi: int = 120,
        ocr_top_fraction: float = 0.35,
        min_text_chars: int = 60,
    ):
        """
        Args:
            patterns: Liste von (label, regex, category) Tupeln
            use_ocr: OCR für gescannte Seiten verwenden
            ocr_dpi: DPI für OCR-Rendering
            ocr_top_fraction: Anteil der Seite (oben) für schnelles OCR
            min_text_chars: Minimum Zeichen bevor OCR verwendet wird
        """
        self.patterns = patterns or DEFAULT_PATTERNS
        self.use_ocr = use_ocr and HAS_OCR and HAS_FITZ
        self.ocr_dpi = ocr_dpi
        self.ocr_top_fraction = ocr_top_fraction
        self.min_text_chars = min_text_chars

        # Kompilierte Patterns
        self._compiled_patterns = [
            (lbl, re.compile(rx, re.IGNORECASE | re.MULTILINE | re.DOTALL), cat)
            for lbl, rx, cat in self.patterns
        ]
        self._page1_pattern = re.compile(DEFAULT_PAGE1_PATTERN, re.IGNORECASE | re.MULTILINE)

    def _ocr_top_strip(self, page, dpi: int = 120, frac: float = 0.35) -> str:
        """Schnelles OCR nur im oberen Bereich der Seite."""
        if not HAS_OCR or not HAS_FITZ:
            return ""

        try:
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            w, h = img.size
            crop = img.crop((0, 0, w, int(h * frac)))
            return pytesseract.image_to_string(crop, lang="deu+eng", config="--psm 6")
        except Exception:
            return ""

    def _extract_text_with_ocr(self, page) -> Tuple[str, bool]:
        """
        Extrahiert Text, mit OCR-Fallback bei gescannten Seiten.

        Returns:
            (text, ocr_used)
        """
        base_text = page.get_text("text").strip()
        ocr_used = False

        if self.use_ocr and len(base_text) < self.min_text_chars:
            try:
                ocr_text = self._ocr_top_strip(page, self.ocr_dpi, self.ocr_top_fraction)
                if ocr_text:
                    base_text = base_text + "\n" + ocr_text
                    ocr_used = True
            except Exception:
                pass

        return base_text.strip(), ocr_used

    def _detect_labels(self, text: str) -> List[Tuple[str, str]]:
        """Erkennt alle passenden Labels im Text."""
        matches = []
        for label, compiled_re, category in self._compiled_patterns:
            if compiled_re.search(text):
                matches.append((label, category))
        return matches

    def _is_page1_marker(self, text: str) -> bool:
        """Prüft ob Text einen 'Seite 1' Marker enthält."""
        return bool(self._page1_pattern.search(text))

    def _extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extrahiert Metadaten wie Datum, Aktenzeichen, Rechnungsnummer."""
        metadata = {}

        # Datum
        m = re.search(r"\b(\d{2}\.\d{2}\.\d{2,4})\b", text)
        if m:
            metadata['date'] = m.group(1)

        # Rechnungsnummer
        m = re.search(r"rechnungs[-\s]?nr\.?\s*[:#]?\s*([0-9A-Z\-\/]+)", text, re.IGNORECASE)
        if m:
            metadata['invoice_nr'] = m.group(1)
        else:
            m = re.search(r"\bnummer\s*[:#]?\s*([0-9A-Z\-\/]+)", text, re.IGNORECASE)
            if m:
                metadata['invoice_nr'] = m.group(1)

        # Aktenzeichen
        m = re.search(r"\bAkte\s+(\d+\/\d+)", text)
        if m:
            metadata['case_nr'] = m.group(1)

        # Geschäftszeichen
        m = re.search(r"(geschäftszeichen|az\.?|unser\s+zeichen)\s*[:#]?\s*([0-9A-Z\-\/\.]+)", text, re.IGNORECASE)
        if m:
            metadata['reference'] = m.group(2)

        return metadata

    def _analyze_pages(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """Analysiert alle Seiten eines PDFs."""
        if not HAS_FITZ:
            # Fallback ohne PyMuPDF
            return self._analyze_pages_pypdf(pdf_bytes)

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []

        for i in range(len(doc)):
            page = doc[i]
            text, ocr_used = self._extract_text_with_ocr(page)
            norm_text = re.sub(r"\s+", " ", text.lower())
            labels = self._detect_labels(text)
            is_page1 = self._is_page1_marker(text)
            metadata = self._extract_metadata(text)

            pages.append({
                "index": i,
                "page_num": i + 1,
                "text": text,
                "norm_text": norm_text,
                "labels": labels,
                "is_page1": is_page1,
                "ocr_used": ocr_used,
                "metadata": metadata,
            })

        doc.close()
        return pages

    def _analyze_pages_pypdf(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """Fallback-Analyse ohne PyMuPDF (kein OCR)."""
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            norm_text = re.sub(r"\s+", " ", text.lower())
            labels = self._detect_labels(text)
            is_page1 = self._is_page1_marker(text)
            metadata = self._extract_metadata(text)

            pages.append({
                "index": i,
                "page_num": i + 1,
                "text": text,
                "norm_text": norm_text,
                "labels": labels,
                "is_page1": is_page1,
                "ocr_used": False,
                "metadata": metadata,
            })

        return pages

    def _is_start_page(self, page_info: Dict[str, Any]) -> bool:
        """Bestimmt ob eine Seite ein neues Dokument beginnt."""
        # Erste Seite ist immer Start
        if page_info["page_num"] == 1:
            return True

        # "Seite 1" Marker
        if page_info["is_page1"]:
            return True

        # Starke Labels
        labels = {lbl for lbl, cat in page_info["labels"]}
        if labels & STRONG_START_LABELS:
            return True

        # Lieferschein mit Metadaten
        if "Lieferschein" in labels:
            if re.search(r"\b(beleg[-\s]?nr|kunden[-\s]?nr|datum:)\b", page_info["norm_text"]):
                return True

        # Rechnung (auch via OCR erkannt)
        if "Rechnung" in labels:
            return True

        # OCR-Fallback: "rechnung" + "nummer" zusammen
        if page_info["ocr_used"]:
            if "rechnung" in page_info["norm_text"] and "nummer" in page_info["norm_text"]:
                return True

        return False

    def _get_primary_label(self, labels: List[Tuple[str, str]]) -> Tuple[str, str]:
        """Wählt das wichtigste Label nach Priorität."""
        label_set = {lbl: cat for lbl, cat in labels}

        for priority_label in LABEL_PRIORITY:
            if priority_label in label_set:
                return priority_label, label_set[priority_label]

        if labels:
            return labels[0]

        return "Dokument", "aussergerichtlich"

    def _build_title(self, label: str, metadata: Dict[str, Any]) -> str:
        """Erstellt einen aussagekräftigen Titel."""
        parts = [label]

        if 'case_nr' in metadata:
            parts.append(f"Akte {metadata['case_nr']}")
        if 'invoice_nr' in metadata:
            parts.append(f"Nr {metadata['invoice_nr']}")
        if 'reference' in metadata:
            parts.append(metadata['reference'])
        if 'date' in metadata:
            parts.append(metadata['date'])

        return " - ".join(parts)

    def split_by_bookmarks(self, pdf_bytes: bytes) -> Optional[List[Segment]]:
        """Teilt PDF anhand von Bookmarks/Outlines."""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            outlines = reader.outline
        except Exception:
            return None

        if not outlines:
            return None

        # Bookmarks flach machen
        flat: List[Tuple[str, int]] = []

        def walk(items):
            for item in items:
                if isinstance(item, list):
                    walk(item)
                else:
                    try:
                        title = getattr(item, 'title', None) or str(item)
                        page_idx = reader.get_destination_page_number(item)
                        flat.append((title, page_idx))
                    except Exception:
                        continue

        try:
            walk(outlines)
        except Exception:
            return None

        flat = sorted(set(flat), key=lambda x: x[1])
        if not flat:
            return None

        num_pages = len(reader.pages)
        segments: List[Segment] = []

        for idx, (title, start_idx) in enumerate(flat):
            start_page = start_idx + 1
            end_idx = flat[idx + 1][1] - 1 if idx + 1 < len(flat) else num_pages - 1
            end_page = end_idx + 1

            segments.append(Segment(
                start_page=start_page,
                end_page=end_page,
                pages=end_page - start_page + 1,
                title=title,
                label="Bookmark",
                category="aussergerichtlich",
                confidence=1.0,
            ))

        return segments

    def split_heuristic(self, pdf_bytes: bytes) -> List[Segment]:
        """Heuristische Dokumententrennung."""
        pages = self._analyze_pages(pdf_bytes)

        # Start-Seiten identifizieren
        start_indices = [p["index"] for p in pages if self._is_start_page(p)]
        start_indices = sorted(set(start_indices))

        if not start_indices:
            # Keine Trennung erkannt - gesamtes PDF als ein Dokument
            return [Segment(
                start_page=1,
                end_page=len(pages),
                pages=len(pages),
                title="Dokument",
                label="Dokument",
                category="aussergerichtlich",
            )]

        segments: List[Segment] = []

        for si, start_i in enumerate(start_indices):
            end_i = start_indices[si + 1] - 1 if si + 1 < len(start_indices) else len(pages) - 1
            start_page = pages[start_i]

            # Label und Kategorie bestimmen
            label, category = self._get_primary_label(start_page["labels"])

            # Titel erstellen
            title = self._build_title(label, start_page["metadata"])

            # Confidence basierend auf Erkennungsmethode
            confidence = 0.9 if start_page["ocr_used"] else 1.0
            if not start_page["labels"]:
                confidence = 0.7  # Nur Page1-Marker

            segments.append(Segment(
                start_page=start_i + 1,
                end_page=end_i + 1,
                pages=end_i - start_i + 1,
                title=title,
                label=label,
                category=category,
                confidence=confidence,
                ocr_used=start_page["ocr_used"],
                metadata=start_page["metadata"],
            ))

        return segments

    def split(self, pdf_bytes: bytes, mode: str = "auto") -> List[Segment]:
        """
        Hauptmethode zur Dokumententrennung.

        Args:
            pdf_bytes: PDF als Bytes
            mode: "auto", "bookmarks", oder "heuristic"

        Returns:
            Liste von Segment-Objekten
        """
        segments = None

        if mode in ("auto", "bookmarks"):
            segments = self.split_by_bookmarks(pdf_bytes)

            if mode == "bookmarks" and not segments:
                raise ValueError("Keine Bookmarks gefunden")

        if segments is None:
            segments = self.split_heuristic(pdf_bytes)

        return segments

    def extract_segment(self, pdf_bytes: bytes, segment: Segment) -> bytes:
        """Extrahiert ein Segment als eigenes PDF."""
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()

        for page_num in range(segment.start_page - 1, segment.end_page):
            writer.add_page(reader.pages[page_num])

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        return output.getvalue()

    def split_to_documents(
        self,
        pdf_bytes: bytes,
        case_id: str,
        mode: str = "auto"
    ) -> Tuple[List[Dict[str, Any]], Dict[str, bytes]]:
        """
        Teilt PDF und liefert InkassoKom-kompatible Dokumente.

        Returns:
            (documents_list, {doc_id: pdf_bytes})
        """
        segments = self.split(pdf_bytes, mode)

        documents = []
        doc_pdfs = {}

        for idx, segment in enumerate(segments, start=1):
            doc_id = f"{case_id}-doc-{idx:03d}"

            # Dokument-Dict für InkassoKom
            doc_dict = segment.to_document_dict(doc_id)
            documents.append(doc_dict)

            # PDF extrahieren
            doc_pdf = self.extract_segment(pdf_bytes, segment)
            doc_pdfs[doc_id] = doc_pdf

        return documents, doc_pdfs


# =============================================================================
# Convenience Functions
# =============================================================================

def split_pdf_intelligent(
    pdf_bytes: bytes,
    case_id: str = "case",
    use_ocr: bool = True,
    mode: str = "auto"
) -> Tuple[List[Dict[str, Any]], Dict[str, bytes]]:
    """
    Convenience-Funktion für intelligente PDF-Trennung.

    Args:
        pdf_bytes: PDF als Bytes
        case_id: Akten-ID für Dokument-IDs
        use_ocr: OCR verwenden (falls verfügbar)
        mode: "auto", "bookmarks", oder "heuristic"

    Returns:
        (documents_list, {doc_id: pdf_bytes})
    """
    splitter = PDFSplitter(use_ocr=use_ocr)
    return splitter.split_to_documents(pdf_bytes, case_id, mode)


def get_splitter_capabilities() -> Dict[str, bool]:
    """Gibt verfügbare Capabilities zurück."""
    return {
        "pymupdf": HAS_FITZ,
        "ocr": HAS_OCR,
        "full_support": HAS_FITZ and HAS_OCR,
    }
