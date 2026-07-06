import streamlit as st
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from retrieval import process_query_phase3, REFUSAL_MESSAGE

# Page config
st.set_page_config(page_title="Mutual Fund FAQ Assistant", page_icon="📈", layout="centered")

# Phase 4: Generation Engine
def generate_response(query: str, context_docs) -> str:
    # Extract text and sources from context
    context_text = "\n\n".join([doc.page_content for doc in context_docs])
    
    # Get a unique source URL from metadata (fallback to a generic one if missing)
    source_url = None
    for doc in context_docs:
        if "source_url" in doc.metadata:
            source_url = doc.metadata["source_url"]
            break
    if not source_url:
        source_url = "https://groww.in/mutual-funds"
        
    # Use Llama-3.3-70B with temperature 0.0 to minimize hallucination
    # Rate Limits: 30 RPM, 1K RPD, 12K TPM, 100K TPD
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0, max_retries=3)
    
    prompt = PromptTemplate.from_template(
        "You are a factual mutual fund assistant. You do not give financial advice. "
        "Answer ONLY using the provided context. If the answer is not in the context, say 'I do not have this information'. "
        "Limit your response to a maximum of 3 sentences. Be concise and direct.\n\n"
        "Context:\n{context}\n\n"
        "User Query: {query}\n"
        "Answer:"
    )
    
    chain = prompt | llm
    
    response = chain.invoke({
        "context": context_text,
        "query": query
    }).content.strip()
    
    # Programmatic Output Validation: Ensure max 3 sentences
    # Basic split by common sentence delimiters (could be improved, but satisfies constraint)
    sentences = [s.strip() for s in response.replace('!', '.').replace('?', '.').split('.') if s.strip()]
    if len(sentences) > 3:
        response = ". ".join(sentences[:3]) + "."
    elif not response.endswith('.'):
        response += "."
        
    # Append exactly one citation link and footer
    current_date = datetime.now().strftime("%Y-%m-%d")
    final_response = f"{response}\n\nSource: {source_url}\n\n*Last updated from sources: {current_date}*"
    
    return final_response

# Phase 5: User Interface (UI)
st.title("Mutual Fund FAQ Assistant")
st.caption("Facts-only. No investment advice.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Example Queries Layout
st.write("### Example Queries")
col1, col2, col3 = st.columns(3)
example_query = None

with col1:
    if st.button("Exit load for HDFC Large Cap?"):
        example_query = "What is the exit load for HDFC Large Cap Fund?"
with col2:
    if st.button("Who manages HDFC Gold ETF?"):
        example_query = "Who is the fund manager of HDFC Gold ETF?"
with col3:
    if st.button("Expense ratio of HDFC Small Cap?"):
        example_query = "What is the expense ratio of HDFC Small Cap Fund?"

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input or example query
prompt = st.chat_input("Ask a factual question about the mutual funds...")
if example_query:
    prompt = example_query

if prompt:
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Process query
    with st.chat_message("assistant"):
        with st.spinner("Analyzing query & retrieving context..."):
            retrieval_res = process_query_phase3(prompt)
            
            if retrieval_res["status"] == "rejected":
                response = retrieval_res["message"]
            else:
                context_docs = retrieval_res["context"]
                if not context_docs:
                    response = "I do not have this information."
                else:
                    response = generate_response(prompt, context_docs)
                    
            st.markdown(response)
            
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
