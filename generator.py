import os
import logging
from dotenv import load_dotenv
from groq import Groq
from typing import List, Dict, Any, Generator

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

class RAGGenerator:
    def __init__(self, api_key: str = None):
        # Resolve API key
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            logger.error("GROQ_API_KEY environment variable is not set.")
            raise ValueError("GROQ_API_KEY not found. Please set it in your .env file.")
            
        logger.info("Initializing Groq client.")
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"

    def rewrite_query(self, query: str, chat_history: List[Dict[str, str]]) -> str:
        """
        Use Groq LLM to rewrite user query based on conversation history.
        If history is empty, returns original query to optimize latency.
        """
        if not chat_history:
            logger.info("Chat history is empty. Skipping query rewriting.")
            return query

        logger.info("Rewriting query based on chat history.")
        history_text = ""
        for msg in chat_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Only include user and assistant messages in the rewrite prompt
            if role in ["user", "assistant"]:
                history_text += f"{role.capitalize()}: {content}\n"

        prompt = f"""Given the following conversation history and a follow-up query, rewrite the follow-up query to be a standalone, self-contained search query that can be used to search a vector database for relevant information.
Do NOT answer the query, just rewrite it. Output ONLY the rewritten standalone query, with no introduction, outro, explanations, or quotes.

Conversation History:
{history_text}

Follow-up Query: {query}

Standalone Query:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100
            )
            rewritten = response.choices[0].message.content.strip()
            # Clean enclosing quotes if added by the LLM
            if (rewritten.startswith('"') and rewritten.endswith('"')) or (rewritten.startswith("'") and rewritten.endswith("'")):
                rewritten = rewritten[1:-1].strip()
            
            logger.info(f"Original query: '{query}' -> Rewritten: '{rewritten}'")
            return rewritten
        except Exception as e:
            logger.error(f"Error during query rewriting: {e}. Using original query.")
            return query

    def generate_response_stream(
        self, 
        query: str, 
        context_chunks: List[Dict[str, Any]], 
        chat_history: List[Dict[str, str]]
    ) -> Generator[str, None, None]:
        """
        Generate a streamed response grounded strictly in the retrieved context chunks.
        Appends inline citations mapping back to source indexes.
        """
        # Format the retrieved context blocks as numbered entries
        if not context_chunks:
            formatted_context = "No retrieved context blocks available."
        else:
            context_items = []
            for idx, chunk in enumerate(context_chunks):
                metadata = chunk.get("metadata", {})
                source = metadata.get("source", metadata.get("source_file", "unknown"))
                text = chunk.get("text", "")
                context_items.append(f"[{idx+1}] Source: {source}\nContent: {text}")
            formatted_context = "\n\n".join(context_items)

        system_prompt = """You are a strictly grounded AI Academic Advisor for the University of Central Florida (UCF).
Your task is to answer the user's questions using ONLY the provided context blocks.

CONSTRAINTS:
1. Use ONLY the information in the provided context blocks to answer the question. Do NOT use any pre-existing or outside knowledge.
2. Every claim or fact you state MUST be followed by an inline citation referencing the source number, for example [1], [2], or [1][3] if multiple sources apply.
3. If the retrieved context blocks do not contain the answer, or if they are empty, you MUST state exactly: "I'm sorry, but I don't have enough information to answer that question." Do not attempt to formulate an answer using general knowledge.
4. Keep your answer professional, clear, and concise. Do not mention that you have context or are forced to use it; simply state the answers and cite the sources directly."""

        # Construct messages payload for Groq
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history dialogue (filters out any sources metadata to avoid cluttering chat model context)
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        # Append the current query and retrieved context
        user_content = f"Retrieved Context:\n---\n{formatted_context}\n---\n\nUser Query: {query}"
        messages.append({"role": "user", "content": user_content})

        logger.info(f"Requesting streamed completion from Groq using model: {self.model}")
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                stream=True
            )
            for chunk in completion:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            logger.error(f"Error in Groq completion stream: {e}")
            yield f"\nAn error occurred during response generation: {e}"

if __name__ == "__main__":
    # Quick manual check of class initialization
    logging.basicConfig(level=logging.INFO)
    try:
        gen = RAGGenerator()
        print("RAGGenerator initialized successfully!")
    except Exception as e:
        print(f"Failed to initialize RAGGenerator: {e}")
