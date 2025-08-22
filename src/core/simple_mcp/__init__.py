"""
MCP集成模块
将MCP功能集成到主LLM项目中
"""
from .server import SimpleMCPServer, run_simple_mcp_server
from .client import SimpleMCPClient, SimpleMCPClientManager, demo_simple_mcp_client
from .config import MCPConfig, MCPToolRegistry, create_default_tools, MCPServerLauncher
from .cli import main as cli_main

# 兼容性别名
MCPLLMServer = SimpleMCPServer
MCPLLMClient = SimpleMCPClient
MCPClientManager = SimpleMCPClientManager
run_mcp_server = run_simple_mcp_server
demo_mcp_client = demo_simple_mcp_client

__all__ = [
    'SimpleMCPServer',
    'SimpleMCPClient', 
    'SimpleMCPClientManager',
    'MCPConfig',
    'MCPToolRegistry',
    'MCPServerLauncher',
    'run_simple_mcp_server',
    'demo_simple_mcp_client',
    'create_default_tools',
    'cli_main',
    # 兼容性别名
    'MCPLLMServer',
    'MCPLLMClient',
    'MCPClientManager', 
    'run_mcp_server',
    'demo_mcp_client'
]

# 版本信息
__version__ = "1.0.0"
__author__ = "LLM Framework Team"
__description__ = "Model Context Protocol integration for LLM framework"
