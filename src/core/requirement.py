import os
import re

from llm.rag import build_multi_file_knowledge_base, show_chroma_collection
from requirements_extration import extract_requirements, optimize_requirements

def extract_md_rows(md_table: str):
    """
    从 markdown 表格提取每行 (模块, 需求点)，用于去重。
    """
    rows = []
    lines = md_table.strip().split("\n")
    # 跳过表头和分隔行
    content_lines = [line for line in lines if not re.match(r"^\s*(\||-)", line) or "|" in line and "---" in line]
    for line in content_lines[2:]:
        cells = [cell.strip() for cell in line.strip().split("|")[1:-1]]
        if len(cells) >= 2:
            module, requirement = cells
            rows.append((module, requirement))
    return rows


def merge_md_tables(md_tables: list):
    """
    合并多个 markdown 表格，并去重
    """
    all_rows = []
    seen = set()

    for table in md_tables:
        rows = extract_md_rows(table)
        for module, req in rows:
            key = (module, req)
            if key not in seen:
                all_rows.append(key)
                seen.add(key)

    # 重新生成 markdown 表格
    md = "| 序号 | 模块 | 需求点 |\n"
    md += "| --- | --- | --- |\n"
    for idx, (module, req) in enumerate(all_rows, 1):
        md += f"| {idx} | {module} | {req} |\n"

    if not all_rows:
        return "未发现需求点"
    else:
        return md


def main():
    # 定义需要处理的文件列表
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    file_list = [
        {
            "file_path": "D:\\testcase\\aitestcases\\data\\需求文件\\需求分析报告-湖北中烟新型烟草产品调研与开发信息反馈系统项目.docx",
            "type": "需求文档"
        },
        {
            "file_path": "D:\\testcase\\aitestcases\\data\\需求文件\\湖北中烟工程中心数字管理应用用户操作手册v1.0.docx",
            "type": "用户手册"
        },
        {
            "file_path": "D:\\testcase\\aitestcases\\data\\需求文件\\数字信息化管理应用系统接口文档.docx",
            "type": "技术文档"
        }
    ]

    # 构建知识库
    collection = build_multi_file_knowledge_base(file_list, max_len=1000)

    # 提取所有需求文档类型的 chunks
    docs = show_chroma_collection(meta_filter={"type": "需求文档"})
    print(f"从知识库提取到 {len(docs)} 个 chunks")

    optimized_tables = []

    for i, chunk in enumerate(docs, 1):
        chunk_text = chunk["content"]
        print(f"\n=== 正在处理 chunk {i} ===")

        # 第一步：提取需求表
        md_table = extract_requirements(chunk_text)

        if md_table.strip() == "未发现需求点":
            print(f"chunk {i} 未提取到需求，跳过优化")
            continue

        # 第二步：优化需求表
        optimized_table = optimize_requirements(chunk_text, md_table)
        optimized_tables.append(optimized_table)

        # 可选：也可以写每个chunk结果到文件
        with open(f"requirements_chunk_{i}_optimized.md", "w", encoding="utf-8") as f:
            f.write(optimized_table)

    # 合并所有优化后的表格
    merged_table = merge_md_tables(optimized_tables)

    # 输出最终结果
    final_path = "final_requirements.md"
    with open(final_path, "w", encoding="utf-8") as f:
        f.write(merged_table)

    print("\n需求提取与优化流程已完成！")
    print(f"最终需求已写入：{final_path}")

if __name__ == "__main__":
    main()