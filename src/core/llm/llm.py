from src.ENV import llm_url, llm_api_key, llm_default_model
from langchain_openai import ChatOpenAI
from .rag import get_embedding, search_knowledge_base, build_multi_file_knowledge_base
from .template_parser.template_parser import TemplateParser, MyModel
from .template_parser.table_parser import TableModel, TableParser
from langchain_core.callbacks import BaseCallbackHandler

class CustomCallbackHandler(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs):
        print("\n====== LLM 开始 ======")
        print(f"提示词：{prompts}")

    def on_llm_end(self, response, **kwargs):
        print("\n====== LLM 结束 ======")
        print(f"输出：{response.generations}")

class LLM:
    def __init__(self, model=None, temperature=0.3, history_len=0, logger=False):
        self.llm = ChatOpenAI(
            base_url=llm_url,
            api_key=llm_api_key,
            model=model or llm_default_model,
            temperature=temperature
        )
        self.file_list = None
        self.history = []
        self.history_len = history_len
        self.logger = logger

    def build_knowledge_base(self, file_list, persist_dir="rag_chroma_db", collection_name="rag_demo", max_len=1000, overlap=100):
        self.file_list = file_list
        collection = build_multi_file_knowledge_base(
            file_list, persist_dir=persist_dir, collection_name=collection_name, max_len=max_len, overlap=overlap
        )
        return collection

    def _build_prompt(self, prompt, docs=None, parser=None):
        history_text = ""
        if self.history_len > 0:
            for item in self.history[-self.history_len:]:
                history_text += f"user: {item['prompt']}\nassistant: {item['response']}\n"

        if docs:
            context = "\n\n".join(
                doc["content"] if isinstance(doc, dict) and "content" in doc else doc for doc in docs
            )
            full_prompt = (
                history_text 
                + "\nuser: " 
                + f"你是知识库问答助手。请根据以下知识内容回答用户问题。\n\n知识内容：\n{context}\n\n用户问题：{prompt}\n\n请简明回答："
            )
        else:
            full_prompt = history_text + "user: " + prompt

        # 仅使用外部传入的 parser
        if parser:
            format_instructions = parser.get_format_instructions()
            full_prompt += "\n\n" + format_instructions

        return full_prompt

    def _invoke_llm(self, full_prompt, **kwargs):
        if self.logger:
            result = self.llm.invoke(full_prompt, **kwargs, config={"callbacks": [CustomCallbackHandler()]})
        else:
            result = self.llm.invoke(full_prompt, **kwargs)

        if hasattr(result, "content"):
            content = result.content
        elif isinstance(result, dict) and "content" in result:
            content = result["content"]
        else:
            content = str(result)
        return content

    def _parse_template_output(self, parser, content, full_prompt=None, max_retry=5, **kwargs):
        if parser:
            parsed = parser.validate(content)
            retry_count = 0
            last_content = content
            while isinstance(parsed, dict) and not parsed.get("success", True) and retry_count < max_retry:
                retry_count += 1
                # 重新生成
                last_content = self._invoke_llm(full_prompt, **kwargs)
                parsed = parser.validate(last_content)
            return parsed
        else:
            return content

    def call(self, prompt, docs=None, parser=None, max_retry=2, **kwargs):
        """
        通用问答接口。
        - prompt: 用户问题
        - docs: 可选，知识块列表。传入则自动拼接为RAG问答，否则普通对话。
        - template: 可选，结构化输出模板字符串。指定则用TemplateParser解析输出，并用格式指导。
        - model_map: 可选，模板变量对应的pydantic模型字典。
        - max_retry: 模板解析失败时最大重试次数
        """
        full_prompt = self._build_prompt(prompt, docs, parser)
        content = self._invoke_llm(full_prompt, **kwargs)
        self.history.append({"prompt": prompt, "response": content})
        return self._parse_template_output(parser, content, full_prompt=full_prompt, max_retry=max_retry, **kwargs)

    def get_embedding(self, text):
        return get_embedding(text)

    def search_knowledge(self, query, top_k=5, meta_filter=None, persist_dir="rag_chroma_db", collection_name="rag_demo"):
        return search_knowledge_base(query, persist_dir=persist_dir, collection_name=collection_name, top_k=top_k, meta_filter=meta_filter)

    def get_history(self):
        return self.history

# 用法示例
if __name__ == "__main__":
    llm = LLM()

    """模型调用示例"""
    answer = llm.call("你是谁")
    print(answer)

    """知识库使用示例"""
    file_list = [
        {"file_path":"data/需求文件/需求分析报告-湖北中烟新型烟草产品调研与开发信息反馈系统项目.docx", "type":"需求文档"},
        {"file_path":"data/需求文件/湖北中烟工程中心数字管理应用用户操作手册v1.0.docx", "type":"用户手册"},
        {"file_path":"data/需求文件/数字信息化管理应用系统接口文档.docx", "type":"技术文档"}
    ]
    llm.build_knowledge_base(file_list)
    query = "请简要介绍用户手册的主要内容。"
    docs = llm.search_knowledge(query, collection_name="rag_demo")
    print("\n【检索到的知识块】")
    for i, doc in enumerate(docs):
        print(f"Top{i+1}:\n{doc}\n------")
    answer = llm.call(query, docs=docs)
    print("\n【RAG答案】\n", answer)

    
    """结构化输出示例"""
    template = "姓名={name:str}，年龄={age:int}，模型={model:json:MyModel}，激活={active:bool}"
    parser = TemplateParser(template, model_map={"MyModel": MyModel})
    query = "请输出一个用户信息示例"
    result = llm.call(query, parser=parser)
    print("\n【结构化解析】\n", result)


    """表格结构化解析示例"""
    table_query = "请输出10行以上的表格内容。"
    table_parser = TableParser(TableModel, value_only=True)
    table_result = llm.call(table_query, parser=table_parser)
    print("\n【表格解析】\n", table_result)
    rows = table_result['data']['table']['rows']
    print("\ntsv格式输出：")
    print(table_parser.to_tsv(rows))
    print("\ncsv格式输出：")
    print(table_parser.to_csv(rows))
    print("\nmarkdown格式输出：")
    print(table_parser.to_markdown(rows))
    print("\njson格式输出：")
    print(table_parser.to_json(rows))


