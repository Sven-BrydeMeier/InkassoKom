"""
PDF Splitter Module for InkassoKom
Intelligente Dokumententrennung mit OCR und Heuristik
"""
from .splitter import (
    PDFSplitter,
    Segment,
    split_pdf_intelligent,
    DEFAULT_PATTERNS,
)

__all__ = [
    'PDFSplitter',
    'Segment',
    'split_pdf_intelligent',
    'DEFAULT_PATTERNS',
]
