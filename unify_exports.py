#!/usr/bin/env python3
import json, glob, hashlib
from pathlib import Path

VAULT = Path(__file__).parent
OUT = VAULT / "normalized" / "all_messages.jsonl"
OUT.parent.mkdir(exist_ok=True)

def classify(text):
    t = text.lower()
    if any(w in t for w in ["z3r0","apk","termux","mainactivity","daemon.py","code_part"]): return "projects"
    if any(w in t for w in ["تصميم","واجهة المستخدم","ux","ui","figma","iris","aurastack"]): return "design"
    if any(w in t for w in ["تداول","trading","سهم","عملة","شارت","forex"]): return "trading"
    if any(w in t for w in ["فيديو","إنتاج","محتوى","clip2earn","يوتيوب"]): return "production"
    if any(w in t for w in ["نفس","psychology","سلوك","اكتئاب","قلق","therapy"]): return "psychology"
    if any(w in t for w in ["كود","python","java","bug"]): return "projects"
    return "misc"

seen = set()
count = 0

def write(source, account, conv_id, role, content, ts=None, title=None):
    global count
    if not content or not str(content).strip(): return
    content = str(content).strip()
    if len(content) < 3: return
    h = hashlib.md5(content.encode("utf-8")).hexdigest()
    if h in seen: return
    seen.add(h)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "source": source, "account": account, "conv_id": conv_id,
            "role": role, "content": content, "topic": classify(content),
            "ts": ts, "title": title
        }, ensure_ascii=False) + "\n")
    count += 1

def account_of(path, platform):
    try:
        rel = Path(path).relative_to(VAULT / "raw" / platform)
        if len(rel.parts) > 1: return rel.parts[0]
    except ValueError: pass
    return "default"

for path in glob.glob(str(VAULT / "raw/deepseek/**/*.json"), recursive=True):
    try: d = json.load(open(path, encoding="utf-8"))
    except: continue
    if not isinstance(d, dict) or "messages" not in d: continue
    acc = account_of(path, "deepseek")
    cid = d.get("id") or Path(path).stem
    title = d.get("title","")
    for m in d.get("messages", []):
        role = (m.get("role") or "").lower()
        role = "user" if role == "user" else "assistant"
        for frag in m.get("fragments", []):
            if frag.get("type") in ("REQUEST","RESPONSE"):
                write("deepseek", acc, cid, role, frag.get("content",""), m.get("inserted_at"), title)

print(f"\n✅ تم التوحيد: {count} رسالة فريدة")
print(f"   📁 {OUT}")
