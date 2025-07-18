import os
import sys
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
    requirement_text: str = Field(..., description="原始需求文本")

class RequirementTableModel(BaseModel):
    rows: List[RequirementRow]

def extract_requirements(document: str, llm: LLM, table_parser: TableParser):
    prompt = (
        "你是专业的需求分析师。\n"
        "请从以下文档中，提取所有模块名称及对应的需求点，与原始需求文本，输出结构化表格数据。\n"
        "不要输出多余文字，只输出结构化表格。\n"
        "\n文档如下：\n" + document
    )
    result = llm.call(prompt, parser=table_parser)
    return result['data']['table']['rows']


def main():
    document_path = "data/中烟cutPRD.md"
    with open(document_path, "r", encoding="utf-8") as f:
        prd_content = f.read()

    llm = LLM(logger=True)
    table_parser = TableParser(RequirementTableModel, value_only=True)

    # 提取需求
    rows = extract_requirements(prd_content, llm, table_parser)
    
    md_content = table_parser.to_markdown(rows)
    md_lines = md_content.splitlines()
    if len(md_lines) >= 2:
        md_lines[0] = "| 序号 | 模块 | 需求点 | 原始需求文本 |"
        md_content = "\n".join(md_lines)

    with open("requirements.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    print("\n初次结构化提取完成，已写入 requirements.md")
    print(md_content)


if __name__ == "__main__":
    main()