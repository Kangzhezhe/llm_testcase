"""
测试Agent的MCP功能
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.llm.agent import Agent, create_agent_with_tools, create_agent_with_mcp

# 尝试导入MCP相关模块
try:
    from src.core.llm.mcp_client import MCPServerConfig, MCPTransportType, MCP_AVAILABLE
except ImportError:
    MCP_AVAILABLE = False


def test_traditional_agent():
    """测试传统Agent功能"""
    print("=== 测试传统Agent功能 ===")
    
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

    # 创建Agent
    agent = create_agent_with_tools(
        tools=[add, multiply, echo],
        logger=True,
        max_iterations=3
    )
    
    print(f"可用工具: {agent.get_available_tools()}")
    
    # 测试简单计算
    print("\n--- 测试简单计算 ---")
    result1 = agent.chat("请帮我计算 5 + 3")
    print(f"结果: {result1['final_response']}")
    print(f"工具调用: {result1['tool_calls']}")
    
    # 测试复合计算
    print("\n--- 测试复合计算 ---")
    result2 = agent.chat("请计算 (2 + 3) × 4，每一步都要用工具")
    print(f"结果: {result2['final_response']}")
    print(f"工具调用: {result2['tool_calls']}")
    print(f"迭代次数: {result2['iterations']}")


async def test_mcp_agent():
    """测试MCP Agent功能"""
    if not MCP_AVAILABLE:
        print("=== MCP功能不可用，跳过测试 ===")
        return
    
    print("=== 测试MCP Agent功能 ===")
    
    # 创建MCP配置
    mcp_configs = [
        MCPServerConfig(
            name="demo",
            command="python",
            args=["-m", "src.core.llm.demo_mcp_server"],
            transport=MCPTransportType.STDIO
        )
    ]
    
    try:
        # 创建支持MCP的Agent
        agent = create_agent_with_mcp(
            mcp_configs=mcp_configs,
            logger=True,
            max_iterations=5
        )
        
        # 初始化MCP连接
        print("初始化MCP连接...")
        await agent.init_mcp()
        
        # 获取可用工具
        tools = agent.get_available_tools()
        print(f"可用工具: {tools}")
        
        # 测试MCP工具调用
        print("\n--- 测试MCP计算工具 ---")
        result1 = agent.chat("请使用calculate工具计算 15 × 3", use_mcp=True)
        print(f"结果: {result1['final_response']}")
        print(f"工具调用: {result1['tool_calls']}")
        
        # 测试获取时间
        print("\n--- 测试获取时间 ---")
        result2 = agent.chat("请获取当前时间", use_mcp=True)
        print(f"结果: {result2['final_response']}")
        print(f"工具调用: {result2['tool_calls']}")
        
        # 测试天气查询
        print("\n--- 测试天气查询 ---")
        result3 = agent.chat("请查询北京的天气", use_mcp=True)
        print(f"结果: {result3['final_response']}")
        print(f"工具调用: {result3['tool_calls']}")
        
    except Exception as e:
        print(f"MCP Agent测试出错: {e}")
    finally:
        # 清理MCP连接
        await agent.cleanup_mcp()


async def test_mixed_agent():
    """测试混合使用传统工具和MCP工具的Agent"""
    if not MCP_AVAILABLE:
        print("=== MCP功能不可用，跳过混合测试 ===")
        return
    
    print("=== 测试混合Agent功能 ===")
    
    # 定义传统工具
    def subtract(a: float, b: float) -> float:
        """减法工具"""
        return a - b

    def divide(a: float, b: float) -> float:
        """除法工具"""
        if b == 0:
            return "除数不能为零"
        return a / b

    # 创建MCP配置
    mcp_configs = [
        MCPServerConfig(
            name="demo",
            command="python",
            args=["-m", "src.core.llm.demo_mcp_server"],
            transport=MCPTransportType.STDIO
        )
    ]
    
    try:
        # 创建支持混合工具的Agent
        agent = Agent(
            logger=True,
            max_iterations=6,
            mcp_configs=mcp_configs
        )
        
        # 注册传统工具
        agent.register_tools([subtract, divide])
        
        # 初始化MCP连接
        await agent.init_mcp()
        
        # 获取所有可用工具
        tools = agent.get_available_tools()
        print(f"所有可用工具: {tools}")
        
        # 测试传统工具
        print("\n--- 使用传统工具 ---")
        result1 = agent.chat("请计算 10 - 3", use_tools=True, use_mcp=False)
        print(f"传统工具结果: {result1['final_response']}")
        print(f"工具调用: {result1['tool_calls']}")
        
        # 测试MCP工具
        print("\n--- 使用MCP工具 ---")
        result2 = agent.chat("请获取当前时间", use_mcp=True)
        print(f"MCP工具结果: {result2['final_response']}")
        print(f"工具调用: {result2['tool_calls']}")
        
        # 测试复杂场景（可能需要多种工具）
        print("\n--- 复杂场景测试 ---")
        result3 = agent.chat(
            "请先用传统工具计算 20 ÷ 4，然后告诉我现在的时间", 
            use_tools=True, 
            use_mcp=True
        )
        print(f"复杂场景结果: {result3['final_response']}")
        print(f"工具调用: {result3['tool_calls']}")
        print(f"迭代次数: {result3['iterations']}")
        
    except Exception as e:
        print(f"混合Agent测试出错: {e}")
    finally:
        await agent.cleanup_mcp()


async def main():
    """主测试函数"""
    print("开始测试Agent的MCP功能")
    print("=" * 60)
    
    # 测试传统Agent
    test_traditional_agent()
    
    print("\n" + "=" * 60)
    
    # 测试MCP Agent
    await test_mcp_agent()
    
    print("\n" + "=" * 60)
    
    # 测试混合Agent
    await test_mixed_agent()
    
    print("\n" + "=" * 60)
    print("Agent MCP功能测试完成！")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())
