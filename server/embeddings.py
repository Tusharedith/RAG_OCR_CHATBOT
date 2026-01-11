"""
Unified embedding strategy for multi-modal content
All modalities normalized to text and embedded in single semantic space
"""
from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np
from models import Chunk, ModalityType


class UnifiedEmbedder:
    """
    Embed all modalities into unified semantic vector space
    Design: Normalize all content to text, use single embedding model
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding model
        
        Args:
            model_name: HuggingFace model from sentence-transformers
                       Options: 
                       - all-MiniLM-L6-v2 (fast, 384 dim)
                       - all-mpnet-base-v2 (better quality, 768 dim)
        """
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"Loaded embedding model: {model_name}, dimension: {self.dimension}")
    
    def embed_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Generate embeddings for all chunks
        Modality-aware preprocessing applied before embedding
        """
        # Prepare texts with modality context
        texts = [self._prepare_text(chunk) for chunk in chunks]
        
        # Batch embedding for efficiency
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        # Attach embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding.tolist()
        
        return chunks
    
    def embed_query(self, query: str) -> List[float]:
        """Embed user query"""
        embedding = self.model.encode(query, convert_to_numpy=True)
        return embedding.tolist()
    
    def _prepare_text(self, chunk: Chunk) -> str:
        """
        Prepare text for embedding with modality-aware prefixes
        This helps the model understand context type
        """
        prefix_map = {
            ModalityType.TEXT: "",  # No prefix for narrative
            ModalityType.TABLE: "[TABLE] ",
            ModalityType.FIGURE: "[FIGURE] ",
            ModalityType.FOOTNOTE: "[FOOTNOTE] ",
            ModalityType.IMAGE_OCR: "[OCR] "
        }
        
        prefix = prefix_map.get(chunk.modality, "")
        
        # Add page context
        text = f"{prefix}Page {chunk.page}: {chunk.content}"
        
        # Truncate if too long (model max: 512 tokens ≈ 2048 chars)
        max_length = 2000
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    
    def compute_similarity(self, embedding1: List[float], 
                          embedding2: List[float]) -> float:
        """Compute cosine similarity between embeddings"""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


class ModalityReranker:
    """
    Rerank results to boost certain modalities based on query
    TABLE queries get highest priority for table chunks
    """
    
    def __init__(self):
        # Keywords that suggest different modalities
        self.table_keywords = ["table", "data", "statistics", "numbers", "percentage", 
                              "percent", "growth", "gdp", "projection", "forecast",
                              "2023", "2024", "2025", "real gdp", "inflation"]
        self.figure_keywords = ["figure", "chart", "graph", "diagram", "visualization", 
                               "trend", "compare", "comparison", "index", "plot", "show",
                               "tfp", "productivity", "growth rate", "decline"]
    
    def rerank(self, results: List[dict], query: str, boost_factor: float = 5.0) -> List[dict]:
        """
        Rerank results based on query-modality alignment
        TABLE queries: Prioritize table chunks exclusively
        FIGURE queries: Prioritize figure chunks
        """
        query_lower = query.lower()
        
        # Detect preferred modality from query
        prefers_table = any(kw in query_lower for kw in self.table_keywords)
        prefers_figure = any(kw in query_lower for kw in self.figure_keywords)
        
        # TABLE QUERIES: Use tables exclusively if available
        if prefers_table:
            table_results = [r for r in results if r.get('modality') == ModalityType.TABLE.value]
            
            if table_results:
                # Boost table scores massively
                for result in table_results:
                    result['score'] *= boost_factor * 3
                
                # Severely penalize non-table results
                for result in results:
                    if result.get('modality') != ModalityType.TABLE.value:
                        result['score'] *= 0.1
        
        # FIGURE QUERIES: Prioritize figures
        elif prefers_figure:
            figure_results = [r for r in results if r.get('modality') == ModalityType.FIGURE.value]
            
            if figure_results:
                # Boost figure scores significantly
                for result in figure_results:
                    result['score'] *= boost_factor * 2
                
                # Keep non-figure results but with lower scores
                for result in results:
                    if result.get('modality') != ModalityType.FIGURE.value:
                        result['score'] *= 0.3
        
        # Re-sort by adjusted scores
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results