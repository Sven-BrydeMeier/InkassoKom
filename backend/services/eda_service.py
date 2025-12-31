"""
EDA Service - Elektronisches Mahnverfahren
Generates EDA data sets for German dunning procedure (Mahnbescheid/Vollstreckungsbescheid)
Based on EDA Format 4.0/4.1 specifications from mahngerichte.de
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
import re

from sqlalchemy.orm import Session

from db.models import (
    Case, Claim, DunningApplication, Document, User,
    TimelineEvent, AuditLog, LimitationEvent
)
from config.settings import DunningStatus


class EDAService:
    """
    Service for generating EDA data sets for the electronic dunning procedure.

    EDA Format:
    - Version 4.0 for Mahnbescheid (MB) applications
    - Version 4.1 for Vollstreckungsbescheid (VB) follow-up applications

    Data structure follows the official EDA specifications from:
    https://www.mahngerichte.de/publikationen/eda-konditionen/
    """

    # EDA field codes and lengths
    RECORD_TYPE_HEADER = '00'
    RECORD_TYPE_APPLICANT = '01'
    RECORD_TYPE_DEFENDANT = '02'
    RECORD_TYPE_CLAIM = '03'
    RECORD_TYPE_COST = '04'
    RECORD_TYPE_TOTAL = '05'
    RECORD_TYPE_FOOTER = '99'

    # Court codes for German Mahngerichte
    COURT_CODES = {
        'schleswig': 'SH',
        'stuttgart': 'BW',
        'berlin': 'BE',
        'coburg': 'BY',
        'hagen': 'NW',
        'hamburg': 'HH',
        'hannover': 'NI',
        'hessen': 'HE',
        'mayen': 'RP',
        'bremen': 'HB',
        'saarbruecken': 'SL',
        'sachsen': 'SN',
        'sachsen-anhalt': 'ST',
        'schleswig-holstein': 'SH',
        'thueringen': 'TH',
        'mecklenburg-vorpommern': 'MV',
        'brandenburg': 'BB',
    }

    # Default court (Schleswig handles most electronic applications)
    DEFAULT_COURT = 'schleswig'
    DEFAULT_COURT_CODE = 'SH'

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # MAHNBESCHEID (MB) APPLICATION
    # =========================================================================

    def create_mb_application(
        self,
        case_id: UUID,
        created_by: UUID,
        court: str = 'schleswig',
        applicant_data: Optional[Dict] = None,
        defendant_data: Optional[Dict] = None,
        claim_data: Optional[Dict] = None
    ) -> DunningApplication:
        """
        Create a new Mahnbescheid application.
        """
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError("Case not found")

        # Check if MB already exists for this case
        existing = self.db.query(DunningApplication).filter(
            DunningApplication.case_id == case_id,
            DunningApplication.application_type == 'mb',
            DunningApplication.status.notin_(['widerspruch', 'erledigt'])
        ).first()

        if existing:
            raise ValueError("Mahnbescheid application already exists for this case")

        # Build application data from case if not provided
        if not applicant_data:
            applicant_data = self._build_applicant_data(case)
        if not defendant_data:
            defendant_data = self._build_defendant_data(case)
        if not claim_data:
            claim_data = self._build_claim_data(case)

        application = DunningApplication(
            case_id=case_id,
            application_type='mb',
            court_code=self.COURT_CODES.get(court, self.DEFAULT_COURT_CODE),
            court_name=f"Amtsgericht {court.title()}",
            status='entwurf',
            applicant_data=applicant_data,
            defendant_data=defendant_data,
            claim_data=claim_data,
            eda_version='4.0',
            created_by=created_by
        )

        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)

        self._create_timeline_event(
            case_id=case_id,
            event_type="mb_created",
            title="Mahnbescheid-Antrag erstellt",
            description="Entwurf für Mahnbescheid-Antrag wurde erstellt",
            category="mahnverfahren",
            actor_id=created_by,
            reference_type="dunning_application",
            reference_id=application.id,
            visible_to_creditor=True,
            visible_to_debtor=False
        )

        return application

    def generate_eda_file(
        self,
        application_id: UUID,
        generated_by: UUID
    ) -> str:
        """
        Generate the EDA data file for an application.
        Returns the EDA file content as a string.
        """
        application = self.db.query(DunningApplication).filter(
            DunningApplication.id == application_id
        ).first()

        if not application:
            raise ValueError("Application not found")

        if application.application_type == 'mb':
            eda_content = self._generate_mb_eda(application)
        else:  # VB
            eda_content = self._generate_vb_eda(application)

        # Store the generated content
        application.eda_file_content = eda_content
        application.generated_at = datetime.utcnow()
        application.status = 'generiert'
        self.db.commit()

        self._log_audit(
            action="generate_eda",
            resource_type="dunning_application",
            resource_id=application.id,
            user_id=generated_by,
            case_id=application.case_id,
            description=f"EDA file generated for {application.application_type.upper()}"
        )

        return eda_content

    def _generate_mb_eda(self, application: DunningApplication) -> str:
        """Generate EDA content for Mahnbescheid."""
        lines = []

        # Header record (00)
        lines.append(self._build_header_record(application))

        # Applicant record (01)
        lines.append(self._build_applicant_record(application.applicant_data))

        # Defendant record (02)
        lines.append(self._build_defendant_record(application.defendant_data))

        # Claim records (03)
        claim_lines = self._build_claim_records(application.claim_data)
        lines.extend(claim_lines)

        # Cost records (04)
        cost_lines = self._build_cost_records(application.claim_data)
        lines.extend(cost_lines)

        # Total record (05)
        lines.append(self._build_total_record(application.claim_data))

        # Footer record (99)
        lines.append(self._build_footer_record(len(lines) + 1))

        return '\n'.join(lines)

    def _generate_vb_eda(self, application: DunningApplication) -> str:
        """Generate EDA content for Vollstreckungsbescheid."""
        # VB uses a simplified format referencing the original MB
        lines = []

        # Header for VB (follow-up application)
        header = self._build_vb_header(application)
        lines.append(header)

        # Reference to original MB
        if application.court_file_number:
            lines.append(f"AZ:{application.court_file_number}")

        # Updated amounts if any payments received
        lines.append(self._build_vb_amount_record(application))

        # Footer
        lines.append(self._build_footer_record(len(lines) + 1))

        return '\n'.join(lines)

    # =========================================================================
    # EDA RECORD BUILDERS
    # =========================================================================

    def _build_header_record(self, application: DunningApplication) -> str:
        """Build the header record (00)."""
        parts = [
            self.RECORD_TYPE_HEADER,
            'EDA',
            application.eda_version or '4.0',
            application.court_code or self.DEFAULT_COURT_CODE,
            datetime.now().strftime('%Y%m%d'),
            'MB' if application.application_type == 'mb' else 'VB',
        ]
        return '|'.join(parts)

    def _build_applicant_record(self, applicant_data: Dict) -> str:
        """Build the applicant record (01)."""
        parts = [
            self.RECORD_TYPE_APPLICANT,
            self._sanitize_field(applicant_data.get('name', ''), 80),
            self._sanitize_field(applicant_data.get('street', ''), 50),
            self._sanitize_field(applicant_data.get('postal_code', ''), 10),
            self._sanitize_field(applicant_data.get('city', ''), 40),
            applicant_data.get('country', 'DE'),
            self._sanitize_field(applicant_data.get('legal_form', ''), 20),
            self._sanitize_field(applicant_data.get('representative', ''), 80),
        ]
        return '|'.join(parts)

    def _build_defendant_record(self, defendant_data: Dict) -> str:
        """Build the defendant record (02)."""
        parts = [
            self.RECORD_TYPE_DEFENDANT,
            self._sanitize_field(defendant_data.get('name', ''), 80),
            self._sanitize_field(defendant_data.get('street', ''), 50),
            self._sanitize_field(defendant_data.get('postal_code', ''), 10),
            self._sanitize_field(defendant_data.get('city', ''), 40),
            defendant_data.get('country', 'DE'),
            defendant_data.get('birth_date', '') or '',
        ]
        return '|'.join(parts)

    def _build_claim_records(self, claim_data: Dict) -> List[str]:
        """Build claim records (03)."""
        records = []
        claims = claim_data.get('claims', [])

        for i, claim in enumerate(claims, 1):
            parts = [
                self.RECORD_TYPE_CLAIM,
                str(i).zfill(2),
                self._format_amount(claim.get('amount', 0)),
                self._sanitize_field(claim.get('description', ''), 100),
                claim.get('due_date', ''),
                self._format_interest_rate(claim.get('interest_rate', 0)),
                claim.get('interest_start_date', ''),
            ]
            records.append('|'.join(parts))

        return records

    def _build_cost_records(self, claim_data: Dict) -> List[str]:
        """Build cost records (04)."""
        records = []
        costs = claim_data.get('costs', [])

        for cost in costs:
            parts = [
                self.RECORD_TYPE_COST,
                cost.get('type', 'SONSTIG'),
                self._format_amount(cost.get('amount', 0)),
                self._sanitize_field(cost.get('description', ''), 50),
            ]
            records.append('|'.join(parts))

        return records

    def _build_total_record(self, claim_data: Dict) -> str:
        """Build total record (05)."""
        total_principal = sum(c.get('amount', 0) for c in claim_data.get('claims', []))
        total_costs = sum(c.get('amount', 0) for c in claim_data.get('costs', []))
        total = total_principal + total_costs

        parts = [
            self.RECORD_TYPE_TOTAL,
            self._format_amount(total_principal),
            self._format_amount(total_costs),
            self._format_amount(total),
        ]
        return '|'.join(parts)

    def _build_footer_record(self, record_count: int) -> str:
        """Build footer record (99)."""
        return f"{self.RECORD_TYPE_FOOTER}|{record_count}"

    def _build_vb_header(self, application: DunningApplication) -> str:
        """Build VB-specific header."""
        parts = [
            self.RECORD_TYPE_HEADER,
            'EDA',
            '4.1',  # VB uses version 4.1
            application.court_code or self.DEFAULT_COURT_CODE,
            datetime.now().strftime('%Y%m%d'),
            'VB',
        ]
        return '|'.join(parts)

    def _build_vb_amount_record(self, application: DunningApplication) -> str:
        """Build VB amount record."""
        claim_data = application.claim_data or {}
        total_principal = sum(c.get('amount', 0) for c in claim_data.get('claims', []))
        total_costs = sum(c.get('amount', 0) for c in claim_data.get('costs', []))

        return f"BETRAG|{self._format_amount(total_principal)}|{self._format_amount(total_costs)}"

    # =========================================================================
    # DATA BUILDERS FROM CASE
    # =========================================================================

    def _build_applicant_data(self, case: Case) -> Dict:
        """Build applicant data from case."""
        return {
            'name': case.creditor_name,
            'street': case.creditor_street or '',
            'postal_code': case.creditor_postal_code or '',
            'city': case.creditor_city or '',
            'country': case.creditor_country or 'DE',
            'legal_form': '',
            'representative': '',
        }

    def _build_defendant_data(self, case: Case) -> Dict:
        """Build defendant data from case."""
        return {
            'name': case.debtor_name,
            'street': case.debtor_street or '',
            'postal_code': case.debtor_postal_code or '',
            'city': case.debtor_city or '',
            'country': case.debtor_country or 'DE',
            'birth_date': case.debtor_birth_date.strftime('%Y%m%d') if case.debtor_birth_date else '',
        }

    def _build_claim_data(self, case: Case) -> Dict:
        """Build claim data from case claims."""
        claims = self.db.query(Claim).filter(Claim.case_id == case.id).all()

        claim_list = []
        for claim in claims:
            claim_list.append({
                'amount': float(claim.principal_amount),
                'description': claim.description,
                'due_date': claim.due_date.strftime('%Y%m%d') if claim.due_date else '',
                'interest_rate': float(claim.interest_rate) if claim.interest_rate else 0,
                'interest_start_date': claim.interest_start_date.strftime('%Y%m%d') if claim.interest_start_date else '',
            })

        # Add standard costs (RA fees, etc.)
        costs = self._calculate_standard_costs(claims)

        return {
            'claims': claim_list,
            'costs': costs,
        }

    def _calculate_standard_costs(self, claims: List[Claim]) -> List[Dict]:
        """Calculate standard costs for dunning procedure."""
        total_value = sum(c.principal_amount for c in claims)
        costs = []

        # Lawyer fees (simplified RVG calculation)
        # This should be replaced with proper RVG fee calculation
        if total_value > 0:
            # 1.3 Geschäftsgebühr according to value
            business_fee = self._calculate_rvg_fee(total_value, 1.3)
            if business_fee > 0:
                costs.append({
                    'type': 'ANWALT',
                    'amount': float(business_fee),
                    'description': '1,3 Geschäftsgebühr Nr. 2300 VV RVG',
                })

            # Postpauschale
            costs.append({
                'type': 'AUSLAGEN',
                'amount': 20.00,
                'description': 'Postpauschale Nr. 7002 VV RVG',
            })

        return costs

    def _calculate_rvg_fee(self, value: Decimal, factor: float) -> Decimal:
        """
        Calculate RVG fee based on value and factor.
        Simplified calculation - should use official RVG fee tables.
        """
        # RVG fee table (simplified, 2024 values)
        fee_table = [
            (500, 49),
            (1000, 88),
            (1500, 127),
            (2000, 166),
            (3000, 222),
            (4000, 278),
            (5000, 334),
            (6000, 390),
            (7000, 446),
            (8000, 502),
            (9000, 558),
            (10000, 614),
            (13000, 666),
            (16000, 718),
            (19000, 770),
            (22000, 822),
            (25000, 874),
            (30000, 955),
            (35000, 1036),
            (40000, 1117),
            (45000, 1198),
            (50000, 1279),
        ]

        base_fee = Decimal('49')  # Minimum
        for threshold, fee in fee_table:
            if value <= threshold:
                base_fee = Decimal(str(fee))
                break

        return base_fee * Decimal(str(factor))

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _sanitize_field(self, value: str, max_length: int) -> str:
        """Sanitize and truncate a field value."""
        if not value:
            return ''
        # Remove pipe characters and newlines
        value = re.sub(r'[\|\n\r]', ' ', str(value))
        # Truncate
        return value[:max_length].strip()

    def _format_amount(self, amount: float) -> str:
        """Format amount as cents without decimal point."""
        cents = int(round(amount * 100))
        return str(cents).zfill(12)

    def _format_interest_rate(self, rate: float) -> str:
        """Format interest rate as basis points."""
        bp = int(round(rate * 100))
        return str(bp).zfill(4)

    # =========================================================================
    # VOLLSTRECKUNGSBESCHEID (VB)
    # =========================================================================

    def create_vb_application(
        self,
        case_id: UUID,
        created_by: UUID
    ) -> DunningApplication:
        """
        Create a Vollstreckungsbescheid application.
        Requires that MB was delivered and no objection received.
        """
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError("Case not found")

        # Check if MB was delivered
        if case.dunning_status not in [DunningStatus.MB_ZUGESTELLT]:
            raise ValueError("MB must be delivered before VB can be applied for")

        # Check for objection
        if case.objection_date:
            raise ValueError("Cannot apply for VB - objection was received")

        # Get original MB application
        mb_application = self.db.query(DunningApplication).filter(
            DunningApplication.case_id == case_id,
            DunningApplication.application_type == 'mb'
        ).first()

        if not mb_application:
            raise ValueError("No MB application found")

        application = DunningApplication(
            case_id=case_id,
            application_type='vb',
            court_code=mb_application.court_code,
            court_name=mb_application.court_name,
            court_file_number=mb_application.court_file_number,
            status='entwurf',
            applicant_data=mb_application.applicant_data,
            defendant_data=mb_application.defendant_data,
            claim_data=mb_application.claim_data,
            eda_version='4.1',
            created_by=created_by
        )

        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)

        self._create_timeline_event(
            case_id=case_id,
            event_type="vb_created",
            title="Vollstreckungsbescheid-Antrag erstellt",
            description="Entwurf für Vollstreckungsbescheid-Antrag wurde erstellt",
            category="mahnverfahren",
            actor_id=created_by,
            reference_type="dunning_application",
            reference_id=application.id,
            visible_to_creditor=True,
            visible_to_debtor=False
        )

        return application

    # =========================================================================
    # STATUS UPDATES
    # =========================================================================

    def mark_as_sent(
        self,
        application_id: UUID,
        sent_by: UUID,
        bea_message_id: Optional[str] = None
    ):
        """Mark application as sent."""
        application = self.db.query(DunningApplication).filter(
            DunningApplication.id == application_id
        ).first()

        if not application:
            raise ValueError("Application not found")

        application.status = 'versendet'
        application.sent_at = datetime.utcnow()
        application.bea_message_id = bea_message_id

        # Update case status
        case = self.db.query(Case).filter(Case.id == application.case_id).first()
        if case and application.application_type == 'mb':
            case.dunning_status = DunningStatus.MB_BEANTRAGT
            case.mb_application_date = date.today()
        elif case and application.application_type == 'vb':
            case.dunning_status = DunningStatus.VB_BEANTRAGT
            case.vb_application_date = date.today()

        self.db.commit()

        # Record limitation event
        from .limitation_service import LimitationService
        lim_service = LimitationService(self.db)
        lim_service.record_dunning_application(
            case_id=application.case_id,
            application_date=date.today(),
            created_by=sent_by
        )

        self._create_timeline_event(
            case_id=application.case_id,
            event_type=f"{application.application_type}_sent",
            title=f"{'Mahnbescheid' if application.application_type == 'mb' else 'Vollstreckungsbescheid'}-Antrag versendet",
            description="Antrag wurde an das Mahngericht übermittelt",
            category="mahnverfahren",
            actor_id=sent_by,
            reference_type="dunning_application",
            reference_id=application.id,
            visible_to_creditor=True,
            visible_to_debtor=True,
            severity="success"
        )

    def record_delivery(
        self,
        application_id: UUID,
        delivery_date: date,
        recorded_by: UUID,
        court_file_number: Optional[str] = None
    ):
        """Record delivery of MB/VB."""
        application = self.db.query(DunningApplication).filter(
            DunningApplication.id == application_id
        ).first()

        if not application:
            raise ValueError("Application not found")

        application.status = 'zugestellt'
        application.delivered_at = datetime.combine(delivery_date, datetime.min.time())
        if court_file_number:
            application.court_file_number = court_file_number

        # Update case
        case = self.db.query(Case).filter(Case.id == application.case_id).first()
        if case and application.application_type == 'mb':
            case.dunning_status = DunningStatus.MB_ZUGESTELLT
            case.mb_delivery_date = delivery_date
            case.court_file_number = court_file_number or case.court_file_number
        elif case and application.application_type == 'vb':
            case.dunning_status = DunningStatus.VB_ERLASSEN
            case.vb_issue_date = delivery_date

        self.db.commit()

        # Record limitation event
        from .limitation_service import LimitationService
        lim_service = LimitationService(self.db)

        if application.application_type == 'mb':
            lim_service.record_dunning_delivery(
                case_id=application.case_id,
                delivery_date=delivery_date,
                created_by=recorded_by
            )
        else:  # VB
            lim_service.record_enforcement_order(
                case_id=application.case_id,
                order_date=delivery_date,
                created_by=recorded_by
            )

        self._create_timeline_event(
            case_id=application.case_id,
            event_type=f"{application.application_type}_delivered",
            title=f"{'Mahnbescheid' if application.application_type == 'mb' else 'Vollstreckungsbescheid'} zugestellt",
            description=f"Zustellungsdatum: {delivery_date.strftime('%d.%m.%Y')}"
                        + (f", Az: {court_file_number}" if court_file_number else ""),
            category="mahnverfahren",
            actor_id=recorded_by,
            reference_type="dunning_application",
            reference_id=application.id,
            visible_to_creditor=True,
            visible_to_debtor=True,
            severity="success"
        )

    def record_objection(
        self,
        application_id: UUID,
        objection_date: date,
        recorded_by: UUID
    ):
        """Record objection (Widerspruch) against MB."""
        application = self.db.query(DunningApplication).filter(
            DunningApplication.id == application_id
        ).first()

        if not application:
            raise ValueError("Application not found")

        application.status = 'widerspruch'
        application.objection_at = datetime.combine(objection_date, datetime.min.time())

        # Update case
        case = self.db.query(Case).filter(Case.id == application.case_id).first()
        if case:
            case.dunning_status = DunningStatus.WIDERSPRUCH
            case.objection_date = objection_date

        self.db.commit()

        self._create_timeline_event(
            case_id=application.case_id,
            event_type="objection_received",
            title="Widerspruch eingegangen",
            description=f"Schuldner hat am {objection_date.strftime('%d.%m.%Y')} Widerspruch eingelegt",
            category="mahnverfahren",
            actor_id=recorded_by,
            reference_type="dunning_application",
            reference_id=application.id,
            visible_to_creditor=True,
            visible_to_debtor=True,
            severity="warning"
        )

    # =========================================================================
    # DOCUMENT GENERATION
    # =========================================================================

    def generate_printout_pdf(
        self,
        application_id: UUID,
        generated_by: UUID
    ) -> bytes:
        """
        Generate a printable PDF version of the application.
        For internal file documentation.
        """
        application = self.db.query(DunningApplication).filter(
            DunningApplication.id == application_id
        ).first()

        if not application:
            raise ValueError("Application not found")

        # Generate PDF content
        # This is a placeholder - in production, use a proper PDF library
        pdf_content = self._generate_pdf_content(application)

        # Store as document
        from .document_service import DocumentService
        doc_service = DocumentService(self.db)

        case = self.db.query(Case).filter(Case.id == application.case_id).first()

        filename = f"{'MB' if application.application_type == 'mb' else 'VB'}_Antrag_{application.id}.pdf"

        document = doc_service.upload_document(
            file_content=pdf_content,
            filename=filename,
            uploaded_by=generated_by,
            organization_id=case.organization_id if case else None,
            case_id=application.case_id,
            document_type='mahnbescheid' if application.application_type == 'mb' else 'vollstreckungsbescheid',
            title=f"{'Mahnbescheid' if application.application_type == 'mb' else 'Vollstreckungsbescheid'}-Antrag",
            visible_to_creditor=True,
            visible_to_debtor=False,
            source='generated',
            run_ocr=False
        )

        application.printout_document_id = document.id
        self.db.commit()

        return pdf_content

    def _generate_pdf_content(self, application: DunningApplication) -> bytes:
        """Generate PDF content for application printout."""
        # Placeholder - would use reportlab or similar
        content = f"""
MAHNANTRAG
==========

Antragsteller:
{application.applicant_data.get('name', '')}
{application.applicant_data.get('street', '')}
{application.applicant_data.get('postal_code', '')} {application.applicant_data.get('city', '')}

Antragsgegner:
{application.defendant_data.get('name', '')}
{application.defendant_data.get('street', '')}
{application.defendant_data.get('postal_code', '')} {application.defendant_data.get('city', '')}

Forderungen:
"""
        for i, claim in enumerate(application.claim_data.get('claims', []), 1):
            content += f"\n{i}. {claim.get('description', '')}: {claim.get('amount', 0):.2f} EUR"

        content += f"\n\nDatum: {datetime.now().strftime('%d.%m.%Y')}"

        return content.encode('utf-8')

    # =========================================================================
    # TIMELINE AND AUDIT
    # =========================================================================

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
