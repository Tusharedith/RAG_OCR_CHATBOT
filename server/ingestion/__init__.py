"""PDF extraction: text, tables, images with OCR"""
from typing import List, Dict, Optional
import hashlib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import DocumentElement, Chunk, ModalityType
from .pdf_text import TextExtractor
from .pdf_tables import TableExtractor
from .pdf_images import ImageExtractor


class MultiModalParser:
    """Orchestrates text, table, and image extraction"""
    
    def __init__(self):
        self.text_extractor = TextExtractor()
        self.table_extractor = TableExtractor()
        self.image_extractor = ImageExtractor()
        self.elements = []
    
    def parse_pdf(self, pdf_path: str) -> List[DocumentElement]:
        """Parses PDF using all extractors"""
        elements = []
        
        print(f"\nParsing PDF: {pdf_path}")
        print("=" * 60)
        
        text_elements = self.text_extractor.extract(pdf_path)
        elements.extend(text_elements)
        
        table_elements = self.table_extractor.extract(pdf_path)
        elements.extend(table_elements)
        
        figure_elements = self.image_extractor.extract(pdf_path)
        elements.extend(figure_elements)
        
        print("=" * 60)
        print(f"Total elements extracted: {len(elements)}")
        print(f"  Text: {sum(1 for e in elements if e.type == ModalityType.TEXT)}")
        print(f"  Tables: {sum(1 for e in elements if e.type == ModalityType.TABLE)}")
        print(f"  Figures: {sum(1 for e in elements if e.type == ModalityType.FIGURE)}")
        print(f"  Image OCR: {sum(1 for e in elements if e.type == ModalityType.IMAGE_OCR)}")
        print(f"  Footnotes: {sum(1 for e in elements if e.type == ModalityType.FOOTNOTE)}")
        print("=" * 60)
        
        return elements


class ModalityAwareChunker:
    """Chunks by modality: text (sliding window), tables/figures (atomic)"""
    
    def __init__(self, text_chunk_size: int = 700, overlap: int = 100):
        self.text_chunk_size = text_chunk_size
        self.overlap = overlap
    
    def chunk_elements(self, elements: List[DocumentElement], source: str) -> List[Chunk]:
        """Applies modality-specific chunking"""
        chunks = []
        modality_counts = {"text": 0, "table": 0, "figure": 0, "image_ocr": 0, "footnote": 0}
        table_counter = 0
        figure_counter = 0
        ocr_counter = 0
        footnote_counter = 0
        
        for elem in elements:
            if elem.type == ModalityType.TEXT:
                text_chunks = self._sliding_window_chunk(elem.content)
                for i, chunk_text in enumerate(text_chunks):
                    chunks.append(self._create_chunk(
                        content=chunk_text,
                        modality=ModalityType.TEXT,
                        page=elem.page,
                        source=source,
                        index=modality_counts["text"] + i,
                        section=elem.section
                    ))
                modality_counts["text"] += len(text_chunks)
            
            elif elem.type == ModalityType.TABLE:
                chunks.append(self._create_chunk(
                    content=elem.content,
                    modality=ModalityType.TABLE,
                    page=elem.page,
                    source=source,
                    index=table_counter,
                    section=elem.section
                ))
                table_counter += 1
                modality_counts["table"] += 1
            
            elif elem.type == ModalityType.FIGURE:
                chunks.append(self._create_chunk(
                    content=elem.content,
                    modality=ModalityType.FIGURE,
                    page=elem.page,
                    source=source,
                    index=figure_counter,
                    section=elem.section
                ))
                figure_counter += 1
                modality_counts["figure"] += 1
            
            elif elem.type == ModalityType.IMAGE_OCR:
                chunks.append(self._create_chunk(
                    content=elem.content,
                    modality=ModalityType.IMAGE_OCR,
                    page=elem.page,
                    source=source,
                    index=ocr_counter,
                    section=elem.section
                ))
                ocr_counter += 1
                modality_counts["image_ocr"] += 1
            
            elif elem.type == ModalityType.FOOTNOTE:
                # Optional: keep as atomic chunk
                chunks.append(self._create_chunk(
                    content=elem.content,
                    modality=ModalityType.FOOTNOTE,
                    page=elem.page,
                    source=source,
                    index=footnote_counter
                ))
                footnote_counter += 1
                modality_counts["footnote"] += 1
        
        print(f"\nChunking complete - Multi-modal breakdown:")
        print(f"  Text chunks: {modality_counts['text']}")
        print(f"  Table chunks: {modality_counts['table']}")
        print(f"  Figure chunks: {modality_counts['figure']}")
        print(f"  Image OCR chunks: {modality_counts['image_ocr']}")
        print(f"  Footnote chunks: {modality_counts['footnote']}")
        print(f"  Total: {len(chunks)} chunks")
        
        return chunks
    
    def _sliding_window_chunk(self, text: str) -> List[str]:
        """Chunks text with sliding window and overlap"""
        words = text.split()
        chunks = []
        
        i = 0
        while i < len(words):
            chunk = ' '.join(words[i:i + self.text_chunk_size])
            chunks.append(chunk)
            i += (self.text_chunk_size - self.overlap)
        
        return chunks
    
    def _create_chunk(self, content: str, modality: ModalityType, 
                     page: int, source: str, index: int = 0, section: Optional[str] = None) -> Chunk:
        """Creates chunk with unique ID"""
        chunk_id = hashlib.md5(
            f"{source}_{page}_{modality.value}_{index}_{content[:100]}".encode()
        ).hexdigest()
        
        return Chunk(
            id=chunk_id,
            content=content,
            modality=modality,
            page=page,
            source=source,
            label=section,
            metadata={
                "chunk_index": index,
                "content_length": len(content),
                "section": section if section else None
            }
        )


__all__ = [
    'TextExtractor',
    'TableExtractor', 
    'ImageExtractor',
    'MultiModalParser',
    'ModalityAwareChunker'
]
