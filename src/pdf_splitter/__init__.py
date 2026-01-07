"""
PDF Splitter Module for InkassoKom
Intelligente Dokumententrennung mit OCR und Heuristik
"""
from .splitter import (
    PDFSplitter,
    Segment,
    split_pdf_intelligent,
    get_splitter_capabilities,
    DEFAULT_PATTERNS,
)

__all__ = [
    'PDFSplitter',
    'Segment',
    'split_pdf_intelligent',
    'get_splitter_capabilities',
    'DEFAULT_PATTERNS',
]
