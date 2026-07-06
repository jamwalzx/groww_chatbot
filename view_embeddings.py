import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

CHROMA_PATH = "chroma_db"

def view_all_embeddings():
    if not os.path.exists(CHROMA_PATH):
        print(f"Error: Database directory '{CHROMA_PATH}' does not exist.")
        return
        
    print("Loading ChromaDB...")
    # Initialize the same embedding model used during ingestion
    embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    
    print("Fetching data from ChromaDB...")
    # Explicitly include embeddings in the fetch request
    data = db.get(include=["embeddings", "documents", "metadatas"])
    
    ids = data.get("ids", [])
    docs = data.get("documents", [])
    metas = data.get("metadatas", [])
    embs = data.get("embeddings", [])
    
    total_chunks = len(ids)
    print(f"\nTotal chunks stored in DB: {total_chunks}")
    
    if total_chunks == 0:
        print("No embeddings found in the database. (If ingest.py crashed during embedding, you may need to re-run it first).")
        return
        
    for i in range(total_chunks):
        print("-" * 50)
        print(f"Chunk {i+1} / {total_chunks} | ID: {ids[i]}")
        
        meta = metas[i] if metas else {}
        print(f"Source URL: {meta.get('source_url', 'N/A')}")
        print(f"Scheme Name: {meta.get('scheme_name', 'N/A')}")
        
        # Clean up newlines for a tidy preview
        doc_preview = docs[i].replace('\n', ' ')[:100] + "..." if docs[i] else "N/A"
        print(f"Document Preview: {doc_preview}")
        
        if embs and len(embs) > i:
            emb = embs[i]
            # Show just the first 5 dimensions rounded for readability
            emb_preview = [round(x, 4) for x in emb[:5]]
            print(f"Embedding Dimensions: {len(emb)}")
            print(f"Embedding Vector Preview: {emb_preview} ...")
        else:
            print("Embedding Vector: MISSING")

if __name__ == "__main__":
    view_all_embeddings()
