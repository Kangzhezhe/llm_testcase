"""
测试不同MCP传输类型的演示脚本
"""

import asyncio
import sys
import os
import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.core.llm.agent import Agent
from src.core.llm.llm import LLM
from src.core.llm.mcp_client import (
    MCPToolCaller, 
    MCPServerConfig, 
    MCPTransportType,
    create_http_mcp_config,
    create_custom_mcp_config
)


async def _test_stdio_transport():
    """测试STDIO传输"""
    print("=== 测试STDIO传输 ===")
    
    configs = [
        MCPServerConfig(
            name="demo",
            command="python",
            args=["-m", "src.core.llm.demo.demo_mcp_server"],
            transport=MCPTransportType.STDIO
        )
    ]
    
    caller = MCPToolCaller(configs)
    
    try:
        await caller.connect_servers()
        print("可用工具:", caller.get_available_tools())
        
        # 测试工具调用
        result = await caller.call_tool("demo.calculate", operation="add", a=5, b=3)
        print(f"计算结果: {result}")
        
    except Exception as e:
        print(f"STDIO测试失败: {e}")
    finally:
        await caller.disconnect_servers()


async def _test_http_transport():
    """测试HTTP传输"""
    print("\n=== 测试HTTP传输 ===")
    
    # 使用便捷函数创建HTTP配置
    config = create_http_mcp_config("http_demo", "http://127.0.0.1:8000", streamable=False)
    caller = MCPToolCaller([config])
    
    try:
        await caller.connect_servers()
        print("可用工具:", caller.get_available_tools())
        
        # 测试工具调用
        result = await caller.call_tool("http_demo.add_numbers", a=10, b=20)
        print(f"加法结果: {result}")
        
    except Exception as e:
        print(f"HTTP测试失败: {e}")
    finally:
        await caller.disconnect_servers()


async def _test_streamable_http_transport():
    """测试Streamable HTTP传输"""
    print("\n=== 测试Streamable HTTP传输 ===")
    
    # 使用便捷函数创建Streamable HTTP配置
    config = create_http_mcp_config("streamable_demo", "http://127.0.0.1:8000", streamable=True)
    caller = MCPToolCaller([config])
    
    try:
        await caller.connect_servers()
        print("可用工具:", caller.get_available_tools())
        
        # 测试工具调用
        result = await caller.call_tool("streamable_demo.get_current_datetime")
        print(f"当前时间: {result}")
        
        # 测试面积计算
        result = await caller.call_tool("streamable_demo.calculate_circle_area", radius=5)
        print(f"圆形面积: {result}")
        
    except Exception as e:
        print(f"Streamable HTTP测试失败: {e}")
    finally:
        await caller.disconnect_servers()


async def _test_custom_transport():
    """测试自定义传输配置"""
    print("\n=== 测试自定义传输配置 ===")
    
    # 创建自定义配置
    custom_config_dict = {
        "mcpServers": {
            "custom_http": {
                "transport": "streamable-http",
                "url": "http://127.0.0.1:8000"
            }
        }
    }
    
    config = create_custom_mcp_config("custom_http", custom_config_dict)
    caller = MCPToolCaller([config])
    
    try:
        await caller.connect_servers()
        print("可用工具:", caller.get_available_tools())
        
        # 测试工具调用
        result = await caller.call_tool("custom_http.echo_text", text="Hello Custom MCP!")
        print(f"回声结果: {result}")
        
    except Exception as e:
        print(f"自定义传输测试失败: {e}")
    finally:
        await caller.disconnect_servers()


async def _test_llm_tool_call_parsing():
    """测试LLM输出解析和工具调用"""
    print("\n=== 测试LLM输出解析 ===")
    
    config = create_http_mcp_config("parse_demo", "http://127.0.0.1:8000", streamable=True)
    caller = MCPToolCaller([config])

    llm = LLM(mcp_configs=[config])
    output = await llm.call_async('用工具计算 半径为3 的圆的面积',use_mcp=True)
    print(f"LLM调用结果: {output}")
    
    try:
        await caller.connect_servers()
        
        # 获取工具使用说明
        instructions = caller.get_instructions()
        print("工具使用说明:")
        print(instructions)
        
        # 模拟LLM输出
        llm_output = '{"tool_call": {"name": "parse_demo.add_numbers", "args": {"a": 15, "b": 25}}}'
        print(f"\nLLM输出: {llm_output}")
        
        # 解析并调用工具
        tool_name, result = await caller.call(llm_output)
        print(f"解析结果 - 工具: {tool_name}, 结果: {result}")
        
    except Exception as e:
        print(f"LLM解析测试失败: {e}")
    finally:
        await caller.disconnect_servers()

async def _test_llm_mcp_connect():
    print("\n=== 测试LLM与MCP连接 ===")

    config = MCPServerConfig(
        name="amap-amap-sse",
        transport=MCPTransportType.SSE,
        url="https://mcp.amap.com/sse?key=749937bed60616bdaa37491c5415006b"
    )
    
    caller = MCPToolCaller([config])
    
    try:
        await caller.connect_servers()
        print("可用工具:", caller.get_available_tools())
        print(caller.available_tools)
        
    except Exception as e:
        print(f"自定义传输测试失败: {e}")
    finally:
        await caller.disconnect_servers()

    agent = Agent(mcp_configs=[config],max_iterations=10)
    output = await agent.chat_async('帮我查一下华中科技大学到武汉站的地铁路线',use_mcp=True)
    print(f"LLM调用结果: {output}")



async def main():
    """主测试函数"""
    print("MCP传输类型测试")
    print("=" * 50)
    
    # 注意：需要先启动HTTP服务器才能测试HTTP相关功能
    print("提示: 在测试HTTP传输前，请先启动HTTP MCP服务器:")
    print("python src/core/llm/demo/demo_mcp_http_server.py")
    print("=" * 50)
    
    # 按顺序测试不同传输类型
    tests = [
        # ("STDIO传输", _test_stdio_transport),
        # ("HTTP传输", _test_http_transport),
        # ("Streamable HTTP传输", _test_streamable_http_transport),
        # ("自定义传输", _test_custom_transport),
        # ("LLM解析", _test_llm_tool_call_parsing),
        ("LLM与MCP连接", _test_llm_mcp_connect)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n开始测试: {test_name}")
            await test_func()
            print(f"✓ {test_name} 测试完成")
        except Exception as e:
            print(f"✗ {test_name} 测试失败: {e}")
        
        # 在测试之间暂停
        await asyncio.sleep(1)
    
    print("\n" + "=" * 50)
    print("所有传输类型测试完成")


if __name__ == "__main__":
    asyncio.run(main())
