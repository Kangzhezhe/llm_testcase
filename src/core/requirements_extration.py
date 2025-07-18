import os
import sys
from src.ENV import llm_url, llm_api_key, llm_default_model
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from llm.template_parser.table_parser import TableParser
from llm.llm import LLM
from pydantic import BaseModel
from typing import List

class RequirementRow(BaseModel):
    index: int         # 序号
    module: str        # 模块
    requirement: str   # 需求点

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
        md_lines[0] = "| 序号 | 模块 | 需求点 |"
        md_content = "\n".join(md_lines)

    with open("requirements.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    print("\n初次结构化提取完成，已写入 requirements.tsv/csv/md/json")
    print(md_content)


if __name__ == "__main__":
    main()