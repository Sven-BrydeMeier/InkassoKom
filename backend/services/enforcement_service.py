"""
Enforcement Service - Zwangsvollstreckung Module
Handles enforcement measures after obtaining a title (Vollstreckungsbescheid/Urteil)
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
import re

from sqlalchemy.orm import Session

from db.models import (
    Case, Claim, EnforcementMeasure, AssetFromVV, Document, User,
    TimelineEvent, AuditLog, Notification
)
from config.settings import EnforcementStatus, ApprovalStatus


class EnforcementService:
    """
    Service for managing enforcement measures (Zwangsvollstreckung).

    Supported measures:
    - Gerichtsvollzieher-Auftrag (GV)
    - Pfändungs- und Überweisungsbeschluss (PfüB) - Bank
    - PfüB - Arbeitgeber
    - Zwangssicherungshypothek
    - Vermögensverzeichnis import and analysis
    """

    # Measure types
    MEASURE_TYPES = {
        'gv_auftrag': 'Gerichtsvollzieher-Auftrag',
        'pfueb_bank': 'PfüB Bankpfändung',
        'pfueb_arbeitgeber': 'PfüB Arbeitgeberpfändung',
        'pfueb_drittschuldner': 'PfüB sonstiger Drittschuldner',
        'hypothek': 'Zwangssicherungshypothek',
        'versteigerung': 'Zwangsversteigerung',
        'verwaltung': 'Zwangsverwaltung',
    }

    # Asset types from Vermögensverzeichnis
    ASSET_TYPES = {
        'konto': 'Bankkonto',
        'lebensversicherung': 'Lebensversicherung',
        'grundstueck': 'Grundstück',
        'fahrzeug': 'Fahrzeug',
        'rente': 'Rentenanspruch',
        'gehalt': 'Gehalt/Arbeitgeber',
        'sonstige': 'Sonstige Vermögenswerte',
    }

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # ENFORCEMENT MEASURE CRUD
    # =========================================================================

    def create_measure(
        self,
        case_id: UUID,
        measure_type: str,
        created_by: UUID,
        target_name: Optional[str] = None,
        target_address: Optional[str] = None,
        target_iban: Optional[str] = None,
        ai_recommendation: Optional[str] = None,
        ai_confidence: Optional[float] = None
    ) -> EnforcementMeasure:
        """Create a new enforcement measure."""
        if measure_type not in self.MEASURE_TYPES:
            raise ValueError(f"Invalid measure type: {measure_type}")

        # Check if case has title
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError("Case not found")

        # Find the court for this measure
        court_info = self._find_court(measure_type, target_address or case.debtor_postal_code or '')

        measure = EnforcementMeasure(
            case_id=case_id,
            measure_type=measure_type,
            status='vorgeschlagen',
            target_type=self._get_target_type(measure_type),
            target_name=target_name,
            target_address=target_address,
            target_iban=target_iban,
            court_name=court_info.get('name'),
            court_address=court_info.get('address'),
            suggested_at=datetime.utcnow(),
            ai_recommendation=ai_recommendation,
            ai_confidence=Decimal(str(ai_confidence)) if ai_confidence else None,
            created_by=created_by
        )

        self.db.add(measure)
        self.db.commit()
        self.db.refresh(measure)

        self._create_timeline_event(
            case_id=case_id,
            event_type="measure_suggested",
            title=f"Vollstreckungsmaßnahme vorgeschlagen: {self.MEASURE_TYPES[measure_type]}",
            description=f"Ziel: {target_name}" if target_name else None,
            category="vollstreckung",
            actor_id=created_by,
            reference_type="enforcement_measure",
            reference_id=measure.id,
            visible_to_creditor=True,
            visible_to_debtor=False
        )

        return measure

    def select_measure(
        self,
        measure_id: UUID,
        selected_by: UUID
    ) -> EnforcementMeasure:
        """Lawyer selects a measure for approval."""
        measure = self.db.query(EnforcementMeasure).filter(
            EnforcementMeasure.id == measure_id
        ).first()

        if not measure:
            raise ValueError("Measure not found")

        measure.status = 'ausgewaehlt'
        measure.selected_at = datetime.utcnow()
        measure.updated_by = selected_by

        self.db.commit()
        self.db.refresh(measure)

        return measure

    def request_approval(
        self,
        measure_id: UUID,
        requested_by: UUID
    ) -> EnforcementMeasure:
        """Request creditor approval for a measure."""
        measure = self.db.query(EnforcementMeasure).filter(
            EnforcementMeasure.id == measure_id
        ).first()

        if not measure:
            raise ValueError("Measure not found")

        measure.status = 'freigabe_ausstehend'
        measure.approval_requested_at = datetime.utcnow()
        measure.updated_by = requested_by

        self.db.commit()
        self.db.refresh(measure)

        # Create notification for creditor
        case = self.db.query(Case).filter(Case.id == measure.case_id).first()
        if case and case.creditor_user_id:
            self._create_notification(
                user_id=case.creditor_user_id,
                title="Freigabe erforderlich: Vollstreckungsmaßnahme",
                message=f"Für Akte {case.internal_number} wurde eine {self.MEASURE_TYPES[measure.measure_type]} "
                        f"zur Freigabe vorgelegt.",
                notification_type="warning",
                category="approval",
                case_id=measure.case_id,
                reference_type="enforcement_measure",
                reference_id=measure.id
            )

        self._create_timeline_event(
            case_id=measure.case_id,
            event_type="approval_requested",
            title="Freigabe angefordert",
            description=f"{self.MEASURE_TYPES[measure.measure_type]} wartet auf Gläubiger-Freigabe",
            category="vollstreckung",
            actor_id=requested_by,
            reference_type="enforcement_measure",
            reference_id=measure.id,
            visible_to_creditor=True,
            visible_to_debtor=False
        )

        return measure

    def approve_measure(
        self,
        measure_id: UUID,
        approved_by: UUID,
        notes: Optional[str] = None
    ) -> EnforcementMeasure:
        """Creditor approves a measure."""
        measure = self.db.query(EnforcementMeasure).filter(
            EnforcementMeasure.id == measure_id
        ).first()

        if not measure:
            raise ValueError("Measure not found")

        if measure.status != 'freigabe_ausstehend':
            raise ValueError("Measure is not awaiting approval")

        measure.status = 'genehmigt'
        measure.approved_at = datetime.utcnow()
        measure.approved_by = approved_by
        measure.approval_notes = notes

        # Update case enforcement status
        case = self.db.query(Case).filter(Case.id == measure.case_id).first()
        if case:
            self._update_case_enforcement_status(case, measure)

        self.db.commit()
        self.db.refresh(measure)

        self._create_timeline_event(
            case_id=measure.case_id,
            event_type="measure_approved",
            title="Maßnahme genehmigt",
            description=f"{self.MEASURE_TYPES[measure.measure_type]} wurde von der Gläubigerin freigegeben",
            category="vollstreckung",
            actor_id=approved_by,
            reference_type="enforcement_measure",
            reference_id=measure.id,
            visible_to_creditor=True,
            visible_to_debtor=False,
            severity="success"
        )

        return measure

    def reject_measure(
        self,
        measure_id: UUID,
        rejected_by: UUID,
        notes: str
    ) -> EnforcementMeasure:
        """Creditor rejects a measure."""
        measure = self.db.query(EnforcementMeasure).filter(
            EnforcementMeasure.id == measure_id
        ).first()

        if not measure:
            raise ValueError("Measure not found")

        measure.status = 'abgelehnt'
        measure.rejection_notes = notes
        measure.updated_by = rejected_by

        self.db.commit()
        self.db.refresh(measure)

        self._create_timeline_event(
            case_id=measure.case_id,
            event_type="measure_rejected",
            title="Maßnahme abgelehnt",
            description=f"{self.MEASURE_TYPES[measure.measure_type]}: {notes}",
            category="vollstreckung",
            actor_id=rejected_by,
            reference_type="enforcement_measure",
            reference_id=measure.id,
            visible_to_creditor=True,
            visible_to_debtor=False,
            severity="warning"
        )

        return measure

    def mark_as_executed(
        self,
        measure_id: UUID,
        executed_by: UUID,
        application_document_id: Optional[UUID] = None
    ) -> EnforcementMeasure:
        """Mark a measure as executed (application sent)."""
        measure = self.db.query(EnforcementMeasure).filter(
            EnforcementMeasure.id == measure_id
        ).first()

        if not measure:
            raise ValueError("Measure not found")

        measure.status = 'ausgefuehrt'
        measure.executed_at = datetime.utcnow()
        measure.application_document_id = application_document_id
        measure.updated_by = executed_by

        # Update case status
        case = self.db.query(Case).filter(Case.id == measure.case_id).first()
        if case:
            self._update_case_enforcement_status(case, measure)

        self.db.commit()
        self.db.refresh(measure)

        self._create_timeline_event(
            case_id=measure.case_id,
            event_type="measure_executed",
            title=f"{self.MEASURE_TYPES[measure.measure_type]} versendet",
            description="Antrag wurde an das zuständige Gericht/die zuständige Stelle übermittelt",
            category="vollstreckung",
            actor_id=executed_by,
            reference_type="enforcement_measure",
            reference_id=measure.id,
            visible_to_creditor=True,
            visible_to_debtor=True,
            severity="success"
        )

        return measure

    def record_result(
        self,
        measure_id: UUID,
        recorded_by: UUID,
        result_amount: Optional[Decimal] = None,
        result_notes: Optional[str] = None,
        result_document_id: Optional[UUID] = None
    ) -> EnforcementMeasure:
        """Record the result of an enforcement measure."""
        measure = self.db.query(EnforcementMeasure).filter(
            EnforcementMeasure.id == measure_id
        ).first()

        if not measure:
            raise ValueError("Measure not found")

        measure.status = 'ruecklaefer'
        measure.completed_at = datetime.utcnow()
        measure.result_amount = result_amount
        measure.result_notes = result_notes
        measure.result_document_id = result_document_id
        measure.updated_by = recorded_by

        self.db.commit()
        self.db.refresh(measure)

        # If amount was recovered, create booking
        if result_amount and result_amount > 0:
            from .ledger_service import LedgerService
            ledger = LedgerService(self.db)
            ledger.create_booking(
                case_id=measure.case_id,
                booking_date=date.today(),
                debit_credit='H',
                amount=result_amount,
                category='vollstreckungskosten',
                description=f"Eingang aus {self.MEASURE_TYPES[measure.measure_type]}",
                source='vollstreckung',
                created_by=recorded_by,
                reference=str(measure.id)
            )

        self._create_timeline_event(
            case_id=measure.case_id,
            event_type="measure_result",
            title=f"Ergebnis: {self.MEASURE_TYPES[measure.measure_type]}",
            description=f"Eingegangen: {result_amount}€" if result_amount else result_notes,
            category="vollstreckung",
            actor_id=recorded_by,
            reference_type="enforcement_measure",
            reference_id=measure.id,
            visible_to_creditor=True,
            visible_to_debtor=True,
            severity="success" if result_amount and result_amount > 0 else "info"
        )

        return measure

    # =========================================================================
    # VERMÖGENSVERZEICHNIS (VV) PROCESSING
    # =========================================================================

    def process_vermoegensverzeichnis(
        self,
        case_id: UUID,
        document_id: UUID,
        processed_by: UUID,
        ocr_text: Optional[str] = None
    ) -> List[AssetFromVV]:
        """
        Process a Vermögensverzeichnis document and extract assets.
        Creates recommendations for enforcement measures.
        """
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError("Document not found")

        text = ocr_text or document.ocr_text
        if not text:
            raise ValueError("No text content available for processing")

        # Extract assets from text
        assets = self._extract_assets_from_vv(text)

        created_assets = []
        for asset_data in assets:
            asset = AssetFromVV(
                case_id=case_id,
                document_id=document_id,
                asset_type=asset_data['type'],
                description=asset_data.get('description'),
                holder_name=asset_data.get('holder_name'),
                holder_address=asset_data.get('holder_address'),
                value_amount=Decimal(str(asset_data['value'])) if asset_data.get('value') else None,
                monthly_income=Decimal(str(asset_data['monthly_income'])) if asset_data.get('monthly_income') else None,
                iban=asset_data.get('iban'),
                employer_name=asset_data.get('employer_name'),
                employer_address=asset_data.get('employer_address'),
                property_address=asset_data.get('property_address'),
                grundbuchamt=asset_data.get('grundbuchamt'),
                status='extracted'
            )
            self.db.add(asset)
            created_assets.append(asset)

        # Update case enforcement status
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if case:
            case.enforcement_status = EnforcementStatus.VV_ERHALTEN

        self.db.commit()

        # Generate recommendations
        self._generate_recommendations(case_id, created_assets, processed_by)

        self._create_timeline_event(
            case_id=case_id,
            event_type="vv_processed",
            title="Vermögensverzeichnis ausgewertet",
            description=f"{len(created_assets)} Vermögenspositionen extrahiert",
            category="vollstreckung",
            actor_id=processed_by,
            reference_type="document",
            reference_id=document_id,
            visible_to_creditor=True,
            visible_to_debtor=False,
            severity="success"
        )

        for asset in created_assets:
            self.db.refresh(asset)

        return created_assets

    def _extract_assets_from_vv(self, text: str) -> List[Dict]:
        """
        Extract asset information from VV text.
        Uses pattern matching for common VV formats.
        """
        assets = []
        text_lower = text.lower()

        # Extract bank accounts
        iban_pattern = r'[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}'
        ibans = re.findall(iban_pattern, text.upper())
        for iban in ibans:
            assets.append({
                'type': 'konto',
                'iban': iban,
                'description': 'Bankkonto',
                'holder_name': self._extract_bank_name(text, iban),
            })

        # Extract employer information
        employer_patterns = [
            r'arbeitgeber[:\s]+([^\n]+)',
            r'beschäftigt bei[:\s]+([^\n]+)',
            r'angestellt bei[:\s]+([^\n]+)',
        ]
        for pattern in employer_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if len(match.strip()) > 3:  # Filter out short matches
                    assets.append({
                        'type': 'gehalt',
                        'employer_name': match.strip().title(),
                        'description': 'Arbeitseinkommen',
                    })
                    break  # Only add one employer

        # Extract property
        property_patterns = [
            r'grundstück[:\s]+([^\n]+)',
            r'immobilie[:\s]+([^\n]+)',
            r'grundbuch[:\s]+([^\n]+)',
        ]
        for pattern in property_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                assets.append({
                    'type': 'grundstueck',
                    'property_address': match.strip().title(),
                    'description': 'Grundstück/Immobilie',
                })

        # Extract life insurance
        insurance_patterns = [
            r'lebensversicherung[:\s]+([^\n]+)',
            r'versicherung[:\s]+([^\n]+)',
        ]
        for pattern in insurance_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if 'lebens' in match or 'kapital' in match:
                    assets.append({
                        'type': 'lebensversicherung',
                        'holder_name': match.strip().title(),
                        'description': 'Lebensversicherung',
                    })

        # Extract vehicle
        vehicle_patterns = [
            r'kfz[:\s]+([^\n]+)',
            r'fahrzeug[:\s]+([^\n]+)',
            r'pkw[:\s]+([^\n]+)',
        ]
        for pattern in vehicle_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                assets.append({
                    'type': 'fahrzeug',
                    'description': f'Fahrzeug: {match.strip().title()}',
                })

        # Extract pension/retirement
        pension_patterns = [
            r'rente[:\s]+([^\n]+)',
            r'pension[:\s]+([^\n]+)',
            r'altersvorsorge[:\s]+([^\n]+)',
        ]
        for pattern in pension_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                assets.append({
                    'type': 'rente',
                    'description': f'Rentenanspruch: {match.strip().title()}',
                })

        return assets

    def _extract_bank_name(self, text: str, iban: str) -> Optional[str]:
        """Try to extract bank name near IBAN."""
        # Look for bank name patterns near the IBAN
        bank_patterns = [
            r'([a-zA-Z]+bank)',
            r'([a-zA-Z]+kasse)',
            r'sparkasse\s+([a-zA-Z\s]+)',
        ]

        text_lower = text.lower()
        iban_pos = text_lower.find(iban.lower())

        if iban_pos > 0:
            # Look in the surrounding 200 characters
            context = text_lower[max(0, iban_pos-100):iban_pos+100]
            for pattern in bank_patterns:
                match = re.search(pattern, context)
                if match:
                    return match.group(1).title()

        return None

    def _generate_recommendations(
        self,
        case_id: UUID,
        assets: List[AssetFromVV],
        created_by: UUID
    ):
        """Generate enforcement measure recommendations based on extracted assets."""
        for asset in assets:
            if asset.asset_type == 'konto' and asset.iban:
                # Recommend bank PfüB
                self.create_measure(
                    case_id=case_id,
                    measure_type='pfueb_bank',
                    created_by=created_by,
                    target_name=asset.holder_name,
                    target_iban=asset.iban,
                    ai_recommendation="Bankpfändung empfohlen basierend auf Vermögensverzeichnis",
                    ai_confidence=0.85
                )
                asset.status = 'action_suggested'

            elif asset.asset_type == 'gehalt' and asset.employer_name:
                # Recommend employer PfüB
                self.create_measure(
                    case_id=case_id,
                    measure_type='pfueb_arbeitgeber',
                    created_by=created_by,
                    target_name=asset.employer_name,
                    target_address=asset.employer_address,
                    ai_recommendation="Lohnpfändung empfohlen basierend auf Vermögensverzeichnis",
                    ai_confidence=0.80
                )
                asset.status = 'action_suggested'

            elif asset.asset_type == 'grundstueck':
                # Recommend Zwangssicherungshypothek
                self.create_measure(
                    case_id=case_id,
                    measure_type='hypothek',
                    created_by=created_by,
                    target_address=asset.property_address,
                    ai_recommendation="Zwangssicherungshypothek empfohlen basierend auf Grundbesitz",
                    ai_confidence=0.75
                )
                asset.status = 'action_suggested'

        self.db.commit()

    # =========================================================================
    # GV AUFTRAG (GERICHTSVOLLZIEHER)
    # =========================================================================

    def create_gv_auftrag(
        self,
        case_id: UUID,
        created_by: UUID
    ) -> EnforcementMeasure:
        """Create a Gerichtsvollzieher-Auftrag."""
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError("Case not found")

        # Find GV distribution office based on debtor address
        gv_info = self._find_gv_office(case.debtor_postal_code)

        measure = self.create_measure(
            case_id=case_id,
            measure_type='gv_auftrag',
            created_by=created_by,
            target_name=case.debtor_name,
            target_address=f"{case.debtor_street}, {case.debtor_postal_code} {case.debtor_city}"
        )

        # Override court info with GV office
        measure.court_name = gv_info.get('name', 'Gerichtsvollzieher-Verteilerstelle')
        measure.court_address = gv_info.get('address', '')
        self.db.commit()

        return measure

    def _find_gv_office(self, postal_code: str) -> Dict[str, str]:
        """Find the responsible GV distribution office."""
        # This would query a database of GV offices
        # Placeholder implementation
        return {
            'name': 'Gerichtsvollzieher-Verteilerstelle',
            'address': 'beim zuständigen Amtsgericht'
        }

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _get_target_type(self, measure_type: str) -> str:
        """Get the target type for a measure type."""
        type_mapping = {
            'gv_auftrag': 'schuldner',
            'pfueb_bank': 'bank',
            'pfueb_arbeitgeber': 'arbeitgeber',
            'pfueb_drittschuldner': 'drittschuldner',
            'hypothek': 'grundbuchamt',
            'versteigerung': 'gericht',
            'verwaltung': 'gericht',
        }
        return type_mapping.get(measure_type, 'sonstige')

    def _find_court(self, measure_type: str, postal_code: str) -> Dict[str, str]:
        """Find the responsible court for a measure."""
        # This would query the Justizportal Orts- und Gerichtsverzeichnis
        # Placeholder implementation
        return {
            'name': 'Amtsgericht',
            'address': f'für PLZ {postal_code}'
        }

    def _update_case_enforcement_status(self, case: Case, measure: EnforcementMeasure):
        """Update case enforcement status based on measure status."""
        if measure.measure_type == 'gv_auftrag':
            case.enforcement_status = EnforcementStatus.GV_AUFTRAG
        elif measure.status == 'ausgefuehrt':
            if 'pfueb' in measure.measure_type:
                case.enforcement_status = EnforcementStatus.PFUEB_BEANTRAGT

    # =========================================================================
    # QUERIES
    # =========================================================================

    def get_measures_for_case(self, case_id: UUID) -> List[EnforcementMeasure]:
        """Get all enforcement measures for a case."""
        return self.db.query(EnforcementMeasure).filter(
            EnforcementMeasure.case_id == case_id
        ).order_by(EnforcementMeasure.created_at.desc()).all()

    def get_pending_approvals(self, organization_id: UUID) -> List[EnforcementMeasure]:
        """Get all measures pending approval for an organization."""
        return self.db.query(EnforcementMeasure).join(Case).filter(
            Case.organization_id == organization_id,
            EnforcementMeasure.status == 'freigabe_ausstehend'
        ).all()

    def get_assets_for_case(self, case_id: UUID) -> List[AssetFromVV]:
        """Get all extracted assets for a case."""
        return self.db.query(AssetFromVV).filter(
            AssetFromVV.case_id == case_id
        ).all()

    # =========================================================================
    # DOCUMENT GENERATION
    # =========================================================================

    def generate_pfueb_application(
        self,
        measure_id: UUID,
        generated_by: UUID
    ) -> Document:
        """Generate a PfüB application document."""
        measure = self.db.query(EnforcementMeasure).filter(
            EnforcementMeasure.id == measure_id
        ).first()

        if not measure:
            raise ValueError("Measure not found")

        case = self.db.query(Case).filter(Case.id == measure.case_id).first()
        if not case:
            raise ValueError("Case not found")

        # Get current balance
        from .ledger_service import LedgerService
        ledger = LedgerService(self.db)
        balance = ledger.get_case_balance(measure.case_id)

        # Generate document content
        content = self._generate_pfueb_content(case, measure, balance)

        # Save as document
        from .document_service import DocumentService
        doc_service = DocumentService(self.db)

        filename = f"PfueB_Antrag_{measure.id}.docx"

        document = doc_service.upload_document(
            file_content=content.encode('utf-8'),
            filename=filename,
            uploaded_by=generated_by,
            organization_id=case.organization_id,
            case_id=case.id,
            document_type='pfueb',
            title=f"PfüB-Antrag - {measure.target_name or 'Drittschuldner'}",
            visible_to_creditor=True,
            visible_to_debtor=False,
            source='generated'
        )

        measure.application_document_id = document.id
        self.db.commit()

        return document

    def _generate_pfueb_content(
        self,
        case: Case,
        measure: EnforcementMeasure,
        balance: Dict
    ) -> str:
        """Generate PfüB application content."""
        # This would use a proper template engine like Jinja2
        # Placeholder implementation
        content = f"""
