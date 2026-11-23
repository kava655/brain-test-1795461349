#!/usr/bin/env python3
"""vault_server.py — خادم MCP يربط أي AI بخزنة المعرفة"""
import sys, json

def main():
    try:
        import chromadb
        from chromadb import Documents, Embeddings
        from fastembed import TextEmbedding
    except ImportError:
        sys.stderr.write("ERROR: chromadb/fastembed not available in this Python\n")
        sys.exit(1)

    class FastEmbedFunction(chromadb.EmbeddingFunction):
        def __init__(self):
            self.model = TextEmbedding(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        def name(self): return "paraphrase-multilingual-MiniLM-L12-v2"
        def get_config(self): return {}
        def __call__(self, input):
            return [list(map(float, e)) for e in self.model.embed(list(input))]

    try:
        ef = FastEmbedFunction()
        client = chromadb.PersistentClient(path="/root/unified-brain/graph/chroma")
        col = client.get_collection("messages", embedding_function=ef)
    except Exception as e:
        sys.stderr.write(f"ERROR: cannot open Chroma: {e}\n")
        sys.exit(1)

    TOOLS = [
        {
            "name": "search",
            "description": "ابحث دلالياً في أرشيف محادثات المستخدم القديمة (DeepSeek, Claude, ChatGPT, Gemini). استخدمه تلقائياً كلما احتجت سياقاً من نقاشات سابقة عن التصميم، التداول، الإنتاج، علم النفس، أو مشاريع البرمجة.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "ما تبحث عنه (بالعربية أو الإنجليزية)"},
                    "topic": {"type": "string", "enum": ["design","trading","production","psychology","projects","misc"], "description": "اختياري: تصفية حسب الموضوع"},
                    "limit": {"type": "integer", "default": 5, "description": "عدد النتائج (1-10)"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "list_topics",
            "description": "قائمة المواضيع المتاحة في الخزنة مع عدد الرسائل في كل منها.",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ]

    def search(query, topic=None, limit=5):
        where = {"topic": topic} if topic else None
        res = col.query(query_texts=[query], n_results=min(limit, 10), where=where)
        out = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            out.append({
                "content": doc[:2000],
                "topic": meta.get("topic"),
                "source": meta.get("source"),
                "role": meta.get("role"),
                "title": meta.get("title"),
                "similarity": round(1 - dist, 3) if dist is not None else None
            })
        return out

    def list_topics():
        data = col.get(include=["metadatas"])
        counts = {}
        for m in data["metadatas"]:
            t = m.get("topic","misc")
            counts[t] = counts.get(t, 0) + 1
        return [{"topic": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except:
            continue
        method = req.get("method")
        rid = req.get("id")
        
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                      "serverInfo": {"name": "unified-brain-vault", "version": "1.0"}}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            try:
                name = req["params"]["name"]
                args = req["params"].get("arguments", {})
                if name == "search":
                    output = search(args.get("query",""), args.get("topic"), args.get("limit", 5))
                elif name == "list_topics":
                    output = list_topics()
                else:
                    output = {"error": f"unknown tool {name}"}
                result = {"content": [{"type": "text", "text": json.dumps(output, ensure_ascii=False, indent=2)}]}
            except Exception as e:
                result = {"content": [{"type": "text", "text": f"ERROR: {e}"}], "isError": True}
        elif method == "notifications/initialized":
            continue
        else:
            result = None
        
        if result is not None:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
