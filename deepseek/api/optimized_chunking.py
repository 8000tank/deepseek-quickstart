#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化的分块策略：按章节分块并保留层级上下文信息
"""

import re
from typing import List, Tuple


def parse_civil_code_by_chapters(file_path: str) -> List[Tuple[str, str]]:
    """
    按章节（#### 开头）分块民法典内容，并保留层级上下文信息

    Args:
        file_path: 民法典md文件路径

    Returns:
        List[Tuple[str, str]]: [(章节标题, 章节内容), ...]
    """

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    # 按章节分割（#### 开头的标题）
    chapter_pattern = r"^####\s+(.+)$"
    chapters = []

    # 找到所有章节标题及其位置
    chapter_matches = list(re.finditer(chapter_pattern, content, re.MULTILINE))

    # 确定当前所在的编、部分等上级标题
    lines = content.split('\n')
    current_part = ""  # 当前编（如"物权编"）
    current_book = ""  # 当前部分（如果有的话）

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

        # 查找最近的编标题（### 开头，如"### （二）物权编"）
        part_matches = list(re.finditer(r"^###\s+(.+)$", content_before, re.MULTILINE))
        if part_matches:
            current_part = part_matches[-1].group(1).strip()

        # 查找最近的更高级标题（## 开头）
        book_matches = list(re.finditer(r"^##\s+(.+)$", content_before, re.MULTILINE))
        if book_matches:
            current_book = book_matches[-1].group(1).strip()

        # 构建完整的层级标题
        full_title_parts = []
        if current_book:
            full_title_parts.append(current_book)
        if current_part:
            full_title_parts.append(current_part)
        full_title_parts.append(f"第{chapter_title}")

        full_title = " / ".join(full_title_parts)

        # 在章节内容前加上完整的层级信息
        enhanced_content = f"【{full_title}】\n\n{chapter_content}"

        chapters.append((full_title, enhanced_content))

    return chapters


def parse_articles_within_chapters(chapters: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """
    在章节分块的基础上，进一步按条文分割，但保留章节上下文

    Args:
        chapters: 章节分块结果

    Returns:
        List[Tuple[str, str]]: [(章节+条文信息, 条文内容), ...]
    """

    articles = []

    for chapter_title, chapter_content in chapters:
        # 按条文分割（**第XXX条** 格式）
        article_pattern = r"\*\*第[零一二三四五六七八九十百千万\d]+条\*\*"

        # 找到所有条文
        article_matches = list(re.finditer(article_pattern, chapter_content))

        for i, match in enumerate(article_matches):
            article_title_match = match.group(0)
            start_pos = match.start()

            # 确定条文内容的结束位置
            if i + 1 < len(article_matches):
                end_pos = article_matches[i + 1].start()
                article_content = chapter_content[start_pos:end_pos].strip()
            else:
                article_content = chapter_content[start_pos:].strip()

            # 提取条文号
            article_num = re.search(r"第([零一二三四五六七八九十百千万\d]+)条", article_title_match)
            if article_num:
                article_number = article_num.group(1)

                # 构建包含章节上下文的标题
                full_article_title = f"{chapter_title} / {article_title_match}"

                # 在条文内容前加上上下文信息
                enhanced_article_content = f"【{full_article_title}】\n\n{article_content}"

                articles.append((full_article_title, enhanced_article_content))

    return articles


def main():
    """主函数，演示两种分块策略"""

    import os
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "mfd.md")

    print("=== 策略1: 按章节分块 ===")
    chapters = parse_civil_code_by_chapters(file_path)
    print(f"总共分为 {len(chapters)} 个章节块")

    # 显示前3个章节块的信息
    for i, (title, content) in enumerate(chapters[:3]):
        print(f"\n--- 章节 {i + 1} ---")
        print(f"标题: {title}")
        print(f"内容长度: {len(content)} 字符")
        print(f"内容预览:\n{content[:200]}...")
        print("-" * 50)

    print("\n=== 策略2: 章节+条文双层分块 ===")
    articles = parse_articles_within_chapters(chapters)
    print(f"总共分为 {len(articles)} 个条文块")

    # 显示前3个条文块的信息
    for i, (title, content) in enumerate(articles[:3]):
        print(f"\n--- 条文 {i + 1} ---")
        print(f"标题: {title}")
        print(f"内容长度: {len(content)} 字符")
        print(f"内容预览:\n{content[:300]}...")
        print("-" * 50)

    # 特别查找包含"不动产登记簿记载的事项错误"相关的条文
    print("\n=== 查找相关条文 ===")
    target_keywords = ["不动产登记簿", "错误", "更正", "异议"]

    relevant_articles = []
    for title, content in articles:
        if any(keyword in content for keyword in target_keywords):
            # 计算相关度得分
            score = sum(1 for keyword in target_keywords if keyword in content)
            relevant_articles.append((score, title, content))

    # 按相关度排序
    relevant_articles.sort(key=lambda x: x[0], reverse=True)

    print(f"找到 {len(relevant_articles)} 个相关条文:")
    for i, (score, title, content) in enumerate(relevant_articles[:5]):
        print(f"\n{i + 1}. 相关度得分: {score}")
        print(f"   标题: {title}")
        print(f"   内容预览: {content[:200]}...")


if __name__ == "__main__":
    main()
