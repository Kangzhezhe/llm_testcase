import os
import time
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = "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"
os.environ["LANGCHAIN_PROJECT"] = "default"
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.callbacks import BaseCallbackHandler

# 从 ENV.py 导入
from ENV import deep_seek_url, deep_seek_api_key, deep_seek_default_model

class CustomCallbackHandler(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs):
        print("\n====== LLM 开始 ======")
        print(f"提示词：{prompts}")

    def on_llm_end(self, response, **kwargs):
        print("\n====== LLM 结束 ======")
        print(f"输出：{response.generations}")

# 配置 LLM
llm = ChatOpenAI(
    base_url=deep_seek_url,
    api_key=deep_seek_api_key,
    model=deep_seek_default_model,
    temperature=0.3
)

# 提示词模板
extract_prompt = ChatPromptTemplate.from_template(
    """
你是专业的需求分析师。

请从以下文档中，提取所有模块名称及对应的需求点。

**需求的定义**：
- 功能需求：描述系统必须执行的功能或服务。例如：用户可以上传图片、支持搜索歌曲、系统自动生成推荐等。
- 非功能需求：描述系统的性能、效率、安全、兼容性等方面的要求。例如：系统在3秒内响应、支持10万并发用户、界面符合公司UI规范等。
- 不要提取以下内容：
  - 背景、市场分析、行业介绍
  - 竞品信息、现状描述
  - UI视觉描述（除非直接体现功能）
  - 流程示意图、参考资料等

要求：
- 按 Markdown 表格输出
- 表头为：序号 | 模块 | 需求点
- 序号从1开始，每个需求点单独占一行，序号连续递增
- 不要回答多余的文字，只输出表格
- 仔细阅读整个文档，识别出明确表达软件功能、性能、约束等方面要求的语句。
- 排除与软件需求无关的信息，如背景介绍、市场分析等。
- 如果文档中没有需求点，请输出“未发现需求点”。
文档如下：
{document}
"""
)

# 构造链
extract_chain = extract_prompt | llm | StrOutputParser()

def extract_requirements(document: str):
    callbacks = [CustomCallbackHandler()]
    md_table = extract_chain.invoke({"document": document}, config={"callbacks": callbacks})
    return md_table

# 优化需求表的提示词
optimize_prompt = ChatPromptTemplate.from_template(
    """
你是专业的软件需求分析师。

以下是软件需求文档 ，以及从中提取的需求表 。

请执行以下任务：
1. 仔细比对 PRD 和需求表，判断：
   - 是否有遗漏需求（PRD里存在但表格没列出的需求点）
   - 是否存在不属于需求的冗余条目（如背景、市场分析、纯视觉描述等）
2. 如果有遗漏或冗余，请修改表格：
   - 增加遗漏的需求
   - 删除冗余的条目
   - 或对描述不准确的需求进行修正
3. 按以下格式输出最终结果：
   - 仅输出最终优化后的 Markdown 表格
   - 不要输出其他解释或文字

要求：
- Markdown 表格表头为：序号 | 模块 | 需求点
- 序号从 1 开始，每个需求点单独占一行
- 保证表格完整且准确

需求文档如下：{document}
下面是目前生成的需求表：{requirements}
"""
)


# 构造优化需求表的 Chain
optimize_chain = optimize_prompt | llm | StrOutputParser()

def optimize_requirements(document: str, requirements_md: str):
    callbacks = [CustomCallbackHandler()]
    optimized_md = optimize_chain.invoke(
        {
            "document": document,
            "requirements": requirements_md
        },
        config={"callbacks": callbacks}
    )
    return optimized_md



def main():

    document_path = "../data/中烟cutPRD.md"
    with open(document_path, "r", encoding="utf-8") as f:
        prd_content = f.read()

    md_table = extract_requirements(prd_content)

    with open("requirements.md", "w", encoding="utf-8") as f:
        f.write(md_table)

    print("\n初次提取完成，已写入 requirements.md")
    print(md_table)

    optimized_table = optimize_requirements(prd_content, md_table)

    with open("requirements_optimized.md", "w", encoding="utf-8") as f:
        f.write(optimized_table)

    print("\n优化完成，已写入 requirements_optimized.md")
    print(optimized_table)

if __name__ == "__main__":
    main()

 