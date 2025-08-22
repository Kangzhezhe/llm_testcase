"""
MCP完整演示脚本
展示如何使用MCP服务器和客户端
"""
import asyncio
import json
import time
from pathlib import Path
import sys

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.simple_mcp import (
    MCPLLMServer, 
    MCPLLMClient, 
    MCPClientManager,
    MCPConfig,
    MCPServerLauncher,
    create_default_tools
)
from src.core.llm.llm import LLM

async def demo_basic_mcp():
    """基础MCP功能演示"""
    print("=== 基础MCP功能演示 ===\n")
    
    # 1. 创建配置
    print("1. 创建MCP配置...")
    config = MCPConfig("demo_config.json")
    
    # 添加示例知识库配置
    file_list = [
        {"file_path": "data/网易云音乐PRD.md", "type": "产品文档"},
        {"file_path": "data/testcase.md", "type": "测试用例"}
    ]
    config.add_knowledge_base("demo_kb", file_list, max_len=1000, overlap=100)
    
    print("   配置创建完成")
    
    # 2. 创建服务器
    print("2. 创建MCP服务器...")
    launcher = MCPServerLauncher(config)
    launcher.register_custom_tools()
    
    # 创建LLM实例
    llm = LLM()
    
    # 尝试构建知识库
    try:
        llm.build_knowledge_base(file_list, collection_name="demo_kb")
        print("   知识库构建成功")
    except Exception as e:
        print(f"   知识库构建失败: {e}")
    
    # 创建服务器实例
    server = MCPLLMServer(llm)
    
    # 注册额外的自定义工具
    def fibonacci(n: int) -> int:
        """计算斐波那契数列"""
        if n <= 1:
            return n
        return fibonacci(n-1) + fibonacci(n-2)
    
    def word_count(text: str) -> dict:
        """统计文本信息"""
        return {
            "characters": len(text),
            "words": len(text.split()),
            "lines": len(text.split('\n'))
        }
    
    server.register_tool("fibonacci", fibonacci, "计算斐波那契数列")
    server.register_tool("word_count", word_count, "统计文本字符、单词和行数")
    
    print("   服务器创建完成")
    
    # 3. 测试工具注册
    print("3. 测试工具注册...")
    print(f"   已注册工具: {list(server.tools.keys())}")
    
    # 4. 模拟MCP交互
    print("4. 模拟MCP交互...")
    
    # 模拟列出工具
    tools = []
    for tool_name, tool_info in server.tools.items():
        param_schema = tool_info["param_model"].model_json_schema() if hasattr(tool_info["param_model"], 'model_json_schema') else {}
        tools.append({
            "name": tool_name,
            "description": tool_info["description"],
            "schema": param_schema
        })
    
    print("   可用工具:")
    for tool in tools:
        print(f"     - {tool['name']}: {tool['description']}")
    
    # 模拟工具调用
    print("\n   测试工具调用:")
    
    # 测试数学运算
    try:
        add_result = server.tools["add"]["func"](3.14, 2.86)
        print(f"     add(3.14, 2.86) = {add_result}")
    except Exception as e:
        print(f"     add 调用失败: {e}")
    
    # 测试斐波那契
    try:
        fib_result = server.tools["fibonacci"]["func"](10)
        print(f"     fibonacci(10) = {fib_result}")
    except Exception as e:
        print(f"     fibonacci 调用失败: {e}")
    
    # 测试文本统计
    try:
        wc_result = server.tools["word_count"]["func"]("Hello world!\nThis is a test.")
        print(f"     word_count result = {wc_result}")
    except Exception as e:
        print(f"     word_count 调用失败: {e}")
    
    print("\n基础功能演示完成！")

async def demo_llm_integration():
    """LLM集成演示"""
    print("\n=== LLM集成演示 ===\n")
    
    # 创建LLM实例
    llm = LLM()
    
    # 1. 普通对话测试
    print("1. 普通对话测试...")
    try:
        response = llm.call("你好，请介绍一下你自己")
        print(f"   LLM回复: {response}")
    except Exception as e:
        print(f"   对话失败: {e}")
    
    # 2. 工具调用测试
    print("\n2. 工具调用测试...")
    from src.core.llm.tool_call import LLMToolCaller
    
    def calculator(a: float, b: float, operation: str = "add") -> float:
        """多功能计算器"""
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            return a / b if b != 0 else 0
        else:
            return 0
    
    caller = LLMToolCaller([calculator])
    
    try:
        result = llm.call("请帮我计算 15 乘以 8", caller=caller)
        print(f"   计算结果: {result}")
    except Exception as e:
        print(f"   工具调用失败: {e}")
    
    # 3. 结构化输出测试
    print("\n3. 结构化输出测试...")
    from src.core.llm.template_parser.template_parser import TemplateParser
    
    template = "结果={result:float}说明={explanation:str}置信度={confidence:float}"
    parser = TemplateParser(template)
    
    try:
        result = llm.call("请计算圆周率乘以3的结果", parser=parser)
        print(f"   结构化结果: {result}")
    except Exception as e:
        print(f"   结构化输出失败: {e}")
    
    print("\nLLM集成演示完成！")

