"""
MCP功能测试
"""
import pytest
import asyncio
import json
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from ..server import SimpleMCPServer
from ..client import SimpleMCPClient, SimpleMCPClientManager
from ..config import MCPConfig, MCPToolRegistry, create_default_tools
from src.core.llm.llm import LLM

class TestMCPServer:
    """MCP服务器测试"""
    
    def test_server_creation(self):
        """测试服务器创建"""
        server = SimpleMCPServer()
        
        # SimpleMCPServer 不需要llm参数，工具在初始化时注册
        assert "add" in server.tools
        assert "multiply" in server.tools
        assert "echo" in server.tools
        assert "search_knowledge" in server.tools
    
    def test_tool_registration(self):
        """测试工具注册"""
        server = SimpleMCPServer()
        
        def test_func(x: int, y: int) -> int:
            return x + y
        
        server.register_tool("test_tool", test_func, "测试工具")
        
        assert "test_tool" in server.tools
        assert server.tools["test_tool"]["func"] == test_func
        assert server.tools["test_tool"]["description"] == "测试工具"
    
    def test_knowledge_base_registration(self):
        """测试知识库注册"""
        import tempfile
        import os
        
        llm = LLM()
        server = SimpleMCPServer(llm)
        
        # 创建临时测试文件，使用英文内容避免编码问题
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("This is test content for MCP knowledge base testing.")
            temp_file_path = f.name
        
        try:
            file_list = [{"file_path": temp_file_path, "type": "document"}]
            
            # SimpleMCPServer 直接注册知识库，不需要mock llm
            server.register_knowledge_base("test_kb", file_list)
            
            assert "test_kb" in server.knowledge_bases
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        assert "knowledge_base_test_kb" in server.resources

class TestMCPConfig:
    """MCP配置测试"""
    
    def test_config_creation(self):
        """测试配置创建"""
        config = MCPConfig()
        
        assert "server" in config.config
        assert "tools" in config.config
        assert "knowledge_bases" in config.config
    
    def test_knowledge_base_addition(self):
        """测试添加知识库"""
        config = MCPConfig()
        
        file_list = [{"file_path": "test.txt", "type": "document"}]
        config.add_knowledge_base("test_kb", file_list, max_len=1000)
        
        assert "test_kb" in config.config["knowledge_bases"]
        assert config.config["knowledge_bases"]["test_kb"]["file_list"] == file_list
    
    def test_custom_tool_addition(self):
        """测试添加自定义工具"""
        config = MCPConfig()
        
        config.add_custom_tool("custom_tool", "自定义工具", "module.path", "function_name")
        
        assert "custom_tool" in config.config["tools"]["custom"]
        assert "custom_tool" in config.config["tools"]["enabled"]

class TestMCPToolRegistry:
    """工具注册表测试"""
    
    def test_registry_creation(self):
        """测试注册表创建"""
        registry = MCPToolRegistry()
        
        assert isinstance(registry.tools, dict)
        assert isinstance(registry.categories, dict)
    
    def test_tool_registration(self):
        """测试工具注册"""
        registry = MCPToolRegistry()
        
        def test_func(x: int) -> int:
            return x * 2
        
        registry.register("double", test_func, "双倍函数", "math")
        
        assert "double" in registry.tools
        assert "double" in registry.categories["math"]
        assert registry.tools["double"]["func"] == test_func
    
    def test_default_tools_creation(self):
        """测试默认工具创建"""
        registry = create_default_tools()
        
        assert "add" in registry.tools
        assert "echo" in registry.tools
        assert "current_time" in registry.tools
        
        # 测试工具分类
        assert "add" in registry.categories["math"]
        assert "echo" in registry.categories["text"]
        assert "current_time" in registry.categories["utility"]

class TestMCPClient:
    """MCP客户端测试"""
    
    @pytest.mark.asyncio
    async def test_client_creation(self):
        """测试客户端创建"""
        client = SimpleMCPClient()
        
        assert client.process is None
        assert isinstance(client.server_command, list)
        assert client.request_id == 0
        assert client.initialized == False
    
    @pytest.mark.asyncio
    async def test_client_manager(self):
        """测试客户端管理器"""
        # 由于需要真实的服务器连接，这里只测试创建
        manager = SimpleMCPClientManager()
        assert isinstance(manager.client, SimpleMCPClient)
        assert manager.connected is False

class TestMCPIntegration:
    """MCP集成测试"""
    
    def test_tool_parameter_inference(self):
        """测试工具参数推断"""
        from src.core.llm.tool_call import infer_param_model
        
        def sample_func(a: int, b: str, c: float = 1.0) -> str:
            return f"{a}-{b}-{c}"
        
        model = infer_param_model(sample_func)
        schema = model.model_json_schema()
        
        assert "a" in schema["properties"]
        assert "b" in schema["properties"] 
        assert "c" in schema["properties"]
    
    def test_server_with_llm_integration(self):
        """测试服务器与LLM集成"""
        # 创建Mock LLM
        mock_llm = Mock(spec=LLM)
        mock_llm.call.return_value = "Test response"
        mock_llm.search_knowledge.return_value = []
        
        server = SimpleMCPServer()
        
        # 测试工具调用
        result = server.tools["add"]["func"](1, 2)
        assert result == 3
        
        # 测试回声工具
        result = server.tools["echo"]["func"]("test")
        assert "test" in result

# 运行测试的辅助函数
def run_tests():
    """运行所有测试"""
    pytest.main([__file__, "-v"])

if __name__ == "__main__":
    run_tests()
