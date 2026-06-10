import os
import sys
import logging

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Add the parent directory of this script to sys.path so we can import modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the main functions from the nested ingestion modules
from ingestion.reddit.download_reddit import main as download_reddit_main
from ingestion.reddit.ingest_reddit import main as ingest_reddit_main
from ingestion.rmp.download_rmp_professors import main as download_rmp_main
from ingestion.rmp.ingest_rmp import main as ingest_rmp_main
from ingestion.syllabus.parse_pdf import main as parse_pdf_main
from ingestion.syllabus.ingest_syllabus import main as ingest_syllabus_main
from ingestion.validate_chunks import validate_chunks

def run_step(step_name, func, *args, **kwargs):
    logging.info(f"==================================================")
    logging.info(f"Starting step: {step_name}")
    logging.info(f"==================================================")
    try:
        func(*args, **kwargs)
        logging.info(f"Successfully completed step: {step_name}\n")
    except Exception as e:
        logging.error(f"Error during step '{step_name}': {e}")
        logging.error("Aborting ingestion pipeline.")
        sys.exit(1)

def main():
    logging.info("Starting Unofficial Guide Ingestion Pipeline Orchestrator...\n")
    
    # 1. Download Reddit Raw Data
    run_step("Download Reddit Raw Data", download_reddit_main)
    
    # 2. Download RateMyProfessor Raw Data
    run_step("Download RateMyProfessor Raw Data", download_rmp_main)
    
    # 3. Extract Syllabus PDF Text
    run_step("Extract Syllabus PDF Text", parse_pdf_main)
    
    # 4. Process/Chunk Reddit Data
    run_step("Process/Chunk Reddit Data", ingest_reddit_main)
    
    # 5. Process/Chunk RateMyProfessor Data
    run_step("Process/Chunk RateMyProfessor Data", ingest_rmp_main)
    
    # 6. Process/Chunk Syllabus Data
    run_step("Process/Chunk Syllabus Data", ingest_syllabus_main)
    
    # 7. Validate Chunks
    documents_dir = os.path.join(project_root, "documents")
    reddit_chunks_path = os.path.join(documents_dir, "chunks", "reddit_chunks.json")
    rmp_chunks_path = os.path.join(documents_dir, "chunks", "rmp_chunks.json")
    syllabus_chunks_path = os.path.join(documents_dir, "chunks", "syllabus_chunks.json")
    
    logging.info("==================================================")
    logging.info("Starting step: Validate Chunks")
    logging.info("==================================================")
    
    reddit_ok = validate_chunks(reddit_chunks_path)
    rmp_ok = validate_chunks(rmp_chunks_path)
    syllabus_ok = validate_chunks(syllabus_chunks_path)
    
    if reddit_ok and rmp_ok and syllabus_ok:
        logging.info("Validation PASSED successfully for all chunks.")
    else:
        logging.error("Validation FAILED! Please check the parser outputs.")
        sys.exit(1)
        
    logging.info("Pipeline Execution Complete!")


if __name__ == "__main__":
    main()
