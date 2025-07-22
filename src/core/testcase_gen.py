import pandas as pd
from pydantic import BaseModel, Field
from typing import List
import io
import os,sys
import concurrent.futures

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from llm.template_parser.table_parser import TableParser
from llm.llm import LLM

from requirements_extration import RequirementRow, RequirementTableModel
from collections import defaultdict
from tqdm import tqdm


class TestcaseRow(BaseModel):
    index: int = Field(..., description="序号,从1开始依次递增")
    module: str = Field(..., description="模块名称")
    requirement: str = Field(..., description="需求点")
    testcase_point: str = Field(..., description="用例测试点")
    precondition: str = Field(..., description="前提与约束")
    steps: str = Field(..., description="操作步骤及输入数据")
    expected: str = Field(..., description="预期结果")

class TestcaseTableModel(BaseModel):
    rows: List[TestcaseRow]

def read_md_table(md_path: str) -> RequirementTableModel:
    # 读取 markdown 表格为 DataFrame
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    # 找到表格起始行
    table_lines = [line for line in lines if line.strip().startswith("|")]
    # 拼接为单个字符串
    table_str = "".join(table_lines)
    # 用 pandas 读取
    df = pd.read_csv(io.StringIO(table_str), sep="|", header=0, skipinitialspace=True)
    # 去除空列名和空行
    df = df.loc[:, df.columns.notnull()]
    df = df.dropna(how="all")
    # 去除首尾空格和多余列
    df = df.rename(columns=lambda x: x.strip())
    df = df[["序号", "模块", "需求点"]]
    # 过滤掉分隔行
    df = df[df["序号"].str.strip().apply(lambda x: x.isdigit())]
    rows = [
        RequirementRow(
            index=int(row["序号"]),
            module=str(row["模块"]).strip(),
            requirement=str(row["需求点"]).strip()
        )
        for _, row in df.iterrows()
    ]
    return RequirementTableModel(rows=rows)

# 用法示例
if __name__ == "__main__":
    model = read_md_table("data/final_requirements.md")

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    file_list = [
        {
            "file_path": "data\\需求文件\\需求分析报告-湖北中烟新型烟草产品调研与开发信息反馈系统项目.docx",
            "type": "需求文档"
        },
        {
            "file_path": "data\\需求文件\\湖北中烟工程中心数字管理应用用户操作手册v1.0.docx",
            "type": "用户手册"
        },
        {
            "file_path": "data\\需求文件\\数字信息化管理应用系统接口文档.docx",
            "type": "技术文档"
        }
    ]
    llm = LLM()
    llm.build_knowledge_base(file_list)

    all_testcases = []

    def generate_testcase(req):
        prompt = f"请根据以下需求点生成针对该功能的测试用例：\n模块：{req.module}\n需求点：{req.requirement}"
        docs = llm.search_knowledge(prompt, collection_name="rag_demo", meta_filter={"type": "re:用户手册|技术文档"})
        prompt += (
            "\n\n以上检索到的知识块是与当前需求点相关的用户手册和技术文档，"
            "请根据以上信息生成与需求点相关且满足手册文档规范的测试用例，忽略其他无关内容。\n"
        )
        table_parser = TableParser(TestcaseTableModel, value_only=True)
        answer = llm.call(prompt, docs=docs, parser=table_parser)
        if not answer or not isinstance(answer, dict) or "data" not in answer:
            print(f"生成测试用例失败，需求点：{req.requirement}")
            return []
        rows = answer['data']['table']['rows']
        return rows

    all_testcases = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(generate_testcase, req) for req in model.rows]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="生成测试用例"):
            rows = future.result()
            all_testcases.extend(rows)

    # 按 (模块, 需求点) 分组
    grouped = defaultdict(list)
    for row in all_testcases:
        key = (row["module"], row["requirement"])
        grouped[key].append(row)

    # 重新编号 index
    final_rows = []
    for idx, row in enumerate(all_testcases, 1):
        row["index"] = idx
        final_rows.append(row)

    table_parser = TableParser(TestcaseTableModel, value_only=True)
    md_content = table_parser.to_markdown(final_rows)
    md_lines = md_content.splitlines()
    if len(md_lines) >= 2:
        md_lines[0] = "| 序号 | 模块名称 | 需求点 | 用例测试点 | 前提与约束 | 操作步骤及输入数据 | 预期结果 |"
        md_content = "\n".join(md_lines)
    with open("output/testcase.md", "w", encoding="utf-8") as f:
        f.write(md_content)
