"""
AI Service - OpenAI Integration for Document Analysis and Suggestions
Optional AI Copilot functionality with strict human oversight
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
import json
import re

from sqlalchemy.orm import Session

from db.models import (
    Case, Claim, Document, InboxItem, User, AuditLog
)
from config.settings import settings


class AIService:
    """
    AI Copilot service for document classification, extraction, and suggestions.

    IMPORTANT: All AI outputs are suggestions only. Lawyer must approve all actions.

    Features:
    - Document classification
    - Data extraction (amounts, dates, IBANs, parties)
    - Case assignment suggestions
    - Response drafting
    - Action recommendations
    """

    # Document type classifications
    DOCUMENT_TYPES = [
        'rechnung',
        'mahnung',
        'schreiben_schuldner',
        'zahlungsbestaetigung',
        'einwand',
        'ratenwunsch',
        'adressaenderung',
        'widerspruch',
        'gerichtsdokument',
        'sonstiges'
    ]

    # Possible actions based on document type
    ACTION_SUGGESTIONS = {
        'rechnung': ['Forderung anlegen', 'Mahnung erstellen', 'Dem Mandanten zuordnen'],
        'mahnung': ['Status prüfen', 'Zahlungsfrist überwachen'],
        'schreiben_schuldner': ['Inhalt prüfen', 'Akte zuordnen', 'Antwort entwerfen'],
        'zahlungsbestaetigung': ['Zahlung verbuchen', 'Forderungskonto aktualisieren'],
        'einwand': ['Einwand prüfen', 'Mandant informieren', 'Stellungnahme entwerfen'],
        'ratenwunsch': ['Ratenplan erstellen', 'Mandant konsultieren'],
        'adressaenderung': ['Adresse aktualisieren', 'Zustelladresse prüfen'],
        'widerspruch': ['Mahnverfahren prüfen', 'Streitiges Verfahren vorbereiten'],
        'gerichtsdokument': ['Status aktualisieren', 'Fristen prüfen'],
        'sonstiges': ['Manuell prüfen', 'Kategorie festlegen'],
    }

    def __init__(self, db: Session):
        self.db = db
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize OpenAI client if API key is available."""
        if settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except ImportError:
                self.client = None

    def is_available(self) -> bool:
        """Check if AI service is available."""
        return self.client is not None

    # =========================================================================
    # DOCUMENT CLASSIFICATION
    # =========================================================================

    def classify_document(
        self,
        document_id: UUID,
        text_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Classify a document and extract key information.
        Returns classification, confidence, and extracted data.
        """
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return {"error": "Document not found"}

        text = text_content or document.ocr_text
        if not text:
            return {"error": "No text content available"}

        if not self.is_available():
            # Fallback to rule-based classification
            return self._classify_by_rules(text, document.filename)

        try:
            result = self._classify_with_ai(text, document.filename)

            # Store results in document
            document.ai_classification = result
            self.db.commit()

            return result

        except Exception as e:
            # Fallback on error
            return self._classify_by_rules(text, document.filename)

    def _classify_with_ai(self, text: str, filename: str) -> Dict[str, Any]:
        """Classify document using OpenAI API."""
        prompt = f"""Analysiere folgendes Dokument aus einem Inkasso-/Mahnverfahren.

Dokumentname: {filename}
Dokumentinhalt (erste 3000 Zeichen):
{text[:3000]}

Bitte klassifiziere das Dokument und extrahiere relevante Informationen.

Antworte NUR im JSON-Format:
{{
    "document_type": "einer von: rechnung, mahnung, schreiben_schuldner, zahlungsbestaetigung, einwand, ratenwunsch, adressaenderung, widerspruch, gerichtsdokument, sonstiges",
    "confidence": 0.0-1.0,
    "summary": "kurze Zusammenfassung (1-2 Sätze)",
    "extracted_data": {{
        "amounts": [{"betrag": 123.45, "beschreibung": "..."}],
        "dates": [{"datum": "2024-01-15", "bedeutung": "..."}],
        "ibans": ["DE89370400440532013000"],
        "parties": [{"name": "...", "rolle": "gläubiger/schuldner/bank/arbeitgeber"}],
        "aktenzeichen": "falls vorhanden",
        "forderungsgrund": "falls erkennbar"
    }},
    "suggested_actions": ["Aktion 1", "Aktion 2"],
    "requires_lawyer_review": true/false,
    "urgency": "niedrig/normal/hoch/kritisch"
}}"""

        response = self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Du bist ein Assistent für eine Rechtsanwaltskanzlei, spezialisiert auf Inkasso und Mahnverfahren. Antworte immer im angeforderten JSON-Format."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )

        result_text = response.choices[0].message.content

        # Parse JSON from response
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(result_text)
        except json.JSONDecodeError:
            result = {
                "document_type": "sonstiges",
                "confidence": 0.5,
                "summary": "Automatische Klassifizierung fehlgeschlagen",
                "requires_lawyer_review": True
            }

        return result

    def _classify_by_rules(self, text: str, filename: str) -> Dict[str, Any]:
        """Rule-based fallback classification."""
        text_lower = text.lower()
        filename_lower = filename.lower()

        # Check for document types
        if any(w in text_lower for w in ['rechnung', 'invoice', 'rechnungsnummer']):
            doc_type = 'rechnung'
            confidence = 0.7
        elif any(w in text_lower for w in ['mahnung', 'zahlungserinnerung', 'letzte mahnung']):
            doc_type = 'mahnung'
            confidence = 0.7
        elif any(w in text_lower for w in ['widerspruch', 'widerspreche']):
            doc_type = 'widerspruch'
            confidence = 0.8
        elif any(w in text_lower for w in ['ratenzahlung', 'raten', 'teilzahlung']):
            doc_type = 'ratenwunsch'
            confidence = 0.7
        elif any(w in text_lower for w in ['zahlung erhalten', 'überwiesen', 'gezahlt']):
            doc_type = 'zahlungsbestaetigung'
            confidence = 0.6
        elif any(w in text_lower for w in ['amtsgericht', 'beschluss', 'mahnbescheid', 'vollstreckung']):
            doc_type = 'gerichtsdokument'
            confidence = 0.8
        elif any(w in text_lower for w in ['einspruch', 'nicht anerkenn', 'bestreite']):
            doc_type = 'einwand'
            confidence = 0.6
        elif any(w in text_lower for w in ['neue adresse', 'umgezogen', 'adressänderung']):
            doc_type = 'adressaenderung'
            confidence = 0.7
        else:
            doc_type = 'sonstiges'
            confidence = 0.3

        # Extract amounts
        amounts = []
        amount_pattern = r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))\s*(?:€|EUR|Euro)'
        for match in re.finditer(amount_pattern, text, re.IGNORECASE):
            amount_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                amounts.append({"betrag": float(amount_str), "beschreibung": "Betrag"})
            except ValueError:
                pass

        # Extract IBANs
        iban_pattern = r'[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}'
        ibans = list(set(re.findall(iban_pattern, text.upper())))

        # Extract dates
        dates = []
        date_pattern = r'(\d{1,2})[./](\d{1,2})[./](\d{2,4})'
        for match in re.finditer(date_pattern, text):
            day, month, year = match.groups()
            if len(year) == 2:
                year = '20' + year
            dates.append({"datum": f"{year}-{month.zfill(2)}-{day.zfill(2)}", "bedeutung": "Datum"})

        return {
            "document_type": doc_type,
            "confidence": confidence,
            "summary": f"Automatisch als '{doc_type}' klassifiziert (Regelbasiert)",
            "extracted_data": {
                "amounts": amounts[:5],  # Limit to first 5
                "dates": dates[:5],
                "ibans": ibans[:3],
                "parties": []
            },
            "suggested_actions": self.ACTION_SUGGESTIONS.get(doc_type, []),
            "requires_lawyer_review": True,
            "urgency": "normal",
            "method": "rule_based"
        }

    # =========================================================================
    # CASE ASSIGNMENT SUGGESTIONS
    # =========================================================================

    def suggest_case_assignment(
        self,
        document_id: UUID,
        organization_id: UUID,
        text_content: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest which case a document should be assigned to.
        Returns top 3 case suggestions with confidence scores.
        """
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return []

        text = text_content or document.ocr_text or document.original_filename
        if not text:
            return []

        # Get all active cases for the organization
        cases = self.db.query(Case).filter(
            Case.organization_id == organization_id,
            Case.is_deleted == False,
            Case.status.notin_(['abgeschlossen', 'uneinbringlich'])
        ).all()

        if not cases:
            return []

        suggestions = []

        for case in cases:
            score = self._calculate_case_match_score(text, case)
            if score > 0:
                suggestions.append({
                    "case_id": str(case.id),
                    "internal_number": case.internal_number,
                    "creditor_name": case.creditor_name,
                    "debtor_name": case.debtor_name,
                    "subject": case.subject,
                    "score": score,
                    "match_reasons": self._get_match_reasons(text, case)
                })

        # Sort by score and return top 3
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions[:3]

    def _calculate_case_match_score(self, text: str, case: Case) -> float:
        """Calculate match score between document text and case."""
        text_lower = text.lower()
        score = 0.0

        # Check for case number
        if case.internal_number and case.internal_number.lower() in text_lower:
            score += 0.4
        if case.external_number and case.external_number.lower() in text_lower:
            score += 0.4
        if case.court_file_number and case.court_file_number.lower() in text_lower:
            score += 0.5

        # Check for party names
        if case.creditor_name and case.creditor_name.lower() in text_lower:
            score += 0.3
        if case.debtor_name and case.debtor_name.lower() in text_lower:
            score += 0.4

        # Check for addresses
        if case.debtor_street and case.debtor_street.lower() in text_lower:
            score += 0.2
        if case.debtor_postal_code and case.debtor_postal_code in text:
            score += 0.15

        # Check claims
        claims = self.db.query(Claim).filter(Claim.case_id == case.id).all()
        for claim in claims:
            if claim.invoice_number and claim.invoice_number.lower() in text_lower:
                score += 0.35
            if claim.contract_number and claim.contract_number.lower() in text_lower:
                score += 0.35

        return min(score, 1.0)  # Cap at 1.0

    def _get_match_reasons(self, text: str, case: Case) -> List[str]:
        """Get reasons why a case matches a document."""
        text_lower = text.lower()
        reasons = []

        if case.internal_number and case.internal_number.lower() in text_lower:
            reasons.append(f"Aktennummer '{case.internal_number}' gefunden")
        if case.court_file_number and case.court_file_number.lower() in text_lower:
            reasons.append(f"Gerichtsaktenzeichen gefunden")
        if case.debtor_name and case.debtor_name.lower() in text_lower:
            reasons.append(f"Schuldnername '{case.debtor_name}' gefunden")
        if case.creditor_name and case.creditor_name.lower() in text_lower:
            reasons.append(f"Gläubigername gefunden")

        return reasons

    # =========================================================================
    # RESPONSE DRAFTING
    # =========================================================================

    def draft_response(
        self,
        case_id: UUID,
        document_id: Optional[UUID] = None,
        context: Optional[str] = None,
        response_type: str = "antwort"
    ) -> Dict[str, Any]:
        """
        Draft a response letter based on case context.

        response_type: antwort, mahnung, ratenzahlung, einwandserwiderung
        """
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {"error": "Case not found"}

        # Build context
        case_context = self._build_case_context(case)

        if document_id:
            doc = self.db.query(Document).filter(Document.id == document_id).first()
            if doc and doc.ocr_text:
                case_context += f"\n\nEingangsdokument:\n{doc.ocr_text[:2000]}"

        if context:
            case_context += f"\n\nZusätzlicher Kontext:\n{context}"

        if not self.is_available():
            return {
                "draft": self._generate_template_response(case, response_type),
                "requires_review": True,
                "method": "template"
            }

        try:
            return self._draft_with_ai(case_context, response_type, case)
        except Exception as e:
            return {
                "draft": self._generate_template_response(case, response_type),
                "requires_review": True,
                "method": "template",
                "error": str(e)
            }

    def _draft_with_ai(self, context: str, response_type: str, case: Case) -> Dict[str, Any]:
        """Draft response using AI."""
        type_prompts = {
            "antwort": "Erstelle ein höfliches aber bestimmtes Antwortschreiben.",
            "mahnung": "Erstelle ein Mahnschreiben mit Fristsetzung.",
            "ratenzahlung": "Erstelle einen Vorschlag für eine Ratenzahlungsvereinbarung.",
            "einwandserwiderung": "Erstelle eine sachliche Erwiderung auf den Einwand des Schuldners.",
        }

        prompt = f"""Du bist Assistent in einer Rechtsanwaltskanzlei (Inkasso).

Aktenkontext:
{context}

Aufgabe: {type_prompts.get(response_type, type_prompts['antwort'])}

Anforderungen:
- Professioneller, rechtlich korrekter Ton
- Korrekte Anrede und Grußformel
- Alle relevanten Fakten einbeziehen
- Keine rechtlichen Zusicherungen ohne Prüfung
- Platzhalter für variable Daten mit [PLATZHALTER] markieren

Erstelle den Entwurf:"""

        response = self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Du bist ein erfahrener Rechtsanwaltsassistent für Inkasso und Forderungsmanagement."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=2000
        )

        draft = response.choices[0].message.content

        return {
            "draft": draft,
            "response_type": response_type,
            "requires_review": True,
            "method": "ai",
            "warning": "WICHTIG: Dieser Entwurf muss vom Rechtsanwalt geprüft und freigegeben werden."
        }

    def _generate_template_response(self, case: Case, response_type: str) -> str:
        """Generate a template-based response."""
        templates = {
            "antwort": f"""Sehr geehrte/r [ANREDE],

in der Angelegenheit

{case.creditor_name} ./. {case.debtor_name}
unser Zeichen: {case.internal_number}

nehmen wir Bezug auf Ihr Schreiben vom [DATUM].

[INHALT]

Mit freundlichen Grüßen

[UNTERSCHRIFT]
Rechtsanwalt""",

            "mahnung": f"""Sehr geehrte/r {case.debtor_name},

in vorbezeichneter Angelegenheit müssen wir Sie erneut auffordern, die offene Forderung unserer Mandantschaft

{case.creditor_name}

in Höhe von [BETRAG] EUR

bis spätestens zum [DATUM] zu begleichen.

Sollte bis zu diesem Termin kein Zahlungseingang zu verzeichnen sein, werden wir ohne weitere Ankündigung gerichtliche Maßnahmen einleiten.

Mit freundlichen Grüßen

[UNTERSCHRIFT]
Rechtsanwalt""",

            "ratenzahlung": f"""RATENZAHLUNGSVEREINBARUNG

zwischen

{case.creditor_name} (Gläubigerin)

und

{case.debtor_name} (Schuldner)

§ 1 Forderung
Die Gesamtforderung beträgt [BETRAG] EUR.

§ 2 Ratenzahlung
Der Schuldner verpflichtet sich, die Forderung in [ANZAHL] monatlichen Raten zu je [RATE] EUR zu tilgen.
Die erste Rate ist fällig am [DATUM], die folgenden Raten jeweils zum [TAG]. des Monats.

§ 3 Verfallklausel
Bei Rückstand von mehr als zwei Raten wird die gesamte Restforderung sofort fällig.

[ORT], [DATUM]

________________________          ________________________
Gläubigerin                       Schuldner""",
        }

        return templates.get(response_type, templates["antwort"])

    def _build_case_context(self, case: Case) -> str:
        """Build context string from case data."""
        from .ledger_service import LedgerService
        ledger = LedgerService(self.db)
        balance = ledger.get_case_balance(case.id)

        claims = self.db.query(Claim).filter(Claim.case_id == case.id).all()

        context = f"""
Akte: {case.internal_number}
Gläubigerin: {case.creditor_name}
Schuldner: {case.debtor_name}
Schuldner-Adresse: {case.debtor_street}, {case.debtor_postal_code} {case.debtor_city}
Status: {case.status}
Mahnverfahren-Status: {case.dunning_status}

Forderungen:"""
        for claim in claims:
            context += f"\n- {claim.description}: {claim.principal_amount}€ (fällig seit {claim.due_date})"

        context += f"""

Aktueller Stand Forderungskonto:
- Hauptforderung offen: {balance.get('total_principal', 0):.2f}€
- Zinsen: {balance.get('total_interest', 0):.2f}€
- Kosten: {balance.get('total_costs', 0):.2f}€
- Gesamtforderung: {balance.get('total_open', 0):.2f}€
"""
        return context

    # =========================================================================
    # AUDIT LOGGING
    # =========================================================================

    def _log_ai_usage(
        self,
        user_id: UUID,
        action: str,
        input_data: str,
        output_data: str,
        case_id: Optional[UUID] = None
    ):
        """Log AI usage for audit trail."""
        log = AuditLog(
            user_id=user_id,
            action=f"ai_{action}",
            resource_type="ai_service",
            description=f"AI {action}: {len(input_data)} chars input, {len(output_data)} chars output",
            case_id=case_id,
            new_values={"input_preview": input_data[:200], "output_preview": output_data[:200]}
        )
        self.db.add(log)
        self.db.commit()
