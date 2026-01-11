import pytesseract
from pdf2image import convert_from_path
from typing import List, Tuple
import sys
import os
import re
import warnings
warnings.filterwarnings('ignore')


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import DocumentElement, ModalityType

# Set Poppler path
POPPLER_PATH = r"D:\Rag_Chatbot-main\poppler\poppler-23.11.0\Library\bin"

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class ImageExtractor:
    """
    Extract and OCR figures/images from PDFs
    Uses Tesseract for text extraction from visual elements
    """
    
    def __init__(self):
        print("Image extractor initialized (OCR enabled)")
    
    def extract(self, pdf_path: str) -> List[DocumentElement]:
        """
        Extract image/figure elements from PDF using OCR
        Detects:
        1. Figure captions in OCR text -> modality=FIGURE
        2. Scanned/image-only pages -> modality=IMAGE_OCR
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of DocumentElement objects with modality=FIGURE or IMAGE_OCR
        """
        elements = []
        
        try:
            print("Extracting figure elements with OCR...")
            print("  Converting PDF to images...")
            
            # Convert PDF pages to images at 200 DPI
            images = convert_from_path(pdf_path, dpi=200, poppler_path=POPPLER_PATH)
            print(f"  Converted {len(images)} pages to images")
            
            for page_num, image in enumerate(images, 1):
                print(f"  Running OCR on page {page_num}...")
                
                # Run Tesseract OCR
                ocr_text = pytesseract.image_to_string(image)
                
                if not ocr_text or len(ocr_text.strip()) < 20:
                    print(f"    Page {page_num}: No significant OCR text found")
                    continue
                
                # Split into lines for processing
                lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
                
                # DEBUG: Show first few lines of OCR text
                print(f"    OCR extracted {len(lines)} lines, sample: {lines[:3] if lines else 'empty'}...")
                
                # Check if this page has figure captions OR is pure OCR content
                figure_elements = self._extract_figures_from_ocr(lines, page_num)
                
                if figure_elements:
                    elements.extend(figure_elements)
                elif len(lines) > 10:
                    # No figures found, but substantial OCR text -> treat as scanned page
                    print(f"    Creating IMAGE_OCR chunk for scanned content")
                    elements.append(DocumentElement(
                        type=ModalityType.IMAGE_OCR,
                        content='\n'.join(lines[:50]),  # Limit to first 50 lines
                        page=page_num,
                        section=f"Scanned Page {page_num}"
                    ))
            
            print(f"  Found {len(elements)} figure elements via OCR")
            return elements
            
        except Exception as e:
            print(f"OCR extraction error: {e}")
            return []
    
    def _extract_figures_from_ocr(self, lines: List[str], page_num: int) -> List[DocumentElement]:
        """
        Extract figure content from OCR text lines
        
        Args:
            lines: OCR text lines
            page_num: Current page number
            
        Returns:
            List of figure DocumentElements
        """
        figures = []
        
        # DEBUG: Check all lines for figure patterns
        matching_lines = [line for line in lines if self._is_figure_caption(line)]
        if matching_lines:
            print(f"    DEBUG: Found {len(matching_lines)} figure captions on page {page_num}")
        else:
            print(f"    DEBUG: No strict figure captions found. Checking for keywords...")
            # Check if any line contains common figure-related keywords
            fig_keywords = ['figure', 'chart', 'graph', 'diagram', 'exhibit', 'plot', 'image']
            lines_with_keywords = [line for line in lines if any(kw in line.lower() for kw in fig_keywords)]
            if lines_with_keywords:
                print(f"    DEBUG: Found {len(lines_with_keywords)} lines with figure keywords")
                print(f"    DEBUG: Samples: {lines_with_keywords[:3]}")
                
                # FALLBACK: Treat pages with figure keywords as having figures
                # Combine all lines with keywords into one figure element
                combined_text = '\n'.join(lines_with_keywords[:10])  # Take first 10 lines
                if combined_text:
                    print(f"    Creating figure from keyword-based detection")
                    figures.append(DocumentElement(
                        type=ModalityType.FIGURE,
                        content=combined_text.strip(),
                        page=page_num,
                        section=f"Figure on page {page_num}"
                    ))
                    return figures
        
        # Standard caption-based extraction
        for idx, line in enumerate(lines):
            if self._is_figure_caption(line):
                print(f"    Found figure: {line[:60]}...")
                
                # Extract caption and surrounding context
                caption = line
                context = self._get_figure_context(lines, idx)
                
                figure_content = f"{caption}\n{context}"
                
                figures.append(DocumentElement(
                    type=ModalityType.FIGURE,
                    content=figure_content.strip(),
                    page=page_num,
                    section=self._extract_label(caption)
                ))
        
        return figures
    
    def _get_figure_context(self, lines: List[str], caption_idx: int) -> str:
        """
        Get contextual text around figure caption
        
        Args:
            lines: All OCR lines
            caption_idx: Index of caption line
            
        Returns:
            Context text (3-5 lines after caption)
        """
        context_lines = []
        
        # Get 3-5 lines after caption
        for i in range(caption_idx + 1, min(caption_idx + 6, len(lines))):
            line = lines[i]
            
            # Stop if we hit another figure
            if self._is_figure_caption(line):
                break
            
            context_lines.append(line)
        
        return '\n'.join(context_lines)
    
    def _is_figure_caption(self, text: str) -> bool:
        """
        Detect if text is a figure caption
        
        Args:
            text: Text line to check
            
        Returns:
            True if text matches figure caption pattern
        """
        text_lower = text.lower().strip()
        
        if len(text_lower) < 3:
            return False
        
        # More flexible patterns - match anywhere in line
        patterns = [
            r'text\s+figure\s*\d+',
            r'figure\s*\d+',
            r'chart\s*\d+',
            r'graph\s*\d+',
            r'diagram\s*\d+',
            r'exhibit\s*\d+',
            r'fig\.\s*\d+',
            r'fig\s+\d+',
            r'table\s*\d+',  # Sometimes figures labeled as tables
        ]
        
        return any(re.search(pattern, text_lower) for pattern in patterns)
    
    def _extract_label(self, caption: str) -> str:
        """
        Extract figure label from caption
        
        Args:
            caption: Figure caption text
            
        Returns:
            Label string (e.g., "Text Figure 1")
        """
        patterns = [
            r'(text figure \d+)',
            r'(figure \d+)',
            r'(chart \d+)',
            r'(graph \d+)',
            r'(diagram \d+)',
            r'(exhibit \d+)',
            r'(fig\.\s*\d+)',
            r'(fig\s+\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, caption.lower())
            if match:
                return match.group(1).title()
        
        return "Figure"
