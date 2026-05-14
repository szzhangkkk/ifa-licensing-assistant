import re
import os
import chromadb
import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

def _infer_module(title):
    if any(k in title for k in ["欢迎", "入群", "新"]):
        return "welcome"
    if any(k in title for k in ["资料", "所需", "准备"]):
        return "document"
    if any(k in title for k in ["IA", "系统", "账号"]):
        return "ia_system"
    if any(k in title for k in ["TR", "协议", "签署"]):
        return "tr_agreement"
    if any(k in title for k in ["缴费", "费用"]):
        return "payment"
    if any(k in title for k in ["邮箱", "邮件"]):
        return "email"
    if any(k in title for k in ["合规", "培训"]):
        return "compliance"
    if any(k in title for k in ["上牌申请", "申请"]):
        return "application"
    if any(k in title for k in ["询问", "沟通"]):
        return "communication"
    return "general"

# ========== 1. 读取清理后的文档 ==========
with open("/home/szzk/ifa_knowledge_base/Agent5-Lili_cleaned.md", "r", encoding="utf-8") as f:
    raw_content = f.read()

# ========== 2. 提取 details 块（完整性优先）==========
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
        content_inner = re.sub(r'<[^>]+>', ' ', inner)
        content_inner = re.sub(r'\s+', ' ', content_inner).strip()
        if title and title in content_inner:
            content_inner = content_inner.replace(title, "", 1)
        results.append((title, f"【{title}】{content_inner}" if title else content_inner))
    return results

details_blocks = extract_yuque_details(raw_content)
print(f"Details 块数量: {len(details_blocks)}")

# ========== 3. 主体内容分块（新策略）==========
def clean_text(text):
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
            chunk_size=800, chunk_overlap=120, length_function=len
        )
    else:
        sec = "## " + sec
        sp = RecursiveCharacterTextSplitter(
            separators=["\n### ", "\n## ", "\n\n", "\n", "。", "；"],
            chunk_size=800, chunk_overlap=120, length_function=len
        )
    chunks.extend(sp.split_text(sec))

print(f"主体分块数量: {len(chunks)}")

# ========== 4. Details 块单独处理（不切分）==========
template_chunks = [b[1] for b in details_blocks]
template_metas = [
    {"chunk_type": "template", "module": _infer_module(title), "title": title}
    for title, _ in details_blocks
]

# ========== 5. 过滤 + 去重 ==========
MIN_LEN = 50
chunks = [c.strip() for c in chunks if len(c.strip()) >= MIN_LEN]

all_chunks = template_chunks + chunks
all_metas = template_metas + [{"chunk_type": "text", "module": "general"} for _ in chunks]

# 去重
seen = set()
unique_chunks = []
unique_metas = []
for c, m in zip(all_chunks, all_metas):
    if c not in seen:
        seen.add(c)
        unique_chunks.append(c)
        unique_metas.append(m)

print(f"Details 块: {len(template_chunks)}")
print(f"主体分块: {len(chunks)}")
print(f"去重后合计: {len(unique_chunks)}")

# ========== 6. 向量化 ==========
print("加载 embedding 模型...")
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

print(f"向量化 {len(unique_chunks)} 个 chunks...")
embeddings = model.encode(unique_chunks, show_progress_bar=True, normalize_embeddings=True)
print(f"Embedding 形状: {embeddings.shape}")

# ========== 7. 写入 ChromaDB ==========
db_path = "/home/szzk/ifa_knowledge_base/chroma_db"
os.makedirs(db_path, exist_ok=True)
client = chromadb.PersistentClient(path=db_path)

try:
    client.delete_collection(name="ifa_licensing_kb")
    print("已删除旧 collection")
except:
    pass

collection = client.create_collection(
    name="ifa_licensing_kb",
    metadata={"description": "IFA上牌小助手知识库", "version": "v2"},
    embedding_function=None,
)

ids = [f"chunk_{i:04d}" for i in range(len(unique_chunks))]
collection.add(
    documents=unique_chunks,
    ids=ids,
    metadatas=unique_metas,
    embeddings=embeddings.tolist()
)

print(f"\n✅ 知识库重建完成，共 {len(unique_chunks)} 个 chunks")
print(f"   存储路径: {db_path}")

# ========== 8. 验证检索 ==========
print("\n=== 检索测试 ===")
test_queries = [
    "上牌需要准备哪些资料？",
    "TR协议要怎么签署？",
    "IA系统怎么填表？",
]
for q in test_queries:
    q_emb = model.encode([q], normalize_embeddings=True)
    results = collection.query(
        query_embeddings=q_emb.tolist(),
        n_results=2,
        include=["documents", "metadatas", "distances"]
    )
    print(f"\nQ: {q}")
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        print(f"  [{dist:.3f}] ({meta.get('chunk_type','?')}/{meta.get('module','?')}) {doc[:80]}...")
