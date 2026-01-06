"""
Email Parser Module

Parses .eml and .msg email files for document management.
Extracts metadata, body, and attachments.
"""

from .parser import (
    EmailParser,
    ParsedEmail,
    EmailAttachment,
    parse_email_file,
    get_parser_capabilities
)

__all__ = [
    'EmailParser',
    'ParsedEmail',
    'EmailAttachment',
    'parse_email_file',
    'get_parser_capabilities'
]
