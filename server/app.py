"""FastAPI backend: PDF upload, query processing, answer generation"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import shutil
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from models import Query, UploadResponse, AnswerSchema
from ingestion import MultiModalParser, ModalityAwareChunker
from embeddings import UnifiedEmbedder
from vector_store import VectorStore
from retrieval import HybridRetriever
from generation import AnswerGenerator
from evaluation import RAGEvaluator

app = FastAPI(
    title="Multi-Modal RAG Chatbot",
    description="Production-grade RAG system for complex policy documents",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

embedder = None
vector_store = None
generator = None
retriever = None

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.on_event("startup")
async def startup_event():
    """Initializes system components on startup"""
    global embedder, vector_store, generator, retriever
    
    print("Initializing Multi-Modal RAG System...")
    embedder = UnifiedEmbedder(model_name="all-MiniLM-L6-v2")
    vector_store = VectorStore(persist_directory="./chroma_db")
    
    try:
        generator = AnswerGenerator()
        print("Answer generator initialized with Ollama (Mistral-7B)")
    except Exception as e:
        print(f"Warning: Answer generator not initialized: {e}")
        generator = None
    
    print("System ready!")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "Multi-Modal RAG Chatbot API",
        "version": "1.0.0"
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Uploads PDF, parses multi-modal content, chunks, embeds, stores in ChromaDB"""
    global retriever
    
    try:
        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"Processing: {file.filename}")
        
        parser = MultiModalParser()
        elements = parser.parse_pdf(str(file_path))
        print(f"Extracted {len(elements)} elements")
        
        chunker = ModalityAwareChunker(text_chunk_size=700, overlap=100)
        chunks = chunker.chunk_elements(elements, source=file.filename)
        print(f"Created {len(chunks)} chunks")
        
        chunks = embedder.embed_chunks(chunks)
        print("Embeddings generated")
        
        collection_name = file.filename.replace(".pdf", "").replace(" ", "_")
        vector_store.create_collection(
            collection_name=collection_name,
            embedding_dimension=embedder.dimension
        )
        vector_store.add_chunks(chunks)
        retriever = HybridRetriever(vector_store, embedder)
        stats = vector_store.get_collection_stats()
        pages = set(chunk.page for chunk in chunks)
        num_pages = len(pages)
        
        return UploadResponse(
            document_id=collection_name,
            filename=file.filename,
            num_chunks=stats['total_chunks'],
            num_pages=num_pages,
            modality_breakdown=stats['modality_breakdown']
        )
    
    except Exception as e:
        import traceback
        print(f"\n❌ Upload error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/query", response_model=AnswerSchema)
async def query_document(query: Query):
    """Queries document: retrieves chunks, generates answer with citations"""
    if not retriever or not generator:
        raise HTTPException(
            status_code=400, 
            detail="System not initialized. Upload a document first."
        )
    
    try:
        vector_store.get_collection(query.document_id)
        retrieved_chunks = retriever.retrieve(
            query=query.question,
            top_k=query.top_k,
            use_reranking=True,
            use_rrf=False
        )
        
        print(f"Retrieved {len(retrieved_chunks)} chunks for: {query.question}")
        answer = generator.generate_answer(
            query=query.question,
            retrieved_chunks=retrieved_chunks
        )
        
        print(f"\n[API] Returning answer with {len(answer.citations)} citations")
        for i, cit in enumerate(answer.citations, 1):
            print(f"  Citation {i}: id={cit.id}, label={cit.label}, page={cit.page}, modality={cit.modality}")
        
        return answer
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/documents")
async def list_documents():
    """List all uploaded documents"""
    collections = vector_store.list_collections()
    return {"documents": collections}


@app.get("/document/{document_id}/stats")
async def document_stats(document_id: str):
    """Get statistics for a specific document"""
    try:
        vector_store.get_collection(document_id)
        stats = vector_store.get_collection_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Document not found: {str(e)}")


@app.delete("/document/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and its collection"""
    try:
        vector_store.delete_collection(document_id)
        return {"message": f"Document {document_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


@app.post("/evaluate")
async def run_evaluation(document_id: str):
    """
    Run evaluation suite on a document
    Returns metrics and detailed results
    """
    if not retriever or not generator:
        raise HTTPException(
            status_code=400,
            detail="System not initialized"
        )
    
    try:
        # Switch to document collection
        vector_store.get_collection(document_id)
        
        # Create evaluator
        evaluator = RAGEvaluator(retriever, generator)
        
        # Create benchmark (customize for your document)
        benchmark = evaluator.create_benchmark(document_id)
        
        # Run evaluation
        metrics = evaluator.run_evaluation(benchmark, top_k=5)
        
        # Generate report
        report = evaluator.generate_report(
            output_file=f"evaluation_{document_id}.json"
        )
        
        return report
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)