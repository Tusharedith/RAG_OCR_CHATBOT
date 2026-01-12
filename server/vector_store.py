"""ChromaDB vector store for embeddings and metadata"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from models import Chunk, ModalityType
import os


class VectorStore:
    """ChromaDB wrapper: stores embeddings, content, page, modality"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
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
        """Adds chunks with embeddings and metadata to ChromaDB"""
        if not chunks:
            return 0
        
        ids = [chunk.id for chunk in chunks]
        embeddings = [chunk.embedding for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        
        metadatas = []
        for chunk in chunks:
            metadata = {
                "page": chunk.page,
                "modality": chunk.modality.value,
                "source": chunk.source,
                "chunk_index": chunk.metadata.get("chunk_index", 0) if chunk.metadata else 0
            }
            if chunk.label:
                metadata["label"] = str(chunk.label)
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
        """Queries vector store with semantic similarity"""
        where_filter = None
        if modality_filter:
            where_filter = {"modality": modality_filter.value}
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        formatted_results = []
        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]
            formatted_results.append({
                "id": results['ids'][0][i],
                "content": results['documents'][0][i],
                "page": metadata['page'],
                "modality": metadata['modality'],
                "source": metadata['source'],
                "label": metadata.get('label'),
                "section": metadata.get('section'),
                "score": 1 - results['distances'][0][i]
            })
        
        return formatted_results
    
    def get_collection_stats(self) -> Dict:
        """Returns collection statistics"""
        count = self.collection.count()
        
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
    
    def get_chunks_by_page(self, page_num: int, modality: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Gets chunks from specific page, optionally filtered by modality"""
        try:
            if modality:
                where_filter = {
                    "$and": [
                        {"page": int(page_num)},
                        {"modality": str(modality)}
                    ]
                }
            else:
                where_filter = {"page": int(page_num)}
            
            results = self.collection.get(
                where=where_filter,
                limit=limit,
                include=["documents", "metadatas"]
            )
            
            formatted_results = []
            if results and results.get('ids') and len(results['ids']) > 0:
                for i in range(len(results['ids'])):
                    metadata = results['metadatas'][i]
                    formatted_results.append({
                        "id": results['ids'][i],
                        "content": results['documents'][i],
                        "page": int(metadata.get('page', page_num)),
                        "modality": metadata.get('modality', 'text'),
                        "source": metadata.get('source', ''),
                        "label": metadata.get('label'),
                        "section": metadata.get('section'),
                        "score": 0.5
                    })
            
            return formatted_results
        
        except Exception as e:
            print(f"Error getting chunks by page {page_num} (modality={modality}): {e}")
            import traceback
            traceback.print_exc()
            return []
    
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