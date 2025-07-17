import pytest
from pydantic import BaseModel
from template_parser.table_parser import TableParser, RowModel, TableModel

import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = "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"
os.environ["LANGCHAIN_PROJECT"] = "default"
from ENV import deep_seek_url, deep_seek_api_key, deep_seek_default_model
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    base_url=deep_seek_url,
    api_key=deep_seek_api_key,
    model=deep_seek_default_model,
    temperature=0.3
)

@pytest.mark.parametrize("value_only,prompt_suffix,check", [
    (False, "\n请输出一组表格数据。", lambda r, parser: r["success"] and r["data"]["table"][parser.table_field][0]["foo"]),
    (True, "\n请输出一组表格数据（仅值格式）。", lambda r, parser: r["success"] and r["data"]["table"][parser.table_field][0]["foo"]),
    (True, "\n请输出foo为test，num为999的内容（仅值格式）。", lambda r, parser: r["success"] and r["data"]["table"][parser.table_field][0]["foo"] == "test" and r["data"]["table"][parser.table_field][0]["num"] == 999),
])
def test_llm_table_parse(value_only, prompt_suffix, check):
    parser = TableParser(TableModel, value_only=value_only)
    instructions = parser.get_format_instructions()
    prompt = instructions + prompt_suffix
    response = llm.invoke(prompt)
    llm_output = response.content
    print("LLM输出：", llm_output)
    result = parser.parse(llm_output)
    print("解析结果：", result)
    assert check(result, parser)

def test_llm_table_extra_fields():
    parser = TableParser(TableModel)
    instructions = parser.get_format_instructions()
    prompt = instructions + "\n请输出表格内容并多加一个字段extra。"
    response = llm.invoke(prompt)
    llm_output = response.content
    result = parser.parse(llm_output)
    print("多字段解析结果：", result)
    assert result["success"]
    assert parser.table_field in result["data"]["table"]

def test_llm_table_special_characters():
    parser = TableParser(TableModel)
    instructions = parser.get_format_instructions()
    prompt = instructions + "\n请输出foo字段为特殊字符的表格内容。"
    response = llm.invoke(prompt)
    llm_output = response.content
    result = parser.parse(llm_output)
    print("特殊字符解析结果：", result)
    assert result["success"]
    assert parser.table_field in result["data"]["table"]

def test_llm_table_value_only_special_characters():
    parser = TableParser(TableModel, value_only=True)
    instructions = parser.get_format_instructions()
    prompt = instructions + "\n请输出foo字段为特殊字符的表格内容（仅值格式）。"
    response = llm.invoke(prompt)
    llm_output = response.content
    result = parser.parse(llm_output)
    print("特殊字符解析结果：", result)
    assert result["success"]
    assert parser.table_field in result["data"]['table']

def test_llm_table_empty():
    parser = TableParser(TableModel)
    instructions = parser.get_format_instructions()
    prompt = instructions + "\n请输出一个空表格。"
    response = llm.invoke(prompt)
    llm_output = response.content
    result = parser.parse(llm_output)
    print("空表格解析结果：", result)
    assert result["success"]
    assert result["data"]["table"][parser.table_field] == []



def test_llm_table_nested_dict():
    class ComplexRowModel(BaseModel):
        foo: str
        num: int
        meta: dict

    class ComplexTableModel(BaseModel):
        rows: list[ComplexRowModel]

    parser = TableParser(ComplexTableModel)
    instructions = parser.get_format_instructions()
    prompt = instructions + "\n请输出包含meta字段（为字典）的表格内容。"
    response = llm.invoke(prompt)
    llm_output = response.content
    result = parser.parse(llm_output)
    print("嵌套dict解析结果：", result)
    assert result["success"]
    assert "meta" in result["data"]["table"][parser.table_field][0]

def test_llm_table_large_rows():
    parser = TableParser(TableModel)
    instructions = parser.get_format_instructions()
    prompt = instructions + "\n请输出10行以上的表格内容。"
    response = llm.invoke(prompt)
    llm_output = response.content
    result = parser.parse(llm_output)
    print("大量行解析结果：", result)
    assert result["success"]
    assert len(result["data"]["table"][parser.table_field]) >= 10



def test_llm_table_mixed_types():
    parser = TableParser(TableModel)
    instructions = parser.get_format_instructions()
    prompt = instructions + "\n请输出num字段有字符串和数字混合的表格内容。"
    response = llm.invoke(prompt)
    llm_output = response.content
    result = parser.parse(llm_output)
    print("混合类型解析结果：", result)
    # 这里可以根据你的解析容错策略断言 success 或 fail