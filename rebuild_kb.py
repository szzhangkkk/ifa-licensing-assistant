#!/usr/bin/env python3
"""
IFA 知识库重建脚本
读取 Agent5-上牌小助手-Lili.md → 分块 → 向量化 → 存入 ChromaDB
"""
import re
import os
import json
from pathlib import Path

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import chromadb
from sentence_transformers import SentenceTransformer

# ── 1. 读取文档 ──────────────────────────────────────────────
doc_path = "/mnt/c/Users/14039/Desktop/Agent5-上牌小助手-Lili.md"
with open(doc_path, "r", encoding="utf-8") as f:
    raw = f.read()

# ── 2. 提取 details 块（飞书格式） ───────────────────────────
def extract_yuque_details(text):
    pattern = re.compile(
        r'<details\s+class="lake-collapse"[^>]*>(.*?)</details>',
        re.DOTALL
    )
    results = []
    for m in pattern.finditer(text):
        inner = m.group(1)
        sm = re.search(r'<summary[^>]*>(.*?)</summary>', inner, re.DOTALL)
        title = re.sub(r'<[^>]+>', '', sm.group(1)).strip() if sm else ""
        content = re.sub(r'<[^>]+>', ' ', inner)
        content = re.sub(r'\s+', ' ', content).strip()
        if title and title in content:
            content = content.replace(title, "", 1)
        results.append(f"【{title}】{content}" if title else content)
    return results

details_blocks = extract_yuque_details(raw)
print(f"提取 {len(details_blocks)} 个 details 块")

# ── 3. 清理主文档 ────────────────────────────────────────────
main_text = re.sub(r'<details[^>]*>.*?</details>', '', raw, flags=re.DOTALL)
main_text = re.sub(r'<[^>]+>', '', main_text)
main_text = re.sub(r'\n{3,}', '\n\n', main_text)
main_text = re.sub(r' {2,}', ' ', main_text).strip()

# 按 ## 功能拆分
sections = re.split(r'\n## ', main_text)

# ── 4. 分块 ──────────────────────────────────────────────────
from langchain_text_splitters import RecursiveCharacterTextSplitter

chunks = []
for i, sec in enumerate(sections):
    sec = sec.strip()
    if not sec:
        continue
    if i == 0:
        sp = RecursiveCharacterTextSplitter(
            separators=["\n# ", "\n\n", "\n"],
            chunk_size=500, chunk_overlap=60, length_function=len
        )
    else:
        sp = RecursiveCharacterTextSplitter(
            separators=["\n### ", "\n## ", "\n\n", "\n"],
            chunk_size=500, chunk_overlap=60, length_function=len
        )
        sec = "## " + sec
    chunks.extend(sp.split_text(sec))

# details 内容作为独立块
chunks.extend([b for b in details_blocks if len(b) > 20])
chunks = [c.strip() for c in chunks if len(c.strip()) > 20]
print(f"分块完成，共 {len(chunks)} 个 chunks")

# ── 5. 向量化（normalize + 多语言模型） ─────────────────────
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
print("模型加载完成，向量化中...")
embeddings = model.encode(chunks, normalize_embeddings=True, show_progress_bar=True)
print(f"向量维度: {embeddings.shape[1]}")

# ── 6. 写入 ChromaDB ─────────────────────────────────────────
persist_dir = "/home/szzk/ifa_knowledge_base/chroma_db"
os.makedirs(persist_dir, exist_ok=True)
client = chromadb.PersistentClient(path=persist_dir)

try:
    client.delete_collection(name="ifa_licensing_kb")
    print("已删除旧 Collection")
except:
    pass

collection = client.create_collection(
    name="ifa_licensing_kb",
    metadata={"description": "IFA上牌小助手知识库"},
    embedding_function=None
)

ids = [f"chunk_{i:04d}" for i in range(len(chunks))]
metadatas = [{"chunk_id": i, "source": "Agent5-上牌小助手-Lili.md"} for i in range(len(chunks))]

collection.add(
    documents=chunks,
    ids=ids,
    metadatas=metadatas,
    embeddings=embeddings.tolist()
)
print(f"写入完成！共 {collection.count()} 条")

# ── 7. 测试检索 ──────────────────────────────────────────────
print("\n=== 检索测试 ===")
queries = [
    "上牌需要准备哪些资料？",
    "IIQE考试要考哪些？",
    "新顾问入群欢迎语",
    "TR协议签署流程",
]
for q in queries:
    vec = model.encode([q]).tolist()
    results = collection.query(
        query_embeddings=vec,
        n_results=2,
        include=["documents", "distances"]
    )
    print(f"\n🔍 {q}")
    for doc, dist in zip(results['documents'][0], results['distances'][0]):
        print(f"   [{dist:.4f}] {doc[:120]}...")
