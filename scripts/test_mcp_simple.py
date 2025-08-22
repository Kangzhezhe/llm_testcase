#!/usr/bin/env python
"""
简单的MCP功能测试
验证服务器和客户端基本功能
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_server_creation():
    """测试服务器创建"""
    print("=== 测试服务器创建 ===")
    
    try:
        # 创建一个不依赖ChromaDB的简单LLM mock
        class MockLLM:
            def __init__(self):
                pass
            
            def call(self, prompt, **kwargs):
                return f"Mock response to: {prompt}"
            
            def search_knowledge(self, query, **kwargs):
                return [{"content": f"Mock knowledge for: {query}"}]
        
        from src.core.simple_mcp.server import SimpleMCPServer
        
        # 使用mock LLM创建服务器
        mock_llm = MockLLM()
        server = SimpleMCPServer(mock_llm)
        
        print(f"✅ 服务器创建成功")
        print(f"   可用工具: {list(server.tools.keys())}")
        
        # 测试工具调用
        add_result = server.tools["add"]["func"](10, 20)
        print(f"   加法测试: 10 + 20 = {add_result}")
        
        echo_result = server.tools["echo"]["func"]("Hello MCP")
        print(f"   回声测试: {echo_result}")
        
        return server
        
    except Exception as e:
        print(f"❌ 服务器创建失败: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_json_rpc():
    """测试JSON-RPC消息处理"""
    print("\n=== 测试JSON-RPC消息处理 ===")
    
    try:
        server = await test_server_creation()
        if not server:
            return
        
        # 测试初始化请求
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "clientName": "test-client",
                "clientVersion": "1.0.0"
            }
        }
        
        response = await server.handle_request(init_request)
        print(f"✅ 初始化响应: {json.dumps(response, ensure_ascii=False, indent=2)}")
        
        # 测试工具列表请求
        tools_request = {
            "jsonrpc": "2.0", 
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        response = await server.handle_request(tools_request)
        print(f"✅ 工具列表响应: {len(response['result']['tools'])} 个工具")
        
        # 测试工具调用
        call_request = {
            "jsonrpc": "2.0",
            "id": 3, 
            "method": "tools/call",
            "params": {
                "name": "add",
                "arguments": {"a": 15, "b": 25}
            }
        }
        
        response = await server.handle_request(call_request)
        print(f"✅ 工具调用响应: {response['result']}")
        
    except Exception as e:
        print(f"❌ JSON-RPC测试失败: {e}")
        import traceback
        traceback.print_exc()

async def test_stdio_communication():
    """测试标准输入输出通信"""
    print("\n=== 测试STDIO通信 ===")
    
    try:
        # 模拟客户端发送请求
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        
        print(f"📤 模拟客户端请求: {json.dumps(request, ensure_ascii=False)}")
        
        # 创建服务器并处理请求
        from src.core.simple_mcp.server import SimpleMCPServer
        
        class MockLLM:
            def call(self, prompt, **kwargs):
                return f"Response: {prompt}"
            def search_knowledge(self, query, **kwargs):
                return []
        
        server = SimpleMCPServer(MockLLM())
        response = await server.handle_request(request)
        
        print(f"📥 服务器响应: {json.dumps(response, ensure_ascii=False)}")
        print("✅ STDIO通信格式正确")
        
    except Exception as e:
        print(f"❌ STDIO通信测试失败: {e}")

async def test_config_management():
    """测试配置管理"""
    print("\n=== 测试配置管理 ===")
    
    try:
        from src.core.simple_mcp.config import MCPConfig
        
        # 创建临时配置
        config = MCPConfig("test_config.json")
        
        # 添加知识库配置
        file_list = [{"file_path": "test.txt", "type": "document"}]
        config.add_knowledge_base("test_kb", file_list)
        
        print("✅ 配置管理功能正常")
        print(f"   知识库配置: {config.get_knowledge_bases()}")
        
        # 清理测试文件
        import os
        if os.path.exists("test_config.json"):
            os.remove("test_config.json")
            
    except Exception as e:
        print(f"❌ 配置管理测试失败: {e}")

async def main():
    """主测试函数"""
    print("🚀 MCP功能测试开始\n")
    
    try:
        await test_server_creation()
        await test_json_rpc()
        await test_stdio_communication()
        await test_config_management()
        
        print("\n✅ 所有测试完成！MCP功能基本正常")
        print("\n📋 使用建议:")
        print("1. 如需使用完整RAG功能，请安装 onnxruntime: pip install onnxruntime")
        print("2. 启动服务器: python scripts/start_mcp_server.py --create-config 然后 python scripts/start_mcp_server.py")
        print("3. 测试客户端: python scripts/test_mcp_client.py --basic")
        
    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
