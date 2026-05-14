#!/usr/bin/env python3
"""
IFA 知识库重建脚本 — Milvus Lite 版
=====================================
从 Agent5-Lili_cleaned.md 重新构建向量知识库，
使用 Milvus Lite 嵌入式存储（替换 ChromaDB）。

用法:
    python3 rebuild_kb_v2.py

依赖:
    pip install pymilvus milvus-lite sentence-transformers langchain numpy
"""

import re
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pymilvus import MilvusClient, DataType

# ============================================================
# 配置
# ============================================================
SOURCE_FILE = os.path.join(os.path.dirname(__file__), "Agent5-Lili_cleaned.md")
DB_PATH = os.path.join(os.path.dirname(__file__), "milvus.db")
COLLECTION_NAME = "ifa_licensing_kb"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
EMBEDDING_DIM = 384  # MiniLM-L12-v2 输出维度

# HuggingFace 镜像（国内加速）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")


def infer_module(title: str) -> str:
    """根据标题推断功能模块"""
    title_lower = title.lower()
    if any(k in title_lower for k in ["欢迎", "入群", "新"]):
        return "welcome"
    if any(k in title_lower for k in ["资料", "所需", "准备"]):
        return "document"
    if any(k in title_lower for k in ["ia", "系统", "账号"]):
        return "ia_system"
    if any(k in title_lower for k in ["tr", "协议", "签署"]):
        return "tr_agreement"
    if any(k in title_lower for k in ["缴费", "费用"]):
        return "payment"
    if any(k in title_lower for k in ["邮箱", "邮件"]):
        return "email"
    if any(k in title_lower for k in ["合规", "培训"]):
        return "compliance"
    if any(k in title_lower for k in ["申请"]):
        return "application"
    if any(k in title_lower for k in ["询问", "沟通"]):
        return "communication"
    return "general"


# ============================================================
# 1. 读取源文档
# ============================================================
print("[1/6] 读取源文档...")
with open(SOURCE_FILE, "r", encoding="utf-8") as f:
    raw_content = f.read()
print(f"      文档长度: {len(raw_content)} 字符")


# ============================================================
# 2. 提取 details 折叠块（话术模板，作为独立 chunk）
# ============================================================
print("[2/6] 提取话术模板块...")

def extract_yuque_details(text: str) -> list[tuple[str, str]]:
    """提取飞书导出的 HTML details 折叠块"""
    pattern = re.compile(
        r'<details\s+class="lake-collapse"[^>]*>(.*?)</details>',
        re.DOTALL,
    )
    results = []
    for m in pattern.finditer(text):
        inner = m.group(1)
        sm = re.search(r'<summary[^>]*>(.*?)</summary>', inner, re.DOTALL)
        title = re.sub(r'<[^>]+>', '', sm.group(1)).strip() if sm else ""
        content_inner = re.sub(r'<[^>]+>', ' ', inner)
        content_inner = re.sub(r'\s+', ' ', content_inner).strip()
        if title and title in content_inner:
            content_inner = content_inner.replace(title, "", 1)
        results.append((title, f"【{title}】{content_inner}" if title else content_inner))
    return results

details_blocks = extract_yuque_details(raw_content)
print(f"      Details 块数量: {len(details_blocks)}")


# ============================================================
# 3. 主体内容按段落分块
# ============================================================
print("[3/6] 主体内容分块...")

