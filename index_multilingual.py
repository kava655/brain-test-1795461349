#!/usr/bin/env python3
import json
import chromadb
from chromadb import Documents, Embeddings
from fastembed import TextEmbedding
from pathlib import Path

class FastEmbedFunction(chromadb.EmbeddingFunction):
    def __init__(self, model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.model = TextEmbedding(model_name=model_name)
    def name(self): return "paraphrase-multilingual-MiniLM-L12-v2"
    def get_config(self): return {}
    def __call__(self, input: Documents) -> Embeddings:
        return [list(map(float, e)) for e in self.model.embed(list(input))]

VAULT = Path(__file__).parent
IN = VAULT / "normalized" / "all_messages.jsonl"
DB = VAULT / "graph" / "chroma"

print("📥 تحميل نموذج paraphrase-multilingual (220MB)...")
ef = FastEmbedFunction()
print("✅ النموذج جاهز\n")

client = chromadb.PersistentClient(path=str(DB))
col = client.get_or_create_collection("messages", embedding_function=ef)

messages = [json.loads(l) for l in open(IN, encoding="utf-8")]
total = len(messages)
print(f"📊 إجمالي الرسائل: {total}\n")

BATCH = 16
for i in range(0, total, BATCH):
    batch = messages[i:i+BATCH]
    ids = [f"msg_{i+j}" for j in range(len(batch))]
    docs = [m["content"][:6000] if m.get("content") else "(فارغ)" for m in batch]
    metas = [{
        "source": m.get("source","?"), "account": m.get("account","?"),
        "topic": m.get("topic","misc"), "role": m.get("role","?"),
        "conv_id": (m.get("conv_id") or "")[:100],
        "title": (m.get("title") or "")[:200],
    } for m in batch]
    try:
        col.add(ids=ids, documents=docs, metadatas=metas)
        if (i+BATCH) % 160 == 0 or i+BATCH >= total:
            print(f"  ✓ {min(i+BATCH, total)}/{total}")
    except Exception as e:
        print(f"  ⚠️ {i}: {str(e)[:80]}")
        for j in range(len(batch)):
            try: col.add(ids=[ids[j]], documents=[docs[j]], metadatas=[metas[j]])
            except: pass

print(f"\n✅ الفهرس جاهز: {col.count()}/{total}")
