"""Hybrid retrieval with two-layer architecture: semantic search + page-scoped expansion"""
from typing import List, Dict, Optional
from models import ModalityType
from embeddings import ModalityReranker
import numpy as np
import re


class HybridRetriever:
    """Two-layer retrieval: semantic search then page-scoped context expansion"""
    
    def __init__(self, vector_store, embedder):
        self.vector_store = vector_store
        self.embedder = embedder
        self.reranker = ModalityReranker()
    
    def retrieve(self, query: str, top_k: int = 5, 
                use_reranking: bool = True,
                use_rrf: bool = False) -> List[Dict]:
        """Main retrieval: Layer 1 (semantic search) + Layer 2 (page-scoped expansion)"""
        modality_preference = self._detect_modality_preference(query)
        table_number = self._extract_table_reference(query)
        
        print(f"\n{'='*60}")
        print(f"[LAYER 1] PRIMARY RETRIEVAL")
        print(f"  Query: {query[:80]}...")
        print(f"  Modality preference: {modality_preference}")
        if table_number:
            print(f"  Explicit table reference: Table {table_number}")
        print(f"{'='*60}\n")
        
        query_embedding = self.embedder.embed_query(query)
        
        comparative_keywords = ['vs', 'versus', 'compare', 'comparison', 'differ', 'difference', 'different', 
                               'evolution', 'transition', 'across', 'between']
        is_comparative = any(kw in query.lower() for kw in comparative_keywords) or \
                        len(re.findall(r'\b(NDS\d+|strategy\s+\d+|version\s+\d+)\b', query, re.IGNORECASE)) > 1
        
        initial_k = top_k * 15 if (table_number or is_comparative) else top_k * 5
        semantic_results = self.vector_store.query(
            query_embedding=query_embedding,
            top_k=initial_k,
            modality_filter=modality_preference if modality_preference else None
        )
        
        if modality_preference and not semantic_results:
            print(f"[RETRY] No results with {modality_preference} filter, retrying without filter...")
            semantic_results = self.vector_store.query(
                query_embedding=query_embedding,
                top_k=initial_k,
                modality_filter=None
            )
        
        if table_number is not None:
            semantic_results = self._filter_by_table_number(semantic_results, table_number)
            
            if not semantic_results:
                print(f"[ERROR] Table {table_number} not found in document")
                return []
            
            print(f"[LAYER 1] Locked to Table {table_number}: {len(semantic_results)} chunks")
        
        if use_reranking and not table_number:
            semantic_results = self.reranker.rerank(semantic_results, query)
        
        if is_comparative:
            primary_k = min(7, top_k * 2)
        else:
            primary_k = min(5, top_k)
        primary_chunks = semantic_results[:primary_k]
        
        print(f"[LAYER 1] Selected {len(primary_chunks)} PRIMARY chunks")
        for i, chunk in enumerate(primary_chunks, 1):
            print(f"  {i}. {chunk['modality']} | Page {chunk['page']} | Score: {chunk['score']:.3f}")
            if chunk.get('label'):
                print(f"     Label: {chunk['label']}")
        
        print(f"\n[LAYER 2] PAGE-SCOPED CONTEXT EXPANSION")
        enriched_results = self._expand_with_page_context(primary_chunks, query)
        
        print(f"[LAYER 2] Final result: {len(enriched_results)} chunks (with context)")
        print(f"{'='*60}\n")
        
        return enriched_results
    
    def _extract_table_reference(self, query: str) -> Optional[int]:
        """Extracts table number from query if mentioned"""
        query_lower = query.lower()
        patterns = [
            r'\btable\s+(\d+)\b',
            r'\btable\s+([ivxlcdm]+)\b',  # Roman numerals
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                table_ref = match.group(1)
                try:
                    return int(table_ref)
                except ValueError:
                    return self._roman_to_int(table_ref)
        
        return None
    
    def _detect_modality_preference(self, query: str) -> Optional[ModalityType]:
        """Detects if query prefers tables, figures, or text"""
        query_lower = query.lower()
        strong_figure_keywords = [
            'figure', 'text figure', 'chart', 'graph', 'diagram', 
            'visualization', 'plot', 'panel', 'outturn', 'outturns',
            'trend', 'trends', 'shows', 'illustrates', 'depicts',
            'real gdp growth outturn', 'productivity', 'tfp'
        ]
        
        # Table indicators (but not exclusive)
        table_keywords = [
            'table', 'data', 'statistics', 'rate', 'percentage', 
            'growth rate', 'projection', 'forecast', 'gdp', 'inflation'
        ]
        
        figure_score = sum(1 for kw in strong_figure_keywords if kw in query_lower)
        table_score = sum(1 for kw in table_keywords if kw in query_lower)
        
        if 'figure' in query_lower or figure_score >= 2:
            return ModalityType.FIGURE
        
        if 'table' in query_lower and table_score > 0:
            return ModalityType.TABLE
        
        if figure_score > 0 and table_score > 0:
            return None
        
        return None
    
    def _expand_with_page_context(self, primary_chunks: List[Dict], query: str) -> List[Dict]:
        """Layer 2: Adds text context from same page for tables/figures"""
        enriched_results = []
        processed_pages = set()
        
        for primary in primary_chunks:
            modality = primary['modality']
            page_num = primary['page']
            
            enriched_results.append(primary)
            
            if page_num in processed_pages:
                continue
            
            processed_pages.add(page_num)
            
            if modality == 'table':
                context_chunks = self._get_page_text_context(page_num, max_chunks=1)
                print(f"[EXPAND] Table on page {page_num} → Added {len(context_chunks)} text chunks")
                enriched_results.extend(context_chunks)
            
            elif modality == 'figure':
                context_chunks = self._get_page_text_context(page_num, max_chunks=1)
                print(f"[EXPAND] Figure on page {page_num} → Added {len(context_chunks)} text chunks")
                enriched_results.extend(context_chunks)
        
        return enriched_results
    
    def _get_page_text_context(self, page_num: int, max_chunks: int = 1) -> List[Dict]:
        """Gets text chunks from specific page for context expansion"""
        try:
            context_chunks = self.vector_store.get_chunks_by_page(
                page_num=page_num,
                modality="text",
                limit=max_chunks
            )
            
            if not context_chunks:
                print(f"[EXPAND] No text chunks found on page {page_num}")
                return []
            
            for chunk in context_chunks:
                content = chunk.get('content', '')
                if len(content) > 500:
                    chunk['content'] = content[:500] + "..."
                chunk['is_context'] = True
                chunk['modality'] = 'text'
            
            print(f"[EXPAND] Retrieved {len(context_chunks)} text chunks from page {page_num}")
            return context_chunks
        
        except Exception as e:
            print(f"[ERROR] Failed to get page context for page {page_num}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _filter_by_table_number(self, chunks: List[Dict], table_number: int) -> List[Dict]:
        """Filters to only chunks matching the specified table number (strict matching)"""
        filtered = []
        
        for chunk in chunks:
            if chunk.get('modality') != 'table':
                continue
            
            label = (chunk.get('label') or '').lower()
            section = (chunk.get('section') or '').lower()
            
            strict_pattern = rf'\btable\s+{table_number}\b'
            variations = [
                rf'\btable\s+{table_number}[:\.\s-]',  # Table 1:, Table 1., Table 1 -, Table 1 
                rf'\btable\s+{table_number}\.',  # Table 1.
                rf'\btable\s+{table_number}\s',  # Table 1 followed by space
            ]
            
            matched = False
            
            if label:
                if re.search(strict_pattern, label):
                    matched = True
                elif any(re.search(v, label) for v in variations):
                    matched = True
            
            if not matched and section:
                if re.search(strict_pattern, section):
                    matched = True
                elif any(re.search(v, section) for v in variations):
                    matched = True
            
            if not matched and not label and not section:
                content = (chunk.get('content') or '')[:300].lower()
                if re.search(strict_pattern, content):
                    match = re.search(rf'\btable\s+{table_number}(\D|$)', content)
                    if match:
                        matched = True
            
            if matched:
                if self._is_scenario_table(label + ' ' + section, chunk.get('content', '')):
                    print(f"[FILTER] Skipping scenario table: {label or section}")
                    continue
                
                print(f"[FILTER] ✓ Matched Table {table_number}: {label or section or 'unnamed'} (Page {chunk['page']})")
                filtered.append(chunk)
        
        return filtered
    
    def _is_scenario_table(self, label: str, content: str) -> bool:
        """Checks if table is simulation/scenario (excludes from baseline queries)"""
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
        """Reciprocal Rank Fusion: combines multiple ranking signals"""
        rankings = {
            'semantic': semantic_results,
            'page_proximity': self._rank_by_page_proximity(semantic_results),
            'modality_diversity': self._rank_by_modality_diversity(semantic_results)
        }
        
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
        
        sorted_results = sorted(
            rrf_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        final_results = []
        for item in sorted_results[:top_k]:
            result = item['result']
            result['score'] = item['score']
            final_results.append(result)
        
        return final_results
    
    def _rank_by_page_proximity(self, results: List[Dict]) -> List[Dict]:
        """Ranks by page proximity (groups nearby pages)"""
        page_groups = {}
        for result in results:
            page = result['page']
            if page not in page_groups:
                page_groups[page] = []
            page_groups[page].append(result)
        
        sorted_pages = sorted(
            page_groups.items(),
            key=lambda x: (len(x[1]), -x[0]),
            reverse=True
        )
        
        reranked = []
        for page, group in sorted_pages:
            reranked.extend(group)
        
        return reranked
    
    def _rank_by_modality_diversity(self, results: List[Dict]) -> List[Dict]:
        """Promotes diversity across modalities"""
        modality_counts = {m.value: 0 for m in ModalityType}
        reranked = []
        remaining = results.copy()
        
        while remaining:
            min_modality = min(
                modality_counts.items(),
                key=lambda x: x[1]
            )[0]
            
            for i, result in enumerate(remaining):
                if result['modality'] == min_modality:
                    reranked.append(result)
                    modality_counts[min_modality] += 1
                    remaining.pop(i)
                    break
            else:
                if remaining:
                    result = remaining.pop(0)
                    reranked.append(result)
                    modality_counts[result['modality']] += 1
        
        return reranked
    
    def retrieve_with_context(self, query: str, top_k: int = 5,
                            expand_context: bool = True) -> Dict:
        """Retrieves with expanded context (neighboring chunks)"""
        results = self.retrieve(query, top_k)
        
        if expand_context:
            expanded = self._expand_context(results)
            return {
                'primary': results,
                'expanded': expanded
            }
        
        return {'primary': results, 'expanded': []}
    
    def _expand_context(self, results: List[Dict]) -> List[Dict]:
        """Gets surrounding context chunks"""
        expanded = []
        
        for result in results:
            page = result['page']
            page_chunks = self.vector_store.query(
                query_embedding=self.embedder.embed_query(f"page {page}"),
                top_k=3
            )
            expanded.extend(page_chunks)
        
        seen = set()
        unique_expanded = []
        for chunk in expanded:
            if chunk['id'] not in seen:
                seen.add(chunk['id'])
                unique_expanded.append(chunk)
        
        return unique_expanded