PFÄNDUNGS- UND ÜBERWEISUNGSBESCHLUSS

An das Amtsgericht
{measure.court_name}
{measure.court_address}

In Sachen
{case.creditor_name}
- Gläubigerin -

gegen

{case.debtor_name}
{case.debtor_street}
{case.debtor_postal_code} {case.debtor_city}
- Schuldner -

wegen: Geldforderung

wird beantragt:

1. Die dem Schuldner gegen den Drittschuldner

{measure.target_name or 'N.N.'}
{measure.target_address or ''}
{f'IBAN: {measure.target_iban}' if measure.target_iban else ''}

zustehende Forderung wird wegen einer Forderung von

{balance.get('total_open', 0):.2f} EUR Hauptforderung
nebst Zinsen und Kosten

gepfändet und der Gläubigerin zur Einziehung überwiesen.

Titel: Vollstreckungsbescheid vom {case.vb_issue_date or '___'}
Aktenzeichen: {case.court_file_number or '___'}

Ort, Datum

_______________________
Unterschrift RA
"""
        return content

    # =========================================================================
    # NOTIFICATIONS AND TIMELINE
    # =========================================================================

    def _create_notification(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: str,
        category: str,
        case_id: Optional[UUID] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[UUID] = None
    ):
        """Create a notification."""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            category=category,
            case_id=case_id,
            reference_type=reference_type,
            reference_id=reference_id
        )
        self.db.add(notification)
        self.db.commit()

    def _create_timeline_event(
        self,
        case_id: UUID,
        event_type: str,
        title: str,
        actor_id: Optional[UUID] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[UUID] = None,
        visible_to_creditor: bool = True,
        visible_to_debtor: bool = False,
        severity: str = "info"
    ) -> TimelineEvent:
        """Create a timeline event."""
        actor_name = None
        actor_role = None

        if actor_id:
            actor = self.db.query(User).filter(User.id == actor_id).first()
            if actor:
                actor_name = actor.full_name
                actor_role = actor.role

        event = TimelineEvent(
            case_id=case_id,
            event_type=event_type,
            title=title,
            description=description,
            category=category,
            severity=severity,
            actor_id=actor_id,
            actor_name=actor_name,
            actor_role=actor_role,
            reference_type=reference_type,
            reference_id=reference_id,
            visible_to_creditor=visible_to_creditor,
            visible_to_debtor=visible_to_debtor
        )

        self.db.add(event)
        self.db.commit()

        return event

    def _log_audit(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        case_id: Optional[UUID] = None,
        description: Optional[str] = None
    ):
        """Log an audit entry."""
        user = None
        organization_id = None

        if user_id:
            user = self.db.query(User).filter(User.id == user_id).first()

        if case_id:
            case = self.db.query(Case).filter(Case.id == case_id).first()
            if case:
                organization_id = case.organization_id

        log = AuditLog(
            user_id=user_id,
            user_email=user.email if user else None,
            user_role=user.role if user else None,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            case_id=case_id
        )

        self.db.add(log)
