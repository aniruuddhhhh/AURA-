import os
import time
import shutil
import pandas as pd

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

CURRENT_USER_ID = "1503960366"
PERSIST_DIR     = "./gemini_aura_vector_db_hf"
JOURNAL_FILE    = "AURA_Realistic_Journals (1).csv"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def build_vector_memory():
    print(" Gemini AURA: Vector Database Construction")
    if os.path.exists(PERSIST_DIR):
        shutil.rmtree(PERSIST_DIR)
        print(f" Cleaned existing directory: {PERSIST_DIR}")
    df = pd.read_csv(JOURNAL_FILE)
    documents = [
        Document(
            page_content=str(row["Entry"]),
            metadata={"user_id": str(row["Id"]).strip(), "timestamp": str(row["Timestamp"])}
        )
        for _, row in df.iterrows()
        if str(row["Id"]).strip() == CURRENT_USER_ID
    ]

    print(f" Loaded {len(documents)} entries for User {CURRENT_USER_ID}")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    split_docs = splitter.split_documents(documents)
    print(f" Created {len(split_docs)} chunks.")

    print(f" Loading {EMBEDDING_MODEL}...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    print(f" Vectorizing {len(split_docs)} chunks...")
    start = time.time()
    
    vector_db = Chroma.from_documents(
        documents=split_docs,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )

    print(f" Success! Time: {(time.time() - start)/60:.2f} min.")
    count = vector_db._collection.count()
    print(f"1. Total Chunks in DB: {count}")
    if count > 0:
        test_res = vector_db.similarity_search("sleep", k=1)
        if test_res:
            print(f"2. Search Test Success! Sample: {test_res[0].page_content[:60]}...")
        else:
            print("2. Search Test Failed: No matches found.")
    else:
        print(" Error: Database is empty. Check User ID filtering.")

if __name__ == "__main__":
    build_vector_memory()
