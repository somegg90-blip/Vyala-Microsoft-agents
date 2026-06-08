# kb/build_local_kb.py
import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding # <-- NEW IMPORT
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# 🔥 Create an explicit HuggingFace embedding instance (configurable via env)
# Set `HF_EMBED_MODEL` to override the default model name.
embed_model_name = os.environ.get("HF_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
embed_model = HuggingFaceEmbedding(model_name=embed_model_name)
Settings.embed_model = embed_model

# Connect to local Qdrant
client = QdrantClient(url="http://localhost:6333")
vector_store = QdrantVectorStore(client=client, collection_name="pqc_knowledge")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def build_index():
    print("📂 Loading documents from data folders...")
    documents = []
    
    sources = {
        "1_nist_fips": "NIST_FIPS",
        "2_cves": "CVE_Database",
        "3_ietf_rfc": "IETF_RFC",
        "4_compliance": "Compliance_Mandates"
    }
    
    for folder, source_name in sources.items():
        path = os.path.join(DATA_DIR, folder)
        if os.path.exists(path) and os.listdir(path):
            print(f"  Reading {folder}...")
            docs = SimpleDirectoryReader(path).load_data()
            for doc in docs:
                doc.metadata["source_type"] = source_name
            documents.extend(docs)
        else:
            print(f"  ⚠️ Skipping {folder} (empty or missing)")

    if not documents:
        print("❌ No documents found!")
        return

    print(f"📄 Loaded {len(documents)} document chunks. Indexing into Qdrant using LOCAL embeddings...")
    
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    # This will download the model on the first run, then use it for free
    # Passing the explicit embed_model instance avoids ambiguous model resolution
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=embed_model,
    )
    
    print("✅ Local PQC Knowledge Base built successfully!")

if __name__ == "__main__":
    build_index()