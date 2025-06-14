#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG调试工具：诊断检索问题
"""

import os
import re
from typing import List, Tuple
from pymilvus import MilvusClient, model as milvus_model
from sentence_transformers import SentenceTransformer


def load_and_parse_articles(file_path: str) -> List[Tuple[str, str]]:
    """加载并解析条文"""

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    # 简单按条文分割进行测试
    article_pattern = r"\*\*第[零一二三四五六七八九十百千万\d]+条\*\*"

    # 找到所有条文
    article_matches = list(re.finditer(article_pattern, content))

    articles = []
    for i, match in enumerate(article_matches):
        article_title = match.group(0)
        start_pos = match.start()

        # 确定条文内容的结束位置
        if i + 1 < len(article_matches):
            end_pos = article_matches[i + 1].start()
            article_content = content[start_pos:end_pos].strip()
        else:
            article_content = content[start_pos:].strip()

        articles.append((article_title, article_content))

    return articles


def debug_search():
    """调试搜索功能"""

    print("🔍 RAG系统调试")
    print("=" * 50)

    # 加载数据
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "mfd.md")
    articles = load_and_parse_articles(file_path)

    print(f"📊 总共解析出 {len(articles)} 个条文")

    # 手动查找目标条文
    target_keywords = ["不动产登记簿", "错误", "更正", "异议"]

    print("\n🎯 手动搜索相关条文:")
    relevant_articles = []

    for i, (title, content) in enumerate(articles):
        score = sum(1 for keyword in target_keywords if keyword in content)
        if score > 0:
            relevant_articles.append((score, i, title, content))

    # 按相关度排序
    relevant_articles.sort(key=lambda x: x[0], reverse=True)

    print(f"找到 {len(relevant_articles)} 个相关条文:")
    for j, (score, idx, title, content) in enumerate(relevant_articles[:5]):
        print(f"\n{j + 1}. 相关度: {score}, 索引: {idx}")
        print(f"   标题: {title}")
        print(f"   内容: {content[:200]}...")

    if not relevant_articles:
        print("❌ 没有找到相关条文！")
        return

    # 使用embedding模型测试
    print("\n🧠 测试Embedding模型:")
    print("正在加载 BAII/bge-large-zh-v1.5 Embedding 模型，这可能需要一些时间...")
    embedding_model = SentenceTransformer('BAAI/bge-large-zh-v1.5')
    print("模型加载完成。")

    # 测试目标条文的embedding
    target_article = relevant_articles[0]  # 最相关的条文
    target_content = target_article[3]

    print(f"目标条文: {target_article[2]}")

    # 生成embedding
    query = "权利人、利害关系人认为不动产登记簿记载的事项错误时怎么办？"

    query_embedding = embedding_model.encode([query])[0]
    target_embedding = embedding_model.encode([target_content])[0]

    # 计算相似度
    import numpy as np

    # 余弦相似度
    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    similarity = cosine_similarity(query_embedding, target_embedding)
    print(f"问题与目标条文的余弦相似度: {similarity:.4f}")

    # 测试其他几个条文的相似度
    print("\n📊 与其他条文的相似度对比:")

    test_indices = [0, 10, 50, 100, 200]  # 测试不同位置的条文

    for idx in test_indices:
        if idx < len(articles):
            test_content = articles[idx][1]
            test_embedding = embedding_model.encode([test_content])[0]
            test_similarity = cosine_similarity(query_embedding, test_embedding)

            print(f"条文 {idx} ({articles[idx][0]}): {test_similarity:.4f}")

    # 尝试Milvus搜索
    print("\n🗄️  测试Milvus搜索:")

    milvus_client = MilvusClient(uri="./debug_milvus.db")
    collection_name = "debug_collection"

    # 删除已存在的collection
    if milvus_client.has_collection(collection_name):
        milvus_client.drop_collection(collection_name)

    # 创建collection
    milvus_client.create_collection(
        collection_name=collection_name,
        dimension=1024,
        metric_type="COSINE",
        consistency_level="Strong"
    )

    # 插入少量数据进行测试
    test_articles = articles[:20]  # 使用前20个条文进行测试
    if relevant_articles:
        # 添加最相关的条文（确保格式一致）
        target_score, target_idx, target_title, target_content = relevant_articles[0]
        test_articles.append((target_title, target_content))

    embeddings = embedding_model.encode([content for _, content in test_articles])

    data = []
    for i, ((title, content), embedding) in enumerate(zip(test_articles, embeddings)):
        data.append({
            "id": i,
            "vector": embedding,
            "title": title,
            "text": content
        })

    milvus_client.insert(collection_name=collection_name, data=data)

    # 执行搜索
    search_results = milvus_client.search(
        collection_name=collection_name,
        data=[query_embedding],
        limit=5,
        search_params={"metric_type": "COSINE", "params": {}},
        output_fields=["title", "text"]
    )

    print("🔍 Milvus搜索结果:")
    for i, result in enumerate(search_results[0]):
        score = result["distance"]
        title = result["entity"]["title"]

        print(f"{i + 1}. 相似度: {score:.4f}")
        print(f"   标题: {title}")
        print(f"   内容: {result['entity']['text'][:100]}...")


if __name__ == "__main__":
    debug_search()
