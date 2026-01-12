"""
Pydantic models for structured data validation and enforcement
"""
from pydantic import BaseModel, Field
from typing import Literal, List, Optional
from enum import Enum


class ModalityType(str, Enum):
    """Supported modality types"""
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"
    FOOTNOTE = "footnote"
    IMAGE_OCR = "image_ocr"  # OCR-extracted text from scanned/image pages


class DocumentElement(BaseModel):
    """Structured element extracted from PDF"""
    type: ModalityType
    content: str
    page: int
    section: Optional[str] = None
    metadata: Optional[dict] = None


class Chunk(BaseModel):
    """Chunked document element ready for embedding"""
    id: str
    content: str
    modality: ModalityType
    page: int
    source: str
    label: Optional[str] = None  # Table X, Figure Y, or section title
    embedding: Optional[List[float]] = None
    metadata: Optional[dict] = None


class Citation(BaseModel):
    """Citation with page, modality, label, and supporting excerpt"""
    id: str
    label: str = Field(
        description="Descriptive label (e.g., 'Text Figure 3: Inflation Developments' or 'Table 1: Economic Indicators')"
    )
    page: int
    modality: ModalityType = Field(
        description="Type of content: text, table, or figure"
    )
    excerpt: Optional[str] = Field(
        None,
        description="Brief excerpt from the source"
    )


class AnswerSchema(BaseModel):
    """Structured answer with clickable citations (ChatGPT-style)"""
    answer: str = Field(
        description="Natural explanatory answer with inline 🔗 reference markers. "
                    "If information is not in context, explicitly state 'Information not found in document.'"
    )
    citations: List[Citation] = Field(
        description="List of clickable citations with id (🔗1, 🔗2, ...), page, modality, and excerpt"
    )


class Query(BaseModel):
    """User query model"""
    question: str
    document_id: str
    top_k: int = 5


class UploadResponse(BaseModel):
    """Response after document upload"""
    document_id: str
    filename: str
    num_chunks: int
    num_pages: int
    modality_breakdown: dict


class EvaluationRecord(BaseModel):
    """Evaluation record for testing"""
    query: str
    expected_page: int
    expected_modality: ModalityType
    retrieved_page: Optional[int] = None
    retrieved_modality: Optional[ModalityType] = None
    correct: Optional[bool] = None
    answer: Optional[str] = None