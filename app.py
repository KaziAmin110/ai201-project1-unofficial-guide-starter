import os
import streamlit as st
import logging
from dotenv import load_dotenv
from retriever import Retriever
from generator import RAGGenerator

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Cache resource initialization to prevent re-initializing database and sentence transformers on every rerun
@st.cache_resource
def get_retriever():
    try:
        logger.info("Initializing Retriever in Streamlit resource cache.")
        return Retriever()
    except Exception as e:
        logger.error(f"Error initializing Retriever: {e}")
        st.error(f"⚠️ Failed to connect to Vector Database: {e}. Make sure you built the vector database first.")
        return None

@st.cache_resource
def get_generator():
    try:
        logger.info("Initializing RAGGenerator in Streamlit resource cache.")
        return RAGGenerator()
    except Exception as e:
        logger.error(f"Error initializing RAGGenerator: {e}")
        st.error(f"⚠️ Failed to initialize LLM generator: {e}. Check that GROQ_API_KEY is correctly set in your .env file.")
        return None

# Page Configuration
st.set_page_config(
    page_title="UCF Unofficial Advisor 🎓",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling Injection
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    /* Apply Font and Core Background styles */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', sans-serif !important;
        background: linear-gradient(135deg, #0b0b0e 0%, #13131a 100%) !important;
        color: #e2e2e9 !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0b0b0d !important;
        border-right: 1px solid rgba(255, 215, 0, 0.1) !important;
    }
    
    /* Custom header with UCF gold gradient and text-shadow */
    .glowing-header {
        font-size: 3rem !important;
        font-weight: 700 !important;
        background: linear-gradient(90deg, #ffd700 0%, #ffaa00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
        text-shadow: 0 0 30px rgba(255, 215, 0, 0.15);
    }
    
    /* Subheading styling */
    .subheading {
        color: #8c8d9e !important;
        font-size: 1.1rem;
        margin-bottom: 25px;
    }
    
    /* Glassmorphism wrapper for stChatMessage */
    div[data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px !important;
        padding: 16px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 4px 25px rgba(0, 0, 0, 0.3) !important;
    }
    
    /* User chat bubble styling - adding gold tint */
    div[data-testid="stChatMessage"][data-testid="stChatMessageUser"] {
        background: rgba(255, 215, 0, 0.05) !important;
        border: 1px solid rgba(255, 215, 0, 0.15) !important;
    }
    
    /* Accordion / Expander styling for sources */
    div[data-testid="stExpander"] {
        background: rgba(0, 0, 0, 0.2) !important;
        border: 1px solid rgba(255, 215, 0, 0.1) !important;
        border-radius: 8px !important;
        margin-top: 10px !important;
    }
    div[data-testid="stExpander"] summary {
        font-weight: 600 !important;
        color: #ffd700 !important;
    }
    
    /* Custom Info text styling inside accordion */
    div.stInfo {
        background-color: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.04) !important;
        color: #d1d1d8 !important;
        border-radius: 8px !important;
        padding: 12px !important;
        font-size: 0.92rem !important;
    }
    
    /* Input field gold accent styling */
    textarea[data-testid="stChatInputTextArea"] {
        border: 1px solid rgba(255, 215, 0, 0.2) !important;
        background-color: rgba(255, 255, 255, 0.02) !important;
        color: #ffffff !important;
    }
    textarea[data-testid="stChatInputTextArea"]:focus {
        border-color: #ffd700 !important;
        box-shadow: 0 0 10px rgba(255, 215, 0, 0.2) !important;
    }
    
    /* Status indicators */
    .status-text {
        font-size: 0.85rem;
        color: #8c8d9e;
        font-style: italic;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def clear_chat():
    st.session_state.messages = []
    st.session_state.chat_history = []
    logger.info("Chat history cleared by user.")

# Sidebar Configuration
st.sidebar.markdown("<h2 style='color: #ffd700; font-weight:700;'>Control Panel 🎛️</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# Top-K settings configuration
top_k = st.sidebar.slider(
    "ChromaDB Top-K Chunks",
    min_value=1,
    max_value=10,
    value=5,
    help="Number of document chunks retrieved from vector store for each query."
)

st.sidebar.markdown("---")

# Display Active Model
st.sidebar.markdown("**LLM Engine:**")
st.sidebar.info("Groq Cloud API\nModel: `llama-3.3-70b-versatile`\nTemp: `0.0` (Grounded)")

st.sidebar.markdown("---")

# Clear chat button
if st.sidebar.button("🗑️ Clear Chat History", use_container_width=True):
    clear_chat()
    st.rerun()

# Main Application Layout
st.markdown("<h1 class='glowing-header'>UCF Unofficial Advisor 🎓</h1>", unsafe_allow_html=True)
st.markdown("<p class='subheading'>Your strictly grounded academic companion. Answers questions about classes, professors, syllabi, and advising policies using official catalog and student review data.</p>", unsafe_allow_html=True)

# Get retriever & generator from resource cache
retriever = get_retriever()
generator = get_generator()

# Render existing conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # If assistant response has sources, display them in an expander
        if msg["role"] == "assistant" and "sources" in msg and msg["sources"]:
            with st.expander("🔍 View Retrieved Sources", expanded=False):
                for idx, src in enumerate(msg["sources"]):
                    metadata = src.get("metadata", {})
                    source_name = metadata.get("source", metadata.get("source_file", "Unknown Source"))
                    distance = src.get("distance", 0.0)
                    text = src.get("text", "")
                    
                    st.markdown(f"**[{idx+1}] {source_name}** *(Cosine Distance: {distance:.4f})*")
                    # Surface extra metadata properties if available
                    meta_tags = []
                    for k in ["course_code", "professor_name", "breadcrumbs"]:
                        if k in metadata and metadata[k]:
                            meta_tags.append(f"`{k}: {metadata[k]}`")
                    if meta_tags:
                        st.markdown(" ".join(meta_tags))
                    st.info(text)

# Chat Input Area
user_input = st.chat_input("Ask a question about UCF classes, professors, or policies...")

if user_input:
    # 1. Display User Message
    with st.chat_message("user"):
        st.markdown(user_input)
    
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # 2. Check if systems are initialized properly
    if not retriever or not generator:
        with st.chat_message("assistant"):
            st.error("RAG Advisor is currently offline. Please resolve the initialization errors displayed above.")
        st.stop()

    # 3. Generate Assistant Response
    with st.chat_message("assistant"):
        # We will use Streamlit status indicators to show execution steps
        status_placeholder = st.empty()
        
        # Step A: Query rewriting
        status_placeholder.markdown("<div class='status-text'>Analyzing conversation history...</div>", unsafe_allow_html=True)
        rewritten_query = generator.rewrite_query(user_input, st.session_state.chat_history)
        
        # Step B: Document Retrieval
        status_placeholder.markdown(f"<div class='status-text'>Retrieving top {top_k} source chunks...</div>", unsafe_allow_html=True)
        context_chunks = retriever.retrieve(rewritten_query, top_k=top_k)
        
        # Step C: Stream generation
        status_placeholder.empty()
        
        # Stream response token-by-token
        response_stream = generator.generate_response_stream(rewritten_query, context_chunks, st.session_state.chat_history)
        full_response = st.write_stream(response_stream)
        
        # Step D: Render Sources Accordion
        if context_chunks:
            with st.expander("🔍 View Retrieved Sources", expanded=False):
                for idx, src in enumerate(context_chunks):
                    metadata = src.get("metadata", {})
                    source_name = metadata.get("source", metadata.get("source_file", "Unknown Source"))
                    distance = src.get("distance", 0.0)
                    text = src.get("text", "")
                    
                    st.markdown(f"**[{idx+1}] {source_name}** *(Cosine Distance: {distance:.4f})*")
                    meta_tags = []
                    for k in ["course_code", "professor_name", "breadcrumbs"]:
                        if k in metadata and metadata[k]:
                            meta_tags.append(f"`{k}: {metadata[k]}`")
                    if meta_tags:
                        st.markdown(" ".join(meta_tags))
                    st.info(text)
        
        # Save assistant message, text response, and retrieved sources to memory
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "sources": context_chunks
        })
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": full_response
        })
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })
