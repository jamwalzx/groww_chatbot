# Implementation Plan: Mutual Fund FAQ Assistant

This implementation plan details the phase-wise execution strategy for building the RAG-based Mutual Fund FAQ Assistant, aligned with the constraints and architecture defined in `Architecture.md`.

## Phase 1: Project Setup & Infrastructure
- Initialize the project repository and a Python virtual environment.
- Define the `requirements.txt` file including dependencies: `langchain`, `langchain-community`, `langchain-groq`, `sentence-transformers` (for BGE embeddings), `beautifulsoup4`, `chromadb`, `streamlit`, and `python-dotenv`.
- Setup `.env` for managing API keys securely.

## Phase 2: Data Ingestion Pipeline
- **Web Scraper:** Implement a script to fetch HTML exclusively from the 5 predefined Groww scheme URLs using `BeautifulSoup` or `WebBaseLoader`. (No PDFs or other external sources).
- **Text Cleaning:** Strip out headers, footers, and non-content elements to isolate the scheme facts.
- **Text Splitting:** Use `RecursiveCharacterTextSplitter` with a smaller chunk size (e.g., `chunk_size=500` characters and `chunk_overlap=100`) because the scraped text is highly dense and lacks standard sentence spacing. Ensure metadata (`source_url`, `scheme_name`) is attached to each chunk.
- **Vector Database:** Generate embeddings using the `BAAI/bge-small-en-v1.5` model and store the chunks in a local instance of ChromaDB. The small model is optimal here because the dense, keyword-heavy chunks do not require the deep semantic nuance of a large model.

## Phase 3: Retrieval & Guardrail System
- **Query Guardrail:** Implement a lightweight classification step (either rule-based or a fast LLM prompt) that runs *before* retrieval. It will evaluate if the query is asking for investment advice or comparing performance.
  - If invalid, return the polite refusal template with an AMFI/SEBI educational link.
- **Semantic Retrieval & Search Strategy:** For valid queries, convert the query to an embedding and retrieve chunks from ChromaDB. Given the small chunk size (500 chars) and dense, keyword-heavy text, use a higher `top-K` (e.g., K=5 to 8) to ensure high recall. Additionally, use Maximum Marginal Relevance (MMR) search instead of standard similarity search to fetch a diverse set of chunks, preventing redundant information from dominating the context window.

## Phase 4: Generation Engine
- **Prompt Engineering:** Construct the strict system prompt that enforces:
  - Facts-only tone.
  - Maximum 3 sentences.
  - Exactly one citation link appended at the end.
  - Footer string: `"Last updated from sources: <date>"`.
- **LLM Integration:** Feed the retrieved chunks and the query into the LLM with `temperature=0.0` to minimize hallucination.
- **Output Validation:** Add a small programmatic check to truncate or format the LLM output to guarantee it does not exceed the 3-sentence constraint.

## Phase 5: User Interface (UI)
- **Streamlit App:** Develop a lightweight `app.py` frontend.
- **Layout:** Include a welcome message, a clear chat interface, and a persistent disclaimer at the top or bottom: `“Facts-only. No investment advice.”`
- **Example Queries:** Provide 3 clickable buttons for example questions to guide user interaction.

## Phase 6: Scheduler Component
- **Cron/Scheduler:** Implement a scheduling mechanism (e.g., using `schedule` Python library, a system cron job, or GitHub Actions) to run the `ingest.py` script automatically every day.
- **Data Refresh:** Ensure the script overwrites or cleanly updates the vector database (`chroma_db`) so the assistant always retrieves the most recent NAV, expense ratios, and fund metrics.

## Phase 7: Testing & Validation
- **Accuracy Testing:** Test factual queries specific to the 5 ingested schemes (e.g., expense ratios, lock-in periods).
- **Refusal Testing:** Test adversarial queries ("Should I buy HDFC Mid Cap?", "Is this fund good?") to ensure the guardrail blocks them reliably.
- **Constraint Testing:** Ensure responses are always ≤ 3 sentences and contain exactly one link.
