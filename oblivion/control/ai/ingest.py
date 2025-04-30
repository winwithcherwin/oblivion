"""
https://www.reddit.com/r/NixOS/comments/1934tok/python3_cant_find_libz_oserror_libzso1_cannot/

TODO: figure out why this is needed.
"""
from ctypes import *
import ctypes.util
cdll.LoadLibrary(ctypes.util.find_library('z'))

import os
import chromadb
from chromadb.config import Settings
import openai
import tiktoken



# --- CONFIG ---
PERSIST_DIR = "./.secrets/chroma"
COLLECTION_NAME = "oblivion"
OPENAI_MODEL = "text-embedding-ada-002"
README_FILE = "TODO.md"
MAX_TOKENS_PER_CHUNK = 300

# --- SETUP ---
openai.api_key = os.getenv("OPENAI_API_KEY")

client = chromadb.PersistentClient(path=PERSIST_DIR)
collection = client.get_or_create_collection(name=COLLECTION_NAME)

# --- LOAD README ---
with open(README_FILE, "r", encoding="utf-8") as f:
    text = f.read()

# --- CHUNKING ---
def chunk_text(text, max_tokens=MAX_TOKENS_PER_CHUNK):
    encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
    paragraphs = text.split("\n\n")
    chunks, current_chunk = [], ""
    for para in paragraphs:
        if len(encoder.encode(current_chunk + para)) < max_tokens:
            current_chunk += para + "\n\n"
        else:
            chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

chunks = chunk_text(text)

# --- EMBED + STORE ---
print(f"Embedding {len(chunks)} chunks...")

for idx, chunk in enumerate(chunks):
    response = openai.embeddings.create( input=chunk,
        model=OPENAI_MODEL
    )
    embedding = response.data[0].embedding

    collection.add(
        documents=[chunk],
        embeddings=[embedding],
        metadatas=[{"chunk_id": idx, "source": README_FILE}],
        ids=[f"readme-{idx}"]
    )

print(f"✅ Ingested {len(chunks)} chunks and saved to {PERSIST_DIR}!")

