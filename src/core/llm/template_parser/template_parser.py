import re
import json
from typing import List, Dict, Any
from pydantic import create_model, ValidationError, constr, BaseModel
from pydantic.json_schema import JsonSchemaValue
from jsonschema import validate as jsonschema_validate, ValidationError as JsonSchemaError

# 示例 pydantic 子模型
class MyModel(BaseModel):
    foo: str
    num: str

class TemplateParser:
    def __init__(self, template, model_map=None):
        self.template = template
        self.model_map = model_map or {}
        self.fields, self.segments = self.parse_template(template, model_map)
        self.DynamicModel = create_model('DynamicModel', **self.fields)

    @staticmethod
    def parse_template(template, model_map=None):
        pattern = r"\{(\w+):(\w+(\[[^\]]+\])?)(:regex=([^\}:]+))?(?::(\w+))?\}"
        fields = {}
        segments = []
        last_end = 0
        type_map = {
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "list[str]": List[str],
            "list[int]": List[int],
            "dict": dict,
            "json": Any,
            "any": Any,
        }
        for m in re.finditer(pattern, template):
            name, typ, _, _, regex, model_name = m.groups()
            segments.append(template[last_end:m.start()])
            last_end = m.end()
            if typ == "str" and regex:
                fields[name] = (constr(pattern=regex), ...)
            elif typ == "json" and model_name and model_map and model_name in model_map:
                fields[name] = (model_map[model_name], ...)
            elif typ in type_map:
                fields[name] = (type_map[typ], ...)
            else:
                fields[name] = (str, ...)
        segments.append(template[last_end:])
        return fields, segments

    def locate_template_segment(self, llm_output):
        start_str = self.segments[0]
        end_str = self.segments[-1]
        start_idx = llm_output.find(start_str)
        if start_idx == -1:
            raise ValueError(f"输出中未找到模板起始标识 '{start_str}'")
        if end_str:
            end_idx = llm_output.rfind(end_str, start_idx)
            if end_idx == -1:
                raise ValueError(f"输出中未找到模板结尾标识 '{end_str}'")
            return llm_output[start_idx:end_idx + len(end_str)]
        else:
            return llm_output[start_idx:]

    def strict_parse_llm_output(self, matched_output):
        result = {}
        idx = 0
        for i, name in enumerate(self.fields.keys()):
            seg_start = self.segments[i]
            seg_end = self.segments[i+1]
            typ = self.fields[name][0]
            if seg_start:
                if not matched_output.startswith(seg_start, idx):
                    raise ValueError(f"输出格式错误，期望 '{seg_start}'")
                idx += len(seg_start)
            else:
                # seg_start 为空时，根据类型自动定位
                if typ == int:
                    m = re.search(r"\d+", matched_output[idx:])
                    if m:
                        idx += m.start()
                    else:
                        raise ValueError(f"未找到字段 {name} 的整数值")
                elif typ == float:
                    m = re.search(r"\d+(\.\d+)?", matched_output[idx:])
                    if m:
                        idx += m.start()
                    else:
                        raise ValueError(f"未找到字段 {name} 的浮点值")
                elif typ == bool:
                    m = re.search(r"(true|false|True|False|1|0)", matched_output[idx:])
                    if m:
                        idx += m.start()
                    else:
                        raise ValueError(f"未找到字段 {name} 的布尔值")
                elif typ in [List[str], List[int]]:
                    m = re.search(r"\[.*?\]", matched_output[idx:])
                    if m:
                        idx += m.start()
                    else:
                        raise ValueError(f"未找到字段 {name} 的列表值")
                elif typ == dict or typ == Any or (isinstance(typ, type) and issubclass(typ, BaseModel)):
                    m = re.search(r"\{.*\}", matched_output[idx:], re.DOTALL)
                    if m:
                        idx += m.start()
                    else:
                        raise ValueError(f"未找到字段 {name} 的 JSON/dict 值")

            if seg_end:
                remain = matched_output[idx:]
                # 优先处理复杂类型
                if (typ == dict or typ == Any or (isinstance(typ, type) and issubclass(typ, BaseModel))) and remain.startswith("{"):
                    count = 0
                    for i, c in enumerate(remain):
                        if c == "{":
                            count += 1
                        elif c == "}":
                            count -= 1
                            if count == 0:
                                value = remain[:i+1].strip()
                                idx += i+1
                                break
                    else:
                        # 没有闭合，退回分割符处理
                        next_pos = remain.find(seg_end)
                        if next_pos == -1:
                            raise ValueError(f"输出格式错误，缺少 '{seg_end}'")
                        value = remain[:next_pos].strip()
                        idx += next_pos
                elif typ in [List[str], List[int]] and remain.startswith("["):
                    count = 0
                    for i, c in enumerate(remain):
                        if c == "[":
                            count += 1
                        elif c == "]":
                            count -= 1
                            if count == 0:
                                value = remain[:i+1].strip()
                                idx += i+1
                                break
                    else:
                        next_pos = remain.find(seg_end)
                        if next_pos == -1:
                            raise ValueError(f"输出格式错误，缺少 '{seg_end}'")
                        value = remain[:next_pos].strip()
                        idx += next_pos
                else:
                    # 统一用分割符处理
                    next_pos = remain.find(seg_end)
                    if next_pos == -1:
                        raise ValueError(f"输出格式错误，缺少 '{seg_end}'")
                    value = remain[:next_pos].strip()
                    idx += next_pos
            else:
                # 自动识别类型结尾
                remain = matched_output[idx:]
                if typ == int:
                    m = re.match(r"^(\d+)", remain)
                    if m:
                        value = m.group(1)
                        idx += len(value)
                    else:
                        raise ValueError(f"结尾字段 {name} 不是合法整数")
                elif typ == float:
                    m = re.match(r"^(\d+(\.\d+)?)", remain)
                    if m:
                        value = m.group(1)
                        idx += len(value)
                    else:
                        raise ValueError(f"结尾字段 {name} 不是合法浮点数")
                elif typ == bool:
                    m = re.match(r"^(true|false|True|False|1|0)", remain)
                    if m:
                        value = m.group(1)
                        idx += len(value)
                    else:
                        value = remain.strip()
                        idx = len(matched_output)
                elif typ in [List[str], List[int]]:
                    # 匹配列表内容，遇到第一个闭合方括号
                    m = re.match(r"^(\[.*?\])", remain)
                    if m:
                        value = m.group(1)
                        idx += len(value)
                    else:
                        raise ValueError(f"结尾字段 {name} 不是合法列表")
                elif typ == dict or typ == Any or (isinstance(typ, type) and issubclass(typ, BaseModel)):
                    # 用括号计数法提取完整 JSON
                    remain = matched_output[idx:]
                    if remain.startswith("{"):
                        count = 0
                        for i, c in enumerate(remain):
                            if c == "{":
                                count += 1
                            elif c == "}":
                                count -= 1
                                if count == 0:
                                    value = remain[:i+1]
                                    idx += i+1
                                    break
                        else:
                            # 没有闭合
                            value = remain.strip()
                            idx = len(matched_output)
                else:
                    # 默认取剩余内容
                    value = remain.strip()
                    idx = len(matched_output)
            result[name] = value
        # 自动类型转换和嵌套模型校验
        for name, field in self.fields.items():
            typ = field[0]
            val = result[name]
            if isinstance(typ, type) and issubclass(typ, BaseModel):
                try:
                    json_obj = json.loads(val)
                    # 严格用 jsonschema 校验
                    schema: JsonSchemaValue = typ.model_json_schema()
                    jsonschema_validate(instance=json_obj, schema=schema)
                    result[name] = typ.model_validate(json_obj)
                except (JsonSchemaError, Exception) as e:
                    raise ValueError(f"字段 {name} 不符合 schema: {e}")
            elif typ == bool:
                if isinstance(val, str):
                    if val.lower() in ("true", "1"):
                        result[name] = True
                    elif val.lower() in ("false", "0"):
                        result[name] = False
            elif typ in [List[str], List[int], dict]:
                try:
                    result[name] = eval(val)
                except Exception:
                    pass
            elif typ == Any:
                try:
                    result[name] = json.loads(val)
                except Exception:
                    result[name] = val
        return result

    def validate(self, llm_output):
        try:
            matched_output = self.locate_template_segment(llm_output)
            data = self.strict_parse_llm_output(matched_output)
            validated = self.DynamicModel(**data)
            return {
                "success": True,
                "data": validated.model_dump(),
                "matched_output": matched_output
            }
        except (ValidationError, ValueError) as e:
            return {
                "success": False,
                "data": str(e),
                "matched_output": matched_output
            }

    def get_format_instructions(self):
        instructions = (
            "请严格按照如下格式输出：\n"
            "变量值需替换模板中的变量定义部分（如 {name:str}），其他内容保持所有字符完全一致，包括所有标点符号及其中英文差别\n"
            "例如：\"姓名={name:str}，年龄={age:int}。\"替换为\"姓名=张三，年龄=18。\"\n"
            "如遇 json 类型变量，请直接嵌入合法 JSON，特殊字符需正确转义，且需符合指定 schema。\n\n"
            "模板如下：\n"
            f"{self.template}\n\n"
            "输出的格式示例如下\n"
        )
        example = self.template
        example_values = {
            "int": "42",
            "float": "3.14",
            "str": "示例内容",
            "bool": "true",
            "list[str]": "[\"A\", \"B\"]",
            "list[int]": "[1, 2]",
            "dict": "{\"key\": \"value\"}",
            "json": "{\"foo\": \"bar\", \"num\": 1}",
            "any": "{\"foo\": \"bar\"}"
        }
        for name, field in self.fields.items():
            typ = field[0]
            typ_str = getattr(typ, "__name__", str(typ))
            if isinstance(typ, type) and issubclass(typ, BaseModel):
                # 自动生成示例值
                fields = list(typ.model_fields.keys())
                value_dict = {f: f"示例值" for f in fields}
                value = json.dumps(value_dict, ensure_ascii=False)
            elif typ_str == "list":
                if typ.__args__[0] == str:
                    value = example_values["list[str]"]
                elif typ.__args__[0] == int:
                    value = example_values["list[int]"]
                else:
                    value = "[...]"
            elif typ_str == "dict":
                value = example_values["dict"]
            elif typ == Any:
                value = example_values["json"]
            elif typ_str in example_values:
                value = example_values[typ_str]
            else:
                value = "示例内容"
            example = re.sub(rf"\{{{name}:[^\}}]+\}}", value, example)
        instructions +=  example 
        if self.model_map:
            instructions += "\n所有可用 json 类型变量的 schema 如下：\n"
            for model_name, model_cls in self.model_map.items():
                if issubclass(model_cls, BaseModel):
                    schema = model_cls.model_json_schema()
                    instructions += f"{model_name} 的 schema:\n{json.dumps(schema, ensure_ascii=False)}\n"
        return instructions



if __name__ == "__main__":
    class ListDictModel(BaseModel):
            items: list
            config: dict
    template = "数据={data:json:ListDictModel}"
    # template = "模型={model:json:MyModel}"
    # llm_output = '模型={"foo": "hello", "num": "123"}。'
    # llm_output = '数据={"items": [1, 2, 3], "config": {"a": 1, "b": 2}}'
    llm_output = '姓名=张三，年龄=18，模型={"foo": "bar", "num": "1"}， 激活=true'
    template = "姓名={name:str}，年龄={age:int}，模型={model:json:MyModel}，激活={active:bool}"
    parser = TemplateParser(template, model_map={"MyModel": MyModel})
    # validator = TemplateParser(template, model_map={"ListDictModel": ListDictModel})
    print(parser.get_format_instructions())
    result = parser.validate(llm_output)
    print(result)