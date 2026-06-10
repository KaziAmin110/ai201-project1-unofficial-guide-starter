import os
import re
import json
import pdfplumber
import sys

def parse_metadata_from_filename(filename):
    """
    Attempts to infer course_code, instructor, and term from the PDF filename.
    Expected patterns like: COP3502C_Szumlanski_Fall2025.pdf
    """
    # Strip extension
    base_name = os.path.splitext(filename)[0]
    
    # Replace separators with spaces to avoid word boundary issues
    base_name_clean = base_name.replace("_", " ").replace("-", " ")
    
    # Initialize defaults
    course_code = "UNKNOWN"
    instructor = "UNKNOWN"
    term = "UNKNOWN"
    
    # 1. Match Course Code (e.g., COP3502C, COT 3100, etc.)
    course_match = re.search(r'\b([a-zA-Z]{3}\s*\d{4}[a-zA-Z]?)\b', base_name_clean)
    if course_match:
        course_code = course_match.group(1).replace(" ", "").upper()
        
    # 2. Match Term (e.g., Fall2025, Fall-2025, Fall_2025, Spring 2024, etc.)
    term_match = re.search(r'\b(Fall|Spring|Summer)\s*(\d{4})\b', base_name_clean, re.IGNORECASE)
    if term_match:
        term = f"{term_match.group(1).capitalize()} {term_match.group(2)}"
    else:
        # Fallback to look for just a year
        year_match = re.search(r'\b(20\d{2})\b', base_name_clean)
        if year_match:
            term = year_match.group(1)
            
    # 3. Match Instructor
    # Remove course code and term from base_name_clean, then clean up to extract instructor
    temp_name = base_name_clean
    if course_match:
        temp_name = temp_name.replace(course_match.group(0), "")
    if term_match:
        temp_name = temp_name.replace(term_match.group(0), "")
        
    # Clean up any remaining course numbers or years
    temp_name = re.sub(r'\d+', '', temp_name)
    
    # Clean up excess delimiters and find remaining words
    words = re.findall(r'[a-zA-Z]+', temp_name)
    # Filter out common terms/months/words
    filtered_words = [w for w in words if w.lower() not in ("fall", "spring", "summer", "syllabus", "pdf", "course", "class")]
    if filtered_words:
        candidate = " ".join(filtered_words).title()
        # Filter out obvious course title words
        invalid_keywords = {"ai", "game", "programming", "syllabus", "introduction", "structures", "science", "engineering", "math", "computer", "design", "concepts", "principles"}
        candidate_words = [w.lower() for w in filtered_words]
        if not any(kw in invalid_keywords for kw in candidate_words):
            instructor = candidate
        
    return course_code, instructor, term


def parse_metadata_from_text(text):
    """
    Fallback method to infer course_code, instructor, and term from the raw PDF text content.
    """
    course_code = None
    instructor = None
    term = None
    
    # 1. Extract Course Code
    course_match = re.search(r'\b([a-zA-Z]{3}\s*\d{4}[a-zA-Z]?)\b', text)
    if course_match:
        course_code = course_match.group(1).replace(" ", "").upper()
        
    # 2. Extract Term
    term_match = re.search(r'\b(Fall|Spring|Summer)[-_\s]+(\d{4})\b', text, re.IGNORECASE)
    if term_match:
        term = f"{term_match.group(1).capitalize()} {term_match.group(2)}"
        
    # 3. Extract Instructor (heuristic: look for "Instructor: [Name]" or "Professor: [Name]" or "Instructor Information\n[Name]")
    instructor_match = re.search(r'(?:Instructor|Professor|Teacher)(?:\s+Information|\s+Name)?\s*[:\n]\s*([a-zA-Z\s\.\-]+)(?:\n|$)', text, re.IGNORECASE)
    if instructor_match:
        instructor = instructor_match.group(1).strip().split('\n')[0]
        # Clean extra whitespace
        instructor = re.sub(r'\s+', ' ', instructor).strip().title()
        
    return course_code, instructor, term

def extract_pdf_text(filepath):
    """
    Extracts text page-by-page using pdfplumber.
    """
    text_content = []
    with pdfplumber.open(filepath) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                text_content.append(text)
            else:
                print(f"Warning: Could not extract text from page {page_num + 1} of {os.path.basename(filepath)}", file=sys.stderr)
    return "\n--- PAGE BREAK ---\n".join(text_content)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    syllabi_dir = os.path.join(project_root, "documents", "raw", "syllabi")
    output_filepath = os.path.join(project_root, "documents", "raw", "syllabus_raw.json")
    
    print(f"Scanning directory for PDFs: {syllabi_dir}")
    if not os.path.exists(syllabi_dir):
        print(f"Directory {syllabi_dir} does not exist. Creating it.")
        os.makedirs(syllabi_dir, exist_ok=True)
        print("Please place syllabus PDF files in the directory and run this script again.")
        sys.exit(0)
        
    pdf_files = [f for f in os.listdir(syllabi_dir) if f.lower().endswith(".pdf")]
    print(f"Found {len(pdf_files)} PDF files.")
    
    if not pdf_files:
        print("No PDF files found to parse. Skipping raw extraction. Writing empty manifest to keep orchestrator happy.")
        with open(output_filepath, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return
        
    raw_syllabi_data = []
    
    for filename in pdf_files:
        filepath = os.path.join(syllabi_dir, filename)
        print(f"\nProcessing {filename}...")
        try:
            raw_text = extract_pdf_text(filepath)
            
            # Infer metadata from filename
            fn_course, fn_instructor, fn_term = parse_metadata_from_filename(filename)
            # Infer metadata from text fallback
            text_course, text_instructor, text_term = parse_metadata_from_text(raw_text[:2000])
            
            # Reconcile metadata (prefer text extraction if found, fallback to filename guessing)
            course_code = text_course if (text_course and text_course != "UNKNOWN") else fn_course
            instructor = text_instructor if (text_instructor and text_instructor != "UNKNOWN") else fn_instructor
            term = text_term if (text_term and text_term != "UNKNOWN") else fn_term
            
            print(f"-> Inferred Metadata:")
            print(f"   Course Code: {course_code}")
            print(f"   Instructor:  {instructor}")
            print(f"   Term:        {term}")

            
            syllabus_record = {
                "source_file": filename,
                "course_code": course_code,
                "instructor": instructor,
                "term": term,
                "raw_text": raw_text
            }
            raw_syllabi_data.append(syllabus_record)
            
        except Exception as e:
            print(f"Error parsing {filename}: {e}", file=sys.stderr)
            
    # Write output JSON file
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(raw_syllabi_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nExtracted text from {len(raw_syllabi_data)} PDFs. Saved to {output_filepath}")

if __name__ == "__main__":
    main()
