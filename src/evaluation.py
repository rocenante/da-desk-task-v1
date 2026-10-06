
## src/evaluation.py

"""Evaluate the extraction and retrieval quality of the tariff RAG pipeline."""

import json
from src.extraction import PromptExtractor
from src.retriever import TariffRetriever
from src.ingestion import initialize_vector_store


def evaluate_pipeline():
    # Load the hand-curated evaluation dataset that contains expected vessel and port values.
    with open("tests/eval_dataset.json", "r") as f:
        test_cases = json.load(f)
        
    vector_store = initialize_vector_store()
    extractor = PromptExtractor()
    retriever = TariffRetriever(vector_store)
    
    extraction_scores = []
    retrieval_scores = []
    
    for case in test_cases:
        query = case["user_query"]
        
        # 1. Test Entity Extraction
        extracted = extractor.extract(query)
        gt_match = extracted.get("gross_tonnage") == case["expected_gt"]
        port_match = extracted.get("port_name", "").lower() == case["expected_port"].lower()
        extraction_scores.append(1.0 if (gt_match and port_match) else 0.0)
        
        # 2. Test Retrieval Coverage
        context = retriever.get_relevant_context(query)
        keywords_found = sum(1 for kw in case["ground_truth_context_keywords"] if kw.lower() in context.lower())
        retrieval_score = keywords_found / len(case["ground_truth_context_keywords"])
        retrieval_scores.append(retrieval_score)
        
    print(f"Extraction Accuracy: {sum(extraction_scores) / len(test_cases) * 100:.2f}%")
    print(f"Average Retrieval Coverage: {sum(retrieval_scores) / len(test_cases) * 100:.2f}%")

if __name__ == "__main__":
    evaluate_pipeline()