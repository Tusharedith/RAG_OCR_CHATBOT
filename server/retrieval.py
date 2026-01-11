"""
Hybrid retrieval with optional RRF (Reciprocal Rank Fusion)
"""
from typing import List, Dict, Optional
from models import ModalityType
from embeddings import ModalityReranker
import numpy as np
import re


class HybridRetriever:
    """
    Retrieval strategy combining:
    1. Semantic similarity (vector search)
    2. Modality-aware reranking
    3. Optional RRF for bonus marks
    """
    
    def __init__(self, vector_store, embedder):
        self.vector_store = vector_store
        self.embedder = embedder
        self.reranker = ModalityReranker()
    
    def retrieve(self, query: str, top_k: int = 5, 
                use_reranking: bool = True,
                use_rrf: bool = False) -> List[Dict]:
        """
        Main retrieval method with table label locking
        
        Args:
            query: User question
            top_k: Number of results
            use_reranking: Apply modality-aware reranking
            use_rrf: Use Reciprocal Rank Fusion (bonus)
        
        Returns:
            List of retrieved chunks with metadata
        """
        # CRITICAL: Detect explicit table references (e.g., "Table 1", "Table X")
        table_number = self._extract_table_reference(query)
        
        # Step 1: Semantic retrieval
        query_embedding = self.embedder.embed_query(query)
        semantic_results = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=top_k * 3  # Get more for filtering
        )
        
        results = semantic_results
        
        # Step 2: TABLE LABEL LOCKING - If explicit table reference detected
        if table_number is not None:
            print(f"[RETRIEVAL] Detected explicit table reference: Table {table_number}")
            results = self._filter_by_table_number(results, table_number)
            
            if not results:
                print(f"[RETRIEVAL] WARNING: Table {table_number} not found in chunks")
                return []  # Return empty if referenced table doesn't exist
            
            print(f"[RETRIEVAL] Filtered to {len(results)} chunks from Table {table_number}")
        
        # Step 3: Optional RRF (combine multiple ranking signals)
        if use_rrf and not table_number:  # Skip RRF if table-locked
            results = self._apply_rrf(query, results, top_k)
        
        # Step 4: Modality-aware reranking
        if use_reranking and not table_number:  # Skip reranking if table-locked
            results = self.reranker.rerank(results, query)
        
        # Return top_k
        return results[:top_k]
    
    def _extract_table_reference(self, query: str) -> Optional[int]:
        """
        Extract explicit table number from query
        Examples: "Table 1", "According to Table 42", "From table 5"
        
        Returns:
            Table number if found, None otherwise
        """
        query_lower = query.lower()
        
        # Match patterns like "table 1", "table X", "Table 42"
        patterns = [
            r'\btable\s+(\d+)\b',
            r'\btable\s+([ivxlcdm]+)\b',  # Roman numerals
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                table_ref = match.group(1)
                try:
                    # Try to convert to int (handles "1", "42", etc.)
                    return int(table_ref)
                except ValueError:
                    # Handle Roman numerals if needed
                    return self._roman_to_int(table_ref)
        
        return None
    
    def _filter_by_table_number(self, chunks: List[Dict], table_number: int) -> List[Dict]:
        """
        Filter chunks to ONLY those matching the specified table number
        
        Args:
            chunks: All retrieved chunks
            table_number: Explicit table number from query
            
        Returns:
            Only chunks from the specified table
        """
        filtered = []
        
        for chunk in chunks:
            # Only consider table chunks
            if chunk.get('modality') != 'table':
                continue
            
            # Check if section/label contains the table number
            section = chunk.get('section', '').lower()
            
            # Match patterns like "Table 1", "table 1:", "Table 1 -"
            if f'table {table_number}' in section or f'table{table_number}' in section:
                # SAFETY CHECK: Reject simulation/scenario tables for baseline queries
                if self._is_scenario_table(section, chunk.get('content', '')):
                    print(f"[RETRIEVAL] Skipping scenario table: {section}")
                    continue
                
                filtered.append(chunk)
        
        return filtered
    
    def _is_scenario_table(self, label: str, content: str) -> bool:
        """
        Detect if table is simulation/scenario (not baseline projections)
        """
        scenario_keywords = [
            'multiplier', 'simulation', 'scenario', 'stress test',
            'alternative', 'sensitivity', 'shock', 'variance'
        ]
        
        text = (label + ' ' + content[:200]).lower()
        return any(keyword in text for keyword in scenario_keywords)
    
    def _roman_to_int(self, roman: str) -> Optional[int]:
        """Convert Roman numerals to integers"""
        roman_map = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100}
        result = 0
        prev = 0
        
        for char in reversed(roman.lower()):
            val = roman_map.get(char, 0)
            if val < prev:
                result -= val
            else:
                result += val
            prev = val
        
        return result if result > 0 else None
    
    def _apply_rrf(self, query: str, semantic_results: List[Dict], 
                   top_k: int, k: int = 60) -> List[Dict]:
        """
        Reciprocal Rank Fusion (RRF)
        Combines multiple ranking signals
        
        Formula: RRF_score(d) = Σ 1/(k + rank_i(d))
        where rank_i is rank from different retrieval methods
        """
        # Create different ranking signals
        rankings = {
            'semantic': semantic_results,
            'page_proximity': self._rank_by_page_proximity(semantic_results),
            'modality_diversity': self._rank_by_modality_diversity(semantic_results)
        }
        
        # Compute RRF scores
        rrf_scores = {}
        for method_name, ranked_results in rankings.items():
            for rank, result in enumerate(ranked_results, 1):
                doc_id = result['id']
                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = {
                        'score': 0,
                        'result': result
                    }
                rrf_scores[doc_id]['score'] += 1.0 / (k + rank)
        
        # Sort by RRF score
        sorted_results = sorted(
            rrf_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        # Extract results and update scores
        final_results = []
        for item in sorted_results[:top_k]:
            result = item['result']
            result['score'] = item['score']
            final_results.append(result)
        
        return final_results
    
    def _rank_by_page_proximity(self, results: List[Dict]) -> List[Dict]:
        """
        Rank by page proximity (group nearby pages together)
        Useful for documents where related info is clustered
        """
        # Group by page
        page_groups = {}
        for result in results:
            page = result['page']
            if page not in page_groups:
                page_groups[page] = []
            page_groups[page].append(result)
        
        # Sort pages, prioritize pages with multiple hits
        sorted_pages = sorted(
            page_groups.items(),
            key=lambda x: (len(x[1]), -x[0]),  # More hits, then lower page
            reverse=True
        )
        
        # Flatten
        reranked = []
        for page, group in sorted_pages:
            reranked.extend(group)
        
        return reranked
    
    def _rank_by_modality_diversity(self, results: List[Dict]) -> List[Dict]:
        """
        Promote diversity in modalities
        Ensures we don't only retrieve one type
        """
        modality_counts = {m.value: 0 for m in ModalityType}
        reranked = []
        remaining = results.copy()
        
        while remaining:
            # Find least represented modality
            min_modality = min(
                modality_counts.items(),
                key=lambda x: x[1]
            )[0]
            
            # Find first result with that modality
            for i, result in enumerate(remaining):
                if result['modality'] == min_modality:
                    reranked.append(result)
                    modality_counts[min_modality] += 1
                    remaining.pop(i)
                    break
            else:
                # No results with min_modality, take first available
                if remaining:
                    result = remaining.pop(0)
                    reranked.append(result)
                    modality_counts[result['modality']] += 1
        
        return reranked
    
    def retrieve_with_context(self, query: str, top_k: int = 5,
                            expand_context: bool = True) -> Dict:
        """
        Retrieve with expanded context
        Returns both direct matches and surrounding chunks
        """
        # Get primary results
        results = self.retrieve(query, top_k)
        
        # Optionally expand context (get neighboring chunks)
        if expand_context:
            expanded = self._expand_context(results)
            return {
                'primary': results,
                'expanded': expanded
            }
        
        return {'primary': results, 'expanded': []}
    
    def _expand_context(self, results: List[Dict]) -> List[Dict]:
        """
        Get surrounding context for each result
        Useful for getting adjacent paragraphs/sections
        """
        expanded = []
        
        for result in results:
            page = result['page']
            
            # Get chunks from same page
            page_chunks = self.vector_store.query(
                query_embedding=self.embedder.embed_query(f"page {page}"),
                top_k=3
            )
            
            expanded.extend(page_chunks)
        
        # Remove duplicates
        seen = set()
        unique_expanded = []
        for chunk in expanded:
            if chunk['id'] not in seen:
                seen.add(chunk['id'])
                unique_expanded.append(chunk)
        
        return unique_expanded