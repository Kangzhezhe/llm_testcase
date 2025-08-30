"""
测试集成MCP支持的LLM类
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.llm.llm import LLM, create_llm_with_mcp
from src.core.llm.tool_call import LLMToolCaller

# 尝试导入MCP相关模块
try:
    from src.core.llm.mcp_client import MCPServerConfig, MCPTransportType, MCP_AVAILABLE
except ImportError:
    MCP_AVAILABLE = False


def test_traditional_tools():
    """测试传统工具调用"""
    print("=== 测试传统工具调用 ===")
    
    # 定义工具函数
    def add(a: float, b: float) -> float:
        """加法工具"""
        return a + b

    def multiply(a: float, b: float) -> float:
        """乘法工具"""
        return a * b

    def echo(text: str) -> str:
        """回声工具"""
        return f"回声: {text}"

    # 创建传统工具调用器
    traditional_caller = LLMToolCaller([add, multiply, echo])
    
    # 创建LLM实例
    llm = LLM()
    
    # 测试传统工具调用
    print("\n--- 测试加法 ---")
    result1 = llm.call("请帮我计算 3 + 5", caller=traditional_caller)
    print(f"结果: {result1}")
    
    print("\n--- 测试乘法 ---")
    result2 = llm.call("请帮我计算 4 × 6", caller=traditional_caller)
    print(f"结果: {result2}")
    
    print("\n--- 测试回声 ---")
    result3 = llm.call("请重复说 'Hello World'", caller=traditional_caller)
    print(f"结果: {result3}")


async def test_mcp_tools():
    """测试MCP工具调用"""
    if not MCP_AVAILABLE:
        print("=== MCP功能不可用，跳过测试 ===")
        return
    
    print("=== 测试MCP工具调用 ===")
    
    # 创建MCP配置
    mcp_configs = [
        MCPServerConfig(
            name="demo",
            command="python",
            args=["-m", "src.core.llm.demo_mcp_server"],
            transport=MCPTransportType.STDIO
        )
    ]
    
    # 创建支持MCP的LLM
    llm = create_llm_with_mcp(mcp_configs)
    
    try:
        # 初始化MCP连接
        print("初始化MCP连接...")
        await llm.init_mcp()
        
        # 获取可用工具
        tools = llm.get_available_tools("mcp")
        print(f"可用的MCP工具: {tools}")
        
        # 测试MCP工具调用
        print("\n--- 测试MCP计算工具 ---")
        result1 = await llm.call("请使用calculate工具计算 10 + 20", use_mcp=True)
        print(f"结果: {result1}")
        
        # print("\n--- 测试获取时间 ---")
        # result2 = llm.call("请获取当前时间", use_mcp=True)
        # print(f"结果: {result2}")
        
        # print("\n--- 测试回声消息 ---")
        # result3 = llm.call("请使用echo_message工具重复'MCP测试成功'", use_mcp=True)
        # print(f"结果: {result3}")
        
    except Exception as e:
        print(f"MCP测试出错: {e}")
    finally:
        # 清理MCP连接
        await llm.cleanup_mcp()


async def test_mixed_usage():
    """测试混合使用传统工具和MCP工具"""
    if not MCP_AVAILABLE:
        print("=== MCP功能不可用，跳过混合测试 ===")
        return
    
    print("=== 测试混合使用 ===")
    
    # 定义传统工具
    def add(a: float, b: float) -> float:
        return a + b
    
    traditional_caller = LLMToolCaller([add])
    
    # 创建MCP配置
    mcp_configs = [
        MCPServerConfig(
            name="demo",
            command="python",
            args=["-m", "src.core.llm.demo_mcp_server"],
            transport=MCPTransportType.STDIO
        )
    ]
    
    llm = LLM(mcp_configs=mcp_configs)
    
    try:
        await llm.init_mcp()
        
        print("\n--- 使用传统工具 ---")
        result1 = llm.call("请计算 5 + 3", caller=traditional_caller, use_mcp=False)
        print(f"传统工具结果: {result1}")
        
        print("\n--- 使用MCP工具 ---")
        result2 = llm.call("请获取当前时间", use_mcp=True)
        print(f"MCP工具结果: {result2}")
        
        print("\n--- 普通对话（不使用工具） ---")
        result3 = llm.call("你好，请介绍一下你自己")
        print(f"普通对话结果: {result3}")
        
    finally:
        await llm.cleanup_mcp()


def test_context_manager():
    """测试上下文管理器"""
    print("=== 测试上下文管理器 ===")
    
    def add(a: float, b: float) -> float:
        return a + b
    
    traditional_caller = LLMToolCaller([add])
    
    # 使用上下文管理器
    with LLM() as llm:
        result = llm.call("请计算 7 + 8", caller=traditional_caller)
        print(f"上下文管理器结果: {result}")


async def main():
    """主测试函数"""
    print("开始测试集成MCP支持的LLM类")
    print("=" * 50)
    
    # 测试传统工具
    test_traditional_tools()
    
    print("\n" + "=" * 50)
    
    # 测试MCP工具
    await test_mcp_tools()
    
    print("\n" + "=" * 50)
    
    # 测试混合使用
    await test_mixed_usage()
    
    print("\n" + "=" * 50)
    
    # 测试上下文管理器
    test_context_manager()
    
    print("\n" + "=" * 50)
    print("所有测试完成！")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())
