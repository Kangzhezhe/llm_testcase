import json
import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = "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"
os.environ["LANGCHAIN_PROJECT"] = "default"

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_core.tracers import ConsoleCallbackHandler
from langchain_core.callbacks import BaseCallbackHandler
import time
from ENV import deep_seek_url, deep_seek_api_key, deep_seek_default_model
from md_to_txt import text_pieces


class CustomCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        self.start_time = None

    def on_chain_start(self, serialized, inputs, **kwargs):
        self.start_time = time.time()
        # print(f"链开始，输入：{inputs}")

    def on_llm_start(self, serialized, prompts, **kwargs):
        print("\n\n============================LLM 开始===================================================")
        print(f"LLM 开始，提示：{prompts}")

    def on_llm_end(self, response, **kwargs):
        print("\n\n============================LLM 结束===================================================")
        print(f"LLM 结束，输出：{response.generations}")

    def on_llm_error(self, error, **kwargs):
        print("\n\n===============================LLM 错误================================================")
        print(f"LLM 错误：{error}")

    def on_chain_end(self, outputs, **kwargs):
        elapsed_time = time.time() - self.start_time
        # print("\n\n==============================链结束==================================================")
        # print(f"链结束，输出：{outputs}，耗时：{elapsed_time:.2f}秒")



# 配置LLM
llm = ChatOpenAI(
    base_url=deep_seek_url,
    api_key=deep_seek_api_key,
    model=deep_seek_default_model,
    temperature=0.7
)

# 定义提示模板
summary_template = ChatPromptTemplate.from_template(
    "你是专业的需求分析师。分析以下需求文档，归纳业务模块摘要：\n{document}"
)

detail_template = ChatPromptTemplate.from_template(
    "你是专业的需求分析师。对以下摘要进行业务细化：\n{summary}"
)

flowchart_template = ChatPromptTemplate.from_template(
    "你是专业的流程分析师。根据以下内容生成mermaid流程图：\n摘要：{summary}\n细化：{detail}"
)

testcase_template = ChatPromptTemplate.from_template(
    "你是专业的测试工程师。根据以下流程图生成markdown格式测试用例：\n{flowchart}"
)

# 构建LCEL链式流程
summary_chain = summary_template | llm | StrOutputParser()
detail_chain = detail_template | llm | StrOutputParser()
flowchart_chain = flowchart_template | llm | StrOutputParser()
testcase_chain = testcase_template | llm | StrOutputParser()

def full_chain(document):
    callbacks = [CustomCallbackHandler()]
    # 步骤1：生成摘要
    summary = summary_chain.invoke({"document": document}, config={"callbacks": callbacks})
    # 步骤2：业务细化
    detail = detail_chain.invoke({"summary": summary}, config={"callbacks": callbacks})
    # 步骤3：生成流程图
    flowchart = flowchart_chain.invoke({"summary": summary, "detail": detail}, config={"callbacks": callbacks})
    # 步骤4：生成测试用例
    testcases = testcase_chain.invoke({"flowchart": flowchart}, config={"callbacks": callbacks})
    return {
        "summary": summary,
        "detail": detail,
        "flowchart": flowchart,
        "testcases": testcases
    }


def main():
    # 执行链式流程
    result = full_chain(text_pieces[0])
    
    # 保存结果
    with open("result.md", "w", encoding="utf-8") as f:
        f.write(result["testcases"])
    
    print("LCEL方式完成！结果保存到 result.md")
    print(result["testcases"])

if __name__ == "__main__":
    main()