def clean_text(text: str) -> str:
    """清理 HTML 标签和多余空白"""
    text = re.sub(r'<details[^>]*>.*?</details>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

main_clean = clean_text(raw_content)
sections = re.split(r'\n## ', main_clean)

chunks = []
for i, sec in enumerate(sections):
    if i == 0:
        sp = RecursiveCharacterTextSplitter(
            separators=["\n# ", "\n\n", "\n", "。", "；"],
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
        )
    else:
        sec = "## " + sec
        sp = RecursiveCharacterTextSplitter(
            separators=["\n### ", "\n## ", "\n\n", "\n", "。", "；"],
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
        )
    chunks.extend(sp.split_text(sec))

print(f"      主体分块数量: {len(chunks)}")


# ============================================================
# 4. 合并 + 去重
# ============================================================
print("[4/6] 合并去重...")

MIN_LEN = 50
template_chunks = [b[1] for b in details_blocks]
template_metas = [
    {"chunk_type": "template", "module": infer_module(title), "title": title}
    for title, _ in details_blocks
]

chunks = [c.strip() for c in chunks if len(c.strip()) >= MIN_LEN]

all_chunks = template_chunks + chunks
all_metas = template_metas + [
    {"chunk_type": "text", "module": "general", "title": ""} for _ in chunks
]

# 去重
seen = set()
unique_chunks = []
unique_metas = []
for c, m in zip(all_chunks, all_metas):
    if c not in seen:
        seen.add(c)
        unique_chunks.append(c)
        unique_metas.append(m)

print(f"      Details 块: {len(template_chunks)}")
print(f"      主体分块: {len(chunks)}")
print(f"      去重后合计: {len(unique_chunks)}")


# ============================================================
# 5. 向量化
# ============================================================
print(f"[5/6] 向量化 ({EMBEDDING_MODEL})...")

model = SentenceTransformer(EMBEDDING_MODEL)
embeddings = model.encode(
    unique_chunks,
    show_progress_bar=True,
    normalize_embeddings=True,  # COSINE 距离需要归一化
)
print(f"      Embedding 形状: {embeddings.shape}")


# ============================================================
# 6. 写入 Milvus
# ============================================================
print(f"[6/6] 写入 Milvus ({DB_PATH})...")

# 如果已存在旧数据库，删除
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("      已删除旧数据库")

client = MilvusClient(DB_PATH)

# 创建 collection（带 schema）
if client.has_collection(COLLECTION_NAME):
    client.drop_collection(COLLECTION_NAME)

client.create_collection(
    collection_name=COLLECTION_NAME,
    dimension=EMBEDDING_DIM,
    metric_type="COSINE",
    auto_id=False,
    enable_dynamic_field=True,  # 允许存储 text/chunk_type/module/title
)

# 构建插入数据
insert_data = []
for i, (chunk, meta, emb) in enumerate(zip(unique_chunks, unique_metas, embeddings)):
    insert_data.append({
        "id": i,
        "text": chunk,
        "vector": emb.tolist(),
        "chunk_type": meta["chunk_type"],
        "module": meta["module"],
        "title": meta.get("title", ""),
    })

# 批量插入
res = client.insert(COLLECTION_NAME, insert_data)
print(f"      已插入 {res['insert_count']} 条记录")

# 创建索引（IVF_FLAT，适合小规模；大规模用 HNSW）
index_params = client.prepare_index_params()
index_params.add_index(
    field_name="vector",
    index_type="IVF_FLAT",
    metric_type="COSINE",
    params={"nlist": 128},
)
client.create_index(COLLECTION_NAME, index_params)
client.load_collection(COLLECTION_NAME)
print("      索引已创建并加载")

# ============================================================
# 7. 验证检索
# ============================================================
print("\n=== 检索验证 ===")
test_queries = [
    "上牌需要准备哪些资料？",
    "TR协议要怎么签署？",
    "IA系统怎么填表？",
]

for q in test_queries:
    q_emb = model.encode([q], normalize_embeddings=True)
    results = client.search(
        collection_name=COLLECTION_NAME,
        data=[q_emb[0].tolist()],
        limit=3,
        output_fields=["text", "chunk_type", "module"],
    )
    print(f"\nQ: {q}")
    for hit in results[0]:
        entity = hit.get("entity", hit)
        distance = hit.get("distance", 0)
        print(f"  [{distance:.3f}] ({entity.get('chunk_type','?')}/{entity.get('module','?')}) {entity.get('text','')[:80]}...")

client.close()
print(f"\n[OK] 知识库重建完成，共 {len(unique_chunks)} 个 chunks")
print(f"      存储路径: {DB_PATH}")