async def demo_performance_test():
    """性能测试演示"""
    print("\n=== 性能测试演示 ===\n")
    
    llm = LLM()
    
    # 1. 响应时间测试
    print("1. 响应时间测试...")
    
    test_queries = [
        "1+1等于多少？",
        "请用一句话介绍人工智能",
        "什么是机器学习？",
        "解释一下深度学习的概念"
    ]
    
    total_time = 0
    for i, query in enumerate(test_queries, 1):
        start_time = time.time()
        try:
            response = llm.call(query)
            end_time = time.time()
            elapsed = end_time - start_time
            total_time += elapsed
            print(f"   查询{i}: {elapsed:.2f}秒 - {query[:20]}...")
        except Exception as e:
            print(f"   查询{i}失败: {e}")
    
    avg_time = total_time / len(test_queries) if test_queries else 0
    print(f"   平均响应时间: {avg_time:.2f}秒")
    
    # 2. 并发测试（简化版）
    print("\n2. 简单并发测试...")
    
    async def single_query(query_id, query):
        start_time = time.time()
        try:
            # 注意：这里使用同步的llm.call，在实际应用中可能需要异步版本
            response = llm.call(f"简短回答: {query}")
            end_time = time.time()
            return {"id": query_id, "time": end_time - start_time, "success": True}
        except Exception as e:
            end_time = time.time()
            return {"id": query_id, "time": end_time - start_time, "success": False, "error": str(e)}
    
    concurrent_queries = [
        "什么是Python？",
        "解释变量的概念",
        "什么是函数？"
    ]
    
    # 由于LLM.call是同步的，这里只是演示结构
    results = []
    for i, query in enumerate(concurrent_queries):
        result = await single_query(i, query)
        results.append(result)
    
    success_count = sum(1 for r in results if r["success"])
    avg_concurrent_time = sum(r["time"] for r in results) / len(results)
    
    print(f"   并发查询成功率: {success_count}/{len(results)}")
    print(f"   平均并发响应时间: {avg_concurrent_time:.2f}秒")
    
    print("\n性能测试演示完成！")

async def demo_error_handling():
    """错误处理演示"""
    print("\n=== 错误处理演示 ===\n")
    
    llm = LLM()
    
    # 1. 工具调用错误
    print("1. 工具调用错误处理...")
    
    def divide_by_zero(a: float, b: float) -> float:
        """可能出错的除法"""
        return a / b  # 当b=0时会出错
    
    from src.core.llm.tool_call import LLMToolCaller
    caller = LLMToolCaller([divide_by_zero])
    
    try:
        result = llm.call("请计算 10 除以 0", caller=caller)
        print(f"   结果: {result}")
    except Exception as e:
        print(f"   捕获错误: {e}")
    
    # 2. 解析错误
    print("\n2. 结构化解析错误处理...")
    
    from src.core.llm.template_parser.template_parser import TemplateParser
    
    # 使用复杂模板测试解析错误
    complex_template = "数字={number:int}，列表={items:json:list}，对象={data:json:dict}"
    parser = TemplateParser(complex_template)
    
    try:
        result = llm.call("请随便说点什么", parser=parser, max_retry=1)
        print(f"   解析结果: {result}")
    except Exception as e:
        print(f"   解析错误: {e}")
    

async def main():
    """主演示函数"""
    print("🚀 MCP (Model Context Protocol) 完整演示")
    print("=" * 50)
    
    try:
        # 运行各个演示
        await demo_basic_mcp()
        await demo_llm_integration()
        await demo_performance_test()
        await demo_error_handling()
        
        print("\n" + "=" * 50)
        print("✅ 所有演示完成！")
        
        print("\n📝 使用说明:")
        print("1. 启动MCP服务器: python -m src.core.mcp.cli server")
        print("2. 运行客户端演示: python -m src.core.mcp.cli client --demo")
        print("3. 交互式客户端: python -m src.core.mcp.cli client --interactive")
        print("4. 创建配置文件: python -m src.core.mcp.cli config create --example")
        
    except KeyboardInterrupt:
        print("\n\n❌ 演示被用户中断")
    except Exception as e:
        print(f"\n\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
