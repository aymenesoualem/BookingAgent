import streamlit as st
import chromadb
from chromadb.utils import embedding_functions
import json

# Initialize ChromaDB Client
def init_chromadb_client():
    return chromadb.HttpClient(host='localhost', port=8000)

# Load documents into ChromaDB
def load_docs_into_chromadb(client, collection_name, documents):
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_functions.DefaultEmbeddingFunction()
    )
    for doc in documents:
        collection.add(embedding_id=doc["id"], embedding=doc["embedding"], metadata=doc["metadata"])
    return f"Loaded {len(documents)} documents into collection '{collection_name}'."

# Retrieve relevant information from ChromaDB
def retrieve_info(client, collection_name, query_embedding, top_k=5):
    collection = client.get_collection(name=collection_name)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    return results


# Streamlit UI
st.title("ChromaDB Document Uploader and Retriever")

# Step 1: Upload documents
documents_file = st.file_uploader("Upload your documents (JSON format)", type=["json"])

if documents_file:
    documents = json.load(documents_file)
    st.write("Uploaded Documents:", documents)

    # Step 2: Load documents into ChromaDB
    if st.button("Load Documents into ChromaDB"):
        client = init_chromadb_client()
        collection_name = st.text_input("Collection Name", value="default_collection")
        if collection_name:
            try:
                message = load_docs_into_chromadb(client, collection_name, documents)
                st.success(message)
            except Exception as e:
                st.error(f"Error: {e}")

# Step 3: Query ChromaDB
st.header("Query ChromaDB")
query_embedding = st.text_input("Enter Query Embedding (comma-separated values)")

if query_embedding:
    query_embedding = [float(x) for x in query_embedding.split(",")]
    top_k = st.number_input("Number of Results", min_value=1, max_value=100, value=5)

    if st.button("Retrieve Relevant Documents"):
        try:
            client = init_chromadb_client()
            collection_name = st.text_input("Collection Name for Query", value="default_collection")
            if collection_name:
                results = retrieve_info(client, collection_name, query_embedding, top_k)
                st.write("Retrieved Results:", results)
        except Exception as e:
            st.error(f"Error: {e}")
