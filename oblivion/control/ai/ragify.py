"""
https://www.reddit.com/r/NixOS/comments/1934tok/python3_cant_find_libz_oserror_libzso1_cannot/

TODO: figure out why this is needed.
"""
from ctypes import *
import ctypes.util
cdll.LoadLibrary(ctypes.util.find_library('z'))

import backoff
import os

from openai import RateLimitError
from openai import AsyncOpenAI

import hashlib
import chromadb

import logging

from collections import defaultdict
from pathlib import Path
from threading import Lock

import asyncio

logging.basicConfig(level=logging.INFO)

# Init Chroma
client = chromadb.PersistentClient(path=".secrets/chroma")
collection = client.get_or_create_collection("oblivion")

openai = AsyncOpenAI()

counter = 0
counter_lock = asyncio.Lock()

async def increment_counter():
    global counter
    async with counter_lock:
        counter += 1

async def decrement_counter():
    global counter
    async with counter_lock:
        counter -= 1

async def monitor_keyboard():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        try:
            # Wait 0.1s for input, non-blocking
            line = await asyncio.wait_for(reader.readline(), timeout=1.0)
            if line:
                async with counter_lock:
                    print(f"🔵 Active tasks: {counter}")
        except asyncio.TimeoutError:
            # No input, just continue looping
            continue

results = collection.get(include=["documents", "metadatas"])
for i, doc in enumerate(results["documents"]):
    print(f"\n📄 ID: {results['ids'][i]}")
    print(f"🛤 Path: {results['metadatas'][i].get('path')}")
    print(f"📚 Summary: {doc[:200]}...")

# Config
EMBED_MODEL = "text-embedding-ada-002"
locks = defaultdict(asyncio.Lock)

WORKERS = os.getenv("NUM_WORKERS")

semaphore = asyncio.Semaphore(int(WORKERS))

def hash_file(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()

def backoff_handler(details):
    logging.info("Backing off {wait:0.1f} seconds after {tries} tries "
       "calling function {target} with args {args} and kwargs "
       "{kwargs}".format(**details))

@backoff.on_exception(backoff.expo, RateLimitError)
async def summarize_code(path):
    content = Path(path).read_text(errors="ignore")[:4000]
    resp = await openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful code summarizer."},
            {"role": "user", "content": f"Summarize the following code:\n\n{content}"}
        ]
    )
    return resp.choices[0].message.content.strip()

async def embed(text):
    resp = await openai.embeddings.create(
        model=EMBED_MODEL,
        input=[text]
    )
    return resp.data[0].embedding

async def process_file(path):
    async with semaphore:
        await increment_counter()
        try:
            file_hash = hash_file(path)
            lock = locks[file_hash]

            async with lock:
                existing = collection.get(ids=[file_hash], include=[])
                if existing["ids"]:
                    logging.info(f"Skipped {path} (already indexed)")

                    return

                logging.info(f"Processing {path}")
                summary = await summarize_code(path)
                embedding = await embed(summary)
                collection.add(
                    documents=[summary],
                    embeddings=[embedding],
                    ids=[file_hash],
                    metadatas=[{
                        "path": path,
                        "language": Path(path).suffix,
                    }]
                )
                logging.info(f"✅ Indexed {path}")
        except Exception as e:
            logging.error(f"⚠️ failed to index {path}: {e}")
        # TODO: You should run this in the exception handler of summarize_code, embed and collection.add
        #       to prevent stale values
        finally:
            await decrement_counter()


async def index_codebase(root, ignore_dirs=None):
    if ignore_dirs is None:
        ignore_dirs = []

    tasks = []
    
    monitor = asyncio.create_task(monitor_keyboard())
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith((".py", ".lua", ".sh", ".yaml", ".yml")):
                full_path = os.path.join(dirpath, fname)
                if any(d in full_path for d in ignore_dirs):
                    logging.info(f"Skipping {full_path}")
                    continue
                
                tasks.append(asyncio.create_task(process_file(full_path)))

    await asyncio.gather(*tasks)
    monitor.cancel()
    try:
        await monitor
    except asyncio.CancelledError:
        pass
    logging.info("done")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python ragify.py <path-to-codebase>")
        sys.exit(1)

    codebase_path = sys.argv[1]
    ignore_dirs = [".devenv", ".direnv", ".git", ".secrets"]
    asyncio.run(index_codebase(codebase_path, ignore_dirs=ignore_dirs))
