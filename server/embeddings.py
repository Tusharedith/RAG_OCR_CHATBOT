"""
Unified embedding strategy for multi-modal content - ENHANCED VERSION
Better handling for tables with improved semantic representation
"""
from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np
from models import Chunk, ModalityType


class UnifiedEmbedder:
    """
    Embed all modalities into unified semantic vector space
    ENHANCED: Better preprocessing for tables
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding model
        
        Args:
            model_name: HuggingFace model from sentence-transformers
                       Options: 
                       - all-MiniLM-L6-v2 (fast, 384 dim) - DEFAULT
                       - all-mpnet-base-v2 (better quality, 768 dim)
                       - paraphrase-multilingual-MiniLM-L12-v2 (multilingual)
        """
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"Loaded embedding model: {model_name}, dimension: {self.dimension}")
    
    def embed_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Generate embeddings for all chunks
        ENHANCED: Better preprocessing for different modalities
        """
        # Prepare texts with enhanced modality-aware preprocessing
        texts = [self._prepare_text_enhanced(chunk) for chunk in chunks]
        
        # Batch embedding for efficiency
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for better similarity
        )
        
        # Attach embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding.tolist()
        
        return chunks
    
    def embed_query(self, query: str) -> List[float]:
        """
        Embed user query with query-specific preprocessing
        """
        # Preprocess query to match document preprocessing
        query_processed = self._preprocess_query(query)
        
        embedding = self.model.encode(
            query_processed, 
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embedding.tolist()
    
    def _prepare_text_enhanced(self, chunk: Chunk) -> str:
        """
        ENHANCED text preparation with better modality handling
        """
        content = chunk.content
        page = chunk.page
        modality = chunk.modality
        
        # Different preprocessing for different modalities
        if modality == ModalityType.TABLE:
            return self._prepare_table_text(content, page)
        elif modality == ModalityType.FIGURE:
            return self._prepare_figure_text(content, page)
        elif modality == ModalityType.TEXT:
            return self._prepare_narrative_text(content, page)
        else:
            # Footnotes and others
            return f"[FOOTNOTE] {content[:2000]}"
    
    def _prepare_table_text(self, content: str, page: int) -> str:
        """
        ENHANCED table text preparation for better semantic matching
        """
        # Add explicit table markers and context
        prefix = f"[TABLE DATA] Contains structured data: "
        
        # Extract key information for better matching
        # Tables often contain: categories, values, comparisons
        
        # Normalize common table terms for better matching
        content_normalized = content.replace("=", " equals ").replace("|", " or ")
        
        # Truncate if too long (embedding models have limits)
        max_length = 2000
        if len(content_normalized) > max_length:
            # Prioritize keeping the structure description and first few rows
            parts = content_normalized.split('\n')
            
            # Keep header info
            header_parts = parts[:5]  # Structure, columns, first rows
            remaining_length = max_length - len(' '.join(header_parts))
            
            # Add as many data rows as fit
            data_parts = parts[5:]
            additional = []
            current_length = 0
            for part in data_parts:
                if current_length + len(part) < remaining_length:
                    additional.append(part)
                    current_length += len(part)
                else:
                    break
            
            content_normalized = ' '.join(header_parts + additional)
        
        return f"{prefix}{content_normalized}"
    
    def _prepare_figure_text(self, content: str, page: int) -> str:
        """
        Enhanced figure text preparation
        """
        prefix = f"[FIGURE/CHART] Shows visualization: "
        
        # Truncate if needed
        max_length = 2000
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        return f"{prefix}{content}"
    
    def _prepare_narrative_text(self, content: str, page: int) -> str:
        """
        Prepare narrative text
        """
        # Minimal prefix for text to maintain natural language
        prefix = ""
        
        # Truncate if needed
        max_length = 2000
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        return f"{prefix}{content}"
    
    def _preprocess_query(self, query: str) -> str:
        """
        Preprocess query to improve matching with documents
        """
        query_lower = query.lower()
        
        # Detect if query is asking about tables
        table_keywords = ['table', 'data', 'statistics', 'rate', 'percentage', 
                         'growth', 'numbers', 'figure', 'chart']
        
        is_table_query = any(keyword in query_lower for keyword in table_keywords)
        
        if is_table_query:
            # Add table context to query
            return f"[TABLE DATA] {query}"
        else:
            return query
    
    def compute_similarity(self, embedding1: List[float], 
                          embedding2: List[float]) -> float:
        """Compute cosine similarity between embeddings"""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


class ModalityReranker:
    """
    ENHANCED modality-aware reranking
    Boosts results based on query-modality alignment
    """
    
    def __init__(self):
        # Keywords that suggest different modalities
        self.table_keywords = [
            "table", "data", "statistics", "numbers", "percentage", 
            "rate", "growth", "value", "amount", "total", "average",
            "year", "2023", "2024", "2025", "forecast", "projection"
        ]
        self.figure_keywords = [
            "figure", "chart", "graph", "diagram", "visualization",
            "plot", "shows", "illustrates", "depicts"
        ]
        self.text_keywords = [
            "explain", "describe", "discuss", "mention", "state",
            "analysis", "conclusion", "recommendation", "summary"
        ]
    
    def rerank(self, results: List[dict], query: str, boost_factor: float = 1.5) -> List[dict]:
        """
        ENHANCED reranking with stronger boosting for aligned modalities
        IMPROVED: Better figure detection, less aggressive table boosting
        """
        query_lower = query.lower()
        
        # Enhanced figure keywords (including IMF-specific terms)
        enhanced_figure_keywords = self.figure_keywords + [
            'outturn', 'outturns', 'panel', 'panels', 'real gdp growth outturn',
            'productivity', 'tfp', 'trend', 'trends', 'shows', 'illustrates'
        ]
        
        # Detect preferred modality from query
        table_score = sum(1 for kw in self.table_keywords if kw in query_lower)
        figure_score = sum(1 for kw in enhanced_figure_keywords if kw in query_lower)
        text_score = sum(1 for kw in self.text_keywords if kw in query_lower)
        
        # Determine primary modality preference (figure takes priority if mentioned)
        if 'figure' in query_lower or figure_score >= 2:
            preferred_modality = ModalityType.FIGURE.value
        elif table_score > figure_score and table_score > text_score:
            preferred_modality = ModalityType.TABLE.value
        elif figure_score > text_score:
            preferred_modality = ModalityType.FIGURE.value
        else:
            preferred_modality = ModalityType.TEXT.value
        
        # Apply boosting
        for result in results:
            modality = result.get('modality')
            
            if modality == preferred_modality:
                # Strong boost for matching modality
                result['score'] *= boost_factor
                result['boosted'] = True
            
            # Additional boost if query explicitly mentions table/figure number
            if 'table' in query_lower and modality == ModalityType.TABLE.value:
                result['score'] *= 1.2
            elif ('figure' in query_lower or 'text figure' in query_lower) and modality == ModalityType.FIGURE.value:
                result['score'] *= 1.3  # Higher boost for figures
        
        # Re-sort by adjusted scores
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results