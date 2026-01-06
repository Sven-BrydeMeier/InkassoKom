"""
Email Parser - Parses .eml and .msg email files

Extracts:
- Sender, Recipients, CC, BCC
- Subject, Date
- Body (plain text and HTML)
- Attachments
- Headers for case matching
"""

import email
import email.policy
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from email.utils import parsedate_to_datetime, parseaddr
import base64
import quopri


@dataclass
class EmailAttachment:
    """Represents an email attachment"""
    filename: str
    content_type: str
    size: int
    content: bytes
    content_id: Optional[str] = None  # For inline attachments

    def get_extension(self) -> str:
        """Get file extension"""
        if '.' in self.filename:
            return self.filename.rsplit('.', 1)[-1].lower()
        return ''

    def is_pdf(self) -> bool:
        return self.content_type == 'application/pdf' or self.get_extension() == 'pdf'

    def is_image(self) -> bool:
        return self.content_type.startswith('image/') or self.get_extension() in ['jpg', 'jpeg', 'png', 'gif', 'bmp']


@dataclass
class ParsedEmail:
    """Represents a parsed email with all metadata"""
    # Basic Info
    subject: str
    date: Optional[datetime]
    message_id: str

    # Participants
    sender: str
    sender_name: str
    sender_email: str
    to: List[str]
    cc: List[str]
    bcc: List[str]
    reply_to: Optional[str]

    # Content
    body_plain: str
    body_html: str

    # Attachments
    attachments: List[EmailAttachment] = field(default_factory=list)

    # Threading
    in_reply_to: Optional[str] = None
    references: List[str] = field(default_factory=list)

    # Raw headers for advanced matching
    headers: Dict[str, str] = field(default_factory=dict)

    # Source file info
    source_filename: str = ""
    source_format: str = "eml"  # eml or msg

    # Case matching hints
    case_references: List[str] = field(default_factory=list)

    def get_display_date(self) -> str:
        """Get formatted date string"""
        if self.date:
            return self.date.strftime("%d.%m.%Y %H:%M")
        return "Unbekannt"

    def get_short_subject(self, max_len: int = 50) -> str:
        """Get truncated subject"""
        if len(self.subject) <= max_len:
            return self.subject
        return self.subject[:max_len-3] + "..."

    def get_body_preview(self, max_len: int = 200) -> str:
        """Get body preview (plain text)"""
        text = self.body_plain or self.strip_html(self.body_html)
        text = ' '.join(text.split())  # Normalize whitespace
        if len(text) <= max_len:
            return text
        return text[:max_len-3] + "..."

    @staticmethod
    def strip_html(html: str) -> str:
        """Simple HTML tag stripper"""
        if not html:
            return ""
        # Remove tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Decode entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        return text.strip()

    def extract_case_references(self) -> List[str]:
        """
        Extract potential case/file references from email.
        Looks for patterns like:
        - Aktenzeichen: 123/2024
        - Az.: 2024-001
        - Unser Zeichen: ABC-123
        - Re: [Case-123]
        """
        references = []

        # Combine subject and body for searching
        search_text = f"{self.subject}\n{self.body_plain}"

        # Pattern 1: German Aktenzeichen formats
        # Matches: 123/2024, 2024/123, ABC-123/24
        az_patterns = [
            r'(?:Aktenzeichen|Az\.?|Unser Zeichen|Ihr Zeichen|Geschäftszeichen|GZ)[:\s]+([A-Za-z0-9\-/]+)',
            r'\b(\d{1,6}[/-]\d{2,4})\b',  # 123/2024 or 123-24
            r'\b([A-Z]{2,4}[/-]\d{3,6}[/-]?\d{0,4})\b',  # ABC-123 or ABC/123/24
        ]

        for pattern in az_patterns:
            matches = re.findall(pattern, search_text, re.IGNORECASE)
            references.extend(matches)

        # Pattern 2: Subject line brackets [Case-123]
        bracket_matches = re.findall(r'\[([^\]]+)\]', self.subject)
        references.extend(bracket_matches)

        # Deduplicate and clean
        seen = set()
        clean_refs = []
        for ref in references:
            ref_clean = ref.strip()
            if ref_clean and ref_clean.lower() not in seen:
                seen.add(ref_clean.lower())
                clean_refs.append(ref_clean)

        self.case_references = clean_refs
        return clean_refs

    def match_to_case(self, cases: List[Dict]) -> Optional[Dict]:
        """
        Try to match email to a case based on:
        1. Explicit case reference in subject/body
        2. Debtor name in participants
        3. Creditor name in participants
        """
        if not self.case_references:
            self.extract_case_references()

        # Get all email addresses involved
        all_participants = [self.sender_email.lower()]
        for addr in self.to + self.cc:
            _, email_addr = parseaddr(addr)
            if email_addr:
                all_participants.append(email_addr.lower())

        for case in cases:
            # Match by Aktenzeichen
            case_az = case.get('aktenzeichen', '').lower()
            for ref in self.case_references:
                if ref.lower() in case_az or case_az in ref.lower():
                    return case

            # Match by debtor email
            debtor_email = case.get('schuldner_email', '').lower()
            if debtor_email and debtor_email in all_participants:
                return case

            # Match by debtor name in email addresses or body
            debtor_name = case.get('schuldner_name', '').lower()
            if debtor_name:
                for participant in all_participants:
                    if debtor_name.split()[0] in participant:  # Match first name
                        return case
                if debtor_name in self.body_plain.lower():
                    return case

        return None


