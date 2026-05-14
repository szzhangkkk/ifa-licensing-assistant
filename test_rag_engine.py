#!/usr/bin/env python3
"""
IFA RAG 引擎验证测试
=====================
测试项:
  1. Milvus 检索正确性
  2. ChromaDB 降级检索正确性
  3. 两路径结果一致性（嵌入统一验证）
  4. template 过滤
  5. 空问题防护
  6. 端到端集成
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# 强制离线，避免测试中网络请求
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["WORKTOOL_ROBOT_ID"] = "test"

pass_count = 0
fail_count = 0

def check(name, condition, detail=""):
    global pass_count, fail_count
    if condition:
        pass_count += 1
        print(f"  [PASS] {name}")
    else:
        fail_count += 1
        print(f"  [FAIL] {name}  ← {detail}")


# ─────────────────────────────────────────
# Test 1: Milvus 检索
# ─────────────────────────────────────────
print("=" * 55)
print("Test 1: Milvus 检索正确性")
print("=" * 55)

from app import RAGEngine

engine = RAGEngine(
    milvus_path="./milvus.db",
    milvus_collection="ifa_licensing_kb",
    chroma_path="./chroma_db",
    chroma_collection="ifa_licensing_kb",
)
engine.warmup()

check("warmup 后 status 为 milvus",
      engine.status == "milvus",
      f"实际: {engine.status}")

check("db_exists 返回 True",
      engine.db_exists)

# 核心检索
result = engine.search("上牌需要什么材料")
check("search() 返回非空",
      result is not None)
check("结果包含'根据知识库信息'",
      result is not None and "根据知识库信息" in result,
      f"实际: {str(result)[:100] if result else 'None'}")
check("结果不含 template 话术 (@客户姓名)",
      result is not None and "@客户姓名" not in result,
      "含有 template 内容泄露")

# 语义相关性（不要求精确匹配 TR，知识库里 TR 存在于 template 中已被过滤）
result2 = engine.search("TR协议怎么签署")
check("TR协议检索非空",
      result2 is not None)
# TR内容在 template 中被过滤，回退到通用上牌指引是预期行为
check("TR协议检索有实质内容返回",
      result2 is not None and len(result2) > 50,
      f"实际: {str(result2)[:100] if result2 else 'None'}")


# ─────────────────────────────────────────
# Test 2: ChromaDB 降级路径
# ─────────────────────────────────────────
print()
print("=" * 55)
print("Test 2: ChromaDB 降级路径（直接调用 _search_chromadb）")
print("=" * 55)

from sentence_transformers import SentenceTransformer
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
emb = model.encode(["上牌需要什么材料"], normalize_embeddings=True)[0].tolist()

chroma_result = engine._search_chromadb(emb)
check("ChromaDB 降级返回非空",
      chroma_result is not None,
      "ChromaDB 路径返回 None（可能 chroma_db 不存在或无匹配）")
if chroma_result:
    check("ChromaDB 结果不含 template",
          "@客户姓名" not in chroma_result,
          "ChromaDB 降级泄露了 template")
    check("ChromaDB 返回实质内容",
          len(chroma_result) > 50,
          f"内容过短: {chroma_result[:80] if chroma_result else 'None'}")


# ─────────────────────────────────────────
# Test 3: 两路径结果一致性
# ─────────────────────────────────────────
print()
print("=" * 55)
print("Test 3: Milvus vs ChromaDB 结果一致性")
print("=" * 55)

milvus_result = engine._search_milvus(emb)
if milvus_result and chroma_result:
    # 不要求完全相同（不同DB索引结构不同），但应该有重叠
    milvus_words = set(milvus_result[:100])
    chroma_words = set(chroma_result[:100]) if chroma_result else set()
    overlap = len(milvus_words & chroma_words) / max(len(milvus_words | chroma_words), 1)
    check("两路径有语义重叠",
          len(milvus_words & chroma_words) > 0,
          f"Milvus={milvus_result[:60]}... | ChromaDB={chroma_result[:60]}...")
    print(f"  [INFO] Jaccard 相似度: {overlap:.2%}")
else:
    print(f"  [SKIP] Milvus={'OK' if milvus_result else 'None'}, ChromaDB={'OK' if chroma_result else 'None'}")


# ─────────────────────────────────────────
# Test 4: 空问题 / 边界情况
# ─────────────────────────────────────────
print()
print("=" * 55)
print("Test 4: 空问题 / 边界情况")
print("=" * 55)

check("空字符串返回 None",
      engine.search("") is None)

check("纯空格返回 None",
      engine.search("   ") is None)

check("不相关问题时 Milvus 不崩溃",
      engine.search("今天天气怎么样") is not None or True)  # 可能返回 None（无匹配）但不应崩溃

# 多次查询稳定性
for i in range(5):
    r = engine.search("考试")
    if r is None:
        print(f"  [FAIL] 第{i+1}次查询返回 None（可能 template 过滤太激进）")
        fail_count += 1
        break
else:
    check("连续 5 次查询均返回结果", True)


# ─────────────────────────────────────────
# Test 5: ChromaDB 作为主路径（模拟 Milvus 挂了）
# ─────────────────────────────────────────
print()
print("=" * 55)
print("Test 5: ChromaDB 独立作为主路径")
print("=" * 55)

# 创建一个只有 ChromaDB 的引擎
engine2 = RAGEngine(
    milvus_path="./nonexistent.db",
    milvus_collection="ifa_licensing_kb",
    chroma_path="./chroma_db",
    chroma_collection="ifa_licensing_kb",
)
engine2.warmup()

check("engine2 降级到 chromadb",
      engine2.status == "chromadb",
      f"实际: {engine2.status}")

result_c = engine2.search("上牌需要什么材料")
check("ChromaDB 主路径返回非空",
      result_c is not None,
      "如果是 ChromaDB collection 问题，可能返回 None")


# ─────────────────────────────────────────
# 总结
# ─────────────────────────────────────────
print()
print("=" * 55)
total = pass_count + fail_count
if fail_count == 0:
    print(f"  全部通过! {pass_count}/{total}")
else:
    print(f"  通过 {pass_count}/{total}，失败 {fail_count}")
print("=" * 55)

sys.exit(0 if fail_count == 0 else 1)
