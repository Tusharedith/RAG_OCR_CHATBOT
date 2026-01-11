"""
ChromaDB vector store with metadata preservation
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from models import Chunk, ModalityType
import os


class VectorStore:
    """
    ChromaDB-backed vector store with metadata
    Stores: embeddings, content, page, modality, source
    """
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize ChromaDB client"""
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        print(f"ChromaDB initialized at: {persist_directory}")
    
    def create_collection(self, collection_name: str, 
                         embedding_dimension: int = 384) -> None:
        """
        Create or get collection for a document
        """
        try:
            # Delete if exists (for re-indexing)
            try:
                self.client.delete_collection(collection_name)
            except:
                pass
            
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"dimension": embedding_dimension}
            )
            print(f"Created collection: {collection_name}")
        
        except Exception as e:
            print(f"Error creating collection: {e}")
            self.collection = self.client.get_collection(collection_name)
    
    def add_chunks(self, chunks: List[Chunk]) -> int:
        """
        Add chunks to vector store with embeddings and metadata
        """
        if not chunks:
            return 0
        
        ids = [chunk.id for chunk in chunks]
        embeddings = [chunk.embedding for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        
        # Prepare metadata (ChromaDB requires dict of lists)
        metadatas = []
        for chunk in chunks:
            metadata = {
                "page": chunk.page,
                "modality": chunk.modality.value,
                "source": chunk.source,
                "chunk_index": chunk.metadata.get("chunk_index", 0) if chunk.metadata else 0
            }
            # Only add section if it exists and is not None/empty
            if chunk.metadata and chunk.metadata.get("section"):
                metadata["section"] = str(chunk.metadata.get("section"))
            metadatas.append(metadata)
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        print(f"Added {len(chunks)} chunks to vector store")
        return len(chunks)
    
    def query(self, query_embedding: List[float], 
              top_k: int = 5,
              modality_filter: Optional[ModalityType] = None) -> List[Dict]:
        """
        Query vector store with semantic similarity
        
        Args:
            query_embedding: Query vector
            top_k: Number of results
            modality_filter: Optional filter by modality
        
        Returns:
            List of results with metadata
        """
        where_filter = None
        if modality_filter:
            where_filter = {"modality": modality_filter.value}
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]
            formatted_results.append({
                "id": results['ids'][0][i],
                "content": results['documents'][0][i],
                "page": metadata['page'],
                "modality": metadata['modality'],
                "source": metadata['source'],
                "section": metadata.get('section'),  # Preserve section metadata
                "score": 1 - results['distances'][0][i]  # Convert distance to similarity
            })
        
        return formatted_results
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection"""
        count = self.collection.count()
        
        # Get sample to analyze modalities
        if count > 0:
            sample = self.collection.get(limit=min(count, 1000))
            modalities = [m['modality'] for m in sample['metadatas']]
            
            modality_counts = {
                ModalityType.TEXT.value: modalities.count(ModalityType.TEXT.value),
                ModalityType.TABLE.value: modalities.count(ModalityType.TABLE.value),
                ModalityType.FIGURE.value: modalities.count(ModalityType.FIGURE.value),
                ModalityType.FOOTNOTE.value: modalities.count(ModalityType.FOOTNOTE.value),
            }
        else:
            modality_counts = {}
        
        return {
            "total_chunks": count,
            "modality_breakdown": modality_counts
        }
    
    def get_collection(self, collection_name: str):
        """Get existing collection"""
        try:
            self.collection = self.client.get_collection(collection_name)
            return self.collection
        except Exception as e:
            print(f"Collection not found: {e}")
            return None
    
    def delete_collection(self, collection_name: str):
        """Delete a collection"""
        try:
            self.client.delete_collection(collection_name)
            print(f"Deleted collection: {collection_name}")
        except Exception as e:
            print(f"Error deleting collection: {e}")
    
    def list_collections(self) -> List[str]:
        """List all collections"""
        collections = self.client.list_collections()
        return [c.name for c in collections]