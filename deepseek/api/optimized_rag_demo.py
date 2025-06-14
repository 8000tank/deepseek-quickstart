#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化的RAG演示：使用章节分块策略改进检索效果
"""

import os
import re
import json
from typing import List, Tuple
from tqdm import tqdm
from pymilvus import MilvusClient, model as milvus_model
from openai import OpenAI


def parse_articles_with_chapter_context(file_path: str) -> List[Tuple[str, str]]:
    """
    按条文分割，但保留章节上下文信息
    """

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    # 按章节分割（#### 开头的标题）
    chapter_pattern = r"^####\s+(.+)$"
    chapter_matches = list(re.finditer(chapter_pattern, content, re.MULTILINE))

    articles = []

    for i, match in enumerate(chapter_matches):
        chapter_title = match.group(1).strip()
        start_pos = match.start()

        # 确定章节内容的结束位置
        if i + 1 < len(chapter_matches):
            end_pos = chapter_matches[i + 1].start()
            chapter_content = content[start_pos:end_pos].strip()
        else:
            chapter_content = content[start_pos:].strip()

        # 查找该章节之前的编、部分信息
        content_before = content[:start_pos]

        # 查找最近的编标题（### 开头）
        part_matches = list(re.finditer(r"^###\s+(.+)$", content_before, re.MULTILINE))
        current_part = part_matches[-1].group(1).strip() if part_matches else ""

        # 查找最近的更高级标题（## 开头）
        book_matches = list(re.finditer(r"^##\s+(.+)$", content_before, re.MULTILINE))
        current_book = book_matches[-1].group(1).strip() if book_matches else ""

        # 构建完整的层级标题
        full_title_parts = []
        if current_book:
            full_title_parts.append(current_book)
        if current_part:
            full_title_parts.append(current_part)
        full_title_parts.append(f"第{chapter_title}")

        chapter_context = " / ".join(full_title_parts)

        # 按条文分割（**第XXX条** 格式）
        article_pattern = r"\*\*第[零一二三四五六七八九十百千万\d]+条\*\*"
        article_matches = list(re.finditer(article_pattern, chapter_content))

        for j, article_match in enumerate(article_matches):
            article_title_match = article_match.group(0)
            article_start = article_match.start()

            # 确定条文内容的结束位置
            if j + 1 < len(article_matches):
                article_end = article_matches[j + 1].start()
                article_content = chapter_content[article_start:article_end].strip()
            else:
                article_content = chapter_content[article_start:].strip()

            # 构建包含章节上下文的标题和内容
            full_article_title = f"{chapter_context} / {article_title_match}"

            # 在条文内容前加上上下文信息，使embedding能理解更丰富的语义
            enhanced_content = f"【{full_article_title}】\n\n{article_content}"

            articles.append((full_article_title, enhanced_content))

    return articles


def build_optimized_rag_system(file_path: str, collection_name: str = "optimized_rag_collection"):
    """
    构建优化的RAG系统
    """

    print("📖 解析文档并生成优化分块...")
    articles = parse_articles_with_chapter_context(file_path)
    print(f"✅ 共生成 {len(articles)} 个条文块")

    # 使用默认embedding模型（在实际项目中建议使用更强的中文模型如BGE）
    print("🔧 初始化Embedding模型...")
    embedding_model = milvus_model.DefaultEmbeddingFunction()

    # 测试embedding维度
    test_embedding = embedding_model.encode_queries(["测试"])[0]
    embedding_dim = len(test_embedding)
    print(f"✅ Embedding维度: {embedding_dim}")

    # 初始化Milvus客户端
    print("🗄️  初始化Milvus数据库...")
    milvus_client = MilvusClient(uri="./optimized_milvus.db")

    # 如果collection已存在则删除
    if milvus_client.has_collection(collection_name):
        milvus_client.drop_collection(collection_name)
        print("🗑️  删除已存在的collection")

    # 创建新collection
    milvus_client.create_collection(
        collection_name=collection_name,
        dimension=embedding_dim,
        metric_type="COSINE",  # 使用余弦相似度，对长度归一化更友好
        consistency_level="Strong"
    )
    print("✅ 创建新collection成功")

    # 生成embeddings并插入数据
    print("🚀 生成embeddings并插入数据...")

    # 只对文本内容生成embedding，不包括标题前缀
    text_content_only = [content for _, content in articles]
    doc_embeddings = embedding_model.encode_documents(text_content_only)

    data = []
    for i, ((title, content), embedding) in enumerate(tqdm(
        zip(articles, doc_embeddings),
        desc="准备数据",
        total=len(articles)
    )):
        data.append({
            "id": i,
            "vector": embedding,
            "title": title,
            "text": content
        })

    # 批量插入
    insert_result = milvus_client.insert(collection_name=collection_name, data=data)
    print(f"✅ 成功插入 {insert_result['insert_count']} 条记录")

    return milvus_client, embedding_model, collection_name


def search_with_optimized_rag(
    question: str,
    milvus_client: MilvusClient,
    embedding_model,
    collection_name: str,
    top_k: int = 5
):
    """
    使用优化的RAG系统进行搜索
    """

    print(f"\n🔍 搜索问题: {question}")

    # 生成查询embedding
    query_embedding = embedding_model.encode_queries([question])

    # 执行向量搜索
    search_results = milvus_client.search(
        collection_name=collection_name,
        data=query_embedding,
        limit=top_k,
        search_params={"metric_type": "COSINE", "params": {}},
        output_fields=["title", "text"]
    )

    print(f"📋 检索到 {len(search_results[0])} 个相关结果:")

    retrieved_contexts = []
    for i, result in enumerate(search_results[0]):
        score = result["distance"]
        title = result["entity"]["title"]
        content = result["entity"]["text"]

        print(f"\n{i + 1}. 相似度得分: {score:.4f}")
        print(f"   标题: {title}")
        print(f"   内容预览: {content[:150]}...")

        retrieved_contexts.append((title, content, score))

    return retrieved_contexts


def generate_answer_with_deepseek(question: str, contexts: List[Tuple[str, str, float]]):
    """
    使用DeepSeek生成答案
    """

    # 构建上下文
    context_text = "\n\n".join([content for _, content, _ in contexts])

    # 构建prompt
    SYSTEM_PROMPT = """