class EmailParser:
    """
    Parser for .eml and .msg email files
    """

    def __init__(self):
        self.supported_formats = ['eml', 'msg']
        self._msg_available = self._check_msg_support()

    def _check_msg_support(self) -> bool:
        """Check if extract_msg library is available"""
        try:
            import extract_msg
            return True
        except ImportError:
            return False

    def parse(self, file_content: bytes, filename: str = "email.eml") -> ParsedEmail:
        """
        Parse email file content

        Args:
            file_content: Raw file bytes
            filename: Original filename (used to determine format)

        Returns:
            ParsedEmail object with extracted data
        """
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'eml'

        if ext == 'msg':
            return self._parse_msg(file_content, filename)
        else:
            return self._parse_eml(file_content, filename)

    def _parse_eml(self, content: bytes, filename: str) -> ParsedEmail:
        """Parse .eml format (RFC 5322)"""
        # Parse with email library
        msg = email.message_from_bytes(content, policy=email.policy.default)

        # Extract sender
        sender = msg.get('From', '')
        sender_name, sender_email = parseaddr(sender)

        # Extract recipients
        to_list = self._parse_address_list(msg.get('To', ''))
        cc_list = self._parse_address_list(msg.get('Cc', ''))
        bcc_list = self._parse_address_list(msg.get('Bcc', ''))

        # Extract date
        date_str = msg.get('Date', '')
        email_date = None
        if date_str:
            try:
                email_date = parsedate_to_datetime(date_str)
            except (ValueError, TypeError):
                pass

        # Extract body
        body_plain = ""
        body_html = ""
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))

                # Skip multipart containers
                if part.is_multipart():
                    continue

                # Check for attachments
                if 'attachment' in content_disposition or part.get_filename():
                    att = self._extract_attachment(part)
                    if att:
                        attachments.append(att)
                elif content_type == 'text/plain' and not body_plain:
                    try:
                        body_plain = part.get_content()
                    except:
                        body_plain = self._decode_payload(part)
                elif content_type == 'text/html' and not body_html:
                    try:
                        body_html = part.get_content()
                    except:
                        body_html = self._decode_payload(part)
                elif content_type.startswith('image/') and 'inline' in content_disposition:
                    # Inline image
                    att = self._extract_attachment(part)
                    if att:
                        attachments.append(att)
        else:
            content_type = msg.get_content_type()
            try:
                content_text = msg.get_content()
            except:
                content_text = self._decode_payload(msg)

            if content_type == 'text/html':
                body_html = content_text
            else:
                body_plain = content_text

        # Extract headers
        headers = {key: str(value) for key, value in msg.items()}

        # Extract threading info
        in_reply_to = msg.get('In-Reply-To', '')
        references = msg.get('References', '').split()

        parsed = ParsedEmail(
            subject=msg.get('Subject', '(Kein Betreff)'),
            date=email_date,
            message_id=msg.get('Message-ID', ''),
            sender=sender,
            sender_name=sender_name or sender_email,
            sender_email=sender_email,
            to=to_list,
            cc=cc_list,
            bcc=bcc_list,
            reply_to=msg.get('Reply-To'),
            body_plain=body_plain,
            body_html=body_html,
            attachments=attachments,
            in_reply_to=in_reply_to,
            references=references,
            headers=headers,
            source_filename=filename,
            source_format='eml'
        )

        # Extract case references
        parsed.extract_case_references()

        return parsed

    def _parse_msg(self, content: bytes, filename: str) -> ParsedEmail:
        """Parse .msg format (Outlook)"""
        if not self._msg_available:
            raise ImportError(
                "extract_msg library required for .msg files. "
                "Install with: pip install extract-msg"
            )

        import extract_msg
        import io

        # Parse MSG file from bytes
        msg = extract_msg.Message(io.BytesIO(content))

        # Extract sender
        sender = msg.sender or ''
        sender_email = msg.senderEmail or ''
        sender_name = msg.senderName or sender_email

        # Extract recipients
        to_list = []
        cc_list = []

        if msg.to:
            to_list = [addr.strip() for addr in msg.to.split(';') if addr.strip()]
        if msg.cc:
            cc_list = [addr.strip() for addr in msg.cc.split(';') if addr.strip()]

        # Extract date
        email_date = msg.date

        # Extract body
        body_plain = msg.body or ''
        body_html = msg.htmlBody or ''
        if isinstance(body_html, bytes):
            body_html = body_html.decode('utf-8', errors='ignore')

        # Extract attachments
        attachments = []
        for att in msg.attachments:
            try:
                attachments.append(EmailAttachment(
                    filename=att.longFilename or att.shortFilename or 'attachment',
                    content_type=att.mimetype or 'application/octet-stream',
                    size=len(att.data) if att.data else 0,
                    content=att.data or b'',
                    content_id=att.cid
                ))
            except:
                pass

        # Clean up
        msg.close()

        parsed = ParsedEmail(
            subject=msg.subject or '(Kein Betreff)',
            date=email_date,
            message_id=msg.messageId or '',
            sender=sender,
            sender_name=sender_name,
            sender_email=sender_email,
            to=to_list,
            cc=cc_list,
            bcc=[],
            reply_to=None,
            body_plain=body_plain,
            body_html=body_html,
            attachments=attachments,
            headers={},
            source_filename=filename,
            source_format='msg'
        )

        parsed.extract_case_references()

        return parsed

    def _parse_address_list(self, address_str: str) -> List[str]:
        """Parse comma-separated email addresses"""
        if not address_str:
            return []

        # Split on comma, but respect quoted strings
        addresses = []
        current = ""
        in_quotes = False

        for char in address_str:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                if current.strip():
                    addresses.append(current.strip())
                current = ""
                continue
            current += char

        if current.strip():
            addresses.append(current.strip())

        return addresses

    def _decode_payload(self, part) -> str:
        """Decode email part payload"""
        payload = part.get_payload(decode=True)
        if payload is None:
            return ""

        charset = part.get_content_charset() or 'utf-8'
        try:
            return payload.decode(charset, errors='replace')
        except:
            return payload.decode('utf-8', errors='replace')

    def _extract_attachment(self, part) -> Optional[EmailAttachment]:
        """Extract attachment from email part"""
        filename = part.get_filename()
        if not filename:
            # Try to get from content-type name parameter
            content_type = part.get_content_type()
            filename = f"attachment.{content_type.split('/')[-1]}"

        # Decode filename if needed
        if filename:
            try:
                from email.header import decode_header
                decoded = decode_header(filename)
                if decoded:
                    filename = decoded[0][0]
                    if isinstance(filename, bytes):
                        charset = decoded[0][1] or 'utf-8'
                        filename = filename.decode(charset, errors='replace')
            except:
                pass

        try:
            content = part.get_payload(decode=True)
            if content is None:
                return None

            return EmailAttachment(
                filename=filename or 'attachment',
                content_type=part.get_content_type(),
                size=len(content),
                content=content,
                content_id=part.get('Content-ID')
            )
        except:
            return None


def parse_email_file(file_content: bytes, filename: str = "email.eml") -> ParsedEmail:
    """
    Convenience function to parse an email file.

    Args:
        file_content: Raw file bytes
        filename: Original filename

    Returns:
        ParsedEmail object
    """
    parser = EmailParser()
    return parser.parse(file_content, filename)


def get_parser_capabilities() -> Dict[str, Any]:
    """
    Get information about parser capabilities.

    Returns:
        Dict with supported formats and features
    """
    parser = EmailParser()

    return {
        'supported_formats': ['eml', 'msg'] if parser._msg_available else ['eml'],
        'msg_support': parser._msg_available,
        'features': [
            'Metadata extraction (subject, date, sender, recipients)',
            'Body extraction (plain text and HTML)',
            'Attachment extraction',
            'Case reference detection',
            'Threading support (In-Reply-To, References)',
            'German Aktenzeichen pattern matching'
        ],
        'install_msg': 'pip install extract-msg' if not parser._msg_available else None
    }
