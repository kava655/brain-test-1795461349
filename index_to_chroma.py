#!/usr/bin/env python3
import json
import chromadb
from pathlib import Path

VAULT = Path(__file__).parent
IN = VAULT / "normalized" / "all_messages.jsonl"
DB = VAULT / "graph" / "chroma"

client = chromadb.PersistentClient(path=str(DB))
col = client.get_or_create_collection("messages")

existing = col.count()
print(f"📊 العناصر الموجودة مسبقاً: {existing}")

messages = [json.loads(l) for l in open(IN, encoding="utf-8")]
print(f"📥 الرسائل في الملف: {len(messages)}")

if existing >= len(messages):
    print("✅ الفهرس مكتمل مسبقاً.")
else:
    BATCH = 32
    total = len(messages)
    print(f"🚀 بدء الفهرسة (دفعات {BATCH})...")
    print("⚠️  أول دفعة ستحمّل نموذج التضمين (~80MB). انتظر.\n")
    
    for i in range(0, total, BATCH):
        batch = messages[i:i+BATCH]
        ids = [f"msg_{i+j}" for j in range(len(batch))]
        docs = [m["content"][:6000] for m in batch]
        metas = [{
            "source": m["source"],
            "account": m["account"],
            "topic": m["topic"],
            "role": m["role"],
            "conv_id": m["conv_id"] or "",
            "title": (m.get("title") or "")[:200],
        } for m in batch]
        
        try:
            col.add(ids=ids, documents=docs, metadatas=metas)
            if (i + BATCH) % 160 == 0 or i + BATCH >= total:
                print(f"  ✓ {min(i+BATCH, total)}/{total}")
        except Exception as e:
            print(f"  ✗ دفعة {i}: {e}")

print(f"\n✅ الفهرس جاهز. عدد العناصر: {col.count()}")
