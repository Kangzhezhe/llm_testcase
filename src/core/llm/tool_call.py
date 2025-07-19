import inspect
import json
from openai import OpenAI
from src.ENV import llm_url, llm_api_key, llm_default_model
from src.core.llm.template_parser.template_parser import TemplateParser
from pydantic import BaseModel, create_model

tool_registry = {}

def infer_param_model(func):
    """
    根据函数签名自动生成pydantic参数模型
    """
    sig = inspect.signature(func)
    fields = {}
    for name, param in sig.parameters.items():
        ann = param.annotation if param.annotation != inspect.Parameter.empty else str
        fields[name] = (ann, ...)
    model = create_model(f"{func.__name__.capitalize()}Params", **fields)
    return model

def register_tool(name=None):
    """
    装饰器注册工具函数，自动推导参数模型
    """
    def decorator(func):
        tool_name = name or func.__name__
        param_model = infer_param_model(func)
        tool_registry[tool_name] = {"func": func, "param_model": param_model}
        return func
    return decorator

def call_tool(name, args):
    if name not in tool_registry:
        raise ValueError(f"未注册的工具: {name}")
    func = tool_registry[name]["func"]
    param_model = tool_registry[name]["param_model"]
    params = param_model(**args)
    return func(**params.model_dump())



def call_llm(prompt):
    client = OpenAI(
        api_key=llm_api_key,
        base_url=llm_url
    )
    resp = client.chat.completions.create(
        model=llm_default_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    if hasattr(resp, "choices"):
        return resp.choices[0].message.content
    return str(resp)



def build_tool_template(tool_names, param_models):
    """
    构建通用tool_call模板，工具名为{name:str}，参数为所有工具的联合
    直接用参数模型Model构建template，语法使用 {args:json:Model}
    """
    args_examples = []
    for tool_name, param_model in param_models.items():
        # 用Model名展示参数结构
        args_examples.append(
            f'如果name为"{tool_name}"，args为: {{args:json:{param_model.__name__}}}'
        )
    # template中用{args:json:Model}表示参数结构
    template = '{"tool_call": {"name": {name:str}, "args": {args:json:对应工具参数Model}}}'
    example = '\n'.join(args_examples)
    return template, example

def get_tool_format_instructions():
    param_models = {name: info["param_model"] for name, info in tool_registry.items()}
    template, example = build_tool_template(list(param_models.keys()), param_models)
    # 构建 model_map，key 为模型名，value 为模型类
    model_map = {model.__name__: model for model in param_models.values()}
    parser = TemplateParser(template, model_map=model_map)
    instructions = (
        "[以下是工具调用格式的说明]\n"
        + "注意：如果没有任何一个工具能满足你的需求，请直接回复原始内容，不要调用 tool_call, 忽略以下内容，不要在回答中提到工具这件事。\n"
        + parser.get_format_instructions()
        + "\n不同工具的args示例：\n" + example
    )
    return instructions, parser, param_models

def handle_tool_call_auto(content, param_models, parser):
    """
    自动识别tool_call中的工具名并分发（用parser解析）
    """
    try:
        parsed = parser.validate(content)
        if not parsed.get('success', False):
            return None, None
        data = parsed["data"]
        tool_name = data.get("name")
        # 去除引号
        if isinstance(tool_name, str) and tool_name.startswith('"') and tool_name.endswith('"'):
            tool_name = tool_name[1:-1]
        if tool_name in param_models:
            param_model = param_models[tool_name]
            tool_args = data.get("args", {})
            # 如果 args 是字符串，转为 dict
            if isinstance(tool_args, str):
                tool_args = json.loads(tool_args)
            # 用参数模型校验和转换
            params = param_model(**tool_args)
            return tool_name, call_tool(tool_name, params.model_dump())
    except Exception as e:
        print("tool_call解析失败:", e)
    return None, None



# 示例工具函数（无需手动定义参数模型）
@register_tool("add")
def add(a: float, b: float):
    return a + b

@register_tool("echo")
def echo(text: str):
    return f"你说的是: {text}"

@register_tool("multiply")
def multiply(x: float, y: float):
    return x * y

def main():
    print("=== Tool Call Demo（工具自动选择，name为参数）===")
    print("可用工具：", list(tool_registry.keys()))
    format_instructions, parser, param_models = get_tool_format_instructions()
    print("\n【格式化指令】\n", format_instructions)
    while True:
        user_input = input("用户问题: ").strip()
        if user_input.lower() == "exit":
            break
        prompt = user_input + "\n\n" + format_instructions
        llm_output = call_llm(prompt)
        print("大模型回复:", llm_output)
        tool_name, tool_result = handle_tool_call_auto(llm_output, param_models, parser)
        if tool_result is not None:
            print(f"本地工具调用结果（{tool_name}）:", tool_result)
            print("最终回复:", tool_result)
        else:
            print("最终回复:", llm_output)

if __name__ == "__main__":
    main()
