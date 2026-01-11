from typing import Optional, List, Dict
from models import AnswerSchema, Citation, ModalityType
import os
import requests
import json
import re


class AnswerGenerator:
    """
    Generate faithful, citation-backed answers using Ollama (Mistral-7B)
    Core principle: Never answer beyond retrieved context
    """

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        """
        Initialize with Ollama local endpoint
        """
        self.ollama_url = ollama_url
        self.model = "mistral"
        
        # Test connection to Ollama
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code != 200:
                print(f"Warning: Ollama may not be running at {self.ollama_url}")
        except Exception as e:
            print(f"Warning: Could not connect to Ollama at {self.ollama_url}: {e}")

    def generate_answer(self, query: str, retrieved_chunks: List[Dict]) -> AnswerSchema:
        """
        Generate structured answer with ChatGPT-style clickable citations

        Args:
            query: User question
            retrieved_chunks: Retrieved context chunks with metadata

        Returns:
            AnswerSchema with answer text and clickable citations
        """
        # CRITICAL: Check if retrieved chunks are empty (table not found)
        if not retrieved_chunks:
            table_ref = self._extract_table_reference(query)
            if table_ref:
                return AnswerSchema(
                    answer=f"Table {table_ref} was not found in the document.",
                    citations=[]
                )
            else:
                return AnswerSchema(
                    answer="Information not found in document.",
                    citations=[]
                )
        
        # Token safety: Limit to top 2 chunks and trim content aggressively
        safe_chunks = []
        for chunk in retrieved_chunks[:2]:  # Reduced from 3 to 2 for speed
            safe_chunk = chunk.copy()
            # Trim content to 600 characters to prevent token overflow and speed up processing
            if safe_chunk.get('content'):
                safe_chunk['content'] = safe_chunk['content'][:600]
            safe_chunks.append(safe_chunk)
        
        # Format context for model
        context = self._format_context(safe_chunks)

        # Construct prompt for natural explanatory response with table/figure faithfulness
        prompt = f"""
Question:
{query}

Context:
{context}

Instructions:
- Answer the question clearly and completely using ONLY the provided context.
- Write a natural explanatory response (around 8-9 sentences if needed).
- If helpful, include 2-3 brief bullet points for clarity (optional).
- Do NOT force a fixed structure; be natural but precise.

CRITICAL - For TABLE questions:
- Copy numeric values EXACTLY as shown in the table - do NOT convert, estimate, or infer.
- Preserve units (%, QAR billions, etc.) exactly as stated.
- Always mention the table name: "According to Table 1..." or "Table X shows..."
- If the table shows "Real GDP growth (%): 2024: 2.0", report EXACTLY "2.0%" NOT "2 percent" or "two percent".

CRITICAL - For FIGURE/CHART questions:
- EXPLICITLY name the figure: "As shown in Text Figure 3..." or "Text Figure 5 demonstrates..."
- NEVER use vague phrases like "the figure" or "the chart" - always include the full name.

CRITICAL - For OCR content (image_ocr modality):
- Reference it naturally: "The scanned page notes that..." or "OCR text indicates..."

- Insert reference markers like 🔗1, 🔗2 IMMEDIATELY after mentioning sources.
- Do NOT invent citations or sources.
- If the answer is not in the context, say exactly: "Information not found in document"

Return ONLY the answer text (with 🔗 markers where applicable).
"""

        # Call Ollama model via HTTP
        try:
            # Combine system prompt and user prompt for Ollama
            full_prompt = f"{self._get_system_prompt()}\n\n{prompt}"
            
            ollama_request = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 800,
                    "num_ctx": 4096,
                    "num_gpu": 0,  # Force CPU usage (disable GPU)
                    "num_thread": 4  # Use 4 CPU threads
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=ollama_request,
                timeout=180  # Increased timeout to 3 minutes
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
            
            # Extract answer from Ollama response
            answer_text = response.json().get("response", "")

            # Detect modality preference from query
            query_lower = query.lower()
            
            table_keywords = ["table", "data", "statistics", "numbers", "percentage", 
                            "percent", "growth", "gdp", "projection", "forecast",
                            "2023", "2024", "2025", "real gdp", "inflation"]
            figure_keywords = ["figure", "chart", "graph", "trend", "compare", "comparison", "index", 
                             "plot", "show", "tfp", "productivity", "growth rate", "decline"]
            
            is_table_query = any(kw in query_lower for kw in table_keywords)
            is_figure_query = any(kw in query_lower for kw in figure_keywords)
            
            # Generate deterministic citations from retrieved chunks
            citations: List[Citation] = []
            
            # For TABLE queries, use ONLY table chunks
            if is_table_query and not is_figure_query:
                table_chunks = [c for c in retrieved_chunks if c.get("modality") == "table"]
                
                if table_chunks:
                    citation_source = table_chunks[:3]  # Use top 3 tables
                else:
                    citation_source = retrieved_chunks[:3]  # Fallback
            
            # For FIGURE queries, prioritize figures
            elif is_figure_query:
                figure_chunks = [c for c in retrieved_chunks if c.get("modality") == "figure"]
                
                if figure_chunks:
                    citation_source = figure_chunks[:3]
                else:
                    citation_source = retrieved_chunks[:3]  # Fallback
            
            # Default: use top chunks
            else:
                citation_source = retrieved_chunks[:3]
            
            for i, chunk in enumerate(citation_source, start=1):
                modality = ModalityType(chunk.get("modality", "text"))
                page = chunk.get("page", -1)
                section = chunk.get("section", "")
                content = chunk.get("content", "")
                
                # Extract label from content or metadata
                label = self._extract_label(content, modality, section, page, i)
                
                citations.append(
                    Citation(
                        id=f"🔗{i}",
                        label=label,
                        page=page,
                        modality=modality,
                        excerpt=content[:200] if content else ""
                    )
                )

            return AnswerSchema(
                answer=answer_text if answer_text is not None else "",
                citations=citations
            )

        except Exception as e:
            print(f"Generation error: {e}")
            # Return error as structured output
            return AnswerSchema(
                answer=f"Error generating answer: {str(e)}",
                citations=[]
            )

    def _extract_label(self, content: str, modality: ModalityType, 
                      section: Optional[str], page: int, index: int) -> str:
        """Extract or generate descriptive label for citation"""
        if modality == ModalityType.FIGURE:
            # Try to extract figure caption from content
            lines = content.strip().split('\n')
            for line in lines:
                line_lower = line.lower().strip()
                # Look for common figure patterns
                if any(pattern in line_lower for pattern in ['figure', 'fig.', 'chart', 'graph']):
                    # Clean and return the caption
                    label = line.strip()[:100]
                    if label:
                        return label
            # Fallback: use section if available
            if section:
                return f"Figure from '{section}' (Page {page})"
            return f"Figure on Page {page}"
        
        elif modality == ModalityType.TABLE:
            # Try to extract table caption
            lines = content.strip().split('\n')
            for line in lines:
                line_lower = line.lower().strip()
                if any(pattern in line_lower for pattern in ['table', 'tbl.']):
                    label = line.strip()[:100]
                    if label:
                        return label
            # Fallback
            if section:
                return f"Table from '{section}' (Page {page})"
            return f"Table on Page {page}"
        
        else:  # TEXT or FOOTNOTE
            # Use section name if available
            if section:
                return f"{section} (Page {page})"
            return f"Text on Page {page}"
    
    def _format_context(self, chunks: List[Dict]) -> str:
        """Format retrieved chunks into readable context with labels"""
        formatted = []

        for i, chunk in enumerate(chunks, 1):
            modality = ModalityType(chunk.get('modality', 'text'))
            page = chunk.get('page', -1)
            section = chunk.get('section', '')
            content = chunk.get('content', '')
            
            # Generate label for this source
            label = self._extract_label(content, modality, section, page, i)
            
            formatted.append(f"[Source {i}] {label}\n{content}\n")
        
        return "\n---\n".join(formatted)
    
    def _extract_table_reference(self, query: str) -> Optional[int]:
        """
        Extract explicit table number from query
        Returns table number if found, None otherwise
        """
        query_lower = query.lower()
        
        # Match patterns like "table 1", "Table 42"
        match = re.search(r'\btable\s+(\d+)\b', query_lower)
        if match:
            return int(match.group(1))
        
        return None

    def _get_system_prompt(self) -> str:
        """System prompt for ChatGPT-style answers with explicit figure/table naming"""
        return """You are a precise document analysis assistant. Your role is to answer questions strictly based on provided context from policy documents.

CRITICAL RULES:
1. FAITHFULNESS: Only use information explicitly stated in the provided context.
2. EXPLICIT FIGURE/TABLE NAMING: When citing graphs, charts, or tables, ALWAYS use their full names:
   - "As shown in Text Figure 3..."
   - "According to Table 1..."
   - "Text Figure 5 demonstrates..."
   - NEVER say "the figure" or "the chart" without the full name.
3. CITATIONS: Insert reference markers (🔗1, 🔗2) IMMEDIATELY after mentioning figure/table names or making factual claims.
4. HONESTY: If information is not in context, clearly state "Information not found in document".
5. NO SPECULATION: Do not infer, extrapolate, or add external knowledge.
6. PRECISION: Be accurate with numbers, dates, and technical terms.
7. STYLE: Write clear, natural explanatory answers (8-9 sentences if needed). Bullet points are optional for clarity.

OUTPUT GUIDELINES:
- Return only the answer text (include 🔗 markers inline where claims are made).
- The API will attach the corresponding cited sources (id, label, page, modality, excerpt) separately.

EXAMPLE (answer only):
Q: What does the report say about inflation?
A: As shown in Text Figure 3 🔗1, inflation has declined through 2023 and 2024, reflecting easing domestic pressures. According to Table 1 🔗2, the medium-term outlook remains positive due to LNG expansion and reforms.

Remember: Quality over quantity. A precise "Information not found in document" is better than an unfaithful answer."""
