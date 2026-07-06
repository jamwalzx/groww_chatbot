import os
import bs4
import json
from dotenv import load_dotenv
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.vectorstores import Chroma

# Load environment variables
load_dotenv()

# The 5 specific Groww mutual fund URLs defined in the Corpus
FUNDS = [
    {
        "name": "HDFC Gold ETF Fund of Fund Direct Plan Growth",
        "url": "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth"
    },
    {
        "name": "HDFC Large Cap Fund Direct Growth",
        "url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
    },
    {
        "name": "HDFC Small Cap Fund Direct Growth",
        "url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"
    },
    {
        "name": "HDFC Silver ETF FOF Direct Growth",
        "url": "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth"
    },
    {
        "name": "HDFC Mid Cap Fund Direct Growth",
        "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
    }
]

# Database directory
CHROMA_PATH = "chroma_db"

def ingest_data():
    all_docs = []
    
    print("Fetching and parsing URLs...")
    for fund in FUNDS:
        print(f"Loading: {fund['name']}")
        
        # We can use bs4.SoupStrainer to target only main content if the page has clear classes,
        # but as a generic approach, we'll load the full page and let the loader parse the text.
        # Groww generally uses specific div structures, but for simplicity we load the whole page.
        loader = WebBaseLoader(
            web_paths=(fund['url'],),
            # Optional: Add SoupStrainer here if we want to ignore headers/footers
            # bs_kwargs=dict(parse_only=bs4.SoupStrainer("div", class_="main-content"))
        )
        docs = loader.load()
        
        # Attach our explicit metadata
        for doc in docs:
            doc.metadata["scheme_name"] = fund["name"]
            doc.metadata["source_url"] = fund["url"]
            all_docs.append(doc)
            
    print(f"Loaded {len(all_docs)} raw documents.")

    print("Saving scraped data to scraped_data.json...")
    scraped_data_list = [{"page_content": d.page_content, "metadata": d.metadata} for d in all_docs]
    with open("scraped_data.json", "w", encoding="utf-8") as f:
        json.dump(scraped_data_list, f, ensure_ascii=False, indent=2)

    print("Splitting text into chunks...")
    # 500 chunk size with 100 overlap because scraped data is highly dense and concatenated
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        add_start_index=True
    )
    chunks = text_splitter.split_documents(all_docs)
    print(f"Generated {len(chunks)} text chunks.")

    print("Initializing FastEmbed BGE Embedding Model...")
    # FastEmbed runs BGE natively without PyTorch, preventing Windows DLL errors
    embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

    print("Creating and persisting Chroma vector database...")
    # Create the Chroma DB and persist it to the disk
    db = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings, 
        persist_directory=CHROMA_PATH
    )
    
    # In newer Chroma versions, persistence is automatic when directory is provided,
    # but we can call persist just in case (deprecated in newer versions).
    try:
        db.persist()
    except Exception:
        pass
        
    print(f"Data ingestion complete! Vector DB saved to {CHROMA_PATH}.")

if __name__ == "__main__":
    ingest_data()
