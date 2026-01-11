"""
Text extraction from PDFs
Handles narrative text, paragraphs, and sections
"""
import pdfplumber
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import NarrativeText
from typing import List, Optional
import re
import sys
import os
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path for models import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import DocumentElement, ModalityType


class TextExtractor:
    """
    Extract and process text content from PDFs
    Uses unstructured.io for intelligent layout detection
    """
    
    def __init__(self):
        print("Text extractor initialized")
    
    def extract(self, pdf_path: str) -> List[DocumentElement]:
        """
        Extract text elements from PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of DocumentElement objects with modality=TEXT
        """
        elements = []
        
        try:
            print("Extracting text elements...")
            
            # Use unstructured for intelligent parsing
            raw_elements = partition_pdf(
                pdf_path,
                strategy="hi_res",
                infer_table_structure=False,  # Tables handled separately
                extract_images_in_pdf=False,   # Images handled separately
                include_page_breaks=True
            )
            
            # Extract with pdfplumber for page tracking
            with pdfplumber.open(pdf_path) as pdf:
                current_page = 1
                
                for elem in raw_elements:
                    # Track page number
                    if hasattr(elem, 'metadata') and elem.metadata.page_number:
                        current_page = elem.metadata.page_number
                    
                    # Process narrative text
                    if isinstance(elem, NarrativeText):
                        text = str(elem).strip()
                        
                        # Skip very short text
                        if len(text) < 10:
                            continue
                        
                        # Check if figure caption (should be handled by images)
                        if self._is_figure_caption(text):
                            continue
                        
                        # Check if footnote
                        if self._is_footnote(text):
                            elements.append(DocumentElement(
                                type=ModalityType.FOOTNOTE,
                                content=text,
                                page=current_page
                            ))
                        else:
                            # Regular text
                            elements.append(DocumentElement(
                                type=ModalityType.TEXT,
                                content=text,
                                page=current_page,
                                section=self._extract_section(elem)
                            ))
            
            print(f"  Found {len(elements)} text elements")
            return elements
            
        except Exception as e:
            print(f"Text extraction error: {e}")
            return self._fallback_extract(pdf_path)
    
    def _fallback_extract(self, pdf_path: str) -> List[DocumentElement]:
        """Fallback text extraction using pdfplumber only"""
        elements = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text and text.strip():
                        elements.append(DocumentElement(
                            type=ModalityType.TEXT,
                            content=text.strip(),
                            page=page_num
                        ))
            print(f"  Fallback: Found {len(elements)} text pages")
        except Exception as e:
            print(f"Fallback extraction failed: {e}")
        
        return elements
    
    def _is_footnote(self, text: str) -> bool:
        """Detect if text is a footnote"""
        return bool(re.match(r'^\d+\.?\s', text)) or text.startswith("*")
    
    def _is_figure_caption(self, text: str) -> bool:
        """Detect if text is a figure caption"""
        text_lower = text.lower().strip()
        if len(text_lower) < 5:
            return False
        
        patterns = [
            r'^text figure \d+',
            r'^figure \d+',
            r'^chart \d+',
            r'^graph \d+',
            r'^diagram \d+',
            r'^exhibit \d+',
            r'^fig\.\s*\d+',
            r'^fig\s+\d+'
        ]
        
        return any(re.search(pattern, text_lower) for pattern in patterns)
    
    def _extract_section(self, elem) -> Optional[str]:
        """Extract section heading if available"""
        if hasattr(elem, 'metadata') and hasattr(elem.metadata, 'section'):
            return elem.metadata.section
        return ""
