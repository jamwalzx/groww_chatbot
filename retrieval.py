import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

# Load environment variables
load_dotenv()

CHROMA_PATH = "chroma_db"
REFUSAL_MESSAGE = "I am a factual assistant and cannot provide investment advice or performance comparisons. For educational resources on mutual funds, please visit AMFI (https://www.amfiindia.com/) or SEBI (https://www.sebi.gov.in/)."

def get_guardrail_result(query: str) -> bool:
    """
    Evaluates if the query is asking for investment advice or comparing performance.
    Returns True if valid (factual query), False if invalid (advice/comparison).
    """
    # Use Llama-3.3-70B on Groq for classification
    # Rate Limits: 30 RPM, 1K RPD, 12K TPM, 100K TPD
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0, max_retries=3)
    
    prompt = PromptTemplate.from_template(
        "You are a strict query classifier for a mutual fund FAQ assistant. "
        "Your job is to determine if the user query is asking for investment advice, recommendations, predictions, or performance comparisons. "
        "If it is asking for advice, recommendations, or comparison, respond with 'INVALID'. "
        "If it is a factual question about mutual fund details (e.g., exit load, expense ratio, NAV, manager), respond with 'VALID'. "
        "Respond with EXACTLY one word: VALID or INVALID.\n\n"
        "User Query: {query}\n"
        "Classification:"
    )
    
    chain = prompt | llm
    
    try:
        result = chain.invoke({"query": query}).content.strip().upper()
        # If it doesn't strictly say INVALID, we default to VALID to be permissive, 
        # but the prompt forces EXACTLY one word.
        if "INVALID" in result:
            return False
        return True
    except Exception as e:
        # Fallback to valid if LLM fails, or we could fallback to False. Let's fallback to False for safety.
        print(f"Guardrail error: {e}")
        return False

def get_retriever(k: int = 4):
    """
    Initializes and returns the ChromaDB retriever using FastEmbed BGE model.
    """
    embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    # Using MMR to fetch diverse chunks because our small chunks are densely packed with facts
    return db.as_retriever(search_type="mmr", search_kwargs={"k": 6})

def process_query_phase3(query: str):
    """
    Processes the query through the guardrail and retrieval system.
    Returns a dictionary with status and data.
    """
    is_valid = get_guardrail_result(query)
    
    if not is_valid:
        return {
            "status": "rejected",
            "message": REFUSAL_MESSAGE,
            "context": []
        }
        
    retriever = get_retriever()
    docs = retriever.invoke(query)
    
    return {
        "status": "approved",
        "message": "Query passed guardrail.",
        "context": docs
    }

if __name__ == "__main__":
    # Test cases to validate Phase 3 functionality
    test_queries = [
        "What is the exit load for HDFC Large Cap Fund?",
        "Should I invest my money in HDFC Small Cap Fund?",
        "Which is better, HDFC Large Cap or Small Cap?",
        "Who is the fund manager of HDFC Gold ETF?"
    ]
    
    for q in test_queries:
        print(f"Query: {q}")
        res = process_query_phase3(q)
        if res["status"] == "rejected":
            print(f"Result: REJECTED\nMessage: {res['message']}\n")
        else:
            print(f"Result: APPROVED\nRetrieved {len(res['context'])} chunks.\n")
