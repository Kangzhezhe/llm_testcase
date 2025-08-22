import os
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from llm.template_parser.table_parser import TableParser
from llm.llm import LLM
from pydantic import BaseModel,Field
from typing import List

class RequirementRow(BaseModel):
    index: int = Field(..., description="序号，从1开始依次递增")
    module: str = Field(..., description="模块名称")
    requirement: str = Field(..., description="需求点")

class RequirementTableModel(BaseModel):
    rows: List[RequirementRow]

def extract_requirements(document: str, llm: LLM, table_parser: TableParser):
    prompt = (
        "你是专业的需求分析师。\n"
        "请从以下文档中，提取所有模块名称及对应的需求点，输出结构化表格数据。\n"
        "不要输出多余文字，只输出结构化表格。\n"
        "\n文档如下：\n" + document
    )
    result = llm.call(prompt, parser=table_parser)
    return result['data']['table']['rows']

def optimize_requirements(document: str, requirements_md: str, llm: LLM, table_parser: TableParser):
    prompt = (
        "你是资深需求分析师，请对比以下需求文档与需求表格，进行如下优化：\n"
        "1. 增补遗漏的需求点（文档中有，表中没有）\n"
        "2. 删除冗余的非需求内容\n"
        "3. 修正分类错误或表述错误的需求\n"
        "\n需求文档如下：\n"
        f"{document}\n"
        "\n待优化需求表如下：\n"
        f"{requirements_md}\n"
    )

    result = llm.call(prompt, parser=table_parser)
    return result['data']['table']['rows']

def final_llm_optimize(requirements_md: str, llm: LLM, table_parser: TableParser):
    prompt = (
        "你是一名经验丰富的软件产品分析专家，以下是一张需求表格（Markdown 格式），包含多个模块及其下的多个需求点。\n"
        "请对该表进行需求点的语义去重，仅合并同一模块下重复或冗余需求。模块名不变。\n"
        "\n需求表格如下：\n"
        f"{requirements_md}\n"
    )

    result = llm.call(prompt, parser=table_parser )
    return result['data']['table']['rows']
 
    return llm.call(prompt)["data"]["text"]

def main():
    document_path = "data/中烟cutPRD.md"
    if not os.path.exists('output'):
        os.makedirs('output')
    with open(document_path, "r", encoding="utf-8") as f:
        prd_content = f.read()

    llm = LLM(logger=True)
    table_parser = TableParser(RequirementTableModel, value_only=True)

    # 提取需求
    rows = extract_requirements(prd_content, llm, table_parser)
    print(rows)
    
    md_content = table_parser.to_markdown(rows)
    md_lines = md_content.splitlines()
    if len(md_lines) >= 2:
        md_lines[0] = "| 序号 | 模块 | 需求点 |"
        md_content = "\n".join(md_lines)

    with open("output/requirements.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    print("\n初次结构化提取完成，已写入 output/requirements.md")
    print(md_content)

 # Step 2: 优化需求
    with open("output/requirements.md", "r", encoding="utf-8") as f:
        requirements_md = f.read()

    optimized_rows = optimize_requirements(prd_content, requirements_md, llm, table_parser)
    optimized_md = table_parser.to_markdown(optimized_rows)

    md_lines = optimized_md.splitlines()
    if len(md_lines) >= 2:
        md_lines[0] = "| 序号 | 模块 | 需求点 |"
        optimized_md = "\n".join(md_lines)

    with open("output/requirements_optimized.md", "w", encoding="utf-8") as f:
        f.write(optimized_md)

    print("\nStep 2: 优化需求完成，已写入 output/requirements_optimized.md")
    print(optimized_md)

      # Step 3: 最终去重
    final_rows = final_llm_optimize(optimized_md, llm, table_parser)
    final_md = table_parser.to_markdown(final_rows)

    md_lines = final_md.splitlines()
    if len(md_lines) >= 2:
        md_lines[0] = "| 序号 | 模块 | 需求点 |"
        final_md = "\n".join(md_lines)

    with open("output/requirements_final.md", "w", encoding="utf-8") as f:
        f.write(final_md)

    print("\nStep 3: 需求最终去重完成，已写入 output/requirements_final.md")
    print(final_md)
 
if __name__ == "__main__":
     main()