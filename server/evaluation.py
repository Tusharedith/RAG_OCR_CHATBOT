"""
Evaluation suite for multi-modal RAG system
Tests faithfulness, citation accuracy, and modality retrieval
"""
from typing import List, Dict
from models import EvaluationRecord, ModalityType
import json


class RAGEvaluator:
    """
    Comprehensive evaluation framework
    Tests: faithfulness, citations, modality retrieval, answer quality
    """
    
    def __init__(self, retriever, generator):
        self.retriever = retriever
        self.generator = generator
        self.results = []
    
    def create_benchmark(self, document_name: str) -> List[EvaluationRecord]:
        """
        Create benchmark queries for a document
        These should be manually curated for your specific documents
        """
        # Example benchmark for IMF Article IV report
        benchmark = [
            EvaluationRecord(
                query="What does Figure 6 indicate about NPLs?",
                expected_page=24,
                expected_modality=ModalityType.FIGURE
            ),
            EvaluationRecord(
                query="What is the GDP growth rate shown in the summary table?",
                expected_page=5,
                expected_modality=ModalityType.TABLE
            ),
            EvaluationRecord(
                query="What are the main fiscal risks mentioned in the report?",
                expected_page=18,
                expected_modality=ModalityType.TEXT
            ),
            EvaluationRecord(
                query="What does Table 3 show about debt sustainability?",
                expected_page=22,
                expected_modality=ModalityType.TABLE
            ),
            EvaluationRecord(
                query="What recommendations are provided in the conclusion?",
                expected_page=75,
                expected_modality=ModalityType.TEXT
            )
        ]
        
        return benchmark
    
    def run_evaluation(self, benchmark: List[EvaluationRecord], 
                      top_k: int = 5) -> Dict:
        """
        Run full evaluation on benchmark
        
        Returns:
            Evaluation metrics and detailed results
        """
        results = []
        
        for record in benchmark:
            # Retrieve
            retrieved = self.retriever.retrieve(record.query, top_k=top_k)
            
            # Generate answer
            answer = self.generator.generate_answer(record.query, retrieved)
            
            # Check correctness
            retrieved_pages = [r['page'] for r in retrieved]
            retrieved_modalities = [r['modality'] for r in retrieved]
            
            # Page hit@k
            page_correct = record.expected_page in retrieved_pages
            
            # Modality match
            modality_correct = record.expected_modality.value in retrieved_modalities
            
            # Update record
            record.retrieved_page = retrieved_pages[0] if retrieved_pages else None
            record.retrieved_modality = ModalityType(retrieved_modalities[0]) if retrieved_modalities else None
            record.correct = page_correct and modality_correct
            record.answer = answer.answer
            
            results.append(record)
        
        # Compute metrics
        metrics = self._compute_metrics(results)
        
        self.results = results
        return metrics
    
    def _compute_metrics(self, results: List[EvaluationRecord]) -> Dict:
        """Compute evaluation metrics"""
        total = len(results)
        
        page_accuracy = sum(1 for r in results if r.correct) / total
        
        # Hit@1 (top result contains correct page)
        hit_at_1 = sum(1 for r in results if r.retrieved_page == r.expected_page) / total
        
        # Modality accuracy
        modality_accuracy = sum(
            1 for r in results 
            if r.retrieved_modality == r.expected_modality
        ) / total
        
        # Citation presence
        has_citations = sum(
            1 for r in results 
            if r.answer and "page" in r.answer.lower()
        ) / total
        
        return {
            "total_queries": total,
            "page_accuracy": page_accuracy,
            "hit_at_1": hit_at_1,
            "modality_accuracy": modality_accuracy,
            "citation_rate": has_citations,
            "overall_score": (page_accuracy + modality_accuracy + has_citations) / 3
        }
    
    def evaluate_faithfulness(self, answer: str, retrieved_chunks: List[Dict]) -> float:
        """
        Evaluate faithfulness score
        Check if answer only uses information from retrieved chunks
        """
        # Simple heuristic: check if key terms from answer appear in context
        context_text = " ".join([c['content'] for c in retrieved_chunks])
        
        # Extract key terms from answer (simplified)
        answer_terms = set(answer.lower().split())
        context_terms = set(context_text.lower().split())
        
        # Faithfulness = overlap ratio
        overlap = len(answer_terms & context_terms)
        faithfulness = overlap / len(answer_terms) if answer_terms else 0
        
        return min(faithfulness, 1.0)
    
    def evaluate_citation_accuracy(self, answer_obj, retrieved_chunks: List[Dict]) -> Dict:
        """
        Check if citations are accurate
        """
        cited_pages = [c.page for c in answer_obj.citations]
        retrieved_pages = [c['page'] for c in retrieved_chunks]
        
        # All cited pages should be in retrieved pages
        correct_citations = all(p in retrieved_pages for p in cited_pages)
        
        # Citation coverage (% of retrieved pages cited)
        coverage = len(set(cited_pages)) / len(set(retrieved_pages)) if retrieved_pages else 0
        
        return {
            "correct_citations": correct_citations,
            "citation_coverage": coverage,
            "num_citations": len(cited_pages)
        }
    
    def generate_report(self, output_file: str = "evaluation_report.json"):
        """Generate detailed evaluation report"""
        if not self.results:
            print("No results to report. Run evaluation first.")
            return
        
        report = {
            "metrics": self._compute_metrics(self.results),
            "results": [
                {
                    "query": r.query,
                    "expected_page": r.expected_page,
                    "retrieved_page": r.retrieved_page,
                    "expected_modality": r.expected_modality.value,
                    "retrieved_modality": r.retrieved_modality.value if r.retrieved_modality else None,
                    "correct": r.correct,
                    "answer_preview": r.answer[:200] if r.answer else None
                }
                for r in self.results
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Evaluation report saved to {output_file}")
        return report
    
    def print_summary(self):
        """Print evaluation summary to console"""
        if not self.results:
            print("No results available.")
            return
        
        metrics = self._compute_metrics(self.results)
        
        print("\n" + "="*50)
        print("EVALUATION SUMMARY")
        print("="*50)
        print(f"Total Queries: {metrics['total_queries']}")
        print(f"Page Accuracy: {metrics['page_accuracy']:.2%}")
        print(f"Hit@1: {metrics['hit_at_1']:.2%}")
        print(f"Modality Accuracy: {metrics['modality_accuracy']:.2%}")
        print(f"Citation Rate: {metrics['citation_rate']:.2%}")
        print(f"Overall Score: {metrics['overall_score']:.2%}")
        print("="*50 + "\n")
        
        # Print failures
        failures = [r for r in self.results if not r.correct]
        if failures:
            print(f"Failed Queries ({len(failures)}):")
            for r in failures:
                print(f"  - {r.query}")
                print(f"    Expected: Page {r.expected_page}, {r.expected_modality.value}")
                print(f"    Got: Page {r.retrieved_page}, {r.retrieved_modality.value if r.retrieved_modality else 'N/A'}\n")