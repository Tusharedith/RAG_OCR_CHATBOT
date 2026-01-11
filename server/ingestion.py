"""
Multi-modal PDF ingestion pipeline with modular extraction
"""
from typing import List, Dict, Optional
import hashlib
from models import DocumentElement, Chunk, ModalityType
from ingestion.pdf_text import TextExtractor
from ingestion.pdf_tables import TableExtractor
from ingestion.pdf_images import ImageExtractor


class MultiModalParser:
    """
    Orchestrator for multi-modal PDF parsing
    Coordinates text, table, and image extraction modules
    """
    
    def __init__(self):
        self.text_extractor = TextExtractor()
        self.table_extractor = TableExtractor()
        self.image_extractor = ImageExtractor()
        self.elements = []
    
    def parse_pdf(self, pdf_path: str) -> List[DocumentElement]:
        """
        Parse PDF using modular extractors
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of DocumentElement objects from all modalities
        """
        elements = []
        
        print(f"\nParsing PDF: {pdf_path}")
        print("=" * 60)
        
        # Extract text elements
        text_elements = self.text_extractor.extract(pdf_path)
        elements.extend(text_elements)
        
        # Extract table elements
        table_elements = self.table_extractor.extract(pdf_path)
        elements.extend(table_elements)
        
        # Extract figure elements with OCR
        figure_elements = self.image_extractor.extract(pdf_path)
        elements.extend(figure_elements)
        
        print("=" * 60)
        print(f"Total elements extracted: {len(elements)}")
        print(f"  Text: {sum(1 for e in elements if e.type == ModalityType.TEXT)}")
        print(f"  Tables: {sum(1 for e in elements if e.type == ModalityType.TABLE)}")
        print(f"  Figures: {sum(1 for e in elements if e.type == ModalityType.FIGURE)}")
        print(f"  Footnotes: {sum(1 for e in elements if e.type == ModalityType.FOOTNOTE)}")
        print("=" * 60)
        
        return elements


class ModalityAwareChunker:
    """Smart chunking strategy based on modality"""
    
    def __init__(self, text_chunk_size: int = 700, overlap: int = 120):
        self.text_chunk_size = text_chunk_size
        self.overlap = overlap
    
    def chunk_elements(self, elements: List[DocumentElement], source: str) -> List[Chunk]:
        """
        Apply modality-specific chunking rules
        Handles text (sliding window), tables (atomic), figures (atomic) as per assignment
        """
        chunks = []
        modality_counts = {"text": 0, "table": 0, "figure": 0, "footnote": 0}
        
        for elem in elements:
            if elem.type == ModalityType.TEXT:
                # Sliding window for narrative text
                text_chunks = self._sliding_window_chunk(elem.content)
                for i, chunk_text in enumerate(text_chunks):
                    chunks.append(self._create_chunk(
                        content=chunk_text,
                        modality=ModalityType.TEXT,
                        page=elem.page,
                        source=source,
                        index=i,
                        section=elem.section
                    ))
                modality_counts["text"] += len(text_chunks)
            
            elif elem.type == ModalityType.TABLE:
                # One table = one chunk (atomic)
                chunks.append(self._create_chunk(
                    content=elem.content,
                    modality=ModalityType.TABLE,
                    page=elem.page,
                    source=source,
                    section=elem.section
                ))
                modality_counts["table"] += 1
            
            elif elem.type == ModalityType.FIGURE:
                # One figure + caption = one chunk (atomic)
                chunks.append(self._create_chunk(
                    content=elem.content,
                    modality=ModalityType.FIGURE,
                    page=elem.page,
                    source=source,
                    section=elem.section
                ))
                modality_counts["figure"] += 1
            
            elif elem.type == ModalityType.FOOTNOTE:
                # Optional: keep as atomic chunk
                chunks.append(self._create_chunk(
                    content=elem.content,
                    modality=ModalityType.FOOTNOTE,
                    page=elem.page,
                    source=source
                ))
                modality_counts["footnote"] += 1
        
        print(f"\nChunking complete - Multi-modal breakdown:")
        print(f"  Text chunks: {modality_counts['text']}")
        print(f"  Table chunks: {modality_counts['table']}")
        print(f"  Figure chunks: {modality_counts['figure']} (OCR-detected)")
        print(f"  Footnote chunks: {modality_counts['footnote']}")
        print(f"  Total: {len(chunks)} chunks")
        
        return chunks
    
    def _sliding_window_chunk(self, text: str) -> List[str]:
        """Sliding window chunking with overlap"""
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
        """Create a chunk with unique ID and metadata"""
        chunk_id = hashlib.md5(
            f"{source}_{page}_{modality.value}_{index}".encode()
        ).hexdigest()
        
        return Chunk(
            id=chunk_id,
            content=content,
            modality=modality,
            page=page,
            source=source,
            metadata={
                "chunk_index": index,
                "content_length": len(content),
                "section": section if section else None
            }
        )