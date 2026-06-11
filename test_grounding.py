import sys
import logging
from retriever import Retriever
from generator import RAGGenerator

# Setup logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REFUSAL_EXPECTED = "I'm sorry, but I cannot answer that question as the retrieved context does not contain the necessary information."

OUT_OF_BOUNDS_QUERIES = [
    "What is the capital of France?",
    "Write a quick python script to reverse a linked list.",
    "Who won the 2022 FIFA World Cup?"
]

EVAL_QUESTIONS = [
    "What are some things which a new student can expect to be provided with at UCF Orientations ?",
    "Where can new students make reservations for visiting campus ?",
    "How are the dining halls at UCF ?",
    "How is the internet generally at UCF ?",
    "How good is the professor Travis Meade for COP3502C ?"
]

def run_grounding_tests():
    print("=" * 80)
    print("INITIALIZING RAG PIPELINE COMPONENTS FOR GROUNDING VERIFICATION")
    print("=" * 80)
    try:
        retriever = Retriever()
        generator = RAGGenerator()
    except Exception as e:
        print(f"Error initializing pipeline components: {e}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("PHASE 1: TESTING STRICT GROUNDING (OUT-OF-BOUNDS QUESTIONS)")
    print("=" * 80)
    
    passed_refusals = True
    for query in OUT_OF_BOUNDS_QUERIES:
        print(f"\nQuery: '{query}'")
        # Retrieve context
        hits = retriever.retrieve(query, top_k=5)
        # Generate response
        response_chunks = list(generator.generate_response_stream(query, hits, []))
        full_response = "".join(response_chunks).strip()
        
        print(f"Response: \"{full_response}\"")
        if REFUSAL_EXPECTED in full_response:
            print("🟢 SUCCESS: Bot correctly refused to answer (Grounded!).")
        else:
            print("🔴 FAIL: Bot failed to refuse or hallucinated an answer!")
            passed_refusals = False
            
    print("\n" + "=" * 80)
    print("PHASE 2: RUNNING EVALUATION QUESTIONS WITH CITATION CHECKS")
    print("=" * 80)
    
    passed_citations = True
    for idx, query in enumerate(EVAL_QUESTIONS):
        print(f"\nEvaluation Question {idx+1}: '{query}'")
        print("-" * 80)
        
        # Retrieve context
        hits = retriever.retrieve(query, top_k=5)
        print(f"Retrieved {len(hits)} source chunks.")
        
        # Generate response
        response_chunks = list(generator.generate_response_stream(query, hits, []))
        full_response = "".join(response_chunks).strip()
        
        print(f"Grounded Response:\n{full_response}\n")
        
        # Verify if citation brackets exist in the response
        has_citation = "[" in full_response and "]" in full_response
        if has_citation:
            print("🟢 CITATION CHECK: PASSED (Contains inline citation brackets)")
        else:
            print("🔴 CITATION CHECK: FAILED (No source citation found)")
            passed_citations = False
            
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    if passed_refusals:
        print("🟢 Grounding Refusal Checks: ALL PASSED")
    else:
        print("🔴 Grounding Refusal Checks: FAILED")
        
    if passed_citations:
        print("🟢 Inline Citations Checks: ALL PASSED")
    else:
        print("🔴 Inline Citations Checks: FAILED")
        
    if passed_refusals and passed_citations:
        print("\n🎉 ALL PIPELINE GROUNDING TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\n❌ SOME PIPELINE GROUNDING TESTS FAILED. PLEASE CHECK LOGS.")
        sys.exit(1)

if __name__ == "__main__":
    run_grounding_tests()
