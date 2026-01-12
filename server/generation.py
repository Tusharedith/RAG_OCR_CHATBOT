from typing import Optional, List, Dict
from models import AnswerSchema, Citation, ModalityType
import os
import requests
import json
import re


class AnswerGenerator:
    """Generates answers with citations using Ollama Mistral-7B"""

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "mistral"
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code != 200:
                print(f"Warning: Ollama may not be running at {self.ollama_url}")
        except Exception as e:
            print(f"Warning: Could not connect to Ollama at {self.ollama_url}: {e}")

    def generate_answer(self, query: str, retrieved_chunks: List[Dict]) -> AnswerSchema:
        """Main method: generates answer with citations from retrieved chunks"""
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
        
        has_content = any(
            chunk.get('content', '').strip() and len(chunk.get('content', '').strip()) > 20 
            for chunk in retrieved_chunks
        )
        if not has_content:
            return AnswerSchema(
                answer="Information not found in document.",
                citations=[]
            )
        
        safe_chunks = []
        max_chunks = min(7, len(retrieved_chunks))
        for chunk in retrieved_chunks[:max_chunks]:
            safe_chunk = chunk.copy()
            if safe_chunk.get('content'):
                safe_chunk['content'] = safe_chunk['content'][:800]
            safe_chunks.append(safe_chunk)
        
        context = self._format_context(safe_chunks)
        
        actual_labels = []
        label_mapping = {}
        for i, chunk in enumerate(safe_chunks, 1):
            label = chunk.get('label') or chunk.get('section') or ""
            
            if not label:
                modality = chunk.get('modality', 'text')
                content = chunk.get('content', '')
                label = self._extract_label_from_content(content, modality, chunk.get('page', -1))
            
            if not label:
                modality = chunk.get('modality', 'text')
                if modality == 'table':
                    label = f"Table on page {chunk.get('page', -1)}"
                elif modality == 'figure':
                    label = f"Figure on page {chunk.get('page', -1)}"
                else:
                    label = f"Text on page {chunk.get('page', -1)}"
            
            citation_id = f"🔗{i}"
            actual_labels.append(f"{citation_id}: {label}")
            label_mapping[citation_id] = {
                'label': label,
                'chunk': chunk,
                'index': i
            }
        
        available_sources = "\n".join(actual_labels)

        comparative_keywords = ['vs', 'versus', 'compare', 'comparison', 'differ', 'difference', 'different', 
                               'evolution', 'transition', 'across', 'between', 'how does', 'what are the differences']
        is_comparative = any(kw in query.lower() for kw in comparative_keywords)
        
        prompt = f"""
Question:
{query}

Context:
{context}

Available Sources (YOU MUST USE THESE EXACT NAMES - DO NOT INVENT NAMES):
{available_sources}

CRITICAL INSTRUCTIONS:
1. Answer using ONLY the context above
2. When citing, you MUST use the EXACT label from "Available Sources" above
3. DO NOT say "Table 1" if the source is labeled "Table 11" - use "Table 11" exactly
4. DO NOT say "Figure 3" if the source is labeled "Text Figure 12" - use "Text Figure 12" exactly
5. SYNTHESIZE information: If the context contains related information across multiple sources, 
   synthesize it into a coherent answer. Look across ALL provided sources to find relevant information.
6. For comparative queries (comparing multiple items), examine ALL sources to identify differences, 
   similarities, and evolution across the items mentioned.
7. After mentioning the exact label, immediately add the 🔗 marker (e.g., "According to Table 11 🔗1...")
8. Response length: {"5-8 sentences for this comparative query" if is_comparative else "3-5 sentences"}
9. Only say "Information not found in document" if truly no relevant information exists in ANY of the sources

Return ONLY answer text with 🔗 markers inline.
"""

        try:
            full_prompt = f"{self._get_system_prompt()}\n\n{prompt}"
            
            ollama_request = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 800,
                    "num_ctx": 4096,
                    "num_gpu": 0,
                    "num_thread": 4
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=ollama_request,
                timeout=270
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
            
            answer_text = response.json().get("response", "")
            query_lower = query.lower()
            
            table_keywords = ["table", "data", "statistics", "numbers", "percentage", 
                            "percent", "growth", "gdp", "projection", "forecast",
                            "2023", "2024", "2025", "real gdp", "inflation"]
            figure_keywords = ["figure", "chart", "graph", "trend", "compare", "comparison", "index", 
                             "plot", "show", "tfp", "productivity", "growth rate", "decline"]
            
            is_table_query = any(kw in query_lower for kw in table_keywords)
            is_figure_query = any(kw in query_lower for kw in figure_keywords)
            
            citations: List[Citation] = []
            citation_pattern = r'🔗(\d+)'
            used_citation_ids = set(re.findall(citation_pattern, answer_text))
            
            citation_map = {}
            for i, chunk in enumerate(safe_chunks, start=1):
                citation_id = f"🔗{i}"
                modality = ModalityType(chunk.get("modality", "text"))
                page = chunk.get("page", -1)
                label = chunk.get("label") or chunk.get("section") or ""
                if not label:
                    label = self._extract_label(
                        chunk.get("content", ""), 
                        modality, 
                        chunk.get("section"), 
                        page, 
                        i
                    )
                
                citation_map[str(i)] = {
                    'chunk': chunk,
                    'label': label,
                    'modality': modality,
                    'page': page
                }
            
            if used_citation_ids:
                for cit_id in sorted(used_citation_ids, key=int):
                    if cit_id in citation_map:
                        cit_data = citation_map[cit_id]
                        chunk = cit_data['chunk']
                        citations.append(
                            Citation(
                                id=f"🔗{cit_id}",
                                label=cit_data['label'],
                                page=cit_data['page'],
                                modality=cit_data['modality'],
                                excerpt=chunk.get("content", "")[:200]
                            )
                        )
            else:
                for i, chunk in enumerate(safe_chunks, start=1):
                    modality = ModalityType(chunk.get("modality", "text"))
                    page = chunk.get("page", -1)
                    label = chunk.get("label") or chunk.get("section") or ""
                    if not label:
                        label = self._extract_label(
                            chunk.get("content", ""), 
                            modality, 
                            chunk.get("section"), 
                            page, 
                            i
                        )
                    
                    citations.append(
                        Citation(
                            id=f"🔗{i}",
                            label=label,
                            page=page,
                            modality=modality,
                            excerpt=chunk.get("content", "")[:200]
                        )
                    )

            return AnswerSchema(
                answer=answer_text if answer_text is not None else "",
                citations=citations
            )

        except Exception as e:
            print(f"Generation error: {e}")
            return AnswerSchema(
                answer=f"Error generating answer: {str(e)}",
                citations=[]
            )

    def _extract_label(self, content: str, modality: ModalityType, 
                      section: Optional[str], page: int, index: int) -> str:
        """Extracts label from content or generates fallback"""
        if modality == ModalityType.FIGURE:
            lines = content.strip().split('\n')
            for line in lines:
                line_lower = line.lower().strip()
                patterns = ['text figure', 'figure', 'fig.', 'chart', 'graph', 'diagram']
                for pattern in patterns:
                    if pattern in line_lower:
                        label = line.strip()[:100]
                        if label:
                            return label
            if section:
                return section
            return f"Figure on page {page}"
        
        elif modality == ModalityType.TABLE:
            lines = content.strip().split('\n')
            for line in lines:
                line_lower = line.lower().strip()
                if re.search(r'table\s+\d+', line_lower):
                    label = line.strip()[:100]
                    if label:
                        return label
            if section:
                return section
            return f"Table on page {page}"
        
        else:
            if section:
                return section
            return f"Text on page {page}"
    
    def _extract_label_from_content(self, content: str, modality: str, page: int) -> str:
        """Extract label from content when metadata is missing"""
        if not content:
            return ""
        
        modality_enum = ModalityType(modality) if isinstance(modality, str) else modality
        return self._extract_label(content, modality_enum, None, page, 0)
    
    def _format_context(self, chunks: List[Dict]) -> str:
        """Formats chunks for LLM with labels"""
        formatted = []

        for i, chunk in enumerate(chunks, 1):
            modality = ModalityType(chunk.get('modality', 'text'))
            page = chunk.get('page', -1)
            section = chunk.get('section', '')
            content = chunk.get('content', '')
            
            label = chunk.get('label') or chunk.get('section') or ""
            if not label:
                label = self._extract_label(content, modality, section, page, i)
            
            context_marker = "[CONTEXT]" if chunk.get('is_context') else "[SOURCE]"
            
            formatted.append(f"{context_marker} {i}: {label} (Page {page})\n{content}\n")
        
        return "\n---\n".join(formatted)
    
    def _extract_table_reference(self, query: str) -> Optional[int]:
        """Extracts table number from query if mentioned"""
        query_lower = query.lower()
        match = re.search(r'\btable\s+(\d+)\b', query_lower)
        if match:
            return int(match.group(1))
        
        return None

    def _get_system_prompt(self) -> str:
        """Returns system prompt for LLM"""
        return """You are a precise document analysis assistant. Your role is to answer questions based on provided context from policy documents.

CRITICAL RULES:
1. FAITHFULNESS: Only use information explicitly stated in the provided context.
2. EXACT LABEL USAGE: You will be given a list of "Available Sources" with exact labels. You MUST use these EXACT labels - DO NOT invent or modify them.
   - If the source says "Table 11", you MUST say "Table 11" (NOT "Table 1")
   - If the source says "Text Figure 12", you MUST say "Text Figure 12" (NOT "Figure 3")
   - NEVER guess or approximate table/figure numbers
3. SYNTHESIS ALLOWED: You may synthesize information across multiple sources in the context. If the question asks for comparisons, differences, or evolution, examine ALL provided sources and combine relevant information.
4. CITATIONS: Insert reference markers (🔗1, 🔗2) IMMEDIATELY after mentioning the exact source name.
5. HONESTY: Only say "Information not found in document" if truly no relevant information exists in ANY of the provided sources.
6. NO SPECULATION: Do not infer, extrapolate, or add external knowledge beyond what's in the context.
7. PRECISION: Be accurate with numbers, dates, and technical terms. Copy table values EXACTLY.
8. STYLE: Write clear, natural explanatory answers. For simple queries: 3-5 sentences. For comparative/complex queries: 5-8 sentences.

OUTPUT GUIDELINES:
- Return only the answer text (include 🔗 markers inline where claims are made).
- Match the exact source names from "Available Sources" - do not create your own names.
- For comparative queries, synthesize information from multiple sources when available.

EXAMPLE (answer only):
Q: What is the GDP growth for 2024?
A: According to Table 11 🔗1, the real GDP growth for 2024 is 1.7 percent.

Q: How does NDS3 differ from NDS1?
A: According to Table I.1 🔗1 and the accompanying text 🔗2, NDS3 differs from NDS1 in several ways: [synthesize differences from multiple sources].

Remember: Use the EXACT labels provided in "Available Sources". Synthesize when multiple sources are relevant."""
