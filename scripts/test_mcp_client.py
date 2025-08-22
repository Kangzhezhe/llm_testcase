#!/usr/bin/env python
"""
MCP客户端测试脚本
"""
import asyncio
import sys
import json
import pytest
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.simple_mcp import SimpleMCPClientManager, demo_simple_mcp_client

# pytest支持的测试函数
@pytest.mark.asyncio
async def test_basic_operations():
    """测试基础操作 - pytest版本"""
    await _test_basic_operations()

@pytest.mark.asyncio  
async def test_advanced_features():
    """测试高级功能 - pytest版本"""
    await _test_advanced_features()

async def _test_basic_operations():
    """测试基础操作"""
    print("=== 基础操作测试 ===\n")
    
    try:
        async with SimpleMCPClientManager() as client:
            # 1. 列出资源
            print("1. 资源列表:")
            resources = await client.list_resources()
            for resource in resources:
                print(f"   - {resource['name']}: {resource['uri']}")
            
            # 2. 列出工具
            print("\n2. 工具列表:")
            tools = await client.list_tools()
            for tool in tools:
                print(f"   - {tool['name']}: {tool['description']}")
            
            # 3. 测试数学运算
            print("\n3. 数学运算测试:")
            try:
                result = await client.add_numbers(10, 20)
                print(f"   10 + 20 = {result}")
                
                result = await client.multiply_numbers(6, 7)
                print(f"   6 × 7 = {result}")
            except Exception as e:
                print(f"   数学运算失败: {e}")
            
            # 4. 测试文本工具
            print("\n4. 文本工具测试:")
            try:
                result = await client.call_tool("echo", {"text": "Hello MCP!"})
                print(f"   回声: {result}")
            except Exception as e:
                print(f"   文本工具失败: {e}")
            
            # 5. 测试聊天
            print("\n5. 聊天测试:")
            try:
                response = await client.chat("请简单介绍一下MCP协议")
                print(f"   回复: {response}")
            except Exception as e:
                print(f"   聊天失败: {e}")
            
    except Exception as e:
        print(f"连接服务器失败: {e}")
        print("请确保MCP服务器正在运行")

async def _test_advanced_features():
    """测试高级功能"""
    print("\n=== 高级功能测试 ===\n")
    
    try:
        async with SimpleMCPClientManager() as client:
            # 1. 结构化输出
            print("1. 结构化输出测试:")
            try:
                template = "名称={name:str}，数量={count:int}，描述={desc:str}"
                result = await client.structured_chat("请输出一个产品信息示例", template)
                print(f"   结构化结果: {result}")
            except Exception as e:
                print(f"   结构化输出失败: {e}")
            
            # 2. 知识库搜索
            print("\n2. 知识库搜索测试:")
            try:
                kb_results = await client.search_knowledge("产品需求", top_k=3)
                print(f"   搜索结果数量: {len(kb_results) if kb_results else 0}")
                if kb_results:
                    for i, result in enumerate(kb_results[:2], 1):
                        if isinstance(result, dict) and 'content' in result:
                            content = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
                            print(f"   结果{i}: {content}")
            except Exception as e:
                print(f"   知识库搜索失败: {e}")
            
            # 3. RAG聊天
            print("\n3. RAG聊天测试:")
            try:
                response = await client.chat("什么是产品需求文档？", use_rag=True)
                print(f"   RAG回复: {response}")
            except Exception as e:
                print(f"   RAG聊天失败: {e}")
                
    except Exception as e:
        print(f"高级功能测试失败: {e}")

async def interactive_mode():
    """交互模式 - 重用CLI中的实现"""
    print("\n=== 交互模式 ===")
    print("调用CLI中的交互模式...")
    
    try:
        # 导入CLI模块
        from src.core.simple_mcp.cli import run_client_interactive
        
        # 创建模拟的args对象
        class MockArgs:
            def __init__(self):
                self.interactive = True
                self.demo = False
                self.server_cmd = None
        
        args = MockArgs()
        
        # 调用CLI中的交互模式
        return await run_client_interactive(args)
        
    except Exception as e:
        print(f"交互模式失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP客户端测试")
    parser.add_argument("--demo", action="store_true", help="运行完整演示")
    parser.add_argument("--basic", action="store_true", help="运行基础测试")
    parser.add_argument("--advanced", action="store_true", help="运行高级测试")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    
    args = parser.parse_args()
    
    if not any([args.demo, args.basic, args.advanced, args.interactive]):
        # 默认运行基础测试
        args.basic = True
    
    try:
        if args.demo:
            await demo_simple_mcp_client()
        
        if args.basic:
            await _test_basic_operations()
        
        if args.advanced:
            await _test_advanced_features()
        
        if args.interactive:
            await interactive_mode()
            
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
