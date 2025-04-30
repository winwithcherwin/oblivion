"""
https://www.reddit.com/r/NixOS/comments/1934tok/python3_cant_find_libz_oserror_libzso1_cannot/

TODO: figure out why this is needed.
"""
from ctypes import *
import ctypes.util
cdll.LoadLibrary(ctypes.util.find_library('z'))


import os
import chromadb
import openai

print("querying")

# --- CONFIG ---
COLLECTION_NAME = "oblivion"
OPENAI_MODEL = "text-embedding-ada-002"

# --- SETUP ---
openai.api_key = os.getenv("OPENAI_API_KEY")

client = chromadb.PersistentClient(path=".secrets/chroma")
collection = client.get_or_create_collection(name=COLLECTION_NAME)

# --- GET QUERY ---
query = input("❓ Ask a question about your project: ")
# --- EMBED QUERY ---
response = openai.embeddings.create(
    input=query,
    model=OPENAI_MODEL
)
query_embedding = response.data[0].embedding  # <-- dot notation

# --- SEARCH ---
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=3,
    include=["documents", "metadatas"],
)
print("yes")

# --- DISPLAY ---
print("\n🔎 Top Matches:\n")
for doc, meta in zip(results['documents'][0], results["metadatas"][0]):  # chromadb still uses dict-style results
    print("-" * 40)
    print(f"Path: {meta['path']}")
    print(doc.strip())
    print("-" * 40)