你是一个专业的法律AI助手。请基于提供的法律条文上下文，准确回答用户的问题。
注意：
1. 只基于提供的上下文信息回答问题
2. 如果上下文中没有足够信息，请明确说明
3. 引用具体的法条时请标明条文编号
4. 回答要准确、简洁、易懂
"""

    USER_PROMPT = f"""
请基于以下法律条文回答问题：

<上下文>
{context_text}
</上下文>

<问题>
{question}
</问题>

请提供准确的法律解答：
"""

    # 调用DeepSeek API
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return "❌ 错误：未设置DEEPSEEK_API_KEY环境变量"

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1"
    )

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT}
            ],
            temperature=0.1  # 较低的temperature确保回答的一致性
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"❌ 调用DeepSeek API时出错: {str(e)}"


def main():
    """
    主演示函数
    """

    print("=" * 60)
    print("🚀 优化RAG系统演示")
    print("=" * 60)

    # 构建RAG系统
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "mfd.md")
    milvus_client, embedding_model, collection_name = build_optimized_rag_system(file_path)

    # 测试问题
    test_questions = [
        "权利人、利害关系人认为不动产登记簿记载的事项错误时怎么办？",
        "什么是异议登记？",
        "不动产登记簿和不动产权属证书记载不一致时以哪个为准？"
    ]

    for question in test_questions:
        print("\n" + "=" * 60)

        # 检索相关上下文
        contexts = search_with_optimized_rag(
            question,
            milvus_client,
            embedding_model,
            collection_name,
            top_k=3
        )

        # 生成答案
        print("\n🤖 生成答案:")
        answer = generate_answer_with_deepseek(question, contexts)
        print(answer)

        print("\n" + "-" * 60)

    print("\n✅ 演示完成！")


if __name__ == "__main__":
    main()
